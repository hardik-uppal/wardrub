"""Privacy-conscious first-party product analytics."""

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.logging_config import get_logger
from app.services.auth import get_current_user

router = APIRouter()
logger = get_logger("analytics")

ActivationEventName = Literal[
    "sign_in_completed",
    "avatar_created",
    "first_garment_added",
    "first_try_on_completed",
    "first_look_saved",
]


class ActivationEvent(BaseModel):
    name: ActivationEventName
    properties: Dict[str, Any] = Field(default_factory=dict)


@router.post("/analytics/events", status_code=202)
async def record_activation_event(
    event: ActivationEvent,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Emit a structured event to Cloud Logging without storing image URLs or tokens."""
    safe_properties = {
        key: value
        for key, value in event.properties.items()
        if key in {"provider", "category", "garment_count", "mode"}
        and isinstance(value, (str, int, float, bool))
    }
    logger.info(
        "activation_event",
        extra={
            "extra_data": {
                "event": event.name,
                "user_id": user["uid"],
                "properties": safe_properties,
            }
        },
    )
    return {"status": "accepted"}
