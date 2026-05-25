#!/usr/bin/env bash
set -euo pipefail

# No-download local QLoRA plumbing smoke test on the already-cached 4-bit Qwen model.
# Run from image-edit-service root:
#   bash training/runpod/run_quantized_lora_gradient_smoke.sh

OUTPUT_PATH=${OUTPUT_PATH:-models/train/wardrub-quantized-lora-gradient-smoke}
MODEL_ID=${MODEL_ID:-toandev/Qwen-Image-Edit-2511-4bit}
LORA_RANK=${LORA_RANK:-8}
LORA_ALPHA=${LORA_ALPHA:-16}
SKIP_SAVE=${SKIP_SAVE:-false}

source training/runpod/logging.sh
init_run_logging "quantized_lora_gradient_smoke"
trap finish_run_logging EXIT

source venv/bin/activate

log_section "Configuration"
log_kv "MODEL_ID" "$MODEL_ID"
log_kv "OUTPUT_PATH" "$OUTPUT_PATH"
log_kv "LORA_RANK" "$LORA_RANK"
log_kv "LORA_ALPHA" "$LORA_ALPHA"
log_kv "SKIP_SAVE" "$SKIP_SAVE"

log_system_snapshot

CMD=(
  python training/scripts/smoke_quantized_lora_gradient.py
  --model-id "$MODEL_ID"
  --output-dir "$OUTPUT_PATH"
  --rank "$LORA_RANK"
  --alpha "$LORA_ALPHA"
)

if [ "$SKIP_SAVE" = "true" ]; then
  CMD+=(--skip-save)
fi

log_section "Launching quantized LoRA gradient smoke"
printf '%q ' "${CMD[@]}"
echo
"${CMD[@]}"
