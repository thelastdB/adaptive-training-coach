"""
eval.py — Evaluation framework for generated training plans.

score_plan()        — Scores a single plan against a rubric using Claude as judge.
save_eval_results() — Persists a suite run to a timestamped JSON file.
run_eval_suite()    — Runs multiple plans from a predefined test set, prints a
                      summary table, identifies the primary failure mode, and saves results.
"""

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from db_supabase import athlete_metrics, get_activities
from plan_generator import (
    DEFAULT_LOCATION,
    WEEKDAY_MAP,
    generate_plan,
    get_weekly_forecast,
    parse_json_response,
    resolve_training_conditions,
)

load_dotenv()

MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Rubric
# ---------------------------------------------------------------------------

RUBRIC: dict[str, str] = {
    "schedule_respected": (
        "Did every planned session stay at or within the athlete's available minutes? "
        "Score 5 if all sessions fit; deduct 1 for each session that exceeds its window."
    ),
    "intensity_progression": (
        "Is the intensity distribution sensible across the week? "
        "Intensity caps are CEILINGS, not targets — prescribing easy or moderate on a day "
        "capped at hard is correct when recovery context justifies it (e.g. back-to-back "
        "training days, post-hard-effort flag, first session after a gap). "
        "Downgrading intensity below the cap is acceptable and encouraged when recovery "
        "rules, consecutive training days, or post-hard-effort flags are present. "
        "Penalize only when: (a) intensity exceeds its cap, or (b) hard sessions appear "
        "back-to-back with no recovery rationale in the description. "
        "Score 5 for a week with clear periodization logic; score 1 only if hard efforts "
        "stack consecutively with zero recovery structure."
    ),
    "rule_compliance": (
        "Did the plan honor every pre-resolved decision from the rule engine? "
        "Specifically: indoor when the indoor flag is True; Run or VirtualRide when ≤60 min "
        "suggested; Yoga when flagged for active recovery; intensity at or below the cap. "
        "Score 5 for perfect compliance; deduct 1 per clear violation."
    ),
    "data_grounded": (
        "Are training targets grounded in this athlete's actual data? Evaluate four things: "
        "(1) HR prescription — does the plan use zone names (Zone 1-5) rather than raw bpm? "
        "Do the zone bpm ranges cited match the athlete's actual per-sport max HR "
        "(e.g. Run Z4 should end near 90% of the athlete's recorded run max HR)? "
        "(2) Power — are wattage targets within the athlete's demonstrated range "
        "(e.g. not prescribing 200W for a cyclist whose recorded average is 99-131W)? "
        "(3) Pace — are run pace targets consistent with the athlete's demonstrated speed "
        "(recorded ~10.4 km/h ≈ 5:46/km avg)? "
        "(4) Zone usage — prescribing 'Zone 2 effort' without any bpm context is fine; "
        "prescribing absolute bpm without any zone reference should be penalized. "
        "Score 5 if zones are used correctly and power/pace targets match history; "
        "score 1 if targets are clearly fabricated or contradict the athlete's data."
    ),
    "description_quality": (
        "Are workout descriptions specific, structured, and actionable? "
        "Score 5 for concrete structure (warm-up, main set, cool-down), numeric targets, "
        "and sport-specific cues. Score 1 for vague descriptions like 'go for a run'."
    ),
    "weather_appropriate": (
        "Does the plan reflect the actual weather conditions provided? "
        "Score 5 if every session acknowledges conditions and adapts (e.g. indoor on rainy days, "
        "early start on hot/humid days, reduced intensity in extreme heat). "
        "Score 1 if weather is completely ignored."
    ),
}

# Cached scoring system prompt (same text every call → cache hit after first)
_SCORE_SYSTEM_PROMPT = (
    "You are an expert endurance sports coach evaluating a generated training plan. "
    "Be critical and precise. A score of 5 requires clear evidence of excellence; "
    "a score of 3 is average; 1 means the criterion is not met. "
    "Return valid JSON only — no markdown fences, no prose."
)

# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------

TEST_SCENARIOS = [
    {
        "name": "Base cycling — 3 days standard",
        "schedule": {
            "monday":    {"minutes": 60,  "time_of_day": "morning"},
            "wednesday": {"minutes": 45,  "time_of_day": "evening"},
            "saturday":  {"minutes": 120, "time_of_day": "morning"},
        },
        "goal": "maintain fitness with a focus on cycling",
    },
    {
        "name": "Time-crunched runner — all ≤60 min (Rule 6 fires every day)",
        "schedule": {
            "tuesday":  {"minutes": 40, "time_of_day": "morning"},
            "thursday": {"minutes": 35, "time_of_day": "evening"},
            "sunday":   {"minutes": 50, "time_of_day": "morning"},
        },
        "goal": "improve 5K pace and running economy",
    },
    {
        "name": "Back-to-back days — Rule 7 stress test",
        "schedule": {
            "monday":   {"minutes": 90,  "time_of_day": "morning"},
            "tuesday":  {"minutes": 60,  "time_of_day": "evening"},
            "thursday": {"minutes": 45,  "time_of_day": "morning"},
            "saturday": {"minutes": 150, "time_of_day": "morning"},
        },
        "goal": "build cycling base for a century ride",
    },
    {
        "name": "Recovery week — low volume, post hard block",
        "schedule": {
            "wednesday": {"minutes": 30, "time_of_day": "morning"},
            "friday":    {"minutes": 30, "time_of_day": "evening"},
            "sunday":    {"minutes": 60, "time_of_day": "morning"},
        },
        "goal": "active recovery and mobility after a hard training block",
    },
    {
        "name": "Multi-sport — four days cycling and running mix",
        "schedule": {
            "monday":    {"minutes": 60, "time_of_day": "morning"},
            "wednesday": {"minutes": 45, "time_of_day": "morning"},
            "friday":    {"minutes": 45, "time_of_day": "evening"},
            "sunday":    {"minutes": 90, "time_of_day": "morning"},
        },
        "goal": "build overall aerobic fitness across cycling and running",
    },
]

# ---------------------------------------------------------------------------
# Helpers for scoring context
# ---------------------------------------------------------------------------

def _athlete_metric_summary(activities: list[dict]) -> str:
    """Thin wrapper — delegates to db.athlete_metrics for the formatted string."""
    return athlete_metrics(activities)["summary_text"]


def _format_resolved_for_eval(resolved: dict) -> str:
    lines = []
    for day in sorted(resolved.keys(), key=lambda d: WEEKDAY_MAP[d.lower()]):
        e = resolved[day]
        lines.append(
            f"  {day.capitalize()} — "
            f"indoor={'Yes' if e['indoor'] else 'No'}, "
            f"activity={e['suggested_activity_type'] or '(open)'}, "
            f"cap={e['intensity_cap']}"
        )
        for flag in e.get("flags", []):
            lines.append(f"    · {flag}")
    return "\n".join(lines)


def _format_schedule_for_eval(schedule: dict) -> str:
    return "\n".join(
        f"  {day.capitalize()}: {info['minutes']} min, {info['time_of_day']}"
        for day, info in schedule.items()
    )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_plan(
    plan: dict,
    schedule: dict,
    recent_activities: list[dict],
    resolved_conditions: dict,
) -> dict:
    """
    Score a generated plan against RUBRIC using Claude as judge.

    Returns a dict with one entry per rubric criterion (score + justification)
    plus an "overall" float that is the mean of individual scores.
    """
    rubric_block = "\n".join(
        f"{i}. {key} (1–5): {desc}"
        for i, (key, desc) in enumerate(RUBRIC.items(), 1)
    )

    prompt = f"""\
Evaluate this training plan against the rubric below. Be critical and precise.

RUBRIC:
{rubric_block}

INPUT SCHEDULE (requested by athlete):
{_format_schedule_for_eval(schedule)}

RULE ENGINE DECISIONS (must be honored — violations lower rule_compliance):
{_format_resolved_for_eval(resolved_conditions)}

ATHLETE PERFORMANCE RANGES (use to judge data_grounded):
{_athlete_metric_summary(recent_activities)}

GENERATED PLAN TO EVALUATE:
{json.dumps(plan, indent=2)}

Return JSON with exactly this structure — one entry per rubric key, plus nothing else:
{{
  "schedule_respected":    {{"score": <1-5>, "justification": "<one sentence>"}},
  "intensity_progression": {{"score": <1-5>, "justification": "<one sentence>"}},
  "rule_compliance":       {{"score": <1-5>, "justification": "<one sentence>"}},
  "data_grounded":         {{"score": <1-5>, "justification": "<one sentence>"}},
  "description_quality":   {{"score": <1-5>, "justification": "<one sentence>"}},
  "weather_appropriate":   {{"score": <1-5>, "justification": "<one sentence>"}}
}}\
"""

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": _SCORE_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    scores = parse_json_response(raw)

    individual = [v["score"] for v in scores.values() if isinstance(v, dict)]
    scores["overall"] = round(statistics.mean(individual), 2) if individual else 0.0
    return scores


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

EVAL_RESULTS_DIR = Path(__file__).parent / "eval_results"


def save_eval_results(results: list[dict], filename: str | None = None) -> Path:
    """
    Save the output of run_eval_suite() to a timestamped JSON file in eval_results/.

    Args:
        results:  List of result dicts returned by run_eval_suite().
        filename: Optional explicit filename. Defaults to eval_YYYYMMDD_HHMMSS.json.

    Returns:
        Path to the written file.
    """
    EVAL_RESULTS_DIR.mkdir(exist_ok=True)

    if filename is None:
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"eval_{ts}.json"

    out_path = EVAL_RESULTS_DIR / filename

    criterion_scores = {c: [] for c in RUBRIC}
    for r in results:
        for c in RUBRIC:
            entry = r["scores"].get(c, {})
            if isinstance(entry, dict):
                criterion_scores[c].append(entry["score"])

    criterion_means = {
        c: round(statistics.mean(v), 2) if v else 0.0
        for c, v in criterion_scores.items()
    }
    overall_mean = round(
        statistics.mean(r["scores"]["overall"] for r in results), 2
    )
    worst_criterion = min(criterion_means, key=criterion_means.get)

    payload = {
        "run_at": datetime.now(tz=timezone.utc).isoformat(),
        "n": len(results),
        "summary": {
            "criterion_means": criterion_means,
            "overall_mean": overall_mean,
            "primary_failure_mode": worst_criterion,
        },
        "runs": [
            {
                "scenario": r["scenario"],
                "overall": r["scores"]["overall"],
                "scores": r["scores"],
                "plan": r["plan"],
            }
            for r in results
        ],
    }

    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"Results saved → {out_path}")
    return out_path


# ---------------------------------------------------------------------------
# Eval suite
# ---------------------------------------------------------------------------

def run_eval_suite(n: int = 5) -> list[dict]:
    """
    Generate and score n plans from TEST_SCENARIOS (cycles if n > len).

    Prints a summary table and identifies the lowest-scoring criterion
    across all runs as the primary failure mode.
    """
    recent_activities = get_activities(days=90)
    forecast = get_weekly_forecast(*DEFAULT_LOCATION)

    results: list[dict] = []
    for i in range(n):
        scenario = TEST_SCENARIOS[i % len(TEST_SCENARIOS)]
        print(f"[{i+1}/{n}] Generating: {scenario['name']} …")

        resolved = resolve_training_conditions(
            scenario["schedule"], forecast, recent_activities
        )
        try:
            plan = generate_plan(
                scenario["schedule"],
                scenario["goal"],
                recent_activities=recent_activities,
            )
        except ValueError as exc:
            print(f"       SKIP — JSON parse error: {exc}")
            continue

        print(f"       Scoring …")
        scores = score_plan(plan, scenario["schedule"], recent_activities, resolved)

        results.append({
            "scenario": scenario["name"],
            "plan": plan,
            "resolved": resolved,
            "scores": scores,
        })
        print(f"       Overall: {scores['overall']:.2f}")

    _print_summary(results)
    save_eval_results(results)
    return results


def _print_summary(results: list[dict]) -> None:
    criteria = list(RUBRIC.keys())
    # Short column headers to keep the table readable
    col_labels = ["sched", "intens", "rule", "data", "desc", "weath"]
    name_w = 42
    col_w = 8

    sep = "─" * (name_w + col_w * len(criteria) + col_w)
    header = f"{'Scenario':<{name_w}}" + "".join(
        f"{h:>{col_w}}" for h in col_labels
    ) + f"{'avg':>{col_w}}"

    print(f"\nEval Suite Results ({len(results)} run{'s' if len(results) != 1 else ''})")
    print("═" * len(sep))
    print(header)
    print(sep)

    criterion_scores: dict[str, list[float]] = {c: [] for c in criteria}

    for r in results:
        scores = r["scores"]
        name = r["scenario"]
        if len(name) > name_w - 1:
            name = name[: name_w - 4] + "…"
        row = f"{name:<{name_w}}"
        for c in criteria:
            entry = scores.get(c, {})
            s = entry["score"] if isinstance(entry, dict) else float(entry)
            row += f"{s:>{col_w}.1f}"
            criterion_scores[c].append(s)
        row += f"{scores['overall']:>{col_w}.2f}"
        print(row)

    print(sep)

    avg_row = f"{'Average':<{name_w}}"
    criterion_means: dict[str, float] = {}
    for c in criteria:
        m = statistics.mean(criterion_scores[c]) if criterion_scores[c] else 0.0
        criterion_means[c] = m
        avg_row += f"{m:>{col_w}.2f}"
    overall_mean = statistics.mean(r["scores"]["overall"] for r in results)
    avg_row += f"{overall_mean:>{col_w}.2f}"
    print(avg_row)
    print("═" * len(sep))

    worst = min(criterion_means, key=criterion_means.get)
    print(f"\nPrimary failure mode: {worst}  (avg {criterion_means[worst]:.2f}/5.0)")
    print(f"  Rubric: {RUBRIC[worst][:120]}…")

    print("\nPer-criterion justifications for lowest scoring run:")
    worst_run = min(results, key=lambda r: r["scores"]["overall"])
    print(f"  Scenario: {worst_run['scenario']}")
    for c in criteria:
        entry = worst_run["scores"].get(c, {})
        if isinstance(entry, dict):
            print(f"  {c}: {entry['score']} — {entry.get('justification','')}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_eval_suite(n=5)
