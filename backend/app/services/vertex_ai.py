"""Vertex AI service for avatar generation and virtual try-on."""

import base64
import os
from io import BytesIO
from typing import List

from PIL import Image
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel, Image as VertexImage

from app.config import get_settings, GEMINI_MODEL_TYPE
from app.logging_config import get_logger

settings = get_settings()
logger = get_logger("vertex_ai")

# Log which model we're using
logger.info(f"🤖 Gemini Model: {settings.GEMINI_MODEL} (type: {GEMINI_MODEL_TYPE})")


class VertexAIService:
    """Service for Vertex AI image generation and virtual try-on."""
    
    def __init__(self):
        """Initialize Vertex AI client."""
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure Vertex AI is initialized."""
        if not self._initialized:
            vertexai.init(
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.VERTEX_AI_LOCATION
            )
            self._initialized = True
    
    def _get_gemini_client(self):
        """Get configured Gemini client."""
        from google import genai
        
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        if api_key:
            return genai.Client(api_key=api_key)
        else:
            return genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.VERTEX_AI_LOCATION
            )
    
    def _fix_image_orientation(self, image: Image.Image) -> Image.Image:
        """Fix EXIF orientation for phone camera images."""
        from PIL import ImageOps
        try:
            return ImageOps.exif_transpose(image)
        except Exception:
            return image
    
    async def process_uploaded_avatar(self, image_bytes: bytes) -> bytes:
        """
        Process an uploaded full-body photo into a clean avatar using Gemini.
        
        Args:
            image_bytes: Full body photo bytes
        
        Returns:
            Processed avatar image bytes
        """
        from google.genai import types
        from PIL import ImageOps
        
        logger.info("📷 Processing uploaded full-body photo into avatar...")
        
        # Fix orientation first
        image = Image.open(BytesIO(image_bytes))
        image = self._fix_image_orientation(image)
        
        # Convert to RGB and get bytes
        if image.mode == "RGBA":
            bg = Image.new("RGB", image.size, (255, 255, 255))
            bg.paste(image, mask=image.split()[3])
            image = bg
        elif image.mode != "RGB":
            image = image.convert("RGB")
        
        # Save fixed image to bytes
        img_buffer = BytesIO()
        image.save(img_buffer, format="PNG")
        fixed_bytes = img_buffer.getvalue()
        
        logger.info(f"📐 Input image size: {image.size}")
        
        client = self._get_gemini_client()
        
        # Prompt to create avatar with neutral clothes and pose
        prompt = """Create a full-body avatar from this person's photo.

CRITICAL INSTRUCTIONS:
1. PRESERVE THE EXACT FACE - same facial features, skin tone, hair style and color
2. CHANGE THE CLOTHING to simple neutral outfit:
   - Plain white t-shirt or simple gray top
   - Blue jeans or neutral colored pants
   - Simple white sneakers or bare feet
3. PUT THEM IN A NEUTRAL STANDING POSE:
   - Standing straight, facing forward
   - Arms relaxed at sides or slightly away from body
   - Feet shoulder-width apart
   - Natural, relaxed posture
4. BACKGROUND: Clean white or light gray gradient
5. FULL BODY: Show from head to feet
6. LIGHTING: Soft, even studio lighting
7. STYLE: Professional fashion model pose for virtual try-on

The avatar should look like a mannequin/model version of this person - same face and body type, but in neutral clothes ready for virtual try-on.

Generate the full-body avatar image."""

        logger.info(f"🎨 Creating avatar using: {settings.GEMINI_MODEL}")
        
        contents = [
            prompt,
            types.Part.from_bytes(data=fixed_bytes, mime_type="image/png")
        ]
        
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
            )
            
            # Extract generated image
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                logger.info("✅ Gemini generated avatar from uploaded photo!")
                                image_data = part.inline_data.data
                                
                                if isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data)
                                
                                # Log result size
                                result = Image.open(BytesIO(image_data))
                                logger.info(f"📐 Output avatar size: {result.size}")
                                
                                return image_data
                            
                            if hasattr(part, 'text') and part.text:
                                logger.debug(f"Gemini text: {part.text[:200]}...")
            
            # Fallback - return enhanced original
            logger.warning("⚠️ Gemini didn't generate image, using enhanced original")
            return self._enhance_uploaded_image(fixed_bytes)
            
        except Exception as e:
            logger.error(f"❌ Avatar processing failed: {e}", exc_info=True)
            return self._enhance_uploaded_image(fixed_bytes)
    
    def _enhance_uploaded_image(self, image_bytes: bytes) -> bytes:
        """Fallback: enhance image without AI processing."""
        from PIL import ImageEnhance
        
        logger.info("🔧 Applying fallback enhancement...")
        
        image = Image.open(BytesIO(image_bytes))
        
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Light enhancement
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.05)
        
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.02)
        
        output = BytesIO()
        image.save(output, format="PNG", optimize=True)
        output.seek(0)
        return output.getvalue()
    
    async def create_avatar_from_selfie(self, selfie_bytes: bytes) -> bytes:
        """
        Create avatar by face-swapping selfie onto a default avatar body.
        
        Args:
            selfie_bytes: Selfie image bytes
        
        Returns:
            Avatar with user's face on default body
        """
        from google.genai import types
        
        logger.info("🤳 Creating avatar from selfie (face swap mode)...")
        
        client = self._get_gemini_client()
        
        # Load and fix selfie orientation
        selfie = Image.open(BytesIO(selfie_bytes))
        selfie = self._fix_image_orientation(selfie)
        
        logger.info(f"📐 Selfie size: {selfie.size}")
        
        # Convert to RGB
        if selfie.mode == "RGBA":
            bg = Image.new("RGB", selfie.size, (255, 255, 255))
            bg.paste(selfie, mask=selfie.split()[3])
            selfie = bg
        elif selfie.mode != "RGB":
            selfie = selfie.convert("RGB")
        
        # Save selfie to bytes
        selfie_buffer = BytesIO()
        selfie.save(selfie_buffer, format="PNG")
        selfie_png = selfie_buffer.getvalue()
        
        # Prompt for creating avatar from selfie
        prompt = """Create a full-body avatar using this person's face from the selfie.

CRITICAL INSTRUCTIONS:
1. EXTRACT THE FACE from this selfie - preserve exact facial features, skin tone, hair
2. CREATE A FULL BODY with natural proportions matching the face
3. CLOTHING: Simple neutral outfit
   - Plain white t-shirt or gray top
   - Blue jeans or neutral pants
   - Simple sneakers or bare feet
4. POSE: Neutral standing position
   - Standing straight, facing forward
   - Arms relaxed at sides
   - Natural, relaxed posture
5. BACKGROUND: Clean white or light gray gradient
6. FULL BODY: Head to feet visible
7. STYLE: Fashion model pose for virtual try-on

The avatar should be a full-body representation of this person based on their face - ready for virtual clothes try-on.

Generate the full-body avatar image."""

        logger.info(f"🎨 Face swap using model: {settings.GEMINI_MODEL}")
        
        contents = [
            prompt,
            types.Part.from_bytes(data=selfie_png, mime_type="image/png")
        ]
        
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
            )
            
            # Extract generated image
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                logger.info("✅ Face swap avatar generated successfully!")
                                image_data = part.inline_data.data
                                
                                if isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data)
                                
                                # Log result size
                                result = Image.open(BytesIO(image_data))
                                logger.info(f"📐 Generated avatar size: {result.size}")
                                
                                return image_data
                            
                            if hasattr(part, 'text') and part.text:
                                logger.debug(f"Gemini response text: {part.text[:100]}...")
            
            # Fallback - return enhanced selfie
            logger.warning("⚠️ Face swap didn't return image, using enhanced selfie as fallback")
            return self._enhance_uploaded_image(selfie_bytes)
            
        except Exception as e:
            logger.error(f"❌ Face swap failed: {e}", exc_info=True)
            return self._enhance_uploaded_image(selfie_bytes)
    
    # Keep old method for backwards compatibility
    async def generate_avatar(self, selfie_bytes_list: List[bytes]) -> bytes:
        """
        Generate a full-body avatar from a frontal selfie using Gemini native image generation.
        
        Args:
            selfie_bytes_list: List containing 1 selfie image bytes
        
        Returns:
            Generated avatar image bytes
        """
        try:
            from google import genai
            from google.genai import types
            
            # Initialize Gemini client
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            
            if api_key:
                client = genai.Client(api_key=api_key)
            else:
                client = genai.Client(
                    vertexai=True,
                    project=settings.GOOGLE_CLOUD_PROJECT,
                    location=settings.VERTEX_AI_LOCATION
                )
            
            # Use the first (and only) selfie
            selfie_bytes = selfie_bytes_list[0]
            selfie_img = Image.open(BytesIO(selfie_bytes))
            
            # Fix EXIF orientation (phone cameras often have rotation metadata)
            from PIL import ImageOps
            try:
                selfie_img = ImageOps.exif_transpose(selfie_img)
            except Exception:
                pass  # No EXIF data or failed to transpose
            
            # Convert to RGB if needed
            if selfie_img.mode == "RGBA":
                bg = Image.new("RGB", selfie_img.size, (255, 255, 255))
                bg.paste(selfie_img, mask=selfie_img.split()[3])
                selfie_img = bg
            elif selfie_img.mode != "RGB":
                selfie_img = selfie_img.convert("RGB")
            
            # Save to PNG bytes (keep original size, no cropping)
            img_buffer = BytesIO()
            selfie_img.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()
            
            print(f"📸 Selfie size: {selfie_img.size}")
            
            # Simple, clear prompt for full-body generation
            prompt = """Look at this person's face in the selfie. Generate a full-body photograph of this SAME person.

IMPORTANT:
- Keep the EXACT same face, skin tone, hair color and style
- Show full body from head to toe
- Standing pose, arms relaxed at sides
- Wearing a plain white t-shirt and blue jeans
- Clean white background
- Natural, friendly expression
- Professional photo quality

Generate the full-body image now."""

            print("🧑 Generating full-body avatar from selfie...")
            
            # Build content
            contents = [
                prompt,
                types.Part.from_bytes(data=img_bytes, mime_type="image/png")
            ]
            
            # Generate using Gemini with native image generation
            print(f"🎨 Avatar generation using: {settings.GEMINI_MODEL}")
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
            )
            
            # Extract generated image
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                print("✅ Gemini generated avatar image!")
                                image_data = part.inline_data.data
                                
                                if isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data)
                                
                                # Process the result - keep original size, no cropping
                                result_image = Image.open(BytesIO(image_data))
                                
                                print(f"✅ Avatar result size: {result_image.size}")
                                
                                output = BytesIO()
                                result_image.save(output, format="PNG", optimize=True)
                                output.seek(0)
                                
                                return output.getvalue()
                            
                            if hasattr(part, 'text') and part.text:
                                print(f"Gemini text: {part.text[:200]}...")
            
            print("⚠️ Gemini didn't return image, using enhanced selfie")
            # Fallback: return enhanced selfie
            return self._enhance_selfie(selfie_bytes)
            
        except Exception as e:
            print(f"❌ Avatar generation failed: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to enhanced selfie
            return self._enhance_selfie(selfie_bytes_list[0])
    
    def _resize_to_portrait(self, image: Image.Image, height: int = 1024) -> Image.Image:
        """Resize image to portrait aspect ratio (9:16)."""
        target_width = int(height * 9 / 16)
        
        # Calculate resize
        img_ratio = image.width / image.height
        target_ratio = target_width / height
        
        if img_ratio > target_ratio:
            # Image is wider, crop sides
            new_width = int(image.height * target_ratio)
            left = (image.width - new_width) // 2
            image = image.crop((left, 0, left + new_width, image.height))
        else:
            # Image is taller, crop top/bottom
            new_height = int(image.width / target_ratio)
            top = (image.height - new_height) // 2
            image = image.crop((0, top, image.width, top + new_height))
        
        return image.resize((target_width, height), Image.Resampling.LANCZOS)
    
    def _enhance_selfie(self, selfie_bytes: bytes) -> bytes:
        """Enhance and format a selfie as fallback avatar."""
        from PIL import ImageEnhance, ImageOps
        
        image = Image.open(BytesIO(selfie_bytes))
        
        # Fix EXIF orientation
        try:
            image = ImageOps.exif_transpose(image)
        except Exception:
            pass
        
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Enhance
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)
        
        # Don't crop - keep original aspect ratio
        output = BytesIO()
        image.save(output, format="PNG", optimize=True)
        output.seek(0)
        return output.getvalue()
    
    async def virtual_try_on(
        self, 
        person_image: bytes, 
        garment_image: bytes,
        category: str
    ) -> bytes:
        """
        Generate a virtual try-on image using Gemini Pro for image generation.
        
        Args:
            person_image: Person/avatar image bytes
            garment_image: Garment image bytes (with transparent background)
            category: Garment category (top, bottom, dress, outerwear)
        
        Returns:
            Generated try-on result image bytes
        """
        try:
            from google import genai
            from google.genai import types
            
            # Initialize Gemini client
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            
            if api_key:
                client = genai.Client(api_key=api_key)
            else:
                client = genai.Client(
                    vertexai=True,
                    project=settings.GOOGLE_CLOUD_PROJECT,
                    location=settings.VERTEX_AI_LOCATION
                )
            
            # Category descriptions for better prompts
            category_desc = {
                "top": "shirt/top/blouse",
                "bottom": "pants/trousers/jeans",
                "dress": "dress",
                "outerwear": "jacket/coat/hoodie"
            }
            garment_type = category_desc.get(category, "clothing")
            
            # Convert images to PIL and prepare bytes
            person_pil = Image.open(BytesIO(person_image))
            garment_pil = Image.open(BytesIO(garment_image))
            
            # Ensure RGB format for person
            if person_pil.mode == "RGBA":
                bg = Image.new("RGB", person_pil.size, (255, 255, 255))
                bg.paste(person_pil, mask=person_pil.split()[3])
                person_pil = bg
            elif person_pil.mode != "RGB":
                person_pil = person_pil.convert("RGB")
            
            # Convert garment to RGB with white background
            if garment_pil.mode == "RGBA":
                bg = Image.new("RGB", garment_pil.size, (255, 255, 255))
                bg.paste(garment_pil, mask=garment_pil.split()[3])
                garment_pil = bg
            elif garment_pil.mode != "RGB":
                garment_pil = garment_pil.convert("RGB")
            
            # Save to PNG bytes
            person_buffer = BytesIO()
            person_pil.save(person_buffer, format="PNG")
            person_bytes = person_buffer.getvalue()
            
            garment_buffer = BytesIO()
            garment_pil.save(garment_buffer, format="PNG")
            garment_bytes = garment_buffer.getvalue()
            
            # Build the prompt for virtual try-on
            prompt = f"""Virtual try-on task: Show the person wearing the garment.

I'm providing two images:
1. A person/avatar photo
2. A {garment_type} garment

Generate a new image showing this SAME person wearing this EXACT garment.

Requirements:
- Keep the person's face, body, and pose exactly the same
- Replace their current {garment_type} with the provided garment
- The garment should fit naturally on the person's body
- Maintain realistic lighting and shadows
- Keep the same background
- Photorealistic quality
- Full body shot if possible

Generate the try-on result now."""

            print(f"👕 Virtual try-on: {garment_type}")
            
            # Build content with both images
            contents = [
                prompt,
                "Person/Avatar:",
                types.Part.from_bytes(data=person_bytes, mime_type="image/png"),
                "Garment to wear:",
                types.Part.from_bytes(data=garment_bytes, mime_type="image/png"),
            ]
            
            # Generate using Gemini with native image generation
            print(f"👕 Try-on using: {settings.GEMINI_MODEL}")
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
            )
            
            # Extract generated image
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                print("✅ Gemini generated try-on image!")
                                image_data = part.inline_data.data
                                
                                if isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data)
                                
                                # Process the result - keep original size
                                result_image = Image.open(BytesIO(image_data))
                                
                                # Don't force resize - return as Gemini generated it
                                output = BytesIO()
                                result_image.save(output, format="PNG", optimize=True)
                                output.seek(0)
                                
                                return output.getvalue()
                            
                            if hasattr(part, 'text') and part.text:
                                print(f"Gemini text: {part.text[:200]}...")
            
            raise ValueError("Gemini didn't return a try-on image")
            
        except Exception as e:
            print(f"❌ Virtual try-on failed: {e}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Virtual try-on failed: {str(e)}")
    
    async def virtual_try_on_multiple(
        self,
        person_image: bytes,
        garments: List[dict]  # [{bytes, category}, ...]
    ) -> bytes:
        """
        Generate a virtual try-on image with multiple garments using Gemini.
        
        Args:
            person_image: Person/avatar image bytes
            garments: List of dicts with 'bytes' and 'category' keys
        
        Returns:
            Generated try-on result image bytes
        """
        try:
            from google import genai
            from google.genai import types
            
            # Initialize Gemini client
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            
            if api_key:
                client = genai.Client(api_key=api_key)
            else:
                client = genai.Client(
                    vertexai=True,
                    project=settings.GOOGLE_CLOUD_PROJECT,
                    location=settings.VERTEX_AI_LOCATION
                )
            
            # Category descriptions for better prompts
            category_desc = {
                "top": "shirt/top/blouse",
                "bottom": "pants/trousers/jeans",
                "dress": "dress",
                "outerwear": "jacket/coat/hoodie"
            }
            
            # Convert person image to PIL and prepare bytes
            person_pil = Image.open(BytesIO(person_image))
            
            # Ensure RGB format for person
            if person_pil.mode == "RGBA":
                bg = Image.new("RGB", person_pil.size, (255, 255, 255))
                bg.paste(person_pil, mask=person_pil.split()[3])
                person_pil = bg
            elif person_pil.mode != "RGB":
                person_pil = person_pil.convert("RGB")
            
            person_buffer = BytesIO()
            person_pil.save(person_buffer, format="PNG")
            person_bytes = person_buffer.getvalue()
            
            # Process all garments
            processed_garments = []
            outfit_description = []
            
            for i, garment in enumerate(garments):
                garment_pil = Image.open(BytesIO(garment["bytes"]))
                
                # Convert garment to RGB with white background
                if garment_pil.mode == "RGBA":
                    bg = Image.new("RGB", garment_pil.size, (255, 255, 255))
                    bg.paste(garment_pil, mask=garment_pil.split()[3])
                    garment_pil = bg
                elif garment_pil.mode != "RGB":
                    garment_pil = garment_pil.convert("RGB")
                
                garment_buffer = BytesIO()
                garment_pil.save(garment_buffer, format="PNG")
                
                processed_garments.append({
                    "bytes": garment_buffer.getvalue(),
                    "category": garment["category"],
                    "type": category_desc.get(garment["category"], "clothing")
                })
                
                outfit_description.append(f"- Garment {i+1}: {category_desc.get(garment['category'], 'clothing')}")
            
            # Build the prompt for multi-garment virtual try-on
            garment_list = "\n".join(outfit_description)
            prompt = f"""Virtual try-on task: Show the person wearing a COMPLETE OUTFIT with multiple garments.

I'm providing:
1. A person/avatar photo
2. Multiple garment images that form a complete outfit:
{garment_list}

Generate a new image showing this SAME person wearing ALL of these garments together as a coordinated outfit.

Requirements:
- Keep the person's face, body shape, and pose exactly the same
- Dress the person in ALL the provided garments simultaneously
- Each garment should fit naturally on the person's body
- The garments should work together as a cohesive outfit
- Maintain realistic lighting and shadows
- Keep the same background
- Photorealistic quality
- Full body shot showing all garments

Generate the complete outfit try-on result now."""

            print(f"👗 Multi-garment virtual try-on: {len(garments)} items")
            
            # Build content with person and all garment images
            contents = [
                prompt,
                "Person/Avatar:",
                types.Part.from_bytes(data=person_bytes, mime_type="image/png"),
            ]
            
            # Add each garment image
            for i, garment in enumerate(processed_garments):
                contents.append(f"Garment {i+1} ({garment['type']}):")
                contents.append(types.Part.from_bytes(data=garment["bytes"], mime_type="image/png"))
            
            # Generate using Gemini with native image generation
            print(f"👗 Multi try-on using: {settings.GEMINI_MODEL}")
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
            )
            
            # Extract generated image
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                print("✅ Gemini generated multi-garment try-on image!")
                                image_data = part.inline_data.data
                                
                                if isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data)
                                
                                # Process the result - keep original size
                                result_image = Image.open(BytesIO(image_data))
                                
                                output = BytesIO()
                                result_image.save(output, format="PNG", optimize=True)
                                output.seek(0)
                                
                                return output.getvalue()
                            
                            if hasattr(part, 'text') and part.text:
                                print(f"Gemini text: {part.text[:200]}...")
            
            raise ValueError("Gemini didn't return a multi-garment try-on image")
            
        except Exception as e:
            print(f"❌ Multi-garment virtual try-on failed: {e}")
            import traceback
            traceback.print_exc()
            raise ValueError(f"Multi-garment virtual try-on failed: {str(e)}")
    
    async def detect_clothes_in_image(self, image_bytes: bytes) -> List[dict]:
        """
        Analyze an image and detect clothing items using Gemini.
        
        Args:
            image_bytes: Image containing clothing items
        
        Returns:
            List of detected items with category and description
        """
        from google.genai import types
        import json
        
        print("🔍 Detecting clothes with Gemini...")
        
        client = self._get_gemini_client()
        
        # Use Flash model for analysis (text-only response)
        prompt = """Analyze this image and identify all clothing items visible.

For EACH distinct clothing item you can see, provide:
1. category: one of "top", "bottom", "dress", "outerwear"
2. description: detailed description including color, style, material, pattern, etc.

Return a JSON array. Example format:
[
  {"category": "top", "description": "Navy blue cotton t-shirt with crew neck, short sleeves, plain solid color"},
  {"category": "bottom", "description": "Light wash denim jeans, slim fit, five-pocket style with slight distressing"}
]

If the image shows a full outfit on a person, identify each garment separately.
If it shows a single item (like a shirt on a hanger), return just that one item.
Focus on the main clothing items - ignore accessories like watches, jewelry, etc.

Return ONLY the JSON array, no other text."""

        contents = [
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        ]
        
        try:
            # Use Flash for analysis (no image generation needed)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=contents,
            )
            
            # Parse the response
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text.strip()
                                
                                # Clean up the response
                                if text.startswith("```json"):
                                    text = text[7:]
                                if text.startswith("```"):
                                    text = text[3:]
                                if text.endswith("```"):
                                    text = text[:-3]
                                text = text.strip()
                                
                                print(f"📝 Gemini analysis: {text[:200]}...")
                                
                                items = json.loads(text)
                                if isinstance(items, list) and len(items) > 0:
                                    print(f"✅ Detected {len(items)} clothing items")
                                    return items
            
            print("⚠️ No items detected")
            return []
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse Gemini response: {e}")
            return []
        except Exception as e:
            print(f"❌ Detection failed: {e}")
            raise
    
    async def create_ghost_mannequin_from_description(
        self,
        image_bytes: bytes,
        description: str,
        category: str
    ) -> bytes:
        """
        Create a ghost mannequin image for a specific clothing item.
        
        Args:
            image_bytes: Original image containing the item
            description: Description of the specific item to extract
            category: Category (top, bottom, dress, outerwear)
        
        Returns:
            Ghost mannequin image bytes
        """
        from google.genai import types
        
        print(f"🎨 Creating ghost mannequin for: {description[:50]}...")
        
        client = self._get_gemini_client()
        
        prompt = f"""Create a professional ghost mannequin product photo of this clothing item:

ITEM: {description}
CATEGORY: {category}

Instructions:
1. Extract ONLY this specific item from the image
2. Remove any person, hanger, or background
3. Create the "ghost mannequin" effect - the garment should appear 3D as if worn by an invisible mannequin
4. Show the natural shape and drape of the garment
5. Use a clean, pure white background
6. Professional e-commerce product photography style
7. Show realistic fabric texture, folds, and shadows

Generate a clean product photo with ghost mannequin effect."""

        contents = [
            prompt,
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        ]
        
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                )
            )
            
            if response.candidates:
                for candidate in response.candidates:
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                print("✅ Ghost mannequin generated!")
                                image_data = part.inline_data.data
                                
                                if isinstance(image_data, str):
                                    image_data = base64.b64decode(image_data)
                                
                                return image_data
                            
                            if hasattr(part, 'text') and part.text:
                                print(f"Gemini: {part.text[:100]}...")
            
            print("⚠️ Gemini didn't generate image, using original")
            return image_bytes
            
        except Exception as e:
            print(f"❌ Ghost mannequin failed: {e}")
            # Fallback - return original image
            return image_bytes

