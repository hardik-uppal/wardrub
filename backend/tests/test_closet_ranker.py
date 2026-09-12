import unittest
import sys
from pathlib import Path

# Match the repository CI invocation from the root, without PYTHONPATH setup.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.garment import GarmentMetadata
from app.models.outfit import WeatherInfo
from app.models.user_profile import UserProfile
from app.services.closet_ranker import ClosetRanker, eligible, outfit_key, valid_outfit
from app.services.magazine_feed_service import MagazineFeedService
from app.services import firestore as db
from app.services.weather import WeatherService
from app.routers import outfit as routes
from app.services.auth import get_current_user


def garment(gid, category='top', **kwargs):
    return GarmentMetadata(garment_id=gid, user_id=kwargs.pop('user_id', 'u'), category=category, **kwargs)


class RankerTests(unittest.TestCase):
    def setUp(self):
        self.ranker = ClosetRanker()
        self.clothes = [garment('a'), garment('b', 'bottom'), garment('c')]

    def test_small_wardrobe_needs_roles_not_count_or_profile(self):
        self.assertTrue(self.ranker.rank(self.clothes[:2], 'u'))
        self.assertTrue(self.ranker.rank([garment('dress', 'dress')], 'u'))
        self.assertEqual(self.ranker.rank([garment(str(i)) for i in range(20)], 'u'), [])

    def test_excludes_foreign_lent_retired_demo_and_laundry(self):
        extras = [garment('foreign', user_id='other'), garment('lent', ownership='lent'),
                  garment('retired', ownership='retired'), garment('mock-demo'), garment('wash', readiness='laundry')]
        for outfit in self.ranker.rank(self.clothes + extras, 'u', limit=20):
            self.assertTrue(valid_outfit(outfit))
            self.assertTrue(all(eligible(g, 'u') for g in outfit))
        self.assertEqual(self.ranker.rank([garment('wash', readiness='laundry'), self.clothes[1]], 'u'), [])

    def test_identity_and_order_stable_across_reads_days_and_users(self):
        first = self.ranker.rank(self.clothes, 'u')
        second = self.ranker.rank(list(reversed(self.clothes)), 'u')
        self.assertEqual([[g.garment_id for g in o] for o in first], [[g.garment_id for g in o] for o in second])
        self.assertEqual(outfit_key('u', self.clothes[:2]), outfit_key('u', list(reversed(self.clothes[:2]))))
        self.assertNotEqual(outfit_key('u', self.clothes[:2]), outfit_key('other', self.clothes[:2]))

    def test_swap_preserves_all_other_pieces_and_changes_identity(self):
        original = self.clothes[:2] + [garment('jacket', 'outerwear'), garment('shoes', 'shoes')]
        result = self.ranker.swap(original + [self.clothes[2]], 'u', [g.garment_id for g in original], 'a')
        self.assertEqual({g.garment_id for g in result}, {'c', 'b', 'jacket', 'shoes'})
        self.assertNotEqual(outfit_key('u', result), outfit_key('u', original))

    def test_swap_can_replace_laundry_but_not_preserve_it(self):
        self.clothes[0].readiness = 'laundry'
        self.assertIsNotNone(self.ranker.swap(self.clothes, 'u', ['a', 'b'], 'a'))
        with self.assertRaises(ValueError):
            self.ranker.swap(self.clothes, 'u', ['a', 'b'], 'b')

    def test_no_alternative_never_changes_another_role(self):
        self.assertIsNone(self.ranker.swap(self.clothes[:2], 'u', ['a', 'b'], 'a'))
        self.assertIsNone(self.ranker.swap(self.clothes, 'u', ['a', 'b'], 'a', 'b'))
        with self.assertRaises(ValueError):
            self.ranker.swap(self.clothes, 'u', ['a', 'a'], 'a')
        with self.assertRaises(ValueError):
            self.ranker.swap(self.clothes, 'u', ['not-owned', 'b'], 'not-owned')

    def test_weather_shortlist_is_not_first_five_uploaded_items(self):
        clothes = [garment(f'warm-{i}', weather_range={'min_temp': -10, 'max_temp': 15}) for i in range(30)]
        clothes += [garment('light', weather_range={'min_temp': 20, 'max_temp': 40}), garment('b', 'bottom')]
        first = self.ranker.rank(clothes, 'u', weather={'temperature': 33})[0]
        self.assertIn('light', {g.garment_id for g in first})


class FoundationServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = MagazineFeedService()
        self.service.firestore.ensure_user_profile = AsyncMock(return_value=UserProfile())
        self.clothes = [garment('a'), garment('b', 'bottom')]
        self.service.firestore.list_garments_metadata = AsyncMock(side_effect=lambda **kw: list(self.clothes))
        self.service.firestore.get_magazine_feed = AsyncMock(side_effect=AssertionError('Old editorial cache must not be read'))

    async def test_unknown_weather_and_readiness_are_explicit(self):
        feed = await self.service.generate_magazine_feed('u')
        self.assertIsNone(feed.weather)
        self.assertEqual(feed.weather_status, 'no_location')
        self.assertEqual(set(feed.cover_look.unknown_readiness_ids), {'a', 'b'})
        self.assertIn('unknown', feed.cover_look.why_it_works)
        self.assertIsNone(feed.underused_edit)

    async def test_same_day_laundry_and_return_recheck_eligibility(self):
        first = await self.service.generate_magazine_feed('u')
        self.clothes[0].readiness = 'laundry'
        second = await self.service.generate_magazine_feed('u')
        self.assertIsNone(second.cover_look)
        self.assertNotEqual(first.wardrobe_version, second.wardrobe_version)
        self.clothes[0].readiness = 'ready'
        returned = await self.service.generate_magazine_feed('u')
        self.assertEqual(first.cover_look.id, returned.cover_look.id)

    async def test_weather_provider_failure_does_not_invent_mild_weather(self):
        self.service.firestore.ensure_user_profile.return_value = UserProfile(location={'lat': 1, 'lon': 2})
        self.service.weather_service.get_cached_weather_by_coords = AsyncMock(return_value=None)
        feed = await self.service.generate_magazine_feed('u')
        self.assertEqual(feed.weather_status, 'unavailable')
        self.assertIsNone(feed.weather)
        self.assertIsNotNone(feed.cover_look)

    async def test_cloud_read_failure_propagates_instead_of_stale_recommendations(self):
        self.service.firestore.list_garments_metadata.side_effect = RuntimeError('offline')
        with self.assertRaises(RuntimeError):
            await self.service.generate_magazine_feed('u')

    async def test_weather_cache_ttl_and_location_change(self):
        weather = WeatherService()
        observation = WeatherInfo(temperature=22, feels_like=21, condition='clear')
        weather.get_weather_by_coords = AsyncMock(return_value=observation)
        with patch('app.services.weather.time.monotonic', return_value=0):
            await weather.get_cached_weather_by_coords(1, 2)
            await weather.get_cached_weather_by_coords(1, 2)
            self.assertEqual(weather.get_weather_by_coords.await_count, 1)
            await weather.get_cached_weather_by_coords(3, 4)
            self.assertEqual(weather.get_weather_by_coords.await_count, 2)
        with patch('app.services.weather.time.monotonic', return_value=601):
            await weather.get_cached_weather_by_coords(1, 2)
            self.assertEqual(weather.get_weather_by_coords.await_count, 3)
        with self.assertRaises(ValueError):
            weather._parse_weather_response({'main': {}, 'weather': [{'id': 800}]})


class ReadinessStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_replay_undo_conflict_and_user_isolation(self):
        service = db.FirestoreService()
        service._use_memory = True
        records = {'a': garment('a').model_dump()}
        with patch.object(db, '_memory_garments', records), patch.object(db.settings, 'ALLOW_DEV_AUTH_BYPASS', True):
            first = await service.set_garment_readiness('u', 'a', 'laundry', 0)
            replay = await service.set_garment_readiness('u', 'a', 'laundry', 0)
            self.assertEqual(first.readiness_version, replay.readiness_version)
            undo = await service.set_garment_readiness('u', 'a', 'unknown', 1)
            self.assertEqual(undo.readiness, 'unknown')
            self.assertEqual(undo.readiness_version, 2)
            with self.assertRaises(ValueError):
                await service.set_garment_readiness('u', 'a', 'ready', 0)
            with self.assertRaises(LookupError):
                await service.set_garment_readiness('another', 'a', 'ready', 2)

    async def test_cloud_transaction_changes_only_readiness_fields(self):
        service = db.FirestoreService()
        service._client = Mock()
        ref = service._client.collection.return_value.document.return_value
        ref.get.return_value.exists = True
        ref.get.return_value.to_dict.return_value = garment('a').model_dump()
        transaction = service._client.transaction.return_value
        with patch('google.cloud.firestore.transactional', lambda fn: fn):
            result = await service.set_garment_readiness('u', 'a', 'laundry', 0)
        ref.get.assert_called_once_with(transaction=transaction)
        self.assertEqual(set(transaction.update.call_args.args[1]), {'readiness', 'readiness_version', 'updated_at'})
        self.assertEqual(result.readiness_version, 1)

    async def test_metadata_analysis_save_preserves_readiness(self):
        service = db.FirestoreService()
        service._use_memory = True
        current = garment('a', readiness='laundry', readiness_version=5)
        with patch.object(db, '_memory_garments', {'a': current.model_dump()}):
            await service.save_garment_metadata(garment('a'))
            record = db._memory_garments['a']
            self.assertEqual(record['readiness'], 'laundry')
            self.assertEqual(record['readiness_version'], 5)

    async def test_production_unavailable_storage_fails_closed(self):
        service = db.FirestoreService()
        service._use_memory = True
        with patch.object(db.settings, 'ALLOW_DEV_AUTH_BYPASS', False):
            with self.assertRaises(RuntimeError):
                await service.set_garment_readiness('u', 'a', 'ready', 0)
            with self.assertRaises(RuntimeError):
                await service.list_garments_metadata('u', strict=True)

    async def test_memory_limit_is_applied_after_user_filter(self):
        service = db.FirestoreService()
        service._use_memory = True
        with patch.object(db, '_memory_garments', {'x': garment('x', user_id='other').model_dump(), 'a': garment('a').model_dump()}):
            result = await service.list_garments_metadata('u', limit=1)
            self.assertEqual([g.garment_id for g in result], ['a'])


class RouteTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(routes.router, prefix='/api')
        app.dependency_overrides[get_current_user] = lambda: {'uid': 'u'}
        self.client = TestClient(app)

    def test_swap_validation_and_no_alternative(self):
        self.assertEqual(self.client.post('/api/outfits/swap', json={'garment_ids': []}).status_code, 422)
        with patch.object(routes.magazine_service, 'swap', AsyncMock(return_value=None)):
            response = self.client.post('/api/outfits/swap', json={'garment_ids': ['a', 'b'], 'replace_item_id': 'a'})
            self.assertEqual(response.json()['status'], 'no_alternative')
        with patch.object(routes.magazine_service, 'swap', AsyncMock(side_effect=ValueError('unavailable'))):
            self.assertEqual(self.client.post('/api/outfits/swap', json={'garment_ids': ['a', 'b'], 'replace_item_id': 'a'}).status_code, 409)

    def test_readiness_ownership_validation_and_failed_write(self):
        payload = {'readiness': 'ready', 'expected_version': 0}
        with patch.object(routes.firestore, 'set_garment_readiness', AsyncMock(side_effect=LookupError())):
            self.assertEqual(self.client.put('/api/closet-state/a', json=payload).status_code, 404)
        with patch.object(routes.firestore, 'set_garment_readiness', AsyncMock(side_effect=RuntimeError())):
            self.assertEqual(self.client.put('/api/closet-state/a', json=payload).status_code, 503)
        self.assertEqual(self.client.put('/api/closet-state/a', json={**payload, 'readiness': 'dirty'}).status_code, 422)

    def test_core_mutation_routes_require_auth(self):
        app = FastAPI()
        app.include_router(routes.router, prefix='/api')
        # Auth dependency is present; no bypass override on this app.
        for path in ('/api/outfits/swap', '/api/closet-state', '/api/closet-state/{garment_id}'):
            route = next(r for r in app.routes if r.path == path)
            self.assertIn(get_current_user, [d.call for d in route.dependant.dependencies])
