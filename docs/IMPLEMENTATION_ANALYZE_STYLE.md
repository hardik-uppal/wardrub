# Analyze Style implementation

Authorized by Hardik on 2026-09-11 to implement and test the interviewed scope.
Source: `docs/PRD_ANALYZE_STYLE.md`.

## Scope and implementation choices

- Keep explicit Profile uploads as the entry point; automatic avatar reuse was
  not decided. Analyze original uploaded photos only.
- Persist independent color and fit progress within `UserProfile`, keeping
  existing result fields for compatibility with outfit recommendations.
- Analyze all photos in each submission together. Use structured model output
  and explicit evidence checks for lighting, framing, and loose clothing.
- Accept results only when evidence is sufficient and confidence meets 0.7
  (an engineering starting point, not a calibrated probability). Otherwise ask
  for a specific photo. Users may leave and resume without blocking wardrobe use.
- Keep previous usable results on insufficient evidence or provider failure.
- Support explicit color/fit retries and automatic selection of incomplete stages.
- Validate upload count, bytes, decoded image type and dimensions. Do not retain
  new raw analysis photos; retain derived results/progress only. Each submission
  supplies the images needed for that attempt.
- Use existing Gemini configuration and Firestore; no new external service.
- Existing opt-in `/create-avatar-full` analysis uses the same service and
  merges results from original photos. The normal avatar flow remains unchanged;
  avatar-source retention follows its existing storage behavior.
- Infer progress for older profiles without a destructive migration.
- Extend Profile and the existing widget, sharing updated profile state immediately.
- Piece swaps, automated shopping, and model accuracy certification are deferred.

## API and persistence contract

`POST /api/profile/analyze` remains authenticated multipart form data with
`files` and optional `stage=auto|color|fit` (default `auto`). Auto analyzes
incomplete stages, or refreshes both if both are ready. The model evaluates all
photos together; only selected stages are merged. No previous raw photos are
implicitly reused.

The response retains `profile`, `color_recommendations`, `fit_recommendations`,
and `quality`. `status=failed` with HTTP 200 means the provider attempt failed
and a structured retry state was saved; prior recommendations remain available.
Invalid inputs return 400/413/422. Storage failure returns 503 and does not claim
success. Provider calls have a 55-second HTTP timeout and a 60-second outer bound.

`profile.style_analysis` has `schema_version=1` and independent `color`/`fit`
records: `status=not_started|needs_input|ready|failed`, last usable `confidence`,
`evidence_assessment`, `requested_input={photo_type,reason,instructions}` or null,
`attempts`, `updated_at`, and `result_updated_at`. Existing top-level result
fields remain authoritative for recommendation consumers. `analyzing` is a
transient client state, avoiding a permanently stuck backend state on interruption.

Firestore transactions merge into the latest document, preserve preference
edits and the other stage, and propagate write failures. In-memory persistence
is permitted only with the existing explicit local development bypass. Legacy
results imply ready stages on read; re-analysis refines them.

The widget marks style complete when both stages are ready. Users may minimize
it, continue wardrobe use, or return later. After three insufficient attempts,
Profile explains that photos may not resolve the uncertainty and offers a pause
without imposing an upload loop. Explicit color/fit selection enables refinement.

## Quality limits and follow-up evaluation

Automated tests use controlled model responses and mocked cloud storage/transport.
They verify contracts, evidence gating, state transitions, UI, and SDK request
serialization. They do not measure live model accuracy or production IAM access.
Before production rollout, evaluate consented original photos spanning lighting,
skin appearances, full-length framing, loose clothing, conflicting views, and
no-person/multiple-person cases. Compare repeatability, correct photo requests,
usefulness of palettes/fit guidance, false confident results, latency, and cost.
The 0.7 gate is not a calibrated accuracy guarantee. No live model benchmark or
production deployment is part of this local implementation verification.

## Work and verification

1. Add progress models, evidence-aware analysis, and atomic profile merging.
   Test stage transitions, legacy profiles, retries, malformed outputs, input
   validation, authentication, user isolation, and persistence failures.
2. Integrate Profile, shared state, and onboarding guidance. Test color-first
   results, targeted requests, retries, completion, and resume behavior.
3. Run backend tests, frontend tests, lint, build, and build verification.
   Document the distinction between mocked functional tests and live model
   quality evaluation, which requires representative consented photos.

## Acceptance criteria

- A face-only upload can return color recommendations while requesting a
  full-length photo for fit; onboarding is not prematurely complete.
- Loose clothing and unsuitable lighting trigger stage-specific instructions.
- Fit retries preserve colors; color retries preserve fit; errors preserve both.
- Stored progress and results survive navigation/reload and drive the widget.
- Failed service calls are retryable without blaming the user's photo.
- Existing preference/location/creation fields survive analysis updates.
- Unauthenticated requests cannot analyze or read another user's profile.
