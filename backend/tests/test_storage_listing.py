"""Listing must not download, transform or upload images to fill derivatives."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services import storage as module


class StorageListingTests(unittest.IsolatedAsyncioTestCase):
    async def test_cloud_wardrobe_uses_only_existing_derivatives(self):
        service = module.StorageService()
        service._client = Mock()
        service._bucket = Mock()
        names = [
            'users/alice/garments/top/old_front.png',
            'users/alice/garments/top/new_front.png',
            'users/alice/garments/top/new_front_thumb.webp',
            'users/alice/garments/top/new_back.png',
            'users/alice/garments/top/new_back_thumb.webp',
        ]
        service._client.list_blobs.return_value = [SimpleNamespace(name=n) for n in names]
        service._generate_signed_url = Mock(side_effect=lambda n: 'signed:' + n)
        service._backfill_gcs_thumbnail = Mock(side_effect=AssertionError('read performed backfill'))
        rows = {r['id']: r for r in await service.list_garments('alice', 'top')}
        self.assertIsNone(rows['old']['thumbnail_url'])
        self.assertEqual(rows['old']['front_url'], 'signed:' + names[0])
        self.assertEqual(rows['new']['thumbnail_url'], 'signed:' + names[2])
        self.assertEqual(rows['new']['back_thumbnail_url'], 'signed:' + names[4])
        service._client.list_blobs.assert_called_once_with(service._bucket, prefix='users/alice/garments/top/')
        service._bucket.blob.assert_not_called()
        service._backfill_gcs_thumbnail.assert_not_called()

    async def test_cloud_looks_keep_metadata_order_and_limit_without_backfill(self):
        service = module.StorageService()
        service._client = Mock()
        service._bucket = Mock()
        prefix = 'users/alice/tryon-results/'
        service._client.list_blobs.return_value = [
            SimpleNamespace(name=prefix + 'old.png', metadata={'created_at': '2026-01-01'}, time_created=None),
            SimpleNamespace(name=prefix + 'new.png', metadata={'created_at': '2026-02-01', 'favorite': 'true'}, time_created=None),
        ]
        service._generate_signed_url = Mock(side_effect=lambda n: 'signed:' + n)
        service._backfill_gcs_thumbnail = Mock(side_effect=AssertionError('read performed backfill'))
        rows = await service.list_tryon_results('alice', limit=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], 'new')
        self.assertTrue(rows[0]['favorite'])
        self.assertIsNone(rows[0]['thumbnail_url'])
        service._client.list_blobs.assert_called_once_with(service._bucket, prefix=prefix)
        service._backfill_gcs_thumbnail.assert_not_called()
        service._bucket.blob.assert_not_called()

    async def test_local_reads_are_non_mutating_and_user_scoped(self):
        files = {'users/alice/garments/top/a_front.png': b'image',
                 'users/alice/tryon-results/a.png': b'image',
                 'users/bob/garments/top/b_front.png': b'private'}
        urls = {}
        with (
            patch.object(module.StorageService, 'bucket', new_callable=PropertyMock, return_value=None),
            patch.object(module, '_memory_files', files),
            patch.object(module, '_memory_signed_urls', urls),
            patch.object(module.StorageService, '_create_thumbnail', side_effect=AssertionError('unexpected transform')),
        ):
            service = module.StorageService()
            wardrobe = await service.list_garments('alice')
            looks = await service.list_tryon_results('alice')
        self.assertEqual([g['id'] for g in wardrobe], ['a'])
        self.assertEqual([g['id'] for g in looks], ['a'])
        self.assertEqual(len(files), 3)
        self.assertEqual(urls, {})
        self.assertIsNone(wardrobe[0]['thumbnail_url'])
        self.assertIsNone(looks[0]['thumbnail_url'])
