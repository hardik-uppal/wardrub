"""Background removal and ghost mannequin service using rembg and Gemini/Qwen."""

from io import BytesIO
from typing import List, Optional
from PIL import Image, ImageEnhance
from rembg import remove
import base64
import os
import tempfile

from app.config import get_settings, GEMINI_MODEL_TYPE

settings = get_settings()

# Image generation backend: "gemini" or "qwen"
# Set IMAGE_GEN_BACKEND=qwen to use self-hosted Qwen-Image-Edit-2511
IMAGE_GEN_BACKEND = os.getenv("IMAGE_GEN_BACKEND", "gemini").lower()

# Portrait dimensions for Qwen backend (768x1024 for mobile)
PORTRAIT_WIDTH = 768
PORTRAIT_HEIGHT = 1024

if IMAGE_GEN_BACKEND == "qwen":
    print(f"🎨 Ghost Mannequin Backend: Qwen-Image-Edit-2511 (self-hosted)")
    print(f"   Output: {PORTRAIT_WIDTH}x{PORTRAIT_HEIGHT} (portrait)")
else:
    print(f"🎨 Ghost Mannequin Model: {settings.GEMINI_MODEL} (type: {GEMINI_MODEL_TYPE})")


class BackgroundRemovalService:
    """Service for removing backgrounds and creating ghost mannequin effect."""
    
    async def remove_background(self, image_bytes: bytes) -> bytes:
        """
        Remove background from an image.
        
        Args:
            image_bytes: Input image bytes (any format)
        
        Returns:
            PNG image bytes with transparent background
        """
        input_image = Image.open(BytesIO(image_bytes))
        
        if input_image.mode != "RGBA":
            input_image = input_image.convert("RGBA")
        
        # Remove background using rembg
        output_image = remove(input_image)
        
        # Convert to bytes
        output_buffer = BytesIO()
        output_image.save(output_buffer, format="PNG", optimize=True)
        output_buffer.seek(0)
        
        return output_buffer.getvalue()
    
    async def create_ghost_mannequin(
        self, 
        front_image_bytes: bytes, 
        back_image_bytes: Optional[bytes] = None,
        category: str = "top"
    ) -> bytes:
        """
        Create ghost mannequin effect using Gemini or Qwen-Image-Edit.
        
        Backend selection via IMAGE_GEN_BACKEND env var:
        - "gemini": Use Gemini 2.5 Flash Image API
        - "qwen": Use self-hosted Qwen-Image-Edit service
        
        Args:
            front_image_bytes: Front view of garment (background removed)
            back_image_bytes: Optional back view of garment (background removed)
            category: Type of garment (top, bottom, dress, outerwear)
        
        Returns:
            PNG image bytes with ghost mannequin effect
        """
        # Use Qwen-Image-Edit if configured
        if IMAGE_GEN_BACKEND == "qwen":
            return await self._create_ghost_mannequin_qwen(
                front_image_bytes, back_image_bytes, category
            )
        
        # Default: Use Gemini
        return await self._create_ghost_mannequin_gemini(
            front_image_bytes, back_image_bytes, category
        )
    
    async def _create_ghost_mannequin_qwen(
        self,
        front_image_bytes: bytes,
        back_image_bytes: Optional[bytes] = None,
        category: str = "top"
    ) -> bytes:
        """Create ghost mannequin using self-hosted Qwen-Image-Edit-2511."""
        try:
            from app.services.qwen_image_edit import get_qwen_image_edit_service
            
            qwen_service = get_qwen_image_edit_service()
            
            result_bytes = await qwen_service.create_ghost_mannequin(
                front_image_bytes=front_image_bytes,
                back_image_bytes=back_image_bytes,
                category=category,
            )
            
            # Remove background from result for clean PNG
            result_image = Image.open(BytesIO(result_bytes))
            result_rgba = remove(result_image)
            
            # Resize to portrait dimensions (768x1024 for mobile)
            result_rgba = self._resize_to_portrait(result_rgba)
            
            output = BytesIO()
            result_rgba.save(output, format="PNG", optimize=True)
            output.seek(0)
            
            return output.getvalue()
            
        except Exception as e:
            print(f"❌ Qwen ghost mannequin failed: {e}")
            import traceback
            traceback.print_exc()
            return await self._enhance_and_resize(front_image_bytes)
    
    async def _create_ghost_mannequin_gemini(
        self,
        front_image_bytes: bytes,
        back_image_bytes: Optional[bytes] = None,
        category: str = "top"
    ) -> bytes:
        """Create ghost mannequin using Gemini 2.5 Flash Image (Nano Banana)."""
        try:
            from google import genai
            from google.genai import types
            
            # Initialize Gemini client with API key or default credentials
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            
            if api_key:
                client = genai.Client(api_key=api_key)
            else:
                # Use default credentials (service account)
                client = genai.Client(
                    vertexai=True,
                    project=settings.GOOGLE_CLOUD_PROJECT,
                    location=settings.VERTEX_AI_LOCATION
                )
            
            # Category-specific prompts for better results
            category_details = {
                "top": "t-shirt, shirt, blouse, or sweater",
                "bottom": "pants, jeans, shorts, or trousers", 
                "dress": "dress, gown, or skirt",
                "outerwear": "jacket, coat, hoodie, or blazer"
            }
            
            garment_type = category_details.get(category, "clothing item")
            
            # Build the prompt
            if back_image_bytes:
                prompt = f"""Transform these front and back photos of a {garment_type} into a professional ghost mannequin product image.

Create an e-commerce style photo where:
- The garment appears to be worn by an invisible mannequin
- Show natural 3D shape, depth and form
- Combine both front and back views seamlessly
- Pure clean white background
- Professional studio lighting with soft shadows
- The clothing floats naturally as if on an invisible body
- High-end fashion retail photography quality"""
            else:
                prompt = f"""Transform this {garment_type} photo into a professional ghost mannequin product image.

Create an e-commerce style photo where:
- The garment appears to be worn by an invisible mannequin  
- Show natural 3D shape, depth and form
- Pure clean white background
- Professional studio lighting with soft shadows
- The clothing floats naturally as if on an invisible body
- High-end fashion retail photography quality"""

            print(f"🎨 Sending to Gemini 2.5 Flash Image: {prompt[:80]}...")
            
            # Prepare image parts using inline data
            front_image = Image.open(BytesIO(front_image_bytes))
            
            # Convert to RGB with white background for better processing
            if front_image.mode == "RGBA":
                bg = Image.new("RGB", front_image.size, (255, 255, 255))
                bg.paste(front_image, mask=front_image.split()[3])
                front_image = bg
            
            # Save to PNG bytes
            front_buffer = BytesIO()
            front_image.save(front_buffer, format="PNG")
            front_bytes = front_buffer.getvalue()
            
            # Build content parts
            contents = [prompt]
            
            # Add front image as Part with inline data
            contents.append(types.Part.from_bytes(data=front_bytes, mime_type="image/png"))
            
            # Add back image if provided
            if back_image_bytes:
                back_image = Image.open(BytesIO(back_image_bytes))
                if back_image.mode == "RGBA":
                    bg = Image.new("RGB", back_image.size, (255, 255, 255))
                    bg.paste(back_image, mask=back_image.split()[3])
                    back_image = bg
                
                back_buffer = BytesIO()
                back_image.save(back_buffer, format="PNG")
                back_bytes = back_buffer.getvalue()
                
                contents.append("Back view:")
                contents.append(types.Part.from_bytes(data=back_bytes, mime_type="image/png"))
            
            # Generate using Gemini (native image generation)
            print(f"👔 Ghost mannequin using: {settings.GEMINI_MODEL}")
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],  # Enable image output
                )
            )
            
            # Extract generated image from response
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            # Check for inline image data
                            if hasattr(part, 'inline_data') and part.inline_data:
                                print("✅ Gemini returned an image!")
                                image_data = part.inline_data.data
                                
                                if isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data)
                                
                                # Process the returned image
                                result_image = Image.open(BytesIO(image_data))
                                
                                # Remove background for clean PNG
                                result_rgba = remove(result_image)
                                
                                # Resize to standard size
                                result_rgba = self._resize_to_square(result_rgba, settings.TARGET_IMAGE_SIZE)
                                
                                output = BytesIO()
                                result_rgba.save(output, format="PNG", optimize=True)
                                output.seek(0)
                                
                                print("✅ Ghost mannequin created successfully!")
                                return output.getvalue()
                            
                            # Log text responses for debugging
                            if hasattr(part, 'text') and part.text:
                                print(f"Gemini text response: {part.text[:200]}...")
            
            print("⚠️ Gemini didn't return an image, using enhanced original")
            return await self._enhance_and_resize(front_image_bytes)
            
        except Exception as e:
            print(f"❌ Ghost mannequin creation failed: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to enhanced original
            return await self._enhance_and_resize(front_image_bytes)
    
    async def _enhance_and_resize(self, image_bytes: bytes) -> bytes:
        """Apply enhancements and resize to standard size."""
        image = Image.open(BytesIO(image_bytes))
        
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        
        # Apply enhancements
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # Resize to square
        image = self._resize_to_square(image, settings.TARGET_IMAGE_SIZE)
        
        output = BytesIO()
        image.save(output, format="PNG", optimize=True)
        output.seek(0)
        return output.getvalue()
    
    def _resize_to_square(self, image: Image.Image, size: int) -> Image.Image:
        """
        Resize image to fit within a square canvas while maintaining aspect ratio.
        Centers the image on a transparent background.
        
        Args:
            image: Input PIL Image
            size: Target square size
        
        Returns:
            Resized image on square transparent canvas
        """
        # Calculate aspect-ratio-preserving size
        original_width, original_height = image.size
        ratio = min(size / original_width, size / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        # Resize with high-quality resampling
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create transparent canvas
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        
        # Center the resized image on canvas
        x_offset = (size - new_width) // 2
        y_offset = (size - new_height) // 2
        canvas.paste(resized, (x_offset, y_offset), resized)
        
        return canvas
    
    def _resize_to_portrait(self, image: Image.Image) -> Image.Image:
        """
        Resize image to fit within portrait canvas (768x1024) for mobile.
        Centers the image on a transparent background.
        
        Args:
            image: Input PIL Image
        
        Returns:
            Resized image on portrait transparent canvas
        """
        target_width = PORTRAIT_WIDTH
        target_height = PORTRAIT_HEIGHT
        
        # Calculate aspect-ratio-preserving size
        original_width, original_height = image.size
        ratio = min(target_width / original_width, target_height / original_height)
        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)
        
        # Resize with high-quality resampling
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create transparent canvas
        canvas = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
        
        # Center the resized image on canvas
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2
        canvas.paste(resized, (x_offset, y_offset), resized)
        
        return canvas
    
    async def validate_image(self, image_bytes: bytes) -> dict:
        """
        Validate an image for processing suitability.
        
        Args:
            image_bytes: Input image bytes
        
        Returns:
            Validation result with is_valid flag and any issues
        """
        issues = []
        
        try:
            image = Image.open(BytesIO(image_bytes))
            
            # Check dimensions
            width, height = image.size
            if width < 256 or height < 256:
                issues.append("Image too small. Minimum size is 256x256.")
            
            if width > 4096 or height > 4096:
                issues.append("Image too large. Maximum size is 4096x4096.")
            
            # Check format
            if image.format not in ["JPEG", "PNG", "WEBP", "GIF"]:
                issues.append(f"Unsupported format: {image.format}")
            
            # Basic brightness check (detect too dark images)
            if image.mode != "L":
                grayscale = image.convert("L")
            else:
                grayscale = image
            
            # Calculate average brightness
            pixels = list(grayscale.getdata())
            avg_brightness = sum(pixels) / len(pixels)
            
            if avg_brightness < 30:
                issues.append("Image appears too dark. Try better lighting.")
            elif avg_brightness > 240:
                issues.append("Image appears too bright or washed out.")
            
            return {
                "is_valid": len(issues) == 0,
                "issues": issues,
                "dimensions": {"width": width, "height": height},
                "format": image.format
            }
            
        except Exception as e:
            return {
                "is_valid": False,
                "issues": [f"Could not read image: {str(e)}"],
                "dimensions": None,
                "format": None
            }

