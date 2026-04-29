"""Recommendation engine for outfit suggestions."""

import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import get_settings
from app.logging_config import get_logger
from app.models.user_profile import UserProfile
from app.models.garment import GarmentMetadata, GarmentCategory
from app.models.outfit import (
    OutfitSuggestion,
    OutfitItem,
    OutfitReasoning,
    WeatherInfo,
    Occasion,
)
from app.services.firestore import FirestoreService
from app.services.weather import WeatherService
from app.services.color_analysis import ColorAnalysisService
from app.services.body_analysis import BodyAnalysisService

settings = get_settings()
logger = get_logger("recommendation")


class RecommendationEngine:
    """Engine for generating outfit recommendations."""
    
    def __init__(self):
        """Initialize recommendation engine."""
        self.firestore = FirestoreService()
        self.weather_service = WeatherService()
        self.color_service = ColorAnalysisService()
        self.body_service = BodyAnalysisService()
    
    async def get_recommendations(
        self,
        user_profile: Optional[UserProfile] = None,
        weather: Optional[WeatherInfo] = None,
        occasion: Optional[Occasion] = None,
        limit: int = 10
    ) -> List[OutfitSuggestion]:
        """
        Get outfit recommendations based on user profile, weather, and occasion.
        
        Args:
            user_profile: User's analyzed profile
            weather: Current weather info
            occasion: Outfit occasion
            limit: Maximum number of suggestions
        
        Returns:
            List of OutfitSuggestion objects
        """
        logger.info(f"Generating recommendations (weather: {weather is not None}, occasion: {occasion})")
        
        # Get user profile if not provided
        if user_profile is None:
            user_profile = await self.firestore.get_user_profile()
        
        # Get all garments with metadata
        garments = await self.firestore.list_garments_metadata()
        
        if not garments:
            logger.warning("No garments found for recommendations")
            return []
        
        # Score all garments
        scored_garments = await self._score_garments(
            garments, user_profile, weather
        )
        
        # Generate outfit combinations
        outfits = await self._generate_outfits(
            scored_garments, user_profile, weather, occasion, limit
        )
        
        return outfits
    
    async def _score_garments(
        self,
        garments: List[GarmentMetadata],
        user_profile: Optional[UserProfile],
        weather: Optional[WeatherInfo]
    ) -> List[Dict[str, Any]]:
        """Score each garment based on user profile and weather."""
        scored = []
        
        for garment in garments:
            score_data = {
                "garment": garment,
                "color_score": 0.5,
                "fit_score": 0.5,
                "weather_score": 0.5,
                "overall_score": 0.5
            }
            
            # Color harmony score
            if user_profile and user_profile.skin_tone and garment.colors:
                score_data["color_score"] = self.color_service.calculate_color_harmony(
                    user_profile.skin_tone,
                    garment.colors
                )
            
            # Fit score
            if user_profile and user_profile.body_type and garment.fit_type:
                score_data["fit_score"] = self.body_service.calculate_fit_score(
                    user_profile.body_type,
                    garment.fit_type,
                    garment.category
                )
            
            # Weather score
            if weather:
                score_data["weather_score"] = self._calculate_weather_score(
                    garment, weather
                )
            
            # Overall score (weighted average)
            score_data["overall_score"] = (
                score_data["color_score"] * 0.35 +
                score_data["fit_score"] * 0.25 +
                score_data["weather_score"] * 0.40
            )
            
            scored.append(score_data)
        
        # Sort by overall score
        scored.sort(key=lambda x: x["overall_score"], reverse=True)
        
        return scored
    
    def _calculate_weather_score(
        self,
        garment: GarmentMetadata,
        weather: WeatherInfo
    ) -> float:
        """Calculate weather suitability score."""
        temp = weather.feels_like
        weather_range = garment.weather_range
        
        # Check if temperature is in garment's range
        if weather_range.min_temp <= temp <= weather_range.max_temp:
            return 1.0
        
        # Calculate how far outside the range
        if temp < weather_range.min_temp:
            diff = weather_range.min_temp - temp
        else:
            diff = temp - weather_range.max_temp
        
        # Score decreases as temperature difference increases
        score = max(0.0, 1.0 - (diff / 20.0))
        
        return score
    
    async def _generate_outfits(
        self,
        scored_garments: List[Dict[str, Any]],
        user_profile: Optional[UserProfile],
        weather: Optional[WeatherInfo],
        occasion: Optional[Occasion],
        limit: int
    ) -> List[OutfitSuggestion]:
        """Generate complete outfit suggestions."""
        outfits = []
        
        # Group garments by category
        by_category = {
            GarmentCategory.TOP: [],
            GarmentCategory.BOTTOM: [],
            GarmentCategory.DRESS: [],
            GarmentCategory.OUTERWEAR: []
        }
        
        for item in scored_garments:
            category = GarmentCategory(item["garment"].category)
            by_category[category].append(item)
        
        # Generate outfit combinations
        
        # Option 1: Top + Bottom combinations
        for top_data in by_category[GarmentCategory.TOP][:5]:
            for bottom_data in by_category[GarmentCategory.BOTTOM][:5]:
                if len(outfits) >= limit:
                    break
                
                outfit = await self._create_outfit(
                    [top_data, bottom_data],
                    user_profile,
                    weather,
                    occasion
                )
                outfits.append(outfit)
        
        # Option 2: Dress combinations
        for dress_data in by_category[GarmentCategory.DRESS][:3]:
            if len(outfits) >= limit:
                break
            
            outfit = await self._create_outfit(
                [dress_data],
                user_profile,
                weather,
                occasion
            )
            outfits.append(outfit)
        
        # Add outerwear to top outfits if weather is cold
        if weather and weather.feels_like < 18:
            outerwear = by_category[GarmentCategory.OUTERWEAR][:2]
            for i, outfit in enumerate(outfits[:3]):
                if outerwear and i < len(outerwear):
                    outfit.items.append(OutfitItem(
                        garment_id=outerwear[i]["garment"].garment_id,
                        category=GarmentCategory.OUTERWEAR,
                        url=outerwear[i]["garment"].ghost_mannequin_url or "",
                        color_harmony_score=outerwear[i]["color_score"]
                    ))
        
        # Sort by overall score
        outfits.sort(key=lambda x: x.overall_score, reverse=True)
        
        return outfits[:limit]
    
    async def _create_outfit(
        self,
        garment_data_list: List[Dict[str, Any]],
        user_profile: Optional[UserProfile],
        weather: Optional[WeatherInfo],
        occasion: Optional[Occasion]
    ) -> OutfitSuggestion:
        """Create a single outfit suggestion."""
        items = []
        total_color_score = 0
        total_weather_score = 0
        
        for data in garment_data_list:
            garment = data["garment"]
            items.append(OutfitItem(
                garment_id=garment.garment_id,
                category=garment.category,
                url=garment.ghost_mannequin_url or "",
                color_harmony_score=data["color_score"]
            ))
            total_color_score += data["color_score"]
            total_weather_score += data["weather_score"]
        
        n = len(garment_data_list)
        avg_color = total_color_score / n if n > 0 else 0.5
        avg_weather = total_weather_score / n if n > 0 else 0.5
        
        # Calculate outfit color harmony (do colors work together?)
        outfit_harmony = self._calculate_outfit_color_harmony(garment_data_list)
        
        overall_score = (
            avg_color * 0.30 +
            outfit_harmony * 0.30 +
            avg_weather * 0.40
        )
        
        return OutfitSuggestion(
            id=str(uuid.uuid4()),
            items=items,
            overall_score=overall_score,
            color_harmony_score=outfit_harmony,
            weather_score=avg_weather,
            occasion=occasion,
            weather=weather,
            reasoning=None,  # Will be filled by Gemini if needed
            created_at=datetime.utcnow()
        )
    
    def _calculate_outfit_color_harmony(
        self,
        garment_data_list: List[Dict[str, Any]]
    ) -> float:
        """Calculate how well outfit colors work together."""
        if len(garment_data_list) < 2:
            return 0.8  # Single item is fine
        
        # Extract color warmth values
        warmths = []
        for data in garment_data_list:
            if data["garment"].colors:
                warmths.append(data["garment"].colors.warmth)
        
        if not warmths:
            return 0.6  # No color data
        
        # Check if warmths are consistent
        unique_warmths = set(warmths)
        
        if len(unique_warmths) == 1:
            return 0.9  # All same warmth - great harmony
        elif "neutral" in unique_warmths:
            return 0.8  # Neutral goes with anything
        else:
            return 0.5  # Mixed warm/cool - less ideal
    
    async def generate_outfit_reasoning(
        self,
        outfit: OutfitSuggestion,
        user_profile: Optional[UserProfile]
    ) -> OutfitReasoning:
        """
        Generate AI reasoning for why an outfit works.
        Uses Gemini to create explanations.
        """
        import json
        from google.genai import types
        
        logger.info(f"Generating reasoning for outfit {outfit.id}")
        
        client = self.color_service._get_gemini_client()
        
        # Build context
        items_desc = []
        for item in outfit.items:
            items_desc.append(f"- {item.category}: Color harmony score {item.color_harmony_score:.0%}")
        
        profile_desc = ""
        if user_profile:
            if user_profile.skin_tone:
                profile_desc = f"User has {user_profile.skin_tone.undertone} undertone, {user_profile.skin_tone.depth} skin depth, and is a {user_profile.skin_tone.season} season."
            if user_profile.body_type:
                profile_desc += f" Body type: {user_profile.body_type}."
        
        weather_desc = ""
        if outfit.weather:
            weather_desc = f"Current weather: {outfit.weather.temperature}°C, {outfit.weather.description} in {outfit.weather.city}."
        
        prompt = f"""Generate a brief, friendly explanation of why this outfit works for the user.

Outfit items:
{chr(10).join(items_desc)}

{profile_desc}

{weather_desc}

Overall harmony score: {outfit.overall_score:.0%}
Color harmony score: {outfit.color_harmony_score:.0%}

Provide reasoning in JSON format:
{{
    "summary": "One sentence summary (max 100 chars)",
    "color_analysis": "How colors work with user's skin tone (max 150 chars)",
    "fit_analysis": "How fit works with body type (max 150 chars)",
    "weather_suitability": "Why appropriate for weather (max 100 chars)",
    "style_notes": "Additional style tip (max 100 chars)"
}}

Be encouraging and helpful. Return ONLY JSON."""

        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt],
            )
            
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text.strip()
                                if text.startswith("```json"):
                                    text = text[7:]
                                if text.startswith("```"):
                                    text = text[3:]
                                if text.endswith("```"):
                                    text = text[:-3]
                                
                                data = json.loads(text.strip())
                                
                                return OutfitReasoning(
                                    summary=data.get("summary", ""),
                                    color_analysis=data.get("color_analysis", ""),
                                    fit_analysis=data.get("fit_analysis", ""),
                                    weather_suitability=data.get("weather_suitability", ""),
                                    style_notes=data.get("style_notes", "")
                                )
            
            return OutfitReasoning(summary="A well-coordinated outfit for you!")
            
        except Exception as e:
            logger.error(f"Failed to generate reasoning: {e}")
            return OutfitReasoning(summary="A well-coordinated outfit for you!")
    
    async def get_daily_outfit(
        self,
        user_profile: Optional[UserProfile] = None,
        use_weather: bool = True,
        occasion: Optional[Occasion] = None
    ) -> Optional[OutfitSuggestion]:
        """
        Get the top recommended outfit for today.
        
        Args:
            user_profile: User profile (fetched if not provided)
            use_weather: Whether to factor in weather
            occasion: Optional occasion filter
        
        Returns:
            Top OutfitSuggestion with reasoning
        """
        # Get profile if needed
        if user_profile is None:
            user_profile = await self.firestore.get_user_profile()
        
        # Get weather if enabled and profile has location
        weather = None
        if use_weather and user_profile and user_profile.location:
            weather = await self.weather_service.get_weather_by_coords(
                user_profile.location.lat,
                user_profile.location.lon
            )
        
        # Get recommendations
        outfits = await self.get_recommendations(
            user_profile=user_profile,
            weather=weather,
            occasion=occasion,
            limit=1
        )
        
        if not outfits:
            return None
        
        outfit = outfits[0]
        
        # Generate reasoning
        outfit.reasoning = await self.generate_outfit_reasoning(outfit, user_profile)
        
        return outfit

