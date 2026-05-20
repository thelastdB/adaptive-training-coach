"""
db_schedule.py — Persistence for user_schedule table.

Uses the same psycopg2 / SUPABASE_DB_URL pattern as db_supabase.py.
Run backend/migrations/001_weekly_schedule.sql in Supabase before deploying.
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]


@contextmanager
def _conn():
    conn = psycopg2.connect(dsn=SUPABASE_DB_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_schedule(user_id: str) -> dict | None:
    """Return the user's weekly schedule row, or None if no row exists yet."""
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT days, fixed_commitments FROM user_schedule WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    days = row["days"]
    commitments = row["fixed_commitments"]
    # JSONB comes back as Python objects from psycopg2, but guard for TEXT fallback
    if isinstance(days, str):
        days = json.loads(days)
    if isinstance(commitments, str):
        commitments = json.loads(commitments)
    return {"days": days, "fixed_commitments": commitments}


def save_schedule(user_id: str, days: dict, fixed_commitments: list) -> None:
    """Upsert the weekly schedule for a user."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_schedule (user_id, days, fixed_commitments, updated_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    days              = EXCLUDED.days,
                    fixed_commitments = EXCLUDED.fixed_commitments,
                    updated_at        = EXCLUDED.updated_at
                """,
                (
                    user_id,
                    json.dumps(days),
                    json.dumps(fixed_commitments),
                    datetime.now(tz=timezone.utc),
                ),
            )
