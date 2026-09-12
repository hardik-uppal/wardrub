# Agent Memory — frontend/src/context

Last updated: 2026-09-11. Scope: style analysis state and onboarding.

- `WardrobeContext.userProfile` is the shared profile used by Profile and the widget.
- `fetchProfile` refreshes on authenticated mount. A revision guard prevents late
  initial reads from replacing a more recent `applyProfile`/analysis update.
- `analyzeProfile(files, stage='auto')` validates photos, submits multipart data,
  and updates shared results even when the provider returns a saved failure state.
- `OnboardingContext` uses backend color/fit progress and legacy result fallback.
  Style completes only when both stages are ready; widget links select the next
  analysis focus via `/profile?analysis=color|fit`.
- Keep callbacks used by Profile effects stable to avoid repeated fetch loops.
- Activation analytics browser deduplication now uses token-subject namespaced
  keys; token decoding is only a UI cache key, never authorization. Backend derives
  identity from verified claims. Milestones remain best-effort per browser, not
  authoritative first-ever events or a complete activity stream.
- Verification: `npm test`, `npm run lint`, and `npm run test:e2e` in frontend.
