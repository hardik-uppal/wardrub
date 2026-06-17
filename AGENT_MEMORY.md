# Agent Memory Index

Last updated: 2026-06-16

## How To Use

This repository uses module-level agent memory files to avoid rereading the entire codebase every session.

Before editing a module:

1. Read the nearest `AGENT_MEMORY.md` in the target directory.
2. Read parent module memory if relevant.
3. Inspect only the precise source files needed for the task.
4. After meaningful code changes, update affected module memory files.

The project skill that defines this workflow is:

```text
.pi/skills/module-memory/SKILL.md
```

Use it with prompts like:

```text
Use the module-memory skill and map backend/app/routers.
```

or:

```text
Use module-memory before editing backend/app/services and update memory after the task.
```

## Module Memories

| Path | Scope | Status |
|---|---|---|
| `backend/AGENT_MEMORY.md` | Backend architecture and API overview | planned |
| `backend/app/AGENT_MEMORY.md` | FastAPI app architecture | mapped |
| `backend/app/routers/AGENT_MEMORY.md` | API route contracts | mapped |
| `backend/app/services/AGENT_MEMORY.md` | Service layer contracts | planned |
| `backend/app/models/AGENT_MEMORY.md` | Pydantic/domain model contracts | planned |
| `backend/app/jobs/AGENT_MEMORY.md` | Background job behavior | planned |
| `backend/app/middleware/AGENT_MEMORY.md` | Middleware behavior | planned |
| `frontend/AGENT_MEMORY.md` | Frontend app overview | planned |
| `frontend/src/AGENT_MEMORY.md` | React source architecture | planned |
| `frontend/src/context/AGENT_MEMORY.md` | Auth/Wardrobe context contracts | planned |
| `frontend/src/pages/AGENT_MEMORY.md` | Page-level flows | planned |
| `frontend/src/components/AGENT_MEMORY.md` | Reusable UI components | planned |
| `image-edit-service/AGENT_MEMORY.md` | Image edit microservice overview | planned |
| `extension/AGENT_MEMORY.md` | Chrome extension architecture | planned after extension exists |

## Recommended Mapping Order

1. `backend/AGENT_MEMORY.md`
2. `backend/app/routers/AGENT_MEMORY.md`
3. `backend/app/services/AGENT_MEMORY.md`
4. `frontend/AGENT_MEMORY.md`
5. `frontend/src/context/AGENT_MEMORY.md`
6. `frontend/src/pages/AGENT_MEMORY.md`
7. `image-edit-service/AGENT_MEMORY.md`
8. `extension/AGENT_MEMORY.md` once created

## ML Project Standard: Two-Track Parallel Progress

**For every ML project, always advance two tracks in parallel:**

### Track A — Curate Data
Data is the product. Without high-quality eval sets, you cannot make decisions.

**Requirements:**
- A **benchmark manifest** (JSONL) per task with curated input/output pairs
- Benchmarks must be **versioned** and **reproducible** (seeded, fixed steps)
- At minimum: 1 starter manifest (1-2 samples for smoke tests) + 1 small manifest (20-50 samples for decisions) + path to scale (full dataset)
- Include **scoring rubrics** (fidelity, background cleanliness, identity consistency, etc.)
- Data lives in `training/benchmarks/` with assets in `training/benchmarks/assets/`

**Checklist:**
- [ ] Public dataset(s) identified and exported (e.g., VITON-HD)
- [ ] Starter manifest (1-2 samples) working end-to-end
- [ ] Small manifest (20-50 samples) built and validated
- [ ] Scoring rubric defined (CSV or JSON schema)
- [ ] Custom/curated data pipeline scoped with source list

### Track B — Test Pipeline
Every pipeline change must be measurable against Track A benchmarks before shipping.

**Requirements:**
- A **service** running the current model with fixed config (steps, resolution, prompt)
- A **launcher** that runs the benchmark manifest against the service and saves outputs + metrics
- A **comparison** method (side-by-side images or scoring sheet) to judge A vs B
- Every experiment gets a **dated run directory** under `runs/`

**Checklist:**
- [ ] Service starts and serves all endpoints (try-on, ghost, edit)
- [ ] Smoke test passes on starter manifest
- [ ] Full benchmark runs on small manifest and produces metrics
- [ ] At least 1 experiment comparing two configs (e.g., lightning vs no-lightning) completed
- [ ] Comparison gallery or scoring sheet filled out

### Decision Gate
You ship a change when:
1. Track A has a benchmark that measures the thing you're improving
2. Track B runs that benchmark on both old and new config
3. The comparison shows a clear win (or at minimum, no regression)

**Without both tracks, you are guessing. With both tracks, you are engineering.**

---

## Companion Skills

| Skill | Purpose |
|---|---|
| `module-memory` | Maintains module-level `AGENT_MEMORY.md` files |
| `product-plan-compactor` | Executes long plans task-by-task and keeps progress ledgers |

When implementing product plans, use both skills:

- Update `docs/progress/*-PROGRESS.md` for plan execution state.
- Update module `AGENT_MEMORY.md` files for durable codebase context.
