"""Garment processing router - background removal, ghost mannequin, and storage."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import Optional, List, Dict, Any
import uuid

from app.services.storage import StorageService
from app.services.background import BackgroundRemovalService
from app.services.vertex_ai import VertexAIService
from app.services.firestore import FirestoreService
from app.services.segmentation import SegmentationService
from app.services.quality_assessment import QualityAssessmentService
from app.services.color_analysis import ColorAnalysisService
from app.services.product_matcher import ProductMatcherService
from app.services.auth import get_current_user
from app.logging_config import get_logger
from app.models.garment import (
    GarmentMetadata,
    GarmentCategory,
    GarmentColors,
    GarmentDescription,
    GarmentVisibility,
    SourceImage,
    RecommendationScores,
    WeatherRange,
    VISIBILITY_THRESHOLDS,
)

router = APIRouter()
storage = StorageService()
bg_remover = BackgroundRemovalService()
vertex_ai = VertexAIService()
firestore = FirestoreService()
segmentation = SegmentationService()
quality_service = QualityAssessmentService()
color_service = ColorAnalysisService()
product_matcher = ProductMatcherService()
logger = get_logger("garment")


@router.post("/process-garment")
async def process_garment(
    front: UploadFile = File(..., description="Front view of garment"),
    back: Optional[UploadFile] = File(None, description="Optional back view of garment"),
    category: str = Form(..., description="Garment category: top, bottom, dress, outerwear"),
    ghost_mannequin: bool = Form(True, description="Apply ghost mannequin effect"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Process garment image(s) by removing background and optionally applying ghost mannequin effect.
    Saves front and back as separate mannequin images under the same garment ID.
    
    Args:
        front: Front view image of the garment
        back: Optional back view image of the garment
        category: The garment category (top, bottom, dress, outerwear)
        ghost_mannequin: Whether to apply AI ghost mannequin effect
        user: Authenticated user from token
    
    Returns:
        URLs and ID of the processed garment (front and optionally back)
    """
    user_id = user["uid"]
    
    if category not in ["top", "bottom", "dress", "outerwear"]:
        raise HTTPException(status_code=400, detail="Invalid category. Must be: top, bottom, dress, outerwear")
    
    # Read front image
    front_bytes = await front.read()
    if not front_bytes:
        raise HTTPException(status_code=400, detail="Empty front image uploaded")
    
    # Read back image if provided
    back_bytes = None
    if back:
        back_bytes = await back.read()
    
    try:
        # Generate unique ID for this garment
        garment_id = str(uuid.uuid4())
        
        # Process FRONT image
        front_nobg = await bg_remover.remove_background(front_bytes)
        
        if ghost_mannequin:
            front_processed = await bg_remover.create_ghost_mannequin(
                front_image_bytes=front_nobg,
                back_image_bytes=None,  # Process front separately
                category=category
            )
        else:
            front_processed = front_nobg
        
        # Upload front image
        front_url = await storage.upload_garment(
            image_bytes=front_processed,
            garment_id=f"{garment_id}_front",
            category=category,
            user_id=user_id
        )
        
        # Process BACK image if provided
        back_url = None
        if back_bytes:
            back_nobg = await bg_remover.remove_background(back_bytes)
            
            if ghost_mannequin:
                back_processed = await bg_remover.create_ghost_mannequin(
                    front_image_bytes=back_nobg,  # Use back as front for processing
                    back_image_bytes=None,
                    category=category
                )
            else:
                back_processed = back_nobg
            
            # Upload back image
            back_url = await storage.upload_garment(
                image_bytes=back_processed,
                garment_id=f"{garment_id}_back",
                category=category,
                user_id=user_id
            )
        
        return {
            "id": garment_id,
            "front_url": front_url,
            "back_url": back_url,
            "category": category,
            "has_back": back_url is not None,
            "ghost_mannequin": ghost_mannequin,
            "status": "processed"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process garment: {str(e)}")


@router.get("/wardrobe")
async def get_wardrobe(
    category: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all garments in the user's wardrobe.
    
    Args:
        category: Optional filter by category
        user: Authenticated user from token
    
    Returns:
        List of garment objects with URLs
    """
    try:
        user_id = user["uid"]
        garments = await storage.list_garments(user_id=user_id, category=category)
        return {"garments": garments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch wardrobe: {str(e)}")


@router.delete("/garment/{garment_id}")
async def delete_garment(
    garment_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a garment from the user's wardrobe.
    
    Args:
        garment_id: The ID of the garment to delete
        user: Authenticated user from token
    
    Returns:
        Confirmation of deletion
    """
    try:
        user_id = user["uid"]
        await storage.delete_garment(garment_id=garment_id, user_id=user_id)
        await firestore.delete_garment_metadata(garment_id)
        return {"status": "deleted", "id": garment_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete garment: {str(e)}")


@router.post("/process-uploaded-clothes")
async def process_uploaded_clothes(
    file: UploadFile = File(..., description="Image containing clothes to detect"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Process an uploaded image by detecting clothes and creating ghost mannequins.
    Uses Gemini to analyze the image and identify clothing items.
    
    Args:
        file: Image containing one or more clothing items
        user: Authenticated user from token
    
    Returns:
        List of processed garments with URLs and descriptions
    """
    user_id = user["uid"]
    logger.info(f"👕 Process uploaded clothes - filename: {file.filename}, user: {user_id}")
    
    image_bytes = await file.read()
    if not image_bytes:
        logger.warning("Empty file uploaded")
        raise HTTPException(status_code=400, detail="Empty image uploaded")
    
    logger.info(f"📦 Received image: {len(image_bytes)} bytes")
    
    try:
        # Step 1: Analyze image with Gemini to detect clothes
        logger.info("🔍 Step 1: Analyzing image for clothing items...")
        detected_items = await vertex_ai.detect_clothes_in_image(image_bytes)
        
        if not detected_items:
            logger.warning("No clothing items detected in image")
            raise HTTPException(
                status_code=400, 
                detail="No clothing items detected in the image. Try with a clearer photo."
            )
        
        logger.info(f"✅ Detected {len(detected_items)} clothing items")
        for i, item in enumerate(detected_items):
            logger.debug(f"  Item {i+1}: {item.get('category')} - {item.get('description', '')[:50]}...")
        
        processed_garments = []
        
        # Step 2: Create ghost mannequin for each detected item
        logger.info("🎨 Step 2: Creating ghost mannequins...")
        for i, item in enumerate(detected_items):
            garment_id = str(uuid.uuid4())
            category = item.get('category', 'top')
            description_text = item.get('description', '')
            
            logger.info(f"  Processing item {i+1}/{len(detected_items)}: {category}")
            
            # Generate ghost mannequin using Gemini
            mannequin_bytes = await vertex_ai.create_ghost_mannequin_from_description(
                image_bytes=image_bytes,
                description=description_text,
                category=category
            )
            
            logger.info(f"  Mannequin generated: {len(mannequin_bytes)} bytes")
            
            # Upload source image (original user upload)
            source_url = await storage.upload_source_image(
                image_bytes=image_bytes,
                user_id=user_id,
                garment_id=garment_id,
                view="original",
                content_type=file.content_type or "image/jpeg"
            )
            logger.info(f"  Source image saved: {source_url[:50]}...")
            
            # Upload processed garment image
            front_url = await storage.upload_garment(
                image_bytes=mannequin_bytes,
                garment_id=f"{garment_id}_front",
                category=category,
                user_id=user_id
            )
            
            logger.info(f"  Uploaded to storage: {front_url[:50]}...")
            
            # Create and save garment metadata to Firestore
            try:
                category_enum = GarmentCategory(category)
            except ValueError:
                category_enum = GarmentCategory.TOP
            
            metadata = GarmentMetadata(
                garment_id=garment_id,
                user_id=user_id,
                category=category_enum,
                source_images=[
                    SourceImage(
                        url=source_url,
                        view="original",
                        quality_score=0.8  # Default score for detected items
                    )
                ],
                ghost_mannequin_url=front_url,
                description=GarmentDescription(
                    short=description_text[:100] if description_text else f"{category} garment",
                    detailed=description_text,
                    style_tags=[]
                ),
                weather_range=_get_weather_range(category)
            )
            
            await firestore.save_garment_metadata(metadata)
            logger.info(f"  ✅ Garment metadata saved to Firestore: {garment_id}")
            
            processed_garments.append({
                "id": garment_id,
                "front_url": front_url,
                "back_url": None,
                "category": category,
                "description": description_text,
                "source_url": source_url,
                "status": "processed"
            })
        
        logger.info(f"✅ Successfully processed {len(processed_garments)} garments")
        
        return {
            "garments": processed_garments,
            "total_detected": len(processed_garments),
            "status": "processed"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to process uploaded clothes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded clothes: {str(e)}")


@router.post("/process-garment-full")
async def process_garment_full(
    files: List[UploadFile] = File(..., description="One or more garment images (front, back, detail)"),
    category: str = Form(..., description="Garment category: top, bottom, dress, outerwear"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Process garment with full analysis pipeline:
    - Quality assessment
    - Segmentation (SAM/rembg)
    - Visibility scoring
    - Color analysis
    - Ghost mannequin generation
    - Metadata storage in Firestore
    
    Args:
        files: List of garment images (front view required, back/detail optional)
        category: The garment category
        user: Authenticated user from token
    
    Returns:
        Processed garment with full metadata and quality feedback
    """
    user_id = user["uid"]
    logger.info(f"👕 Full garment processing - {len(files)} files, category: {category}, user: {user_id}")
    
    if category not in ["top", "bottom", "dress", "outerwear"]:
        raise HTTPException(status_code=400, detail="Invalid category. Must be: top, bottom, dress, outerwear")
    
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one image")
    
    try:
        garment_id = str(uuid.uuid4())
        category_enum = GarmentCategory(category)
        
        # Process each uploaded image
        processed_images = []
        source_images = []
        
        for i, file in enumerate(files):
            image_bytes = await file.read()
            if not image_bytes:
                continue
            
            logger.info(f"Processing image {i+1}/{len(files)}: {len(image_bytes)} bytes")
            
            # 1. Quality assessment
            quality = await quality_service.assess_image_quality(image_bytes)
            logger.info(f"  Quality score: {quality['score']:.2f}")
            
            if not quality["is_acceptable"]:
                logger.warning(f"  Image {i+1} quality too low, skipping")
                continue
            
            # 2. Segmentation
            mask, mask_metadata = await segmentation.segment_garment(image_bytes, category)
            
            # 3. Visibility scoring
            if mask is not None:
                from PIL import Image
                from io import BytesIO
                img = Image.open(BytesIO(image_bytes))
                visibility = await quality_service.calculate_visibility_score(
                    mask, img.size, category_enum
                )
            else:
                visibility = GarmentVisibility(
                    score=0.5,
                    category_threshold=VISIBILITY_THRESHOLDS.get(category_enum, 0.5),
                    status="acceptable"
                )
            
            logger.info(f"  Visibility: {visibility.score:.2%} ({visibility.status})")
            
            # 4. Extract foreground
            foreground_bytes = await segmentation.extract_foreground(image_bytes, mask)
            
            # Determine view type
            view = "front" if i == 0 else ("back" if i == 1 else f"detail_{i}")
            
            processed_images.append({
                "bytes": foreground_bytes,
                "original_bytes": image_bytes,
                "view": view,
                "quality": quality,
                "visibility": visibility,
                "mask": mask,
                "content_type": file.content_type or "image/jpeg"
            })
            
            # Upload source image and store reference
            source_url = await storage.upload_source_image(
                image_bytes=image_bytes,
                user_id=user_id,
                garment_id=garment_id,
                view=view,
                content_type=file.content_type or "image/jpeg"
            )
            logger.info(f"  Source image uploaded: {source_url[:50]}...")
            
            source_images.append(SourceImage(
                url=source_url,
                view=view,
                quality_score=quality["score"]
            ))
        
        if not processed_images:
            raise HTTPException(
                status_code=400,
                detail="None of the uploaded images were acceptable. Please try better quality photos."
            )
        
        # Check if more images needed
        needs_more, more_recommendation = await quality_service.needs_more_images(
            [p["visibility"] for p in processed_images]
        )
        
        # Select best image for ghost mannequin
        best_image = max(processed_images, key=lambda x: x["visibility"].score)
        
        # 5. Create ghost mannequin
        logger.info("Creating ghost mannequin...")
        ghost_bytes = await bg_remover.create_ghost_mannequin(
            front_image_bytes=best_image["bytes"],
            back_image_bytes=processed_images[1]["bytes"] if len(processed_images) > 1 else None,
            category=category
        )
        
        # 6. Color analysis
        logger.info("Analyzing colors...")
        colors = await color_service.analyze_garment_colors(ghost_bytes, category)
        
        # 7. Upload processed images
        ghost_url = await storage.upload_garment(
            image_bytes=ghost_bytes,
            garment_id=f"{garment_id}_front",
            category=category,
            user_id=user_id
        )
        
        # Upload back if available
        back_url = None
        if len(processed_images) > 1:
            back_url = await storage.upload_garment(
                image_bytes=processed_images[1]["bytes"],
                garment_id=f"{garment_id}_back",
                category=category,
                user_id=user_id
            )
        
        # 8. Create and save metadata
        # Get user profile for recommendation scores
        user_profile = await firestore.get_user_profile(user_id)
        
        # Calculate recommendation scores
        color_harmony = 0.5
        fit_score = 0.5
        if user_profile and user_profile.skin_tone and colors:
            color_harmony = color_service.calculate_color_harmony(
                user_profile.skin_tone, colors
            )
        
        metadata = GarmentMetadata(
            garment_id=garment_id,
            user_id=user_id,
            category=category_enum,
            source_images=source_images,
            ghost_mannequin_url=ghost_url,
            mask_url=None,  # Could store mask if needed
            colors=colors,
            description=GarmentDescription(
                short=f"{colors.color_family.capitalize() if colors else ''} {category}".strip(),
                detailed="",
                style_tags=[]
            ),
            fit_type=None,  # Would need AI to determine
            season_suitability=_get_season_suitability(colors) if colors else [],
            weather_range=_get_weather_range(category),
            visibility=best_image["visibility"],
            recommendation_scores=RecommendationScores(
                color_harmony_with_user=color_harmony,
                fit_recommendation=fit_score,
                versatility=0.7,
                overall=(color_harmony * 0.5 + fit_score * 0.3 + 0.7 * 0.2)
            )
        )
        
        await firestore.save_garment_metadata(metadata)
        logger.info(f"✅ Garment metadata saved: {garment_id}")
        
        return {
            "id": garment_id,
            "front_url": ghost_url,
            "back_url": back_url,
            "category": category,
            "colors": colors.model_dump() if colors else None,
            "visibility": best_image["visibility"].model_dump(),
            "recommendation_scores": metadata.recommendation_scores.model_dump(),
            "quality_feedback": {
                "needs_more_images": needs_more,
                "recommendation": more_recommendation,
                "images_processed": len(processed_images)
            },
            "status": "processed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Full garment processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process garment: {str(e)}")


@router.get("/garment/{garment_id}/metadata")
async def get_garment_metadata(
    garment_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get metadata for a specific garment.
    
    Args:
        garment_id: The garment ID
        user: Authenticated user from token
    
    Returns:
        Garment metadata including colors, visibility, recommendations
    """
    try:
        metadata = await firestore.get_garment_metadata(garment_id)
        
        if not metadata:
            return {
                "metadata": None,
                "status": "not_found",
                "message": "Garment has no metadata. Re-process with full analysis."
            }
        
        # Verify ownership
        if metadata.user_id != user["uid"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return {
            "metadata": metadata.model_dump(),
            "status": "found"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get garment metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/garment/{garment_id}/analyze")
async def analyze_existing_garment(
    garment_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Analyze an existing garment that doesn't have metadata.
    Downloads from storage and runs analysis.
    
    Args:
        garment_id: The garment ID to analyze
        user: Authenticated user from token
    
    Returns:
        Updated metadata
    """
    user_id = user["uid"]
    logger.info(f"Analyzing existing garment: {garment_id} for user: {user_id}")
    
    try:
        # Check if already has metadata
        existing = await firestore.get_garment_metadata(garment_id)
        if existing:
            # Verify ownership
            if existing.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            return {
                "metadata": existing.model_dump(),
                "status": "already_analyzed"
            }
        
        # Get garment from storage
        garments = await storage.list_garments(user_id=user_id)
        garment = next((g for g in garments if g["id"] == garment_id), None)
        
        if not garment:
            raise HTTPException(status_code=404, detail="Garment not found")
        
        # Download image
        front_url = garment.get("front_url") or garment.get("url")
        image_bytes = await storage.download_image(front_url)
        
        category = garment.get("category", "top")
        
        # Run color analysis
        colors = await color_service.analyze_garment_colors(image_bytes, category)
        
        # Create metadata
        metadata = GarmentMetadata(
            garment_id=garment_id,
            user_id=user_id,
            category=GarmentCategory(category),
            ghost_mannequin_url=front_url,
            colors=colors,
            description=GarmentDescription(
                short=f"{colors.color_family.capitalize() if colors else ''} {category}".strip(),
                detailed="",
                style_tags=[]
            ),
            weather_range=_get_weather_range(category),
            visibility=GarmentVisibility(
                score=0.7,  # Assume acceptable for existing items
                category_threshold=VISIBILITY_THRESHOLDS.get(GarmentCategory(category), 0.5),
                status="acceptable"
            )
        )
        
        # Calculate recommendation scores if profile exists
        user_profile = await firestore.get_user_profile(user_id)
        if user_profile and user_profile.skin_tone and colors:
            color_harmony = color_service.calculate_color_harmony(
                user_profile.skin_tone, colors
            )
            metadata.recommendation_scores.color_harmony_with_user = color_harmony
            metadata.recommendation_scores.overall = color_harmony * 0.5 + 0.5 * 0.5
        
        await firestore.save_garment_metadata(metadata)
        
        return {
            "metadata": metadata.model_dump(),
            "status": "analyzed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze garment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _get_season_suitability(colors: GarmentColors) -> List[str]:
    """Determine season suitability based on colors."""
    if not colors:
        return ["spring", "summer", "autumn", "winter"]
    
    warmth = colors.warmth
    color_family = colors.color_family.lower()
    
    # Dark colors = autumn/winter
    # Light colors = spring/summer
    # Warm colors = spring/autumn
    # Cool colors = summer/winter
    
    seasons = []
    
    if warmth == "warm":
        seasons.extend(["spring", "autumn"])
    elif warmth == "cool":
        seasons.extend(["summer", "winter"])
    else:
        seasons.extend(["spring", "summer", "autumn", "winter"])
    
    # Color-specific adjustments
    if color_family in ["white", "cream", "beige"]:
        seasons = ["spring", "summer"]
    elif color_family in ["black", "navy", "burgundy"]:
        seasons = ["autumn", "winter"]
    
    return list(set(seasons))


def _get_weather_range(category: str) -> WeatherRange:
    """Get default weather range for category."""
    ranges = {
        "top": WeatherRange(min_temp=15, max_temp=35),
        "bottom": WeatherRange(min_temp=10, max_temp=35),
        "dress": WeatherRange(min_temp=18, max_temp=32),
        "outerwear": WeatherRange(min_temp=-5, max_temp=20),
    }
    return ranges.get(category, WeatherRange(min_temp=10, max_temp=30))


# =============================================================================
# Product Matching Endpoints - Find similar products & extract rich metadata
# =============================================================================

@router.post("/find-similar-products")
async def find_similar_products(
    file: UploadFile = File(..., description="Garment image to find matches for"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Find visually similar products online using Google Cloud Vision API.
    Returns a list of similar product images for user to confirm.
    
    Args:
        file: Garment image to match
        user: Authenticated user
    
    Returns:
        List of similar products with image URLs, web entities, and best guess labels
    """
    logger.info(f"🔍 Finding similar products for user: {user['uid']}")
    
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image uploaded")
    
    try:
        result = await product_matcher.find_similar_products(image_bytes)
        
        return {
            "similar_products": result["similar_products"],
            "web_entities": result["web_entities"],
            "best_guess_labels": result["best_guess_labels"],
            "pages_with_matches": result["pages_with_matches"],
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to find similar products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to find similar products: {str(e)}")


@router.post("/garment/{garment_id}/find-similar")
async def find_similar_for_garment(
    garment_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Find visually similar products for an existing garment in the wardrobe.
    
    Args:
        garment_id: ID of the garment to find matches for
        user: Authenticated user
    
    Returns:
        List of similar products with image URLs
    """
    user_id = user["uid"]
    logger.info(f"🔍 Finding similar products for garment: {garment_id}")
    
    try:
        # Get garment from storage
        garments = await storage.list_garments(user_id=user_id)
        garment = next((g for g in garments if g["id"] == garment_id), None)
        
        if not garment:
            raise HTTPException(status_code=404, detail="Garment not found")
        
        # Download garment image
        front_url = garment.get("front_url") or garment.get("url")
        image_bytes = await storage.download_image(front_url)
        
        # Find similar products
        result = await product_matcher.find_similar_products(image_bytes)
        
        return {
            "garment_id": garment_id,
            "similar_products": result["similar_products"],
            "web_entities": result["web_entities"],
            "best_guess_labels": result["best_guess_labels"],
            "pages_with_matches": result["pages_with_matches"],
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find similar products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/garment/{garment_id}/confirm-match")
async def confirm_product_match(
    garment_id: str,
    match_image_url: str = Form(..., description="URL of the confirmed similar product image"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Confirm a product match and extract detailed information using Gemini.
    Updates the garment metadata with the enhanced product details.
    
    Args:
        garment_id: ID of the garment
        match_image_url: URL of the confirmed similar product image
        user: Authenticated user
    
    Returns:
        Extracted product details and updated garment metadata
    """
    user_id = user["uid"]
    logger.info(f"✅ Confirming product match for garment: {garment_id}")
    logger.info(f"   Match URL: {match_image_url[:80]}...")
    
    try:
        # Get existing garment metadata
        metadata = await firestore.get_garment_metadata(garment_id)
        
        if not metadata:
            # Get garment from storage to determine category
            garments = await storage.list_garments(user_id=user_id)
            garment = next((g for g in garments if g["id"] == garment_id), None)
            if not garment:
                raise HTTPException(status_code=404, detail="Garment not found")
            category = garment.get("category", "top")
            
            # Download garment image for comparison
            front_url = garment.get("front_url") or garment.get("url")
            original_image_bytes = await storage.download_image(front_url)
        else:
            # Verify ownership
            if metadata.user_id != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            category = metadata.category
            
            # Download original image
            if metadata.ghost_mannequin_url:
                original_image_bytes = await storage.download_image(metadata.ghost_mannequin_url)
            else:
                original_image_bytes = None
        
        # Extract product details from confirmed match
        product_details = await product_matcher.extract_product_details(
            image_url=match_image_url,
            garment_category=category if isinstance(category, str) else category.value,
            original_image_bytes=original_image_bytes
        )
        
        # Update or create metadata with enhanced info
        if metadata:
            # Update existing metadata
            if product_details.description:
                metadata.description = GarmentDescription(
                    short=product_details.product_name or metadata.description.short,
                    detailed=product_details.description,
                    style_tags=product_details.features or metadata.description.style_tags
                )
            
            if product_details.fit:
                from app.models.garment import FitType
                fit_mapping = {
                    "slim": FitType.FITTED,
                    "fitted": FitType.FITTED,
                    "regular": FitType.REGULAR,
                    "relaxed": FitType.LOOSE,
                    "loose": FitType.LOOSE,
                    "oversized": FitType.OVERSIZED,
                    "tailored": FitType.FITTED
                }
                metadata.fit_type = fit_mapping.get(product_details.fit.lower(), FitType.REGULAR)
            
            if product_details.season:
                metadata.season_suitability = product_details.season
            
            metadata.updated_at = __import__("datetime").datetime.utcnow()
            
            await firestore.save_garment_metadata(metadata)
        else:
            # Create new metadata with extracted info
            metadata = GarmentMetadata(
                garment_id=garment_id,
                user_id=user_id,
                category=GarmentCategory(category),
                description=GarmentDescription(
                    short=product_details.product_name or f"{category.capitalize()} garment",
                    detailed=product_details.description,
                    style_tags=product_details.features or []
                ),
                season_suitability=product_details.season or [],
                weather_range=_get_weather_range(category)
            )
            await firestore.save_garment_metadata(metadata)
        
        logger.info(f"✅ Updated garment {garment_id} with product details")
        
        return {
            "garment_id": garment_id,
            "product_details": {
                "source_url": product_details.source_url,
                "brand": product_details.brand,
                "product_name": product_details.product_name,
                "material": product_details.material,
                "fabric_composition": product_details.fabric_composition,
                "style": product_details.style,
                "fit": product_details.fit,
                "care_instructions": product_details.care_instructions,
                "occasions": product_details.occasion,
                "seasons": product_details.season,
                "features": product_details.features,
                "description": product_details.description,
                "price_range": product_details.price_range
            },
            "metadata_updated": True,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm product match: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-product-info")
async def extract_product_info(
    file: UploadFile = File(..., description="Garment image"),
    category: str = Form(..., description="Garment category"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    One-step process: Find similar products and auto-extract details from best match.
    Great for quickly getting enhanced garment information.
    
    Args:
        file: Garment image
        category: Garment category (top, bottom, dress, outerwear)
        user: Authenticated user
    
    Returns:
        Similar products + auto-extracted details from best match
    """
    logger.info(f"🔮 Auto-extracting product info for category: {category}")
    
    if category not in ["top", "bottom", "dress", "outerwear"]:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image uploaded")
    
    try:
        result = await product_matcher.get_enhanced_garment_info(image_bytes, category)
        
        return {
            "similar_products": result["similar_products"],
            "web_entities": result["web_entities"],
            "best_guess_labels": result["best_guess_labels"],
            "auto_extracted_details": result["auto_extracted_details"],
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to extract product info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

