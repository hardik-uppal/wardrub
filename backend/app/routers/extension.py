"""Chrome extension router - bootstrap and extension-specific endpoints."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.logging_config import get_logger
from app.services.auth import get_current_user
from app.services.storage import StorageService

router = APIRouter()
storage = StorageService()
logger = get_logger("extension")


class ExtensionBootstrapUser(BaseModel):
    """Authenticated user info needed by the extension."""

    id: str
    email: Optional[str] = None


class ExtensionBootstrapResponse(BaseModel):
    """Bootstrap payload returned to initialize the extension UI."""

    user: ExtensionBootstrapUser
    avatar_url: Optional[str] = None
    has_avatar: bool


@router.get("/extension/bootstrap", response_model=ExtensionBootstrapResponse)
async def extension_bootstrap(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Bootstrap endpoint for the Chrome extension.

    Returns minimal authenticated user info plus avatar availability so the side panel
    can initialize in a single API call.
    """
    try:
        user_id = user["uid"]
        avatar_url = await storage.get_avatar(user_id=user_id)

        return ExtensionBootstrapResponse(
            user=ExtensionBootstrapUser(
                id=user_id,
                email=user.get("email"),
            ),
            avatar_url=avatar_url,
            has_avatar=bool(avatar_url),
        )
    except Exception as exc:
        logger.error("Failed to bootstrap extension", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to bootstrap extension: {exc}")
