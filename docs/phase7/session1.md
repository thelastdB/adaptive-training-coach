# Session 1: FastAPI Backend

## Goal
Scaffold the FastAPI backend and wire existing modules as REST endpoints.

## Constraints
- Do not rewrite existing logic. Import and wrap it.
- Use python-jose for JWT, supabase-py for DB.
- All endpoints return typed Pydantic models.
- CORS: allow all origins for now, env-controlled later.

## Tasks (do in order)
1. Create /backend folder structure per docs/phase7/architecture.md
2. Scaffold main.py, routers/, models/, deps.py
3. Stub all endpoints with placeholder 200 responses + correct Pydantic shapes
4. Wire POST /plan/generate to the existing plan generator module
5. Wire GET /activities/summary to the existing activity processor
6. Wire GET /auth/strava + /auth/strava/callback to existing Strava OAuth logic
7. Add /health endpoint
8. Confirm: uvicorn app.main:app --reload starts without errors

## Reference
- Architecture doc: docs/phase7/architecture.md
- Existing plan generator: [path]
- Existing Strava OAuth: [path]
- Existing activity processor: [path]