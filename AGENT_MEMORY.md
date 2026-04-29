# Agent Memory Index

Last updated: 2026-04-28

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
| `backend/app/AGENT_MEMORY.md` | FastAPI app architecture | planned |
| `backend/app/routers/AGENT_MEMORY.md` | API route contracts | planned |
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

## Companion Skills

| Skill | Purpose |
|---|---|
| `module-memory` | Maintains module-level `AGENT_MEMORY.md` files |
| `product-plan-compactor` | Executes long plans task-by-task and keeps progress ledgers |

When implementing product plans, use both skills:

- Update `docs/progress/*-PROGRESS.md` for plan execution state.
- Update module `AGENT_MEMORY.md` files for durable codebase context.
