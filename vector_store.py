import json
import os

import faiss
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

from db import get_activities

load_dotenv()

STORE_DIR = "./faiss_store"
INDEX_FILE = os.path.join(STORE_DIR, "index.faiss")
META_FILE = os.path.join(STORE_DIR, "meta.json")
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536

_openai = OpenAI()


def _activity_text(act: dict) -> str:
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


def embed_activities() -> int:
    """Embed all activities from the DB and write the FAISS index to disk."""
    activities = get_activities(days=None)
    if not activities:
        print("No activities in database.")
        return 0

    texts = [_activity_text(a) for a in activities]
    response = _openai.embeddings.create(model=EMBED_MODEL, input=texts)
    vectors = np.array([item.embedding for item in response.data], dtype=np.float32)

    # Normalize so IndexFlatIP gives cosine similarity scores in [−1, 1]
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(vectors)

    os.makedirs(STORE_DIR, exist_ok=True)
    faiss.write_index(index, INDEX_FILE)

    meta = [
        {
            "strava_id": a["strava_id"],
            "date": str(a["date"]),
            "activity_type": a["activity_type"],
            "distance_km": a["distance_km"],
            "duration_seconds": a["duration_seconds"],
            "name": a["name"],
            "average_heartrate": a.get("average_heartrate"),
            "max_heartrate": a.get("max_heartrate"),
            "average_watts": a.get("average_watts"),
            "weighted_average_watts": a.get("weighted_average_watts"),
            "total_elevation_gain": a.get("total_elevation_gain"),
            "average_speed": a.get("average_speed"),
            "suffer_score": a.get("suffer_score"),
            "workout_type": a.get("workout_type"),
            "text": t,
        }
        for a, t in zip(activities, texts)
    ]
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"Embedded {len(activities)} activities → {STORE_DIR}")
    return len(activities)


def search_activities(query: str, n: int = 5) -> list[dict]:
    """Return the n most similar activities to a natural language query."""
    if not os.path.exists(INDEX_FILE):
        raise RuntimeError("No index found — run embed_activities() first.")

    response = _openai.embeddings.create(model=EMBED_MODEL, input=[query])
    q_vec = np.array([response.data[0].embedding], dtype=np.float32)
    faiss.normalize_L2(q_vec)

    index = faiss.read_index(INDEX_FILE)
    with open(META_FILE) as f:
        meta = json.load(f)

    scores, indices = index.search(q_vec, n)

    return [
        {**meta[idx], "score": round(float(scores[0][rank]), 4)}
        for rank, idx in enumerate(indices[0])
        if idx >= 0
    ]


if __name__ == "__main__":
    embed_activities()

    print("\nSample search: 'long hard ride'")
    for r in search_activities("long hard ride"):
        print(f"  [{r['score']:.3f}] {r['text']}")
