"""User profile models for recommendation engine."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class Undertone(str, Enum):
    """Skin undertone classification."""
    WARM = "warm"
    COOL = "cool"
    NEUTRAL = "neutral"


class SkinDepth(str, Enum):
    """Skin depth/darkness level."""
    FAIR = "fair"
    LIGHT = "light"
    MEDIUM = "medium"
    TAN = "tan"
    DEEP = "deep"


class ColorSeason(str, Enum):
    """Seasonal color analysis type."""
    SPRING = "spring"  # Warm + Light
    SUMMER = "summer"  # Cool + Light
    AUTUMN = "autumn"  # Warm + Deep
    WINTER = "winter"  # Cool + Deep


class BodyType(str, Enum):
    """Body shape classification."""
    HOURGLASS = "hourglass"
    PEAR = "pear"
    APPLE = "apple"
    RECTANGLE = "rectangle"
    INVERTED_TRIANGLE = "inverted_triangle"


class ShoulderWidth(str, Enum):
    NARROW = "narrow"
    AVERAGE = "average"
    BROAD = "broad"


class TorsoLength(str, Enum):
    SHORT = "short"
    AVERAGE = "average"
    LONG = "long"


class SkinTone(BaseModel):
    """Skin tone analysis result."""
    undertone: Undertone = Field(..., description="Warm, cool, or neutral undertone")
    depth: SkinDepth = Field(..., description="Skin depth from fair to deep")
    hex_approximation: str = Field(..., description="Approximate hex color of skin")
    season: ColorSeason = Field(..., description="Seasonal color palette type")


class BodyMeasurementsEstimate(BaseModel):
    """Estimated body measurements from image analysis."""
    shoulder_width: ShoulderWidth = ShoulderWidth.AVERAGE
    torso_length: TorsoLength = TorsoLength.AVERAGE


class Location(BaseModel):
    """User location for weather-based recommendations."""
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    city: Optional[str] = Field(None, description="City name")


class AnalysisQuality(BaseModel):
    """Quality metrics for profile analysis."""
    skin_tone_confidence: float = Field(0.0, ge=0.0, le=1.0)
    body_type_confidence: float = Field(0.0, ge=0.0, le=1.0)
    needs_more_images: bool = Field(False, description="Whether more images would improve analysis")
    recommendation: Optional[str] = Field(None, description="Suggestion for better images")


class UserProfile(BaseModel):
    """Complete user profile for recommendations."""
    # Core analysis
    skin_tone: Optional[SkinTone] = None
    body_type: Optional[BodyType] = None
    body_measurements: Optional[BodyMeasurementsEstimate] = None
    
    # Preferences
    style_preferences: List[str] = Field(default_factory=list)
    
    # Location
    location: Optional[Location] = None
    
    # Source tracking
    source_images: List[str] = Field(default_factory=list, description="GCS URLs of source images")
    
    # Quality metrics
    analysis_quality: AnalysisQuality = Field(default_factory=AnalysisQuality)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class UserProfileUpdate(BaseModel):
    """Partial update model for user profile."""
    style_preferences: Optional[List[str]] = None
    location: Optional[Location] = None

