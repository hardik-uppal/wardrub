#!/usr/bin/env bash
set -euo pipefail
# ================================================================
# Wardrub — Full-precision Qwen baseline + Try-On LoRA training
# Runs on RunPod A100 80GB
# ================================================================

export HOME=/root
export DEBIAN_FRONTEND=noninteractive
THIS_DIR=$(cd "$(dirname "$0")" && pwd)
REPO_ROOT=/workspace/wardrub
IMAGE_SERVICE_DIR="$REPO_ROOT/image-edit-service"
DIFFSYNTH_DIR=${DIFFSYNTH_DIR:-/workspace/DiffSynth-Studio}

# ---- Config ----
BENCHMARKS=( \
  "ghost_test_v1.jsonl:ghost-mannequin:24" \
  "avatar_test_v1.jsonl:edit:24" \
  "look_test_v1.jsonl:try-on:24" \
)
BASELINE_RUN_ID="baseline_fp32_$(date +%Y%m%d_%H%M%S)"
LORA_OUTPUT="models/train/wardrub-tryon-lora-v1"

echo "============================================"
echo " WARDRUB — Baseline + LoRA Pipeline"
echo " RunPod A100 80GB"
echo "============================================"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
df -h /workspace | tail -1

# ---- 1. Clone & Setup ----
echo ""
echo "=== 1. SETUP ==="

if [ ! -d "$REPO_ROOT/.git" ]; then
  git clone https://github.com/hardikuppal/wardrub.git "$REPO_ROOT"
fi
cd "$IMAGE_SERVICE_DIR"

if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q --upgrade pip wheel setuptools
pip install -q -r requirements.txt
pip install -q -r training/requirements-training.txt
pip install -q hf_transfer wandb py-cpuinfo

if [ ! -d "$DIFFSYNTH_DIR/.git" ]; then
  git clone https://github.com/modelscope/DiffSynth-Studio.git "$DIFFSYNTH_DIR"
fi
pip install -q -e "$DIFFSYNTH_DIR"

export HF_HUB_ENABLE_HF_TRANSFER=1
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH="$IMAGE_SERVICE_DIR/training/patches:${PYTHONPATH:-}"

echo "Setup complete."

# ---- 2. Prepare Data ----
echo ""
echo "=== 2. DATA PREP ==="

if [ ! -d data/viton_hd_proto/train/garments ] || [ -z "$(ls -A data/viton_hd_proto/train/garments 2>/dev/null)" ]; then
  echo "Downloading VITON-HD (128 samples)..."
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

python -c "
import json
meta = json.load(open('data/viton_hd_proto/diffsynth_tryon_metadata.json'))
print(f'Training samples ready: {len(meta)}')
"

# ---- 3. Start full-precision Qwen service ----
echo ""
echo "=== 3. STARTING FULL-PRECISION QWEN SERVICE ==="

# Override env for full-precision (no 4-bit, no lightning)
export MODEL_ID="Qwen/Qwen-Image-Edit-2511"
export USE_LIGHTNING_LORA=false
export NUM_INFERENCE_STEPS=28
export OUTPUT_WIDTH=768
export OUTPUT_HEIGHT=1024
export ENABLE_CPU_OFFLOAD=false
export PREPROCESS_MODE=native

echo "Model: $MODEL_ID"
echo "Steps: $NUM_INFERENCE_STEPS"
echo "Lightning: $USE_LIGHTNING_LORA"

# Generate a .env file so the service picks up the overrides
cat > .env << EOF
MODEL_ID=$MODEL_ID
USE_LIGHTNING_LORA=$USE_LIGHTNING_LORA
NUM_INFERENCE_STEPS=$NUM_INFERENCE_STEPS
OUTPUT_WIDTH=$OUTPUT_WIDTH
OUTPUT_HEIGHT=$OUTPUT_HEIGHT
ENABLE_CPU_OFFLOAD=$ENABLE_CPU_OFFLOAD
PREPROCESS_MODE=$PREPROCESS_MODE
EOF

python main.py --port 8012 --host 0.0.0.0 > /tmp/service.log 2>&1 &
SERVICE_PID=$!
echo "Service PID: $SERVICE_PID"

# Wait for service to be ready (full model download takes a few minutes)
echo "Waiting for service (downloading full model ~30GB, may take 5-10 min)..."
for i in $(seq 1 300); do
  if curl -s http://localhost:8012/health > /dev/null 2>&1; then
    echo "Service ready after ${i}s"
    break
  fi
  if ! kill -0 $SERVICE_PID 2>/dev/null; then
    echo "SERVICE DIED! Check /tmp/service.log"
    tail -50 /tmp/service.log
    exit 1
  fi
  sleep 2
  if [ $((i % 15)) -eq 0 ]; then echo "  still waiting... ($((i*2))s, GPU mem: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader))"; fi
done

# ---- 4. Run all benchmarks (full-precision baseline) ----
echo ""
echo "=== 4. RUNNING FULL-PRECISION BASELINE BENCHMARKS ==="

for bench_spec in "${BENCHMARKS[@]}"; do
  IFS=':' read -r manifest endpoint limit <<< "$bench_spec"
  echo ""
  echo "--- Benchmark: $manifest ($endpoint, limit=$limit) ---"
  
  python training/eval/run_benchmark_manifest.py \
    --manifest "training/benchmarks/$manifest" \
    --dataset-root . \
    --base-url http://localhost:8012 \
    --endpoint "$endpoint" \
    --limit "$limit" \
    --seed-start 42 \
    --out "runs/benchmarks/${BASELINE_RUN_ID}_${manifest%.jsonl}"
done

echo ""
echo "Baseline benchmarks complete."

# ---- 5. Train Try-On LoRA ----
echo ""
echo "=== 5. TRAINING TRY-ON LORA ==="

export WANDB_PROJECT="${WANDB_PROJECT:-wardrub-vton-lora}"
export WANDB_RUN_GROUP="${WANDB_RUN_GROUP:-june-v1}"
export WANDB_RUN_NAME="${WANDB_RUN_NAME:-tryon-lora-rank32}"

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
  --output_path "$LORA_OUTPUT" \
  --lora_base_model "dit" \
  --lora_target_modules "${LORA_TARGET_MODULES:-to_q,to_k,to_v,add_q_proj,add_k_proj,add_v_proj,to_out.0,to_add_out,img_mlp.net.2,img_mod.1,txt_mlp.net.2,txt_mod.1}" \
  --lora_rank ${LORA_RANK:-32} \
  --use_gradient_checkpointing \
  --dataset_num_workers ${DATASET_NUM_WORKERS:-8} \
  --find_unused_parameters \
  --zero_cond_t \
  --save_steps 500

echo ""
echo "=== DONE ==="
echo "LoRA saved: $LORA_OUTPUT"
echo "Baseline images: runs/benchmarks/${BASELINE_RUN_ID}_*"

# Stop service
kill $SERVICE_PID 2>/dev/null || true
