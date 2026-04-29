---
name: module-memory
description: Use when building, exploring, refactoring, or debugging a codebase and the user wants compact agent-friendly memory at module/package/folder level. Creates and maintains AGENT_MEMORY.md files inside modules so future agent sessions can understand architecture, contracts, entrypoints, dependencies, gotchas, and safe modification rules without rereading the entire codebase.
---

# Module Memory

Use this skill to create and maintain compact, module-level codebase memory files for agents.

The goal is to make the codebase easier for future sessions to navigate by storing durable summaries next to the code they describe.

## Core Idea

For each meaningful module/package/folder, maintain a small file named:

```text
AGENT_MEMORY.md
```

The file lives inside the module it describes, for example:

```text
backend/AGENT_MEMORY.md
backend/app/routers/AGENT_MEMORY.md
backend/app/services/AGENT_MEMORY.md
frontend/src/context/AGENT_MEMORY.md
frontend/src/pages/AGENT_MEMORY.md
image-edit-service/AGENT_MEMORY.md
```

These files should be:

- Compact.
- Accurate.
- Durable.
- Useful to coding agents.
- Updated whenever the module changes meaningfully.

They should not replace source code or human docs. They are a navigation and compaction layer.

## When To Use

Use this skill when the user asks to:

- Build or maintain codebase memory.
- Compact module knowledge.
- Create agent-friendly documentation.
- Explore a repo before implementation.
- Continue work without rereading the whole codebase.
- Update context after changing a module.
- Generate summaries for backend/frontend/services/routers/components.

Example prompts:

```text
Use the module-memory skill and map the backend services folder.
```

```text
Before implementing this task, read relevant AGENT_MEMORY.md files and update them after changes.
```

```text
Create module memories for the Wardrub backend, one folder at a time.
```

## Core Rules

1. **Prefer local memory before broad reading.**
   - Before working in a module, check for `AGENT_MEMORY.md` in that module and parent modules.
   - If memory exists, read it first.
   - Then inspect only the specific source files needed for the task.

2. **Create memory incrementally.**
   - Do not attempt to summarize the whole repository in one massive pass unless explicitly asked.
   - Work module by module.
   - Start at high-value boundaries: backend app, routers, services, frontend context, frontend pages/components.

3. **Store memory next to the code.**
   - Put `AGENT_MEMORY.md` in the module directory it describes.
   - Do not put all module memories into one central file.
   - A root index is allowed but should only link to module memories.

4. **Keep memory compact.**
   - Capture durable structure and contracts, not line-by-line code summaries.
   - Prefer bullets and tables.
   - Avoid long reasoning traces.
   - Avoid copying large chunks of source code.

5. **Update memory after meaningful changes.**
   - If you add/change endpoints, models, services, config, commands, APIs, state contracts, or data flow, update the relevant module memory.
   - If a change affects multiple modules, update each affected module memory.

6. **Record uncertainty clearly.**
   - If behavior is inferred but not verified, mark it as `Inferred`.
   - If something needs runtime verification, add it to `Open Questions` or `Verification Notes`.

7. **Do not store secrets.**
   - Never include actual tokens, keys, service account contents, private URLs with credentials, or `.env` values.
   - It is okay to document env var names and their purpose.

## Module Memory Template

Use this template for each module-level `AGENT_MEMORY.md`:

```markdown
# Agent Memory — <module path>

Last updated: <YYYY-MM-DD>

## Purpose

One short paragraph describing what this module owns.

## Mental Model

Compact explanation of how this module works and how it fits into the larger system.

## Key Files

| File | Role |
|---|---|
| `file.py` | What agents should know about it |

## Public Interfaces / Contracts

Document durable interfaces exposed by this module:

- API routes
- service methods
- React context values
- config names
- database collections
- storage paths
- message/event shapes
- command-line scripts

## Dependencies

### Internal

- `path/to/module` — why this module depends on it

### External

- library/service — purpose

## Data Flow

Short bullets or ASCII diagram showing important flows.

## Safe Modification Rules

Rules future agents should follow when editing this module.

Examples:

- Keep Firebase auth dependency on protected endpoints.
- Preserve user-scoped storage paths under `users/{user_id}/...`.
- Update Firestore metadata when storage objects are created/deleted.

## Gotchas

Known sharp edges, implicit assumptions, or fragile behavior.

## Verification

How to verify changes to this module.

Examples:

- `python -m compileall backend/app`
- `npm run build`
- targeted API call
- manual UI flow

## Recent Changes

| Date | Change | Files |
|---|---|---|

## Open Questions

- Questions or uncertainties future agents should resolve.
```

## Root Index Template

Optionally create a root index at:

```text
AGENT_MEMORY.md
```

Use it only as a map to module memories, not as a full repo summary.

```markdown
# Agent Memory Index

Last updated: <YYYY-MM-DD>

## How To Use

Read the most specific `AGENT_MEMORY.md` for the module you are editing, plus parent memories when useful.

## Module Memories

| Path | Scope |
|---|---|
| `backend/AGENT_MEMORY.md` | Backend architecture and API overview |
| `frontend/src/AGENT_MEMORY.md` | Frontend architecture overview |
```

## Workflow: Creating Memory For A Module

When asked to map a module:

1. Identify the module path.
2. Check for an existing `AGENT_MEMORY.md` in that module.
3. List files in the module.
4. Read only the key files needed to understand responsibility and public contracts.
5. Write or update `AGENT_MEMORY.md` using the template.
6. Keep it concise.
7. Report:
   - memory file path
   - files inspected
   - important contracts captured
   - suggested next module to map

## Workflow: Working On Code With Memory

Before editing:

1. Read nearest `AGENT_MEMORY.md` in the target module.
2. Read parent `AGENT_MEMORY.md` if it exists and seems relevant.
3. Inspect precise source files for the task.
4. Make the code change.
5. Run targeted verification.
6. Update affected `AGENT_MEMORY.md` files.
7. Summarize changed code and changed memory.

## Recommended Module Boundaries For Wardrub

For this repository, useful memory boundaries are:

```text
AGENT_MEMORY.md                         # Repo index only
backend/AGENT_MEMORY.md                 # Backend overview
backend/app/AGENT_MEMORY.md             # FastAPI app architecture
backend/app/routers/AGENT_MEMORY.md     # API route contracts
backend/app/services/AGENT_MEMORY.md    # Service layer contracts
backend/app/models/AGENT_MEMORY.md      # Pydantic/domain models
backend/app/jobs/AGENT_MEMORY.md        # Background jobs
backend/app/middleware/AGENT_MEMORY.md  # Middleware behavior
frontend/AGENT_MEMORY.md                # Frontend overview
frontend/src/AGENT_MEMORY.md            # React app architecture
frontend/src/context/AGENT_MEMORY.md    # Auth/Wardrobe context contracts
frontend/src/pages/AGENT_MEMORY.md      # Page-level flows
frontend/src/components/AGENT_MEMORY.md # Reusable UI components
image-edit-service/AGENT_MEMORY.md      # Image edit microservice overview
extension/AGENT_MEMORY.md               # Chrome extension overview, once created
```

## What To Capture For Backend Modules

For backend modules, prioritize:

- Route paths, methods, request/response shapes.
- Auth requirements.
- Firestore collections and document ownership rules.
- GCS path conventions.
- Service method responsibilities.
- External service usage: Firebase, Gemini/Vertex AI, GCS, Firestore, OpenWeather, Vision API.
- Error handling patterns.
- Verification commands.

## What To Capture For Frontend Modules

For frontend modules, prioritize:

- Routes/pages.
- Context state shape and exposed actions.
- API client conventions.
- Auth flow.
- UI data flow.
- Environment variables.
- Build/test commands.
- Component responsibilities.

## Update Rules

Update module memory when any of these change:

- Public API route or request/response shape.
- Service method signature or behavior.
- Storage path convention.
- Firestore data shape.
- Auth requirement.
- Environment variable or config behavior.
- Frontend route or context contract.
- Extension message/event shape.
- Verification command.
- Important gotcha or blocker discovered.

Do not update memory for purely cosmetic changes unless they affect how agents should work in the module.

## Response Format

After creating or updating module memory, respond with:

```markdown
Updated module memory: `<path/to/AGENT_MEMORY.md>`

Inspected:
- `<file>` — <why>

Captured:
- <important contract or mental-model point>

Verification:
- <command or note>

Next suggested module:
- `<path>` — <reason>
```

## If The User Asks To Map The Whole Project

Do not dump everything at once. Propose an order and start with the highest-value module.

Recommended order for Wardrub:

1. `backend/AGENT_MEMORY.md`
2. `backend/app/routers/AGENT_MEMORY.md`
3. `backend/app/services/AGENT_MEMORY.md`
4. `frontend/AGENT_MEMORY.md`
5. `frontend/src/context/AGENT_MEMORY.md`
6. `frontend/src/pages/AGENT_MEMORY.md`
7. `image-edit-service/AGENT_MEMORY.md`
8. `extension/AGENT_MEMORY.md` once created

## Interaction With Product Plans

When using this with a plan such as `docs/CHROME_EXTENSION_PLAN.md`:

- Use `product-plan-compactor` to track plan execution.
- Use `module-memory` to maintain durable codebase context for affected modules.
- After implementing a plan task, update both:
  - the plan progress ledger, and
  - relevant module `AGENT_MEMORY.md` files.
