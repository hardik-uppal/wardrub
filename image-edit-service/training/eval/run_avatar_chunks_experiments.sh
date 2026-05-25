#!/usr/bin/env bash
set -euo pipefail

cd /home/hardik/Projects/wardrub/image-edit-service
source venv/bin/activate

STAMP=${STAMP:-$(date +%Y%m%d_%H%M%S)}
RUN_ROOT=${RUN_ROOT:-runs/benchmarks/${STAMP}_avatar_chunks_qwen4bit_lightning}
BASE_URL=${BASE_URL:-http://127.0.0.1:8001}
PID_FILE=${PID_FILE:-/tmp/wardrub_avatar_chunks_service.pid}

mkdir -p "$RUN_ROOT"

SERVICE_STARTED_BY_SCRIPT=0
if ! curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
  echo "[avatar-chunks] starting image-edit-service..."
  nohup python main.py > "$RUN_ROOT/service.log" 2>&1 &
  SERVICE_PID=$!
  echo "$SERVICE_PID" > "$PID_FILE"
  SERVICE_STARTED_BY_SCRIPT=1

  for _ in $(seq 1 180); do
    if curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
      echo "[avatar-chunks] service healthy"
      break
    fi
    sleep 2
  done
fi

if ! curl -fsS "$BASE_URL/health" >/dev/null 2>&1; then
  echo "[avatar-chunks] ERROR: service not healthy at $BASE_URL"
  exit 1
fi

{
  echo "run_root=$RUN_ROOT"
  echo "base_url=$BASE_URL"
  echo "started_at=$(date -Is)"
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader || true
} | tee "$RUN_ROOT/_run_info.txt"

run_chunk() {
  local chunk_name=$1
  local manifest=$2
  local out_dir="$RUN_ROOT/$chunk_name"
  local log_file="$RUN_ROOT/${chunk_name}.log"

  python training/eval/run_benchmark_manifest.py \
    --manifest "$manifest" \
    --dataset-root . \
    --base-url "$BASE_URL" \
    --out "$out_dir" \
    | tee "$log_file"

  local summary="$out_dir/summary.json"
  if [ -f "$summary" ]; then
    local count success
    count=$(python - <<PY
import json
s=json.load(open('$summary'))
print(s.get('count',0))
PY
)
    success=$(python - <<PY
import json
s=json.load(open('$summary'))
print(s.get('success_count',0))
PY
)

    python training/experiments/log_experiment.py \
      --task avatar \
      --phase eval \
      --dataset-chunk "$chunk_name" \
      --model-config "qwen-4bit+lightning" \
      --prompt-profile "$(basename "$manifest" .jsonl)" \
      --steps 24 \
      --manifest "$manifest" \
      --params-json '{"runner":"run_avatar_chunks_experiments.sh","base_url":"http://127.0.0.1:8001"}' \
      --run-dir "$out_dir" \
      --count "$count" \
      --success-count "$success" \
      --notes "avatar chunk benchmark"
  fi
}

run_chunk "face_identity_lfw_small_v1" "training/benchmarks/avatar_identity_lfw_small_v1.jsonl"
run_chunk "fullbody_viton_small_v1" "training/benchmarks/avatar_fullbody_viton_small_v1.jsonl"

{
  echo "finished_at=$(date -Is)"
  nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu,power.draw --format=csv,noheader || true
} | tee -a "$RUN_ROOT/_run_info.txt"

if [[ "$SERVICE_STARTED_BY_SCRIPT" == "1" ]]; then
  echo "[avatar-chunks] stopping service pid=$(cat "$PID_FILE")"
  kill -TERM "$(cat "$PID_FILE")" || true
fi

echo "[avatar-chunks] done: $RUN_ROOT"
