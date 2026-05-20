from fastapi import APIRouter, Depends, HTTPException

from server.deps import get_current_user
from server.models.goals import GoalsProfile, TargetEvent, WeeklySchedule

router = APIRouter()


def _fetch_goals_profile(user_id: str) -> GoalsProfile:
    """Read goals from DB and coerce upcoming_events through TargetEvent, dropping malformed entries."""
    from db_supabase import get_goals

    raw = get_goals(user_id=user_id)
    valid_events: list[dict] = []
    for entry in raw.get("upcoming_events") or []:
        try:
            valid_events.append(TargetEvent(**entry).model_dump(mode="json"))
        except Exception:
            pass
    raw["upcoming_events"] = valid_events
    return GoalsProfile(**raw)


@router.get("/goals", response_model=GoalsProfile)
def get_goals_endpoint(user_id: str = Depends(get_current_user)):
    """Return the current user's goals and target events."""
    return _fetch_goals_profile(user_id)


@router.put("/goals", response_model=GoalsProfile)
def update_goals(
    body: GoalsProfile,
    user_id: str = Depends(get_current_user),
):
    """Update the current user's goals."""
    # Strict validation on write — raise 422 if any event fails TargetEvent parsing
    validated_events: list[dict] = []
    for entry in body.upcoming_events:
        try:
            validated_events.append(TargetEvent(**entry).model_dump(mode="json"))
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Invalid event entry: {exc}")

    payload = body.model_dump(mode="json")
    payload["upcoming_events"] = validated_events

    from db_supabase import save_goals

    save_goals(payload, user_id=user_id)
    return _fetch_goals_profile(user_id)


@router.get("/preferences/schedule", response_model=WeeklySchedule)
def get_schedule_endpoint(user_id: str = Depends(get_current_user)):
    """Return the user's weekly availability template."""
    from db_schedule import get_schedule

    row = get_schedule(user_id)
    if row is None:
        return WeeklySchedule(days={}, fixed_commitments=[])
    return WeeklySchedule(**row)


@router.put("/preferences/schedule", response_model=WeeklySchedule)
def update_schedule(
    body: WeeklySchedule,
    user_id: str = Depends(get_current_user),
):
    """Update the user's weekly availability template."""
    from db_schedule import get_schedule, save_schedule

    save_schedule(
        user_id=user_id,
        days={k: v.model_dump() for k, v in body.days.items()},
        fixed_commitments=[c.model_dump() for c in body.fixed_commitments],
    )
    row = get_schedule(user_id)
    return WeeklySchedule(**(row or {"days": {}, "fixed_commitments": []}))
