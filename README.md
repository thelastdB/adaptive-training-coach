# Adaptive Training Coach

An AI-powered training plan generator that adapts to your actual fitness 
data, schedule, and goals.

🚀 **[Live app](https://adaptive-training-coach-9lkoq4b5w2ulbhd4mamhm2.streamlit.app)**

## What it does

Adaptive Training Coach connects to your Strava account and generates 
personalized weekly training plans grounded in your real training history. 
Unlike static training plans, it adapts to:

- **Your actual fitness data** — wattage targets, HR zones, and pace 
  targets derived from your recorded activities, not textbook values
- **Your schedule** — tell it which days you have available and how much 
  time, and it plans accordingly
- **Weather conditions** — checks the forecast and recommends indoor vs 
  outdoor sessions, adjusts for humidity, wind, and temperature
- **Your goals** — upcoming events (races, centuries, sportives) with 
  countdown-aware training phases (build, peak, taper)
- **Recovery** — detects back-to-back hard efforts, consecutive training 
  days, and post-hard-effort recovery needs

## How it works

1. **Connect Strava** — OAuth authentication syncs your last 90 days of 
   activities
2. **Set your profile** — add upcoming events, sport preferences, and any 
   physical notes (injuries, fitness level)
3. **Enter your weekly schedule** — toggle available days, set time 
   available and time of day per session
4. **Generate a plan** — AI generates a structured weekly plan with 
   specific workout descriptions, intensity targets, and weather-aware 
   recommendations
5. **Coaching assessment** — each plan includes a RED/YELLOW/GREEN 
   assessment of volume, sport balance, progression, and event readiness

## Architecture

- **Data pipeline** — Strava API → Supabase Postgres
- **RAG retrieval** — pgvector similarity search over activity history, 
  so plans reference workouts you've actually done
- **Deterministic rule engine** — 10 coaching rules applied before the LLM 
  runs (indoor/outdoor, intensity caps, recovery logic, time constraints)
- **Plan generation** — Claude Sonnet with athlete-specific HR zones, 
  wattage ranges, and pace targets
- **Validation layer** — post-generation checks with targeted repair for 
  out-of-range targets
- **Eval framework** — LLM-as-judge scoring across 6 criteria, used to 
  iterate prompt quality (baseline 4.04 → 4.50 overall)

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| LLM | Anthropic Claude Sonnet |
| Embeddings | OpenAI text-embedding-3-small |
| Database | Supabase Postgres |
| Vector search | pgvector |
| Weather | Open-Meteo (free, no API key) |
| Auth | Strava OAuth |
| Hosting | Streamlit Community Cloud |

## Local development

```bash
# Clone and install
git clone https://github.com/thelastdB/adaptive-training-coach
cd adaptive-training-coach
uv install

# Set up environment variables
cp .env.example .env
# Add your API keys to .env

# Run locally
uv run streamlit run app.py
```

Required environment variables:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `SUPABASE_DB_URL`
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STREAMLIT_APP_URL`

## Status

Live and in active development. Built as a portfolio project to demonstrate 
practical AI product skills: RAG pipelines, prompt engineering, eval 
frameworks, and multi-user architecture.

**Planned:** FastAPI backend, React frontend, Garmin HRV/recovery 
integration, email delivery of weekly plans.