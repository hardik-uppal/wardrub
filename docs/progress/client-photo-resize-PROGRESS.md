# Client clothing-photo resizing

## Scope and evidence

Follow-up to PR #28 on `fix/client-photo-resize`. Production logs confirmed four JPEG-named clothing uploads returned HTTP 400 during normalization, before detection/generation. The exact rejection detail and original files were unavailable. A high-resolution iPhone photo exceeding the server's 20 MP limit is a hypothesis, not a confirmed root cause.

## Implementation

- Shared `prepareClothingPhoto` utility is called by `processUploadedClothes` for both camera and gallery before multipart submission. Other avatar/style upload paths are unchanged.
- Clothing picker accepts up to 25 MB per source (five-photo batch remains); preparation/uploads remain sequential. Browser-decodable images above 2048 pixels on either edge are resized proportionally and encoded as actual JPEG at quality 0.92. No upscaling. Transparent pixels are composited on white; browser EXIF orientation is respected. Small originals remain unchanged for server normalization.
- Prepared uploads must stay under the existing 10 MB server limit. Canvas resources and preparation object URLs are released. Images above 64 MP are rejected after the browser reports dimensions. This is not a guarantee of bounded native decoder memory; real-device peak-memory testing remains needed, including batch previews.
- Accept `image/jpg` MIME alias as well as `image/jpeg`; server byte validation remains authoritative.
- If browser decoding fails, pass original bytes/MIME to the server only within 10 MB. Never rename undecoded HEIC into purported JPEG. Larger undecodable inputs get an explicit smaller-JPEG instruction.
- **HEIC limitation:** browser support varies. Server fallback still rejects over-20-MP originals. This change does not solve every high-resolution HEIC case; Safari/device checks and a consented original failing photo remain required.
- No new dependency, backend limit increase, paid model request or model change.

## Verification

- ESLint, production build and static-route smoke checks passed.
- 77 unit tests passed on rerun. Initial run hit an existing legacy MagazineFeed mock race (`ClosetReadiness` received an undefined garments list); no unrelated source/test fix included.
- Full 32-test browser suite passed with `--timeout=90000`. Default 30-second run passed 30 tests but timed out both existing 18-screen visual sweeps; longer run took ~39/~33 seconds for those tests. Repository timeout configuration unchanged.
- Subsequently added real EXIF-rotation regression; all six focused mobile/desktop resize tests passed with default timeout. Tests generate 24/48 MP JPEGs, exercise the real browser encoder and inspect outgoing multipart JPEG bytes/dimensions. API responses are mocked; no model calls or private photos used.
- Chromium mobile emulation is not validation on a physical iPhone/Safari. Vanika's exact issue remains unconfirmed.

Not merged or deployed. Review and device verification precede rollout.
