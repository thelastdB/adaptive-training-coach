import logging
import os
import re
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from stravalib import Client

from db_supabase import save_activities

logging.getLogger("stravalib").setLevel(logging.ERROR)


def fmt_duration(total_seconds):
    h, rem = divmod(int(total_seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

load_dotenv()

client_id = int(os.environ["STRAVA_CLIENT_ID"])
client_secret = os.environ["STRAVA_CLIENT_SECRET"]
refresh_token = os.environ["STRAVA_REFRESH_TOKEN"]

client = Client()
token_response = client.refresh_access_token(
    client_id=client_id,
    client_secret=client_secret,
    refresh_token=refresh_token,
)
client.access_token = token_response["access_token"]

# Persist rotated refresh token if Strava issued a new one
new_refresh = token_response.get("refresh_token", refresh_token)
if new_refresh != refresh_token:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    with open(env_path, "r") as f:
        contents = f.read()
    contents = re.sub(r"STRAVA_REFRESH_TOKEN=.*", f"STRAVA_REFRESH_TOKEN={new_refresh}", contents)
    with open(env_path, "w") as f:
        f.write(contents)

since = datetime.now(tz=timezone.utc) - timedelta(days=90)
activities = client.get_activities(after=since)

print(f"{'Date':<12} {'Type':<20} {'Distance':>10} {'Duration':>10}")
print("-" * 56)

def _float(val) -> float | None:
    return float(val) if val is not None else None


rows = []
for act in activities:
    date = act.start_date_local.date()
    sport = (act.sport_type or act.type).root
    distance_km = float(act.distance) / 1000
    duration_seconds = int(act.moving_time)
    rows.append({
        "strava_id": act.id,
        "date": date,
        "activity_type": sport,
        "distance_km": distance_km,
        "duration_seconds": duration_seconds,
        "name": act.name or "",
        "average_heartrate": _float(act.average_heartrate),
        "max_heartrate": _float(act.max_heartrate),
        "average_watts": _float(act.average_watts),
        "weighted_average_watts": act.weighted_average_watts,
        "total_elevation_gain": _float(act.total_elevation_gain),
        "average_speed": round(_float(act.average_speed) * 3.6, 2) if act.average_speed is not None else None,
        "suffer_score": act.suffer_score,
        "workout_type": act.workout_type,
    })
    print(f"{str(date):<12} {sport:<20} {distance_km:>9.2f} km {fmt_duration(duration_seconds):>10}")

saved = save_activities(rows)
print(f"\n{saved} activities saved to training.db")
