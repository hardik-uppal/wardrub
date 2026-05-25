#!/usr/bin/env bash
set -euo pipefail

# Run from image-edit-service root on RunPod.
# Example:
#   cd /workspace/wardrub/image-edit-service
#   bash training/runpod/setup_runpod.sh

source training/runpod/logging.sh
init_run_logging "setup_runpod"
trap finish_run_logging EXIT

python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip wheel setuptools

# Service + training deps
pip install -r requirements.txt
pip install -r training/requirements-training.txt

# DiffSynth-Studio install. Use existing clone if present, otherwise clone.
DIFFSYNTH_DIR=${DIFFSYNTH_DIR:-/workspace/DiffSynth-Studio}
if [ ! -d "$DIFFSYNTH_DIR/.git" ]; then
  mkdir -p "$(dirname "$DIFFSYNTH_DIR")"
  git clone https://github.com/modelscope/DiffSynth-Studio.git "$DIFFSYNTH_DIR"
fi
pip install -e "$DIFFSYNTH_DIR"

# Faster HF downloads
pip install hf_transfer || true
export HF_HUB_ENABLE_HF_TRANSFER=1

log_system_snapshot

echo "RunPod setup complete. If needed, run: huggingface-cli login"
echo "DiffSynth-Studio: $DIFFSYNTH_DIR"
