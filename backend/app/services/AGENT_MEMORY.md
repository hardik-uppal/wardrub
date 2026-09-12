# Agent Memory — backend/app/services

Last updated: 2026-09-12. Scope: progressive style analysis and storage listing.

- Magazine daily cache keys are explicitly UTC (`datetime.now(timezone.utc)`).
  `test_magazine_freshness.py` verifies same-day reuse, next-day generation with
  unchanged garments, forced refresh and user isolation against a mocked provider.
  New editions need not contain wholly different outfits; no live diversity claim.
- `StorageService.list_garments` and `list_tryon_results` never generate missing
  thumbnails, in cloud or local mode. Missing derivative URLs stay null; existing
  frontend consumers fall back to originals. Upload-time thumbnail creation is
  unchanged. A separately bounded legacy backfill remains follow-up work.
- Listing regression tests: `python -m unittest discover -s backend/tests -p test_storage_listing.py`.
  This removes request-time derivative work, not signed-URL generation or blob listing.

- `image_input.py` is the shared JPEG/PNG/WebP/HEIC/HEIF ingress decoder.
  Byte-sniffed content, 10 MB / 20 MP limits, off-thread decoding, EXIF orientation,
  ICC-to-sRGB conversion and alpha-on-white; outputs metadata-free JPEG up to
  2048 px. Raw-upload sources stored by avatar/garment routes are now normalized
  JPEG, not byte-identical originals. Style retains its 256 px minimum / 1536 px cap.
  `pillow-heif` is required; tests encode/decode real synthetic HEIF, not renamed JPEG.
- `style_analysis.py` validates/normalizes original photos, asks Gemini for
  structured evidence across all photos in a submission, and merges stage state.
- Blocking issues override confidence. Threshold 0.7 is an engineering gate,
  not a calibrated probability. Provider errors propagate to persisted retry state.
- `merge_analysis` preserves usable results, other stages, and profile preferences.
- `FirestoreService.apply_style_analysis` uses a transaction against the latest
  user document. Write failures propagate; local fallback requires explicit dev
  auth bypass. `ensure_user_profile` atomically creates a non-inferred default,
  preserves existing profiles, and is used by profile bootstrap and Magazine so
  pre-profile accounts are not blocked. Other older Firestore methods retain their
  existing fallback behavior.
- No new raw photos are saved by Profile analysis. Existing avatar-source storage
  is separate. Never analyze a generated avatar as evidence of the user's body.
- Uses existing `GEMINI_TEXT_MODEL` and Gemini credentials/Vertex configuration.
- Tests: `python -m unittest discover -s backend/tests -p test_style_analysis.py`.
  Mocked functional tests do not establish live model accuracy.
