# Agent Memory — frontend/src/context

Last updated: 2026-09-11. Scope: style analysis state and onboarding.

- `WardrobeContext.userProfile` is the shared profile used by Profile and the widget.
- `WardrobeProvider` keys its private session by UID, clearing state and cache on
  logout/direct account switches. Do not lift cached private data outside the session.
- `readCache` shares pending reads, caches successful empty values for five minutes,
  and invalidates resource/category entries on mutations. Stale completions cannot
  overwrite newer mutations. Failed reads remain retryable and preserve loaded state.
- GET requests have a 30-second abort timer; mutation/generation requests are unchanged.
- `fetchProfile(false)` shares/caches bootstrap reads. The default explicit refresh
  `fetchProfile(true)` supersedes pending old reads after direct profile edits.
  A revision guard also protects newer analysis results. Profile mount uses false.
- `analyzeProfile(files, stage='auto')` validates photos, submits multipart data,
  and updates shared results even when the provider returns a saved failure state.
- `OnboardingContext` uses backend color/fit progress and legacy result fallback.
  Style completes only when both stages are ready; widget links select the next
  analysis focus via `/profile?analysis=color|fit`.
- Keep callbacks used by Profile effects stable to avoid repeated fetch loops.
- Verification: `npm test`, `npm run lint`, and `npm run test:e2e` in frontend.
