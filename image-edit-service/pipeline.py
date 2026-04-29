"""Qwen-Image-Edit-2511 pipeline with pre-quantized 4-bit model.

Uses toandev/Qwen-Image-Edit-2511-4bit for efficient inference on 24GB VRAM.
Outputs portrait-oriented images (768x1024) optimized for mobile viewing.
"""

import torch
from PIL import Image
from typing import Optional
import gc

from config import get_settings

settings = get_settings()

# Global pipeline instance
_pipeline = None
_is_loaded = False


def get_pipeline():
    """Get or initialize the Qwen-Image-Edit-2511 pipeline."""
    global _pipeline, _is_loaded
    
    if _is_loaded and _pipeline is not None:
        return _pipeline
    
    print("🚀 Loading Qwen-Image-Edit-2511 pipeline...")
    print(f"   Model: {settings.MODEL_ID}")
    print(f"   Output: {settings.OUTPUT_WIDTH}x{settings.OUTPUT_HEIGHT} (portrait)")
    
    # Import here to avoid slow startup when just importing module
    from diffusers import QwenImageEditPlusPipeline
    
    torch_dtype = torch.bfloat16
    
    # Load pre-quantized model directly - no manual quantization needed
    print("📦 Loading pre-quantized 4-bit model...")
    pipe = QwenImageEditPlusPipeline.from_pretrained(
        settings.MODEL_ID,
        torch_dtype=torch_dtype,
        cache_dir=settings.CACHE_DIR,
    )
    
    # Load Lightning LoRA for faster inference (4 steps instead of 40)
    if settings.USE_LIGHTNING_LORA:
        print(f"⚡ Loading Lightning LoRA for 4-step inference...")
        pipe.load_lora_weights(
            settings.LIGHTNING_LORA_REPO,
            weight_name=settings.LIGHTNING_LORA_WEIGHT,
            cache_dir=settings.CACHE_DIR,
        )
        print(f"   LoRA: {settings.LIGHTNING_LORA_WEIGHT}")
    
    # Enable CPU offload for memory efficiency
    if settings.ENABLE_CPU_OFFLOAD:
        print("💾 Enabling model CPU offload...")
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to("cuda")
    
    pipe.set_progress_bar_config(disable=None)
    
    _pipeline = pipe
    _is_loaded = True
    
    # Clear CUDA cache
    gc.collect()
    torch.cuda.empty_cache()
    
    print("✅ Pipeline loaded successfully!")
    _print_gpu_stats()
    
    return _pipeline


def _print_gpu_stats():
    """Print GPU memory statistics."""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"   GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved, {total:.2f}GB total")


def resize_to_portrait(image: Image.Image) -> Image.Image:
    """
    Resize image to fit within portrait canvas (768x1024).
    
    Preserves aspect ratio and centers on transparent canvas.
    
    Args:
        image: Input PIL Image
        
    Returns:
        Image resized to fit within 768x1024 portrait canvas
    """
    target_width = settings.OUTPUT_WIDTH
    target_height = settings.OUTPUT_HEIGHT
    
    original_width, original_height = image.size
    
    # Calculate scaling ratio to fit within target dimensions
    ratio = min(target_width / original_width, target_height / original_height)
    new_width = int(original_width * ratio)
    new_height = int(original_height * ratio)
    
    # Resize with high-quality resampling
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # For RGB images, use white background; for RGBA, use transparent
    if image.mode == "RGBA":
        canvas = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    else:
        canvas = Image.new("RGB", (target_width, target_height), (255, 255, 255))
    
    # Center the resized image on canvas
    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2
    
    if image.mode == "RGBA":
        canvas.paste(resized, (x_offset, y_offset), resized)
    else:
        canvas.paste(resized, (x_offset, y_offset))
    
    return canvas


def _prepare_image(image: Image.Image) -> Image.Image:
    """Convert image to RGB and resize to portrait."""
    if image.mode == "RGBA":
        bg = Image.new("RGB", image.size, (255, 255, 255))
        bg.paste(image, mask=image.split()[3])
        image = bg
    else:
        image = image.convert("RGB")
    return resize_to_portrait(image)


def generate_image(
    image: Image.Image,
    prompt: str,
    num_steps: Optional[int] = None,
    seed: Optional[int] = None,
) -> tuple[Image.Image, int]:
    """
    Generate edited image using Qwen-Image-Edit-2511.
    
    Args:
        image: Input PIL Image
        prompt: Edit instruction
        num_steps: Number of inference steps (default: 40)
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (output_image, seed_used)
    """
    pipe = get_pipeline()
    
    # Prepare image - convert to RGB and resize
    image = _prepare_image(image)
    
    # Setup generator for reproducibility
    if seed is None:
        seed = torch.randint(0, 2**32, (1,)).item()
    
    generator = torch.Generator(device="cuda").manual_seed(seed)
    
    # Use configured steps or override
    steps = num_steps or settings.NUM_INFERENCE_STEPS
    
    print(f"🎨 Generating with prompt: {prompt[:80]}...")
    print(f"   Steps: {steps}, Seed: {seed}, Size: {image.size}")
    
    # Generate with Qwen-Image-Edit-2511 parameters
    with torch.inference_mode():
        torch.cuda.empty_cache()
        output = pipe(
            image=image,
            prompt=prompt,
            num_inference_steps=steps,
            generator=generator,
            guidance_scale=settings.GUIDANCE_SCALE,
            true_cfg_scale=settings.TRUE_CFG_SCALE,
            negative_prompt=" ",
            num_images_per_prompt=1,
        )
    
    output_image = output.images[0]
    
    print(f"✅ Generation complete!")
    _print_gpu_stats()
    
    return output_image, seed


def generate_tryon(
    avatar: Image.Image,
    garment: Image.Image,
    prompt: str,
    num_steps: Optional[int] = None,
    seed: Optional[int] = None,
) -> tuple[Image.Image, int]:
    """
    Generate virtual try-on using both avatar and garment images.
    
    Uses Qwen-Image-Edit-2511's multi-image input capability.
    
    Args:
        avatar: Person/avatar PIL Image
        garment: Garment PIL Image
        prompt: Try-on instruction
        num_steps: Number of inference steps
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (output_image, seed_used)
    """
    pipe = get_pipeline()
    
    # Prepare both images
    avatar = _prepare_image(avatar)
    garment = _prepare_image(garment)
    
    # Setup generator for reproducibility
    if seed is None:
        seed = torch.randint(0, 2**32, (1,)).item()
    
    generator = torch.Generator(device="cuda").manual_seed(seed)
    
    # Use configured steps or override
    steps = num_steps or settings.NUM_INFERENCE_STEPS
    
    print(f"👕 Try-on with prompt: {prompt[:80]}...")
    print(f"   Steps: {steps}, Seed: {seed}")
    print(f"   Avatar size: {avatar.size}, Garment size: {garment.size}")
    
    # Generate with BOTH images - avatar first, then garment
    with torch.inference_mode():
        torch.cuda.empty_cache()
        output = pipe(
            image=[avatar, garment],  # Multi-image input!
            prompt=prompt,
            num_inference_steps=steps,
            generator=generator,
            guidance_scale=settings.GUIDANCE_SCALE,
            true_cfg_scale=settings.TRUE_CFG_SCALE,
            negative_prompt=" ",
            num_images_per_prompt=1,
        )
    
    output_image = output.images[0]
    
    print(f"✅ Try-on complete!")
    _print_gpu_stats()
    
    return output_image, seed


def generate_ghost_mannequin(
    front: Image.Image,
    back: Optional[Image.Image],
    prompt: str,
    num_steps: Optional[int] = None,
    seed: Optional[int] = None,
) -> tuple[Image.Image, int]:
    """
    Generate ghost mannequin using front and optionally back images.
    
    When both front and back are provided, uses multi-image input.
    
    Args:
        front: Front view of garment
        back: Optional back view of garment
        prompt: Ghost mannequin instruction
        num_steps: Number of inference steps
        seed: Random seed for reproducibility
        
    Returns:
        Tuple of (output_image, seed_used)
    """
    pipe = get_pipeline()
    
    # Prepare images
    front = _prepare_image(front)
    
    # Setup generator for reproducibility
    if seed is None:
        seed = torch.randint(0, 2**32, (1,)).item()
    
    generator = torch.Generator(device="cuda").manual_seed(seed)
    
    # Use configured steps or override
    steps = num_steps or settings.NUM_INFERENCE_STEPS
    
    # Determine if multi-image
    if back is not None:
        back = _prepare_image(back)
        images = [front, back]
        print(f"🎨 Ghost mannequin (front+back) with prompt: {prompt[:60]}...")
        print(f"   Front size: {front.size}, Back size: {back.size}")
    else:
        images = front
        print(f"🎨 Ghost mannequin (front only) with prompt: {prompt[:60]}...")
        print(f"   Front size: {front.size}")
    
    print(f"   Steps: {steps}, Seed: {seed}")
    
    # Generate
    with torch.inference_mode():
        torch.cuda.empty_cache()
        output = pipe(
            image=images,
            prompt=prompt,
            num_inference_steps=steps,
            generator=generator,
            guidance_scale=settings.GUIDANCE_SCALE,
            true_cfg_scale=settings.TRUE_CFG_SCALE,
            negative_prompt=" ",
            num_images_per_prompt=1,
        )
    
    output_image = output.images[0]
    
    print(f"✅ Ghost mannequin complete!")
    _print_gpu_stats()
    
    return output_image, seed


def unload_pipeline():
    """Unload pipeline to free GPU memory."""
    global _pipeline, _is_loaded
    
    if _pipeline is not None:
        del _pipeline
        _pipeline = None
        _is_loaded = False
        
        gc.collect()
        torch.cuda.empty_cache()
        
        print("🗑️ Pipeline unloaded, GPU memory freed")
