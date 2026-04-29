"""Outfit suggestion models for recommendation engine."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class Occasion(str, Enum):
    """Outfit occasion types."""
    CASUAL = "casual"
    WORK = "work"
    DATE_NIGHT = "date_night"
    FORMAL = "formal"
    SPORTY = "sporty"
    WEEKEND = "weekend"


class WeatherCondition(str, Enum):
    """Weather condition types."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAINY = "rainy"
    SNOWY = "snowy"
    HOT = "hot"
    COLD = "cold"


class WeatherInfo(BaseModel):
    """Current weather information."""
    temperature: float = Field(..., description="Temperature in Celsius")
    feels_like: float = Field(..., description="Feels like temperature")
    condition: WeatherCondition = Field(..., description="Weather condition")
    description: str = Field("", description="Weather description")
    humidity: int = Field(0, description="Humidity percentage")
    city: str = Field("", description="City name")
    
    class Config:
        use_enum_values = True


class OutfitItem(BaseModel):
    """A single item in an outfit suggestion."""
    garment_id: str
    category: str
    url: str
    color_harmony_score: float = Field(0.0, ge=0.0, le=1.0)


class OutfitReasoning(BaseModel):
    """AI-generated reasoning for outfit recommendation."""
    summary: str = Field("", description="Brief summary of why this outfit works")
    color_analysis: str = Field("", description="How colors complement user's skin tone")
    fit_analysis: str = Field("", description="How fit works with body type")
    weather_suitability: str = Field("", description="Why it's appropriate for the weather")
    style_notes: str = Field("", description="Additional style tips")


class OutfitSuggestion(BaseModel):
    """Complete outfit suggestion."""
    id: str = Field(..., description="Unique suggestion ID")
    
    # Items in the outfit
    items: List[OutfitItem] = Field(default_factory=list)
    
    # Scores
    overall_score: float = Field(0.0, ge=0.0, le=1.0)
    color_harmony_score: float = Field(0.0, ge=0.0, le=1.0)
    weather_score: float = Field(0.0, ge=0.0, le=1.0)
    
    # Context
    occasion: Optional[Occasion] = None
    weather: Optional[WeatherInfo] = None
    
    # AI reasoning
    reasoning: Optional[OutfitReasoning] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class OutfitRequest(BaseModel):
    """Request for outfit suggestions."""
    occasion: Optional[Occasion] = None
    include_weather: bool = Field(True, description="Factor in current weather")
    limit: int = Field(5, ge=1, le=20, description="Number of suggestions")
    
    class Config:
        use_enum_values = True

