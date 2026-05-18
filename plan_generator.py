import json
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import anthropic
import requests
from dotenv import load_dotenv

from db_supabase import athlete_metrics, calculate_hr_zones, get_activities, get_goals, save_plan
from vector_store_supabase import search_activities

load_dotenv()

MODEL = "claude-sonnet-4-6"


def parse_json_response(text: str) -> dict:
    """
    Robustly parse JSON from an LLM response.

    Attempts in order:
      1. Plain json.loads on the stripped text.
      2. Strip markdown code fences (```json ... ``` or ``` ... ```).
      3. Regex-extract the first {...} block and parse that.

    Raises ValueError with a preview of the raw text if all attempts fail.
    """
    text = text.strip()

    # Attempt 1 — clean response
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Attempt 2 — strip markdown code fences
    fenced = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    fenced = re.sub(r'\s*```$', '', fenced)
    try:
        return json.loads(fenced.strip())
    except json.JSONDecodeError:
        pass

    # Attempt 3 — extract first {...} block
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse JSON from model response. "
        f"First 200 chars: {text[:200]!r}"
    )
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

TIME-OF-DAY RULE:
The time_of_day field represents the athlete's stated availability window — preserve \
it by default. Only change it when a rule engine flag has definitively re-routed the \
session (e.g. "session falls outside sunrise/sunset — moved indoors"). Humidity and \
heat advisories ("consider shifting to morning", "consider starting earlier") are \
informational: acknowledge the concern in the description, recommend an early start \
within the window, but do NOT change the time_of_day field.

INTENSITY PROGRESSION — MANDATORY:
Even in weeks where every session is short (≤60 min), intensity must still vary \
across the week. At least one session must be easy or moderate — short duration \
does not justify assigning hard intensity to every day. A week of all-hard sessions \
provides no recovery stimulus and violates basic periodization. Distribute intensity \
as you would for any other week: one quality session, one moderate session, \
one recovery session.

RULE OVERRIDE TRANSPARENCY — MANDATORY:
When a day's flags list contains two rules that pull in different directions — for \
example, one flag suggesting Run (Rule 6: ≤60 min) and another suggesting Yoga \
(Rule 10: day after hard effort) — the winning rule takes priority and the \
description field MUST explicitly name the conflict and explain the resolution. \
State which rule was overridden, which rule won, and why. Use plain language \
directly in the description. Example: "Yoga is prescribed here instead of the \
default short-session Run because yesterday's 69 km ride triggered the active \
recovery rule (Rule 10 override of Rule 6)." \
Silently ignoring a lower-priority flag without acknowledging it in the description \
is a compliance violation. Every flag that was not acted on must be accounted for.

HR TARGETS:
Always prescribe heart rate targets using zones (e.g. "Zone 2 effort", "upper Zone 3 \
to low Zone 4") rather than absolute bpm values. Reference the athlete's zone \
definitions provided in the constraints section. Never write absolute bpm numbers \
as the primary target — zones only.

DESCRIPTION LENGTH — MANDATORY:
Each day's description must be 2-4 sentences maximum. Be specific and actionable \
but concise — no preamble, no restating rule engine decisions, no explaining why \
rules fired. Just tell the athlete what to do.\

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


def _c_to_display(temp_c_str: str, units: str) -> str:
    """Convert a '19°C' string to °F if units='imperial', else return unchanged."""
    if units == "metric" or not temp_c_str or "°" not in str(temp_c_str):
        return temp_c_str
    try:
        c = float(str(temp_c_str).replace("°C", "").strip())
        return f"{c * 9 / 5 + 32:.0f}°F"
    except (ValueError, AttributeError):
        return temp_c_str


def _format_resolved_schedule(resolved: dict, units: str = "metric") -> str:
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
            t_max = _c_to_display(w.get("temp_max", "?"), units)
            t_min = _c_to_display(w.get("temp_min", "?"), units)
            lines.append(
                f"  Weather: {w.get('conditions','?')}, "
                f"{t_max}/{t_min}, "
                f"wind {w.get('wind_mph','?')}mph, "
                f"precip {w.get('precipitation_chance','?')}, "
                f"humidity {w.get('humidity','n/a')}, "
                f"UV {w.get('uv_index','?')}, "
                f"sunrise {w.get('sunrise','?')} → sunset {w.get('sunset','?')}"
            )
    return "\n".join(lines)


_JSON_CLOSING = "\nAlways respond with valid JSON only — no markdown fences, no prose."


def _build_system_prompt(athlete_m: dict, goals: dict | None = None) -> str:
    """
    Return SYSTEM_PROMPT with athlete profile (goals) and HR ceilings injected
    before the closing JSON instruction.
    """
    extra = ""

    # -- Athlete profile from persisted goals ---------------------------------
    if goals:
        profile_parts: list[str] = []

        if goals.get("objective"):
            profile_parts.append(f"Objective: {goals['objective']}")

        prefs = goals.get("sport_preferences") or {}
        pref_items = []
        if prefs.get("primary_sport"):
            pref_items.append(f"primary sport is {prefs['primary_sport']}")
        if prefs.get("secondary_sport"):
            pref_items.append(f"secondary is {prefs['secondary_sport']}")
        if pref_items:
            profile_parts.append("Sport preferences: " + ", ".join(pref_items) + ".")

        if goals.get("physical_notes"):
            profile_parts.append(
                "PHYSICAL CONSTRAINTS (hard limits — never violate): "
                + goals["physical_notes"]
            )

        future_events: list[str] = []
        for ev in goals.get("upcoming_events") or []:
            try:
                ev_date = date.fromisoformat(str(ev["date"]))
                days = (ev_date - date.today()).days
                if days < 0:
                    continue
                if days <= 14:
                    guidance = "final prep — taper and sharpen this week"
                elif days <= 28:
                    guidance = "peak build — race-specificity is a priority"
                elif days <= 56:
                    guidance = "build phase — support this event with progressive overload"
                else:
                    guidance = "long horizon — maintain general fitness"
                line = f"  · {ev.get('name', 'Event')}"
                if ev.get("sport"):
                    line += f" ({ev['sport']})"
                line += f" — {days} days away. {guidance}."
                if ev.get("notes"):
                    line += f" Notes: {ev['notes']}"
                future_events.append(line)
            except (ValueError, KeyError, TypeError):
                pass

        if future_events:
            profile_parts.append("Upcoming events:\n" + "\n".join(future_events))

        if profile_parts:
            extra += "\n\nATHLETE PROFILE:\n" + "\n".join(profile_parts)

    # -- Per-sport HR zones ---------------------------------------------------
    max_hr_by_sport = athlete_m.get("max_hr_by_sport", {})
    if max_hr_by_sport:
        zones = calculate_hr_zones(max_hr_by_sport)
        if zones:
            # Prioritise primary sports; sort the rest alphabetically
            priority = ["Run", "Ride", "VirtualRide"]
            ordered = [s for s in priority if s in zones] + \
                      [s for s in sorted(zones) if s not in priority]
            zone_lines = []
            for sport in ordered:
                z = zones[sport]
                zone_lines.append(
                    f"  {sport}: "
                    f"Z1 <{z['z1_ceiling']}bpm, "
                    f"Z2 {z['z1_ceiling']}–{z['z2_ceiling']}bpm, "
                    f"Z3 {z['z2_ceiling']}–{z['z3_ceiling']}bpm, "
                    f"Z4 {z['z3_ceiling']}–{z['z4_ceiling']}bpm, "
                    f"Z5 >{z['z4_ceiling']}bpm (max {z['max']}bpm)"
                )
            extra += (
                "\n\nATHLETE HR ZONES:\n"
                "Use these zone definitions. Prescribe 'Zone 2', 'Zone 3-4', etc. — "
                "never absolute bpm as the primary target. "
                "Zone 5 is race-intensity only; do not assign it in general training plans.\n"
                + "\n".join(zone_lines)
            )

    if not extra:
        return SYSTEM_PROMPT
    return SYSTEM_PROMPT.replace(_JSON_CLOSING, extra + _JSON_CLOSING)


# ---------------------------------------------------------------------------
# Layer 1 — Deterministic validator
# ---------------------------------------------------------------------------

_CYCLING_TYPES = {"Ride", "VirtualRide"}

_REPAIR_SYSTEM_PROMPT = (
    "You are a training plan repair system. Fix exactly the violations listed. "
    "Reproduce all unaffected fields verbatim. "
    "Return valid JSON for a single day object — no markdown, no prose."
)


def _extract_watt_values(text: str) -> list[float]:
    """Extract all wattage figures from text, including both ends of ranges."""
    values: list[float] = []
    for m in re.finditer(
        r'(\d+(?:\.\d+)?)(?:\s*[-–]\s*(\d+(?:\.\d+)?))?\s*[Ww](?:atts?)?\b', text
    ):
        values.append(float(m.group(1)))
        if m.group(2):
            values.append(float(m.group(2)))
    return values


def _extract_hr_values(text: str) -> list[int]:
    """Extract all heart-rate figures from text, including both ends of ranges."""
    values: list[int] = []
    for m in re.finditer(r'(\d+)(?:\s*[-–]\s*(\d+))?\s*bpm\b', text, re.IGNORECASE):
        values.append(int(m.group(1)))
        if m.group(2):
            values.append(int(m.group(2)))
    for m in re.finditer(r'(?:HR|heart rate)\s*:?\s*(\d+)', text, re.IGNORECASE):
        values.append(int(m.group(1)))
    return values


def validate_day(
    day_plan: dict,
    available_minutes: int,
    athlete_m: dict,
) -> list[dict]:
    """
    Check a single day plan for rule violations.

    Returns a list of dicts, each with:
      type        – machine-readable violation name
      description – human-readable explanation
      severity    – "critical" | "warning"
    """
    violations: list[dict] = []
    description = day_plan.get("description", "")
    activity_type = day_plan.get("activity_type", "")
    is_cycling = activity_type in _CYCLING_TYPES

    watt_values = _extract_watt_values(description)
    hr_values = _extract_hr_values(description)

    max_watts = athlete_m.get("max_watts")
    # Sport-specific HR ceiling; fall back to the global max if the sport has no data
    sport_max_hr = (
        athlete_m.get("max_hr_by_sport", {}).get(activity_type)
        or athlete_m.get("max_hr")
    )

    # Check 1: wattage in description for a non-cycling activity
    if watt_values and not is_cycling:
        violations.append({
            "type": "invalid_wattage",
            "description": (
                f"Wattage ({', '.join(f'{w:.0f}W' for w in watt_values)}) "
                f"prescribed for {activity_type} — watts only apply to cycling"
            ),
            "severity": "critical",
        })

    # Check 2: wattage exceeds athlete max by >20%
    if is_cycling and watt_values and max_watts:
        threshold = max_watts * 1.20
        bad = [w for w in watt_values if w > threshold]
        if bad:
            violations.append({
                "type": "wattage_too_high",
                "description": (
                    f"Prescribed {', '.join(f'{w:.0f}W' for w in bad)} "
                    f"exceeds athlete max {max_watts:.0f}W by >20% "
                    f"(threshold {threshold:.0f}W)"
                ),
                "severity": "critical",
            })

    # Check 3: absolute HR above Zone 4 ceiling without accompanying zone references.
    # If the description uses zone language (e.g. "Zone 3"), bpm values are
    # treated as supplementary context rather than primary targets — skip the check.
    if hr_values and sport_max_hr:
        z4_ceiling = int(sport_max_hr * 0.90)
        has_zone_refs = bool(re.search(r'\bZone\s*[1-5]\b', description, re.IGNORECASE))
        if not has_zone_refs:
            bad_hr = [h for h in hr_values if h > z4_ceiling]
            if bad_hr:
                violations.append({
                    "type": "hr_above_zone4",
                    "description": (
                        f"Absolute HR {', '.join(str(h) for h in bad_hr)}bpm "
                        f"prescribed without zone references — exceeds Zone 4 ceiling "
                        f"({z4_ceiling}bpm, 90% of {sport_max_hr:.0f}bpm max for {activity_type}). "
                        "Use zone references (e.g. 'Zone 3-4') instead of absolute bpm targets."
                    ),
                    "severity": "critical",
                })

    # Check 4: duration exceeds available window
    duration = day_plan.get("duration_minutes", 0)
    if duration > available_minutes:
        violations.append({
            "type": "duration_exceeded",
            "description": (
                f"Session {duration} min exceeds available {available_minutes} min"
            ),
            "severity": "critical",
        })

    # Check 5 (warning): indoor cycling watts suspiciously low
    if is_cycling and day_plan.get("indoor") and watt_values:
        avg_watts = athlete_m.get("avg_watts_by_sport", {}).get(activity_type)
        if avg_watts:
            low = [w for w in watt_values if w < avg_watts * 0.50]
            if low:
                violations.append({
                    "type": "wattage_suspiciously_low",
                    "description": (
                        f"Indoor {activity_type} targets "
                        f"{', '.join(f'{w:.0f}W' for w in low)} "
                        f"are <50% of athlete avg {avg_watts:.0f}W"
                    ),
                    "severity": "warning",
                })

    return violations


# ---------------------------------------------------------------------------
# Layer 2 — Targeted LLM repair
# ---------------------------------------------------------------------------

def repair_day(
    day_plan: dict,
    violations: list[dict],
    schedule_day: dict,
    athlete_m: dict,
    recent_activities: list[dict],
) -> dict:
    """
    Ask Claude to regenerate one day, correcting only the listed violations.
    Returns the day dict with repaired=True and repair_reason added.
    """
    violation_text = "\n".join(
        f"  [{v['severity'].upper()}] {v['type']}: {v['description']}"
        for v in violations
    )

    max_w = athlete_m.get("max_watts")
    max_hr = athlete_m.get("max_hr")
    watts_by_sport = athlete_m.get("avg_watts_by_sport", {})
    hr_by_sport = athlete_m.get("avg_hr_by_sport", {})

    metrics_block = "\n".join(filter(None, [
        f"  Max cycling watts (average_watts): {max_w:.0f}W" if max_w else None,
        "  Avg watts by sport: " + ", ".join(
            f"{s} {w:.0f}W" for s, w in watts_by_sport.items()
        ) if watts_by_sport else None,
        f"  Absolute max HR recorded: {max_hr:.0f}bpm" if max_hr else None,
        "  Avg HR by sport: " + ", ".join(
            f"{s} {h:.0f}bpm" for s, h in hr_by_sport.items()
        ) if hr_by_sport else None,
    ]))

    prompt = f"""\
A training plan day has violations. Reproduce it exactly and fix ONLY the violations listed.
Do not change activity_type, indoor, intensity, time_of_day, flags, or weather.
Only correct duration_minutes and description.

ORIGINAL DAY:
{json.dumps(day_plan, indent=2)}

VIOLATIONS TO FIX:
{violation_text}

ATHLETE METRICS — prescribed targets must stay within these ranges:
{metrics_block}

HARD CONSTRAINTS:
  duration_minutes must be ≤ {schedule_day.get('minutes', 999)}
  indoor: {str(day_plan.get('indoor', False)).lower()}

Return a single JSON day object with keys:
  day, activity_type, duration_minutes, distance_km, intensity,
  time_of_day, description, indoor, flags, weather\
"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": _REPAIR_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": prompt}],
    )
    repaired = parse_json_response(response.content[0].text)
    repaired["repaired"] = True
    repaired["repair_reason"] = "; ".join(
        v["description"] for v in violations if v["severity"] == "critical"
    )
    return repaired


def _fallback_fix_day(
    day_plan: dict,
    violations: list[dict],
    available_minutes: int,
    athlete_m: dict,
) -> dict:
    """
    Deterministic in-place fix when LLM repair still has critical violations.
    Caps/strips bad values directly in the description text.
    """
    fixed = dict(day_plan)
    fixed["fallback"] = True
    fixed["fallback_reason"] = "; ".join(
        v["description"] for v in violations if v["severity"] == "critical"
    )

    if fixed.get("duration_minutes", 0) > available_minutes:
        fixed["duration_minutes"] = available_minutes

    description = fixed.get("description", "")
    vtypes = {v["type"] for v in violations}
    max_watts = athlete_m.get("max_watts")
    activity_type = fixed.get("activity_type", "")
    sport_max_hr = (
        athlete_m.get("max_hr_by_sport", {}).get(activity_type)
        or athlete_m.get("max_hr")
    )

    if "invalid_wattage" in vtypes:
        description = re.sub(
            r'\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*[Ww](?:atts?)?\b',
            "[effort target]",
            description,
        )

    if "wattage_too_high" in vtypes and max_watts:
        cap = int(max_watts * 0.90)
        threshold = max_watts * 1.20

        def _cap_watt(m: re.Match) -> str:
            nums = [float(n) for n in re.findall(r'\d+(?:\.\d+)?', m.group(0))]
            return f"{cap}W" if any(n > threshold for n in nums) else m.group(0)

        description = re.sub(
            r'\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?\s*[Ww](?:atts?)?\b',
            _cap_watt,
            description,
        )

    if ("hr_too_high" in vtypes or "hr_above_zone4" in vtypes) and sport_max_hr:
        z4_ceiling = int(sport_max_hr * 0.90)
        # Replace all absolute bpm targets with a zone-based placeholder
        description = re.sub(
            r'\d+(?:\s*[-–]\s*\d+)?\s*bpm\b',
            f"Zone 3-4 effort (≤{z4_ceiling}bpm)",
            description,
            count=1,
            flags=re.IGNORECASE,
        )
        # Strip any remaining bare bpm values
        description = re.sub(
            r'\d+(?:\s*[-–]\s*\d+)?\s*bpm\b',
            "[see zone chart]",
            description,
            flags=re.IGNORECASE,
        )

    fixed["description"] = description
    return fixed


# ---------------------------------------------------------------------------
# Core plan generator
# ---------------------------------------------------------------------------

def generate_plan(
    schedule: dict,
    goal: str,
    location: tuple[float, float] = DEFAULT_LOCATION,
    recent_activities: list[dict] | None = None,
    goals: dict | None = None,
    units: str = "imperial",
    on_token=None,
) -> dict:
    """
    Generate a structured weekly training plan.

    Args:
        schedule:           {"day": {"minutes": int, "time_of_day": str}, ...}
        goal:               Natural language goal string
        location:           (lat, lon) — defaults to Tacoma, WA
        recent_activities:  Pre-fetched activity list; fetched if not provided
        goals:              Persisted athlete profile from get_goals(); optional
        units:              "imperial" or "metric" — controls temp display in prompt
        on_token:           Optional callback(chars: int) called during streaming
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

{_format_resolved_schedule(resolved, units=units)}

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

    athlete_m = athlete_metrics(recent_activities)
    client = anthropic.Anthropic()
    api_kwargs = dict(
        model=MODEL,
        max_tokens=2048,
        system=[{"type": "text", "text": _build_system_prompt(athlete_m, goals), "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )

    if on_token is not None:
        with client.messages.stream(**api_kwargs) as stream:
            raw_text = ""
            for chunk in stream.text_stream:
                raw_text += chunk
                on_token(len(raw_text))
    else:
        response = client.messages.create(**api_kwargs)
        raw_text = response.content[0].text

    plan = parse_json_response(raw_text)

    # -- Post-generation validation and repair --------------------------------
    days_repaired = 0
    days_fallback = 0
    all_violations: list[dict] = []

    repaired_days = []
    for day in plan.get("days", []):
        day_name = day.get("day", "").lower()
        sched_day = schedule.get(day_name, {})
        available = sched_day.get("minutes", 9999)

        violations = validate_day(day, available, athlete_m)
        all_violations.extend(violations)
        critical = [v for v in violations if v["severity"] == "critical"]

        if critical:
            repaired = repair_day(day, critical, sched_day, athlete_m, recent_activities)
            re_violations = validate_day(repaired, available, athlete_m)
            re_critical = [v for v in re_violations if v["severity"] == "critical"]

            if re_critical:
                repaired = _fallback_fix_day(repaired, re_critical, available, athlete_m)
                days_fallback += 1
            else:
                days_repaired += 1

            repaired_days.append(repaired)
        else:
            repaired_days.append(day)

    plan["days"] = repaired_days
    plan["validation_summary"] = {
        "total_days": len(repaired_days),
        "days_clean": len(repaired_days) - days_repaired - days_fallback,
        "days_repaired": days_repaired,
        "days_fallback": days_fallback,
        "violations_found": len(all_violations),
        "critical": len([v for v in all_violations if v["severity"] == "critical"]),
        "warnings": len([v for v in all_violations if v["severity"] == "warning"]),
    }

    try:
        plan_id = save_plan(schedule, goal, plan)
        plan["plan_id"] = plan_id
    except Exception as exc:
        print(f"Warning: could not persist plan to database: {exc}")

    try:
        plan["coaching_assessment"] = assess_training_week(plan, recent_activities, goals)
    except Exception as exc:
        print(f"Warning: coaching assessment failed: {exc}")

    return plan


# ---------------------------------------------------------------------------
# Coaching assessment
# ---------------------------------------------------------------------------

# Maps goal-profile sport labels to plan activity_type values
_SPORT_LABEL_TO_TYPES: dict[str, set[str]] = {
    "Cycling":   {"Ride", "VirtualRide"},
    "Running":   {"Run"},
    "Triathlon": {"Ride", "VirtualRide", "Run", "Swim"},
    "Swimming":  {"Swim"},
}


def _compute_assessment_signals(
    plan: dict,
    recent_activities: list[dict],
    goals: dict | None,
) -> dict:
    """Deterministic layer: compute RED/YELLOW/GREEN per criterion."""
    today = datetime.now(tz=timezone.utc).date()
    planned_days = plan.get("days", [])
    planned_minutes = sum(d.get("duration_minutes", 0) for d in planned_days)

    # 4-week average weekly volume
    cutoff_4w = today - timedelta(days=28)
    acts_4w = [a for a in recent_activities if a["date"] >= cutoff_4w]
    weekly_bucket: dict[tuple, int] = defaultdict(int)
    for act in acts_4w:
        wk = act["date"].isocalendar()[:2]
        weekly_bucket[wk] += act["duration_seconds"] // 60
    avg_weekly_mins = (
        statistics.mean(weekly_bucket.values()) if weekly_bucket else 0
    )

    # Last 7-day actual volume
    cutoff_1w = today - timedelta(days=7)
    last_week_mins = sum(
        a["duration_seconds"] // 60
        for a in recent_activities if a["date"] >= cutoff_1w
    )

    signals: dict[str, dict] = {}

    # -- Volume ---------------------------------------------------------------
    if avg_weekly_mins > 0:
        vol_delta = abs(planned_minutes - avg_weekly_mins) / avg_weekly_mins
        vol_signal = "GREEN" if vol_delta <= 0.10 else ("YELLOW" if vol_delta <= 0.25 else "RED")
    else:
        vol_delta = 0.0
        vol_signal = "YELLOW"

    signals["volume"] = {
        "signal":              vol_signal,
        "planned_minutes":     planned_minutes,
        "avg_weekly_minutes":  round(avg_weekly_mins),
        "delta_pct":           round(vol_delta * 100),
    }

    # -- Sport balance --------------------------------------------------------
    primary_label = (goals or {}).get("sport_preferences", {}).get("primary_sport", "")
    primary_types = _SPORT_LABEL_TO_TYPES.get(primary_label, set())
    primary_minutes = sum(
        d.get("duration_minutes", 0) for d in planned_days
        if d.get("activity_type", "") in primary_types
    )
    if planned_minutes > 0 and primary_types:
        balance_pct = primary_minutes / planned_minutes
        bal_signal = "GREEN" if balance_pct >= 0.60 else ("YELLOW" if balance_pct >= 0.40 else "RED")
    else:
        balance_pct = 0.0
        bal_signal = "YELLOW"

    signals["sport_balance"] = {
        "signal":          bal_signal,
        "primary_sport":   primary_label or "unset",
        "primary_minutes": primary_minutes,
        "total_minutes":   planned_minutes,
        "primary_pct":     round(balance_pct * 100),
    }

    # -- Progression ----------------------------------------------------------
    if last_week_mins > 0:
        prog_delta = abs(planned_minutes - last_week_mins) / last_week_mins
        prog_signal = "GREEN" if prog_delta <= 0.15 else ("YELLOW" if prog_delta <= 0.25 else "RED")
    else:
        prog_delta = 0.0
        prog_signal = "YELLOW"

    signals["progression"] = {
        "signal":            prog_signal,
        "planned_minutes":   planned_minutes,
        "last_week_minutes": last_week_mins,
        "delta_pct":         round(prog_delta * 100),
    }

    # -- Event readiness (nearest event within 90 days) -----------------------
    upcoming = (goals or {}).get("upcoming_events") or []
    nearest_event: dict | None = None
    nearest_days: int | None = None
    for ev in upcoming:
        try:
            ev_date = date.fromisoformat(str(ev["date"]))
            days_left = (ev_date - today).days
            if 0 <= days_left <= 90:
                if nearest_days is None or days_left < nearest_days:
                    nearest_days = days_left
                    nearest_event = ev
        except (ValueError, KeyError, TypeError):
            pass

    if nearest_event and nearest_days is not None:
        has_hard = any(d.get("intensity") == "hard" for d in planned_days)
        hard_count = sum(1 for d in planned_days if d.get("intensity") == "hard")

        if nearest_days > 60:
            phase = "build"
            ev_signal = "GREEN" if vol_delta <= 0.25 else "YELLOW"
        elif nearest_days > 30:
            phase = "peak_build"
            if planned_minutes >= avg_weekly_mins * 0.90 and has_hard:
                ev_signal = "GREEN"
            elif planned_minutes >= avg_weekly_mins * 0.75:
                ev_signal = "YELLOW"
            else:
                ev_signal = "RED"
        elif nearest_days > 14:
            phase = "taper"
            if planned_minutes <= avg_weekly_mins * 0.85:
                ev_signal = "GREEN"
            elif planned_minutes <= avg_weekly_mins:
                ev_signal = "YELLOW"
            else:
                ev_signal = "RED"
        else:
            phase = "taper_hard"
            if planned_minutes <= avg_weekly_mins * 0.70 and hard_count == 0:
                ev_signal = "GREEN"
            elif hard_count <= 1:
                ev_signal = "YELLOW"
            else:
                ev_signal = "RED"

        signals["event_readiness"] = {
            "signal":       ev_signal,
            "event_name":   nearest_event.get("name", "Upcoming event"),
            "days_until":   nearest_days,
            "phase":        phase,
            "planned_minutes":    planned_minutes,
            "avg_weekly_minutes": round(avg_weekly_mins),
            "hard_sessions":      hard_count,
        }

    return signals


def _enrich_signals_with_llm(signals: dict, plan: dict, goals: dict | None) -> dict:
    """LLM layer: add one-sentence explanation + suggestion/affirmation per criterion."""
    PHASE_LABELS = {
        "build":      "build phase (>60 days out)",
        "peak_build": "peak build phase (30-60 days out)",
        "taper":      "taper phase (14-30 days out)",
        "taper_hard": "hard taper phase (<14 days out)",
    }

    context_lines = []
    for key, data in signals.items():
        sig = data["signal"]
        if key == "volume":
            context_lines.append(
                f"Volume [{sig}]: {data['planned_minutes']}min planned vs "
                f"{data['avg_weekly_minutes']}min 4-week avg ({data['delta_pct']}% delta)"
            )
        elif key == "sport_balance":
            context_lines.append(
                f"Sport balance [{sig}]: {data['primary_pct']}% of planned time "
                f"in primary sport ({data['primary_sport']})"
            )
        elif key == "progression":
            context_lines.append(
                f"Progression [{sig}]: {data['planned_minutes']}min planned vs "
                f"{data['last_week_minutes']}min last week ({data['delta_pct']}% change)"
            )
        elif key == "event_readiness":
            phase_label = PHASE_LABELS.get(data["phase"], data["phase"])
            context_lines.append(
                f"Event readiness [{sig}]: '{data['event_name']}' in {data['days_until']} days "
                f"({phase_label}); {data['hard_sessions']} hard session(s) planned"
            )

    criteria_json = {
        k: {"signal": v["signal"], "explanation": "", "suggestion_or_affirmation": ""}
        for k, v in signals.items()
    }

    prompt = f"""\
You are reviewing an automated training plan assessment. Four criteria have been scored \
GREEN/YELLOW/RED by deterministic rules. Write a brief explanation for each and either \
a specific suggestion (if YELLOW/RED) or a short affirmation (if GREEN).

SIGNALS:
{chr(10).join(context_lines)}

PLAN: {plan.get('week_goal', '')}

Rules:
- explanation: one sentence stating WHY the signal was assigned
- suggestion_or_affirmation: one sentence — specific fix if YELLOW/RED, short affirmation if GREEN
- Keep both under 20 words each

Return only this JSON (no other text):
{json.dumps(criteria_json, indent=2)}\
"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    result = parse_json_response(response.content[0].text)

    # Guarantee signal values come from the deterministic layer
    for key, data in signals.items():
        if key in result:
            result[key]["signal"] = data["signal"]
        else:
            result[key] = {"signal": data["signal"], "explanation": "", "suggestion_or_affirmation": ""}

    return result


def assess_training_week(
    plan: dict,
    recent_activities: list[dict],
    goals: dict | None = None,
) -> dict:
    """
    Compute a coaching assessment for the generated plan.
    Returns a dict keyed by criterion with signal, explanation, suggestion_or_affirmation.
    """
    signals = _compute_assessment_signals(plan, recent_activities, goals)
    return _enrich_signals_with_llm(signals, plan, goals)


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
    goals = get_goals()

    print(f"Goal     : {goal}")
    print(f"Location : Tacoma, WA {DEFAULT_LOCATION}")
    print(f"Days     : {', '.join(schedule.keys())}")
    print(f"History  : {len(recent_activities)} activities loaded")
    if goals:
        print(f"Objective: {goals.get('objective') or '(none)'}")
        events = goals.get("upcoming_events") or []
        for ev in events:
            try:
                days_until = (date.fromisoformat(str(ev["date"])) - date.today()).days
                print(f"  Event  : {ev['name']} in {days_until}d")
            except (ValueError, KeyError):
                pass
    print()

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
    plan = generate_plan(schedule, goal, recent_activities=recent_activities, goals=goals)

    print(f"Week goal: {plan['week_goal']}")
    if plan.get("plan_id"):
        print(f"Saved as plan #{plan['plan_id']}\n")
    else:
        print()
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
