"""Image quality assessment service for garments and avatars."""

from io import BytesIO
from typing import Tuple, Optional, List, Dict, Any
import numpy as np
from PIL import Image

from app.logging_config import get_logger
from app.models.garment import (
    GarmentCategory,
    GarmentVisibility,
    VisibilityStatus,
    VISIBILITY_THRESHOLDS,
)

logger = get_logger("quality_assessment")


class QualityAssessmentService:
    """Service for assessing image quality and garment visibility."""
    
    def __init__(self):
        """Initialize quality assessment service."""
        pass
    
    async def assess_image_quality(
        self, 
        image_bytes: bytes
    ) -> Dict[str, Any]:
        """
        Assess basic image quality metrics.
        
        Args:
            image_bytes: Image bytes to assess
        
        Returns:
            Dictionary with quality metrics
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            
            # Basic metrics
            width, height = image.size
            aspect_ratio = width / height if height > 0 else 0
            
            # Convert to RGB for analysis
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Calculate brightness
            img_array = np.array(image)
            brightness = np.mean(img_array) / 255.0
            
            # Calculate contrast (standard deviation)
            contrast = np.std(img_array) / 255.0
            
            # Check if image is too dark or too bright
            is_too_dark = brightness < 0.2
            is_too_bright = brightness > 0.9
            is_low_contrast = contrast < 0.1
            
            # Resolution check
            min_dimension = min(width, height)
            is_low_resolution = min_dimension < 256
            
            # Overall quality score
            quality_score = 1.0
            issues = []
            
            if is_too_dark:
                quality_score -= 0.3
                issues.append("Image is too dark")
            if is_too_bright:
                quality_score -= 0.2
                issues.append("Image is overexposed")
            if is_low_contrast:
                quality_score -= 0.2
                issues.append("Image has low contrast")
            if is_low_resolution:
                quality_score -= 0.3
                issues.append("Image resolution is too low")
            
            quality_score = max(0.0, quality_score)
            
            return {
                "score": quality_score,
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
                "brightness": brightness,
                "contrast": contrast,
                "issues": issues,
                "is_acceptable": quality_score >= 0.5,
                "recommendation": self._get_quality_recommendation(issues) if issues else None
            }
        except Exception as e:
            logger.error(f"Failed to assess image quality: {e}")
            return {
                "score": 0.0,
                "issues": [f"Failed to process image: {str(e)}"],
                "is_acceptable": False,
                "recommendation": "Please upload a valid image file"
            }
    
    def _get_quality_recommendation(self, issues: List[str]) -> str:
        """Generate recommendation based on issues."""
        if "Image is too dark" in issues:
            return "Try taking the photo in better lighting"
        if "Image is overexposed" in issues:
            return "Avoid direct sunlight or flash"
        if "Image has low contrast" in issues:
            return "Use a contrasting background"
        if "Image resolution is too low" in issues:
            return "Use a higher resolution camera"
        return "Try taking a clearer photo"
    
    async def calculate_visibility_score(
        self,
        mask: np.ndarray,
        image_size: Tuple[int, int],
        category: GarmentCategory
    ) -> GarmentVisibility:
        """
        Calculate visibility score from segmentation mask.
        
        Args:
            mask: Binary segmentation mask (0/1 or 0/255)
            image_size: Original image (width, height)
            category: Garment category for threshold
        
        Returns:
            GarmentVisibility with score and status
        """
        try:
            # Normalize mask to binary
            if mask.max() > 1:
                mask = (mask > 127).astype(np.uint8)
            
            # Calculate mask area
            mask_area = np.sum(mask)
            total_area = image_size[0] * image_size[1]
            
            # Visibility score is the ratio of mask to total image
            visibility_score = mask_area / total_area if total_area > 0 else 0.0
            
            # Get threshold for this category
            threshold = VISIBILITY_THRESHOLDS.get(category, 0.5)
            
            # Determine status
            if visibility_score >= threshold * 1.2:
                status = VisibilityStatus.GOOD
            elif visibility_score >= threshold:
                status = VisibilityStatus.ACCEPTABLE
            else:
                status = VisibilityStatus.NEEDS_MORE
            
            logger.info(
                f"Visibility score for {category}: {visibility_score:.2%} "
                f"(threshold: {threshold:.0%}, status: {status})"
            )
            
            return GarmentVisibility(
                score=visibility_score,
                category_threshold=threshold,
                status=status
            )
        except Exception as e:
            logger.error(f"Failed to calculate visibility score: {e}")
            return GarmentVisibility(
                score=0.0,
                category_threshold=VISIBILITY_THRESHOLDS.get(category, 0.5),
                status=VisibilityStatus.NEEDS_MORE
            )
    
    async def needs_more_images(
        self,
        visibility_scores: List[GarmentVisibility]
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if more images are needed based on visibility scores.
        
        Args:
            visibility_scores: List of visibility scores from uploaded images
        
        Returns:
            Tuple of (needs_more, recommendation)
        """
        if not visibility_scores:
            return True, "Please upload at least one image"
        
        # Check if any image has good visibility
        has_good = any(v.status == VisibilityStatus.GOOD for v in visibility_scores)
        has_acceptable = any(v.status == VisibilityStatus.ACCEPTABLE for v in visibility_scores)
        
        if has_good:
            return False, None
        
        if has_acceptable:
            return False, "Consider adding a closer photo for better analysis"
        
        # All images have poor visibility
        avg_score = sum(v.score for v in visibility_scores) / len(visibility_scores)
        
        if avg_score < 0.1:
            return True, "The garment is barely visible. Please take a closer photo with the garment filling more of the frame"
        elif avg_score < 0.3:
            return True, "Please take a photo with the garment more clearly visible"
        else:
            return True, "Consider adding another angle for better analysis"
    
    async def select_best_images(
        self,
        images_with_scores: List[Dict[str, Any]],
        max_images: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Select the best images from a list based on quality and visibility.
        
        Args:
            images_with_scores: List of dicts with 'image_bytes', 'quality', 'visibility'
            max_images: Maximum images to select
        
        Returns:
            List of best images sorted by combined score
        """
        # Calculate combined score for each image
        scored_images = []
        for img_data in images_with_scores:
            quality_score = img_data.get("quality", {}).get("score", 0.5)
            visibility_score = img_data.get("visibility", GarmentVisibility()).score
            
            # Combined score: 40% quality, 60% visibility
            combined_score = (quality_score * 0.4) + (visibility_score * 0.6)
            
            scored_images.append({
                **img_data,
                "combined_score": combined_score
            })
        
        # Sort by combined score
        scored_images.sort(key=lambda x: x["combined_score"], reverse=True)
        
        # Return top images
        return scored_images[:max_images]

