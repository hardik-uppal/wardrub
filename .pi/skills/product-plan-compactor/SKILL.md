---
name: product-plan-compactor
description: Use when executing implementation work from long product/architecture plan documents such as docs/CHROME_EXTENSION_PLAN.md. Turns a product plan into small executable tasks, implements one task at a time, and maintains a compact progress ledger after each task so future agent sessions can resume without rereading full context.
---

# Product Plan Compactor

Use this skill when the user wants to build from a detailed product plan, architecture document, roadmap, PRD, or implementation plan.

The goal is to avoid context drift by converting a long plan into a task queue and updating a compact implementation ledger after every completed task.

## Core Rules

1. **Read the source plan first.**
   - Load the referenced plan document, e.g. `docs/CHROME_EXTENSION_PLAN.md`.
   - Identify the active phase, immediate task, expected deliverable, dependencies, and acceptance criteria.

2. **Work in small vertical slices.**
   - Select one clear task or subtask at a time.
   - Prefer end-to-end slices that can be verified.
   - Do not start multiple phases unless the user asks.

3. **Maintain a compact progress ledger.**
   - After each meaningful task, update a concise progress file.
   - Default path:
     - `docs/progress/<plan-slug>-PROGRESS.md`
   - Example for `docs/CHROME_EXTENSION_PLAN.md`:
     - `docs/progress/chrome-extension-PROGRESS.md`

4. **Compact after every task.**
   - Record only durable facts, not verbose reasoning.
   - Include files changed, decisions made, tests run, current status, and next task.
   - This ledger should be sufficient for another session to resume.

5. **Keep the source plan stable unless the plan itself changes.**
   - Do not rewrite the original plan just to track progress.
   - Use the progress ledger for execution state.
   - If the plan changes materially, add a short `Plan Changes` entry to the progress ledger.

6. **Report concise checkpoints to the user.**
   - At the end of each task, provide:
     - completed task
     - files changed
     - verification status
     - next recommended task

## Workflow

### Step 1: Initialize From Plan

When the user names a plan document:

1. Read the plan document.
2. Determine a slug from the filename.
3. Create or update the progress ledger at:

```text
docs/progress/<plan-slug>-PROGRESS.md
```

4. If no ledger exists, initialize it from this template:

```markdown
# <Plan Title> Progress

Source plan: `<path/to/plan.md>`

## Current State

- Active phase: <phase name or TBD>
- Active task: <task name or TBD>
- Status: not-started | in-progress | blocked | done
- Last updated: <YYYY-MM-DD>

## Compact Context

Short summary of what we are building and the most important architectural decisions.

## Task Ledger

| ID | Task | Status | Files | Verification |
|---|---|---|---|---|
| P1.T1 | Example task | not-started | - | - |

## Decisions

| Date | Decision | Reason |
|---|---|---|

## Interfaces / Contracts

Document important API shapes, routes, config names, message types, or file conventions that future tasks must preserve.

## Verification Log

| Date | Command/Test | Result | Notes |
|---|---|---|---|

## Next Task

Describe the exact next task to execute.

## Resume Prompt

A short prompt a future session can use to continue, including source plan path, progress ledger path, active phase, and next task.
```

### Step 2: Extract Tasks

Create task IDs from the plan:

```text
P<phase-number>.T<task-number>
```

Example:

```text
P1.T1 Add backend extension router
P1.T2 Implement secure image URL downloader
P1.T3 Add /api/extension/bootstrap
P1.T4 Add /api/extension/try-on-product
```

For each task, capture:

- task title
- status
- relevant files
- verification approach
- dependencies

### Step 3: Execute One Task

For the chosen task:

1. Inspect only the files needed for that task.
2. Implement the smallest useful slice.
3. Run targeted verification if possible.
4. Avoid unrelated refactors.
5. If blocked, write the blocker into the progress ledger and stop.

### Step 4: Compact Into Progress Ledger

After the task, update the ledger with:

```markdown
## Task Ledger

| ID | Task | Status | Files | Verification |
|---|---|---|---|---|
| P1.T1 | Add backend extension router | done | `backend/app/routers/extension.py`, `backend/app/main.py` | `python -m compileall backend/app` passed |
```

Add a dated detail entry when needed:

```markdown
## Update Log

### 2026-04-28 — P1.T1 Add backend extension router

- Added `backend/app/routers/extension.py`.
- Registered router in `backend/app/main.py`.
- Added placeholder authenticated bootstrap endpoint.
- Verification: `python -m compileall backend/app` passed.
- Next: implement secure image URL downloader for `try-on-product`.
```

Update `Current State` and `Resume Prompt` every time.

### Step 5: End With a Checkpoint

Respond to the user with this structure:

```markdown
Completed: <task ID and title>

Changed:
- `<file>` — <short reason>

Verified:
- `<command>` — <result>

Compacted progress:
- `<progress-ledger-path>` updated

Next recommended task:
- <task ID and title>
```

## Compaction Guidelines

Good compact notes:

- Durable decisions.
- Public interfaces.
- File paths and function names.
- Commands/tests and results.
- Current blockers.
- Next exact task.

Avoid compacting:

- Long reasoning traces.
- Duplicated source plan text.
- Full command outputs unless necessary.
- Speculative ideas not selected.

## Resume Prompt Format

Every progress ledger should end with a `Resume Prompt` like:

```markdown
Continue executing `<source-plan>` using the product-plan-compactor skill. Read `<progress-ledger>`, resume at `<task-id> <task-title>`, preserve the documented interfaces/contracts, and compact progress after completing the task.
```

## When To Ask The User

Ask before proceeding if:

- The next task is ambiguous.
- The implementation may require a new external service/account/secret.
- A plan decision conflicts with the current codebase.
- A task would substantially change the product direction.
- Verification cannot be done locally and the risk is high.

## Recommended First Task For Chrome Extension Plan

For `docs/CHROME_EXTENSION_PLAN.md`, start with:

```text
P1.T1 Initialize progress ledger from the Chrome extension plan.
```

Then proceed to:

```text
P1.T2 Add backend extension router skeleton and bootstrap endpoint.
P1.T3 Implement secure image URL downloader.
P1.T4 Implement try-on-product endpoint.
```
