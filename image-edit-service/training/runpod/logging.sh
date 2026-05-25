#!/usr/bin/env bash
# Shared logging helpers for Wardrub image-edit training scripts.
# Source this file from scripts run at image-edit-service root.

set -o pipefail

init_run_logging() {
  local default_name="${1:-run}"
  RUN_ID="${RUN_ID:-$(date +%Y%m%d_%H%M%S)_${default_name}}"
  LOG_ROOT="${LOG_ROOT:-runs/training}"
  mkdir -p "$LOG_ROOT"
  LOG_FILE="${LOG_FILE:-$LOG_ROOT/${RUN_ID}.log}"
  METADATA_FILE="${METADATA_FILE:-$LOG_ROOT/${RUN_ID}.metadata.txt}"

  # Tee all stdout/stderr into a timestamped log file.
  exec > >(tee -a "$LOG_FILE") 2>&1

  echo "============================================================"
  echo "Wardrub training run"
  echo "run_id: $RUN_ID"
  echo "started_at: $(date -Is)"
  echo "cwd: $(pwd)"
  echo "log_file: $LOG_FILE"
  echo "metadata_file: $METADATA_FILE"
  echo "============================================================"
}

log_section() {
  echo
  echo "============================================================"
  echo "$*"
  echo "============================================================"
}

log_kv() {
  printf '%-32s %s\n' "$1:" "$2"
}

log_system_snapshot() {
  {
    echo "# Run metadata"
    echo "run_id=$RUN_ID"
    echo "started_at=$(date -Is)"
    echo "cwd=$(pwd)"
    echo
    echo "# Git"
    git rev-parse --show-toplevel 2>/dev/null || true
    git rev-parse --short HEAD 2>/dev/null || true
    git status --short 2>/dev/null || true
    echo
    echo "# Disk"
    df -h /home . 2>/dev/null || df -h
    echo
    echo "# GPU"
    nvidia-smi 2>/dev/null || true
    echo
    echo "# Python"
    command -v python || true
    python --version 2>/dev/null || true
    python - <<'PY' 2>/dev/null || true
import torch
print('torch', torch.__version__)
print('cuda_available', torch.cuda.is_available())
if torch.cuda.is_available():
    print('gpu', torch.cuda.get_device_name(0))
    print('vram_gb', round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2))
PY
    echo
    echo "# Selected environment"
    env | sort | grep -E '^(RUN_ID|LOG_ROOT|DATASET_BASE_PATH|METADATA_PATH|OUTPUT_PATH|DIFFSYNTH_DIR|DATASET_REPEAT|NUM_EPOCHS|LEARNING_RATE|LORA_RANK|MAX_PIXELS|DATASET_NUM_WORKERS|HF_HOME|HF_HUB_CACHE|HF_HUB_ENABLE_HF_TRANSFER|MODELSCOPE_CACHE|CUDA_VISIBLE_DEVICES|WANDB|TOKENIZERS_PARALLELISM)=' || true
  } | tee "$METADATA_FILE"
}

log_training_outputs() {
  log_section "Training outputs"
  if [ -n "${OUTPUT_PATH:-}" ]; then
    log_kv "OUTPUT_PATH" "$OUTPUT_PATH"
    du -sh "$OUTPUT_PATH" 2>/dev/null || true
    find "$OUTPUT_PATH" -maxdepth 3 -type f 2>/dev/null | sort | head -n 80 || true
  fi
  log_kv "LOG_FILE" "${LOG_FILE:-}"
  log_kv "METADATA_FILE" "${METADATA_FILE:-}"
}

finish_run_logging() {
  local exit_code=$?
  log_section "Run finished"
  echo "finished_at: $(date -Is)"
  echo "exit_code: $exit_code"
  df -h /home . 2>/dev/null || df -h
  nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || true
  log_training_outputs || true
  exit "$exit_code"
}
