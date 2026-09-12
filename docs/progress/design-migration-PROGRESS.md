# Wardrub design migration progress

Last updated: 2026-09-13.

## Current state

- Active phase: M0 — record current journeys and proposed differences.
- This audit slice is done. The full M0 design specification and visual migration are not complete.
- Source specification: the task deliverable `wardrub-design-migration-plan.md`.
- Repository flow register: `docs/product/USER_FLOWS_CURRENT_AND_PROPOSED.md`.
- Audited application: `40961a8`, based on main `d754dda`. Recommender foundation is local and undeployed; see `recommender-PROGRESS.md`.

## Task ledger

| Task | Status | Verification |
|---|---|---|
| Inventory all routed screens, dialogs and recovery paths | Done | App routes, all eight page components, related components/context and API handlers inspected |
| Compare current/proposed flows, preserve avatar and try-on | Done | F01–F30 register, route map, five walkthroughs and source map |
| Separate visual migration from new behavior and deferred scope | Done | Saved outfit, plan/wear, batch readiness, avatar candidate/return and feedback contracts identified |
| Full token/component/state specification and live visual audit | Pending | Existing design plan supplies direction; runtime production parity not verified by this code audit |
| Implement simplified Wardrobe and remaining Release A flows | Pending | No UI code changed in this audit |

## Decisions and gotchas

- Release A: Today / Wardrobe; Items / Outfits within Wardrobe; Profile in header. Shop later; social deferred.
- Existing wardrobe search/sort, gallery queue and generated-history management should be retained.
- Feed Save currently records feedback. LookPreview Save downloads an image. Neither is a saved-combination flow.
- Current avatar creation returns to `/`; candidate acceptance and return-to-outfit remain new work.
- Manual try-on permits single-item previews; do not apply the complete daily-outfit rule to every preview.
- Feed try-on omits garment IDs and bypasses the shared Looks-cache update. History API limits reads to 50. Address identity/freshness/retrieval before claiming seamless unified Outfits history.
- The unused DailyOutfit page and other unmounted components/API utilities are not active user journeys.

## Verification

Documentation coverage and source-path checks; `git diff --check`. No application tests re-run because this slice changes documentation only. Previous foundation test results are explicitly labeled historical and fixture-based in the register. No push, deployment, production generation or data migration performed.

## Next task

Use the flow register to finish the reusable component/state specification, then implement the Wardrobe Items slice (F03, F07–F09, F15) with existing search, filters, images, deletion and readiness preserved. Build real saved-outfit persistence before introducing Saved outfits navigation. Keep all current avatar/try-on entries reachable until their replacements and return paths work.

## Resume prompt

Read this ledger, `docs/product/USER_FLOWS_CURRENT_AND_PROPOSED.md`, the design migration plan deliverable and relevant module memories. Continue the minimalist design migration from the audited local foundation. Do not confuse this completed flow audit with completed screen redesign or deployment.
