import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, Date, Float, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import NullPool

engine = create_engine("sqlite:///training.db", poolclass=NullPool)


class Base(DeclarativeBase):
    pass


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True)
    strava_id = Column(Integer, unique=True, nullable=False)
    date = Column(Date, nullable=False)
    activity_type = Column(String, nullable=False)
    distance_km = Column(Float, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    average_heartrate = Column(Float, nullable=True)
    max_heartrate = Column(Float, nullable=True)
    average_watts = Column(Float, nullable=True)
    weighted_average_watts = Column(Integer, nullable=True)
    total_elevation_gain = Column(Float, nullable=True)
    average_speed = Column(Float, nullable=True)   # km/h
    suffer_score = Column(Integer, nullable=True)
    workout_type = Column(Integer, nullable=True)


Base.metadata.create_all(engine)


def _migrate() -> None:
    """Add new columns to existing tables without dropping data."""
    inspector = inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("activities")}
    additions = {
        "average_heartrate": "FLOAT",
        "max_heartrate": "FLOAT",
        "average_watts": "FLOAT",
        "weighted_average_watts": "INTEGER",
        "total_elevation_gain": "FLOAT",
        "average_speed": "FLOAT",
        "suffer_score": "INTEGER",
        "workout_type": "INTEGER",
    }
    with engine.connect() as conn:
        for col, typ in additions.items():
            if col not in existing:
                conn.execute(text(f"ALTER TABLE activities ADD COLUMN {col} {typ}"))
        conn.commit()


_migrate()


def save_activities(activities: list[dict]) -> int:
    """Upsert a list of activity dicts keyed by strava_id. Returns count saved."""
    with Session(engine) as session:
        for data in activities:
            obj = session.query(Activity).filter_by(strava_id=data["strava_id"]).first()
            if obj is None:
                obj = Activity()
                session.add(obj)
            for key, value in data.items():
                setattr(obj, key, value)
        session.commit()
    return len(activities)


def athlete_metrics(activities: list[dict]) -> dict:
    """
    Compute per-sport power/HR/pace statistics for validation and evaluation.

    Returns a dict with:
      max_watts          – max average_watts across cycling activities (Ride, VirtualRide)
      avg_watts_by_sport – mean average_watts keyed by sport
      max_hr             – max max_heartrate across all activities
      avg_hr_by_sport    – mean average_heartrate keyed by sport
      summary_text       – preformatted string for LLM prompts
    """
    sport_watts: dict[str, list] = defaultdict(list)
    sport_hr: dict[str, list] = defaultdict(list)
    sport_max_hr: dict[str, list] = defaultdict(list)
    sport_speed: dict[str, list] = defaultdict(list)
    all_max_hr: list[float] = []

    for act in activities:
        sport = act["activity_type"]
        if act.get("average_watts"):
            sport_watts[sport].append(act["average_watts"])
        if act.get("average_heartrate"):
            sport_hr[sport].append(act["average_heartrate"])
        if act.get("average_speed"):
            sport_speed[sport].append(act["average_speed"])
        if act.get("max_heartrate"):
            all_max_hr.append(act["max_heartrate"])
            sport_max_hr[sport].append(act["max_heartrate"])

    cycling_watts = [
        w for sport in ("Ride", "VirtualRide") for w in sport_watts.get(sport, [])
    ]

    all_sports = sorted(set(sport_watts) | set(sport_hr) | set(sport_speed))
    lines = []
    for sport in all_sports:
        parts = []
        if sport_watts[sport]:
            w = sport_watts[sport]
            parts.append(f"power {min(w):.0f}–{max(w):.0f}W (avg {statistics.mean(w):.0f}W)")
        if sport_hr[sport]:
            h = sport_hr[sport]
            parts.append(f"HR {min(h):.0f}–{max(h):.0f} bpm (avg {statistics.mean(h):.0f})")
        if sport_speed[sport]:
            s = sport_speed[sport]
            avg_pace = 60 / statistics.mean(s)
            parts.append(
                f"speed {statistics.mean(s):.1f} km/h "
                f"(~{int(avg_pace)}:{round((avg_pace % 1) * 60):02d}/km)"
            )
        if parts:
            lines.append(f"  {sport}: " + ", ".join(parts))

    return {
        "max_watts": max(cycling_watts) if cycling_watts else None,
        "avg_watts_by_sport": {
            sport: statistics.mean(vals) for sport, vals in sport_watts.items() if vals
        },
        "max_hr": max(all_max_hr) if all_max_hr else None,
        "max_hr_by_sport": {
            sport: max(vals) for sport, vals in sport_max_hr.items() if vals
        },
        "avg_hr_by_sport": {
            sport: statistics.mean(vals) for sport, vals in sport_hr.items() if vals
        },
        "summary_text": "\n".join(lines) if lines else "  No detailed metrics available.",
    }


def get_activities(days: int | None = 90) -> list[dict]:
    """Return activities from the last N days as a list of dicts. Pass days=None for all."""
    with Session(engine) as session:
        q = session.query(Activity)
        if days is not None:
            since = (datetime.now(tz=timezone.utc) - timedelta(days=days)).date()
            q = q.filter(Activity.date >= since)
        rows = q.order_by(Activity.date.desc()).all()
        return [
            {
                "strava_id": r.strava_id,
                "date": r.date,
                "activity_type": r.activity_type,
                "distance_km": r.distance_km,
                "duration_seconds": r.duration_seconds,
                "name": r.name,
                "average_heartrate": r.average_heartrate,
                "max_heartrate": r.max_heartrate,
                "average_watts": r.average_watts,
                "weighted_average_watts": r.weighted_average_watts,
                "total_elevation_gain": r.total_elevation_gain,
                "average_speed": r.average_speed,
                "suffer_score": r.suffer_score,
                "workout_type": r.workout_type,
            }
            for r in rows
        ]
