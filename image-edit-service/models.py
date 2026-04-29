"""Pydantic models for API requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class GarmentCategory(str, Enum):
    """Supported garment categories."""
    TOP = "top"
    BOTTOM = "bottom"
    DRESS = "dress"
    OUTERWEAR = "outerwear"


class GhostMannequinRequest(BaseModel):
    """Request for ghost mannequin generation."""
    category: GarmentCategory = Field(
        default=GarmentCategory.TOP,
        description="Type of garment for optimized prompting"
    )
    custom_prompt: Optional[str] = Field(
        default=None,
        description="Custom prompt (overrides category-based prompt)"
    )
    steps: Optional[int] = Field(
        default=None,
        ge=4, le=50,
        description="Inference steps (default: 8 with Lightning LoRA)"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducibility"
    )


class ImageEditRequest(BaseModel):
    """Generic image edit request."""
    prompt: str = Field(
        ...,
        description="Edit instruction (e.g., 'change background to white')"
    )
    steps: Optional[int] = Field(default=None, ge=4, le=50)
    seed: Optional[int] = Field(default=None)


class TryOnRequest(BaseModel):
    """Request for virtual try-on."""
    category: GarmentCategory = Field(default=GarmentCategory.TOP)
    preserve_face: bool = Field(default=True)
    seed: Optional[int] = Field(default=None)


class ImageResponse(BaseModel):
    """Response with generated image."""
    success: bool
    image_base64: Optional[str] = None
    error: Optional[str] = None
    processing_time_ms: int = 0
    seed_used: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    gpu_available: bool
    gpu_name: Optional[str] = None
    vram_used_gb: Optional[float] = None
    vram_total_gb: Optional[float] = None
    quantization: Optional[str] = None
