"""Segmentation service using rembg + optional Replicate SAM."""

import asyncio
import base64
from io import BytesIO
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
from PIL import Image
import httpx

from app.config import get_settings
from app.logging_config import get_logger

settings = get_settings()
logger = get_logger("segmentation")


class SegmentationService:
    """Service for image segmentation using rembg + optional SAM refinement."""
    
    def __init__(self):
        """Initialize segmentation service."""
        pass
    
    async def segment_garment(
        self,
        image_bytes: bytes,
        category: str = "clothing"
    ) -> Tuple[Optional[np.ndarray], Dict[str, Any]]:
        """
        Segment garment from image.
        
        Flow:
        1. rembg removes background (foreground extraction)
        2. If Replicate API configured, refine mask with SAM
        3. Return mask + metadata
        
        Args:
            image_bytes: Input image bytes
            category: Garment category for prompt
        
        Returns:
            Tuple of (mask array, metadata dict)
        """
        logger.info(f"Segmenting {category} from image...")
        
        try:
            from rembg import remove
            
            # Step 1: Remove background with rembg
            input_image = Image.open(BytesIO(image_bytes))
            original_size = input_image.size
            
            foreground_bytes = remove(
                image_bytes,
                alpha_matting=True,
                alpha_matting_foreground_threshold=240,
                alpha_matting_background_threshold=10
            )
            
            foreground_image = Image.open(BytesIO(foreground_bytes))
            
            # Extract alpha channel as initial mask
            if foreground_image.mode == "RGBA":
                alpha = foreground_image.split()[3]
                mask_array = np.array(alpha)
            else:
                arr = np.array(foreground_image.convert("RGB"))
                mask_array = np.any(arr < 250, axis=2).astype(np.uint8) * 255
            
            method = "rembg"
            
            # Step 2: Optionally refine with Fal.ai Segmentation
            if settings.FAL_KEY:
                try:
                    refined_mask = await self._segment_with_fal(foreground_bytes)
                    if refined_mask is not None:
                        mask_array = refined_mask
                        method = "rembg+fal_sam"
                        logger.info("Fal.ai refinement successful")
                except Exception as e:
                    logger.warning(f"Fal.ai refinement failed, using rembg only: {e}")
            
            # Calculate mask statistics
            mask_area = np.sum(mask_array > 127)
            total_area = mask_array.shape[0] * mask_array.shape[1]
            coverage = mask_area / total_area if total_area > 0 else 0
            
            metadata = {
                "mask_area_pixels": int(mask_area),
                "total_area_pixels": int(total_area),
                "coverage_ratio": coverage,
                "original_size": original_size,
                "mask_size": mask_array.shape,
                "method": method
            }
            
            logger.info(f"Segmentation complete: {coverage:.1%} coverage ({method})")
            
            return mask_array, metadata
            
        except Exception as e:
            logger.error(f"Segmentation failed: {e}")
            return None, {"error": str(e)}
    
    async def _segment_with_fal(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Use Fal.ai's SAM/BiRefNet API (serverless, very cheap).
        
        Args:
            image_bytes: Image bytes
        
        Returns:
            Mask array or None if failed
        """
        api_token = settings.FAL_KEY
        if not api_token:
            return None
        
        logger.info("Calling Fal.ai Segmentation API...")
        
        # Convert to base64 data URL
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{image_b64}"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # We use BiRefNet for state-of-the-art background removal on Fal.ai
            # You can also change this to 'fal-ai/sam2/image' or SAM3 when needed
            endpoint = "https://fal.run/fal-ai/birefnet"
            
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Key {api_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "image_url": data_url
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Fal.ai API error: {response.status_code} - {response.text}")
                return None
            
            prediction = response.json()
            # Standard Fal.ai image output schema
            output_url = None
            if "image" in prediction and "url" in prediction["image"]:
                output_url = prediction["image"]["url"]
            elif "url" in prediction:
                output_url = prediction["url"]
            
            if not output_url:
                logger.error(f"No image URL in Fal.ai response: {prediction}")
                return None
                
            # Download mask/cutout
            mask_response = await client.get(output_url)
            if mask_response.status_code == 200:
                # Get the alpha channel of the returned cutout as the mask
                mask_image = Image.open(BytesIO(mask_response.content)).convert("RGBA")
                alpha = mask_image.split()[3]
                return np.array(alpha)
            
            return None
    
    async def extract_foreground(
        self,
        image_bytes: bytes,
        mask: Optional[np.ndarray] = None
    ) -> bytes:
        """
        Extract foreground from image using mask.
        
        Args:
            image_bytes: Input image bytes
            mask: Optional pre-computed mask
        
        Returns:
            PNG bytes with transparent background
        """
        try:
            if mask is None:
                # Use rembg directly
                from rembg import remove
                return remove(image_bytes)
            
            # Apply mask to image
            image = Image.open(BytesIO(image_bytes)).convert("RGBA")
            
            # Normalize mask to 0-255
            if mask.max() <= 1:
                mask = (mask * 255).astype(np.uint8)
            
            # Resize mask if needed
            if mask.shape[:2] != (image.height, image.width):
                mask_image = Image.fromarray(mask)
                mask_image = mask_image.resize((image.width, image.height), Image.LANCZOS)
                mask = np.array(mask_image)
            
            # Apply mask as alpha
            r, g, b, a = image.split()
            mask_pil = Image.fromarray(mask)
            
            # Combine original alpha with mask
            combined_alpha = Image.fromarray(
                np.minimum(np.array(a), mask).astype(np.uint8)
            )
            
            result = Image.merge("RGBA", (r, g, b, combined_alpha))
            
            # Save to bytes
            output = BytesIO()
            result.save(output, format="PNG")
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Foreground extraction failed: {e}")
            # Fallback to rembg
            from rembg import remove
            return remove(image_bytes)
    
    async def get_bounding_box(
        self,
        mask: np.ndarray
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Get bounding box from mask.
        
        Args:
            mask: Binary mask array
        
        Returns:
            Tuple of (x1, y1, x2, y2) or None if no mask
        """
        try:
            # Find non-zero pixels
            if mask.max() <= 1:
                mask = (mask * 255).astype(np.uint8)
            
            rows = np.any(mask > 127, axis=1)
            cols = np.any(mask > 127, axis=0)
            
            if not np.any(rows) or not np.any(cols):
                return None
            
            y1, y2 = np.where(rows)[0][[0, -1]]
            x1, x2 = np.where(cols)[0][[0, -1]]
            
            return (int(x1), int(y1), int(x2), int(y2))
            
        except Exception as e:
            logger.error(f"Failed to get bounding box: {e}")
            return None

