# Experiment Tracking

Use this folder to track every benchmark/training experiment.

## Files

- `registry.csv` — one row per experiment run
- `plan_v1.md` — active hypothesis + test matrix
- `log_experiment.py` — helper to append rows to `registry.csv`

## Experiment ID format (informative)

We now use informative IDs with task/chunk/model/prompt/steps:

`exp__YYYYMMDD-HHMM__<task>__<dataset_chunk>__<model_config>__<prompt_profile>__s<steps>__<phase>`

Example:

`exp__20260524-0510__avatar__face-identity-lfw-small-v1__qwen-4bit-no-lightning__portrait-neutral-v2__s24__eval`

You can pass `--experiment-id` manually, or let `log_experiment.py` auto-generate from args.

## Minimum fields to log

- experiment_id
- task (`ghost` / `look` / `avatar`)
- dataset chunk (`face_identity_lfw_small_v1`, `fullbody_viton_small_v1`, etc.)
- model config (`4bit+lightning`, `4bit-no-lightning`, etc.)
- prompt profile (`ghost_canonical_v2`, `portrait_neutral_v1`, ...)
- steps
- dataset/manifest
- output run dir
- pass/fail summary + notes

## Logging command template

```bash
python training/experiments/log_experiment.py \
  --task avatar \
  --phase eval \
  --dataset-chunk face_identity_lfw_small_v1 \
  --model-config qwen-4bit-no-lightning \
  --prompt-profile portrait_neutral_v1 \
  --steps 24 \
  --manifest training/benchmarks/avatar_identity_lfw_small_v1.jsonl \
  --run-dir runs/benchmarks/<run_name>/avatar_identity \
  --count 48 \
  --success-count 45 \
  --notes "identity preserved on neutral poses, weak on profile faces"
```
