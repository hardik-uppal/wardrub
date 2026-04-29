"""Virtual try-on router - combines avatar with garments using Vertex AI."""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.storage import StorageService
from app.services.vertex_ai import VertexAIService
from app.services.auth import get_current_user

router = APIRouter()
storage = StorageService()
vertex_ai = VertexAIService()


class TryOnRequest(BaseModel):
    """Request model for try-on endpoint."""
    avatar_url: str
    garment_url: str
    category: str  # top, bottom, dress, outerwear


class GarmentItem(BaseModel):
    """Individual garment for multi-try-on."""
    url: str
    category: str  # top, bottom, dress, outerwear


class MultiTryOnRequest(BaseModel):
    """Request model for multi-garment try-on endpoint."""
    avatar_url: str
    garments: List[GarmentItem]


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
        result_url = await storage.upload_tryon_result(result_bytes, user_id=user_id)
        
        return {
            "result_url": result_url,
            "status": "success"
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
    for garment in request.garments:
        if garment.category not in valid_categories:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category '{garment.category}'. Must be: {', '.join(valid_categories)}"
            )
    
    try:
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
        result_url = await storage.upload_tryon_result(result_bytes, user_id=user_id)
        
        return {
            "result_url": result_url,
            "status": "success",
            "garment_count": len(request.garments)
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

