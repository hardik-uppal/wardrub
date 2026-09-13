"""Original-photo capture contracts; no live model, storage or private photos."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from io import BytesIO
import unittest
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException, UploadFile
from app.models.garment import FitObservation, GarmentMetadata
from app.services.clothing_detection import normalize_detections
from app.routers import garment
from app.services.firestore import FirestoreService


def detection(**fit):
    return {
        "category": "top",
        "name": "Blue shirt",
        "description": "Blue shirt with a dropped shoulder",
        "style_tags": ["casual"],
        "fit_observation": {
            "source": "worn",
            "fit": "loose",
            "length": "hip length",
            "drape": "Fabric falls away from the torso",
            "evidence": ["Visible space through the torso"],
            "confidence": 0.85,
            "visibility": "clear",
            **fit,
        },
    }


class DetectionTests(unittest.TestCase):
    def test_worn_fit_requires_visible_evidence(self):
        self.assertEqual(
            normalize_detections([detection()])[0]["fit_observation"]["fit"], "loose"
        )
        for change in [
            {"source": "flat"},
            {"source": "hanging"},
            {"visibility": "partial"},
            {"confidence": 0.4},
            {"evidence": []},
        ]:
            self.assertEqual(
                normalize_detections([detection(**change)])[0]["fit_observation"][
                    "fit"
                ],
                "unknown",
            )

    def test_bad_optional_fit_does_not_destroy_label_or_default_regular(self):
        for change in [
            {"fit": "medium"},
            {"confidence": float("nan")},
            {"evidence": "invented"},
        ]:
            result = normalize_detections([detection(**change)])[0]
            self.assertEqual(result["name"], "Blue shirt")
            self.assertEqual(result["fit_observation"]["fit"], "unknown")
        self.assertIsNone(
            GarmentMetadata(
                garment_id="old", user_id="a", category="top"
            ).fit_observation
        )

    def test_invalid_category_or_unbounded_response_rejected(self):
        for raw in [
            [{**detection(), "category": "watch"}],
            [detection()] * 9,
            {"category": "top"},
        ]:
            with self.assertRaises(ValueError):
                normalize_detections(raw)


class CaptureTests(unittest.IsolatedAsyncioTestCase):
    async def test_original_fit_and_label_persist_independently_of_generated_image(
        self,
    ):
        save = AsyncMock(return_value=True)
        with patch.object(
            garment, "read_photo", AsyncMock(return_value=b"original")
        ), patch.object(
            garment.vertex_ai,
            "detect_clothes_in_image",
            AsyncMock(return_value=[detection()]),
        ), patch.object(
            garment.vertex_ai,
            "create_ghost_mannequin_from_description",
            AsyncMock(return_value=b"generated"),
        ) as render, patch.object(
            garment.storage, "upload_source_image", AsyncMock(return_value="source")
        ), patch.object(
            garment.storage, "upload_garment", AsyncMock(return_value="clean")
        ), patch.object(
            garment.firestore, "save_garment_metadata", save
        ):
            result = await garment.process_uploaded_clothes(
                UploadFile(BytesIO(b"input")), {"uid": "alice"}
            )
        metadata = save.await_args.args[0]
        self.assertEqual(metadata.user_id, "alice")
        self.assertEqual(metadata.description.short, "Blue shirt")
        self.assertEqual(metadata.fit_observation.fit, "loose")
        self.assertIsNone(
            metadata.fit_type
        )  # observed on a wearer, not a calibrated garment cut
        self.assertEqual(metadata.source_images[0].url, "source")
        self.assertEqual(
            metadata.weather_range.max_temp, 40
        )  # no category-based warmth guess
        self.assertEqual(render.await_args.kwargs["image_bytes"], b"original")
        self.assertTrue(save.await_args.kwargs["strict"])
        self.assertEqual(
            result["garments"][0]["fit_observation"]["basis"], "original_photo"
        )

    async def test_partial_item_failure_returns_saved_items_without_inviting_whole_photo_retry(
        self,
    ):
        with patch.object(
            garment, "read_photo", AsyncMock(return_value=b"original")
        ), patch.object(
            garment.vertex_ai,
            "detect_clothes_in_image",
            AsyncMock(
                return_value=[detection(), {**detection(), "category": "bottom"}]
            ),
        ), patch.object(
            garment.vertex_ai,
            "create_ghost_mannequin_from_description",
            AsyncMock(side_effect=[b"generated", RuntimeError("failed")]),
        ), patch.object(
            garment.storage, "upload_source_image", AsyncMock(return_value="source")
        ), patch.object(
            garment.storage, "upload_garment", AsyncMock(return_value="clean")
        ), patch.object(
            garment.firestore, "save_garment_metadata", AsyncMock(return_value=True)
        ):
            result = await garment.process_uploaded_clothes(
                UploadFile(BytesIO(b"input")), {"uid": "alice"}
            )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(len(result["garments"]), 1)

    async def test_labels_survive_wardrobe_reload_without_cross_user_metadata(self):
        own = GarmentMetadata(
            garment_id="a",
            user_id="alice",
            category="top",
            description={"short": "Blue shirt"},
            fit_observation=FitObservation(**detection()["fit_observation"]),
        )
        foreign = GarmentMetadata(
            garment_id="b",
            user_id="bob",
            category="top",
            description={"short": "Private"},
        )
        with patch.object(
            garment.storage,
            "list_garments",
            AsyncMock(
                return_value=[
                    {"id": "a", "front_url": "fresh"},
                    {"id": "b", "front_url": "other"},
                ]
            ),
        ), patch.object(
            garment.firestore,
            "list_garments_metadata",
            AsyncMock(return_value=[own, foreign]),
        ):
            result = await garment.get_wardrobe(user={"uid": "alice"})
        self.assertEqual(result["garments"][0]["front_url"], "fresh")
        self.assertEqual(result["garments"][0]["fit_observation"]["fit"], "loose")
        self.assertNotIn("description", result["garments"][1])

    async def test_strict_save_never_falls_back_when_production_storage_unavailable(
        self,
    ):
        service = FirestoreService()
        service._use_memory = True
        with patch("app.services.firestore.settings.ALLOW_DEV_AUTH_BYPASS", False):
            with self.assertRaises(RuntimeError):
                await service.save_garment_metadata(
                    GarmentMetadata(garment_id="a", user_id="alice", category="top"),
                    strict=True,
                )
