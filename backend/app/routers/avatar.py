"""Avatar generation router - creates full-body avatar with analysis."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional, Dict, Any

from app.services.storage import StorageService
from app.services.vertex_ai import VertexAIService
from app.services.firestore import FirestoreService
from app.services.quality_assessment import QualityAssessmentService
from app.services.color_analysis import ColorAnalysisService
from app.services.body_analysis import BodyAnalysisService
from app.services.auth import get_current_user
from app.logging_config import get_logger
from app.models.user_profile import UserProfile, AnalysisQuality

router = APIRouter()
storage = StorageService()
vertex_ai = VertexAIService()
firestore = FirestoreService()
quality_service = QualityAssessmentService()
color_service = ColorAnalysisService()
body_service = BodyAnalysisService()
logger = get_logger("avatar")


@router.post("/create-avatar")
async def create_avatar(
    files: List[UploadFile] = File(...),
    mode: str = Form("upload"),  # 'upload' (full body) or 'selfie' (face swap)
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a full-body avatar.
    
    Modes:
        - 'upload': Use the uploaded full-body photo, process with Gemini
        - 'selfie': Apply the selfie face to a default avatar body
    
    Args:
        files: User image(s)
        mode: 'upload' or 'selfie'
        user: Authenticated user from token
    
    Returns:
        URL of the generated avatar
    """
    user_id = user["uid"]
    logger.info(f"🎭 Create avatar request - mode: {mode}, files: {len(files)}, user: {user_id}")
    
    if not files:
        logger.warning("No files uploaded")
        raise HTTPException(status_code=400, detail="Please upload an image")
    
    # Read the first image
    image_bytes = await files[0].read()
    if not image_bytes:
        logger.warning("Empty file uploaded")
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    logger.info(f"📦 Received image: {len(image_bytes)} bytes, filename: {files[0].filename}")
    
    try:
        # Save source image first
        source_type = "fullbody" if mode == "upload" else "selfie"
        source_url = await storage.upload_avatar_source(
            image_bytes=image_bytes,
            user_id=user_id,
            source_type=source_type,
            content_type=files[0].content_type or "image/jpeg"
        )
        logger.info(f"📷 Source image saved: {source_url[:50]}...")
        
        if mode == "upload":
            # Full body upload - process through Gemini for clean avatar
            logger.info("🔄 Processing as UPLOAD mode (full body photo)")
            avatar_bytes = await vertex_ai.process_uploaded_avatar(image_bytes)
        else:
            # Selfie mode - face swap onto default avatar
            logger.info("🔄 Processing as SELFIE mode (face swap)")
            avatar_bytes = await vertex_ai.create_avatar_from_selfie(image_bytes)
        
        logger.info(f"✅ Avatar generated: {len(avatar_bytes)} bytes")
        
        # Upload avatar to storage
        avatar_url = await storage.upload_avatar(avatar_bytes, user_id=user_id)
        logger.info(f"📤 Avatar uploaded to storage: {avatar_url[:50]}...")
        
        return {
            "avatar_url": avatar_url,
            "source_url": source_url,
            "mode": mode,
            "status": "created"
        }
    
    except Exception as e:
        logger.error(f"❌ Avatar creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create avatar: {str(e)}")


@router.get("/avatar")
async def get_avatar(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get the current user's avatar.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        Avatar URL if exists
    """
    try:
        user_id = user["uid"]
        avatar_url = await storage.get_avatar(user_id=user_id)
        if not avatar_url:
            return {"avatar_url": None, "status": "not_created"}
        return {"avatar_url": avatar_url, "status": "exists"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch avatar: {str(e)}")


@router.delete("/avatar")
async def delete_avatar(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Delete the current user's avatar.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        Confirmation of deletion
    """
    try:
        user_id = user["uid"]
        await storage.delete_avatar(user_id=user_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete avatar: {str(e)}")


@router.post("/create-avatar-full")
async def create_avatar_full(
    files: List[UploadFile] = File(..., description="One or more photos for avatar and profile"),
    mode: str = Form("upload"),  # 'upload' (full body) or 'selfie' (face swap)
    analyze_profile: bool = Form(True, description="Also analyze for profile (skin tone, body type)"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create avatar with full profile analysis.
    
    Supports multiple images for better analysis:
    - Best quality image used for avatar generation
    - All images analyzed for skin tone and body type
    - Returns quality feedback if more images would help
    
    Args:
        files: User image(s) - more images = better analysis
        mode: 'upload' (full body) or 'selfie' (face)
        analyze_profile: Whether to run skin tone and body type analysis
        user: Authenticated user from token
    
    Returns:
        Avatar URL, profile analysis, and quality feedback
    """
    user_id = user["uid"]
    logger.info(f"🎭 Full avatar creation - mode: {mode}, files: {len(files)}, analyze: {analyze_profile}, user: {user_id}")
    
    if not files:
        raise HTTPException(status_code=400, detail="Please upload at least one image")
    
    try:
        # Process all uploaded images
        processed_images = []
        source_urls = []
        
        for i, file in enumerate(files):
            image_bytes = await file.read()
            if not image_bytes:
                continue
            
            logger.info(f"Processing image {i+1}/{len(files)}: {len(image_bytes)} bytes")
            
            # Quality assessment
            quality = await quality_service.assess_image_quality(image_bytes)
            
            if quality["is_acceptable"]:
                # Save source image
                source_type = f"source_{i}" if i > 0 else ("fullbody" if mode == "upload" else "selfie")
                source_url = await storage.upload_avatar_source(
                    image_bytes=image_bytes,
                    user_id=user_id,
                    source_type=source_type,
                    content_type=file.content_type or "image/jpeg"
                )
                source_urls.append(source_url)
                logger.info(f"  Source image saved: {source_url[:50]}...")
                
                processed_images.append({
                    "bytes": image_bytes,
                    "quality": quality,
                    "filename": file.filename,
                    "source_url": source_url
                })
            else:
                logger.warning(f"Image {i+1} quality too low: {quality['issues']}")
        
        if not processed_images:
            raise HTTPException(
                status_code=400,
                detail="None of the uploaded images were acceptable quality. Try better lighting."
            )
        
        # Select best image for avatar
        best_image = max(processed_images, key=lambda x: x["quality"]["score"])
        image_bytes = best_image["bytes"]
        
        # Generate avatar
        if mode == "upload":
            logger.info("Creating avatar from full body photo...")
            avatar_bytes = await vertex_ai.process_uploaded_avatar(image_bytes)
        else:
            logger.info("Creating avatar from selfie...")
            avatar_bytes = await vertex_ai.create_avatar_from_selfie(image_bytes)
        
        # Upload avatar
        avatar_url = await storage.upload_avatar(avatar_bytes, user_id=user_id)
        logger.info(f"Avatar uploaded: {avatar_url[:50]}...")
        
        # Profile analysis
        profile_data = None
        color_recommendations = None
        fit_recommendations = None
        quality_feedback = None
        
        if analyze_profile:
            logger.info("Analyzing profile from images...")
            
            # Skin tone analysis (use avatar or original)
            skin_tone, skin_confidence = await color_service.analyze_skin_tone(
                avatar_bytes if mode == "upload" else image_bytes
            )
            
            # Body type analysis (use full body image if available)
            body_type = None
            body_measurements = None
            body_confidence = 0.0
            
            if mode == "upload":
                body_type, body_measurements, body_confidence = await body_service.analyze_body_type(
                    image_bytes
                )
            
            # Determine if more images needed
            needs_more = (
                (skin_confidence < 0.7 if skin_tone else True) or
                (body_confidence < 0.7 if body_type else True) or
                len(processed_images) < 2
            )
            
            recommendation = None
            if needs_more:
                if not skin_tone or skin_confidence < 0.7:
                    recommendation = "Add a well-lit face photo for better skin tone analysis"
                elif not body_type or body_confidence < 0.7:
                    recommendation = "Add a full-body photo for body type analysis"
                else:
                    recommendation = "Adding more photos can improve recommendations"
            
            # Get or update profile
            existing_profile = await firestore.get_user_profile(user_id)
            
            profile = UserProfile(
                skin_tone=skin_tone,
                body_type=body_type,
                body_measurements=body_measurements,
                style_preferences=existing_profile.style_preferences if existing_profile else [],
                location=existing_profile.location if existing_profile else None,
                source_images=source_urls,  # Use actual uploaded source URLs
                analysis_quality=AnalysisQuality(
                    skin_tone_confidence=skin_confidence,
                    body_type_confidence=body_confidence,
                    needs_more_images=needs_more,
                    recommendation=recommendation
                )
            )
            
            await firestore.save_user_profile(profile, user_id)
            
            profile_data = {
                "skin_tone": skin_tone.model_dump() if skin_tone else None,
                "body_type": body_type.value if body_type else None,
                "analysis_quality": profile.analysis_quality.model_dump()
            }
            
            if skin_tone:
                color_recommendations = color_service.get_color_recommendations(skin_tone)
            
            if body_type:
                fit_recommendations = body_service.get_fit_recommendations(body_type)
            
            quality_feedback = {
                "images_processed": len(processed_images),
                "needs_more_images": needs_more,
                "recommendation": recommendation
            }
        
        return {
            "avatar_url": avatar_url,
            "source_urls": source_urls,
            "mode": mode,
            "profile": profile_data,
            "color_recommendations": color_recommendations,
            "fit_recommendations": fit_recommendations,
            "quality_feedback": quality_feedback,
            "status": "created"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Full avatar creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create avatar: {str(e)}")

