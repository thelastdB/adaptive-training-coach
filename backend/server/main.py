import sys
from pathlib import Path

# Append repo root so existing modules (plan_generator, db_supabase, etc.) are importable.
# append() not insert(0) — the repo root contains app.py which must never shadow this package.
_repo_root = str(Path(__file__).parent.parent.parent)
if _repo_root not in sys.path:
    sys.path.append(_repo_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routers import activities, auth, goals, plan, weather

app = FastAPI(title="eigentakt API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,       prefix="/api/v1/auth",       tags=["auth"])
app.include_router(plan.router,       prefix="/api/v1/plan",        tags=["plan"])
app.include_router(activities.router, prefix="/api/v1/activities",  tags=["activities"])
app.include_router(goals.router,      prefix="/api/v1",             tags=["goals"])
app.include_router(weather.router,    prefix="/api/v1/weather",     tags=["weather"])


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
