"""User profile router for analysis and management."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, Depends
from typing import List, Optional, Dict, Any, Literal
import asyncio

from app.services.firestore import FirestoreService
from app.services.color_analysis import ColorAnalysisService
from app.services.body_analysis import BodyAnalysisService
from app.services.style_analysis import (
    StyleAnalysisService, MAX_PHOTOS, MAX_PHOTO_BYTES, prepare_photo, select_stages,
)
from app.services.auth import get_current_user
from app.logging_config import get_logger
from app.models.user_profile import (
    UserProfile,
    UserProfileUpdate,
    Location,
)

router = APIRouter()
firestore = FirestoreService()
color_service = ColorAnalysisService()
body_service = BodyAnalysisService()
style_service = StyleAnalysisService()
logger = get_logger("profile")


@router.get("/profile")
async def get_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get the current user's profile.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        User profile with analysis data
    """
    try:
        user_id = user["uid"]
        profile = await firestore.get_user_profile(user_id)
        
        if not profile:
            return {
                "profile": None,
                "status": "not_created",
                "message": "Profile not created yet. Upload photos to analyze."
            }
        
        return {
            "profile": profile.model_dump(),
            "status": "exists"
        }
    except Exception as e:
        logger.error(f"Failed to get profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")


@router.post("/profile/analyze")
async def analyze_profile(
    files: List[UploadFile] = File(..., description="1–4 original face or full-length photos"),
    user: Dict[str, Any] = Depends(get_current_user),
    stage: Literal["auto", "color", "fit"] = Form("auto"),
):
    """Refine independent analysis stages without discarding existing results."""
    user_id = user["uid"]
    if not files or len(files) > MAX_PHOTOS:
        raise HTTPException(status_code=400, detail="Upload between 1 and 4 photos.")
    photos = []
    for file in files:
        raw = await file.read(MAX_PHOTO_BYTES + 1)
        if len(raw) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=413, detail="Each photo must be no larger than 10 MB.")
        try:
            photos.append(await asyncio.to_thread(prepare_photo, raw))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        existing = await firestore.get_user_profile(user_id) or UserProfile()
        stages = select_stages(existing, stage)
        failed = False
        try:
            evidence = await style_service.analyze(photos)
        except Exception:
            logger.warning("Style analysis provider failed", exc_info=True)
            evidence, failed = None, True
        profile = await firestore.apply_style_analysis(evidence, stages, user_id, failed=failed)
    except Exception as e:
        logger.error("Failed to persist style analysis", exc_info=True)
        raise HTTPException(status_code=503, detail="Could not save your analysis. Please retry.") from e

    # Return persisted stage failures as structured state so clients can offer retry.
    return {
        "profile": profile.model_dump(),
        "color_recommendations": color_service.get_color_recommendations(profile.skin_tone) if profile.skin_tone else None,
        "fit_recommendations": body_service.get_fit_recommendations(profile.body_type) if profile.body_type else None,
        "quality": {"images_analyzed": len(photos), **profile.analysis_quality.model_dump()},
        "status": "failed" if failed else "analyzed",
    }


@router.put("/profile")
async def update_profile(
    updates: UserProfileUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update user profile preferences.
    
    Args:
        updates: Profile fields to update
        user: Authenticated user from token
    
    Returns:
        Updated profile
    """
    try:
        user_id = user["uid"]
        update_dict = {}
        
        if updates.style_preferences is not None:
            update_dict["style_preferences"] = updates.style_preferences
        
        if updates.location is not None:
            update_dict["location"] = updates.location.model_dump()
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        success = await firestore.update_user_profile(update_dict, user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update profile")
        
        # Return updated profile
        profile = await firestore.get_user_profile(user_id)
        
        return {
            "profile": profile.model_dump() if profile else None,
            "status": "updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")


@router.put("/profile/location")
async def update_location(
    location: Location,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update user's location for weather-based recommendations.
    
    Args:
        location: Location with lat/lon coordinates
        user: Authenticated user from token
    
    Returns:
        Updated profile
    """
    try:
        user_id = user["uid"]
        success = await firestore.update_user_profile({
            "location": location.model_dump()
        }, user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update location")
        
        return {
            "location": location.model_dump(),
            "status": "updated"
        }
        
    except Exception as e:
        logger.error(f"Failed to update location: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update location: {str(e)}")


@router.delete("/profile")
async def delete_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Delete user profile.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        Confirmation of deletion
    """
    try:
        user_id = user["uid"]
        success = await firestore.delete_user_profile(user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete profile")
        
        return {"status": "deleted"}
        
    except Exception as e:
        logger.error(f"Failed to delete profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete profile: {str(e)}")


@router.get("/profile/color-recommendations")
async def get_color_recommendations(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get color recommendations based on user's skin tone.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        List of recommended and avoid colors
    """
    try:
        user_id = user["uid"]
        profile = await firestore.get_user_profile(user_id)
        
        if not profile or not profile.skin_tone:
            raise HTTPException(
                status_code=400,
                detail="Profile not analyzed yet. Upload photos first."
            )
        
        recommendations = color_service.get_color_recommendations(profile.skin_tone)
        
        return {
            "season": profile.skin_tone.season,
            "recommendations": recommendations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get color recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/fit-recommendations")
async def get_fit_recommendations(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get fit recommendations based on user's body type.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        Fit recommendations by garment category
    """
    try:
        user_id = user["uid"]
        profile = await firestore.get_user_profile(user_id)
        
        if not profile or not profile.body_type:
            raise HTTPException(
                status_code=400,
                detail="Profile not analyzed yet. Upload photos first."
            )
        
        recommendations = body_service.get_fit_recommendations(profile.body_type)
        
        return {
            "body_type": profile.body_type,
            "recommendations": recommendations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get fit recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# Data Migration Endpoints
# =========================================================================

@router.get("/check-legacy-data")
async def check_legacy_data(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Check if there's any legacy data that can be migrated.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        Whether legacy data exists
    """
    try:
        # Check for legacy data in both storage and Firestore
        has_storage_legacy = await storage.has_legacy_data()
        has_firestore_legacy = await firestore.has_legacy_data()
        
        return {
            "has_legacy_data": has_storage_legacy or has_firestore_legacy,
            "storage_legacy": has_storage_legacy,
            "firestore_legacy": has_firestore_legacy
        }
        
    except Exception as e:
        logger.error(f"Failed to check legacy data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrate-legacy-data")
async def migrate_legacy_data(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Migrate all legacy data to the authenticated user's namespace.
    
    This is a one-time migration that moves:
    - Avatar from avatars/current.png to users/{user_id}/avatar.png
    - Garments from garments/ to users/{user_id}/garments/
    - Try-on results from tryon-results/ to users/{user_id}/tryon-results/
    - Profile from default_user to the user's profile
    - Garment metadata to include user_id
    
    Args:
        user: Authenticated user from token
    
    Returns:
        Migration summary with counts
    """
    user_id = user["uid"]
    logger.info(f"Starting legacy data migration for user: {user_id}")
    
    try:
        # Migrate storage data
        storage_summary = await storage.migrate_legacy_data(user_id)
        
        # Migrate Firestore data
        firestore_summary = await firestore.migrate_legacy_firestore_data(user_id)
        
        total_summary = {
            "status": "completed",
            "user_id": user_id,
            "storage": storage_summary,
            "firestore": firestore_summary,
            "total_items_migrated": (
                (1 if storage_summary.get("avatar_migrated") else 0) +
                storage_summary.get("garments_migrated", 0) +
                storage_summary.get("tryon_results_migrated", 0) +
                (1 if firestore_summary.get("profile_migrated") else 0) +
                firestore_summary.get("garments_migrated", 0) +
                firestore_summary.get("daily_looks_migrated", 0)
            )
        }
        
        logger.info(f"Migration completed: {total_summary}")
        return total_summary
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
