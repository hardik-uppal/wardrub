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
