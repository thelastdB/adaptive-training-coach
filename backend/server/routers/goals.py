from fastapi import APIRouter, Depends

from server.deps import get_current_user
from server.models.goals import GoalsProfile, WeeklySchedule

router = APIRouter()


@router.get("/goals", response_model=GoalsProfile)
def get_goals_endpoint(user_id: str = Depends(get_current_user)):
    """Return the current user's goals and target events."""
    from db_supabase import get_goals
    return get_goals(user_id=user_id)


@router.put("/goals", response_model=GoalsProfile)
def update_goals(
    body: GoalsProfile,
    user_id: str = Depends(get_current_user),
):
    """Update the current user's goals."""
    from db_supabase import save_goals
    save_goals(body.model_dump(), user_id=user_id)
    from db_supabase import get_goals
    return get_goals(user_id=user_id)


@router.get("/preferences/schedule")
def get_schedule(user_id: str = Depends(get_current_user)):
    """Return the user's weekly availability template. (stub)"""
    return WeeklySchedule(days={}, fixed_commitments=[])


@router.put("/preferences/schedule")
def update_schedule(
    body: WeeklySchedule,
    user_id: str = Depends(get_current_user),
):
    """Update the user's weekly availability template. (stub)"""
    return body
