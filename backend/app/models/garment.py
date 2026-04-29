"""Garment metadata models for recommendation engine."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class GarmentCategory(str, Enum):
    """Clothing categories."""
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"


class FitType(str, Enum):
    """Garment fit classification."""
    FITTED = "fitted"
    REGULAR = "regular"
    LOOSE = "loose"
    OVERSIZED = "oversized"


class ColorWarmth(str, Enum):
    """Color temperature classification."""
    WARM = "warm"
    COOL = "cool"
    NEUTRAL = "neutral"


class VisibilityStatus(str, Enum):
    """Image visibility quality status."""
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    NEEDS_MORE = "needs_more"


class SourceImage(BaseModel):
    """Source image metadata."""
    url: str = Field(..., description="GCS URL of source image")
    view: str = Field("front", description="View type: front, back, detail")
    quality_score: float = Field(0.0, ge=0.0, le=1.0, description="Image quality score")


class GarmentColors(BaseModel):
    """Color analysis results for a garment."""
    dominant: str = Field(..., description="Dominant color hex code")
    secondary: List[str] = Field(default_factory=list, description="Secondary color hex codes")
    palette: List[str] = Field(default_factory=list, description="Color names in palette")
    color_family: str = Field("", description="Primary color family (blue, red, etc)")
    warmth: ColorWarmth = Field(ColorWarmth.NEUTRAL, description="Color temperature")
    
    class Config:
        use_enum_values = True


class GarmentDescription(BaseModel):
    """AI-generated description of garment."""
    short: str = Field("", description="Brief description")
    detailed: str = Field("", description="Detailed description")
    style_tags: List[str] = Field(default_factory=list, description="Style tags")


class GarmentVisibility(BaseModel):
    """Visibility assessment for garment image."""
    score: float = Field(0.0, ge=0.0, le=1.0, description="Visibility score (mask area ratio)")
    category_threshold: float = Field(0.6, description="Minimum threshold for this category")
    status: VisibilityStatus = Field(VisibilityStatus.NEEDS_MORE)
    
    class Config:
        use_enum_values = True


class WeatherRange(BaseModel):
    """Temperature range suitability."""
    min_temp: int = Field(0, description="Minimum comfortable temperature (Celsius)")
    max_temp: int = Field(40, description="Maximum comfortable temperature (Celsius)")


class RecommendationScores(BaseModel):
    """Pre-computed recommendation scores."""
    color_harmony_with_user: float = Field(0.0, ge=0.0, le=1.0)
    fit_recommendation: float = Field(0.0, ge=0.0, le=1.0)
    versatility: float = Field(0.0, ge=0.0, le=1.0)
    overall: float = Field(0.0, ge=0.0, le=1.0)


class GarmentMetadata(BaseModel):
    """Complete garment metadata for recommendations."""
    garment_id: str = Field(..., description="Unique garment identifier")
    user_id: str = Field(..., description="Owner user ID")
    category: GarmentCategory = Field(..., description="Garment category")
    
    # Source images (kept for reference/re-analysis)
    source_images: List[SourceImage] = Field(default_factory=list)
    
    # Processed outputs
    ghost_mannequin_url: Optional[str] = Field(None, description="Ghost mannequin image URL")
    mask_url: Optional[str] = Field(None, description="Segmentation mask URL")
    
    # Analysis results
    colors: Optional[GarmentColors] = None
    description: Optional[GarmentDescription] = None
    fit_type: Optional[FitType] = None
    
    # Weather/season
    season_suitability: List[str] = Field(default_factory=list)
    weather_range: WeatherRange = Field(default_factory=WeatherRange)
    
    # Quality assessment
    visibility: GarmentVisibility = Field(default_factory=GarmentVisibility)
    
    # Recommendation scores
    recommendation_scores: RecommendationScores = Field(default_factory=RecommendationScores)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


# Visibility thresholds by category
VISIBILITY_THRESHOLDS = {
    GarmentCategory.TOP: 0.60,
    GarmentCategory.BOTTOM: 0.50,
    GarmentCategory.DRESS: 0.65,
    GarmentCategory.OUTERWEAR: 0.55,
}

