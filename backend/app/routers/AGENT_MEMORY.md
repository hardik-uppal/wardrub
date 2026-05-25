# Agent Memory — backend/app/routers

Last updated: 2026-04-28

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
- Preserve category constraints (`top`, `bottom`, `dress`, `outerwear`) where applicable.
- If route contracts change, update frontend/extension clients and this memory file.

## Gotchas

- Many route functions are async but call mixed async/sync cloud SDK operations via services.
- Signed URL access can expire; clients should refresh via API calls rather than caching forever.

## Verification

- `python3 -m compileall backend/app`
- For endpoint smoke tests, run backend and call route with Bearer token.

## Recent Changes

| Date | Change | Files |
|---|---|---|
| 2026-04-28 | Added extension router skeleton and bootstrap endpoint | `backend/app/routers/extension.py`, `backend/app/main.py` |

## Open Questions

- Should `/api/extension/bootstrap` include display name / profile completion fields for side-panel UX states?
- Should extension endpoints live under `/api/extension/*` (current) or be split by domain for reuse?
