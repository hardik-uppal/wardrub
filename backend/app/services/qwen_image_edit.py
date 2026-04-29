"""
Qwen-Image-Edit-2511 client for ghost mannequin generation.

This service calls the self-hosted Qwen-Image-Edit-2511 service
as a drop-in replacement for Gemini image generation.

Configure IMAGE_EDIT_SERVICE_URL in your environment.

Output: 768x1024 portrait images optimized for mobile.
"""

import base64
import os
import httpx
from io import BytesIO
from typing import Optional, Literal
from PIL import Image

from app.config import get_settings

settings = get_settings()

# Service URL - defaults to localhost:8001
IMAGE_EDIT_SERVICE_URL = os.getenv("IMAGE_EDIT_SERVICE_URL", "http://localhost:8001")

# Portrait output dimensions (matching image-edit-service)
PORTRAIT_WIDTH = 768
PORTRAIT_HEIGHT = 1024


GarmentCategory = Literal["top", "bottom", "dress", "outerwear"]


class QwenImageEditService:
    """
    Client for the self-hosted Qwen-Image-Edit service.
    
    Drop-in replacement for Gemini-based ghost mannequin generation.
    """
    
    def __init__(self, base_url: str = IMAGE_EDIT_SERVICE_URL, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        print(f"🎨 QwenImageEdit Service: {self.base_url}")
    
    async def health_check(self) -> dict:
        """Check if the image edit service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def create_ghost_mannequin(
        self,
        front_image_bytes: bytes,
        back_image_bytes: Optional[bytes] = None,
        category: str = "top",
    ) -> bytes:
        """
        Create ghost mannequin effect using Qwen-Image-Edit.
        
        This is a drop-in replacement for the Gemini-based method.
        
        Args:
            front_image_bytes: Front view of garment (background removed)
            back_image_bytes: Optional back view (currently not used by Qwen)
            category: Type of garment (top, bottom, dress, outerwear)
        
        Returns:
            PNG image bytes with ghost mannequin effect
        """
        print(f"🎨 Creating ghost mannequin via Qwen-Image-Edit...")
        print(f"   Service: {self.base_url}")
        print(f"   Category: {category}")
        
        # Map category
        category_map = {
            "top": "top",
            "bottom": "bottom", 
            "dress": "dress",
            "outerwear": "outerwear",
        }
        mapped_category = category_map.get(category, "top")
        
        # Prepare request
        files = {"image": ("image.png", front_image_bytes, "image/png")}
        data = {"category": mapped_category}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ghost-mannequin",
                    files=files,
                    data=data,
                )
            
            result = response.json()
            
            if result.get("success") and result.get("image_base64"):
                print(f"✅ Ghost mannequin created in {result.get('processing_time_ms', 0)}ms")
                return base64.b64decode(result["image_base64"])
            else:
                error = result.get("error", "Unknown error")
                print(f"❌ Ghost mannequin failed: {error}")
                # Fallback to enhanced original
                return await self._enhance_fallback(front_image_bytes)
                
        except httpx.TimeoutException:
            print("❌ Request timed out - service may be processing")
            return await self._enhance_fallback(front_image_bytes)
            
        except httpx.ConnectError:
            print(f"❌ Cannot connect to image edit service at {self.base_url}")
            return await self._enhance_fallback(front_image_bytes)
            
        except Exception as e:
            print(f"❌ Ghost mannequin error: {e}")
            return await self._enhance_fallback(front_image_bytes)
    
    async def edit_image(
        self,
        image_bytes: bytes,
        prompt: str,
    ) -> bytes:
        """
        Generic image editing with text prompt.
        
        Args:
            image_bytes: Input image bytes
            prompt: Edit instruction
            
        Returns:
            Edited image bytes
        """
        files = {"image": ("image.png", image_bytes, "image/png")}
        data = {"prompt": prompt}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/edit",
                    files=files,
                    data=data,
                )
            
            result = response.json()
            
            if result.get("success") and result.get("image_base64"):
                return base64.b64decode(result["image_base64"])
            else:
                print(f"❌ Image edit failed: {result.get('error')}")
                return image_bytes  # Return original
                
        except Exception as e:
            print(f"❌ Image edit error: {e}")
            return image_bytes
    
    async def _enhance_fallback(self, image_bytes: bytes) -> bytes:
        """Fallback enhancement when service fails."""
        from PIL import ImageEnhance
        
        print("⚠️ Using fallback enhancement...")
        
        image = Image.open(BytesIO(image_bytes))
        
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        # Basic enhancements
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # Resize to portrait dimensions (matching image-edit-service)
        image = self._resize_to_portrait(image)
        
        output = BytesIO()
        image.save(output, format="PNG", optimize=True)
        output.seek(0)
        return output.getvalue()
    
    def _resize_to_portrait(self, image: Image.Image) -> Image.Image:
        """Resize image to fit within portrait canvas (768x1024)."""
        target_width = PORTRAIT_WIDTH
        target_height = PORTRAIT_HEIGHT
        
        original_width, original_height = image.size
        ratio = min(target_width / original_width, target_height / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        canvas = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
        
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        canvas.paste(resized, (x_offset, y_offset), resized)
        
        return canvas


# Singleton instance
_qwen_service = None


def get_qwen_image_edit_service() -> QwenImageEditService:
    """Get or create the Qwen image edit service instance."""
    global _qwen_service
    if _qwen_service is None:
        _qwen_service = QwenImageEditService()
    return _qwen_service
