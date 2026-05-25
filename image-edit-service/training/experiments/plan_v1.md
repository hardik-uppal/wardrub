# Plan v1

## Current findings

- Ghost outputs from baseline often keep mannequin/person artifacts and are not standardized enough.
- Avatar quality drops on non-neutral poses; face clarity + identity consistency are weak.

## Hypotheses

1. **Inference config bottleneck**: 4bit + lightning 4-step is too quality-constrained for ghost/avatar tasks.
2. **Prompt bottleneck**: task-specific prompt profiles can significantly improve canonical outputs.
3. **Data bottleneck (avatar identity)**: we need multi-image same-identity eval set; VITON proto is not identity-labeled for this purpose.

## Experiment matrix (next)

### E-20260522-01 (ghost quality sweep)
- Task: ghost
- Set: `training/benchmarks/ghost_test_v1.jsonl` (or 20-sample subset)
- Variants:
  - A: current baseline (lightning, step=4 default)
  - B: no-lightning, step=24
  - C: no-lightning, step=32 + strict canonical prompt profile
- Measure: pass rate + fidelity + background cleanliness + artifact leakage

### E-20260522-02 (avatar identity baseline)
- Build `avatar_identity_v1.jsonl` from folder with per-identity subdirs
- Use 3-5 images per identity
- Evaluate neutral avatar generation from each image
- Measure: identity consistency, face clarity, pose normalization quality

### E-20260522-03 (people+ghost -> final look)
- Keep VITON person image as avatar input
- Compare garment input:
  - native garment image
  - generated ghost image from same garment
- Measure: final look fidelity, garment detail retention
