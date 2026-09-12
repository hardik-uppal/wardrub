# Issue #12 — shared image ingestion

Branch `fix/image-format-ingestion`; baseline `edf8530` includes CI timing fix #20.

## Before / after

Before: backend Pillow did not register a HEIF decoder; style explicitly rejected
HEIC, gallery rejected missing MIME, and browser previews could show broken images.
Avatar/garment endpoints forwarded raw, inconsistently validated bytes and MIME.

After: a shared decoder supports JPEG, PNG, WebP, HEIC and HEIF by actual content.
Avatar (simple/full), garment (front/back, gallery, full processing, product matching
and enhanced-info uploads) use it before storage/model work. Style uses it with its
existing stricter sizing rules. Auth/ownership and AI providers are unchanged.

- Pin pillow-heif 0.18.0, compatible with current Pillow 10.4.0.
- Per-photo 10 MB compressed / 20 million decoded pixels. Bounded reads, dimensions
  checked before load, blocking decode in a worker thread. GIF/animated/unsupported,
  corrupt and empty files produce actionable HTTP 400 responses.
- Apply orientation, convert embedded ICC to sRGB, composite transparency on white,
  strip EXIF/GPS/ICC, output JPEG quality 95, max 2048 px. Style: min 256 px,
  max 1536 px, quality 90. Invalid ICC profiles are rejected with an export hint.
- Stored source assets are normalized JPEG and labelled image/jpeg; this does NOT
  retain byte-identical source files, HDR, original metadata or full resolution.
  Existing stored objects are untouched. No new storage location or photo reuse.
- Shared frontend format hints allow HEIC/HEIF including missing/octet-stream MIME
  with recognized extensions. The backend still validates bytes independently.
- Non-blocking preview fallback in gallery, avatar and front/back capture. Native
  camera inputs retain image/* rather than changing mobile capture behavior.

## Verification

- Real synthetic HEIF encode/decode tests (no renamed-JPEG substitution), existing
  JPEG/PNG/WebP, EXIF orientation, color profile, alpha, output size, invalid types,
  byte/pixel limits and MIME mismatch. Style and gallery model-boundary coverage.
- Malformed avatar/gallery inputs rejected before mocked model calls.
- Frontend format/MIME tests and preview fallback/reset tests.
- Full frontend tests, browser journeys, lint, build and build smoke run locally.
- No private photos or actual inference used. This is compatibility evidence, not
  a measured production latency or model-quality improvement.

## Manual release checks still required

Real iPhone Safari: gallery HEIC, full-body avatar HEIC, style selfie HEIC, camera
capture and multi-select. Include portrait/landscape orientation, a Live Photo still,
HDR/wide-gamut and a 48 MP original (expected explicit >20 MP rejection; export at
standard resolution). Compare visible garment colors with a standard JPEG export.
Desktop/mobile Chromium mocks do not prove native iOS picker or codec behavior.
Keep #12 open until this device validation is recorded. HEIF primary still is used;
there is no Live Photo video processing or HDR preservation guarantee.
