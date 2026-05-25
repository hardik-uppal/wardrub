#!/usr/bin/env bash
set -euo pipefail

cd /home/hardik/Projects/wardrub/image-edit-service
source venv/bin/activate

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
RUN_ROOT=${RUN_ROOT:-runs/benchmarks/${STAMP}_qwen_base_v1}
BASE_URL=${BASE_URL:-http://127.0.0.1:8001}
PID_FILE=${PID_FILE:-/tmp/wardrub_benchmark_service.pid}

mkdir -p "$RUN_ROOT"

SERVICE_STARTED_BY_SCRIPT=0
if ! curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
  echo "[bench] starting image-edit-service..."
  nohup python main.py > "$RUN_ROOT/service.log" 2>&1 &
  SERVICE_PID=$!
  echo "$SERVICE_PID" > "$PID_FILE"
  SERVICE_STARTED_BY_SCRIPT=1

  for i in $(seq 1 180); do
    if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
      echo "[bench] service healthy"
      break
    fi
    sleep 2
  done
fi

if ! curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
  echo "[bench] ERROR: service not healthy at $BASE_URL"
  exit 1
fi

{
  echo "run_root=$RUN_ROOT"
  echo "base_url=$BASE_URL"
  echo "started_at=$(date -Is)"
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader || true
} | tee "$RUN_ROOT/_run_info.txt"

python training/eval/run_benchmark_manifest.py \
  --manifest training/benchmarks/ghost_test_v1.jsonl \
  --dataset-root . \
  --base-url "$BASE_URL" \
  --out "$RUN_ROOT/ghost" \
  | tee "$RUN_ROOT/ghost.log"

python training/eval/run_benchmark_manifest.py \
  --manifest training/benchmarks/look_test_v1.jsonl \
  --dataset-root . \
  --base-url "$BASE_URL" \
  --out "$RUN_ROOT/look" \
  | tee "$RUN_ROOT/look.log"

python training/eval/run_benchmark_manifest.py \
  --manifest training/benchmarks/avatar_test_v1.jsonl \
  --dataset-root . \
  --base-url "$BASE_URL" \
  --out "$RUN_ROOT/avatar" \
  | tee "$RUN_ROOT/avatar.log"

{
  echo "finished_at=$(date -Is)"
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader || true
} | tee -a "$RUN_ROOT/_run_info.txt"

if [[ "$SERVICE_STARTED_BY_SCRIPT" == "1" ]]; then
  echo "[bench] stopping service pid=$(cat "$PID_FILE")"
  kill -TERM "$(cat "$PID_FILE")" || true
fi

echo "[bench] done: $RUN_ROOT"
