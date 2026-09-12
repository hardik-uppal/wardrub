import io
import json
import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import product_events
from app.routers.analytics import ActivationEvent, record_activation_event


class ProductEventsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setFormatter(product_events.EventFormatter())
        self.patch = patch.object(product_events.logger, "handlers", [self.handler])
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_json_event_uses_closed_schema(self):
        product_events.emit_event("profile_loaded", "test-uid")
        event = json.loads(self.stream.getvalue())
        self.assertEqual(event["user_id"], "test-uid")
        self.assertEqual(event["event_schema"], "wardrub_product_v1")
        self.assertEqual(set(event), {"event_schema", "event_name", "user_id", "event_time", "revision", "severity"})
        self.assertFalse(product_events.logger.propagate)

    async def test_client_cannot_inject_identifiers_or_sensitive_properties(self):
        await record_activation_event(ActivationEvent(name="avatar_created", properties={
            "user_id": "another-user", "url": "secret-image", "provider": "secret-token",
            "garment_count": 3,
        }), {"uid": "authenticated-user"})
        event = json.loads(self.stream.getvalue())
        self.assertEqual(event["user_id"], "authenticated-user")
        self.assertEqual(event["garment_count"], 3)
        self.assertNotIn("secret", self.stream.getvalue())
        self.assertNotIn("another-user", self.stream.getvalue())

    def test_invalid_count_not_logged(self):
        product_events.emit_event("first_garment_added", "test-uid", garment_count="private-text")
        self.assertNotIn("private-text", self.stream.getvalue())

    def test_arbitrary_events_are_rejected(self):
        with self.assertRaises(ValueError):
            product_events.emit_event("private-user-content", "test-uid")
        self.assertEqual(self.stream.getvalue(), "")

    def test_telemetry_failure_does_not_break_product(self):
        with patch.object(product_events.logger, "info", side_effect=RuntimeError("logging offline")):
            product_events.emit_event("magazine_requested", "test-uid")
