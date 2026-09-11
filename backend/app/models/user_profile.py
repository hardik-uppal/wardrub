"""User profile models for recommendation engine."""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, model_validator


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


class PhotoRequest(BaseModel):
    photo_type: Literal["face", "full_length"]
    reason: str
    instructions: str


class AnalysisStage(BaseModel):
    status: Literal["not_started", "needs_input", "ready", "failed"] = "not_started"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    evidence_assessment: str = ""
    requested_input: Optional[PhotoRequest] = None
    attempts: int = 0
    updated_at: Optional[datetime] = None
    result_updated_at: Optional[datetime] = None


class StyleAnalysisProgress(BaseModel):
    schema_version: int = 1
    color: AnalysisStage = Field(default_factory=AnalysisStage)
    fit: AnalysisStage = Field(default_factory=AnalysisStage)


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
    style_analysis: StyleAnalysisProgress = Field(default_factory=StyleAnalysisProgress)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="before")
    @classmethod
    def migrate_analysis_progress(cls, data):
        """Read older profiles without requiring an offline migration."""
        if isinstance(data, dict) and not data.get("style_analysis"):
            data = dict(data)
            quality = data.get("analysis_quality") or {}
            if isinstance(quality, AnalysisQuality):
                quality = quality.model_dump()
            progress = StyleAnalysisProgress()
            for name, result, confidence_key in (
                ("color", data.get("skin_tone"), "skin_tone_confidence"),
                ("fit", data.get("body_type"), "body_type_confidence"),
            ):
                if result:
                    setattr(progress, name, AnalysisStage(
                        status="ready",
                        confidence=quality.get(confidence_key, 0.0),
                        evidence_assessment="Existing profile result; re-analyze to refine it.",
                        result_updated_at=data.get("updated_at"),
                    ))
            data["style_analysis"] = progress
        return data
    
    class Config:
        use_enum_values = True


class UserProfileUpdate(BaseModel):
    """Partial update model for user profile."""
    style_preferences: Optional[List[str]] = None
    location: Optional[Location] = None
