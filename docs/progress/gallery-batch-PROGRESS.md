# Issue #4 — multiple gallery photos

Branch: `fix/multi-gallery-upload`; baseline `5f19a3e`.

- Capture gallery uses a dedicated GalleryUpload component; camera front/back flow unchanged.
- Native multiple selection, up to 5 photos and 10 MB per photo. Invalid selections
  are rejected as a whole with an explanation, not silently truncated.
- Local object-URL previews, removal before processing, selected count, aggregate
  outcomes and current-photo progress. URLs released on removal/unmount.
- Sequential calls to the existing authenticated single-photo endpoint. No batch
  backend, changed ownership rules, unbounded parallel jobs or automatic retries.
- Each successful response is added by the existing WardrobeContext method.
  Failed/empty detections remain individually retryable; successful entries are
  excluded from further processing. The page stays open to review batch outcomes.
- Leaving stops the remaining queue; the in-flight server request may still finish.
  A new gallery cannot start processing while the context has another active job.
- Network uncertainty is disclosed: check wardrobe before retrying because the
  existing backend does not provide idempotency for a lost successful response.

## Verification

- 39 frontend tests pass, including five new gallery tests (multi-select/removal,
  sequential progress/partial failure/retry, empty detection, limits and unmount).
- 10 Playwright checks pass across mobile/desktop Chromium. New browser fixture:
  select 3 → remove 1 → process 2 → one succeeds, one fails → retry failure.
  Exactly 3 mocked processing requests, peak concurrent processing requests = 1.
- Lint, production build and build smoke pass.
- No production photos or actual AI inference used in these tests.

## Boundaries

Native picker behavior on real iOS and HEIC/HEIF decoding remain issue #12;
this change does not claim new image-format support. These are client UX limits,
not a replacement for backend upload validation/rate limits. Thumbnail backfill
work is untouched in its separate worktree and has not been run.
