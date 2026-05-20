from datetime import date

from pydantic import BaseModel


class ActivityRecord(BaseModel):
    strava_id: int
    date: date
    activity_type: str
    distance_km: float
    duration_seconds: int
    name: str
    average_heartrate: float | None = None
    max_heartrate: float | None = None
    average_watts: float | None = None
    weighted_average_watts: int | None = None
    total_elevation_gain: float | None = None
    average_speed: float | None = None
    suffer_score: int | None = None
    workout_type: int | None = None


class ActivitiesResponse(BaseModel):
    page: int
    per_page: int
    total: int
    items: list[ActivityRecord]
