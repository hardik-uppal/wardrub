# Wardrub Chrome Extension Progress

Source plan: `docs/CHROME_EXTENSION_PLAN.md`

## Current State

- Active phase: Phase 1 — Backend URL Try-On Endpoint
- Active task: P1.T3 Implement secure product image URL downloader
- Status: in-progress
- Last updated: 2026-04-28

## Compact Context

Wardrub is adding a Chrome extension that lets a signed-in user select clothing from browser product pages and virtually try it on their existing Wardrub avatar. The existing backend already has Firebase auth, avatar retrieval, garment processing, wardrobe storage, and try-on endpoints. The plan is to first prove the backend vertical slice, then build a Manifest V3 side-panel extension around it.

The execution style for this plan is task-by-task compaction: after each task, update this ledger with durable progress, changed files, verification, decisions, and the next task.

## Task Ledger

| ID | Task | Status | Files | Verification |
|---|---|---|---|---|
| P1.T1 | Initialize progress ledger from Chrome extension plan | done | `docs/progress/chrome-extension-PROGRESS.md`, `.pi/skills/product-plan-compactor/SKILL.md` | Files created |
| P1.T2 | Add backend extension router skeleton and bootstrap endpoint | done | `backend/app/routers/extension.py`, `backend/app/main.py` | `python3 -m compileall backend/app` passed |
| P1.T3 | Implement secure product image URL downloader | not-started | TBD | SSRF/content-type/size validation tests TBD |
| P1.T4 | Implement `/api/extension/try-on-product` endpoint | not-started | TBD | Local API test with product image URL TBD |
| P1.T5 | Add save temporary garment/look endpoints | not-started | TBD | API tests TBD |
| P2.T1 | Create Chrome extension skeleton | not-started | `extension/` | Load unpacked extension TBD |
| P3.T1 | Add extension auth/bootstrap flow | not-started | `extension/src/shared/auth.js`, `extension/src/shared/api.js` | Sign-in and bootstrap call TBD |
| P4.T1 | Add product image detection content script | not-started | `extension/src/content/*` | Manual test page TBD |
| P5.T1 | Add side-panel try-on flow | not-started | `extension/src/sidepanel/*` | End-to-end try-on TBD |

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-04-28 | Track execution in a separate progress ledger instead of editing the source plan | Keeps the product plan stable while allowing compact resumable implementation state |
| 2026-04-28 | Add project-level pi skill at `.pi/skills/product-plan-compactor/SKILL.md` | Makes this task-by-task compaction workflow reusable for this repo |
| 2026-04-28 | Keep module-level compaction files (`AGENT_MEMORY.md`) updated alongside plan progress | Allows faster future implementation with local, agent-friendly context |

## Interfaces / Contracts

Planned backend extension endpoints from the source plan:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/extension/bootstrap` | Initialize extension with user/avatar state |
| `POST` | `/api/extension/try-on-product` | Download/process product image and generate try-on |
| `POST` | `/api/extension/save-garment` | Convert temporary browser garment to permanent wardrobe item |
| `POST` | `/api/extension/save-look` | Convert temporary generated look to saved look |

Planned product-selected message shape for the extension:

```json
{
  "type": "WARDRUB_PRODUCT_SELECTED",
  "payload": {
    "imageUrl": "https://store.com/image.jpg",
    "pageUrl": "https://store.com/product",
    "title": "Black Denim Jacket",
    "brand": "Example Brand",
    "price": "$89",
    "merchant": "store.com"
  }
}
```

## Verification Log

| Date | Command/Test | Result | Notes |
|---|---|---|---|
| 2026-04-28 | Created skill file and progress ledger | passed | No runtime verification needed yet |
| 2026-04-28 | `python3 -m compileall backend/app` | passed | Includes new extension router and app registration |

## Update Log

### 2026-04-28 — P1.T1 Initialize progress ledger from Chrome extension plan

- Added project-level pi skill `.pi/skills/product-plan-compactor/SKILL.md`.
- Added compact progress ledger `docs/progress/chrome-extension-PROGRESS.md`.
- Captured initial phase/task queue from `docs/CHROME_EXTENSION_PLAN.md`.
- Next: add backend extension router skeleton and bootstrap endpoint.

### 2026-04-28 — P1.T2 Add backend extension router skeleton and bootstrap endpoint

- Added `backend/app/routers/extension.py` with authenticated `GET /api/extension/bootstrap`.
- Added response models for extension bootstrap payload (`user`, `avatar_url`, `has_avatar`).
- Registered extension router in `backend/app/main.py`.
- Compacted module memory while exploring:
  - `backend/app/AGENT_MEMORY.md`
  - `backend/app/routers/AGENT_MEMORY.md`
  - updated root index `AGENT_MEMORY.md`
- Verification: `python3 -m compileall backend/app` passed.
- Next: implement secure product image URL downloader (P1.T3).

## Next Task

P1.T3 Implement secure product image URL downloader.

Expected scope:

- Add a reusable downloader utility for extension product image URLs.
- Enforce SSRF protections (scheme + private/local IP blocking + redirect revalidation).
- Enforce content-type and size limits for image fetches.
- Return validated image bytes for downstream try-on endpoint.

## Resume Prompt

Continue executing `docs/CHROME_EXTENSION_PLAN.md` using the product-plan-compactor skill. Read `docs/progress/chrome-extension-PROGRESS.md`, resume at `P1.T3 Implement secure product image URL downloader`, preserve the documented interfaces/contracts, and compact progress after completing the task.
