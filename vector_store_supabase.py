"""
vector_store_supabase.py — pgvector reimplementation of vector_store.py.

Stores activity embeddings in Postgres using the pgvector extension.
Cosine similarity search via the <=> (cosine distance) operator.

IMPORTANT: The pgvector extension must be enabled before setup_embeddings_table().
  Option A: Run in Supabase dashboard SQL editor:
              CREATE EXTENSION IF NOT EXISTS vector;
  Option B: setup_embeddings_table() attempts it automatically (requires superuser).

All queries are parameterized — no string interpolation of user input.
"""

import json
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SUPABASE_DB_URL = os.environ["SUPABASE_DB_URL"]
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

_openai = OpenAI()


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

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


@contextmanager
def _autocommit_conn():
    conn = psycopg2.connect(dsn=SUPABASE_DB_URL)
    conn.autocommit = True
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def setup_embeddings_table() -> None:
    """
    Enable pgvector and create the activity_embeddings table.

    The IVFFlat index is NOT created here — it requires data to exist first.
    Call create_ivfflat_index() after embed_activities() has run.
    """
    with _autocommit_conn() as conn:
        with conn.cursor() as cur:
            # This may fail if the pooler user lacks superuser rights.
            # If so, enable the extension through the Supabase dashboard instead.
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            except psycopg2.Error as e:
                print(f"Warning: could not create vector extension: {e}")
                print("Enable it via the Supabase dashboard → Database → Extensions → vector")

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS activity_embeddings (
                    id            BIGSERIAL PRIMARY KEY,
                    user_id       TEXT    NOT NULL,
                    strava_id     BIGINT  NOT NULL,
                    embedding     vector({EMBED_DIM}) NOT NULL,
                    activity_text TEXT    NOT NULL,
                    metadata      JSONB,
                    UNIQUE (user_id, strava_id)
                )
                """
            )
            cur.execute("""
                CREATE INDEX IF NOT EXISTS activity_embeddings_user_idx
                ON activity_embeddings (user_id)
            """)


def create_ivfflat_index(lists: int = 100) -> None:
    """
    Create an IVFFlat approximate-nearest-neighbour index for fast cosine search.
    Must be called AFTER data exists in activity_embeddings.
    lists = 100 is a sensible default for up to ~1 million rows.
    """
    with _autocommit_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS activity_embeddings_ivfflat_idx
                ON activity_embeddings
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = %s)
                """,
                (lists,),
            )
    print(f"IVFFlat index created (lists={lists}).")


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _activity_text(act: dict) -> str:
    """
    Build a rich natural-language description of an activity for embedding.
    Identical to vector_store.py so embeddings are comparable.
    """
    h, rem = divmod(act["duration_seconds"], 3600)
    m, s = divmod(rem, 60)
    duration = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
    parts = [f"{act['date']} {act['activity_type']}: {act['distance_km']:.2f} km in {duration}"]

    details = []
    if act.get("total_elevation_gain") is not None:
        details.append(f"{act['total_elevation_gain']:.0f}m elev")
    if act.get("average_watts") is not None:
        wp = f"avg {act['average_watts']:.0f}W"
        if act.get("weighted_average_watts") is not None:
            wp += f" NP {act['weighted_average_watts']}W"
        details.append(wp)
    if act.get("average_heartrate") is not None:
        hr = f"avg HR {act['average_heartrate']:.0f}"
        if act.get("max_heartrate") is not None:
            hr += f"/{act['max_heartrate']:.0f}"
        hr += " bpm"
        details.append(hr)
    if act.get("suffer_score") is not None:
        details.append(f"suffer {act['suffer_score']}")

    if details:
        parts.append(", ".join(details))

    text = ", ".join(parts)
    if act.get("name"):
        text += f" — {act['name']}"
    return text


def _vec_to_pg(embedding: list[float]) -> str:
    """
    Serialize a float list to pgvector's text format: '[0.12345678,...]'.
    psycopg2 passes this as a quoted string; the ::vector cast in the SQL
    tells Postgres to parse it as a vector.
    """
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed_activities(user_id: str = "local") -> int:
    """
    Embed all activities for a user using OpenAI text-embedding-3-small and
    upsert the vectors into activity_embeddings.

    Calls OpenAI in a single batch (safe for ≤2048 items).
    Returns the number of activities embedded.
    """
    from db_supabase import get_activities

    activities = get_activities(days=None, user_id=user_id)
    if not activities:
        print(f"No activities found for user_id='{user_id}'.")
        return 0

    texts = [_activity_text(a) for a in activities]

    print(f"Requesting embeddings for {len(texts)} activities...")
    response = _openai.embeddings.create(model=EMBED_MODEL, input=texts)
    vectors = [item.embedding for item in response.data]

    with _conn() as conn:
        with conn.cursor() as cur:
            for act, text, vec in zip(activities, texts, vectors):
                metadata = {
                    "strava_id":              act["strava_id"],
                    "date":                   str(act["date"]),
                    "activity_type":          act["activity_type"],
                    "distance_km":            act["distance_km"],
                    "duration_seconds":       act["duration_seconds"],
                    "name":                   act.get("name") or "",
                    "average_heartrate":      act.get("average_heartrate"),
                    "max_heartrate":          act.get("max_heartrate"),
                    "average_watts":          act.get("average_watts"),
                    "weighted_average_watts": act.get("weighted_average_watts"),
                    "total_elevation_gain":   act.get("total_elevation_gain"),
                    "average_speed":          act.get("average_speed"),
                    "suffer_score":           act.get("suffer_score"),
                    "workout_type":           act.get("workout_type"),
                }
                cur.execute(
                    """
                    INSERT INTO activity_embeddings
                        (user_id, strava_id, embedding, activity_text, metadata)
                    VALUES (%s, %s, %s::vector, %s, %s)
                    ON CONFLICT (user_id, strava_id) DO UPDATE SET
                        embedding     = EXCLUDED.embedding,
                        activity_text = EXCLUDED.activity_text,
                        metadata      = EXCLUDED.metadata
                    """,
                    (
                        user_id,
                        act["strava_id"],
                        _vec_to_pg(vec),
                        text,
                        json.dumps(metadata),
                    ),
                )

    print(f"Embedded {len(activities)} activities for user_id='{user_id}'.")
    return len(activities)


def search_activities(query: str, user_id: str = "local", n: int = 5) -> list[dict]:
    """
    Return the n activities most similar to `query` using cosine similarity.

    Uses pgvector's <=> (cosine distance) operator.
    score = 1 - cosine_distance, so higher is more similar.
    """
    response = _openai.embeddings.create(model=EMBED_MODEL, input=[query])
    q_vec = _vec_to_pg(response.data[0].embedding)

    with _conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    strava_id,
                    activity_text,
                    metadata,
                    1 - (embedding <=> %s::vector) AS score
                FROM activity_embeddings
                WHERE user_id = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (q_vec, user_id, q_vec, n),
            )
            rows = cur.fetchall()

    results = []
    for row in rows:
        meta = row["metadata"]
        if isinstance(meta, str):
            meta = json.loads(meta or "{}")
        results.append({
            **meta,
            "text":  row["activity_text"],
            "score": round(float(row["score"]), 4),
        })
    return results
