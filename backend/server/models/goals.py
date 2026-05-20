from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class TargetEvent(BaseModel):
    name: str
    date: date
    sport: str
    distance_km: float | None = None
    notes: str | None = None


class Goal(BaseModel):
    type: Literal["target_event", "build_base", "return_to_training"]
    event: TargetEvent | None = None


class GoalsProfile(BaseModel):
    objective: str = ""
    upcoming_events: list[dict] = []
    sport_preferences: dict = {}
    physical_notes: str = ""
    units: str = "imperial"
    updated_at: datetime | None = None


class DayAvailability(BaseModel):
    enabled: bool
    duration_minutes: int


class FixedCommitment(BaseModel):
    day: str
    time: str
    duration_minutes: int
    label: str


class WeeklySchedule(BaseModel):
    days: dict[str, DayAvailability]
    fixed_commitments: list[FixedCommitment]
