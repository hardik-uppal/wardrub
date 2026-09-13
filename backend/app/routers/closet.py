"""Additive APIs for saved combinations, daily intent and explicit preferences."""

from datetime import date
from typing import Literal, Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.services.auth import get_current_user
from app.services.closet_library import ClosetLibrary

router = APIRouter()
library = ClosetLibrary()


class ClosetAction(BaseModel):
    action: Literal[
        "save",
        "delete",
        "plan",
        "wore",
        "unwear",
        "unplan",
        "location",
        "styles",
        "feedback",
        "undo_feedback",
    ]
    operation_id: str = Field(pattern=r"^[a-zA-Z0-9-]{8,80}$")
    expected_version: int = Field(ge=0)
    garment_ids: list[
        Annotated[str, Field(min_length=1, max_length=150, pattern=r"^[^/]+$")]
    ] = Field(default_factory=list, max_length=50)
    outfit_id: str = Field(default="", max_length=100)
    title: str = Field(default="", max_length=100)
    reason: Literal["not_today", "occasion", "comfort", "style"] = "not_today"
    policy_version: str = Field(default="unknown", max_length=80)
    day: date | None = None
    location: str = Field(default="", max_length=80)
    styles: list[
        Literal[
            "casual",
            "minimalist",
            "classic",
            "sporty",
            "formal",
            "streetwear",
            "bohemian",
        ]
    ] = Field(default_factory=list, max_length=7)


def public(state):
    return {key: value for key, value in state.items() if key != "operations"}


@router.get("/closet-library")
async def get_library(user=Depends(get_current_user)):
    try:
        return public(await library.read(user["uid"]))
    except Exception:
        raise HTTPException(503, "Could not read your saved outfits. Please retry.")


@router.post("/closet-library/actions")
async def act(request: ClosetAction, user=Depends(get_current_user)):
    try:
        return public(await library.mutate(user["uid"], request))
    except LookupError as error:
        raise HTTPException(404, str(error))
    except ValueError as error:
        raise HTTPException(409, str(error))
    except Exception:
        raise HTTPException(
            503, "This change was not confirmed. Refresh before retrying."
        )


class ReadinessChange(BaseModel):
    id: str = Field(min_length=1, max_length=150, pattern=r"^[^/]+$")
    readiness: Literal["ready", "unknown", "laundry"]
    expected_version: int = Field(ge=0)


class ReadinessBatch(BaseModel):
    changes: list[ReadinessChange] = Field(min_length=1, max_length=50)


@router.post("/closet-state/batch")
async def readiness_batch(request: ReadinessBatch, user=Depends(get_current_user)):
    try:
        items = await library.firestore.set_readiness_batch(
            user["uid"], request.changes
        )
        return {
            "garments": [
                {
                    "id": g.garment_id,
                    "readiness": g.readiness,
                    "version": g.readiness_version,
                }
                for g in items
            ]
        }
    except LookupError as error:
        raise HTTPException(404, str(error))
    except ValueError as error:
        raise HTTPException(409, str(error))
    except Exception:
        raise HTTPException(
            503, "Laundry changes were not confirmed. Refresh before retrying."
        )
