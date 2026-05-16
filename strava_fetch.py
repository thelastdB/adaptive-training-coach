import logging
import os
import re
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from stravalib import Client

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

for act in activities:
    date = act.start_date_local.strftime("%Y-%m-%d")
    sport = (act.sport_type or act.type).root
    distance = f"{float(act.distance) / 1000:.2f} km"
    duration = fmt_duration(act.moving_time)
    print(f"{date:<12} {sport:<20} {distance:>10} {duration:>10}")
