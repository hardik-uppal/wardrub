"""Persistence contracts for the new daily wardrobe UI; no cloud/model calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from tempfile import TemporaryDirectory
from app.models.garment import GarmentMetadata
from app.routers.closet import (
    ClosetAction,
    ReadinessChange,
    router,
    library as route_library,
)
from app.services.closet_library import ClosetLibrary, apply_action, empty_library
from app.services.firestore import FirestoreService, _memory_garments
from app.services.auth import get_current_user
from fastapi import FastAPI
from fastapi.testclient import TestClient


def clothes():
    return [
        GarmentMetadata(
            garment_id="a", user_id="alice", category="top", readiness="ready"
        ),
        GarmentMetadata(
            garment_id="b", user_id="alice", category="bottom", readiness="unknown"
        ),
    ]


def request(action="save", version=0, **kwargs):
    return ClosetAction(
        action=action,
        expected_version=version,
        operation_id=kwargs.pop("operation_id", f"operation-{version}-{action.replace(chr(95), chr(45))}"),
        garment_ids=kwargs.pop("garment_ids", ["a", "b"]),
        **kwargs,
    )


class ReducerTests(unittest.TestCase):
    def test_save_replay_dedup_and_delete_preserve_daily_intent(self):
        r = request()
        state = apply_action(None, r, clothes(), "alice")
        saved_id = next(iter(state["outfits"]))
        self.assertEqual(apply_action(state, r, clothes(), "alice"), state)
        duplicate = apply_action(state, request(version=1), clothes(), "alice")
        self.assertEqual(len(duplicate["outfits"]), 1)
        planned = apply_action(
            duplicate, request("plan", 2, day="2026-09-13"), clothes(), "alice"
        )
        removed = apply_action(
            planned, request("delete", 3, outfit_id=saved_id), clothes(), "alice"
        )
        self.assertEqual(removed["outfits"], {})
        self.assertEqual(removed["days"]["2026-09-13"]["id"], saved_id)

    def test_stale_version_and_reused_operation_are_conflicts(self):
        state = apply_action(None, request(), clothes(), "alice")
        with self.assertRaises(ValueError):
            apply_action(state, request("plan", day="2026-09-13"), clothes(), "alice")
        with self.assertRaises(ValueError):
            apply_action(
                state,
                request(version=1, operation_id="operation-0-save"),
                clothes(),
                "alice",
            )

    def test_wear_and_undo_never_change_readiness(self):
        items = clothes()
        planned = apply_action(None, request("plan", day="2026-09-13"), items, "alice")
        worn = apply_action(
            planned, request("wore", 1, day="2026-09-13"), items, "alice"
        )
        self.assertTrue(worn["days"]["2026-09-13"]["worn"])
        with self.assertRaises(ValueError):
            apply_action(worn, request("plan", 2, day="2026-09-13"), items, "alice")
        key = worn["days"]["2026-09-13"]["id"]
        undone = apply_action(
            worn, request("unwear", 2, day="2026-09-13", outfit_id=key), items, "alice"
        )
        self.assertFalse(undone["days"]["2026-09-13"]["worn"])
        self.assertEqual([g.readiness for g in items], ["ready", "unknown"])

    def test_foreign_missing_duplicate_and_incomplete_clothes_rejected(self):
        for ids, who, error in [
            (["a", "b"], "bob", LookupError),
            (["a", "missing"], "alice", LookupError),
            (["a", "a"], "alice", LookupError),
            (["a"], "alice", ValueError),
        ]:
            with self.assertRaises(error):
                apply_action(None, request(garment_ids=ids), clothes(), who)

    def test_laundry_can_be_saved_but_not_planned_or_worn(self):
        items = clothes()
        items[0].readiness = "laundry"
        self.assertEqual(
            len(apply_action(None, request(), items, "alice")["outfits"]), 1
        )
        for action in ["plan", "wore"]:
            with self.assertRaises(ValueError):
                apply_action(None, request(action, day="2026-09-13"), items, "alice")

    def test_locations_and_explicit_preference_clear(self):
        state = apply_action(
            None, request("location", location="Top drawer"), clothes(), "alice"
        )
        self.assertEqual(state["locations"], {"a": "Top drawer", "b": "Top drawer"})
        state = apply_action(
            state, request("styles", 1, styles=["casual"], garment_ids=[]), [], "alice"
        )
        state = apply_action(
            state, request("styles", 2, styles=[], garment_ids=[]), [], "alice"
        )
        self.assertEqual(state["styles"], [])
        self.assertTrue(state["styles_set"])


class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_correction_is_durable_day_scoped_and_reversible(self):
        from app.models.user_profile import UserProfile
        from app.services.magazine_feed_service import MagazineFeedService

        items = clothes()
        correction = request("feedback", day="2026-09-13", reason="comfort")
        state = apply_action(None, correction, items, "alice")
        self.assertEqual(state["styles"], [])
        self.assertEqual(state["days"], {})
        self.assertEqual([g.readiness for g in items], ["ready", "unknown"])
        self.assertEqual(apply_action(state, correction, items, "alice"), state)
        with TemporaryDirectory() as directory, patch(
            "app.services.closet_library.LOCAL_DIR", Path(directory)
        ), patch("app.services.closet_library.settings.ALLOW_DEV_AUTH_BYPASS", True):
            store = ClosetLibrary()
            store.firestore._use_memory = True
            store.firestore.list_garments_metadata = AsyncMock(return_value=items)
            written = await store.mutate("alice", correction)
            persisted = await store.read("alice")
            self.assertEqual(persisted["feedback"], written["feedback"])
            feed = MagazineFeedService()
            profile = UserProfile(user_id="alice")
            feed.context = AsyncMock(
                return_value=(profile, items, None, "no_location", persisted)
            )
            today = await feed.generate_magazine_feed("alice", local_day="2026-09-13")
            tomorrow = await feed.generate_magazine_feed(
                "alice", local_day="2026-09-14"
            )
            self.assertIsNone(today.cover_look)
            self.assertTrue(today.skipped_for_day)
            self.assertIsNotNone(tomorrow.cover_look)
            undone = await store.mutate(
                "alice",
                request(
                    "undo_feedback",
                    1,
                    outfit_id=correction.operation_id,
                    garment_ids=[],
                ),
            )
            feed.context.return_value = (profile, items, None, "no_location", undone)
            restored = await feed.generate_magazine_feed(
                "alice", local_day="2026-09-13"
            )
            self.assertIsNotNone(restored.cover_look)

    async def test_explicit_styles_override_and_clear_without_changing_profile(self):
        from app.models.user_profile import UserProfile
        from app.services.magazine_feed_service import MagazineFeedService

        feed = MagazineFeedService()
        original = UserProfile(user_id="alice", style_preferences=["classic"])
        feed.firestore.ensure_user_profile = AsyncMock(return_value=original)
        feed.firestore.list_garments_metadata = AsyncMock(return_value=clothes())
        for state, expected in [
            ({}, ["classic"]),
            ({"styles_set": True, "styles": ["casual"]}, ["casual"]),
            ({"styles_set": True, "styles": []}, []),
        ]:
            with patch(
                "app.services.closet_library.ClosetLibrary.read",
                AsyncMock(return_value=state),
            ):
                profile, *_ = await feed.context("alice")
                self.assertEqual(profile.style_preferences, expected)
        self.assertEqual(original.style_preferences, ["classic"])

    async def test_local_restart_and_user_isolation(self):
        with TemporaryDirectory() as directory, patch(
            "app.services.closet_library.LOCAL_DIR", Path(directory)
        ), patch("app.services.closet_library.settings.ALLOW_DEV_AUTH_BYPASS", True):
            first = ClosetLibrary()
            first.firestore._use_memory = True
            first.firestore.list_garments_metadata = AsyncMock(return_value=clothes())
            await first.mutate("alice", request())
            second = ClosetLibrary()
            second.firestore._use_memory = True
            self.assertEqual(len((await second.read("alice"))["outfits"]), 1)
            self.assertEqual((await second.read("bob"))["outfits"], {})

    async def test_production_storage_failure_does_not_use_local_file(self):
        service = ClosetLibrary()
        service.firestore._use_memory = True
        with patch("app.services.closet_library.settings.ALLOW_DEV_AUTH_BYPASS", False):
            with self.assertRaises(RuntimeError):
                await service.read("alice")

    async def test_transaction_reads_owned_clothes_before_any_write(self):
        service = ClosetLibrary()
        client = MagicMock()
        service.firestore._client = client
        service.firestore.list_garments_metadata = AsyncMock(return_value=clothes())
        library_ref = MagicMock()
        library_ref.get.return_value.exists = False
        garment_refs = []
        for g in clothes():
            ref = MagicMock()
            ref.get.return_value.to_dict.return_value = g.model_dump()
            garment_refs.append(ref)

        def collection(name):
            coll = MagicMock()
            if name == "closet_libraries":
                coll.document.return_value = library_ref
            else:
                coll.document.side_effect = lambda gid: garment_refs[
                    ["a", "b"].index(gid)
                ]
            return coll

        client.collection.side_effect = collection
        with patch("google.cloud.firestore.transactional", lambda f: f):
            result = await service.mutate("alice", request())
        self.assertEqual(result["version"], 1)
        client.transaction.return_value.set.assert_called_once()
        for ref in garment_refs:
            ref.get.assert_called_once_with(transaction=client.transaction.return_value)

    async def test_batch_is_atomic_on_conflict_then_replay_and_undo(self):
        service = FirestoreService()
        service._use_memory = True
        data = {g.garment_id: g.model_dump() for g in clothes()}
        with patch.dict(_memory_garments, data, clear=True), patch(
            "app.services.firestore.settings.ALLOW_DEV_AUTH_BYPASS", True
        ), patch("app.services.firestore.save_local_db"):
            invalid = [
                ReadinessChange(id="a", readiness="laundry", expected_version=0),
                ReadinessChange(id="b", readiness="laundry", expected_version=9),
            ]
            with self.assertRaises(ValueError):
                await service.set_readiness_batch("alice", invalid)
            self.assertEqual(_memory_garments["a"]["readiness"], "ready")
            good = [
                ReadinessChange(
                    id=g.garment_id, readiness="laundry", expected_version=0
                )
                for g in clothes()
            ]
            await service.set_readiness_batch("alice", good)
            replay = await service.set_readiness_batch("alice", good)
            self.assertEqual([g.readiness_version for g in replay], [1, 1])
            with self.assertRaises(LookupError):
                await service.set_readiness_batch("bob", good)
            undo = [
                ReadinessChange(
                    id=g.garment_id, readiness=g.readiness, expected_version=1
                )
                for g in clothes()
            ]
            result = await service.set_readiness_batch("alice", undo)
            self.assertEqual([g.readiness for g in result], ["ready", "unknown"])

    async def test_avatar_candidate_does_not_replace_until_activation(self):
        from app.services.storage import StorageService, _memory_files

        service = StorageService()
        service._use_mock = True
        with patch.object(
            StorageService, "bucket", new_callable=lambda: property(lambda self: None)
        ), patch(
            "app.services.storage.settings.ALLOW_DEV_AUTH_BYPASS", True
        ), patch.dict(
            _memory_files, {}, clear=True
        ):
            await service.upload_avatar(b"old", "alice")
            candidate, _ = await service.upload_avatar_candidate(b"new", "alice")
            self.assertEqual(_memory_files["users/alice/avatar.png"], b"old")
            with self.assertRaises(FileNotFoundError):
                await service.activate_avatar_candidate("bob", candidate)
            await service.activate_avatar_candidate("alice", candidate)
            self.assertEqual(_memory_files["users/alice/avatar.png"], b"new")


class ApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: {"uid": "alice"}
        self.client = TestClient(app)

    def test_read_hides_operation_receipts(self):
        with patch.object(
            route_library, "read", AsyncMock(return_value=empty_library())
        ):
            response = self.client.get("/closet-library")
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("operations", response.json())

    def test_missing_auth_dependency_is_enforced(self):
        app = FastAPI()
        app.include_router(router)
        self.assertIn(TestClient(app).get("/closet-library").status_code, [401, 403])

    def test_validation_conflicts_and_storage_failures(self):
        payload = request().model_dump(mode="json")
        for error, status in [
            (ValueError("conflict"), 409),
            (LookupError("missing"), 404),
            (RuntimeError(), 503),
        ]:
            with patch.object(route_library, "mutate", AsyncMock(side_effect=error)):
                self.assertEqual(
                    self.client.post(
                        "/closet-library/actions", json=payload
                    ).status_code,
                    status,
                )
        payload["garment_ids"] = ["../other"]
        self.assertEqual(
            self.client.post("/closet-library/actions", json=payload).status_code, 422
        )


class TryOnContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_avatar_change_invalidates_cache_and_preserves_garment_identity(self):
        from app.routers import tryon

        request = tryon.MultiTryOnRequest(
            avatar_url="avatar",
            garments=[tryon.GarmentItem(id="a", url="shirt", category="top")],
        )
        cache = {}
        avatar = [b"first avatar"]

        async def download(url):
            return avatar[0] if url == "avatar" else b"shirt"

        async def save(**kwargs):
            cache[kwargs["cache_key"]] = kwargs["result_url"]

        storage = MagicMock()
        storage.download_image = AsyncMock(side_effect=download)
        storage.upload_tryon_result = AsyncMock(return_value="stored-result")
        storage.refresh_tryon_url.return_value = "refreshed-result"
        firestore = MagicMock()
        firestore.get_cached_tryon = AsyncMock(side_effect=lambda key: cache.get(key))
        firestore.save_tryon_cache = AsyncMock(side_effect=save)
        vertex = MagicMock()
        vertex.virtual_try_on_multiple = AsyncMock(return_value=b"render")
        with patch.object(tryon, "storage", storage), patch.object(
            tryon, "firestore", firestore
        ), patch.object(tryon, "vertex_ai", vertex):
            first = await tryon.try_on_multiple(request, {"uid": "alice"})
            repeat = await tryon.try_on_multiple(request, {"uid": "alice"})
            self.assertFalse(first["cached"])
            self.assertTrue(repeat["cached"])
            self.assertEqual(repeat["result_url"], "refreshed-result")
            self.assertEqual(vertex.virtual_try_on_multiple.await_count, 1)
            avatar[0] = b"replacement avatar"
            changed = await tryon.try_on_multiple(request, {"uid": "alice"})
            self.assertFalse(changed["cached"])
            self.assertEqual(vertex.virtual_try_on_multiple.await_count, 2)
            calls = storage.upload_tryon_result.await_args_list
            self.assertEqual(calls[1].kwargs["garment_ids"], ["a"])
            self.assertNotEqual(
                calls[0].kwargs["avatar_revision"], calls[1].kwargs["avatar_revision"]
            )

    async def test_history_pagination_reaches_older_results_and_validates_bounds(self):
        from app.routers import tryon

        app = FastAPI()
        app.include_router(tryon.router)
        app.dependency_overrides[get_current_user] = lambda: {"uid": "alice"}
        rows = [{"id": str(i)} for i in range(53)]

        async def listing(user_id, limit):
            self.assertEqual(user_id, "alice")
            return rows[:limit]

        with patch.object(
            tryon.storage, "list_tryon_results", AsyncMock(side_effect=listing)
        ):
            client = TestClient(app)
            first = client.get("/try-on/history").json()
            second = client.get("/try-on/history?offset=50").json()
            self.assertEqual(first["next_offset"], 50)
            self.assertEqual(first["results"] + second["results"], rows)
            self.assertIsNone(second["next_offset"])
            self.assertEqual(client.get("/try-on/history?offset=-1").status_code, 422)
