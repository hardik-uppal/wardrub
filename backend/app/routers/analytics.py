"""Privacy-conscious first-party product analytics."""

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.product_events import emit_event
from app.services.auth import get_current_user

router = APIRouter()

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
    emit_event(event.name, user["uid"], garment_count=event.properties.get("garment_count"))
    return {"status": "accepted"}
