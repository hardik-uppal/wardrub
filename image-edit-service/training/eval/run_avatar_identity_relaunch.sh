#!/usr/bin/env bash
set -euo pipefail

cd /home/hardik/Projects/wardrub/image-edit-service
source venv/bin/activate

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
RUN_ROOT=${RUN_ROOT:-runs/benchmarks/${STAMP}_avatar_identity_nolightning_strict_s32}
PORT=${PORT:-8011}
BASE_URL=${BASE_URL:-http://127.0.0.1:${PORT}}
PID_FILE=${PID_FILE:-/tmp/wardrub_avatar_identity_service_${PORT}.pid}
LIMIT=${LIMIT:-24}

MANIFEST=${MANIFEST:-training/benchmarks/avatar_identity_lfw_small_v1_strict_s32.jsonl}

mkdir -p "$RUN_ROOT"

# Start clean dedicated service on a separate port with no Lightning LoRA for quality.
pkill -TERM -f "python main.py" || true
sleep 1

nohup env USE_LIGHTNING_LORA=false NUM_INFERENCE_STEPS=32 PORT="$PORT" python main.py > "$RUN_ROOT/service.log" 2>&1 &
SERVICE_PID=$!
echo "$SERVICE_PID" > "$PID_FILE"

for _ in $(seq 1 180); do
  if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
  echo "service failed to start at $BASE_URL"
  exit 1
fi

{
  echo "run_root=$RUN_ROOT"
  echo "manifest=$MANIFEST"
  echo "limit=$LIMIT"
  echo "started_at=$(date -Is)"
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader || true
} | tee "$RUN_ROOT/_run_info.txt"

python training/eval/run_benchmark_manifest.py \
  --manifest "$MANIFEST" \
  --dataset-root . \
  --base-url "$BASE_URL" \
  --out "$RUN_ROOT/eval" \
  --limit "$LIMIT" \
  | tee "$RUN_ROOT/eval.log"

SUMMARY="$RUN_ROOT/eval/summary.json"
if [ -f "$SUMMARY" ]; then
  COUNT=$(python - <<PY
import json
s=json.load(open('$SUMMARY'))
print(s.get('count',0))
PY
)
  SUCCESS=$(python - <<PY
import json
s=json.load(open('$SUMMARY'))
print(s.get('success_count',0))
PY
)

  python training/experiments/log_experiment.py \
    --task avatar \
    --phase eval \
    --dataset-chunk face_identity_lfw_small_v1 \
    --model-config qwen-4bit-no-lightning \
    --prompt-profile portrait_neutral_strict_v2 \
    --steps 32 \
    --manifest "$MANIFEST" \
    --params-json '{"relaunch":true,"subset":"pilot24","base_url":"dedicated_port"}' \
    --run-dir "$RUN_ROOT/eval" \
    --count "$COUNT" \
    --success-count "$SUCCESS" \
    --notes "Relaunch after identity collapse under lightning config"
fi

{
  echo "finished_at=$(date -Is)"
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader || true
} | tee -a "$RUN_ROOT/_run_info.txt"

kill -TERM "$(cat "$PID_FILE")" || true

echo "done: $RUN_ROOT"
