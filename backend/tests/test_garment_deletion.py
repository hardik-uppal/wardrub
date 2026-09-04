import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.routers import garment as garment_router


class GarmentDeletionRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_metadata_failure_returns_500_instead_of_success(self):
        get_metadata = AsyncMock(return_value=SimpleNamespace(user_id="user-1"))
        delete_metadata = AsyncMock(return_value=False)
        delete_files = AsyncMock()

        with (
            patch.object(
                garment_router.firestore,
                "get_garment_metadata",
                get_metadata,
            ),
            patch.object(
                garment_router.firestore,
                "delete_garment_metadata",
                delete_metadata,
            ),
            patch.object(garment_router.storage, "delete_garment", delete_files),
        ):
            with self.assertRaises(HTTPException) as raised:
                await garment_router.delete_garment(
                    garment_id="garment-1",
                    user={"uid": "user-1"},
                )

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(raised.exception.detail, "Failed to delete garment metadata")
        delete_files.assert_awaited_once_with(
            garment_id="garment-1",
            user_id="user-1",
        )
        delete_metadata.assert_awaited_once_with("garment-1")

    async def test_success_preserves_existing_response(self):
        events = []

        async def delete_metadata(garment_id):
            events.append(("metadata", garment_id))
            return True

        async def delete_files(*, garment_id, user_id):
            events.append(("files", garment_id, user_id))

        with (
            patch.object(
                garment_router.firestore,
                "get_garment_metadata",
                AsyncMock(return_value=SimpleNamespace(user_id="user-1")),
            ),
            patch.object(
                garment_router.firestore,
                "delete_garment_metadata",
                side_effect=delete_metadata,
            ),
            patch.object(
                garment_router.storage,
                "delete_garment",
                side_effect=delete_files,
            ),
        ):
            result = await garment_router.delete_garment(
                garment_id="garment-1",
                user={"uid": "user-1"},
            )

        self.assertEqual(result, {"status": "deleted", "id": "garment-1"})
        self.assertEqual(
            events,
            [
                ("files", "garment-1", "user-1"),
                ("metadata", "garment-1"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
