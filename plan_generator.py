import json
import os
from collections import defaultdict
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

from db import get_activities
from vector_store import search_activities

load_dotenv()

MODEL = "claude-sonnet-4-6"

# time_of_day is passed through to the prompt and preserved in the output so that
# a future weather lookup can adjust recommendations (e.g. avoid hard efforts in
# afternoon heat, suggest indoor alternatives during morning rain).
SYSTEM_PROMPT = """\
You are an expert endurance sports coach specializing in cycling, running, and \
cross-training periodization. Generate personalized weekly training plans that \
respect the athlete's recent load, available time, and stated goal.

Principles to apply:
- Match intensity distribution to goal (base vs. threshold vs. race prep)
- Balance stress and recovery across the week
- Size estimated distances to realistic paces given the athlete's history
- Only schedule sessions on days the athlete has listed as available

Always respond with valid JSON only — no markdown fences, no prose, no explanation.\
"""


def _training_load_summary(days: int = 28) -> str:
    """Return a human-readable summary of the last N days grouped by ISO week and sport."""
    activities = get_activities(days=days)
    if not activities:
        return "No recent activity data available."

    today = datetime.now(tz=timezone.utc).date()

    # week_key: ISO (year, week) tuple so partial weeks are accurate
    weekly: dict[tuple, dict[str, dict]] = defaultdict(
        lambda: defaultdict(lambda: {"sessions": 0, "km": 0.0, "min": 0})
    )
    for act in activities:
        key = act["date"].isocalendar()[:2]  # (year, week_number)
        bucket = weekly[key][act["activity_type"]]
        bucket["sessions"] += 1
        bucket["km"] += act["distance_km"]
        bucket["min"] += act["duration_seconds"] // 60

    lines = []
    for week_key in sorted(weekly.keys(), reverse=True):
        year, wk = week_key
        days_since = (today - datetime.strptime(f"{year}-W{wk:02d}-1", "%G-W%V-%u").date()).days
        label = f"Week of ~{days_since}d ago (ISO {year}-W{wk:02d})"
        lines.append(label)
        for sport, s in sorted(weekly[week_key].items()):
            lines.append(
                f"  {sport}: {s['sessions']} session(s), "
                f"{s['km']:.1f} km, {s['min']} min"
            )
    return "\n".join(lines)


def _format_schedule(schedule: dict) -> str:
    return "\n".join(
        f"  {day.capitalize()}: {info['minutes']} min available, {info['time_of_day']}"
        for day, info in schedule.items()
    )


def _format_examples(examples: list[dict]) -> str:
    return "\n".join(f"  - {e['text']}" for e in examples)


def generate_plan(schedule: dict, goal: str) -> dict:
    """
    Generate a structured weekly training plan.

    Args:
        schedule: Dict mapping day names to {"minutes": int, "time_of_day": str}
        goal: Natural language goal string

    Returns:
        Parsed JSON plan dict
    """
    training_load = _training_load_summary()
    examples = search_activities(goal, n=5)

    user_message = f"""\
GOAL: {goal}

RECENT TRAINING LOAD (last 4 weeks):
{training_load}

SIMILAR PAST WORKOUTS (reference examples from athlete's history):
{_format_examples(examples)}

AVAILABLE TRAINING DAYS:
{_format_schedule(schedule)}

Return a JSON object with exactly this structure:
{{
  "week_goal": "<one-sentence focus for the week>",
  "days": [
    {{
      "day": "<day name matching the schedule>",
      "activity_type": "<e.g. Ride, Run, VirtualRide, Walk, Yoga, Rest>",
      "duration_minutes": <integer>,
      "distance_km": <float or null if not applicable>,
      "intensity": "<easy | moderate | hard | race>",
      "time_of_day": "<morning | afternoon | evening>",
      "description": "<specific workout instructions, 1-3 sentences>"
    }}
  ]
}}

Include one entry per day listed in the schedule. Do not add extra days.\
"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    return json.loads(raw)


def main() -> None:
    schedule = {
        "monday": {"minutes": 60, "time_of_day": "morning"},
        "wednesday": {"minutes": 45, "time_of_day": "evening"},
        "saturday": {"minutes": 120, "time_of_day": "morning"},
    }
    goal = "maintain fitness with a focus on cycling"

    print(f"Goal : {goal}")
    print(f"Days : {', '.join(schedule.keys())}")
    print("Generating plan...\n")

    plan = generate_plan(schedule, goal)

    print(f"Week goal: {plan['week_goal']}\n")
    for day in plan["days"]:
        dist = f"~{day['distance_km']} km" if day.get("distance_km") else "no distance target"
        print(
            f"{day['day'].capitalize()} [{day['time_of_day']}]  "
            f"{day['activity_type']}  {day['duration_minutes']} min  "
            f"{dist}  ({day['intensity']})"
        )
        print(f"  {day['description']}")
        print()

    print("Full JSON:")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
