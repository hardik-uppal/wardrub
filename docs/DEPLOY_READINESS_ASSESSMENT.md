# Wardrub Deploy Readiness Assessment

Date: 2026-05-11  
Assessed by: Coding agent (repo audit)

## Executive Summary

Wardrub is currently **dev-runnable** but **not yet deploy-ready for public usage**.

- Frontend builds successfully
- Backend starts successfully and health endpoint responds
- Linting and deployment hygiene/security controls need work before public deployment

---

## What Was Evaluated

### Repository and architecture
- Monorepo modules: `frontend`, `backend`, `image-edit-service`
- Existing docs: root `README.md`, extension progress docs

### Runtime checks
- Frontend:
  - `npm run build` ✅ passed
  - `npm run lint` ❌ failed (8 errors, 3 warnings)
- Backend:
  - `uvicorn app.main:app` ✅ starts
  - `GET /health` ✅ returns `{"status":"ok"}`

### Deployment readiness checks
- Security/secrets handling
- CI/CD presence
- Config/env templates
- Operational docs completeness
- In-progress feature impact

---

## Current State by Area

## 1) Build and Runtime

### ✅ Working
- Frontend production build works (`vite build`)
- Backend imports/compilation pass (`python -m compileall app`)
- Backend service starts and serves `/health`

### ⚠️ Needs attention
- Frontend lint is failing, blocking clean quality gates

---

## 2) Security and Secret Management

### ⚠️ High-priority gaps
- Local secret-bearing files exist in workspace:
  - `backend/.env`
  - `backend/service-account.json`
- `backend/Dockerfile` currently uses `COPY . .`
- No `.dockerignore` found, so local sensitive/artifact files can be copied into build context/image unless excluded

### Impact
- Risk of accidental credential inclusion in images or deploy artifacts

---

## 3) Deployment Automation

### ⚠️ Missing
- No CI workflows found (`.github/workflows/*` absent)
- No cloud build/deploy config files found (e.g. `cloudbuild.yaml`)
- No hosting deploy config in repo root for frontend platform

### Impact
- Deploys are manual and error-prone; no repeatable release pipeline

---

## 4) Documentation and Environment Setup

### ⚠️ Incomplete/misaligned
- Root README references backend `.env.example`, but backend template file is missing
- Frontend README is still mostly Vite template text
- No clear production deployment runbook for this current repo state

---

## 5) Product/Feature Completeness vs Deployment

### ⚠️ In-progress areas
- Chrome extension backend plan is in progress (`docs/progress/chrome-extension-PROGRESS.md`)
- Background scheduler has disabled daily looks job (`backend/app/jobs/scheduler.py` TODO)

### Note
- These do not necessarily block basic deployment, but they do affect feature completeness and launch confidence

---

## 6) Repository Hygiene

### ⚠️ Cleanup candidates in tracked files
- Backend includes large/generated/test artifacts and odd placeholder-like files:
  - `backend/product_match_grid.html`
  - `backend/product_match_grid.png`
  - `backend/vision_api_results.json`
  - `backend/=1.0.0`
  - `backend/=6.0.0`

### Impact
- Increases repo noise and may leak non-essential local artifacts into builds

---

## Effort Estimate

## Option A — Publicly Deployable MVP (manual ops acceptable)

**Estimated effort: 2–4 days**

Scope:
1. Secret hygiene + credential rotation + Docker context hardening
2. Fix frontend lint errors/warnings to acceptable baseline
3. Add env templates and accurate setup/deploy docs
4. Deploy backend + frontend with production env/CORS/domain setup
5. Smoke-test key user flows

## Option B — Production-Grade Launch

**Estimated effort: 1.5–3 weeks**

Includes Option A plus:
1. CI/CD pipeline with quality gates and controlled releases
2. Basic automated tests for critical backend/frontend flows
3. Monitoring/alerts + operational runbook
4. Hardening of retries/timeouts/error handling/security controls

---

## Recommended Next Steps (Prioritized)

1. **Security first**
   - Add `.dockerignore`
   - Ensure secrets are injected via runtime env/secret manager, not copied from workspace
   - Rotate any exposed API keys/credentials as needed

2. **Quality gate cleanup**
   - Fix frontend lint errors and hook dependency warnings

3. **Docs + config correctness**
   - Add `backend/.env.example` and `frontend/.env.example`
   - Replace frontend template README with project-specific instructions

4. **Deployment path**
   - Add explicit backend and frontend deploy configs/scripts
   - Validate CORS and auth behavior in production URLs

5. **Post-deploy hardening**
   - Add CI checks and minimum test coverage for critical flows

---

## Definition of “Deployable” for Wardrub (MVP)

Wardrub can be considered deployable when all of the following are true:

- [ ] Backend and frontend deploy from clean repo without manual local hacks
- [ ] No credentials/secrets in repo or container image layers
- [ ] Frontend lint/build and backend startup checks pass in CI
- [ ] Core user flow works in production:
  - sign-in → avatar → garment upload → try-on → saved look
- [ ] Basic monitoring/log visibility is available for both services

---

## Appendix: Commands used during assessment

- `npm run build` (frontend)
- `npm run lint` (frontend)
- `python -m compileall app` (backend)
- `uvicorn app.main:app` + `curl /health` (backend)
- repo and file inventory checks for docs/config/deploy artifacts
