"""Body type analysis service using Gemini Vision."""

import json
from io import BytesIO
from typing import Optional, Tuple, Dict, Any

from PIL import Image

from app.config import get_settings
from app.logging_config import get_logger
from app.models.user_profile import (
    BodyType,
    BodyMeasurementsEstimate,
    ShoulderWidth,
    TorsoLength,
)

settings = get_settings()
logger = get_logger("body_analysis")


class BodyAnalysisService:
    """Service for analyzing body type from images using Gemini Vision."""
    
    def __init__(self):
        """Initialize body analysis service."""
        pass
    
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
    
    async def analyze_body_type(
        self,
        image_bytes: bytes
    ) -> Tuple[Optional[BodyType], Optional[BodyMeasurementsEstimate], float]:
        """
        Analyze body type from full-body image.
        
        Args:
            image_bytes: Full-body image bytes
        
        Returns:
            Tuple of (BodyType, BodyMeasurementsEstimate, confidence)
        """
        from google.genai import types
        
        logger.info("Analyzing body type from image...")
        
        client = self._get_gemini_client()
        
        prompt = """Analyze this person's body type for fashion recommendations.

Body type classifications:
- HOURGLASS: Shoulders and hips roughly equal width, defined waist
- PEAR: Hips wider than shoulders, defined waist
- APPLE: Shoulders wider than hips, less defined waist, fuller midsection
- RECTANGLE: Shoulders, waist, and hips similar width
- INVERTED_TRIANGLE: Shoulders notably wider than hips

Provide analysis in JSON format:
{
    "body_type": "hourglass" | "pear" | "apple" | "rectangle" | "inverted_triangle",
    "shoulder_width": "narrow" | "average" | "broad",
    "torso_length": "short" | "average" | "long",
    "confidence": 0.0-1.0,
    "style_notes": "Brief notes on flattering styles for this body type"
}

Be respectful and focus on helping with fashion choices.
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
                                
                                body_type = BodyType(data.get("body_type", "rectangle"))
                                
                                measurements = BodyMeasurementsEstimate(
                                    shoulder_width=ShoulderWidth(data.get("shoulder_width", "average")),
                                    torso_length=TorsoLength(data.get("torso_length", "average"))
                                )
                                
                                confidence = data.get("confidence", 0.7)
                                
                                logger.info(f"Body type analyzed: {body_type} (confidence: {confidence})")
                                return body_type, measurements, confidence
            
            logger.warning("Failed to get body type analysis from Gemini")
            return None, None, 0.0
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse body type response: {e}")
            return None, None, 0.0
        except Exception as e:
            logger.error(f"Body type analysis failed: {e}")
            return None, None, 0.0
    
    def get_fit_recommendations(
        self,
        body_type: BodyType
    ) -> Dict[str, Any]:
        """
        Get fit recommendations based on body type.
        
        Args:
            body_type: User's body type
        
        Returns:
            Dictionary with fit recommendations
        """
        recommendations = {
            BodyType.HOURGLASS: {
                "tops": ["Fitted tops", "Wrap tops", "V-necks", "Belted styles"],
                "bottoms": ["High-waisted pants", "Fitted skirts", "Bootcut jeans"],
                "dresses": ["Wrap dresses", "Fit and flare", "Bodycon"],
                "avoid": ["Boxy shapes", "Oversized tops", "Low-rise pants"],
                "notes": "Emphasize your natural waist with fitted styles"
            },
            BodyType.PEAR: {
                "tops": ["Boat necks", "Off-shoulder", "Structured shoulders", "Bright colors on top"],
                "bottoms": ["A-line skirts", "Dark bottoms", "Bootcut pants"],
                "dresses": ["A-line dresses", "Empire waist", "Fit and flare"],
                "avoid": ["Tapered pants", "Pencil skirts", "Hip details"],
                "notes": "Balance proportions by adding volume on top"
            },
            BodyType.APPLE: {
                "tops": ["V-necks", "Empire waist", "Flowy tops", "Structured jackets"],
                "bottoms": ["Straight leg pants", "Bootcut jeans", "Mid-rise"],
                "dresses": ["Empire waist", "A-line", "Wrap dresses"],
                "avoid": ["Tight midsection", "Clingy fabrics", "High-waisted tight"],
                "notes": "Draw attention up with neckline details"
            },
            BodyType.RECTANGLE: {
                "tops": ["Peplum", "Ruffles", "Layered looks", "Belted styles"],
                "bottoms": ["Wide leg pants", "Pleated skirts", "Details on hips"],
                "dresses": ["Belted dresses", "Peplum", "Fit and flare"],
                "avoid": ["Shapeless clothes", "Boxy cuts"],
                "notes": "Create curves with strategic details and belting"
            },
            BodyType.INVERTED_TRIANGLE: {
                "tops": ["V-necks", "Scoop necks", "Raglan sleeves", "Dark colors on top"],
                "bottoms": ["Wide leg pants", "Flared skirts", "Bold patterns", "Bright colors"],
                "dresses": ["A-line", "Fit and flare from waist"],
                "avoid": ["Shoulder pads", "Boat necks", "Puffy sleeves"],
                "notes": "Balance by adding volume below the waist"
            }
        }
        
        return recommendations.get(body_type, recommendations[BodyType.RECTANGLE])
    
    def calculate_fit_score(
        self,
        body_type: BodyType,
        garment_fit: str,
        garment_category: str
    ) -> float:
        """
        Calculate fit score for a garment based on body type.
        
        Args:
            body_type: User's body type
            garment_fit: Garment fit type (fitted, regular, loose, oversized)
            garment_category: Garment category (top, bottom, dress, outerwear)
        
        Returns:
            Fit score 0.0-1.0
        """
        # Fit preferences by body type
        fit_preferences = {
            BodyType.HOURGLASS: {
                "top": {"fitted": 0.9, "regular": 0.7, "loose": 0.5, "oversized": 0.3},
                "bottom": {"fitted": 0.8, "regular": 0.8, "loose": 0.5, "oversized": 0.4},
                "dress": {"fitted": 0.9, "regular": 0.8, "loose": 0.5, "oversized": 0.3},
                "outerwear": {"fitted": 0.8, "regular": 0.7, "loose": 0.6, "oversized": 0.5}
            },
            BodyType.PEAR: {
                "top": {"fitted": 0.6, "regular": 0.8, "loose": 0.7, "oversized": 0.5},
                "bottom": {"fitted": 0.5, "regular": 0.7, "loose": 0.8, "oversized": 0.6},
                "dress": {"fitted": 0.5, "regular": 0.7, "loose": 0.8, "oversized": 0.6},
                "outerwear": {"fitted": 0.7, "regular": 0.8, "loose": 0.7, "oversized": 0.5}
            },
            BodyType.APPLE: {
                "top": {"fitted": 0.4, "regular": 0.7, "loose": 0.8, "oversized": 0.6},
                "bottom": {"fitted": 0.5, "regular": 0.8, "loose": 0.7, "oversized": 0.5},
                "dress": {"fitted": 0.4, "regular": 0.7, "loose": 0.8, "oversized": 0.6},
                "outerwear": {"fitted": 0.5, "regular": 0.7, "loose": 0.8, "oversized": 0.7}
            },
            BodyType.RECTANGLE: {
                "top": {"fitted": 0.7, "regular": 0.7, "loose": 0.6, "oversized": 0.5},
                "bottom": {"fitted": 0.6, "regular": 0.7, "loose": 0.7, "oversized": 0.6},
                "dress": {"fitted": 0.7, "regular": 0.7, "loose": 0.6, "oversized": 0.5},
                "outerwear": {"fitted": 0.7, "regular": 0.7, "loose": 0.7, "oversized": 0.6}
            },
            BodyType.INVERTED_TRIANGLE: {
                "top": {"fitted": 0.5, "regular": 0.7, "loose": 0.6, "oversized": 0.4},
                "bottom": {"fitted": 0.6, "regular": 0.7, "loose": 0.8, "oversized": 0.7},
                "dress": {"fitted": 0.5, "regular": 0.7, "loose": 0.8, "oversized": 0.6},
                "outerwear": {"fitted": 0.6, "regular": 0.7, "loose": 0.7, "oversized": 0.5}
            }
        }
        
        body_prefs = fit_preferences.get(body_type, fit_preferences[BodyType.RECTANGLE])
        category_prefs = body_prefs.get(garment_category, body_prefs.get("top", {}))
        
        return category_prefs.get(garment_fit, 0.6)

