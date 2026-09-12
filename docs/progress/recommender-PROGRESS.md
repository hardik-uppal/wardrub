# Wardrub recommender implementation progress

Source direction: [mission and strategy PR #25](https://github.com/hardik-uppal/wardrub/pull/25),
plus the September 13 founder decision to prioritize the recommender and defer social imports.

## Current state

- Active phase: grounded recommendation foundation.
- Branch: `codex/recommender-foundation`, based on `d754dda`.
- Status: done for the foundation milestone; not deployed.
- Last updated: 2026-09-13.

## Task ledger

| Task | Status | Files | Verification |
|---|---|---|---|
| Deterministic ranking, role-based cold start, stable identity | Done | `services/closet_ranker.py`, feed service/model | Pure/service tests; 24-case benchmark |
| Truthful weather and input freshness | Done | weather service/model, feed service/page | TTL/location/error tests; UTC rollover tests retained |
| Authenticated constrained swaps | Done | outfit router, ranker, MagazineFeed | API tests; UI tests; mobile/desktop browser loop |
| Ready/laundry/unknown and versioned undo | Done | garment model, Firestore, outfit router, ClosetReadiness | Replay/conflict/ownership/storage-failure tests; browser undo |
| Preserve existing generation access | Done | MagazineFeed | Core routes/browser checks; shoes explicitly omitted from unsupported preview |
| Benchmark and progress/module documentation | Done | benchmark manifests/runner, module memories | Synthetic comparison: new 24/24; old scorer 14/24 |

## Contracts and decisions

- No Gemini call or cached editorial selection in the active magazine-feed path.
  GET and explicit refresh recompute from a fresh, strictly read user wardrobe and
  profile. Successful weather observations cache per coordinate pair for ten
  minutes, bounded to 128 locations; unknown weather stays null.
- Outfit identity hashes user ID and canonical category/garment pairs. It survives
  dates/refreshes, changes on swap, and differs across users. It is not a saved
  outfit record or an exposure event ID.
- Feed retains its response envelope/date and optional legacy editorial fields.
  `cover_look` can be null for no viable outfit. New fields identify policy,
  wardrobe version, weather status and unknown readiness.
- `POST /api/outfits/swap` accepts garment IDs and a replacement target; an optional
  proposed replacement is revalidated. Known unavailable locked pieces yield 409;
  no replacement returns `no_alternative` without mutation.
- `GET /api/closet-state` and `PUT /api/closet-state/{id}` require auth. PUT compares
  `expected_version`, performs a transaction, returns the new version, and rejects
  conflicts. Exact request replay does not increment twice. Undo is a subsequent
  compare-and-set back to the previous state. No automatic laundry transitions.
- Readiness writes and strict recommendation reads fail closed in production.
  Generic metadata analysis saves merge and cannot overwrite readiness/ownership.
- Legacy `/recommendations` and `/daily-outfit` selection delegate to the grounded
  ranker. Legacy private scoring helpers remain for compatibility; dated generated
  look history is still history and is not reclassified as currently ready.
- Existing avatar creation, dressing room, saved generated history and generation
  services remain. The renderer does not support shoes; the UI discloses their
  omission from a preview while retaining them in the outfit.
- This phase uses bounded rules and existing explicit profile style tags. It does
  not infer taste from feedback yet. Existing feedback recording remains separate
  from laundry. A save feedback event is still not a durable saved outfit.

## Verification log — 2026-09-13

- Backend unittest suite: 72 passed, including mocked cloud transaction behavior.
- Frontend Vitest: 62 passed in 15 files.
- Playwright: 12 passed across mobile and desktop; core routes, capture, profile,
  loading cache and the new swap/laundry/undo loop. No serious/critical automated
  accessibility violations in the checked flows. Mobile screenshot inspected.
- Frontend ESLint and production build passed; build smoke checks passed.
- Synthetic benchmark: starter 2/2; small 24/24 versus legacy scorer14/24.
  Results: `runs/2026-09-13-recommender/{starter,small}.json`.
- `git diff --check`: passed.

## Verification limits

Synthetic fixtures establish invariants, not personal styling accuracy. Browser
journeys use deterministic API fixtures; API/storage tests use mocked cloud
transactions and isolated development records. No live Firestore, live weather,
real-user data, or paid generation was used. No deployment or remote push occurred.

## Next task

Add durable decision/exposure/action records and reason-aware feedback, with
separate meanings for selected, wore, unavailable, temporary occasion mismatch,
and enduring preference. Design idempotent event ingestion and actual-visibility
logging before claiming preference learning; coordinate with reporting PR #16.
Then evaluate conservative preference adjustments against this versioned baseline.
Batch laundry, physical location, saved/planned outfits, trained models and social
imports remain follow-up phases, not hidden claims of this implementation.

## Resume prompt

Read this ledger and affected AGENT_MEMORY.md files. Continue at the decision-event
and feedback phase, preserving the wardrobe-state transaction, stable identity,
legacy generation access and benchmark. Do not replace the ranking baseline with
free-form model selection or start social integrations.
