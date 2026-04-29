# Qwen-Image-Edit-2511 Service

A lightweight self-hosted image editing service using [Qwen-Image-Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) (pre-quantized 4-bit) for ghost mannequin generation and virtual try-on.

**Output**: 768x1024 portrait images optimized for mobile viewing.

## Hardware Requirements

- **GPU**: NVIDIA with 24GB VRAM (RTX 3090, RTX 4090, A5000, etc.)
- **RAM**: 32GB recommended
- **Storage**: ~20GB for pre-quantized model weights

With the pre-quantized 4-bit model, uses ~12-16GB VRAM at 768x1024 resolution.

## Quick Start

### 1. Setup Environment

```bash
cd image-edit-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies (diffusers from git for QwenImageEditPlusPipeline)
pip install -r requirements.txt
```

### 2. Configure

```bash
cp env.example .env
# Edit .env if needed
```

### 3. Run Service

```bash
# Start the service
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8001
```

First run will download model weights from HuggingFace.

### 4. Test

```bash
# Health check
curl http://localhost:8001/health

# Ghost mannequin (using curl)
curl -X POST http://localhost:8001/ghost-mannequin \
  -F "image=@garment.png" \
  -F "category=top"
```

## API Endpoints

### `GET /health`

Health check with GPU and model status.

### `POST /ghost-mannequin`

Create ghost mannequin effect from garment image.

| Parameter | Type | Description |
|-----------|------|-------------|
| image | file | Garment image (PNG/JPG) |
| category | string | top, bottom, dress, outerwear |
| custom_prompt | string | Optional custom prompt |
| steps | int | Inference steps (4-100, default: 40) |
| seed | int | Random seed for reproducibility |

**Output**: 768x1024 portrait PNG

### `POST /edit`

Generic image editing with text prompt.

| Parameter | Type | Description |
|-----------|------|-------------|
| image | file | Image to edit |
| prompt | string | Edit instruction |
| steps | int | Inference steps |
| seed | int | Random seed |

**Output**: 768x1024 portrait PNG

### `POST /try-on`

Virtual try-on (experimental).

| Parameter | Type | Description |
|-----------|------|-------------|
| avatar | file | Person/avatar image |
| garment | file | Garment image |
| category | string | Garment type |
| seed | int | Random seed |

**Output**: 768x1024 portrait PNG

## Integration with Wardrub Backend

Set environment variables in your backend:

```bash
IMAGE_GEN_BACKEND=qwen
IMAGE_EDIT_SERVICE_URL=http://localhost:8001
```

Or use the client directly:

```python
from client import ImageEditClient

client = ImageEditClient("http://localhost:8001")

async def create_ghost_mannequin(image_bytes: bytes, category: str) -> bytes:
    result = await client.create_ghost_mannequin(
        image_bytes=image_bytes,
        category=category
    )
    
    if result["success"]:
        return result["image_bytes"]
    else:
        raise Exception(result["error"])
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| HOST | 0.0.0.0 | Server host |
| PORT | 8001 | Server port |
| MODEL_ID | toandev/Qwen-Image-Edit-2511-4bit | Pre-quantized model |
| NUM_INFERENCE_STEPS | 40 | Default inference steps |
| GUIDANCE_SCALE | 1.0 | Guidance scale |
| TRUE_CFG_SCALE | 4.0 | True CFG scale for 2511 |
| ENABLE_CPU_OFFLOAD | true | Enable CPU offload |
| OUTPUT_WIDTH | 768 | Output width (portrait) |
| OUTPUT_HEIGHT | 1024 | Output height (portrait) |

## Performance

On RTX 4090 with pre-quantized 4-bit model:
- Ghost mannequin: ~15-25 seconds (40 steps)
- VRAM usage: ~12-14GB at 768x1024

On RTX 3090:
- Ghost mannequin: ~25-35 seconds (40 steps)
- VRAM usage: ~14-16GB at 768x1024

## Troubleshooting

### Out of Memory (OOM)

1. Ensure `ENABLE_CPU_OFFLOAD=true`
2. Close other GPU applications
3. Reduce inference steps if needed

### Slow First Request

First request loads the model. Subsequent requests are faster.

### Model Download Issues

Set `HF_HUB_ENABLE_HF_TRANSFER=1` for faster downloads:

```bash
pip install hf_transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
```

## Model Changes from v1

| Feature | v1 (Qwen-Image-Edit) | v2 (Qwen-Image-Edit-2511) |
|---------|----------------------|---------------------------|
| Model | Qwen/Qwen-Image-Edit | toandev/Qwen-Image-Edit-2511-4bit |
| Pipeline | QwenImageEditPipeline | QwenImageEditPlusPipeline |
| Quantization | Manual NF4 in code | Pre-quantized |
| LoRA | Lightning LoRA (8 steps) | Built-in optimizations |
| Steps | 8 | 40 |
| Output | 1024x1024 (square) | 768x1024 (portrait) |

## Credits

- [Qwen-Image-Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) by Alibaba
- [Pre-quantized 4-bit model](https://huggingface.co/toandev/Qwen-Image-Edit-2511-4bit) by @toandev
- QwenImageEditPlusPipeline from HuggingFace Diffusers

## License

Apache 2.0 (following Qwen-Image-Edit license)
