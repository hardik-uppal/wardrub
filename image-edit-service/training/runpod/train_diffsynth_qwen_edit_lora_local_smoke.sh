#!/usr/bin/env bash
set -euo pipefail

# Local RTX 4090 smoke launcher for DiffSynth Qwen-Image-Edit-2511 LoRA.
# WARNING: this downloads large full Qwen training weights if they are not present.
# For pure no-download local QLoRA plumbing, use:
#   python training/scripts/smoke_quantized_lora_gradient.py

DATASET_BASE_PATH=${DATASET_BASE_PATH:-data/viton_hd_proto}
METADATA_PATH=${METADATA_PATH:-data/viton_hd_proto/diffsynth_tryon_metadata.json}
OUTPUT_PATH=${OUTPUT_PATH:-models/train/wardrub-qwen-edit-vton-lora-local-smoke}
DIFFSYNTH_DIR=${DIFFSYNTH_DIR:-/home/hardik/Projects/DiffSynth-Studio}
DATASET_REPEAT=${DATASET_REPEAT:-1}
NUM_EPOCHS=${NUM_EPOCHS:-1}
LEARNING_RATE=${LEARNING_RATE:-1e-4}
LORA_RANK=${LORA_RANK:-8}
MAX_PIXELS=${MAX_PIXELS:-262144}
DATASET_NUM_WORKERS=${DATASET_NUM_WORKERS:-2}
LORA_TARGET_MODULES=${LORA_TARGET_MODULES:-to_q,to_k,to_v,to_out.0,add_q_proj,add_k_proj,add_v_proj,to_add_out}

source training/runpod/logging.sh
init_run_logging "diffsynth_qwen_edit_lora_local_smoke"
trap finish_run_logging EXIT

if [ ! -d "$DIFFSYNTH_DIR" ]; then
  echo "DiffSynth-Studio not found at $DIFFSYNTH_DIR"
  exit 1
fi

if [ ! -f "$METADATA_PATH" ]; then
  echo "Metadata not found: $METADATA_PATH"
  exit 1
fi

source venv/bin/activate
export TOKENIZERS_PARALLELISM=false
export HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-1}

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

mkdir -p "$(dirname "$OUTPUT_PATH")"

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
  --use_gradient_checkpointing_offload
  --enable_model_cpu_offload
  --enable_optimizer_cpu_offload
  --dataset_num_workers "$DATASET_NUM_WORKERS"
  --find_unused_parameters
  --initialize_model_on_cpu
  --zero_cond_t
)

log_section "Launching training"
printf '%q ' "${CMD[@]}"
echo
"${CMD[@]}"
