# Agent Memory — backend/app

Last updated: 2026-04-28

## Purpose

Owns the FastAPI application runtime: app bootstrap, middleware, API router registration, domain models, service layer, and background jobs.

## Mental Model

`backend/app/main.py` assembles the API. Startup lifecycle initializes Firebase auth and scheduler jobs. Most business behavior sits in `services/`, while `routers/` expose HTTP contracts and call service methods.

## Key Files

| File | Role |
|---|---|
| `main.py` | FastAPI app creation, CORS/auth middleware, router registration, startup/shutdown lifecycle |
| `config.py` | Environment-backed settings used by all modules |
| `middleware/auth.py` | Request auth middleware behavior |
| `routers/*` | API endpoints grouped by domain |
| `services/*` | Core business integrations (GCS, Firestore, Gemini/Vertex AI, etc.) |
| `jobs/scheduler.py` | APScheduler setup + start/stop |

## Public Interfaces / Contracts

- API base namespace is `/api` via `app.include_router(..., prefix="/api")`.
- Lifecycle startup in `main.py` currently:
  - initializes Firebase (`initialize_firebase()`)
  - starts background description backfill task
  - starts scheduler
- Request logging middleware emits request id, method/path, status, and duration.

## Dependencies

### Internal

- `app.services.auth` for Firebase initialization/auth dependencies.
- `app.jobs.*` for startup scheduler/backfill tasks.
- `app.routers.*` for HTTP interfaces.

### External

- FastAPI / Starlette middleware stack.
- Firebase Admin SDK.
- APScheduler.

## Data Flow

HTTP request -> middleware (CORS, auth, request logging) -> router endpoint -> service layer -> storage/AI/db -> response.

## Safe Modification Rules

- Keep protected endpoints using `Depends(get_current_user)`.
- Register new API domains through `main.py` router includes.
- Preserve startup/shutdown lifecycle behavior unless intentionally changing job/auth initialization.

## Gotchas

- Local shell may only have `python3` (not `python`) for verification commands.
- Some services initialize cloud clients lazily; import-only checks can pass even if runtime creds are missing.

## Verification

- `python3 -m compileall backend/app`

## Recent Changes

| Date | Change | Files |
|---|---|---|
| 2026-04-28 | Added extension router registration | `backend/app/main.py` |

## Open Questions

- Should extension bootstrap eventually include profile readiness fields beyond avatar presence?
