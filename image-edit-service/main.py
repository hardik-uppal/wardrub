"""
Qwen-Image-Edit-2511 FastAPI Service for Ghost Mannequin Generation.

A lightweight self-hosted image editing service using the pre-quantized
Qwen-Image-Edit-2511-4bit model optimized for 24GB VRAM.

Output: 768x1024 portrait images optimized for mobile viewing.

Usage:
    uvicorn main:app --host 0.0.0.0 --port 8001

Endpoints:
    POST /ghost-mannequin  - Create ghost mannequin from garment image
    POST /edit             - Generic image editing
    POST /try-on           - Virtual try-on (garment on avatar)
    GET  /health           - Health check with GPU stats
"""

import base64
import time
from io import BytesIO
from contextlib import asynccontextmanager

import torch
from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from models import (
    GhostMannequinRequest,
    ImageEditRequest,
    TryOnRequest,
    ImageResponse,
    HealthResponse,
    GarmentCategory,
)

settings = get_settings()

# Lazy load pipeline
_pipeline_loaded = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler - preload model on startup."""
    global _pipeline_loaded
    
    print("🚀 Starting Qwen-Image-Edit-2511 Service...")
    print(f"   Host: {settings.HOST}:{settings.PORT}")
    print(f"   Model: {settings.MODEL_ID}")
    print(f"   Output: {settings.OUTPUT_WIDTH}x{settings.OUTPUT_HEIGHT} (portrait)")
    print(f"   CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
        total_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"   VRAM: {total_mem:.1f}GB")
    
    # Preload pipeline (comment out for lazy loading)
    try:
        from pipeline import get_pipeline
        get_pipeline()
        _pipeline_loaded = True
    except Exception as e:
        print(f"⚠️ Failed to preload pipeline: {e}")
        print("   Pipeline will load on first request")
    
    yield
    
    # Cleanup
    print("🛑 Shutting down...")
    from pipeline import unload_pipeline
    unload_pipeline()


app = FastAPI(
    title="Qwen-Image-Edit-2511 Service",
    description="Self-hosted image editing for ghost mannequin and virtual try-on with configurable preprocessing (native aspect-ratio or portrait canvas).",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Prompts for different use cases ===

# Ghost mannequin prompts - strict floating garment (no mannequin/body)
GHOST_FLOATING_GARMENT_GUARDRAIL = """
FINAL OUTPUT REQUIREMENT (NON-NEGOTIABLE):
- Show ONLY a floating garment product photo.
- No mannequin, no dummy, no torso form, no neck block, no body silhouette, no person.
- If any mannequin/body structure appears, remove it completely and keep only empty/hollow garment.
""".strip()


def _sanitize_ghost_prompt(text: str) -> str:
    """Reduce mannequin-triggering wording in custom prompts."""
    out = text
    out = out.replace("ghost mannequin", "floating garment")
    out = out.replace("Ghost mannequin", "Floating garment")
    out = out.replace("ghost-mannequin", "floating garment")
    return out


GHOST_MANNEQUIN_PROMPTS = {
    GarmentCategory.TOP: """Create a clean e-commerce product image of ONLY the shirt/top as a floating garment.

HARD REQUIREMENTS:
- Keep the garment faithful to the input (color, print, fabric texture, shape)
- Remove person completely
- No mannequin, no torso, no neck, no arms, no hands, no skin
- No hanger, no model, no extra clothing
- Garment appears naturally hollow/empty inside (floating ghost style)
- Centered on pure white background
- Professional studio product photography""",

    GarmentCategory.BOTTOM: """Create a clean e-commerce product image of ONLY the pants/bottoms as a floating garment.

HARD REQUIREMENTS:
- Keep the garment faithful to the input (color, print, fabric texture, shape)
- Remove person completely
- No mannequin, no body, no legs, no feet, no skin
- No hanger, no model, no extra clothing
- Garment appears naturally hollow/empty inside (floating ghost style)
- Centered on pure white background
- Professional studio product photography""",

    GarmentCategory.DRESS: """Create a clean e-commerce product image of ONLY the dress as a floating garment.

HARD REQUIREMENTS:
- Keep the garment faithful to the input (color, print, fabric texture, shape)
- Remove person completely
- No mannequin, no torso, no neck, no arms, no legs, no skin
- No hanger, no model, no extra clothing
- Garment appears naturally hollow/empty inside (floating ghost style)
- Centered on pure white background
- Professional studio product photography""",

    GarmentCategory.OUTERWEAR: """Create a clean e-commerce product image of ONLY the jacket/coat as a floating garment.

HARD REQUIREMENTS:
- Keep the garment faithful to the input (color, print, fabric texture, shape)
- Remove person completely
- No mannequin, no torso, no neck, no arms, no hands, no skin
- No hanger, no model, no extra clothing
- Garment appears naturally hollow/empty inside (floating ghost style)
- Centered on pure white background
- Professional studio product photography""",
}


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    buffer = BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def load_upload_image(upload: UploadFile) -> Image.Image:
    """Load uploaded file as PIL Image."""
    contents = upload.file.read()
    return Image.open(BytesIO(contents))


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check with GPU and model status."""
    gpu_available = torch.cuda.is_available()
    
    response = HealthResponse(
        status="healthy",
        model_loaded=_pipeline_loaded,
        gpu_available=gpu_available,
        quantization="4bit",  # Pre-quantized model
    )
    
    if gpu_available:
        response.gpu_name = torch.cuda.get_device_name(0)
        response.vram_total_gb = round(
            torch.cuda.get_device_properties(0).total_memory / 1024**3, 2
        )
        response.vram_used_gb = round(
            torch.cuda.memory_allocated() / 1024**3, 2
        )
    
    return response


@app.post("/ghost-mannequin", response_model=ImageResponse)
async def create_ghost_mannequin(
    image: UploadFile = File(..., description="Front view of garment (background removed preferred)"),
    back_image: UploadFile = File(None, description="Optional back view of garment"),
    category: GarmentCategory = Form(default=GarmentCategory.TOP),
    custom_prompt: str = Form(default=None),
    steps: int = Form(default=None, ge=4, le=100),
    seed: int = Form(default=None),
):
    """
    Create ghost mannequin effect from garment image(s).
    
    The garment will appear floating as if worn by an INVISIBLE mannequin
    with professional e-commerce photography lighting.
    
    Supports both single image (front only) and multi-image (front + back).
    
    Output: 768x1024 portrait image.
    """
    start_time = time.time()
    
    try:
        from pipeline import generate_ghost_mannequin
        
        # Load front image
        front_image = load_upload_image(image)
        
        # Load back image if provided
        back_img = None
        if back_image is not None:
            try:
                back_img = load_upload_image(back_image)
            except Exception:
                pass  # Ignore if back image fails to load
        
        # Select prompt
        if back_img is not None:
            # Multi-image prompt
            prompt = f"""Combine image 1 (front view) and image 2 (back view) to create ONE clean floating garment product photo.

HARD REQUIREMENTS:
- Keep garment details faithful (color, logos, print, seams, texture)
- No mannequin, no torso, no neck, no body parts, no skin
- No hanger, no model, no extra garment pieces
- Garment must look empty/hollow inside, not worn by anyone
- Single centered garment on pure white background
- Natural product shape and depth, professional studio lighting"""
        elif custom_prompt and not settings.GHOST_PROMPT_LOCKED:
            prompt = _sanitize_ghost_prompt(custom_prompt)
        else:
            if custom_prompt and settings.GHOST_PROMPT_LOCKED:
                print("[ghost] ignoring custom_prompt because GHOST_PROMPT_LOCKED=true")
            prompt = GHOST_MANNEQUIN_PROMPTS[category]

        prompt = f"{prompt}\n\n{GHOST_FLOATING_GARMENT_GUARDRAIL}"
        
        # Generate using ghost mannequin function
        output_image, seed_used = generate_ghost_mannequin(
            front=front_image,
            back=back_img,
            prompt=prompt,
            num_steps=steps,
            seed=seed,
        )
        
        # Convert to base64
        image_b64 = image_to_base64(output_image)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ImageResponse(
            success=True,
            image_base64=image_b64,
            processing_time_ms=processing_time,
            seed_used=seed_used,
        )
        
    except Exception as e:
        print(f"❌ Ghost mannequin error: {e}")
        import traceback
        traceback.print_exc()
        
        return ImageResponse(
            success=False,
            error=str(e),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )


@app.post("/edit", response_model=ImageResponse)
async def edit_image(
    image: UploadFile = File(..., description="Primary image to edit"),
    reference_images: list[UploadFile] | None = File(default=None, description="Optional additional reference images for multi-image edit"),
    prompt: str = Form(..., description="Edit instruction"),
    steps: int = Form(default=None, ge=4, le=100),
    seed: int = Form(default=None),
):
    """
    Generic image editing with text prompt.
    
    Output: 768x1024 portrait image.
    
    Examples:
    - "change background to pure white"
    - "remove the person, keep only the clothing"
    - "make it look like studio photography"
    """
    start_time = time.time()
    
    try:
        from pipeline import generate_image
        
        input_image = load_upload_image(image)
        refs: list[Image.Image] = []
        if reference_images:
            refs = [load_upload_image(ref_upload) for ref_upload in reference_images]

        output_image, seed_used = generate_image(
            image=input_image,
            prompt=prompt,
            num_steps=steps,
            seed=seed,
            reference_images=refs,
        )
        
        image_b64 = image_to_base64(output_image)
        processing_time = int((time.time() - start_time) * 1000)
        
        return ImageResponse(
            success=True,
            image_base64=image_b64,
            processing_time_ms=processing_time,
            seed_used=seed_used,
        )
        
    except Exception as e:
        print(f"❌ Edit error: {e}")
        import traceback
        traceback.print_exc()
        
        return ImageResponse(
            success=False,
            error=str(e),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )


@app.post("/try-on", response_model=ImageResponse)
async def virtual_try_on(
    avatar: UploadFile = File(..., description="Avatar/person image"),
    garment: UploadFile = File(..., description="Garment image"),
    category: GarmentCategory = Form(default=GarmentCategory.TOP),
    seed: int = Form(default=None),
):
    """
    Virtual try-on - place garment on avatar.
    
    Sends BOTH avatar and garment images to the model for proper try-on.
    
    Output: 768x1024 portrait image.
    """
    start_time = time.time()
    
    try:
        from pipeline import generate_tryon
        
        # Load both images
        avatar_image = load_upload_image(avatar)
        garment_image = load_upload_image(garment)
        
        # Category descriptions
        category_names = {
            GarmentCategory.TOP: "shirt/top",
            GarmentCategory.BOTTOM: "pants/bottoms", 
            GarmentCategory.DRESS: "dress",
            GarmentCategory.OUTERWEAR: "jacket/coat",
        }
        
        # Prompt for try-on with both images
        prompt = f"""Virtual try-on: Show the person from the first image wearing the {category_names[category]} from the second image.

Requirements:
- Keep the person's face, body, and pose exactly the same
- Replace their current {category_names[category]} with the garment shown
- The garment should fit naturally on the person's body
- Maintain realistic lighting and shadows
- Keep the same background
- Photorealistic quality result"""
        
        # Generate with BOTH images
        output_image, seed_used = generate_tryon(
            avatar=avatar_image,
            garment=garment_image,
            prompt=prompt,
            num_steps=settings.NUM_INFERENCE_STEPS,
            seed=seed,
        )
        
        image_b64 = image_to_base64(output_image)
        processing_time = int((time.time() - start_time) * 1000)
        
        return ImageResponse(
            success=True,
            image_base64=image_b64,
            processing_time_ms=processing_time,
            seed_used=seed_used,
        )
        
    except Exception as e:
        print(f"❌ Try-on error: {e}")
        import traceback
        traceback.print_exc()
        
        return ImageResponse(
            success=False,
            error=str(e),
            processing_time_ms=int((time.time() - start_time) * 1000),
        )


@app.post("/unload")
async def unload_model():
    """Unload model to free GPU memory."""
    global _pipeline_loaded
    
    from pipeline import unload_pipeline
    unload_pipeline()
    _pipeline_loaded = False
    
    return {"status": "unloaded", "message": "Model unloaded, GPU memory freed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,  # Disable reload in production
    )
