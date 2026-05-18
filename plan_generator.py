import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import anthropic
import requests
from dotenv import load_dotenv

from db import get_activities
from vector_store import search_activities

load_dotenv()

MODEL = "claude-sonnet-4-6"
DEFAULT_LOCATION = (47.2529, -122.4443)  # Tacoma, WA

# time_of_day is preserved through every layer so weather rules can compare it
# against sunrise/sunset per session. A future step will also use it to fetch
# hourly forecasts for the specific window rather than daily aggregates.

SYSTEM_PROMPT = """\
You are an expert endurance sports coach specializing in cycling, running, and \
cross-training periodization. Generate personalized weekly training plans.

The schedule you receive has already been processed by a rule engine. Each day \
carries an indoor flag, a suggested activity type, an intensity cap, and flags \
explaining every decision. Your job is to write the workout, not re-evaluate the \
conditions. Honor every pre-resolved decision; override only when there is a clear \
athletic reason and explain it in the description.

Always respond with valid JSON only — no markdown fences, no prose.\
"""

DAILY_FIELDS = [
    "temperature_2m_max", "temperature_2m_min",
    "precipitation_sum", "precipitation_probability_max",
    "weathercode", "windspeed_10m_max", "winddirection_10m_dominant",
    "sunrise", "sunset", "uv_index_max",
]

WMO_CODES: dict[int, str] = {
    0: "clear",
    1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "icy fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light showers", 81: "showers", 82: "heavy showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm with hail",
}

WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

# Approximate session start hour for each time-of-day bucket.
# Used for sunrise/sunset boundary checks (Rule 4).
TIME_OF_DAY_HOUR = {"morning": 6, "afternoon": 12, "evening": 19}


# ---------------------------------------------------------------------------
# Weather: fetch + summarise
# ---------------------------------------------------------------------------

def get_weekly_forecast(lat: float, lon: float) -> dict[str, dict]:
    """
    Fetch a 7-day daily forecast from Open-Meteo (free, no API key).
    relativehumidity_2m_max is not a valid daily variable, so hourly humidity
    is fetched in the same request and collapsed to a per-day maximum.
    Returns a dict keyed by ISO date string.
    """
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join(DAILY_FIELDS),
            "hourly": "relativehumidity_2m",
            "timezone": "auto",
            "forecast_days": 7,
        },
        timeout=10,
    )
    resp.raise_for_status()
    payload = resp.json()
    daily, hourly = payload["daily"], payload["hourly"]

    daily_humidity_max: dict[str, int] = {}
    for i, ts in enumerate(hourly["time"]):
        h = hourly["relativehumidity_2m"][i]
        if h is not None:
            day_str = ts[:10]
            daily_humidity_max[day_str] = max(daily_humidity_max.get(day_str, 0), h)

    forecast: dict[str, dict] = {}
    for i, day_str in enumerate(daily["time"]):
        entry = {f: daily[f][i] for f in DAILY_FIELDS if f in daily}
        entry["relativehumidity_2m_max"] = daily_humidity_max.get(day_str)
        forecast[day_str] = entry
    return forecast


def _iso_to_decimal_hour(iso: str) -> float:
    t = datetime.fromisoformat(iso)
    return t.hour + t.minute / 60


def _fmt_time(iso: str) -> str:
    """'2026-05-18T05:29' → '5:29am'."""
    t = datetime.fromisoformat(iso)
    h = t.hour % 12 or 12
    return f"{h}:{t.minute:02d}{'am' if t.hour < 12 else 'pm'}"


def weather_summary(raw: dict) -> dict:
    """Convert a raw Open-Meteo day dict to a structured plain-English summary."""
    code = int(raw.get("weathercode") or 0)
    wind_kmh = raw.get("windspeed_10m_max") or 0.0
    humidity = raw.get("relativehumidity_2m_max")
    precip = raw.get("precipitation_probability_max") or 0
    sunrise_raw = raw.get("sunrise")
    sunset_raw = raw.get("sunset")
    return {
        "conditions": WMO_CODES.get(code, f"code {code}"),
        "temp_max": f"{raw.get('temperature_2m_max', 0):.0f}°C",
        "temp_min": f"{raw.get('temperature_2m_min', 0):.0f}°C",
        "wind_mph": round(wind_kmh * 0.621371),
        "humidity": f"{humidity}%" if humidity is not None else None,
        "precipitation_chance": f"{precip:.0f}%",
        "sunrise": _fmt_time(sunrise_raw) if sunrise_raw else None,
        "sunset": _fmt_time(sunset_raw) if sunset_raw else None,
        "uv_index": round(raw.get("uv_index_max") or 0, 1),
    }


# ---------------------------------------------------------------------------
# Deterministic rule engine
# ---------------------------------------------------------------------------

def resolve_training_conditions(
    schedule: dict,
    forecast: dict[str, dict],
    recent_activities: list[dict],
) -> dict:
    """
    Apply deterministic rules in order and return an enriched schedule.

    Each day gains:
      indoor (bool)              – whether to train indoors
      suggested_activity_type    – concrete sport override, or None
      intensity_cap              – "easy" | "moderate" | "hard" (hard = uncapped)
      flags                      – ordered list of human-readable decision strings
      weather                    – weather_summary dict for the day
      date                       – ISO date string

    Rules are applied in declaration order; later rules can tighten earlier decisions.
    """
    ordered_names = sorted(schedule.keys(), key=lambda d: WEEKDAY_MAP[d.lower()])

    enriched: dict[str, dict] = {}
    for day_name in ordered_names:
        info = schedule[day_name]
        target_date = _next_date_for_day(day_name)
        date_str = target_date.isoformat()
        raw_fc = forecast.get(date_str, {})
        summary = weather_summary(raw_fc) if raw_fc else {}

        enriched[day_name] = {
            **info,
            "date": date_str,
            "indoor": False,
            "suggested_activity_type": None,
            "intensity_cap": "hard",
            "flags": [],
            "weather": summary,
        }

    # -- Rules 1-5: Weather (applied per day independently) ------------------
    for day_name, entry in enriched.items():
        summary = entry["weather"]
        if not summary:
            entry["flags"].append("No forecast data available for this day")
            continue

        raw_fc = forecast.get(entry["date"], {})
        time_of_day = entry["time_of_day"]

        precip_pct = int(summary["precipitation_chance"].rstrip("%"))
        wind_mph = summary["wind_mph"]
        humidity_str = summary.get("humidity")
        humidity = int(humidity_str.rstrip("%")) if humidity_str else None
        temp_max = float(summary["temp_max"].rstrip("°C"))
        temp_min = float(summary["temp_min"].rstrip("°C"))

        # Rule 1: precipitation
        if precip_pct > 60:
            entry["indoor"] = True
            entry["flags"].append(
                f"Precipitation chance {precip_pct}% > 60% threshold — moved indoors"
            )

        # Rule 2: wind
        if wind_mph > 25:
            entry["indoor"] = True
            entry["flags"].append(
                f"Wind {wind_mph}mph > 25mph threshold — moved indoors"
            )

        # Rule 3: humidity — flags conflict, does not force indoor
        if humidity is not None and humidity > 85:
            if time_of_day == "morning":
                suggestion = "consider starting earlier or shifting to afternoon"
            elif time_of_day == "afternoon":
                suggestion = "consider shifting to morning or evening"
            else:
                suggestion = "consider shifting to morning"
            entry["flags"].append(
                f"Humidity {humidity}% > 85% threshold — {suggestion}"
            )

        # Rule 4: session time outside sunrise/sunset window
        sunrise_raw = raw_fc.get("sunrise")
        sunset_raw = raw_fc.get("sunset")
        if sunrise_raw and sunset_raw:
            sunrise_hr = _iso_to_decimal_hour(sunrise_raw)
            sunset_hr = _iso_to_decimal_hour(sunset_raw)
            session_hr = TIME_OF_DAY_HOUR.get(time_of_day, 12)
            if session_hr < sunrise_hr:
                entry["indoor"] = True
                entry["flags"].append(
                    f"{time_of_day.capitalize()} session (~{session_hr}:00) starts before "
                    f"sunrise ({summary['sunrise']}) — moved indoors"
                )
            elif session_hr > sunset_hr:
                entry["indoor"] = True
                entry["flags"].append(
                    f"{time_of_day.capitalize()} session (~{session_hr}:00) falls after "
                    f"sunset ({summary['sunset']}) — moved indoors"
                )

        # Rule 5: extreme temperature
        if temp_min < 2:
            entry["indoor"] = True
            entry["flags"].append(
                f"Min temperature {temp_min:.0f}°C < 2°C — moved indoors"
            )
        if temp_max > 35:
            entry["indoor"] = True
            entry["flags"].append(
                f"Max temperature {temp_max:.0f}°C > 35°C — moved indoors"
            )

    # -- Rule 6: Time budget (applied per day) --------------------------------
    for entry in enriched.values():
        if entry["minutes"] <= 60 and entry["suggested_activity_type"] is None:
            pick = "VirtualRide" if entry["indoor"] else "Run"
            entry["suggested_activity_type"] = pick
            entry["flags"].append(
                f"≤60 min available — suggested {pick} for time efficiency"
            )

    # -- Rules 7-8: Consecutive-day structure (across the week) ---------------
    ordered = [(n, enriched[n]) for n in ordered_names]

    for i in range(1, len(ordered)):
        prev_name, _ = ordered[i - 1]
        curr_name, curr_entry = ordered[i]
        gap = WEEKDAY_MAP[curr_name.lower()] - WEEKDAY_MAP[prev_name.lower()]
        if gap == 1:
            # Rule 7: back-to-back days → cap second at easy
            if curr_entry["intensity_cap"] == "hard":
                curr_entry["intensity_cap"] = "easy"
                curr_entry["flags"].append(
                    f"Back-to-back session after {prev_name.capitalize()} "
                    "— intensity capped at easy"
                )

    for i in range(2, len(ordered)):
        a, b, c = WEEKDAY_MAP[ordered[i-2][0].lower()], \
                   WEEKDAY_MAP[ordered[i-1][0].lower()], \
                   WEEKDAY_MAP[ordered[i][0].lower()]
        if b - a == 1 and c - b == 1:
            # Rule 8: three consecutive training days
            ordered[i][1]["flags"].append(
                "3 consecutive training days — recovery or rest strongly recommended "
                "after this session"
            )

    # -- Rules 9-10: Training load from recent history -----------------------
    if recent_activities:
        most_recent_date = max(a["date"] for a in recent_activities)

        # Rule 9: first scheduled session after a 3+ day gap
        first_name, first_entry = ordered[0]
        gap_days = (_next_date_for_day(first_name) - most_recent_date).days
        if gap_days >= 3:
            first_entry["intensity_cap"] = "easy"
            first_entry["flags"].append(
                f"First session after a {gap_days}-day training gap "
                "— intensity capped at easy"
            )

        # Rule 10: day after a long ride (>60 km) or hard run (suffer_score > 80)
        hard_dates: set[date] = set()
        for act in recent_activities:
            long_ride = act["activity_type"] in ("Ride", "VirtualRide") and act["distance_km"] > 60
            hard_run = act["activity_type"] == "Run" and (act.get("suffer_score") or 0) > 80
            if long_ride or hard_run:
                hard_dates.add(act["date"])

        for day_name, entry in enriched.items():
            prev_date = _next_date_for_day(day_name) - timedelta(days=1)
            if prev_date in hard_dates:
                entry["suggested_activity_type"] = "Yoga"
                entry["flags"].append(
                    f"Day after a hard session on {prev_date.isoformat()} "
                    "— suggested Yoga for active recovery"
                )

    return enriched


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def _training_load_summary(activities: list[dict]) -> str:
    """Summarise last 28 days of the provided activity list, grouped by ISO week and sport."""
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=28)).date()
    recent = [a for a in activities if a["date"] >= cutoff]
    if not recent:
        return "No activity data in the last 28 days."

    today = datetime.now(tz=timezone.utc).date()
    weekly: dict[tuple, dict[str, dict]] = defaultdict(
        lambda: defaultdict(lambda: {"sessions": 0, "km": 0.0, "min": 0})
    )
    for act in recent:
        key = act["date"].isocalendar()[:2]
        b = weekly[key][act["activity_type"]]
        b["sessions"] += 1
        b["km"] += act["distance_km"]
        b["min"] += act["duration_seconds"] // 60

    lines = []
    for key in sorted(weekly.keys(), reverse=True):
        yr, wk = key
        days_since = (today - datetime.strptime(f"{yr}-W{wk:02d}-1", "%G-W%V-%u").date()).days
        lines.append(f"Week ~{days_since}d ago (W{wk:02d}):")
        for sport, s in sorted(weekly[key].items()):
            lines.append(f"  {sport}: {s['sessions']}x, {s['km']:.1f} km, {s['min']} min")
    return "\n".join(lines)


def _format_examples(examples: list[dict]) -> str:
    return "\n".join(f"  - {e['text']}" for e in examples)


def _next_date_for_day(day_name: str) -> date:
    today = datetime.now(tz=timezone.utc).date()
    return today + timedelta(days=(WEEKDAY_MAP[day_name.lower()] - today.weekday()) % 7)


def _format_resolved_schedule(resolved: dict) -> str:
    """
    Render the enriched schedule for the prompt.
    The model receives decisions, not raw numbers to reason about.
    """
    lines = [
        "RESOLVED TRAINING SCHEDULE",
        "(All rules have fired. Honor indoor, suggested_activity, and intensity_cap.",
        " Override only with explicit athletic justification in the description.)",
    ]
    for day_name in sorted(resolved.keys(), key=lambda d: WEEKDAY_MAP[d.lower()]):
        e = resolved[day_name]
        w = e["weather"]
        activity_str = e["suggested_activity_type"] or "coach's choice"
        lines.append(
            f"\n{day_name.capitalize()} — {e['date']} ({e['time_of_day']}):"
            f"\n  Available: {e['minutes']} min"
            f"\n  Indoor: {'Yes' if e['indoor'] else 'No'}"
            f"  |  Activity: {activity_str}"
            f"  |  Intensity cap: {e['intensity_cap']}"
        )
        if e["flags"]:
            lines.append("  Decisions:")
            for flag in e["flags"]:
                lines.append(f"    · {flag}")
        else:
            lines.append("  Decisions: none — all conditions nominal")
        if w:
            lines.append(
                f"  Weather: {w.get('conditions','?')}, "
                f"{w.get('temp_max','?')}/{w.get('temp_min','?')}, "
                f"wind {w.get('wind_mph','?')}mph, "
                f"precip {w.get('precipitation_chance','?')}, "
                f"humidity {w.get('humidity','n/a')}, "
                f"UV {w.get('uv_index','?')}, "
                f"sunrise {w.get('sunrise','?')} → sunset {w.get('sunset','?')}"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core plan generator
# ---------------------------------------------------------------------------

def generate_plan(
    schedule: dict,
    goal: str,
    location: tuple[float, float] = DEFAULT_LOCATION,
    recent_activities: list[dict] | None = None,
) -> dict:
    """
    Generate a structured weekly training plan.

    Args:
        schedule:           {"day": {"minutes": int, "time_of_day": str}, ...}
        goal:               Natural language goal string
        location:           (lat, lon) — defaults to Tacoma, WA
        recent_activities:  Pre-fetched activity list; fetched if not provided
    """
    if recent_activities is None:
        recent_activities = get_activities(days=90)

    training_load = _training_load_summary(recent_activities)
    examples = search_activities(goal, n=5)
    forecast = get_weekly_forecast(*location)
    resolved = resolve_training_conditions(schedule, forecast, recent_activities)

    user_message = f"""\
GOAL: {goal}

RECENT TRAINING LOAD (last 4 weeks):
{training_load}

SIMILAR PAST WORKOUTS (for pacing and intensity reference):
{_format_examples(examples)}

{_format_resolved_schedule(resolved)}

Return a JSON object:
{{
  "week_goal": "<one sentence>",
  "days": [
    {{
      "day": "<name>",
      "activity_type": "<Ride | Run | VirtualRide | Walk | Yoga | Rest | etc.>",
      "duration_minutes": <int>,
      "distance_km": <float or null>,
      "intensity": "<easy | moderate | hard | race>",
      "time_of_day": "<morning | afternoon | evening>",
      "description": "<1-3 sentences with specific workout instructions>",
      "indoor": <true | false>,
      "flags": [<echo the flags list from the resolved schedule>],
      "weather": {{
        "conditions": "<str>", "temp_max": "<N°C>", "temp_min": "<N°C>",
        "wind_mph": <int>, "humidity": "<N%> or null",
        "precipitation_chance": "<N%>", "sunrise": "<str>", "sunset": "<str>",
        "uv_index": <number>
      }}
    }}
  ]
}}\
"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )
    return json.loads(response.content[0].text.strip())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    schedule = {
        "monday": {"minutes": 60, "time_of_day": "morning"},
        "wednesday": {"minutes": 45, "time_of_day": "evening"},
        "saturday": {"minutes": 120, "time_of_day": "morning"},
    }
    goal = "maintain fitness with a focus on cycling"

    recent_activities = get_activities(days=90)

    print(f"Goal     : {goal}")
    print(f"Location : Tacoma, WA {DEFAULT_LOCATION}")
    print(f"Days     : {', '.join(schedule.keys())}")
    print(f"History  : {len(recent_activities)} activities loaded\n")

    # Show what the rule engine decided before calling the model
    forecast = get_weekly_forecast(*DEFAULT_LOCATION)
    resolved = resolve_training_conditions(schedule, forecast, recent_activities)
    print("Rule engine output:")
    for day_name in sorted(resolved.keys(), key=lambda d: WEEKDAY_MAP[d.lower()]):
        e = resolved[day_name]
        print(
            f"  {day_name.capitalize()}: indoor={e['indoor']}"
            f"  activity={e['suggested_activity_type'] or '(open)'}"
            f"  cap={e['intensity_cap']}"
        )
        for flag in e["flags"]:
            print(f"    · {flag}")
    print()

    print("Generating plan...\n")
    plan = generate_plan(schedule, goal, recent_activities=recent_activities)

    print(f"Week goal: {plan['week_goal']}\n")
    for day in plan["days"]:
        w = day.get("weather", {})
        dist = f"~{day['distance_km']} km" if day.get("distance_km") else "no distance"
        print(
            f"{day['day'].capitalize()} [{day['time_of_day']}]  "
            f"{'[INDOOR] ' if day.get('indoor') else ''}"
            f"{day['activity_type']}  {day['duration_minutes']} min  "
            f"{dist}  ({day['intensity']})"
        )
        print(
            f"  Weather: {w.get('conditions','?')}, {w.get('temp_max','?')}/{w.get('temp_min','?')}, "
            f"wind {w.get('wind_mph','?')}mph, precip {w.get('precipitation_chance','?')}"
        )
        for flag in day.get("flags", []):
            print(f"  · {flag}")
        print(f"  {day['description']}")
        print()

    print("Full JSON:")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
