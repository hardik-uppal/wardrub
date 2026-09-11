import asyncio
from datetime import datetime
from io import BytesIO
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from app.models.user_profile import UserProfile
from app.routers import profile as profile_router
from app.services import firestore as firestore_module
from app.services.auth import get_current_user
from app.services.style_analysis import (
    MAX_PHOTO_BYTES, StyleAnalysisService, StyleEvidence, merge_analysis,
    prepare_photo, select_stages,
)


SKIN = dict(undertone="warm", depth="medium", hex_approximation="#B08060", season="autumn")


def evidence(color=True, fit=False, color_issues=None, fit_issues=None, confidence=0.9):
    return StyleEvidence(
        color=dict(sufficient=color, confidence=confidence,
                   issues=color_issues if color_issues is not None else ([] if color else ["lighting"]),
                   explanation="Skin lighting assessed.", skin_tone=SKIN if color else None),
        fit=dict(sufficient=fit, confidence=confidence,
                 issues=fit_issues if fit_issues is not None else ([] if fit else ["full_length_missing"]),
                 explanation="Body visibility assessed.", body_type="rectangle" if fit else None,
                 measurements=None),
    )


def photo_bytes(size=(320, 480), format="JPEG"):
    buffer = BytesIO()
    Image.new("RGB", size, (120, 100, 90)).save(buffer, format=format)
    return buffer.getvalue()


class StyleProgressTests(unittest.TestCase):
    def test_face_first_gives_colors_and_specific_fit_request(self):
        profile = merge_analysis(UserProfile(), evidence(), ["color", "fit"])
        self.assertEqual(profile.skin_tone.season.value, "autumn")
        self.assertIsNone(profile.body_type)
        self.assertEqual(profile.style_analysis.color.status, "ready")
        self.assertEqual(profile.style_analysis.fit.status, "needs_input")
        self.assertEqual(profile.style_analysis.fit.requested_input.photo_type, "full_length")
        self.assertEqual(select_stages(profile, "auto"), ["fit"])

    def test_fit_followup_preserves_colors_preferences_and_creation(self):
        original = UserProfile(style_preferences=["casual"],
                               location=dict(lat=28.6, lon=77.2, city="Delhi"),
                               created_at=datetime(2025, 1, 1), source_images=["existing-source"])
        first = merge_analysis(original, evidence(), ["color", "fit"])
        updated = merge_analysis(first, evidence(color=False, fit=True), ["fit"])
        self.assertEqual(updated.skin_tone, first.skin_tone)
        self.assertEqual(updated.style_analysis.color, first.style_analysis.color)
        self.assertEqual(updated.body_type, "rectangle")
        self.assertEqual(updated.style_preferences, ["casual"])
        self.assertEqual(updated.location.city, "Delhi")
        self.assertEqual(updated.created_at, original.created_at)
        self.assertEqual(updated.source_images, ["existing-source"])
        self.assertFalse(updated.analysis_quality.needs_more_images)

    def test_confidence_does_not_override_loose_clothing_or_lighting(self):
        for name, issue in (("color", "lighting"), ("fit", "loose_clothing")):
            with self.subTest(stage=name):
                report = evidence(color=True, fit=True, confidence=0.99,
                                  **{f"{name}_issues": [issue]})
                profile = merge_analysis(UserProfile(), report, [name])
                state = getattr(profile.style_analysis, name)
                self.assertEqual(state.status, "needs_input")
                self.assertIsNone(profile.skin_tone if name == "color" else profile.body_type)
                self.assertIn("lighting" if name == "color" else "Loose clothing", state.requested_input.reason)

    def test_low_confidence_and_missing_result_do_not_manufacture_results(self):
        for report in (evidence(confidence=0.69), evidence(color=False, color_issues=[])):
            profile = merge_analysis(UserProfile(), report, ["color"])
            self.assertIsNone(profile.skin_tone)
            self.assertEqual(profile.style_analysis.color.status, "needs_input")

    def test_uncertain_retry_preserves_previous_usable_result_and_date(self):
        first = merge_analysis(UserProfile(), evidence(color=True, fit=True), ["color", "fit"])
        updated = merge_analysis(first, evidence(color=False), ["color"])
        self.assertEqual(updated.skin_tone, first.skin_tone)
        self.assertEqual(updated.body_type, first.body_type)
        self.assertEqual(updated.style_analysis.color.result_updated_at, first.style_analysis.color.result_updated_at)
        self.assertEqual(updated.style_analysis.color.attempts, 2)
        self.assertEqual(updated.style_analysis.color.status, "needs_input")

    def test_provider_failure_has_retry_state_without_new_photo_request(self):
        first = merge_analysis(UserProfile(), evidence(color=True, fit=True), ["color", "fit"])
        updated = merge_analysis(first, None, ["fit"], failed=True)
        self.assertEqual(updated.style_analysis.fit.status, "failed")
        self.assertIsNone(updated.style_analysis.fit.requested_input)
        self.assertEqual(updated.body_type, first.body_type)
        self.assertEqual(updated.skin_tone, first.skin_tone)
        self.assertFalse(updated.analysis_quality.needs_more_images)

    def test_legacy_profiles_are_migrated_on_read_and_roundtrip(self):
        profile = UserProfile(skin_tone=SKIN)
        self.assertEqual(profile.style_analysis.color.status, "ready")
        self.assertEqual(profile.style_analysis.fit.status, "not_started")
        self.assertEqual(select_stages(profile, "auto"), ["fit"])
        self.assertEqual(UserProfile.model_validate_json(profile.model_dump_json()), profile)
        self.assertEqual(select_stages(profile, "color"), ["color"])

    def test_malformed_model_output_is_rejected(self):
        for value in ("{}", "not json", '{"color": {"confidence": 2}, "fit": {}}'):
            with self.assertRaises(ValidationError):
                StyleEvidence.model_validate_json(value)

    def test_all_blocking_issues_request_stage_appropriate_photo(self):
        for issue in ("multiple_people", "conflicting_photos", "blur", "uncertain"):
            with self.subTest(issue=issue):
                updated = merge_analysis(UserProfile(), evidence(color_issues=[issue]), ["color"])
                self.assertEqual(updated.style_analysis.color.status, "needs_input")
                self.assertEqual(updated.style_analysis.color.requested_input.photo_type, "face")

    def test_photo_validation_and_normalization(self):
        result = prepare_photo(photo_bytes(size=(1600, 1800), format="PNG"))
        with Image.open(BytesIO(result)) as photo:
            self.assertEqual(photo.format, "JPEG")
            self.assertLessEqual(max(photo.size), 1536)
        for raw in (b"", b"not an image", photo_bytes((40, 40)), photo_bytes(format="GIF")):
            with self.subTest(length=len(raw)), self.assertRaises(ValueError):
                prepare_photo(raw)


class StyleServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_sdk_serializes_request_and_parses_response_without_network(self):
        from google import genai
        client = genai.Client(api_key="test-not-a-real-key")
        payload = {"candidates": [{"content": {"role": "model", "parts": [{"text": evidence().model_dump_json()}]}}]}
        with patch.object(client._api_client, "request", return_value=payload) as transport, patch(
            "app.services.style_analysis.ColorAnalysisService._get_gemini_client", return_value=client
        ):
            result = await StyleAnalysisService().analyze([photo_bytes()])
        self.assertEqual(result, evidence())
        transport.assert_called_once()

    async def test_schema_is_supported_by_installed_gemini_sdk(self):
        from google import genai
        from google.genai import _transformers
        client = genai.Client(api_key="test-not-a-real-key")
        schema = _transformers.t_schema(client._api_client, StyleEvidence)
        self.assertEqual(set(schema.properties), {"color", "fit"})

    async def test_provider_receives_every_photo_and_structured_schema(self):
        expected = evidence()
        generate = Mock(return_value=SimpleNamespace(text=expected.model_dump_json()))
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
        with patch("app.services.style_analysis.ColorAnalysisService._get_gemini_client", return_value=client):
            result = await StyleAnalysisService().analyze([b"first", b"second"])
        self.assertEqual(result, expected)
        contents = generate.call_args.kwargs["contents"]
        self.assertEqual([p.inline_data.data for p in contents[1:]], [b"first", b"second"])
        self.assertEqual(generate.call_args.kwargs["config"].response_schema, StyleEvidence)

    async def test_provider_exception_is_not_converted_to_photo_uncertainty(self):
        client = SimpleNamespace(models=SimpleNamespace(generate_content=Mock(side_effect=RuntimeError("offline"))))
        with patch("app.services.style_analysis.ColorAnalysisService._get_gemini_client", return_value=client):
            with self.assertRaises(RuntimeError):
                await StyleAnalysisService().analyze([b"photo"])


class StylePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cloud_transaction_merges_into_latest_document(self):
        current = UserProfile(style_preferences=["recently edited"], skin_tone=SKIN)
        snapshot = Mock()
        snapshot.to_dict.return_value = current.model_dump()
        document = Mock()
        document.get.return_value = snapshot
        client = Mock()
        client.collection.return_value.document.return_value = document
        transaction = client.transaction.return_value
        service = firestore_module.FirestoreService()
        service._client = client
        with patch("google.cloud.firestore.transactional", side_effect=lambda fn: fn):
            result = await service.apply_style_analysis(evidence(color=False, fit=True), ["fit"], "alice")
        client.collection.assert_called_once_with("user_profiles")
        client.collection.return_value.document.assert_called_once_with("alice")
        document.get.assert_called_once_with(transaction=transaction)
        self.assertEqual(result.style_preferences, ["recently edited"])
        self.assertEqual(result.skin_tone, current.skin_tone)
        args, kwargs = transaction.set.call_args
        self.assertEqual(args[0], document)
        self.assertTrue(kwargs["merge"])
        self.assertNotIn("style_preferences", args[1])
        self.assertEqual(args[1]["style_analysis"]["fit"]["status"], "ready")

    async def test_cloud_write_failure_does_not_fall_back_to_local_storage(self):
        document = Mock()
        document.get.return_value.to_dict.return_value = {}
        client = Mock()
        client.collection.return_value.document.return_value = document
        client.transaction.return_value.set.side_effect = RuntimeError("cloud write failed")
        service = firestore_module.FirestoreService()
        service._client = client
        records = {}
        with patch("google.cloud.firestore.transactional", side_effect=lambda fn: fn), patch.object(firestore_module, "_memory_profiles", records):
            with self.assertRaisesRegex(RuntimeError, "cloud write failed"):
                await service.apply_style_analysis(evidence(), ["color"], "alice")
        self.assertEqual(records, {})

    async def test_updates_merge_latest_profile_and_isolate_users(self):
        records = {"alice": UserProfile(style_preferences=["new preference"]).model_dump(),
                   "bob": UserProfile(style_preferences=["untouched"]).model_dump()}
        service = firestore_module.FirestoreService()
        service._use_memory = True
        with patch.object(firestore_module, "_memory_profiles", records), patch.object(firestore_module.settings, "ALLOW_DEV_AUTH_BYPASS", True):
            await asyncio.gather(
                service.apply_style_analysis(evidence(), ["color"], "alice"),
                service.apply_style_analysis(evidence(fit=True), ["fit"], "alice"),
            )
            reread = await service.get_user_profile("alice")
        self.assertIsNotNone(reread.skin_tone)
        self.assertIsNotNone(reread.body_type)
        self.assertEqual(reread.style_preferences, ["new preference"])
        self.assertIsNone(records["bob"]["skin_tone"])

    async def test_no_production_fallback_when_storage_is_unavailable(self):
        service = firestore_module.FirestoreService()
        service._use_memory = True
        with patch.object(firestore_module.settings, "ALLOW_DEV_AUTH_BYPASS", False):
            with self.assertRaisesRegex(RuntimeError, "storage is unavailable"):
                await service.apply_style_analysis(evidence(), ["color"], "alice")


class StyleRouteTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(profile_router.router, prefix="/api")
        app.dependency_overrides[get_current_user] = lambda: {"uid": "alice"}
        self.app = app
        self.client = TestClient(app)
        self.records = {}
        self.addCleanup(self.client.close)
        for patcher in (
            patch.object(firestore_module, "_memory_profiles", self.records),
            patch.object(profile_router.firestore, "_use_memory", True),
            patch.object(firestore_module.settings, "ALLOW_DEV_AUTH_BYPASS", True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.analyze = AsyncMock(return_value=evidence())
        patcher = patch.object(profile_router.style_service, "analyze", self.analyze)
        patcher.start()
        self.addCleanup(patcher.stop)

    def upload(self, stage="auto", content=None, count=1):
        return self.client.post("/api/profile/analyze", data={"stage": stage},
                                files=[("files", ("photo.jpg", content if content is not None else photo_bytes(), "image/jpeg")) for _ in range(count)])

    def test_full_http_color_then_fit_journey_and_reload(self):
        first = self.upload().json()
        self.assertTrue(first["color_recommendations"]["best"])
        self.assertIsNone(first["fit_recommendations"])
        self.assertEqual(first["profile"]["style_analysis"]["fit"]["status"], "needs_input")
        self.analyze.return_value = evidence(color=False, fit=True)
        second = self.upload(stage="fit").json()
        self.assertTrue(second["fit_recommendations"]["tops"])
        self.assertEqual(first["color_recommendations"], second["color_recommendations"])
        reloaded = self.client.get("/api/profile").json()["profile"]
        self.assertEqual(reloaded["style_analysis"]["fit"]["status"], "ready")
        self.assertEqual(reloaded["source_images"], [])
        self.assertEqual(set(self.records), {"alice"})

    def test_failed_provider_returns_persisted_retry_state(self):
        first = self.upload().json()
        self.analyze.side_effect = TimeoutError()
        response = self.upload(stage="fit")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "failed")
        self.assertEqual(data["profile"]["style_analysis"]["fit"]["status"], "failed")
        self.assertEqual(data["color_recommendations"], first["color_recommendations"])

    def test_upload_validation_precedes_provider_and_storage(self):
        for kwargs, status in (({"count": 5}, 400), ({"content": b"fake"}, 400),
                               ({"content": b"x" * (MAX_PHOTO_BYTES + 1)}, 413),
                               ({"stage": "invalid"}, 422)):
            with self.subTest(kwargs=list(kwargs)):
                self.assertEqual(self.upload(**kwargs).status_code, status)
        self.analyze.assert_not_awaited()
        self.assertEqual(self.records, {})

    def test_storage_failure_is_not_reported_as_success(self):
        with patch.object(profile_router.firestore, "apply_style_analysis", AsyncMock(side_effect=RuntimeError("write failed"))):
            self.assertEqual(self.upload().status_code, 503)

    def test_authentication_required(self):
        self.app.dependency_overrides.clear()
        with patch.object(firestore_module.settings, "ALLOW_DEV_AUTH_BYPASS", False):
            self.assertIn(self.upload().status_code, (401, 403))
            self.assertIn(self.client.get("/api/profile").status_code, (401, 403))
        self.analyze.assert_not_awaited()


class AvatarAnalysisCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_opt_in_avatar_analysis_uses_originals_and_preserves_existing_colors(self):
        from fastapi import UploadFile
        from app.routers import avatar as avatar_router
        original = photo_bytes()
        records = {"alice": UserProfile(skin_tone=SKIN, style_preferences=["casual"]).model_dump()}
        analyze = AsyncMock(return_value=evidence(color=False, fit=True))
        with (
            patch.object(avatar_router.quality_service, "assess_image_quality", AsyncMock(return_value={"is_acceptable": True, "score": 0.9})),
            patch.object(avatar_router.storage, "upload_avatar_source", AsyncMock(return_value="existing-avatar-source")),
            patch.object(avatar_router.storage, "upload_avatar", AsyncMock(return_value="avatar-result")),
            patch.object(avatar_router.vertex_ai, "process_uploaded_avatar", AsyncMock(return_value=b"synthetic-avatar")),
            patch.object(avatar_router.firestore, "_use_memory", True),
            patch.object(firestore_module, "_memory_profiles", records),
            patch.object(firestore_module.settings, "ALLOW_DEV_AUTH_BYPASS", True),
            patch.object(avatar_router.StyleAnalysisService, "analyze", analyze),
        ):
            result = await avatar_router.create_avatar_full(
                files=[UploadFile(filename="photo.jpg", file=BytesIO(original))],
                mode="upload", analyze_profile=True, user={"uid": "alice"},
            )
        analyze.assert_awaited_once_with([prepare_photo(original)])
        self.assertEqual(result["profile"]["skin_tone"], SKIN)
        self.assertEqual(result["profile"]["style_preferences"], ["casual"])
        self.assertEqual(result["profile"]["style_analysis"]["fit"]["status"], "ready")


if __name__ == "__main__":
    unittest.main()
