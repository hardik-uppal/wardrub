"""Allowlisted product telemetry; separate from potentially sensitive app logs."""
import json
import logging
import os
import sys
from datetime import datetime, timezone

EVENTS = {
    "sign_in_completed", "avatar_created", "first_garment_added",
    "first_try_on_completed", "first_look_saved", "profile_loaded",
    "magazine_requested", "magazine_generated", "magazine_cache_hit",
    "magazine_failed", "magazine_onboarding",
}


class EventFormatter(logging.Formatter):
    def format(self, record):
        # Deliberately do not include messages, exceptions or arbitrary extras.
        return json.dumps(record.product_event)


logger = logging.getLogger("wardrub_product_events")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(EventFormatter())
    logger.addHandler(handler)


def emit_event(name: str, user_id: str, *, garment_count=None):
    """Best-effort telemetry must never block the product journey."""
    if name not in EVENTS:
        raise ValueError("Unknown product event")
    event = {
        "event_schema": "wardrub_product_v1",
        "event_name": name,
        "user_id": user_id,
        "event_time": datetime.now(timezone.utc).isoformat(),
        "revision": os.environ.get("K_REVISION", "local"),
        "severity": "INFO",
    }
    if isinstance(garment_count, int) and not isinstance(garment_count, bool) and garment_count >= 0:
        event["garment_count"] = garment_count
    try:
        logger.info("product_event", extra={"product_event": event})
    except Exception:
        pass
