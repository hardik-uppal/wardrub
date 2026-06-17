#!/usr/bin/env bash
set -euo pipefail
# ============================================================
# Wardrub Qwen LoRA — One-shot setup + train on RunPod
# ============================================================
export HOME=/root
export DEBIAN_FRONTEND=noninteractive

echo "=== SYSTEM ==="
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo "Disk:"
df -h /workspace

# ---- Clone repo if not present ----
if [ ! -d /workspace/wardrub ]; then
  echo "=== CLONING WARDUB ==="
  git clone https://github.com/hardikuppal/wardrub.git /workspace/wardrub
fi
cd /workspace/wardrub/image-edit-service

# ---- Python venv ----
if [ ! -d venv ]; then
  echo "=== CREATING VENV ==="
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip wheel setuptools

# ---- Install deps ----
echo "=== INSTALLING DEPS ==="
pip install -r requirements.txt
pip install -r training/requirements-training.txt

# ---- DiffSynth ----
DIFFSYNTH_DIR=${DIFFSYNTH_DIR:-/workspace/DiffSynth-Studio}
if [ ! -d "$DIFFSYNTH_DIR/.git" ]; then
  echo "=== CLONING DIFFSYNTH ==="
  git clone https://github.com/modelscope/DiffSynth-Studio.git "$DIFFSYNTH_DIR"
fi
pip install -e "$DIFFSYNTH_DIR"
pip install hf_transfer wandb

# ---- Prepare dataset ----
echo "=== PREPARING DATA ==="
if [ ! -d data/viton_hd_proto/train/garments ] || [ -z "$(ls -A data/viton_hd_proto/train/garments 2>/dev/null)" ]; then
  python training/datasets/prepare_viton_hd.py \
    --dataset forgeml/viton_hd \
    --output data/viton_hd_proto \
    --max-samples 128
fi

if [ ! -f data/viton_hd_proto/diffsynth_tryon_metadata.json ]; then
  python training/datasets/export_diffsynth_metadata.py \
    --manifest data/viton_hd_proto/manifests/tryon_train.jsonl \
    --out data/viton_hd_proto/diffsynth_tryon_metadata.json
fi

echo "=== DATASET READY ==="
python -c "
import json
meta = json.load(open('data/viton_hd_proto/diffsynth_tryon_metadata.json'))
print(f'Training samples: {len(meta)}')
"

# ---- TRAIN ----
echo "=== STARTING TRAINING ==="
echo "WANDB project: ${WANDB_PROJECT:-wardrub-vton-lora}"
echo "WANDB run: ${WANDB_RUN_NAME:-june-v1-full}"

export TOKENIZERS_PARALLELISM=false
export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONPATH="/workspace/wardrub/image-edit-service/training/patches:${PYTHONPATH:-}"

accelerate launch "$DIFFSYNTH_DIR/examples/qwen_image/model_training/train.py" \
  --dataset_base_path data/viton_hd_proto \
  --dataset_metadata_path data/viton_hd_proto/diffsynth_tryon_metadata.json \
  --data_file_keys "image,edit_image" \
  --extra_inputs "edit_image" \
  --max_pixels 1048576 \
  --dataset_repeat ${DATASET_REPEAT:-50} \
  --model_id_with_origin_paths "Qwen/Qwen-Image-Edit-2511:transformer/diffusion_pytorch_model*.safetensors,Qwen/Qwen-Image:text_encoder/model*.safetensors,Qwen/Qwen-Image:vae/diffusion_pytorch_model.safetensors" \
  --learning_rate ${LEARNING_RATE:-1e-4} \
  --num_epochs ${NUM_EPOCHS:-5} \
  --remove_prefix_in_ckpt "pipe.dit." \
  --output_path models/train/wardrub-qwen-edit-vton-lora-june-v1 \
  --lora_base_model "dit" \
  --lora_target_modules "${LORA_TARGET_MODULES:-to_q,to_k,to_v,add_q_proj,add_k_proj,add_v_proj,to_out.0,to_add_out,img_mlp.net.2,img_mod.1,txt_mlp.net.2,txt_mod.1}" \
  --lora_rank ${LORA_RANK:-32} \
  --use_gradient_checkpointing \
  --dataset_num_workers ${DATASET_NUM_WORKERS:-8} \
  --find_unused_parameters \
  --zero_cond_t \
  --save_steps 500

echo "=== DONE ==="
ls -la models/train/wardrub-qwen-edit-vton-lora-june-v1/
