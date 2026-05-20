from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel


class Signal(BaseModel):
    label: str
    text: str
    status: Literal["green", "amber", "red"]


class Assessment(BaseModel):
    volume: Signal
    sport_balance: Signal
    progression: Signal
    event_readiness: Signal | None = None


class ActivityDay(BaseModel):
    day: str
    activity_type: str
    duration_minutes: int
    intensity: str
    description: str
    is_fixed: bool = False
    is_stale: bool = False
    weather_note: str | None = None


class PlanWeek(BaseModel):
    """Raw DB shape — mirrors the columns returned by _row_to_plan_dict()."""
    id: int
    user_id: str
    created_at: datetime | None = None
    week_start_date: date
    schedule: dict[str, Any]
    goal_text: str
    plan: dict[str, Any]
    rating: int | None = None


class ComputedPlanWeek(PlanWeek):
    """PlanWeek extended with fields derived from the plan JSONB blob."""
    focus: str = ""
    event_name: str | None = None
    days_to_event: int | None = None
    days: list[ActivityDay] = []
    assessment: Assessment | None = None


class DaySchedule(BaseModel):
    minutes: int
    time_of_day: Literal["morning", "afternoon", "evening"]


class PlanGenerateRequest(BaseModel):
    schedule: dict[str, DaySchedule]
    goal: str
    location: tuple[float, float] | None = None
    units: str = "imperial"


class PlanGenerateResponse(BaseModel):
    week_goal: str
    days: list[dict[str, Any]]
    plan_id: int | None = None
    validation_summary: dict[str, Any] | None = None
    coaching_assessment: dict[str, Any] | None = None


class ActivityPatch(BaseModel):
    activity_type: str | None = None
    duration_seconds: int | None = None
    intensity: str | None = None
    description: str | None = None
