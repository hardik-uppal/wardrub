"""Virtual try-on router - combines avatar with garments using Vertex AI."""

import hashlib
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.storage import StorageService
from app.services.vertex_ai import VertexAIService
from app.services.firestore import FirestoreService
from app.services.auth import get_current_user

router = APIRouter()
storage = StorageService()
vertex_ai = VertexAIService()
firestore = FirestoreService()


class TryOnRequest(BaseModel):
    """Request model for try-on endpoint."""
    avatar_url: str
    garment_url: str
    category: str  # top, bottom, dress, outerwear


class GarmentItem(BaseModel):
    """Individual garment for multi-try-on."""
    id: Optional[str] = None
    url: str
    category: str  # top, bottom, dress, outerwear


class MultiTryOnRequest(BaseModel):
    """Request model for multi-garment try-on endpoint."""
    avatar_url: str
    garments: List[GarmentItem]


class LookMetadataRequest(BaseModel):
    """User-editable metadata for a saved look."""
    favorite: Optional[bool] = None
    occasion: Optional[str] = None


def calculate_tryon_cache_key(avatar_url: str, garment_urls: List[str]) -> str:
    """Sort garment URLs and generate a SHA-256 hash for deterministic cache keys."""
    sorted_urls = sorted(garment_urls)
    combination_str = f"{avatar_url}|" + "|".join(sorted_urls)
    return hashlib.sha256(combination_str.encode('utf-8')).hexdigest()


@router.post("/try-on")
async def try_on(
    request: TryOnRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate a virtual try-on image combining avatar with garment.
    
    Args:
        request: TryOnRequest with avatar_url, garment_url, and category
        user: Authenticated user from token
    
    Returns:
        URL of the generated try-on result
    """
    user_id = user["uid"]
    
    if request.category not in ["top", "bottom", "dress", "outerwear"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid category. Must be: top, bottom, dress, outerwear"
        )
    
    try:
        # Check cache first
        cache_key = calculate_tryon_cache_key(request.avatar_url, [request.garment_url])
        cached_url = await firestore.get_cached_tryon(cache_key)
        if cached_url:
            return {
                "result_url": cached_url,
                "status": "success",
                "cached": True
            }

        # Download images from storage
        avatar_bytes = await storage.download_image(request.avatar_url)
        garment_bytes = await storage.download_image(request.garment_url)
        
        # Generate try-on using Vertex AI
        result_bytes = await vertex_ai.virtual_try_on(
            person_image=avatar_bytes,
            garment_image=garment_bytes,
            category=request.category
        )
        
        # Upload result to storage
        result_url = await storage.upload_tryon_result(
            result_bytes,
            user_id=user_id,
            garment_categories=[request.category],
        )
        
        # Save to cache
        await firestore.save_tryon_cache(
            cache_key=cache_key,
            user_id=user_id,
            avatar_url=request.avatar_url,
            garment_urls=[request.garment_url],
            result_url=result_url
        )
        
        return {
            "result_url": result_url,
            "status": "success",
            "cached": False
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Try-on failed: {str(e)}")


@router.post("/try-on-multiple")
async def try_on_multiple(
    request: MultiTryOnRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate a virtual try-on image combining avatar with multiple garments.
    
    Args:
        request: MultiTryOnRequest with avatar_url and list of garments
        user: Authenticated user from token
    
    Returns:
        URL of the generated try-on result
    """
    user_id = user["uid"]
    
    if not request.garments:
        raise HTTPException(status_code=400, detail="At least one garment is required")
    
    if len(request.garments) > 4:
        raise HTTPException(status_code=400, detail="Maximum 4 garments allowed")
    
    # Validate categories
    valid_categories = ["top", "bottom", "dress", "outerwear"]
    garment_urls = []
    for garment in request.garments:
        if garment.category not in valid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{garment.category}'. Must be: {', '.join(valid_categories)}"
            )
        garment_urls.append(garment.url)
    
    try:
        # Check cache first
        cache_key = calculate_tryon_cache_key(request.avatar_url, garment_urls)
        cached_url = await firestore.get_cached_tryon(cache_key)
        if cached_url:
            return {
                "result_url": cached_url,
                "status": "success",
                "garment_count": len(request.garments),
                "cached": True
            }

        # Download avatar image
        avatar_bytes = await storage.download_image(request.avatar_url)
        
        # Download all garment images
        garments_data = []
        for garment in request.garments:
            garment_bytes = await storage.download_image(garment.url)
            garments_data.append({
                "bytes": garment_bytes,
                "category": garment.category
            })
        
        # Generate try-on using Vertex AI with multiple garments
        result_bytes = await vertex_ai.virtual_try_on_multiple(
            person_image=avatar_bytes,
            garments=garments_data
        )
        
        # Upload result to storage
        result_url = await storage.upload_tryon_result(
            result_bytes,
            user_id=user_id,
            garment_ids=[garment.id for garment in request.garments if garment.id],
            garment_categories=[garment.category for garment in request.garments],
        )
        
        # Save to cache
        await firestore.save_tryon_cache(
            cache_key=cache_key,
            user_id=user_id,
            avatar_url=request.avatar_url,
            garment_urls=garment_urls,
            result_url=result_url
        )
        
        return {
            "result_url": result_url,
            "status": "success",
            "garment_count": len(request.garments),
            "cached": False
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Multi try-on failed: {str(e)}")


@router.get("/try-on/history")
async def get_tryon_history(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get recent try-on results for the current user.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        List of recent try-on result URLs
    """
    try:
        user_id = user["uid"]
        results = await storage.list_tryon_results(user_id=user_id, limit=50)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")


@router.delete("/look/{look_id}")
async def delete_look(
    look_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a saved look.
    
    Args:
        look_id: The ID of the look to delete
        user: Authenticated user from token
    
    Returns:
        Confirmation of deletion
    """
    try:
        user_id = user["uid"]
        await storage.delete_look(look_id=look_id, user_id=user_id)
        return {"status": "deleted", "id": look_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete look: {str(e)}")


@router.patch("/look/{look_id}")
async def update_look(
    look_id: str,
    request: LookMetadataRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Update favorite and occasion metadata for a saved look."""
    if request.occasion is not None and len(request.occasion) > 40:
        raise HTTPException(status_code=400, detail="Occasion must be 40 characters or fewer")

    try:
        metadata = await storage.update_look_metadata(
            look_id=look_id,
            user_id=user["uid"],
            favorite=request.favorite,
            occasion=request.occasion.strip() if request.occasion is not None else None,
        )
        return {"status": "updated", "id": look_id, **metadata}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update look: {error}",
        ) from error

