from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, patch

from app.models.garment import GarmentMetadata
from app.models.user_profile import UserProfile
from app.services.magazine_feed_service import MagazineFeedService


class MagazineFreshnessTests(unittest.IsolatedAsyncioTestCase):
    async def test_daily_edition_refresh_keeps_logical_identity_and_user_isolation(self):
        service = MagazineFeedService()
        service.firestore.ensure_user_profile = AsyncMock(return_value=UserProfile())
        service.firestore.list_garments_metadata = AsyncMock(side_effect=lambda user_id, **kwargs: [
            GarmentMetadata(garment_id='top', user_id=user_id, category='top'),
            GarmentMetadata(garment_id='bottom', user_id=user_id, category='bottom'),
        ])
        with patch('app.services.magazine_feed_service.datetime', wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 9, 12, 23, 59, tzinfo=timezone.utc)
            first = await service.generate_magazine_feed('alice')
            self.assertEqual(first.date, '2026-09-12')
            clock.now.return_value = datetime(2026, 9, 13, tzinfo=timezone.utc)
            second = await service.generate_magazine_feed('alice')
            self.assertEqual(second.date, '2026-09-13')
            self.assertEqual(second.cover_look.id, first.cover_look.id)
            forced = await service.generate_magazine_feed('alice', force_regenerate=True)
            self.assertEqual(forced.date, second.date)
            self.assertEqual(forced.cover_look.id, second.cover_look.id)
            bob = await service.generate_magazine_feed('bob')
            self.assertNotEqual(bob.cover_look.id, first.cover_look.id)
            clock.now.assert_called_with(timezone.utc)
