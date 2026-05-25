#!/usr/bin/env bash
set -euo pipefail

# DiffSynth-Studio Qwen-Image-Edit-2511 LoRA training launcher for Wardrub.
# Run from image-edit-service root.
#
# Short test-run defaults are intentional. Override env vars for serious runs.

DATASET_BASE_PATH=${DATASET_BASE_PATH:-data/viton_hd_proto}
METADATA_PATH=${METADATA_PATH:-data/viton_hd_proto/diffsynth_tryon_metadata.json}
OUTPUT_PATH=${OUTPUT_PATH:-models/train/wardrub-qwen-edit-vton-lora}
DIFFSYNTH_DIR=${DIFFSYNTH_DIR:-/workspace/DiffSynth-Studio}
DATASET_REPEAT=${DATASET_REPEAT:-1}
NUM_EPOCHS=${NUM_EPOCHS:-1}
LEARNING_RATE=${LEARNING_RATE:-1e-4}
LORA_RANK=${LORA_RANK:-32}
MAX_PIXELS=${MAX_PIXELS:-1048576}
DATASET_NUM_WORKERS=${DATASET_NUM_WORKERS:-8}
LORA_TARGET_MODULES=${LORA_TARGET_MODULES:-to_q,to_k,to_v,add_q_proj,add_k_proj,add_v_proj,to_out.0,to_add_out,img_mlp.net.2,img_mod.1,txt_mlp.net.2,txt_mod.1}
SAVE_STEPS=${SAVE_STEPS:-}
RUN_ID=${WARDRUB_RUN_ID:-$(date +%Y%m%d_%H%M%S)_qwen_edit_lora}
MONITOR_DIR=${MONITOR_DIR:-runs/training/${RUN_ID}}
PREVIEW_ROWS=${PREVIEW_ROWS:-8}
WARDRUB_ENABLE_DIFFSYNTH_MONITORING=${WARDRUB_ENABLE_DIFFSYNTH_MONITORING:-1}
WARDRUB_ENABLE_TENSORBOARD=${WARDRUB_ENABLE_TENSORBOARD:-1}
WARDRUB_ENABLE_WANDB=${WARDRUB_ENABLE_WANDB:-auto}
WANDB_PROJECT=${WANDB_PROJECT:-wardrub-vton-lora}
WANDB_RUN_GROUP=${WANDB_RUN_GROUP:-runpod-smoke}
WANDB_RUN_NAME=${WANDB_RUN_NAME:-$RUN_ID}
WANDB_RUN_ID=${WANDB_RUN_ID:-$RUN_ID}
WANDB_RESUME=${WANDB_RESUME:-allow}
DIFFSYNTH_DOWNLOAD_SOURCE=${DIFFSYNTH_DOWNLOAD_SOURCE:-huggingface}
HF_XET_HIGH_PERFORMANCE=${HF_XET_HIGH_PERFORMANCE:-1}

export DATASET_BASE_PATH METADATA_PATH OUTPUT_PATH DIFFSYNTH_DIR DATASET_REPEAT NUM_EPOCHS LEARNING_RATE LORA_RANK MAX_PIXELS DATASET_NUM_WORKERS LORA_TARGET_MODULES
export DIFFSYNTH_DOWNLOAD_SOURCE HF_XET_HIGH_PERFORMANCE
export WARDRUB_RUN_ID="$RUN_ID"
export WARDRUB_TRAINING_MONITOR_DIR="$MONITOR_DIR"
export WARDRUB_ENABLE_DIFFSYNTH_MONITORING WARDRUB_ENABLE_TENSORBOARD WARDRUB_ENABLE_WANDB
export WANDB_PROJECT WANDB_RUN_GROUP WANDB_RUN_NAME WANDB_RUN_ID WANDB_RESUME

source training/runpod/logging.sh
init_run_logging "diffsynth_qwen_edit_lora"
trap finish_run_logging EXIT

if [ ! -d "$DIFFSYNTH_DIR" ]; then
  echo "DiffSynth-Studio not found at $DIFFSYNTH_DIR"
  echo "Clone it first: git clone https://github.com/modelscope/DiffSynth-Studio.git $DIFFSYNTH_DIR && cd $DIFFSYNTH_DIR && pip install -e ."
  exit 1
fi

if [ ! -f "$METADATA_PATH" ]; then
  echo "Metadata not found: $METADATA_PATH"
  exit 1
fi

source venv/bin/activate
export TOKENIZERS_PARALLELISM=false
export HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-1}
export PYTHONPATH="$PWD/training/patches:${PYTHONPATH:-}"

log_section "Configuration"
log_kv "DATASET_BASE_PATH" "$DATASET_BASE_PATH"
log_kv "METADATA_PATH" "$METADATA_PATH"
log_kv "OUTPUT_PATH" "$OUTPUT_PATH"
log_kv "DIFFSYNTH_DIR" "$DIFFSYNTH_DIR"
log_kv "DATASET_REPEAT" "$DATASET_REPEAT"
log_kv "NUM_EPOCHS" "$NUM_EPOCHS"
log_kv "LEARNING_RATE" "$LEARNING_RATE"
log_kv "LORA_RANK" "$LORA_RANK"
log_kv "MAX_PIXELS" "$MAX_PIXELS"
log_kv "DATASET_NUM_WORKERS" "$DATASET_NUM_WORKERS"
log_kv "LORA_TARGET_MODULES" "$LORA_TARGET_MODULES"
log_kv "SAVE_STEPS" "${SAVE_STEPS:-epoch-end-only}"
log_kv "RUN_ID" "$RUN_ID"
log_kv "MONITOR_DIR" "$MONITOR_DIR"
log_kv "PREVIEW_ROWS" "$PREVIEW_ROWS"
log_kv "WARDRUB_ENABLE_TENSORBOARD" "$WARDRUB_ENABLE_TENSORBOARD"
log_kv "WARDRUB_ENABLE_WANDB" "$WARDRUB_ENABLE_WANDB"
log_kv "WANDB_PROJECT" "$WANDB_PROJECT"
log_kv "WANDB_RUN_NAME" "$WANDB_RUN_NAME"
log_kv "DIFFSYNTH_DOWNLOAD_SOURCE" "$DIFFSYNTH_DOWNLOAD_SOURCE"
log_kv "HF_XET_HIGH_PERFORMANCE" "$HF_XET_HIGH_PERFORMANCE"

log_system_snapshot

log_section "Metadata sample"
python - <<PY
import json
from pathlib import Path
p = Path("$METADATA_PATH")
rows = json.loads(p.read_text())
print('rows', len(rows))
print(json.dumps(rows[0], indent=2) if rows else '[]')
PY

mkdir -p "$(dirname "$OUTPUT_PATH")" "$MONITOR_DIR"

log_section "Dataset visual preview"
python training/scripts/create_diffsynth_dataset_preview.py \
  --dataset-base-path "$DATASET_BASE_PATH" \
  --metadata-path "$METADATA_PATH" \
  --out-dir "$MONITOR_DIR/previews" \
  --max-rows "$PREVIEW_ROWS" || echo "Dataset preview generation failed; continuing training."

CMD=(
  accelerate launch "$DIFFSYNTH_DIR/examples/qwen_image/model_training/train.py"
  --dataset_base_path "$DATASET_BASE_PATH"
  --dataset_metadata_path "$METADATA_PATH"
  --data_file_keys "image,edit_image"
  --extra_inputs "edit_image"
  --max_pixels "$MAX_PIXELS"
  --dataset_repeat "$DATASET_REPEAT"
  --model_id_with_origin_paths "Qwen/Qwen-Image-Edit-2511:transformer/diffusion_pytorch_model*.safetensors,Qwen/Qwen-Image:text_encoder/model*.safetensors,Qwen/Qwen-Image:vae/diffusion_pytorch_model.safetensors"
  --learning_rate "$LEARNING_RATE"
  --num_epochs "$NUM_EPOCHS"
  --remove_prefix_in_ckpt "pipe.dit."
  --output_path "$OUTPUT_PATH"
  --lora_base_model "dit"
  --lora_target_modules "$LORA_TARGET_MODULES"
  --lora_rank "$LORA_RANK"
  --use_gradient_checkpointing
  --dataset_num_workers "$DATASET_NUM_WORKERS"
  --find_unused_parameters
  --zero_cond_t
)

if [ -n "$SAVE_STEPS" ]; then
  CMD+=(--save_steps "$SAVE_STEPS")
fi

log_section "Launching training"
printf '%q ' "${CMD[@]}"
echo
"${CMD[@]}"
