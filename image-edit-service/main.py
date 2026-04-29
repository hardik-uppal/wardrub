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
    description="Self-hosted image editing for ghost mannequin and virtual try-on. Outputs 768x1024 portrait images.",
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

# Ghost mannequin prompts - extract garment from person, clean product photo
GHOST_MANNEQUIN_PROMPTS = {
    GarmentCategory.TOP: """Extract just the shirt/top from this image and create a clean product photo.

Remove the person completely. Show ONLY the garment on pure white background.
- Remove head, arms, hands, skin - nothing visible except the clothing item
- Pure white background, no shadows
- Keep exact original color and texture of the fabric
- Flat frontal product view, centered
- Professional e-commerce catalog style""",

    GarmentCategory.BOTTOM: """Extract just the pants/bottoms from this image and create a clean product photo.

Remove the person completely. Show ONLY the garment on pure white background.
- Remove body, legs, feet - nothing visible except the pants
- Pure white background, no shadows
- Keep exact original color and texture of the fabric
- Flat frontal product view, centered
- Professional e-commerce catalog style""",

    GarmentCategory.DRESS: """Extract just the dress from this image and create a clean product photo.

Remove the person completely. Show ONLY the garment on pure white background.
- Remove head, arms, legs - nothing visible except the dress
- Pure white background, no shadows
- Keep exact original color and texture of the fabric
- Flat frontal product view, centered
- Professional e-commerce catalog style""",

    GarmentCategory.OUTERWEAR: """Extract just the jacket/coat from this image and create a clean product photo.

Remove the person completely. Show ONLY the garment on pure white background.
- Remove head, arms, hands - nothing visible except the jacket
- Pure white background, no shadows
- Keep exact original color and texture of the fabric
- Flat frontal product view, centered
- Professional e-commerce catalog style""",
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
        if custom_prompt:
            prompt = custom_prompt
        elif back_img is not None:
            # Multi-image prompt
            prompt = f"""Create a professional ghost mannequin e-commerce photo combining these front and back views.

The first image shows the FRONT of the garment.
The second image shows the BACK of the garment.

CRITICAL: Create a SINGLE floating garment showing its 3D shape.
- NO visible mannequin or body parts
- The garment should appear to float
- Show natural shape and depth
- Pure white background
- Professional studio lighting
- High-end fashion e-commerce style"""
        else:
            prompt = GHOST_MANNEQUIN_PROMPTS[category]
        
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
    image: UploadFile = File(..., description="Image to edit"),
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
        
        output_image, seed_used = generate_image(
            image=input_image,
            prompt=prompt,
            num_steps=steps,
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
