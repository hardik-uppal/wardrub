"""Pydantic models for the recommendation engine."""

from app.models.user_profile import (
    UserProfile,
    SkinTone,
    BodyType,
    AnalysisQuality,
    Location,
)
from app.models.garment import (
    GarmentMetadata,
    GarmentColors,
    GarmentDescription,
    GarmentVisibility,
    SourceImage,
    RecommendationScores,
)
from app.models.outfit import (
    OutfitSuggestion,
    WeatherInfo,
    OutfitReasoning,
)
from app.models.magazine_feed import (
    SwapSuggestion,
    LookCard,
    MagazineFeed,
    LookFeedback,
)

__all__ = [
    # User Profile
    "UserProfile",
    "SkinTone",
    "BodyType",
    "AnalysisQuality",
    "Location",
    # Garment
    "GarmentMetadata",
    "GarmentColors",
    "GarmentDescription",
    "GarmentVisibility",
    "SourceImage",
    "RecommendationScores",
    # Outfit
    "OutfitSuggestion",
    "WeatherInfo",
    "OutfitReasoning",
    # Magazine Feed
    "SwapSuggestion",
    "LookCard",
    "MagazineFeed",
    "LookFeedback",
]


