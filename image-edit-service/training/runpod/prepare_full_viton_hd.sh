#!/usr/bin/env bash
set -euo pipefail

# Run from image-edit-service root after setup_runpod.sh.
source venv/bin/activate
export HF_HUB_ENABLE_HF_TRANSFER=1

# max-samples 0 means full split.
python training/datasets/prepare_viton_hd.py \
  --dataset forgeml/viton_hd \
  --output data/viton_hd_full \
  --max-samples 0

echo "Full VITON-HD export complete: data/viton_hd_full"
