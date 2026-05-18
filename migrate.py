"""
migrate.py — One-time migration from SQLite training.db → Supabase Postgres.

Usage:
    uv run python migrate.py

What it does:
  1. Creates all tables in Supabase via setup_schema()
  2. Enables pgvector and creates activity_embeddings table
  3. Copies all activities from SQLite → Postgres (user_id='local')
  4. Copies the goals profile
  5. Copies all historical plans (preserving original week_start_date)
  6. Generates and stores pgvector embeddings for all activities
  7. Prints a migration summary

Safe to re-run — all inserts use ON CONFLICT DO UPDATE.
"""

import json
import sys
from datetime import datetime, timezone

from db import (
    get_activities as sqlite_get_activities,
    get_goals as sqlite_get_goals,
    get_plans as sqlite_get_plans,
)
from db_supabase import (
    _conn,
    get_activities as pg_get_activities,
    save_activities as pg_save_activities,
    save_goals as pg_save_goals,
    setup_schema,
)
from vector_store_supabase import (
    create_ivfflat_index,
    embed_activities,
    setup_embeddings_table,
)

USER_ID = "local"


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------

def step_schema() -> None:
    print("Step 1: Creating Supabase schema...")
    setup_schema()
    print("  ✓ Tables ready.\n")


def step_pgvector() -> bool:
    print("Step 2: Setting up pgvector...")
    try:
        setup_embeddings_table()
        print("  ✓ activity_embeddings table ready.\n")
        return True
    except Exception as exc:
        print(f"  ⚠ pgvector setup error: {exc}")
        print("  → Enable the 'vector' extension in Supabase dashboard:")
        print("    Database → Extensions → search 'vector' → Enable\n")
        return False


def step_activities() -> int:
    print("Step 3: Migrating activities...")
    acts = sqlite_get_activities(days=None)
    if not acts:
        print("  No activities in SQLite.\n")
        return 0
    count = pg_save_activities(acts, user_id=USER_ID)
    print(f"  ✓ {count} activities migrated.\n")
    return count


def step_goals() -> int:
    print("Step 4: Migrating goals profile...")
    goals = sqlite_get_goals(user_id=USER_ID)
    if not goals:
        print("  No goals profile in SQLite.\n")
        return 0
    pg_save_goals(goals, user_id=USER_ID)
    print("  ✓ Goals profile migrated.\n")
    return 1


def step_plans() -> int:
    print("Step 5: Migrating plans...")
    plans = sqlite_get_plans(user_id=USER_ID, limit=1000)
    if not plans:
        print("  No plans in SQLite.\n")
        return 0

    migrated = 0
    with _conn() as conn:
        with conn.cursor() as cur:
            for p in plans:
                # Preserve the original week_start_date rather than computing
                # today's Monday, which would collapse all plans to the same key.
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
                    """,
                    (
                        USER_ID,
                        p.get("created_at") or datetime.now(tz=timezone.utc).isoformat(),
                        p["week_start_date"],
                        json.dumps(p["schedule"], default=str),
                        p["goal_text"],
                        json.dumps(p["plan"], default=str),
                    ),
                )
                migrated += 1

    print(f"  ✓ {migrated} plan(s) migrated.\n")
    return migrated


def step_embeddings() -> int:
    print("Step 6: Building pgvector embeddings...")
    try:
        count = embed_activities(user_id=USER_ID)
        print(f"  ✓ {count} embeddings stored.")
    except Exception as exc:
        print(f"  ⚠ Embedding failed: {exc}\n")
        return 0

    if count > 0:
        print("  Creating IVFFlat index for fast similarity search...")
        try:
            create_ivfflat_index()
            print("  ✓ IVFFlat index created.")
        except Exception as exc:
            print(f"  ⚠ IVFFlat index skipped: {exc}")
            print("  → Search will use sequential scan (fine for <10k rows).")
            print("  → To create the index later, run in the Supabase SQL editor:")
            print("    CREATE INDEX activity_embeddings_ivfflat_idx")
            print("    ON activity_embeddings USING ivfflat (embedding vector_cosine_ops)")
            print("    WITH (lists = 100);")
    print()
    return count


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify() -> None:
    print("Verification:")
    pg_acts = pg_get_activities(days=None, user_id=USER_ID)
    sqlite_acts = sqlite_get_activities(days=None)
    print(f"  SQLite activities : {len(sqlite_acts)}")
    print(f"  Supabase activities: {len(pg_acts)}")
    if len(pg_acts) != len(sqlite_acts):
        print("  ⚠ Count mismatch — re-run migrate.py to retry failed rows.")
    else:
        print("  ✓ Activity counts match.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 50)
    print("Adaptive Training Coach — Supabase Migration")
    print("=" * 50 + "\n")

    step_schema()
    pgvector_ok = step_pgvector()
    n_acts      = step_activities()
    n_goals     = step_goals()
    n_plans     = step_plans()
    n_embedded  = step_embeddings() if pgvector_ok else 0

    print("=" * 50)
    print("Migration Summary")
    print("=" * 50)
    print(f"  Activities migrated : {n_acts}")
    print(f"  Goals profiles      : {n_goals}")
    print(f"  Plans migrated      : {n_plans}")
    print(f"  Embeddings stored   : {n_embedded}")
    print()

    verify()

    print()
    if not pgvector_ok:
        print("Next steps:")
        print("  1. Enable 'vector' extension in Supabase dashboard")
        print("  2. Re-run: uv run python migrate.py")
    else:
        print("Migration complete.")
        print("To switch the app to Supabase, replace imports of db / vector_store")
        print("with db_supabase / vector_store_supabase.")


if __name__ == "__main__":
    main()
