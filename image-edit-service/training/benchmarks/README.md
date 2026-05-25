# Wardrub Benchmark Sets (v1)

This folder defines **offline evaluation sets** so we can compare:

- Nano Banana (current baseline)
- Qwen base service
- Qwen + LoRA checkpoints

without paying for RunPod until we have clear win criteria.

## Benchmarks

- `ghost_test_v1.template.jsonl` — ghost mannequin from varied inputs (person/hanger/bed/flatlay)
- `look_test_v1.template.jsonl` — avatar + garment (usually ghost garment) -> final look
- `avatar_test_v1.template.jsonl` — avatar creation/edit consistency tasks
- `avatar_identity_lfw_small_v1.jsonl` — **small face-identity chunk** (48 images, 8 identities × 6)
- `avatar_fullbody_viton_small_v1.jsonl` — **small full-body chunk** (48 images from VITON persons)
- `*.starter.jsonl` — tiny runnable manifests using current `test_images/`
- `scoring_template.csv` — human rating sheet

## Manifest format

Each line is one JSON object.

Common fields:

- `id` (string, required)
- `endpoint` (required): `ghost-mannequin` | `try-on` | `edit`
- `tags` (optional dict): source type, category, difficulty, etc.
- `notes` (optional string)

Endpoint-specific fields:

### ghost-mannequin

Required:

- `image` (path)

Optional:

- `back_image` (path)
- `category` (`top|bottom|dress|outerwear`)
- `custom_prompt` (string)
- `steps` (int)
- `seed` (int)

### try-on

Required:

- `avatar` (path)
- `garment` (path)

Optional:

- `category`
- `seed`

### edit

Required:

- `image` (path)
- `prompt` (string)

Optional:

- `steps`
- `seed`

## Build small dataset chunks (recommended for fast iteration)

### A) Face identity chunk (small, multi-image per identity)

```bash
source venv/bin/activate
pip install scikit-learn

python training/benchmarks/download_lfw_identity_subset.py \
  --out-root training/benchmarks/assets/chunks/face_identity_lfw_small_v1 \
  --max-identities 8 \
  --max-images-per-identity 6

python training/benchmarks/build_avatar_identity_manifest.py \
  --assets-root training/benchmarks/assets/chunks/face_identity_lfw_small_v1 \
  --out training/benchmarks/avatar_identity_lfw_small_v1.jsonl \
  --prompt-mode portrait_neutral \
  --steps 24
```

### B) Full-body chunk (small)

```bash
python training/benchmarks/build_fullbody_viton_chunk.py \
  --repo-root . \
  --count 48 \
  --steps 24
```

This gives quick test chunks without pulling full datasets.

## Build local v1 sets from existing proto data

If you already have `data/viton_hd_proto` (we do), auto-build ready benchmark folders + manifests:

```bash
python training/benchmarks/build_v1_sets.py \
  --repo-root . \
  --ghost-count 24 \
  --look-count 24 \
  --avatar-count 24
```

This creates:

- `training/benchmarks/assets/v1/...` (copied benchmark images)
- `training/benchmarks/ghost_test_v1.jsonl`
- `training/benchmarks/look_test_v1.jsonl`
- `training/benchmarks/avatar_test_v1.jsonl`

## Run benchmark

1) Start service

```bash
cd image-edit-service
source venv/bin/activate
python main.py
```

2) Validate manifest

```bash
# For starter files with existing local images:
python training/benchmarks/validate_manifest.py \
  --manifest training/benchmarks/ghost_test_v1.starter.jsonl \
  --dataset-root .

# For template files before replacing paths:
python training/benchmarks/validate_manifest.py \
  --manifest training/benchmarks/ghost_test_v1.template.jsonl \
  --dataset-root . \
  --no-path-check
```

3) Run benchmark

```bash
python training/eval/run_benchmark_manifest.py \
  --manifest training/benchmarks/ghost_test_v1.starter.jsonl \
  --dataset-root . \
  --base-url http://localhost:8001 \
  --out runs/benchmarks/ghost_test_v1_qwen_base
```

## What we need from you to finalize v1 sets

- Source image folders for each task (ghost/look/avatar)
- Target sample counts per bucket (easy/medium/hard)
- Any private policy constraints (logos, faces, model pose restrictions)
- Preferred scoring priorities (fidelity vs realism vs background cleanliness)
