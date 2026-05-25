# Wardrub VTON Prototype Baseline Results

Date: 2026-05-21

## Hardware

```text
GPU: NVIDIA GeForce RTX 4090
VRAM: 24 GB class / 23.55 GiB reported
Idle VRAM before run: ~40 MiB
```

## Service Configuration

```text
Model: toandev/Qwen-Image-Edit-2511-4bit
Speed LoRA: lightx2v/Qwen-Image-Edit-2511-Lightning
Inference steps: 4
CPU offload during smoke run: false
Output size: 768x1024
```

## Dataset

Prepared local prototype from Hugging Face `forgeml/viton_hd`:

```text
data/viton_hd_proto
rows: 64
try-on manifest: data/viton_hd_proto/manifests/tryon_train.jsonl
ghost manifest: data/viton_hd_proto/manifests/ghost_train.jsonl
DiffSynth try-on metadata: data/viton_hd_proto/diffsynth_tryon_metadata.json
DiffSynth ghost metadata: data/viton_hd_proto/diffsynth_ghost_metadata.json
```

DiffSynth metadata validation passed:

```text
dataset length: 64
image target size after max_pixels=262144 resize: 432x576
edit_image list length: 2
edit_image sizes: 432x576, 432x576
```

## Baseline Endpoint Smoke Results

### Try-on

Command:

```bash
python training/eval/run_service_eval.py \
  --manifest data/viton_hd_proto/manifests/tryon_train.jsonl \
  --dataset-root data/viton_hd_proto \
  --endpoint try-on \
  --limit 2 \
  --out runs/eval_tryon_baseline_2
```

Result:

```text
success_count: 2 / 2
avg_service_processing_time_ms: 28,750.5
avg_wall_time_ms: 28,761
sample 000000: 29,078 ms
sample 000001: 28,423 ms
```

Outputs:

```text
runs/eval_tryon_baseline_2/try-on_000000.png
runs/eval_tryon_baseline_2/try-on_000001.png
runs/eval_tryon_baseline_2/metrics.json
```

### Ghost mannequin / extraction

Command:

```bash
python training/eval/run_service_eval.py \
  --manifest data/viton_hd_proto/manifests/ghost_train.jsonl \
  --dataset-root data/viton_hd_proto \
  --endpoint ghost-mannequin \
  --limit 2 \
  --steps 4 \
  --out runs/eval_ghost_baseline_2
```

Result:

```text
success_count: 2 / 2
avg_service_processing_time_ms: 16,641.5
avg_wall_time_ms: 16,648
sample 000000: 16,641 ms
sample 000001: 16,642 ms
```

Outputs:

```text
runs/eval_ghost_baseline_2/ghost-mannequin_000000.png
runs/eval_ghost_baseline_2/ghost-mannequin_000001.png
runs/eval_ghost_baseline_2/metrics.json
```

## VRAM Observations

```text
Model loaded: ~16.43 GiB allocated
During generation: ~21.65-21.67 GiB reserved
After service shutdown: ~40 MiB
```

## Takeaways

1. Local VITON-HD export works.
2. DiffSynth metadata mapping works.
3. Existing Wardrub service successfully runs Qwen-Image-Edit-2511 4-bit + Lightning on the local 4090.
4. Baseline speed is still slow for product UX:
   - try-on: ~29s per image
   - ghost/extraction: ~16.6s per image
5. This confirms the need for:
   - Wardrub task LoRA for quality/consistency
   - Lightning/LCM compatibility for 2-4 step diffusion
   - later CNN/feed-forward distillation for near-real-time UX

## Next Step

Run a small DiffSynth training smoke test using:

```text
rank: 8 local smoke / 32 serious run
target modules local smoke: attention-only
target modules serious run: DiffSynth full Qwen-Image-Edit-2511 target list
zero_cond_t: true
extra_inputs: edit_image
data_file_keys: image,edit_image
```
