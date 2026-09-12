# Agent Memory — backend/app/routers

Last updated: 2026-09-11

## Purpose

Defines HTTP contracts for the backend. Routers are thin layers that validate request shape, enforce auth, and delegate logic to service classes.

## Mental Model

Each router file maps to one product domain:
- `garment.py` for garment ingestion/wardrobe/product matching
- `avatar.py` for avatar creation/retrieval
- `tryon.py` for try-on generation/history
- `profile.py` and `outfit.py` for profile + recommendations
- `extension.py` for Chrome-extension-specific bootstrap and (later) URL try-on flow

Routers are included from `backend/app/main.py` with `/api` prefix.

## Key Files

| File | Role |
|---|---|
| `avatar.py` | Avatar creation/get/delete endpoints |
| `garment.py` | Upload + process garment(s), wardrobe operations, product matching endpoints |
| `tryon.py` | Single/multi try-on, history, look deletion |
| `extension.py` | Extension bootstrap endpoint (`GET /api/extension/bootstrap`) |

## Public Interfaces / Contracts

### Extension

- `GET /api/extension/bootstrap`
  - Auth: required (`Depends(get_current_user)`)
  - Response shape:
    - `user.id` (Firebase UID)
    - `user.email` (optional)
    - `avatar_url` (nullable)
    - `has_avatar` (boolean)

### Existing Core Routes (high-impact)

- `POST /api/profile/analyze`: authenticated multipart `files` (1–4) and
  `stage=auto|color|fit`; persists independent progress through the style service.
  Provider failure returns structured `status=failed` with saved retry state;
  storage failure returns 503. Usable prior recommendations are retained.
- `GET /api/profile`: includes additive `profile.style_analysis` stage progress and
  idempotently initializes a non-inferred default profile for legacy/new accounts.
- `POST /api/create-avatar-full`: opt-in analysis shares the staged service;
  evaluates originals, never a generated avatar. Standard avatar flow is unchanged.

- `POST /api/process-garment`
- `POST /api/process-uploaded-clothes`
- `GET /api/wardrobe`
- `POST /api/create-avatar`
- `GET /api/avatar`
- `POST /api/try-on`
- `POST /api/try-on-multiple`
- `GET /api/try-on/history`

## Dependencies

### Internal

- `app.services.auth.get_current_user` for protected endpoints.
- `app.services.storage.StorageService` for avatar/garment/look object retrieval/upload.
- `app.services.vertex_ai.VertexAIService` for AI generation paths.
- `app.services.firestore.FirestoreService` for metadata/profile persistence.

### External

- FastAPI (`APIRouter`, `Depends`, `HTTPException`).
- Pydantic request/response models.

## Data Flow

Client request -> auth dependency -> parse request model/form-data -> call services -> return normalized response JSON.

## Safe Modification Rules

- Keep endpoint auth consistent with user-scoped data access.
- All avatar/garment multipart photos pass through `read_photo` before model calls
  or source storage. It returns normalized JPEG and actionable HTTP 400 errors.
  Store its bytes with image/jpeg, not the original upload's declared MIME.
  Profile analysis uses the same decoder via its stricter `prepare_photo` wrapper.
- Preserve category constraints (`top`, `bottom`, `dress`, `outerwear`) where applicable.
- If route contracts change, update frontend/extension clients and this memory file.

## Gotchas

- Many route functions are async but call mixed async/sync cloud SDK operations via services.
- Signed URL access can expire; clients should refresh via API calls rather than caching forever.

## Verification

- `python -m unittest discover -s backend/tests` from the repo root in a backend
  test environment; disable dotenv loading for credential-free mocked tests.

- `python3 -m compileall backend/app`
- For endpoint smoke tests, run backend and call route with Bearer token.

## Recent Changes

| Date | Change | Files |
|---|---|---|
| 2026-04-28 | Added extension router skeleton and bootstrap endpoint | `backend/app/routers/extension.py`, `backend/app/main.py` |

## Open Questions

- Should `/api/extension/bootstrap` include display name / profile completion fields for side-panel UX states?
- Should extension endpoints live under `/api/extension/*` (current) or be split by domain for reuse?
