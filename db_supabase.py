"""
db_supabase.py — Supabase Postgres reimplementation of all db.py functions.

Uses psycopg2 with the SUPABASE_DB_URL connection string (transaction-mode pooler).
All queries are parameterized — no user-input string formatting.

NOTE: setup_schema() requires DDL privileges. If the pooler rejects CREATE TABLE,
run the setup SQL directly in the Supabase dashboard SQL editor.
"""

import json
import os
import statistics
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras
import requests as _http
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]


# ---------------------------------------------------------------------------
# Connection helper
# ---------------------------------------------------------------------------

@contextmanager
def _conn():
    """
    Yield a psycopg2 connection.
    Commits on clean exit, rolls back and re-raises on any exception.
    Always closes the connection.
    """
    conn = psycopg2.connect(dsn=SUPABASE_DB_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def _autocommit_conn():
    """
    Yield a connection with autocommit=True — required for DDL (CREATE TABLE,
    CREATE EXTENSION) when using a transaction-mode pooler.
    """
    conn = psycopg2.connect(dsn=SUPABASE_DB_URL)
    conn.autocommit = True
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema setup
# ---------------------------------------------------------------------------

def setup_schema() -> None:
    """
    Create all application tables if they don't exist.

    Tables created:
      users        — one row per Strava athlete (for Phase 6 OAuth)
      activities   — Strava activities with metrics
      goals        — one goals profile per user
      plans        — one generated plan per user per week
    """
    with _autocommit_conn() as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id                  BIGSERIAL PRIMARY KEY,
                    strava_athlete_id   BIGINT      UNIQUE NOT NULL,
                    access_token        TEXT,
                    refresh_token       TEXT,
                    token_expires_at    BIGINT,
                    athlete_name        TEXT,
                    athlete_profile_pic TEXT,
                    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
            # Idempotent migrations for existing installs that have the old minimal schema
            for col, ddl in [
                ("access_token",        "TEXT"),
                ("refresh_token",       "TEXT"),
                ("token_expires_at",    "BIGINT"),
                ("athlete_name",        "TEXT"),
                ("athlete_profile_pic", "TEXT"),
            ]:
                cur.execute(
                    f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {ddl}"
                )

            cur.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id                     BIGSERIAL PRIMARY KEY,
                    user_id                TEXT    NOT NULL DEFAULT 'local',
                    strava_id              BIGINT  NOT NULL,
                    date                   DATE    NOT NULL,
                    activity_type          TEXT    NOT NULL,
                    distance_km            FLOAT   NOT NULL DEFAULT 0,
                    duration_seconds       INTEGER NOT NULL DEFAULT 0,
                    name                   TEXT    NOT NULL DEFAULT '',
                    average_heartrate      FLOAT,
                    max_heartrate          FLOAT,
                    average_watts          FLOAT,
                    weighted_average_watts INTEGER,
                    total_elevation_gain   FLOAT,
                    average_speed          FLOAT,
                    suffer_score           INTEGER,
                    workout_type           INTEGER,
                    UNIQUE (user_id, strava_id)
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS activities_user_date_idx
                ON activities (user_id, date DESC)
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id                BIGSERIAL PRIMARY KEY,
                    user_id           TEXT        NOT NULL DEFAULT 'local',
                    objective         TEXT,
                    upcoming_events   JSONB       NOT NULL DEFAULT '[]',
                    sport_preferences JSONB       NOT NULL DEFAULT '{}',
                    physical_notes    TEXT,
                    units             TEXT        DEFAULT 'imperial',
                    updated_at        TIMESTAMPTZ,
                    UNIQUE (user_id)
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    id              BIGSERIAL PRIMARY KEY,
                    user_id         TEXT        NOT NULL DEFAULT 'local',
                    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    week_start_date DATE        NOT NULL,
                    schedule        JSONB       NOT NULL DEFAULT '{}',
                    goal_text       TEXT        NOT NULL DEFAULT '',
                    plan            JSONB       NOT NULL DEFAULT '{}',
                    rating          INTEGER     CHECK (rating BETWEEN 1 AND 5),
                    UNIQUE (user_id, week_start_date)
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS plans_user_created_idx
                ON plans (user_id, created_at DESC)
            """)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def get_or_create_user(strava_athlete_id: int) -> str:
    """
    Upsert a minimal user record keyed by strava_athlete_id.
    Returns user_id as str(strava_athlete_id).
    Prefer upsert_user() for OAuth flows that supply token and profile data.
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (strava_athlete_id)
                VALUES (%s)
                ON CONFLICT (strava_athlete_id) DO NOTHING
                """,
                (int(strava_athlete_id),),
            )
    return str(strava_athlete_id)


def upsert_user(
    strava_athlete_id: int | str,
    access_token: str,
    refresh_token: str,
    token_expires_at: int,
    athlete_name: str,
    athlete_profile_pic: str,
) -> str:
    """
    Upsert a user with full OAuth token and profile data.
    Returns user_id = str(strava_athlete_id), which is the value stored in
    the user_id column of activities / goals / plans tables.
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users
                    (strava_athlete_id, access_token, refresh_token,
                     token_expires_at, athlete_name, athlete_profile_pic)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (strava_athlete_id) DO UPDATE SET
                    access_token        = EXCLUDED.access_token,
                    refresh_token       = EXCLUDED.refresh_token,
                    token_expires_at    = EXCLUDED.token_expires_at,
                    athlete_name        = EXCLUDED.athlete_name,
                    athlete_profile_pic = EXCLUDED.athlete_profile_pic
                """,
                (
                    int(strava_athlete_id),
                    access_token,
                    refresh_token,
                    token_expires_at,
                    athlete_name,
                    athlete_profile_pic,
                ),
            )
    return str(strava_athlete_id)


def get_user_by_strava_id(strava_athlete_id: int | str) -> dict | None:
    """Return the full users row for a given Strava athlete id, or None."""
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM users WHERE strava_athlete_id = %s",
                (int(strava_athlete_id),),
            )
            row = cur.fetchone()
    return dict(row) if row else None


def refresh_strava_token(user_id: str) -> str:
    """
    Return a valid Strava access token for user_id (= str(strava_athlete_id)).
    If the stored token expires within 5 minutes, calls the Strava refresh
    endpoint, persists the new tokens, and returns the fresh access_token.

    Raises RuntimeError if no user record is found.
    Requires STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in the environment.
    """
    user = get_user_by_strava_id(user_id)
    if user is None:
        raise RuntimeError(f"No user record found for user_id={user_id!r}")

    expires_at = user.get("token_expires_at") or 0
    if int(expires_at) > time.time() + 300:
        return user["access_token"]

    resp = _http.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id":     os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "refresh_token": user["refresh_token"],
            "grant_type":    "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    token_data = resp.json()

    new_access  = token_data["access_token"]
    new_refresh = token_data["refresh_token"]
    new_expires = int(token_data["expires_at"])

    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users
                SET access_token = %s, refresh_token = %s, token_expires_at = %s
                WHERE strava_athlete_id = %s
                """,
                (new_access, new_refresh, new_expires, int(user_id)),
            )

    return new_access


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------

def save_activities(activities: list[dict], user_id: str = "local") -> int:
    """
    Upsert a list of activity dicts keyed by (user_id, strava_id).
    Returns the number of rows processed.
    All column values are passed as parameters — no string interpolation.
    """
    if not activities:
        return 0

    with _conn() as conn:
        with conn.cursor() as cur:
            for data in activities:
                cur.execute(
                    """
                    INSERT INTO activities (
                        user_id, strava_id, date, activity_type,
                        distance_km, duration_seconds, name,
                        average_heartrate, max_heartrate, average_watts,
                        weighted_average_watts, total_elevation_gain,
                        average_speed, suffer_score, workout_type
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s
                    )
                    ON CONFLICT (user_id, strava_id) DO UPDATE SET
                        date                   = EXCLUDED.date,
                        activity_type          = EXCLUDED.activity_type,
                        distance_km            = EXCLUDED.distance_km,
                        duration_seconds       = EXCLUDED.duration_seconds,
                        name                   = EXCLUDED.name,
                        average_heartrate      = EXCLUDED.average_heartrate,
                        max_heartrate          = EXCLUDED.max_heartrate,
                        average_watts          = EXCLUDED.average_watts,
                        weighted_average_watts = EXCLUDED.weighted_average_watts,
                        total_elevation_gain   = EXCLUDED.total_elevation_gain,
                        average_speed          = EXCLUDED.average_speed,
                        suffer_score           = EXCLUDED.suffer_score,
                        workout_type           = EXCLUDED.workout_type
                    """,
                    (
                        user_id,
                        data["strava_id"],
                        data["date"],
                        data["activity_type"],
                        data.get("distance_km", 0),
                        data.get("duration_seconds", 0),
                        data.get("name") or "",
                        data.get("average_heartrate"),
                        data.get("max_heartrate"),
                        data.get("average_watts"),
                        data.get("weighted_average_watts"),
                        data.get("total_elevation_gain"),
                        data.get("average_speed"),
                        data.get("suffer_score"),
                        data.get("workout_type"),
                    ),
                )
    return len(activities)


def get_activities(days: int | None = 90, user_id: str = "local") -> list[dict]:
    """
    Return activities for a user from the last N days.
    Pass days=None to return all activities.
    """
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if days is not None:
                since = (datetime.now(tz=timezone.utc) - timedelta(days=days)).date()
                cur.execute(
                    """
                    SELECT strava_id, date, activity_type, distance_km,
                           duration_seconds, name, average_heartrate, max_heartrate,
                           average_watts, weighted_average_watts, total_elevation_gain,
                           average_speed, suffer_score, workout_type
                    FROM activities
                    WHERE user_id = %s AND date >= %s
                    ORDER BY date DESC
                    """,
                    (user_id, since),
                )
            else:
                cur.execute(
                    """
                    SELECT strava_id, date, activity_type, distance_km,
                           duration_seconds, name, average_heartrate, max_heartrate,
                           average_watts, weighted_average_watts, total_elevation_gain,
                           average_speed, suffer_score, workout_type
                    FROM activities
                    WHERE user_id = %s
                    ORDER BY date DESC
                    """,
                    (user_id,),
                )
            return [dict(row) for row in cur.fetchall()]


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------

def save_goals(goals_dict: dict, user_id: str = "local") -> None:
    """Upsert the goals profile for a user (one record per user_id)."""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO goals
                    (user_id, objective, upcoming_events, sport_preferences,
                     physical_notes, units, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    objective         = EXCLUDED.objective,
                    upcoming_events   = EXCLUDED.upcoming_events,
                    sport_preferences = EXCLUDED.sport_preferences,
                    physical_notes    = EXCLUDED.physical_notes,
                    units             = EXCLUDED.units,
                    updated_at        = EXCLUDED.updated_at
                """,
                (
                    user_id,
                    goals_dict.get("objective") or "",
                    json.dumps(goals_dict.get("upcoming_events") or []),
                    json.dumps(goals_dict.get("sport_preferences") or {}),
                    goals_dict.get("physical_notes") or "",
                    goals_dict.get("units") or "imperial",
                    datetime.now(tz=timezone.utc),
                ),
            )


def get_goals(user_id: str = "local") -> dict | None:
    """Return the goals profile for a user, or None if not set."""
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM goals WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    # JSONB columns come back as Python dicts/lists from psycopg2
    events = row["upcoming_events"]
    prefs = row["sport_preferences"]
    return {
        "user_id":          row["user_id"],
        "objective":        row["objective"] or "",
        "upcoming_events":  events if isinstance(events, list) else json.loads(events or "[]"),
        "sport_preferences": prefs if isinstance(prefs, dict) else json.loads(prefs or "{}"),
        "physical_notes":   row["physical_notes"] or "",
        "units":            row["units"] or "imperial",
        "updated_at":       row["updated_at"].isoformat() if row["updated_at"] else None,
    }


# ---------------------------------------------------------------------------
# Plans
# ---------------------------------------------------------------------------

def _row_to_plan_dict(row: dict) -> dict:
    """Convert a psycopg2 row dict to the canonical plan dict format."""
    schedule = row["schedule"]
    plan_data = row["plan"]
    # Defensive: JSONB comes back as dict, TEXT-JSON as string
    if isinstance(schedule, str):
        schedule = json.loads(schedule)
    if isinstance(plan_data, str):
        plan_data = json.loads(plan_data)
    return {
        "id":              row["id"],
        "user_id":         row["user_id"],
        "created_at":      row["created_at"].isoformat() if row.get("created_at") else None,
        "week_start_date": row["week_start_date"].isoformat() if row.get("week_start_date") else None,
        "schedule":        schedule,
        "goal_text":       row["goal_text"],
        "plan":            plan_data,
        "rating":          row.get("rating"),
    }


def save_plan(
    schedule: dict,
    goal_text: str,
    plan: dict,
    user_id: str = "local",
    week_start_date=None,
) -> int:
    """
    Upsert a generated plan keyed by (user_id, week_start_date).
    Regenerating for the same week overwrites rather than appending.
    week_start_date defaults to Monday of the current week; supply it
    explicitly when migrating historical plans.
    Returns the plan id.
    """
    if week_start_date is None:
        today = datetime.now(tz=timezone.utc).date()
        week_start_date = today - timedelta(days=today.weekday())

    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO plans
                    (user_id, created_at, week_start_date, schedule, goal_text, plan)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, week_start_date) DO UPDATE SET
                    created_at = EXCLUDED.created_at,
                    schedule   = EXCLUDED.schedule,
                    goal_text  = EXCLUDED.goal_text,
                    plan       = EXCLUDED.plan
                RETURNING id
                """,
                (
                    user_id,
                    datetime.now(tz=timezone.utc),
                    week_start_date,
                    json.dumps(schedule, default=str),
                    goal_text,
                    json.dumps(plan, default=str),
                ),
            )
            return cur.fetchone()[0]


def get_plans(user_id: str = "local", limit: int = 10) -> list[dict]:
    """Return the most recent N plans for a user, newest first."""
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, user_id, created_at, week_start_date,
                       schedule, goal_text, plan, rating
                FROM plans
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return [_row_to_plan_dict(dict(row)) for row in cur.fetchall()]


def get_plan(plan_id: int) -> dict | None:
    """Return a single plan by id, or None if not found."""
    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, user_id, created_at, week_start_date,
                       schedule, goal_text, plan, rating
                FROM plans WHERE id = %s
                """,
                (plan_id,),
            )
            row = cur.fetchone()
    return _row_to_plan_dict(dict(row)) if row else None


def rate_plan(plan_id: int, rating: int) -> bool:
    """Set the 1-5 rating on a plan. Returns True if the plan was found."""
    if rating not in range(1, 6):
        raise ValueError(f"rating must be 1-5, got {rating}")
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE plans SET rating = %s WHERE id = %s",
                (rating, plan_id),
            )
            return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Analytics — identical logic to db.py, operates on an activity list
# ---------------------------------------------------------------------------

def athlete_metrics(activities: list[dict]) -> dict:
    """
    Compute per-sport power/HR/pace statistics.
    Logic is identical to db.py — only the data source changes.
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
        "max_hr":         max(all_max_hr) if all_max_hr else None,
        "max_hr_by_sport": {
            sport: max(vals) for sport, vals in sport_max_hr.items() if vals
        },
        "avg_hr_by_sport": {
            sport: statistics.mean(vals) for sport, vals in sport_hr.items() if vals
        },
        "summary_text": "\n".join(lines) if lines else "  No detailed metrics available.",
    }


def calculate_hr_zones(max_hr_by_sport: dict) -> dict:
    """
    Compute 5-zone HR model per sport.
    Logic is identical to db.py.
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
