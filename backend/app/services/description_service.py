"""Garment description service using Gemini 2.0 Flash."""

import json
from io import BytesIO
from typing import Optional, Dict, Any, List

from PIL import Image

from app.config import get_settings
from app.logging_config import get_logger
from app.models.garment import (
    GarmentDescription, 
    FitType, 
    WeatherRange,
    GarmentCategory
)

settings = get_settings()
logger = get_logger("description_service")


class DescriptionService:
    """Service for generating rich garment descriptions using Gemini Vision."""
    
    def __init__(self):
        """Initialize description service."""
        self._client = None
    
    def _get_gemini_client(self):
        """Get configured Gemini client."""
        import os
        from google import genai
        
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        if api_key:
            return genai.Client(api_key=api_key)
        else:
            return genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.VERTEX_AI_LOCATION
            )
    
    async def analyze_garment_description(
        self,
        image_bytes: bytes,
        category: str
    ) -> Dict[str, Any]:
        """
        Analyze a garment image to generate rich descriptions.
        
        Args:
            image_bytes: Garment image bytes
            category: Garment category (top, bottom, dress, outerwear)
        
        Returns:
            Dictionary with description, fit_type, style_tags, 
            season_suitability, and weather_range
        """
        from google.genai import types
        
        logger.info(f"Generating description for {category} garment...")
        
        client = self._get_gemini_client()
        
        prompt = f"""Analyze this {category} garment image for a fashion recommendation system.

Provide a detailed analysis in JSON format:
{{
    "short": "1-2 sentence description (e.g., 'Classic navy blue cotton t-shirt with crew neck')",
    "detailed": "Full description including style, apparent material, pattern, notable features, and fit observations. 2-3 sentences.",
    "style_tags": ["array", "of", "style", "tags"],
    "fit_type": "fitted" | "regular" | "loose" | "oversized",
    "season_suitability": ["spring", "summer", "autumn", "winter"],
    "weather_range": {{
        "min_temp": 10,
        "max_temp": 25
    }}
}}

Guidelines:
- style_tags should include: formality (casual, smart-casual, formal, sporty), occasion (everyday, work, party, lounge), and style (classic, trendy, vintage, minimalist, bohemian, preppy, streetwear)
- fit_type: "fitted" (body-hugging), "regular" (standard fit), "loose" (relaxed), "oversized" (intentionally large)
- season_suitability: list all seasons this garment would be appropriate for
- weather_range: estimate min/max comfortable temperatures in Celsius based on apparent fabric weight and coverage

Return ONLY the JSON, no other text."""

        # Prepare image
        image = Image.open(BytesIO(image_bytes))
        if image.mode == "RGBA":
            bg = Image.new("RGB", image.size, (255, 255, 255))
            bg.paste(image, mask=image.split()[3])
            image = bg
        elif image.mode != "RGB":
            image = image.convert("RGB")
        
        img_buffer = BytesIO()
        image.save(img_buffer, format="PNG")
        img_bytes = img_buffer.getvalue()
        
        contents = [
            prompt,
            types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        ]
        
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
            )
            
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text.strip()
                                
                                # Clean JSON
                                if text.startswith("```json"):
                                    text = text[7:]
                                if text.startswith("```"):
                                    text = text[3:]
                                if text.endswith("```"):
                                    text = text[:-3]
                                text = text.strip()
                                
                                data = json.loads(text)
                                
                                # Validate and normalize fit_type
                                fit_type_raw = data.get("fit_type", "regular").lower()
                                if fit_type_raw not in ["fitted", "regular", "loose", "oversized"]:
                                    fit_type_raw = "regular"
                                
                                # Normalize seasons
                                seasons = data.get("season_suitability", [])
                                valid_seasons = ["spring", "summer", "autumn", "winter"]
                                seasons = [s.lower() for s in seasons if s.lower() in valid_seasons]
                                if not seasons:
                                    seasons = ["spring", "autumn"]  # Default
                                
                                # Weather range defaults based on category
                                weather = data.get("weather_range", {})
                                category_defaults = {
                                    "top": {"min_temp": 15, "max_temp": 30},
                                    "bottom": {"min_temp": 10, "max_temp": 35},
                                    "dress": {"min_temp": 15, "max_temp": 28},
                                    "outerwear": {"min_temp": -5, "max_temp": 18}
                                }
                                defaults = category_defaults.get(category, {"min_temp": 10, "max_temp": 25})
                                
                                result = {
                                    "description": GarmentDescription(
                                        short=data.get("short", f"A {category} garment"),
                                        detailed=data.get("detailed", ""),
                                        style_tags=data.get("style_tags", ["casual"])
                                    ),
                                    "fit_type": FitType(fit_type_raw),
                                    "season_suitability": seasons,
                                    "weather_range": WeatherRange(
                                        min_temp=weather.get("min_temp", defaults["min_temp"]),
                                        max_temp=weather.get("max_temp", defaults["max_temp"])
                                    )
                                }
                                
                                logger.info(f"Description generated: {result['description'].short[:50]}...")
                                return result
            
            logger.warning("Failed to get description from Gemini")
            return self._get_default_description(category)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse description response: {e}")
            return self._get_default_description(category)
        except Exception as e:
            logger.error(f"Description analysis failed: {e}")
            return self._get_default_description(category)
    
    def _get_default_description(self, category: str) -> Dict[str, Any]:
        """Return default description when analysis fails."""
        category_defaults = {
            "top": {
                "short": "A top garment",
                "detailed": "A top garment suitable for various occasions.",
                "style_tags": ["casual"],
                "fit_type": "regular",
                "seasons": ["spring", "summer", "autumn"],
                "min_temp": 15,
                "max_temp": 30
            },
            "bottom": {
                "short": "A bottom garment",
                "detailed": "A bottom garment suitable for various occasions.",
                "style_tags": ["casual"],
                "fit_type": "regular",
                "seasons": ["spring", "summer", "autumn", "winter"],
                "min_temp": 10,
                "max_temp": 35
            },
            "dress": {
                "short": "A dress",
                "detailed": "A dress suitable for various occasions.",
                "style_tags": ["casual", "feminine"],
                "fit_type": "regular",
                "seasons": ["spring", "summer"],
                "min_temp": 18,
                "max_temp": 30
            },
            "outerwear": {
                "short": "An outerwear piece",
                "detailed": "An outerwear piece for cooler weather.",
                "style_tags": ["casual", "layering"],
                "fit_type": "regular",
                "seasons": ["autumn", "winter"],
                "min_temp": -5,
                "max_temp": 18
            }
        }
        
        defaults = category_defaults.get(category, category_defaults["top"])
        
        return {
            "description": GarmentDescription(
                short=defaults["short"],
                detailed=defaults["detailed"],
                style_tags=defaults["style_tags"]
            ),
            "fit_type": FitType(defaults["fit_type"]),
            "season_suitability": defaults["seasons"],
            "weather_range": WeatherRange(
                min_temp=defaults["min_temp"],
                max_temp=defaults["max_temp"]
            )
        }
    
    async def batch_analyze(
        self,
        garments: List[Dict[str, Any]],
        delay_seconds: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple garments with rate limiting.
        
        Args:
            garments: List of dicts with 'image_bytes' and 'category'
            delay_seconds: Delay between API calls to avoid rate limits
        
        Returns:
            List of analysis results
        """
        import asyncio
        
        results = []
        total = len(garments)
        
        for i, garment in enumerate(garments):
            logger.info(f"Processing garment {i+1}/{total}...")
            
            result = await self.analyze_garment_description(
                garment["image_bytes"],
                garment["category"]
            )
            results.append({
                "garment_id": garment.get("garment_id"),
                **result
            })
            
            # Rate limit
            if i < total - 1:
                await asyncio.sleep(delay_seconds)
        
        return results

