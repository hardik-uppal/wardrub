import inspect
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.models.garment import GarmentMetadata
from app.routers import garment as garment_router
from app.routers import outfit as outfit_router
from app.services import firestore as firestore_module
from app.services.magazine_feed_service import MagazineFeedService


def make_garment(garment_id: str, user_id: str = "user-1") -> GarmentMetadata:
    return GarmentMetadata(
        garment_id=garment_id,
        user_id=user_id,
        category="top",
    )


class DemoGarmentRemovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_wardrobe_returns_only_uploaded_garments(self):
        uploaded = {
            "id": "garment-1",
            "url": "https://example.com/garment-1.png",
            "category": "top",
        }
        retired_demo = {
            "id": "mock-g1",
            "url": "https://example.com/demo.png",
            "category": "outerwear",
        }

        with patch.object(
            garment_router.storage,
            "list_garments",
            AsyncMock(return_value=[uploaded, retired_demo]),
        ):
            result = await garment_router.get_wardrobe(
                category=None,
                user={"uid": "hardik-user", "email": "hardikuppal.hu@gmail.com"},
            )

        self.assertEqual(result, {"garments": [uploaded]})

    async def test_empty_wardrobe_stays_empty_for_former_dev_account(self):
        list_garments = AsyncMock(return_value=[])

        with patch.object(garment_router.storage, "list_garments", list_garments):
            first = await garment_router.get_wardrobe(
                category=None,
                user={"uid": "hardik-user", "email": "hardikuppal.hu@gmail.com"},
            )
            second = await garment_router.get_wardrobe(
                category=None,
                user={"uid": "hardik-user", "email": "hardikuppal.hu@gmail.com"},
            )

        self.assertEqual(first, {"garments": []})
        self.assertEqual(second, {"garments": []})
        self.assertEqual(list_garments.await_count, 2)

    async def test_firestore_quarantines_legacy_demo_records(self):
        service = firestore_module.FirestoreService()
        service._use_memory = True
        records = {
            "mock-g1": make_garment("mock-g1").model_dump(),
            "garment-1": make_garment("garment-1").model_dump(),
        }

        with patch.object(firestore_module, "_memory_garments", records):
            garments = await service.list_garments_metadata(user_id="user-1")
            blocked_save = await service.save_garment_metadata(make_garment("mock-g2"))

        self.assertEqual([garment.garment_id for garment in garments], ["garment-1"])
        self.assertFalse(blocked_save)
        self.assertNotIn("mock-g2", records)

    async def test_underfilled_magazine_uses_real_onboarding_for_every_user(self):
        list_metadata = AsyncMock(return_value=[make_garment(f"garment-{i}") for i in range(3)])
        generate_feed = AsyncMock()

        with (
            patch.object(outfit_router.firestore, "list_garments_metadata", list_metadata),
            patch.object(outfit_router.magazine_service, "generate_magazine_feed", generate_feed),
        ):
            result = await outfit_router.get_magazine_feed_endpoint(
                user={"uid": "hardik-user", "email": "hardikuppal.hu@gmail.com"},
            )

        self.assertEqual(result["status"], "onboarding")
        self.assertEqual(result["count"], 3)
        generate_feed.assert_not_awaited()

    async def test_full_magazine_uses_real_generation_for_former_dev_account(self):
        list_metadata = AsyncMock(return_value=[make_garment(f"garment-{i}") for i in range(10)])
        feed = SimpleNamespace(model_dump=lambda: {"user_id": "hardik-user"})
        generate_feed = AsyncMock(return_value=feed)

        with (
            patch.object(outfit_router.firestore, "list_garments_metadata", list_metadata),
            patch.object(outfit_router.magazine_service, "generate_magazine_feed", generate_feed),
        ):
            result = await outfit_router.get_magazine_feed_endpoint(
                user={"uid": "hardik-user", "email": "hardikuppal.hu@gmail.com"},
            )

        self.assertEqual(result["status"], "success")
        generate_feed.assert_awaited_once_with("hardik-user")

    async def test_cached_demo_magazine_is_ignored_after_restart(self):
        demo_look = SimpleNamespace(
            garment_ids=["mock-g1"],
            hero_item_id="mock-g1",
            swaps=[],
        )
        cached_demo_feed = SimpleNamespace(
            cover_look=demo_look,
            daily_fits=[],
            one_item_three_ways=[],
            underused_edit=demo_look,
        )
        service = MagazineFeedService()
        service.firestore.get_magazine_feed = AsyncMock(return_value=cached_demo_feed)
        service.firestore.get_user_profile = AsyncMock(return_value=None)

        result = await service.generate_magazine_feed("user-1")

        self.assertIsNone(result)
        service.firestore.get_user_profile.assert_awaited_once_with("user-1")

    async def test_regenerate_rejects_underfilled_real_wardrobe(self):
        with patch.object(
            outfit_router.firestore,
            "list_garments_metadata",
            AsyncMock(return_value=[]),
        ):
            with self.assertRaises(HTTPException) as raised:
                await outfit_router.regenerate_magazine_feed_endpoint(
                    user={"uid": "hardik-user", "email": "hardikuppal.hu@gmail.com"},
                )

        self.assertEqual(raised.exception.status_code, 400)
        self.assertNotIn(
            "mock",
            inspect.signature(outfit_router.regenerate_magazine_feed_endpoint).parameters,
        )


if __name__ == "__main__":
    unittest.main()
