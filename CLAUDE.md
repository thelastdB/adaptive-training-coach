# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the Streamlit app (current production UI)
uv run streamlit run app.py

# Run the plan generator as a CLI (prints full JSON plan to stdout)
uv run python plan_generator.py

# Fetch Strava activities to local DB
uv run python strava_fetch.py

# Run the eval suite (LLM-as-judge scoring)
uv run python eval.py

# Run the FastAPI backend (Phase 7 in-progress)
cd backend && uvicorn server.main:app --reload

# Dependency management — use uv, not pip
uv add <package>
uv sync
```

Python version: 3.13 (managed by `.python-version`). Virtual env at `.venv/`.

## Architecture

This project is called **eigentakt**. It generates personalized weekly training plans using Strava activity history, a deterministic rule engine, and Claude.

### Current state (what's deployed)

The **Streamlit frontend** (`app.py`) is the live app at Streamlit Community Cloud. All DB access goes through `db_supabase.py` (raw psycopg2 against Supabase Postgres). The `backend/` directory contains a FastAPI backend that is being built out as part of the Phase 7 migration.

### Key modules

| File | Role |
|------|------|
| `app.py` | Streamlit frontend — auth gate, schedule builder, plan display, history, profile |
| `plan_generator.py` | Core AI pipeline — weather fetch, rule engine, prompt assembly, Claude call, validation |
| `db_supabase.py` | All DB operations — users, activities, goals, plans, Strava token refresh |
| `vector_store_supabase.py` | pgvector embeddings — stores and searches activity text via OpenAI |
| `strava_fetch.py` | Strava API client — fetches activities and saves them |
| `eval.py` | LLM-as-judge eval framework — 6 criteria, saves results to `eval_results/` |
| `backend/server/main.py` | FastAPI app init — imports routers from `backend/server/routers/` |

### Plan generation pipeline (`plan_generator.py`)

The pipeline runs in strict order:

1. **Fetch weather** — Open-Meteo 7-day forecast (free, no key). Temperature stored internally as °C; converted to °F only for display when `units="imperial"`.
2. **Rule engine** (`resolve_training_conditions`) — 10 deterministic rules set `indoor`, `suggested_activity_type`, `intensity_cap`, and `flags` for each day. Runs *before* the LLM. The LLM must honor these decisions.
3. **RAG retrieval** (`search_activities`) — pgvector cosine similarity search over past workout descriptions.
4. **LLM call** — Claude Sonnet with a system prompt that includes athlete HR zones and profile. Streaming mode when `on_token` callback is provided.
5. **Validation** (`validate_day`) — checks wattage sanity, HR ceilings, duration, and non-cycling watt prescriptions.
6. **Repair** (`repair_day`) — if critical violations found, calls Claude again with targeted instructions. If repair still fails, `_fallback_fix_day` applies regex-based deterministic corrections.
7. **Coaching assessment** (`assess_training_week`) — deterministic RED/YELLOW/GREEN signals, then LLM enriches them with one-sentence explanations.

### Database

Supabase Postgres via psycopg2 with direct `SUPABASE_DB_URL`. DDL (CREATE TABLE, CREATE EXTENSION) must use `_autocommit_conn()` because the transaction-mode pooler rejects DDL in transactions. Regular queries use `_conn()` which auto-commits on clean exit.

The pgvector extension must be enabled before `setup_embeddings_table()` — either via Supabase dashboard or it attempts `CREATE EXTENSION IF NOT EXISTS vector` automatically (requires superuser).

`db.py` is the old SQLite implementation — no longer used, kept for reference.

### Phase 7 — FastAPI + React migration

Documented in `docs/phase7/architecture.md`. The backend routers live at `backend/server/routers/` (not `backend/app/routers/` as some older docs suggest). The React frontend described in the architecture doc does not yet exist in this repo.

JWT auth: issued on Strava OAuth callback, stored in `localStorage`, attached via Axios interceptor. On 401, clear token and redirect to `/login`.

## Design system (eigentakt)

Design references live in `design-reference/`. When implementing UI, **read the HTML files directly** — they are the canonical source for tokens, component states, and layout.

- `eigentakt_calendar_reference.html` — primary week view reference (tokens, card states)
- `eigentakt_brand_system.md` — brand values and motion direction

CSS custom properties (all prefixed `--et-`): graphite `#2C2C2A`, olive `#4A5C3E`, bone `#F5F2EC`. Fonts: Geist (UI), Lora (editorial), Geist Mono (metrics). No Tailwind, no CSS-in-JS.

## Environment variables

Required in `.env`:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY` (embeddings)
- `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_DB_URL`
- `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`
- `STREAMLIT_APP_URL` (OAuth redirect URI)

Backend (Railway) also needs `JWT_SECRET` and `CORS_ORIGINS`.
