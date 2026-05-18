import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, Text, create_engine, inspect, text
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


class Goals(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local", index=True)
    objective = Column(Text, nullable=True)
    upcoming_events = Column(Text, nullable=True)    # JSON array
    sport_preferences = Column(Text, nullable=True)  # JSON object
    physical_notes = Column(Text, nullable=True)
    units = Column(String, nullable=True, default="imperial")  # "imperial" | "metric"
    updated_at = Column(DateTime, nullable=True)


class Plans(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local", index=True)
    created_at = Column(DateTime, nullable=False)
    week_start_date = Column(Date, nullable=False)
    schedule = Column(Text, nullable=False)   # JSON
    goal_text = Column(String, nullable=False)
    plan = Column(Text, nullable=False)        # JSON
    rating = Column(Integer, nullable=True)    # 1-5


Base.metadata.create_all(engine)


def _migrate() -> None:
    """Add new columns to existing tables without dropping data."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.connect() as conn:
        if "activities" in table_names:
            existing = {col["name"] for col in inspector.get_columns("activities")}
            for col, typ in {
                "average_heartrate": "FLOAT",
                "max_heartrate": "FLOAT",
                "average_watts": "FLOAT",
                "weighted_average_watts": "INTEGER",
                "total_elevation_gain": "FLOAT",
                "average_speed": "FLOAT",
                "suffer_score": "INTEGER",
                "workout_type": "INTEGER",
            }.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE activities ADD COLUMN {col} {typ}"))

        if "goals" in table_names:
            existing_goals = {col["name"] for col in inspector.get_columns("goals")}
            if "units" not in existing_goals:
                conn.execute(text("ALTER TABLE goals ADD COLUMN units TEXT DEFAULT 'imperial'"))

        conn.commit()


_migrate()


def calculate_hr_zones(max_hr_by_sport: dict) -> dict:
    """
    Compute a 5-zone HR model per sport using standard percentages of max HR.

    Zone 1: <60%    Recovery
    Zone 2: 60-70%  Aerobic base
    Zone 3: 70-80%  Tempo
    Zone 4: 80-90%  Threshold
    Zone 5: 90-100% VO2 max

    Returns {sport: {"max": int, "z1_ceiling": int, "z2_ceiling": int,
                     "z3_ceiling": int, "z4_ceiling": int}}
    """
    zones: dict[str, dict] = {}
    for sport, max_hr in max_hr_by_sport.items():
        if not max_hr:
            continue
        m = int(max_hr)
        zones[sport] = {
            "max":        m,
            "z1_ceiling": int(m * 0.60),
            "z2_ceiling": int(m * 0.70),
            "z3_ceiling": int(m * 0.80),
            "z4_ceiling": int(m * 0.90),
        }
    return zones


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


def save_goals(goals_dict: dict, user_id: str = "local") -> None:
    """Upsert the goals profile for a user (one record per user_id)."""
    with Session(engine) as session:
        obj = session.query(Goals).filter_by(user_id=user_id).first()
        if obj is None:
            obj = Goals(user_id=user_id)
            session.add(obj)
        obj.objective = goals_dict.get("objective") or ""
        obj.upcoming_events = json.dumps(goals_dict.get("upcoming_events") or [])
        obj.sport_preferences = json.dumps(goals_dict.get("sport_preferences") or {})
        obj.physical_notes = goals_dict.get("physical_notes") or ""
        obj.units = goals_dict.get("units") or "imperial"
        obj.updated_at = datetime.now(tz=timezone.utc)
        session.commit()


def get_goals(user_id: str = "local") -> dict | None:
    """Return the goals profile for a user, or None if not set."""
    with Session(engine) as session:
        obj = session.query(Goals).filter_by(user_id=user_id).first()
        if obj is None:
            return None
        return {
            "user_id": obj.user_id,
            "objective": obj.objective or "",
            "upcoming_events": json.loads(obj.upcoming_events or "[]"),
            "sport_preferences": json.loads(obj.sport_preferences or "{}"),
            "physical_notes": obj.physical_notes or "",
            "units": obj.units or "imperial",
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }


def save_plan(
    schedule: dict,
    goal_text: str,
    plan: dict,
    user_id: str = "local",
) -> int:
    """
    Upsert a generated plan keyed by (user_id, week_start_date).
    Regenerating for the same week overwrites rather than appending.
    Returns the plan id.
    """
    today = datetime.now(tz=timezone.utc).date()
    week_start = today - timedelta(days=today.weekday())  # Monday of current week
    with Session(engine) as session:
        obj = session.query(Plans).filter_by(user_id=user_id, week_start_date=week_start).first()
        if obj is None:
            obj = Plans(user_id=user_id, week_start_date=week_start)
            session.add(obj)
        obj.created_at = datetime.now(tz=timezone.utc)
        obj.schedule = json.dumps(schedule, default=str)
        obj.goal_text = goal_text
        obj.plan = json.dumps(plan, default=str)
        session.flush()
        plan_id = obj.id
        session.commit()
        return plan_id


def _plan_row_to_dict(r: Plans) -> dict:
    return {
        "id": r.id,
        "user_id": r.user_id,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "week_start_date": r.week_start_date.isoformat() if r.week_start_date else None,
        "schedule": json.loads(r.schedule or "{}"),
        "goal_text": r.goal_text,
        "plan": json.loads(r.plan or "{}"),
        "rating": r.rating,
    }


def get_plans(user_id: str = "local", limit: int = 10) -> list[dict]:
    """Return the most recent N plans for a user, newest first."""
    with Session(engine) as session:
        rows = (
            session.query(Plans)
            .filter_by(user_id=user_id)
            .order_by(Plans.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_plan_row_to_dict(r) for r in rows]


def get_plan(plan_id: int) -> dict | None:
    """Return a single plan by id, or None if not found."""
    with Session(engine) as session:
        obj = session.query(Plans).filter_by(id=plan_id).first()
        return _plan_row_to_dict(obj) if obj else None


def rate_plan(plan_id: int, rating: int) -> bool:
    """Set the 1-5 rating on a plan. Returns True if the plan was found."""
    if rating not in range(1, 6):
        raise ValueError(f"rating must be 1-5, got {rating}")
    with Session(engine) as session:
        obj = session.query(Plans).filter_by(id=plan_id).first()
        if obj is None:
            return False
        obj.rating = rating
        session.commit()
        return True


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
