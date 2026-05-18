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
