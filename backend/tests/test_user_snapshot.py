import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'infra/observability'))
from user_snapshot import summarize


class UserSnapshotTests(unittest.TestCase):
    def test_inventory_is_aggregate_and_disabled_users_not_in_readiness(self):
        users = [{'localId': 'alice', 'email': 'private@example.com', 'createdAt': '1768290347440'},
                 {'localId': 'bob', 'disabled': True}]
        collections = {'garments': {str(i): {'user_id': 'alice'} for i in range(10)},
                       'user_profiles': {'alice': {'style_analysis': {'color': {'status': 'ready'}}}},
                       'magazine_feeds': {}}
        collections['garments']['mock-g1'] = {'user_id': 'alice'}
        result = summarize(users, collections, ['users/alice/avatar.png', 'users/bob/avatar.png'])
        c = result['counts']
        self.assertEqual(c['total_registered'], 2)
        self.assertEqual(c['disabled_accounts'], 1)
        self.assertEqual(c['with_avatar'], 1)
        self.assertEqual(c['with_ten_garments'], 1)
        self.assertEqual(c['ten_garments_without_saved_magazine'], 1)
        self.assertEqual(c['ten_garments_without_profile'], 0)
        self.assertEqual(c['color_ready'], 1)
        self.assertNotIn('alice', str(result))
        self.assertNotIn('private@example.com', str(result))

    def test_empty_inventory_is_valid_snapshot(self):
        r = summarize([], {'garments': {}, 'user_profiles': {}, 'magazine_feeds': {}}, [])
        self.assertTrue(all(v == 0 for v in r['counts'].values()))
        self.assertEqual(r['signup_days'], {})
