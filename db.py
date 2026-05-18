from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, Date, Float, Integer, String, create_engine
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


Base.metadata.create_all(engine)


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
            }
            for r in rows
        ]
