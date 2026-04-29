"""Outfit recommendation router for daily outfit suggestions."""

from datetime import date
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Depends
from typing import Optional, List, Dict, Any

from app.services.firestore import FirestoreService
from app.services.storage import StorageService
from app.services.recommendation import RecommendationEngine
from app.services.weather import WeatherService
from app.services.auth import get_current_user
from app.logging_config import get_logger
from app.models.outfit import Occasion, OutfitRequest
from app.models.daily_looks import DailyLooks, DailyLook
from app.jobs.daily_looks_generator import generate_daily_looks
from app.jobs.scheduler import get_job_status

router = APIRouter()
firestore = FirestoreService()
storage = StorageService()
recommendation_engine = RecommendationEngine()
weather_service = WeatherService()
logger = get_logger("outfit")


async def _ensure_garments_synced(user_id: str):
    """Ensure garments from storage are synced to metadata store for a user."""
    # Check if we have any garments in metadata
    garments = await firestore.list_garments_metadata(user_id=user_id, limit=1)
    if not garments:
        # Sync from storage
        storage_garments = await storage.list_garments(user_id=user_id)
        if storage_garments:
            await firestore.sync_garments_from_storage(user_id=user_id, storage_garments=storage_garments)


@router.get("/daily-outfit")
async def get_daily_outfit(
    use_weather: bool = Query(True, description="Include weather in recommendations"),
    occasion: Optional[str] = Query(None, description="Occasion: casual, work, date_night, formal"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get today's recommended outfit based on user profile and weather.
    
    This is the main endpoint for the Daily Outfit page.
    
    Args:
        use_weather: Whether to factor in current weather
        occasion: Optional occasion filter
        user: Authenticated user from token
    
    Returns:
        Top outfit recommendation with reasoning
    """
    user_id = user["uid"]
    logger.info(f"Getting daily outfit (weather: {use_weather}, occasion: {occasion}, user: {user_id})")
    
    try:
        # Ensure garments are synced from storage
        await _ensure_garments_synced(user_id)
        
        # Parse occasion if provided
        occasion_enum = None
        if occasion:
            try:
                occasion_enum = Occasion(occasion)
            except ValueError:
                logger.warning(f"Invalid occasion: {occasion}")
        
        # Get user profile
        profile = await firestore.get_user_profile(user_id)
        
        if not profile:
            return {
                "outfit": None,
                "status": "no_profile",
                "message": "Create your profile first to get personalized recommendations"
            }
        
        # Get daily outfit
        outfit = await recommendation_engine.get_daily_outfit(
            user_profile=profile,
            use_weather=use_weather,
            occasion=occasion_enum
        )
        
        if not outfit:
            return {
                "outfit": None,
                "status": "no_outfits",
                "message": "Add clothes to your wardrobe to get recommendations"
            }
        
        # Get weather info for display
        weather_info = None
        if profile.location and use_weather:
            weather_info = await weather_service.get_weather_by_coords(
                profile.location.lat,
                profile.location.lon
            )
        
        return {
            "outfit": outfit.model_dump(),
            "weather": weather_info.model_dump() if weather_info else None,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get daily outfit: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get outfit: {str(e)}")


@router.post("/recommendations")
async def get_recommendations(
    request: OutfitRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get multiple outfit recommendations.
    
    Args:
        request: OutfitRequest with optional occasion and limit
        user: Authenticated user from token
    
    Returns:
        List of outfit suggestions
    """
    user_id = user["uid"]
    logger.info(f"Getting {request.limit} recommendations for user: {user_id}")
    
    try:
        # Get user profile
        profile = await firestore.get_user_profile(user_id)
        
        # Get weather if enabled
        weather = None
        if request.include_weather and profile and profile.location:
            weather = await weather_service.get_weather_by_coords(
                profile.location.lat,
                profile.location.lon
            )
        
        # Get recommendations
        outfits = await recommendation_engine.get_recommendations(
            user_profile=profile,
            weather=weather,
            occasion=request.occasion,
            limit=request.limit
        )
        
        return {
            "outfits": [o.model_dump() for o in outfits],
            "weather": weather.model_dump() if weather else None,
            "count": len(outfits),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.get("/recommendations/{outfit_id}/reasoning")
async def get_outfit_reasoning(outfit_id: str):
    """
    Get AI-generated reasoning for why an outfit works.
    
    Args:
        outfit_id: Outfit suggestion ID
    
    Returns:
        OutfitReasoning with detailed explanations
    """
    # Note: This would require storing outfits temporarily or regenerating
    # For MVP, reasoning is included in the daily-outfit response
    raise HTTPException(
        status_code=501,
        detail="Reasoning is included in the daily-outfit response"
    )


@router.get("/weather")
async def get_current_weather(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get current weather for the user's location.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        Weather info and clothing recommendations
    """
    try:
        user_id = user["uid"]
        profile = await firestore.get_user_profile(user_id)
        
        if not profile or not profile.location:
            return {
                "weather": None,
                "status": "no_location",
                "message": "Set your location in profile to get weather"
            }
        
        weather = await weather_service.get_weather_by_coords(
            profile.location.lat,
            profile.location.lon
        )
        
        if not weather:
            return {
                "weather": None,
                "status": "weather_unavailable",
                "message": "Could not fetch weather data"
            }
        
        # Get clothing recommendations for this weather
        clothing_recs = weather_service.get_clothing_recommendation(weather)
        
        return {
            "weather": weather.model_dump(),
            "clothing_recommendations": clothing_recs,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get weather: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weather/forecast")
async def get_day_forecast(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get weather forecast for different times of day (morning, noon, evening, night).
    
    Args:
        user: Authenticated user from token
    
    Returns:
        List of forecasts with temperature, condition, and icon for each time period
    """
    try:
        user_id = user["uid"]
        profile = await firestore.get_user_profile(user_id)
        
        if not profile or not profile.location:
            return {
                "forecast": None,
                "status": "no_location",
                "message": "Set your location in profile to get forecast"
            }
        
        forecast = await weather_service.get_day_forecast(
            profile.location.lat,
            profile.location.lon
        )
        
        if not forecast:
            return {
                "forecast": None,
                "status": "forecast_unavailable",
                "message": "Could not fetch forecast data"
            }
        
        return {
            "forecast": forecast,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get forecast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/garments/recommended")
async def get_recommended_garments(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, ge=1, le=50, description="Max results"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get garments sorted by recommendation score.
    
    Args:
        category: Optional category filter
        limit: Maximum number of results
        user: Authenticated user from token
    
    Returns:
        List of garments with recommendation scores
    """
    try:
        user_id = user["uid"]
        profile = await firestore.get_user_profile(user_id)
        garments = await firestore.list_garments_metadata(user_id=user_id, category=category, limit=limit)
        
        if not garments:
            return {
                "garments": [],
                "count": 0,
                "status": "empty"
            }
        
        # Sort by overall recommendation score
        garments.sort(
            key=lambda g: g.recommendation_scores.overall if g.recommendation_scores else 0,
            reverse=True
        )
        
        return {
            "garments": [g.model_dump() for g in garments[:limit]],
            "count": len(garments),
            "has_profile": profile is not None,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get recommended garments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# Daily Looks Endpoints (Pre-generated Try-On Recommendations)
# =========================================================================

@router.get("/daily-looks")
async def get_daily_looks_endpoint(
    date_str: Optional[str] = Query(None, description="Date in YYYY-MM-DD format (defaults to today)"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get pre-generated daily looks for a specific date.
    
    These are outfit recommendations with pre-rendered try-on images,
    generated by the daily background job.
    
    Args:
        date_str: Optional date (defaults to today)
        user: Authenticated user from token
    
    Returns:
        DailyLooks with 3 pre-rendered outfit looks
    """
    try:
        user_id = user["uid"]
        if date_str is None:
            date_str = date.today().isoformat()
        
        daily_looks = await firestore.get_daily_looks(user_id, date_str)
        
        if not daily_looks:
            return {
                "looks": None,
                "date": date_str,
                "status": "not_generated",
                "message": "Daily looks not generated yet. They are created automatically at 6 AM."
            }
        
        return {
            "looks": daily_looks.model_dump(),
            "date": date_str,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get daily looks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-looks/latest")
async def get_latest_daily_looks_endpoint(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Get the most recent pre-generated daily looks.
    
    Args:
        user: Authenticated user from token
    
    Returns:
        Most recent DailyLooks
    """
    try:
        user_id = user["uid"]
        daily_looks = await firestore.get_latest_daily_looks(user_id)
        
        if not daily_looks:
            return {
                "looks": None,
                "status": "not_generated",
                "message": "No daily looks generated yet."
            }
        
        return {
            "looks": daily_looks.model_dump(),
            "date": daily_looks.date,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get latest daily looks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-looks/history")
async def get_daily_looks_history(
    limit: int = Query(7, ge=1, le=30, description="Number of days to return"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get history of daily looks.
    
    Args:
        limit: Number of days to return (max 30)
        user: Authenticated user from token
    
    Returns:
        List of DailyLooks, most recent first
    """
    try:
        user_id = user["uid"]
        history = await firestore.list_daily_looks(user_id, limit=limit)
        
        return {
            "history": [dl.model_dump() for dl in history],
            "count": len(history),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get daily looks history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/daily-looks/generate")
async def trigger_daily_looks_generation(
    background_tasks: BackgroundTasks,
    force: bool = Query(False, description="Force regenerate even if today's looks exist"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Manually trigger daily looks generation.
    
    This is an admin/manual trigger for the daily job that normally
    runs at 6 AM via the scheduler.
    
    Args:
        force: If True, regenerate even if looks exist for today
        user: Authenticated user from token
    
    Returns:
        Status of the generation trigger
    """
    try:
        user_id = user["uid"]
        today = date.today().isoformat()
        
        # Check if already exists
        if not force:
            existing = await firestore.get_daily_looks(user_id, today)
            if existing:
                return {
                    "status": "already_exists",
                    "date": today,
                    "looks_count": len(existing.looks),
                    "message": "Daily looks already generated. Use force=true to regenerate."
                }
        
        # Trigger generation in background
        background_tasks.add_task(generate_daily_looks, user_id, 3)
        
        return {
            "status": "triggered",
            "date": today,
            "message": "Daily looks generation started in background"
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger daily looks generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status")
async def get_scheduler_status_endpoint():
    """
    Get status of the background scheduler.
    
    Returns:
        Scheduler status and list of jobs
    """
    try:
        status = get_job_status()
        return {
            "scheduler": status,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

