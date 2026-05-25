"""Models for the personalized Magazine Feed feature."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SwapSuggestion(BaseModel):
    """An alternative garment suggested for a look card."""
    replace_item_id: str = Field(..., description="Garment ID to be replaced")
    with_item_id: str = Field(..., description="Alternative garment ID from user's closet")
    reason: str = Field(..., description="Why this replacement works")


class LookCard(BaseModel):
    """A styled look card in the editorial magazine feed."""
    id: str = Field(..., description="Unique look identifier")
    title: str = Field(..., description="Editorial style title (e.g. 'Soft Sunday Neutrals')")
    subtitle: Optional[str] = Field(None, description="Optional sub-header")
    section: str = Field(..., description="cover, daily, one_item_three_ways, underused")
    garment_ids: List[str] = Field(..., description="List of garment IDs in this outfit")
    hero_item_id: Optional[str] = Field(None, description="Featured garment in this look")
    occasion: Optional[str] = Field(None, description="Occasion name (e.g. Work, Brunch)")
    why_it_works: str = Field(..., description="AI editorial explanation of style cohesion")
    styling_tips: List[str] = Field(default_factory=list, description="List of styling tips")
    swaps: List[SwapSuggestion] = Field(default_factory=list, description="Alternative garments list")
    score: float = Field(..., description="Scoring match percentage (0.0 to 1.0)")
    tryon_image_url: Optional[str] = Field(None, description="Pre-rendered tryon image URL if ran")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class MagazineFeed(BaseModel):
    """Today's personalized magazine feed for a user."""
    user_id: str = Field(..., description="Owner ID")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    cover_look: LookCard = Field(..., description="The main featured look of the day")
    daily_fits: List[LookCard] = Field(default_factory=list, description="3 fits for the day")
    one_item_three_ways: List[LookCard] = Field(default_factory=list, description="3 fits styling one garment")
    underused_edit: LookCard = Field(..., description="Outfit showcasing a rarely worn garment")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LookFeedback(BaseModel):
    """User feedback on a look card."""
    id: str = Field(..., description="Feedback event unique ID")
    user_id: str = Field(..., description="User ID who left feedback")
    look_id: str = Field(..., description="Look card ID")
    action: str = Field(..., description="love, save, dislike, wore_this")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
