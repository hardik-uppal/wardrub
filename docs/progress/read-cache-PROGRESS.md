# Loading pass 2 — shared reads and empty-result caching

Branch `perf/shared-read-cache`. Baseline `59eba88` (includes thumbnail read-path PR #15).

## Changes

- Per-UID provider session resets private state on logout/direct account switches.
- In-memory read cache shares concurrent GETs and caches valid empty lists/null avatar.
- Five-minute TTL with force refresh and mutation invalidation, including every
  category-specific wardrobe cache; data is not persisted in browser storage.
- Stable callbacks no longer depend on list lengths/avatar response values.
- Non-2xx/malformed list responses preserve loaded data and are not cached.
- Invalidated older reads cannot resurrect deleted items or replace fresh analysis.
- Profile bootstrap is shared, explicit post-edit refresh supersedes pending reads.
- Read-only fetches abort after 30 seconds; mutation/generation timeouts unchanged.
- Migration refreshes independent resources concurrently instead of sequentially.

## Measured browser request counts

Same Playwright fixture in a detached baseline worktree and candidate. Journey:
Wardrobe → Try On → Wardrobe using SPA navigation, successful empty wardrobe,
synthetic inline avatar and mocked API responses with 100 ms latency.

| Environment | Version | Wardrobe GET | Avatar GET | Profile GET | Total |
|---|---|---:|---:|---:|---:|
| Mobile Chromium | baseline | 6 | 2 | 2 | 10 |
| Mobile Chromium | candidate | 1 | 1 | 1 | 3 |
| Desktop Chromium | baseline | 6 | 2 | 2 | 10 |
| Desktop Chromium | candidate | 1 | 1 | 1 | 3 |

70% fewer requests for this controlled development-mode journey. React StrictMode
replays mount effects in this environment, contributing to baseline duplicates.
This is NOT a measured 70% production speedup or byte reduction. Real authentication,
GCS signing, image transfers, Cloud Run cold starts and billing were not measured.

Reproduce: `npm run test:e2e -- --grep 'empty wardrobe navigation'` in frontend.
The test prints counts and attaches JSON to Playwright results. It fails on baseline
(expected one wardrobe request, received six), passes on candidate.

## Verification

Unit/integration coverage includes concurrent-read sharing, TTL, force refresh,
empty caching, failure/retry, category invalidation, deleted-item stale responses,
account switches and analysis preservation. Full E2E suite covers existing product
flows and accessibility as well as the loading fixture.

## Remaining loading work

Read-only production object inventory found 23/61 garment originals and 26/38
saved-look originals without WebP thumbnails. Counts are object counts, not unique
users or garments. A bounded create-only backfill should address these separately
so legacy items do not depend on large original-image fallbacks. No photos were
read or changed by that inventory. Signing and true end-to-end production latency
remain unmeasured. Avoid conflating this frontend change with backend CPU benchmarks.
