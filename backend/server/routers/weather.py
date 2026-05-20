import asyncio

from fastapi import APIRouter, Depends

from server.deps import get_current_user

router = APIRouter()

DEFAULT_LAT = 47.2529
DEFAULT_LON = -122.4443


@router.get("")
async def get_weather(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    user_id: str = Depends(get_current_user),
):
    """Return the current week's weather forecast for the given coordinates."""
    from plan_generator import get_weekly_forecast, weather_summary

    raw = await asyncio.to_thread(get_weekly_forecast, lat, lon)
    return {date: weather_summary(day) for date, day in raw.items()}
