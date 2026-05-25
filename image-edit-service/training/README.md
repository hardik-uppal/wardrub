# Wardrub VTON / Ghost LoRA Prototype

This folder contains the local prototype workflow for training a Wardrub-specific image-edit LoRA and debugging it on the local RTX 4090 before a serious RunPod run.

Current service backend:

- Model: `toandev/Qwen-Image-Edit-2511-4bit`
- Speed adapter: `lightx2v/Qwen-Image-Edit-2511-Lightning`
- Service endpoints: `/try-on`, `/ghost-mannequin`, `/edit`
- Target output: `768x1024`

## Strategy

1. Use an open-source VTON dataset for a quick prototype.
2. Export a small local dataset first (`32-128` examples) to debug data shape, prompts, and service latency on the local 4090.
3. Train or adapter-smoke-test locally only at tiny scale.
4. Move full LoRA training to RunPod after the data/eval loop is proven.
5. Later speed path: combine Wardrub LoRA with Lightning/LCM, then distill to a CNN/feed-forward student.

## Dataset

Primary prototype dataset:

- `forgeml/viton_hd` on Hugging Face

Columns used:

- `agnostic` -> person/avatar conditioning image
- `cloth` -> garment conditioning image
- `image` -> target person wearing garment
- `cloth_mask` -> optional garment mask
- `pose` -> optional pose conditioning/debug image
- `caption` -> dataset caption

This gives us two useful supervised tasks:

1. **Try-on:** `agnostic person + garment -> target person wearing garment`
2. **Ghost/extract:** `person wearing garment -> isolated garment product image`

The second task is not a perfect ghost mannequin target, but it is good enough for first-pass extraction/garment-preservation debugging. Later we should generate and curate proper ghost mannequin targets using the Qwen teacher.

## Local setup

From `image-edit-service`:

```bash
cd /home/hardik/Projects/wardrub/image-edit-service
source venv/bin/activate
pip install -r training/requirements-training.txt
```

## Step 1: Export a tiny VITON-HD prototype

```bash
python training/datasets/prepare_viton_hd.py \
  --dataset forgeml/viton_hd \
  --output data/viton_hd_proto \
  --max-samples 64
```

Output:

```text
data/viton_hd_proto/
  train/persons/*.png
  train/garments/*.png
  train/targets/*.png
  train/garment_masks/*.png
  train/poses/*.png
  manifests/tryon_train.jsonl
  manifests/ghost_train.jsonl
  manifests/mixed_train.jsonl
  manifests/samples_debug_grid.jpg
```

Use `--max-samples 0` only on RunPod/full runs.

## Step 2: Start local image service

```bash
cd /home/hardik/Projects/wardrub/image-edit-service
source venv/bin/activate
python main.py
```

Recommended local debug `.env`:

```bash
USE_LIGHTNING_LORA=true
NUM_INFERENCE_STEPS=4
ENABLE_CPU_OFFLOAD=false   # local 4090 should usually fit; use true if OOM
OUTPUT_WIDTH=768
OUTPUT_HEIGHT=1024
```

## Step 3: Run service eval on 5 samples

Try-on:

```bash
python training/eval/run_service_eval.py \
  --manifest data/viton_hd_proto/manifests/tryon_train.jsonl \
  --dataset-root data/viton_hd_proto \
  --endpoint try-on \
  --limit 5 \
  --out runs/eval_tryon_proto
```

Ghost/extraction:

```bash
python training/eval/run_service_eval.py \
  --manifest data/viton_hd_proto/manifests/ghost_train.jsonl \
  --dataset-root data/viton_hd_proto \
  --endpoint ghost-mannequin \
  --limit 5 \
  --steps 4 \
  --out runs/eval_ghost_proto
```

This creates output PNGs and `metrics.json` with service/wall-clock latency.

## Step 4: Inspect LoRA target modules

Before implementing/launching the full trainer, inspect Qwen's transformer module names so we target the correct attention/MLP projections:

```bash
python training/scripts/inspect_qwen_modules.py --max-lines 300
```

DiffSynth-Studio's Qwen-Image-Edit-2511 LoRA recipe recommends this serious-run target set:

```text
to_q,to_k,to_v,add_q_proj,add_k_proj,add_v_proj,to_out.0,to_add_out,img_mlp.net.2,img_mod.1,txt_mlp.net.2,txt_mod.1
```

For local 4090 smoke tests, start cheaper with attention-only:

```text
to_q,to_k,to_v,to_out.0,add_q_proj,add_k_proj,add_v_proj,to_add_out
```

Important Qwen-Image-Edit-2511-specific DiffSynth notes:

- Use `--zero_cond_t`; DiffSynth explicitly marks this as required/special for Qwen-Image-Edit-2511.
- Treat edit conditioning as `edit_image` via `--extra_inputs "edit_image"`.
- Use `--data_file_keys "image,edit_image"`.
- For 2511 inference, even a single edit input should be a list: `edit_image=[image]`, not `edit_image=image`.
- Lightning inference uses `FlowMatchScheduler("Qwen-Image-Lightning")` with 4 steps.

## Step 5: No-download quantized LoRA gradient smoke

Before downloading full Qwen training weights, verify LoRA adapter injection and gradient flow on the already-cached 4-bit inference model:

```bash
bash training/runpod/run_quantized_lora_gradient_smoke.sh
```

This writes timestamped logs to:

```text
runs/training/*_quantized_lora_gradient_smoke.log
runs/training/*_quantized_lora_gradient_smoke.metadata.txt
```

It confirms:

- 4-bit Qwen loads locally
- PEFT LoRA injection works
- trainable LoRA params exist
- backward pass produces non-zero LoRA gradients
- optimizer step works
- adapter save works

## Step 6: Export DiffSynth metadata

Convert the prepared Wardrub JSONL manifest into DiffSynth-compatible `metadata.json`:

```bash
python training/datasets/export_diffsynth_metadata.py \
  --manifest data/viton_hd_proto/manifests/tryon_train.jsonl \
  --out data/viton_hd_proto/diffsynth_tryon_metadata.json
```

For ghost/extraction:

```bash
python training/datasets/export_diffsynth_metadata.py \
  --manifest data/viton_hd_proto/manifests/ghost_train.jsonl \
  --out data/viton_hd_proto/diffsynth_ghost_metadata.json
```

DiffSynth mapping:

```text
image      = target/result image
edit_image = conditioning image(s)
prompt     = edit instruction
```

For try-on:

```text
image      = target person wearing garment
edit_image = [agnostic person, flat-lay garment]
```

For ghost/extraction:

```text
image      = isolated garment/product target
edit_image = [person wearing garment]
```

## Step 7: Adapter-stack smoke test

Before training a Wardrub LoRA, confirm the service can stack Lightning + Wardrub adapters:

```bash
python training/scripts/smoke_adapter_stack.py --cpu-offload
```

After we have a trained LoRA directory:

```bash
python training/scripts/smoke_adapter_stack.py \
  --wardrub-lora-path /path/to/wardrub-vton-lora \
  --cpu-offload
```

## LoRA training direction

For the first actual LoRA run, train against `manifests/tryon_train.jsonl` first. The target behavior is:

```text
input images: [agnostic person, garment]
prompt: Wardrub try-on preservation prompt
target: original VITON-HD model image
```

After that, create a curated ghost dataset:

```text
input image: garment/person source image
target image: approved Qwen ghost mannequin output or clean isolated garment
```

Then train either:

- one combined `wardrub-vton-ghost` LoRA, or
- separate `wardrub-tryon` and `wardrub-ghost` LoRAs.

## Speed plan

Short term:

```text
Qwen-Image-Edit-2511 4-bit + Lightning LoRA + Wardrub task LoRA
```

Mid term:

```text
Wardrub-compatible Lightning/LCM LoRA for 2-4 step generation
```

Long term:

```text
Qwen/LoRA teacher -> synthetic dataset -> CNN/feed-forward student distillation
```

Do not start with CNN distillation until we have a high-quality teacher and a clean curated dataset.

## RunPod handoff

Use the scripts in `training/runpod/` after local data/eval is stable.

Recommended first serious instance:

- A100 80GB if training Qwen LoRA directly
- RTX 4090/A100 40GB for dataset export and teacher generation experiments

The RunPod launcher defaults to short test-run settings:

```text
DATASET_REPEAT=1
NUM_EPOCHS=1
```

For longer training, override explicitly:

```bash
DATASET_REPEAT=50 NUM_EPOCHS=5 bash training/runpod/train_diffsynth_qwen_edit_lora.sh
```
