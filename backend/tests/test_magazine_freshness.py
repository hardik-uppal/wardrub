from datetime import datetime, timezone
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.models.garment import GarmentMetadata
from app.models.user_profile import UserProfile
from app.services.magazine_feed_service import MagazineFeedService


class MagazineFreshnessTests(unittest.IsolatedAsyncioTestCase):
    async def test_unchanged_wardrobe_daily_cache_force_refresh_and_user_isolation(self):
        service = MagazineFeedService()
        cache = {}

        async def get_feed(uid, day):
            return cache.get((uid, day))

        async def save_feed(feed):
            cache[(feed.user_id, feed.date)] = feed
            return True

        service.firestore.get_magazine_feed = AsyncMock(side_effect=get_feed)
        service.firestore.save_magazine_feed = AsyncMock(side_effect=save_feed)
        service.firestore.ensure_user_profile = AsyncMock(return_value=UserProfile())
        service.firestore.list_garments_metadata = AsyncMock(side_effect=lambda user_id: [
            GarmentMetadata(garment_id=f'garment-{i}', user_id=user_id, category='top') for i in range(10)
        ])
        service.firestore.list_user_feedback = AsyncMock(return_value=[])
        service.scorer.generate_top_outfits = Mock(return_value=[SimpleNamespace(
            garment_ids=['garment-0', 'garment-1'], overall_score=0.9,
            items=[SimpleNamespace(description='top')],
        )])
        look = dict(title='Everyday layers', garment_ids=['garment-0', 'garment-1'],
                    hero_item_id='garment-0', why_it_works='Balanced essentials.', score=0.9)
        editorial = dict(cover_look=look, daily_fits=[], one_item_three_ways=[], underused_edit=look)
        generate = Mock(return_value=SimpleNamespace(candidates=[SimpleNamespace(
            content=SimpleNamespace(parts=[SimpleNamespace(text=json.dumps(editorial))]),
        )]))
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
        with patch.object(service, '_get_gemini_client', return_value=client), patch(
            'app.services.magazine_feed_service.datetime', wraps=datetime,
        ) as clock:
            clock.now.return_value = datetime(2026, 9, 12, 23, 59, tzinfo=timezone.utc)
            first = await service.generate_magazine_feed('alice')
            self.assertEqual(first.date, '2026-09-12')
            self.assertIs(await service.generate_magazine_feed('alice'), first)
            self.assertEqual(generate.call_count, 1)
            service.firestore.list_garments_metadata.assert_awaited_once_with(user_id='alice')

            # No garment writes or changes: the next UTC day selects a new cache key.
            clock.now.return_value = datetime(2026, 9, 13, tzinfo=timezone.utc)
            second = await service.generate_magazine_feed('alice')
            self.assertEqual(second.date, '2026-09-13')
            self.assertIsNot(second, first)
            self.assertEqual(generate.call_count, 2)
            self.assertEqual(second.cover_look.garment_ids, first.cover_look.garment_ids)
            self.assertNotEqual(second.cover_look.id, first.cover_look.id)

            forced = await service.generate_magazine_feed('alice', force_regenerate=True)
            self.assertIsNot(forced, second)
            self.assertEqual(forced.date, second.date)  # Calendar edition, not sequence counter.
            self.assertEqual(generate.call_count, 3)

            bob = await service.generate_magazine_feed('bob')
            self.assertEqual(bob.user_id, 'bob')
            self.assertEqual(generate.call_count, 4)
            self.assertIs(await service.generate_magazine_feed('alice'), forced)
            self.assertEqual(generate.call_count, 4)
            self.assertIs(cache[('alice', '2026-09-12')], first)
            clock.now.assert_called_with(timezone.utc)
