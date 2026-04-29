"""Color analysis service using Gemini Vision."""

import json
from io import BytesIO
from typing import Optional, Dict, Any, List, Tuple

from PIL import Image

from app.config import get_settings
from app.logging_config import get_logger
from app.models.user_profile import SkinTone, Undertone, SkinDepth, ColorSeason
from app.models.garment import GarmentColors, ColorWarmth

settings = get_settings()
logger = get_logger("color_analysis")


class ColorAnalysisService:
    """Service for analyzing colors in images using Gemini Vision."""
    
    def __init__(self):
        """Initialize color analysis service."""
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
    
    async def analyze_skin_tone(
        self, 
        image_bytes: bytes
    ) -> Tuple[Optional[SkinTone], float]:
        """
        Analyze skin tone from avatar/selfie image.
        
        Args:
            image_bytes: Image bytes containing person's face/skin
        
        Returns:
            Tuple of (SkinTone, confidence_score)
        """
        from google.genai import types
        
        logger.info("Analyzing skin tone from image...")
        
        client = self._get_gemini_client()
        
        prompt = """Analyze this person's skin tone for fashion/color recommendations.

Provide a detailed analysis in JSON format:
{
    "undertone": "warm" | "cool" | "neutral",
    "depth": "fair" | "light" | "medium" | "tan" | "deep",
    "hex_approximation": "#XXXXXX",
    "season": "spring" | "summer" | "autumn" | "winter",
    "confidence": 0.0-1.0,
    "notes": "Brief explanation of the analysis"
}

Guidelines for seasonal color analysis:
- SPRING: Warm undertone + Light/Medium depth. Best with warm, bright colors (peach, coral, warm green)
- SUMMER: Cool undertone + Light/Medium depth. Best with soft, muted cool colors (lavender, powder blue, rose)
- AUTUMN: Warm undertone + Medium/Deep depth. Best with rich, warm colors (olive, rust, burgundy, mustard)
- WINTER: Cool undertone + Any depth with high contrast. Best with bold, cool colors (black, white, jewel tones)

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
                                
                                skin_tone = SkinTone(
                                    undertone=Undertone(data.get("undertone", "neutral")),
                                    depth=SkinDepth(data.get("depth", "medium")),
                                    hex_approximation=data.get("hex_approximation", "#D4A574"),
                                    season=ColorSeason(data.get("season", "autumn"))
                                )
                                confidence = data.get("confidence", 0.7)
                                
                                logger.info(f"Skin tone analyzed: {skin_tone.season} ({skin_tone.undertone}, {skin_tone.depth})")
                                return skin_tone, confidence
            
            logger.warning("Failed to get skin tone analysis from Gemini")
            return None, 0.0
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse skin tone response: {e}")
            return None, 0.0
        except Exception as e:
            logger.error(f"Skin tone analysis failed: {e}")
            return None, 0.0
    
    async def analyze_garment_colors(
        self,
        image_bytes: bytes,
        category: str = "top"
    ) -> Optional[GarmentColors]:
        """
        Analyze colors in a garment image.
        
        Args:
            image_bytes: Garment image bytes (ideally with background removed)
            category: Garment category for context
        
        Returns:
            GarmentColors or None
        """
        from google.genai import types
        
        logger.info(f"Analyzing garment colors for {category}...")
        
        client = self._get_gemini_client()
        
        prompt = f"""Analyze the colors of this {category} garment for fashion recommendations.

Provide a detailed color analysis in JSON format:
{{
    "dominant": "#XXXXXX",
    "secondary": ["#XXXXXX", "#XXXXXX"],
    "palette": ["color name 1", "color name 2"],
    "color_family": "blue" | "red" | "green" | "yellow" | "purple" | "orange" | "pink" | "brown" | "black" | "white" | "gray" | "navy" | "beige",
    "warmth": "warm" | "cool" | "neutral",
    "pattern": "solid" | "striped" | "plaid" | "floral" | "geometric" | "other",
    "notes": "Brief description of the color scheme"
}}

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
                                
                                colors = GarmentColors(
                                    dominant=data.get("dominant", "#000000"),
                                    secondary=data.get("secondary", []),
                                    palette=data.get("palette", []),
                                    color_family=data.get("color_family", ""),
                                    warmth=ColorWarmth(data.get("warmth", "neutral"))
                                )
                                
                                logger.info(f"Garment colors: {colors.dominant} ({colors.color_family})")
                                return colors
            
            logger.warning("Failed to get garment color analysis from Gemini")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse garment color response: {e}")
            return None
        except Exception as e:
            logger.error(f"Garment color analysis failed: {e}")
            return None
    
    def calculate_color_harmony(
        self,
        user_skin_tone: SkinTone,
        garment_colors: GarmentColors
    ) -> float:
        """
        Calculate color harmony score between user's skin tone and garment.
        
        Args:
            user_skin_tone: User's analyzed skin tone
            garment_colors: Garment's color analysis
        
        Returns:
            Harmony score 0.0-1.0
        """
        score = 0.5  # Base score
        
        # Undertone matching
        if user_skin_tone.undertone.value == "warm":
            if garment_colors.warmth.value == "warm":
                score += 0.25
            elif garment_colors.warmth.value == "neutral":
                score += 0.15
        elif user_skin_tone.undertone.value == "cool":
            if garment_colors.warmth.value == "cool":
                score += 0.25
            elif garment_colors.warmth.value == "neutral":
                score += 0.15
        else:  # Neutral undertone
            score += 0.20  # Neutral works with most
        
        # Seasonal color recommendations
        season = user_skin_tone.season.value
        color_family = garment_colors.color_family.lower()
        
        seasonal_good_colors = {
            "spring": ["coral", "peach", "warm green", "golden", "cream", "turquoise", "orange", "yellow"],
            "summer": ["lavender", "powder blue", "rose", "soft pink", "gray", "navy", "mauve", "plum"],
            "autumn": ["olive", "rust", "burgundy", "mustard", "brown", "orange", "teal", "gold"],
            "winter": ["black", "white", "navy", "red", "purple", "emerald", "fuchsia", "royal blue"]
        }
        
        if color_family in seasonal_good_colors.get(season, []):
            score += 0.25
        
        # Universal colors that work for most
        universal_colors = ["navy", "white", "gray", "black", "beige"]
        if color_family in universal_colors:
            score += 0.10
        
        return min(1.0, score)
    
    def get_color_recommendations(
        self,
        skin_tone: SkinTone
    ) -> Dict[str, List[str]]:
        """
        Get color recommendations based on skin tone.
        
        Args:
            skin_tone: User's skin tone analysis
        
        Returns:
            Dictionary with recommended and avoid colors
        """
        season = skin_tone.season.value
        
        recommendations = {
            "spring": {
                "best": ["Coral", "Peach", "Golden yellow", "Warm green", "Turquoise", "Cream"],
                "good": ["Warm red", "Orange", "Ivory", "Camel"],
                "avoid": ["Black", "Dark gray", "Burgundy", "Muted colors"]
            },
            "summer": {
                "best": ["Lavender", "Powder blue", "Rose pink", "Soft white", "Mauve", "Soft navy"],
                "good": ["Gray", "Plum", "Periwinkle", "Mint"],
                "avoid": ["Orange", "Gold", "Tomato red", "Black"]
            },
            "autumn": {
                "best": ["Rust", "Olive", "Burgundy", "Mustard", "Teal", "Burnt orange"],
                "good": ["Brown", "Gold", "Moss green", "Terracotta"],
                "avoid": ["Pastel pink", "Icy blue", "Pure white", "Black"]
            },
            "winter": {
                "best": ["Pure white", "Black", "Navy", "Emerald", "Royal blue", "Fuchsia"],
                "good": ["Burgundy", "Ice pink", "Charcoal", "Purple"],
                "avoid": ["Orange", "Gold", "Beige", "Muted earth tones"]
            }
        }
        
        return recommendations.get(season, recommendations["autumn"])

