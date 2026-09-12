# Loading performance progress

## Workspace

Branch `perf/loading`, isolated worktree `/Users/hardikuppal/wardrub-loading`.
The main workspace's monitoring changes are untouched. This patch is not deployed.

## First bounded change: read-only thumbnail lookup

Wardrobe and saved-look listing previously generated missing derivatives inline:
cloud download → image transform → cloud upload → URL signing. Local reads also
mutated thumbnail storage. Removed this work from both listing methods. Existing
thumbnails and original URLs are returned as before; missing thumbnails return null.
Home and SavedLooks already fall back to original URLs. Upload-time thumbnail
creation is unchanged.

Trade-off: legacy items without thumbnails now load larger originals until an
explicit bounded backfill generates derivatives. This removes server-side work
but is not a measured improvement to every page's total load time. No production
latency or browser waterfall benchmark has been collected yet.

Verification: 43 backend tests passed including three new cloud/local listing
regressions; git diff --check passed. Tests verify no derivative generation,
original-image fallback data, existing front/back thumbnails, user-scoped listing,
look sorting and limits. Frontend unchanged. No production data changed.

## Measured before/after (synthetic CPU microbenchmark)

Baseline: `a60892c`; exact candidate file hash and environment in
`loading-benchmark.json`. Reproduce with:

```sh
python backend/benchmarks/benchmark_storage_listing.py \
  --baseline a60892c --repeats 10 --out docs/progress/loading-benchmark.json
```

Ten repetitions per case using a seeded 1536x2048 RGB PNG and real Pillow
thumbnail processing. GCS listing/download/upload and signing are fake in-memory
implementations; NO real network latency or user images. These are function CPU
measurements, not API response times or browser load measurements.

| Case | Items | Before median | After median | Downloads/uploads per request, before → after |
|---|---:|---:|---:|---|
| Wardrobe, missing thumbnails | 10 | 868.63 ms | 0.01 ms | 10/10 → 0/0 |
| Wardrobe, missing thumbnails | 50 | 4402.58 ms | 0.06 ms | 50/50 → 0/0 |
| Looks, missing thumbnails | 10 | 897.67 ms | 0.02 ms | 10/10 → 0/0 |
| Looks, missing thumbnails | 50 | 4490.38 ms | 0.10 ms | 50/50 → 0/0 |

With existing thumbnails both versions are approximately 0.01–0.13 ms under fake
IO: no meaningful claimed improvement in that case. Patched microsecond timings
exclude cloud listing and signing costs and MUST NOT be presented as production
latency or percentage page-load speedup. Ten samples provide only a rough p95;
raw samples are retained. High-entropy synthetic PNGs are not representative photos.

## Follow-up investigation, not implemented

1. Measure request durations and browser waterfalls for empty/small/large wardrobes.
2. Count per-image URL signing operations; investigate bounded caching keyed by
   user/asset/version/expiry without leaking private URLs across accounts.
3. Audit repeated frontend fetches and in-flight request sharing. Existing callbacks
   depend on result state, empty collections bypass cache guards, and shared callers
   have no in-flight deduplication. Test account switches and stale responses.
4. Loading skeletons and independent page/data loading states.
5. Explicit dry-run-first, bounded thumbnail backfill for legacy objects with owner
   scoping and create-only preconditions. Do not restore background writes on GET.

CS-007 is only partially addressed: the read-path change is implemented, but a
bounded backfill workflow and measured latency verification remain open.
