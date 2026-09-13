# Wardrub design migration progress

Last updated: 2026-09-13.

## Current state

- Active phase: Release A implementation, ready for PR review after local verification.
- Branch: `codex/minimalist-design`; base `origin/main` at `fd453ce` (merged recommender PR #26 and its release fixes).
- Source plans: task deliverable `wardrub-design-migration-plan.md` and `docs/product/USER_FLOWS_CURRENT_AND_PROPOSED.md`.
- Implemented component/state reference: `docs/product/DESIGN_SYSTEM.md`.
- Publication is pending. Last inspected GitHub permission was read-only (`push: false`). No new redesign deployment or merge has been performed.

## Task ledger

| Slice | Status | Evidence |
|---|---|---|
| M0 flow audit | Done | Historical F01–F30 register, routes and before/after walkthroughs |
| M0 tokens/components/states | Implemented | DESIGN_SYSTEM.md, semantic CSS, shared chrome, outfit panel and dialog |
| M1 Items | Implemented | Search/sort/category/shoes/readiness, detail, deletion, optional locations and try-on entry |
| M2 durable actions and Outfits | Implemented | User-scoped save/plan/wear/undo, batch laundry/return, generated history views and pagination |
| M3 Today/capture/navigation | Implemented | Two destinations, a useful-outfit starting point, real swaps, capture completion and explicit corrections |
| M3 avatar and try-on parity | Implemented | Candidate/accept, current-avatar preservation, user-keyed input return, failure retry, avatar-aware cache and history |
| Profile and optional utilities | Implemented | Focused location/preferences/history/style/recovery, existing analysis retries and account isolation |
| M4 production pilot | Pending | No live cloud persistence, camera/native-share, generated-image or user taste study performed |
| M5 Shop / social imports | Deferred | Separate product milestone and founder decision |

## Contracts and boundaries

See DESIGN_SYSTEM.md for persistence caps and public state meanings. The new APIs are authenticated GET `/api/closet-library`, POST `/api/closet-library/actions`, POST `/api/closet-state/batch`, and POST `/api/avatar-candidates/{id}/activate`. Avatar creation accepts additive `activate=false`; legacy callers default to immediate activation. Feed GET accepts optional `local_day`; history accepts offset/limit and returns next_offset.

Corrections temporarily remove an outfit for a local day and remain reversible. They do not infer taste or record training exposures. Explicit style tags supply the existing ranker's bounded boost. Image generation never confirms wear or moves clothes into laundry. Shop, detected-item review/editing, full generation-job persistence and avatar-history/cleanup are not included.

## Verification

- Backend: 94 isolated Python tests passed, including ownership, version conflicts, atomic readiness, persistence/restart, corrections/undo, style override/clear, avatar acceptance, cache invalidation and older-history retrieval.
- Frontend: 63 unit tests passed. ESLint, production build and static-route build checks passed.
- Browser: 20 tests passed across mobile and desktop, including light/dark visual/accessibility checks on nine views. Synthetic API fixtures, no production model calls.
- Recommender: fixed starter 2/2 and small 24/24; legacy comparison 14/24 on small. Outputs `runs/2026-09-13-design/`. No regression against the merged foundation; correctness fixtures do not establish taste quality.
- `git diff --check` and patch applicability are final publication checks.

## Next task

Publish this branch and open a draft PR against main once GitHub write access is available. Review screenshots and diff, let repository CI run, then perform the M4 test-account pilot. Do not mark the redesign deployed because the earlier recommender PR was merged.

## Resume prompt

Read this ledger, DESIGN_SYSTEM.md and affected module memories. Continue publishing and reviewing the existing `codex/minimalist-design` branch. Preserve the real durable actions and avatar/try-on flows. Do not restart the redesign or treat Shop/social or unvalidated pilot outcomes as delivered.
