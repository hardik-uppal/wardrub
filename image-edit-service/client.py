"""
Client library for the Qwen-Image-Edit service.

Use this from the main wardrub backend to call the image edit service.

Example:
    from image_edit_client import ImageEditClient
    
    client = ImageEditClient("http://localhost:8001")
    
    # Create ghost mannequin
    result = await client.create_ghost_mannequin(
        image_bytes=garment_image_bytes,
        category="top"
    )
    
    if result["success"]:
        output_bytes = result["image_bytes"]
"""

import base64
import httpx
from typing import Optional, Literal
from io import BytesIO


GarmentCategory = Literal["top", "bottom", "dress", "outerwear"]


class ImageEditClient:
    """Client for the Qwen-Image-Edit service."""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        timeout: float = 120.0,  # 2 minutes for generation
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
    
    async def health_check(self) -> dict:
        """Check service health and GPU status."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/health")
            return response.json()
    
    async def create_ghost_mannequin(
        self,
        image_bytes: bytes,
        category: GarmentCategory = "top",
        custom_prompt: Optional[str] = None,
        steps: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> dict:
        """
        Create ghost mannequin effect from garment image.
        
        Args:
            image_bytes: Input image bytes
            category: Garment type (top, bottom, dress, outerwear)
            custom_prompt: Override default prompt
            steps: Inference steps (default: 8)
            seed: Random seed for reproducibility
            
        Returns:
            Dict with success, image_bytes (if success), error, processing_time_ms
        """
        files = {"image": ("image.png", image_bytes, "image/png")}
        data = {"category": category}
        
        if custom_prompt:
            data["custom_prompt"] = custom_prompt
        if steps:
            data["steps"] = steps
        if seed:
            data["seed"] = seed
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/ghost-mannequin",
                files=files,
                data=data,
            )
        
        result = response.json()
        
        # Decode base64 image if present
        if result.get("success") and result.get("image_base64"):
            result["image_bytes"] = base64.b64decode(result["image_base64"])
            del result["image_base64"]  # Remove to save memory
        
        return result
    
    async def edit_image(
        self,
        image_bytes: bytes,
        prompt: str,
        steps: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> dict:
        """
        Generic image editing with text prompt.
        
        Args:
            image_bytes: Input image bytes
            prompt: Edit instruction
            steps: Inference steps
            seed: Random seed
            
        Returns:
            Dict with success, image_bytes (if success), error
        """
        files = {"image": ("image.png", image_bytes, "image/png")}
        data = {"prompt": prompt}
        
        if steps:
            data["steps"] = steps
        if seed:
            data["seed"] = seed
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/edit",
                files=files,
                data=data,
            )
        
        result = response.json()
        
        if result.get("success") and result.get("image_base64"):
            result["image_bytes"] = base64.b64decode(result["image_base64"])
            del result["image_base64"]
        
        return result
    
    async def virtual_try_on(
        self,
        avatar_bytes: bytes,
        garment_bytes: bytes,
        category: GarmentCategory = "top",
        seed: Optional[int] = None,
    ) -> dict:
        """
        Virtual try-on - place garment on avatar.
        
        Args:
            avatar_bytes: Avatar/person image bytes
            garment_bytes: Garment image bytes
            category: Garment type
            seed: Random seed
            
        Returns:
            Dict with success, image_bytes (if success), error
        """
        files = {
            "avatar": ("avatar.png", avatar_bytes, "image/png"),
            "garment": ("garment.png", garment_bytes, "image/png"),
        }
        data = {"category": category}
        
        if seed:
            data["seed"] = seed
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/try-on",
                files=files,
                data=data,
            )
        
        result = response.json()
        
        if result.get("success") and result.get("image_base64"):
            result["image_bytes"] = base64.b64decode(result["image_base64"])
            del result["image_base64"]
        
        return result


# Synchronous wrapper for non-async contexts
class ImageEditClientSync:
    """Synchronous client wrapper."""
    
    def __init__(self, base_url: str = "http://localhost:8001", timeout: float = 120.0):
        self._async_client = ImageEditClient(base_url, timeout)
    
    def _run_async(self, coro):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    def health_check(self) -> dict:
        return self._run_async(self._async_client.health_check())
    
    def create_ghost_mannequin(self, **kwargs) -> dict:
        return self._run_async(self._async_client.create_ghost_mannequin(**kwargs))
    
    def edit_image(self, **kwargs) -> dict:
        return self._run_async(self._async_client.edit_image(**kwargs))
    
    def virtual_try_on(self, **kwargs) -> dict:
        return self._run_async(self._async_client.virtual_try_on(**kwargs))
