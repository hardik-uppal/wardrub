import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.dev_auth import decode_dev_auth_token


class DevAuthTests(unittest.TestCase):
    def test_bypass_is_rejected_by_default(self):
        self.assertIsNone(
            decode_dev_auth_token("dev-mock-admin-token", enabled=False)
        )
        self.assertIsNone(
            decode_dev_auth_token("mock-token-reviewer", enabled=False)
        )

    def test_bypass_requires_explicit_enablement(self):
        user = decode_dev_auth_token("mock-token-reviewer", enabled=True)

        self.assertIsNotNone(user)
        self.assertEqual(user["uid"], "reviewer")


if __name__ == "__main__":
    unittest.main()
