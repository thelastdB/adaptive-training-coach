import asyncio

from fastapi import APIRouter, Depends, HTTPException

from server.deps import get_current_user

router = APIRouter()


@router.get("/sync")
async def sync_activities(user_id: str = Depends(get_current_user)):
    """Trigger a Strava sync for the current user."""
    from db_supabase import refresh_strava_token
    from strava_fetch import fetch_and_save_activities

    access_token = await asyncio.to_thread(refresh_strava_token, user_id)
    saved = await asyncio.to_thread(
        fetch_and_save_activities,
        user_id,
        access_token,
        90,     # days
    )
    return {"status": "ok", "activities_saved": saved}


@router.get("")
def list_activities(
    page: int = 1,
    per_page: int = 20,
    user_id: str = Depends(get_current_user),
):
    """Return a paginated activity list. (stub — full pagination TBD)"""
    from db_supabase import get_activities
    activities = get_activities(days=None, user_id=user_id)
    start = (page - 1) * per_page
    return {
        "page": page,
        "per_page": per_page,
        "total": len(activities),
        "items": activities[start : start + per_page],
    }


@router.get("/summary")
async def activities_summary(
    days: int = 90,
    user_id: str = Depends(get_current_user),
):
    """Return HR zones, volume, and fitness summary for the current user."""
    from db_supabase import athlete_metrics, get_activities

    activities = await asyncio.to_thread(get_activities, days, user_id)
    metrics = athlete_metrics(activities)
    return {
        "activity_count": len(activities),
        **metrics,
    }
