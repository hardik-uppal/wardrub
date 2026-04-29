"""Daily looks models for pre-generated outfit recommendations."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class OutfitItem(BaseModel):
    """A single garment in an outfit."""
    garment_id: str = Field(..., description="Unique garment identifier")
    category: str = Field(..., description="Garment category")
    image_url: str = Field(..., description="URL of garment image")
    description: Optional[str] = Field(None, description="Short description of garment")


class DailyLook(BaseModel):
    """A single pre-generated outfit look."""
    id: str = Field(..., description="Unique look identifier")
    outfit_items: List[OutfitItem] = Field(..., description="Garments in this outfit")
    tryon_image_url: str = Field(..., description="Pre-rendered try-on image URL")
    score: float = Field(..., ge=0.0, le=1.0, description="Overall recommendation score")
    reasoning: str = Field(..., description="Why this outfit was recommended")
    weather_context: str = Field(..., description="Weather info used (e.g., '15°C, Cloudy in London')")
    color_harmony_notes: str = Field("", description="Notes about color matching")
    style_notes: Optional[str] = Field(None, description="Additional style tips")


class DailyLooks(BaseModel):
    """Collection of daily outfit recommendations."""
    user_id: str = Field(..., description="User identifier")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    looks: List[DailyLook] = Field(default_factory=list, description="List of recommended outfits")
    weather_summary: Optional[str] = Field(None, description="Weather summary for the day")
    location: Optional[str] = Field(None, description="Location used for weather")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="When looks were generated")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ScoredOutfit(BaseModel):
    """An outfit with scoring breakdown (used internally)."""
    garment_ids: List[str] = Field(..., description="List of garment IDs in outfit")
    items: List[OutfitItem] = Field(..., description="Full garment items")
    
    # Scoring breakdown
    weather_score: float = Field(0.0, ge=0.0, le=1.0)
    color_harmony_score: float = Field(0.0, ge=0.0, le=1.0)
    style_cohesion_score: float = Field(0.0, ge=0.0, le=1.0)
    versatility_score: float = Field(0.0, ge=0.0, le=1.0)
    overall_score: float = Field(0.0, ge=0.0, le=1.0)
    
    # Explanations
    weather_reasoning: str = Field("")
    color_reasoning: str = Field("")
    style_reasoning: str = Field("")

