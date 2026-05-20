import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from server.deps import get_current_user
from server.models.plan import (
    ActivityDay,
    ActivityPatch,
    Assessment,
    ComputedPlanWeek,
    PlanGenerateRequest,
    PlanGenerateResponse,
    PlanWeek,
)

router = APIRouter()


def _build_computed(raw: dict) -> ComputedPlanWeek:
    """Build a ComputedPlanWeek from the raw dict returned by _row_to_plan_dict()."""
    blob: dict[str, Any] = raw.get("plan") or {}

    days: list[ActivityDay] = []
    for d in blob.get("days") or []:
        try:
            days.append(ActivityDay(**d))
        except Exception:
            pass

    assessment: Assessment | None = None
    if ca := blob.get("coaching_assessment"):
        try:
            assessment = Assessment(**ca)
        except Exception:
            pass

    return ComputedPlanWeek(
        **raw,
        focus=blob.get("week_goal") or "",
        days=days,
        assessment=assessment,
    )


@router.get("/current", response_model=ComputedPlanWeek)
def get_current_plan(user_id: str = Depends(get_current_user)):
    """Return the most recent generated plan for the current week."""
    from db_supabase import get_plans

    plans = get_plans(user_id=user_id, limit=1)
    if not plans:
        raise HTTPException(status_code=404, detail="No plan found")
    return _build_computed(plans[0])


@router.post("/generate", response_model=PlanGenerateResponse)
async def generate(
    body: PlanGenerateRequest,
    user_id: str = Depends(get_current_user),
):
    """Generate (or regenerate) a weekly training plan."""
    from db_supabase import get_goals
    from plan_generator import DEFAULT_LOCATION, generate_plan

    goals = await asyncio.to_thread(get_goals, user_id)

    schedule = {day: s.model_dump() for day, s in body.schedule.items()}
    location = tuple(body.location) if body.location else DEFAULT_LOCATION

    plan = await asyncio.to_thread(
        generate_plan,
        schedule,
        body.goal,
        location,
        None,
        goals,
        body.units,
        None,
        user_id,
    )
    return plan


@router.patch("/{week_id}/activity/{day}")
def patch_activity(
    week_id: str,
    day: str,
    body: ActivityPatch,
    user_id: str = Depends(get_current_user),
):
    """Move or edit a single activity within a plan. (stub)"""
    return {"status": "ok", "week_id": week_id, "day": day}


@router.delete("/{week_id}/activity/{day}")
def delete_activity(
    week_id: str,
    day: str,
    user_id: str = Depends(get_current_user),
):
    """Remove an activity from a plan. (stub)"""
    return {"status": "ok", "week_id": week_id, "day": day}


@router.post("/{week_id}/evaluate")
def evaluate_plan(
    week_id: str,
    user_id: str = Depends(get_current_user),
):
    """Run the eval framework against a plan and return scores. (stub)"""
    return {"status": "ok", "week_id": week_id, "scores": {}}


@router.get("/history", response_model=list[PlanWeek])
def plan_history(
    limit: int = 10,
    user_id: str = Depends(get_current_user),
):
    """Return past generated plans, newest first."""
    from db_supabase import get_plans

    return get_plans(user_id=user_id, limit=limit)
