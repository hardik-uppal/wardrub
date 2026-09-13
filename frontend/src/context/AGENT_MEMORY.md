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

## Recommendation readiness — 2026-09-13

- Onboarding clothes milestone now checks an indexed top+bottom or dress instead
  of ten arbitrary garments. Avatar/style milestones remain optional setup tools;
  the recommendation API/page do not gate on them. Current laundry eligibility is
  server-owned and distinct from having enough categories indexed.

## Release A session state — 2026-09-13

- `ClosetContext` is mounted inside the protected layout and keyed by UID. Library + readiness reads have revision guards; mutation confirmation updates library/version. Failures trigger a read, never blind replay.
- `draft` persists selected garment IDs and origin in `sessionStorage` keyed by UID. Auth sign-out clears draft keys; account switches remount the private context. These are navigation drafts, not background generation jobs.
- `createAvatar(files, mode, activate=false)` returns a review candidate without changing avatarUrl. `fetchAvatar(true)` follows successful activation. Legacy default activate=true remains compatible.
- `WardrobeContext` exposes nextLookOffset/loadMoreLooks with deduplicated history appends. Try-on sends garment IDs and refreshes history after success. Existing garment/avatar/profile read cache remains.
- `checkLegacyData` now propagates failed/non-boolean responses; recovery distinguishes unknown/error from empty.

## One-photo follow-up — 2026-09-13

- processUploadedClothes stores additive name/fit_observation. Uses one truthful pending message, with no timed synthetic progress stages for this endpoint. Other avatar/try-on contracts unchanged.
