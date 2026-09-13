# Agent Memory — backend/app/models

Last updated: 2026-09-11. Scope: style analysis additions.

- `user_profile.py`: `UserProfile.style_analysis` holds independent `color` and
  `fit` `AnalysisStage` records, schema version 1. `PhotoRequest` describes a
  face/full-length photo, reason, and instructions.
- Stage status: `not_started`, `needs_input`, `ready`, `failed`. Result confidence
  and date describe the last usable result, separate from the latest attempt.
- Existing `skin_tone`, `body_type`, and `body_measurements` remain the results
  consumed by recommendations. Do not duplicate them in progress records.
- A before-validator adds progress to legacy profiles on read. Existing results
  imply ready stages; no destructive migration is needed.
- Verify with `python -m unittest discover -s backend/tests -p test_style_analysis.py`.

## Recommender foundation — 2026-09-13

- `GarmentMetadata` adds ownership (owned/lent/retired), readiness
  (unknown/ready/laundry), and readiness_version. Legacy defaults owned/unknown/0.
  Do not derive laundry from wear or treat unknown as clean.
- `MagazineFeed.cover_look` and `underused_edit` are nullable. Additive fields:
  weather, weather_status, policy_version, wardrobe_version. LookCard adds policy
  and unknown_readiness_ids; score is a heuristic, not a match probability.
- `WeatherInfo` preserves actual/feels-like temperature, optional observation/fetch
  timestamps and source. Non-finite temperatures are invalid.

## Daily correction context — 2026-09-13

- `MagazineFeed.skipped_for_day` is additive, default false: one or more explicit outfit corrections apply to the requested local day. It is not a learned preference signal. ClosetAction request bounds and literal action/reason/style values live in `routers/closet.py`.
