# Wardrub Qwen LoRA RunPod Quickstart

This is the fast path to run a short DiffSynth Qwen-Image-Edit-2511 LoRA job on RunPod with proper logs.

## Recommended pod

- A100 80GB preferred for first serious Qwen LoRA run
- A100 40GB may work with smaller settings/offload
- Use a PyTorch CUDA image with Python 3.10+
- Persistent volume recommended: 250-300GB for first Qwen run/model cache
- Account balance must be funded before API pod creation
- Add an SSH public key in RunPod account settings if you want `ssh`/`rsync` access

## 1. Clone/copy Wardrub onto pod

Example if using git:

```bash
cd /workspace
git clone <wardrub-repo-url> wardrub
cd /workspace/wardrub/image-edit-service
```

If copying manually, make sure this folder exists:

```text
/workspace/wardrub/image-edit-service
```

## 2. Setup environment

```bash
cd /workspace/wardrub/image-edit-service
bash training/runpod/setup_runpod.sh
```

Logs will be written to:

```text
runs/training/<timestamp>_setup_runpod.log
runs/training/<timestamp>_setup_runpod.metadata.txt
```

## 3. Prepare dataset

For a quick 64-sample test:

```bash
source venv/bin/activate
python training/datasets/prepare_viton_hd.py \
  --dataset forgeml/viton_hd \
  --output data/viton_hd_proto \
  --max-samples 64

python training/datasets/export_diffsynth_metadata.py \
  --manifest data/viton_hd_proto/manifests/tryon_train.jsonl \
  --out data/viton_hd_proto/diffsynth_tryon_metadata.json
```

For a full VITON-HD export:

```bash
source venv/bin/activate
python training/datasets/prepare_viton_hd.py \
  --dataset forgeml/viton_hd \
  --output data/viton_hd_full \
  --max-samples 0

python training/datasets/export_diffsynth_metadata.py \
  --manifest data/viton_hd_full/manifests/tryon_train.jsonl \
  --out data/viton_hd_full/diffsynth_tryon_metadata.json
```

## 4. Quick RunPod smoke training

This runs one short epoch with DiffSynth's recommended Qwen-Image-Edit-2511 target modules.

```bash
cd /workspace/wardrub/image-edit-service

DATASET_BASE_PATH=data/viton_hd_proto \
METADATA_PATH=data/viton_hd_proto/diffsynth_tryon_metadata.json \
OUTPUT_PATH=models/train/wardrub-qwen-edit-vton-lora-runpod-smoke \
DATASET_REPEAT=1 \
NUM_EPOCHS=1 \
LORA_RANK=16 \
MAX_PIXELS=524288 \
DATASET_NUM_WORKERS=4 \
DIFFSYNTH_DIR=/workspace/DiffSynth-Studio \
WARDRUB_ENABLE_WANDB=auto \
WANDB_PROJECT=wardrub-vton-lora \
bash training/runpod/train_diffsynth_qwen_edit_lora.sh
```

Logs:

```text
runs/training/<timestamp>_diffsynth_qwen_edit_lora.log
runs/training/<timestamp>_diffsynth_qwen_edit_lora.metadata.txt
runs/training/<run_id>/loss.csv
runs/training/<run_id>/tensorboard/
runs/training/<run_id>/previews/contact_sheet.jpg
runs/training/<run_id>/previews/preview_*.jpg
```

If `WANDB_API_KEY` is set, the wrapper also logs dataset preview images and `train/loss` to WandB. If no WandB key is set, the same information is still available locally via CSV, TensorBoard, and JPEG previews.

Output adapter/checkpoints:

```text
models/train/wardrub-qwen-edit-vton-lora-runpod-smoke
```

## 5. Longer first run

Only after the smoke run succeeds:

```bash
DATASET_BASE_PATH=data/viton_hd_full \
METADATA_PATH=data/viton_hd_full/diffsynth_tryon_metadata.json \
OUTPUT_PATH=models/train/wardrub-qwen-edit-vton-lora-vitonhd-r32 \
DATASET_REPEAT=10 \
NUM_EPOCHS=1 \
LORA_RANK=32 \
MAX_PIXELS=1048576 \
DATASET_NUM_WORKERS=8 \
DIFFSYNTH_DIR=/workspace/DiffSynth-Studio \
bash training/runpod/train_diffsynth_qwen_edit_lora.sh
```

Avoid jumping straight to `DATASET_REPEAT=50 NUM_EPOCHS=5`; that can produce a lot of runtime/checkpoints. Start small.

## 6. What gets logged

Each run captures:

- run id
- full command
- git status
- disk usage
- GPU / VRAM
- Python / torch / CUDA
- selected env vars
- metadata sample
- dataset visual previews/contact sheet
- per-step loss in stdout as `WARDRUB_TRAINING_METRIC step=... loss=...`
- per-step loss CSV at `runs/training/<run_id>/loss.csv`
- TensorBoard scalar logs at `runs/training/<run_id>/tensorboard/`
- optional WandB dataset images + `train/loss`
- output path listing
- exit code

Monitor live:

```bash
tail -f runs/training/*_diffsynth_qwen_edit_lora.log
watch -n 2 nvidia-smi
# If using TensorBoard:
tensorboard --logdir runs/training --host 0.0.0.0 --port 6006
```

## 7. Copy results back

From local machine:

```bash
rsync -avP <pod>:/workspace/wardrub/image-edit-service/models/train/wardrub-qwen-edit-vton-lora-runpod-smoke/ ./runpod-results/
rsync -avP <pod>:/workspace/wardrub/image-edit-service/runs/training/ ./runpod-logs/
```
