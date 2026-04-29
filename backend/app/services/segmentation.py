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
            
            # Step 2: Optionally refine with Replicate SAM
            if settings.REPLICATE_API_TOKEN:
                try:
                    refined_mask = await self._segment_with_replicate(foreground_bytes)
                    if refined_mask is not None:
                        mask_array = refined_mask
                        method = "rembg+replicate_sam"
                        logger.info("SAM refinement successful")
                except Exception as e:
                    logger.warning(f"SAM refinement failed, using rembg only: {e}")
            
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
    
    async def _segment_with_replicate(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Use Replicate's SAM API (serverless, pay-per-call).
        
        Args:
            image_bytes: Image bytes (ideally with background already removed)
        
        Returns:
            Mask array or None if failed
        """
        api_token = settings.REPLICATE_API_TOKEN
        if not api_token:
            return None
        
        logger.info("Calling Replicate SAM API...")
        
        # Convert to base64 data URL
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{image_b64}"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Start prediction using SAM model
            # Using facebook/sam-vit-huge for automatic mask generation
            response = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Token {api_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "version": "ee7c6e01f3d9fef96b9dfe9c4bfcf7e5d8e6c4a2b1d0e9f8a7b6c5d4e3f2a1b0",
                    "input": {
                        "image": data_url,
                        "multimask_output": False
                    }
                }
            )
            
            if response.status_code != 201:
                logger.error(f"Replicate API error: {response.status_code} - {response.text}")
                return None
            
            prediction = response.json()
            prediction_url = prediction.get("urls", {}).get("get")
            
            if not prediction_url:
                logger.error("No prediction URL returned")
                return None
            
            # Poll for result (max 60 seconds)
            for _ in range(60):
                await asyncio.sleep(1)
                
                status_response = await client.get(
                    prediction_url,
                    headers={"Authorization": f"Token {api_token}"}
                )
                prediction = status_response.json()
                status = prediction.get("status")
                
                if status == "succeeded":
                    output = prediction.get("output")
                    if output:
                        # Output is typically a URL to the mask image
                        if isinstance(output, str):
                            mask_url = output
                        elif isinstance(output, list) and len(output) > 0:
                            mask_url = output[0]
                        else:
                            logger.warning(f"Unexpected output format: {output}")
                            return None
                        
                        # Download mask
                        mask_response = await client.get(mask_url)
                        if mask_response.status_code == 200:
                            mask_image = Image.open(BytesIO(mask_response.content)).convert("L")
                            return np.array(mask_image)
                    return None
                
                elif status == "failed":
                    error = prediction.get("error", "Unknown error")
                    logger.error(f"Replicate prediction failed: {error}")
                    return None
                
                # Still processing, continue polling
            
            logger.warning("Replicate SAM timed out")
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

