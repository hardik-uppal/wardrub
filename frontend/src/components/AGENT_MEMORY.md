# Agent Memory — frontend/src/components

Last updated: 2026-09-11. Scope: style analysis guidance.

- `StyleAnalysisProgress.jsx` shows independent colors/fit state, backend photo
  requests, retained results after retries, and a pause suggestion after repeated
  inconclusive attempts. Uses `utils/styleAnalysis.js` for legacy normalization.
- `OnboardingWidget.jsx` displays actionable style descriptions, navigates to
  focused Profile uploads, and can reappear if an analysis needs attention again.
- Widget minimization does not discard backend progress.
- `UploadPreview.jsx` shows a non-blocking fallback when browsers cannot decode a
  selected image (notably HEIC). Shared `utils/imageUploads.js` defines format hints
  and permits recognized extensions with missing/octet-stream MIME; backend bytes
  are authoritative. Camera inputs keep image/* to preserve native capture behavior.
- `GalleryUpload.jsx` owns the Capture gallery queue: at most 5 photos / 10 MB
  per photo, one existing upload request at a time, previews/removal and explicit
  per-photo retries. Successes are not requeued. Leaving stops unscheduled work,
  not the current server request. Object URLs are released on removal/unmount.
  No automatic retries: a lost response may follow successful backend writes.
- Verification: component/context tests and mobile/desktop browser journey,
  including automated accessibility checks.

## Clothing readiness — 2026-09-13

- `ClosetReadiness.jsx` reads authenticated `/closet-state`, provides searchable
  per-item unknown/ready/laundry controls and versioned Undo. It waits for server
  confirmation; uncertain writes trigger a read and outfit refresh, never a
  blind automatic replay. API409 prompts refresh; no taste inference.
- The component remains mounted during parent outfit refresh so undo survives.
  An expanded panel is optional; initial capture and avatar access are unchanged.
- Tests: `ClosetReadiness.test.jsx` and `e2e/recommender.spec.js`.

## Release A shared UI — 2026-09-13

- `AppChrome`: PageHeader + WardrobeTabs. Two primary destinations via BottomNav/SideNav, Profile in header/footer. Profile links always open Profile.
- `OutfitPanel` renders garment identity/readiness/locations, confirmed save/plan/wear/undo and optional try-on. Missing garments disable invalid actions and link to a fresh suggestion.
- `Dialog` uses native modal/focus/escape behavior. Home owns versioned single/batch readiness and detail/location/delete actions. The older ClosetReadiness remains for legacy unmounted Magazine UI.
- Global OnboardingWidget is unmounted; capture success and relevant optional avatar/style entries replace its persistent checklist. GalleryUpload preserves bounded retries and adds a completion callback.
- LookPreview labels image export Download; Save outfit is the separate persistence action.

## One-photo follow-up — 2026-09-13

- GalleryUpload now owns gallery and camera input, optional webcam dialog and native fallback. Both call processUploadedClothes with one file; no category/back fields. Stream teardown handles cancel/unmount and late permission.
- Queue remains bounded/sequential; partial success preserves added pieces and cannot blindly retry the same photo. Added pieces show automatic labels; Done returns to origin. Unit and one-photo browser tests cover input/persistence and partial outcomes.
