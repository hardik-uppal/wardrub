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
