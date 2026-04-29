"""Daily looks generator job - creates pre-rendered outfit recommendations."""

import asyncio
import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from app.logging_config import get_logger
from app.services.firestore import FirestoreService
from app.services.storage import StorageService
from app.services.weather import WeatherService
from app.services.vertex_ai import VertexAIService
from app.services.outfit_scorer import OutfitScorerService
from app.models.daily_looks import DailyLook, DailyLooks, ScoredOutfit

logger = get_logger("daily_looks_generator")


async def generate_daily_looks(
    user_id: str = "default_user",
    num_looks: int = 3,
    delay_between_tryon: float = 2.0
) -> Optional[DailyLooks]:
    """
    Generate daily outfit recommendations with pre-rendered try-on images.
    
    This job:
    1. Loads user profile (skin tone, location, avatar)
    2. Fetches current weather for the user's location
    3. Loads all garments with descriptions
    4. Scores all possible outfit combinations
    5. Selects top N outfits
    6. Generates virtual try-on images for each outfit
    7. Saves DailyLooks to Firestore
    
    Args:
        user_id: User to generate looks for
        num_looks: Number of outfit looks to generate (default 3)
        delay_between_tryon: Seconds to wait between try-on API calls
    
    Returns:
        DailyLooks object or None if failed
    """
    logger.info(f"Starting daily looks generation for user {user_id}...")
    
    firestore = FirestoreService()
    storage = StorageService()
    weather_service = WeatherService()
    vertex_ai = VertexAIService()
    outfit_scorer = OutfitScorerService()
    
    # 1. Load user profile
    user_profile = await firestore.get_user_profile(user_id)
    if not user_profile:
        logger.warning(f"No user profile found for {user_id}")
        return None
    
    # 2. Get avatar
    avatar_url = await storage.get_avatar()
    if not avatar_url:
        logger.warning(f"No avatar found for {user_id} - cannot generate try-on images")
        return None
    
    # Download avatar image
    try:
        avatar_bytes = await storage.download_image(avatar_url)
    except Exception as e:
        logger.error(f"Failed to download avatar: {e}")
        return None
    
    # 3. Fetch weather
    weather_data = None
    weather_dict = None
    location_str = None
    
    if user_profile.location:
        city = user_profile.location.city
        weather_info = await weather_service.get_weather_by_coords(
            user_profile.location.lat,
            user_profile.location.lon
        )
        
        if weather_info:
            location_str = city or weather_info.city
            # Convert to dict for scoring service
            weather_dict = {
                "temperature": weather_info.temperature,
                "description": weather_info.description,
                "humidity": weather_info.humidity,
                "condition": weather_info.condition
            }
            logger.info(f"Weather for {location_str}: {weather_info.temperature}°C, {weather_info.description}")
    
    if not weather_dict:
        # Use default weather
        weather_dict = {
            "temperature": 20,
            "description": "mild",
            "humidity": 50
        }
        logger.info("Using default weather (no location set)")
    
    # 4. Load garments with metadata
    garments = await firestore.list_garments_metadata()
    
    if len(garments) < 2:
        logger.warning(f"Not enough garments ({len(garments)}) to create outfits")
        return None
    
    logger.info(f"Loaded {len(garments)} garments for outfit generation")
    
    # 5. Generate top outfit combinations
    scored_outfits = outfit_scorer.generate_top_outfits(
        garments=garments,
        user_profile=user_profile,
        weather=weather_dict,
        limit=num_looks
    )
    
    if not scored_outfits:
        logger.warning("No valid outfit combinations generated")
        return None
    
    logger.info(f"Generated {len(scored_outfits)} top scoring outfits")
    
    # 6. Generate try-on images for each outfit
    daily_looks: List[DailyLook] = []
    
    for i, scored_outfit in enumerate(scored_outfits):
        logger.info(f"Generating try-on {i+1}/{len(scored_outfits)} (score: {scored_outfit.overall_score:.2f})...")
        
        try:
            # Download garment images
            garment_images = []
            for item in scored_outfit.items:
                if item.image_url:
                    try:
                        garment_bytes = await storage.download_image(item.image_url)
                        garment_images.append({
                            "bytes": garment_bytes,
                            "category": item.category
                        })
                    except Exception as e:
                        logger.warning(f"Failed to download garment {item.garment_id}: {e}")
            
            if not garment_images:
                logger.warning(f"No valid garment images for outfit {i+1}")
                continue
            
            # Generate try-on image
            if len(garment_images) == 1:
                # Single garment try-on
                tryon_bytes = await vertex_ai.virtual_try_on(
                    person_image=avatar_bytes,
                    garment_image=garment_images[0]["bytes"],
                    garment_category=garment_images[0]["category"]
                )
            else:
                # Multi-garment try-on
                tryon_bytes = await vertex_ai.virtual_try_on_multiple(
                    person_image=avatar_bytes,
                    garments=garment_images
                )
            
            # Upload try-on result
            tryon_url = await storage.upload_tryon_result(tryon_bytes)
            logger.info(f"  Try-on image uploaded: {tryon_url[:50]}...")
            
            # Build weather context string
            temp = weather_dict.get("temperature", 20)
            desc = weather_dict.get("description", "")
            weather_context = f"{temp}°C, {desc}"
            if location_str:
                weather_context += f" in {location_str}"
            
            # Build reasoning string (only weather reasoning - style is shown separately)
            reasoning = scored_outfit.weather_reasoning if scored_outfit.weather_reasoning else "Great outfit for today"
            
            # Create DailyLook
            daily_look = DailyLook(
                id=f"look-{uuid.uuid4().hex[:8]}",
                outfit_items=scored_outfit.items,
                tryon_image_url=tryon_url,
                score=scored_outfit.overall_score,
                reasoning=reasoning,
                weather_context=weather_context,
                color_harmony_notes=scored_outfit.color_reasoning,
                style_notes=scored_outfit.style_reasoning
            )
            daily_looks.append(daily_look)
            
            # Rate limit between API calls
            if i < len(scored_outfits) - 1:
                await asyncio.sleep(delay_between_tryon)
        
        except Exception as e:
            logger.error(f"Failed to generate try-on for outfit {i+1}: {e}")
            continue
    
    if not daily_looks:
        logger.error("Failed to generate any try-on images")
        return None
    
    # 7. Create DailyLooks object
    today = date.today().isoformat()
    weather_summary = None
    if weather_dict:
        temp = weather_dict.get("temperature", "?")
        desc = weather_dict.get("description", "")
        weather_summary = f"{temp}°C, {desc}"
    
    daily_looks_obj = DailyLooks(
        user_id=user_id,
        date=today,
        looks=daily_looks,
        weather_summary=weather_summary,
        location=location_str,
        generated_at=datetime.utcnow()
    )
    
    # 8. Save to Firestore
    await firestore.save_daily_looks(daily_looks_obj)
    
    logger.info(f"Daily looks generation complete: {len(daily_looks)} looks saved for {today}")
    return daily_looks_obj


async def run_daily_looks_job():
    """
    Main entry point for the scheduled daily job.
    This is called by APScheduler.
    """
    logger.info("=== Running scheduled daily looks generation ===")
    
    try:
        result = await generate_daily_looks()
        
        if result:
            logger.info(f"Daily looks job completed: {len(result.looks)} looks generated")
        else:
            logger.warning("Daily looks job completed with no results")
    
    except Exception as e:
        logger.error(f"Daily looks job failed: {e}")
        import traceback
        traceback.print_exc()


async def regenerate_daily_looks_if_missing(user_id: str = "default_user") -> bool:
    """
    Check if today's looks exist, generate if missing.
    Called on server startup.
    
    Returns:
        True if looks were generated, False if already existed
    """
    firestore = FirestoreService()
    
    today = date.today().isoformat()
    existing = await firestore.get_daily_looks(user_id, today)
    
    if existing:
        logger.info(f"Daily looks for {today} already exist ({len(existing.looks)} looks)")
        return False
    
    logger.info(f"No daily looks for {today}, generating...")
    result = await generate_daily_looks(user_id)
    return result is not None

