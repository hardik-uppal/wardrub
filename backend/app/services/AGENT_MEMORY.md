# Agent Memory — backend/app/services

Last updated: 2026-09-12. Scope: progressive style analysis and storage listing.

- The former dated editorial cache is bypassed by the grounded recommender below.
  UTC dates remain display context; refreshing does not call a generation model.
- Release review corrected forecast-parser validation indentation; period parsing,
  fallback, empty forecasts and missing-condition rejection have regression tests
  in `test_weather_forecast.py`.
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

## Grounded recommender — 2026-09-13

- `closet_ranker.py` owns pure bounded candidate generation, eligibility and swaps.
  Valid core: top+bottom or dress; optional outerwear/shoes. Only owned garments,
  current user, no retired demo IDs, no known laundry. Unknown readiness is allowed
  but disclosed. Category shortlists rank all input items before pruning to 12;
  beam width 96; identity/ties use canonical user-scoped garment/category keys.
- `magazine_feed_service.py` now builds rule-grounded LookCards without Gemini or
  cached editorial selection. Every read loads strict current wardrobe/profile;
  no ten-item gate or random underused claim. Null cover means no viable outfit.
  Logical IDs survive UTC dates and refresh, change on swaps, and are not event IDs.
- `weather.py` caches successful coordinate observations for 600 seconds (max128).
  Location changes use a different key; failures remain unknown, malformed missing
  temperatures/conditions are rejected. Actual and feels-like values stay distinct.
- `FirestoreService.list_garments_metadata(limit=None, strict=True)` reads all user
  records and propagates storage failure. Production cannot fall back to stale
  development memory. Memory filtering precedes the limit.
- `set_garment_readiness` uses transaction/CAS with ownership validation, versions,
  exact replay, and conflict detection. Undo is a new versioned change. Metadata
  analysis saves merge and exclude readiness/ownership to preserve confirmations.
- `RecommendationEngine.get_recommendations` also delegates selection to the
  grounded ranker; daily reasoning no longer needs generation. Legacy private
  helpers/dated generated history remain. No implicit-feedback learning yet.
- Verify backend tests and `backend/benchmarks/evaluate_recommender.py` with the
  versioned `training/benchmarks/recommender/v1` fixtures. See progress ledger for
  scope and measured results; synthetic correctness is not taste validation.
