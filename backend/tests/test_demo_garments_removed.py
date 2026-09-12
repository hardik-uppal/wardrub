import inspect
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.models.garment import GarmentMetadata
from app.models.user_profile import UserProfile
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

    async def test_retired_demo_never_enters_grounded_magazine(self):
        service = MagazineFeedService()
        service.firestore.ensure_user_profile = AsyncMock(return_value=UserProfile())
        service.firestore.list_garments_metadata = AsyncMock(return_value=[
            make_garment("mock-g1"),
            GarmentMetadata(garment_id="bottom", user_id="user-1", category="bottom"),
        ])
        result = await service.generate_magazine_feed("user-1")
        self.assertIsNone(result.cover_look)

    async def test_profileless_legacy_user_gets_neutral_small_wardrobe_feed(self):
        service = MagazineFeedService()
        service.firestore.ensure_user_profile = AsyncMock(return_value=UserProfile())
        service.firestore.list_garments_metadata = AsyncMock(return_value=[
            make_garment("top"),
            GarmentMetadata(garment_id="bottom", user_id="user-1", category="bottom"),
        ])
        result = await service.generate_magazine_feed("user-1")
        self.assertIsNotNone(result.cover_look)
        service.firestore.ensure_user_profile.assert_awaited_once_with("user-1")
        self.assertIsNone(result.weather)

    async def test_regenerate_empty_wardrobe_is_honest_success(self):
        service = MagazineFeedService()
        service.firestore.ensure_user_profile = AsyncMock(return_value=UserProfile())
        service.firestore.list_garments_metadata = AsyncMock(return_value=[])
        with patch.object(outfit_router, "magazine_service", service):
            result = await outfit_router.regenerate_magazine_feed_endpoint(user={"uid": "user-1"})
        self.assertEqual(result["status"], "success")
        self.assertIsNone(result["feed"]["cover_look"])


if __name__ == "__main__":
    unittest.main()
