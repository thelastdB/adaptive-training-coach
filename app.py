"""
app.py — Adaptive Training Coach Streamlit frontend.

Sidebar navigation: Weekly Plan · Plan History · Profile & Goals
"""

import json
from collections import defaultdict
from datetime import date, timedelta

import anthropic
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from db import (
    athlete_metrics,
    get_activities,
    get_goals,
    get_plan,
    get_plans,
    rate_plan,
    save_goals,
)
from plan_generator import (
    MODEL,
    _build_system_prompt,
    generate_plan,
    parse_json_response,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
TIME_OPTIONS = ["morning", "afternoon", "evening"]
SPORT_OPTIONS = ["Cycling", "Running", "Triathlon", "Swimming", "Other"]

INTENSITY_BADGE = {
    "easy":     "🟢 Easy",
    "moderate": "🟡 Moderate",
    "hard":     "🔴 Hard",
    "race":     "🟣 Race",
}

def _fmt_temp(temp_str: str, units: str) -> str:
    """Convert a stored '19°C' string to °F for display when units='imperial'."""
    if units == "metric" or not temp_str or "°" not in str(temp_str):
        return temp_str
    try:
        c = float(str(temp_str).replace("°C", "").strip())
        return f"{c * 9 / 5 + 32:.0f}°F"
    except (ValueError, AttributeError):
        return temp_str


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Training Coach",
    page_icon="🚴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _init_state() -> None:
    if "goals" not in st.session_state:
        st.session_state.goals = get_goals()

    if "current_plan" not in st.session_state:
        st.session_state.current_plan = None

    # Per-day widget defaults — only written once; widgets own values after that
    _defaults = {
        "monday":    (True,  60,  "morning"),
        "tuesday":   (False, 45,  "morning"),
        "wednesday": (True,  45,  "evening"),
        "thursday":  (False, 45,  "morning"),
        "friday":    (False, 45,  "morning"),
        "saturday":  (True,  120, "morning"),
        "sunday":    (False, 60,  "morning"),
    }
    for day, (enabled, minutes, tod) in _defaults.items():
        st.session_state.setdefault(f"chk_{day}", enabled)
        st.session_state.setdefault(f"min_{day}", minutes)
        st.session_state.setdefault(f"tod_{day}", tod)

    st.session_state.setdefault("week_notes", "")


_init_state()

# ---------------------------------------------------------------------------
# Cached data helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def _load_data(days: int = 90):
    """Return (activities list, athlete_metrics dict). Cached 5 min."""
    acts = get_activities(days=days)
    return acts, athlete_metrics(acts)


@st.cache_data(ttl=60)
def _load_last_week():
    return get_activities(days=7)

# ---------------------------------------------------------------------------
# Schedule helpers
# ---------------------------------------------------------------------------

def _active_schedule() -> dict:
    """Build schedule dict from session_state widget values for checked days."""
    return {
        day: {
            "minutes":     st.session_state.get(f"min_{day}", 60),
            "time_of_day": st.session_state.get(f"tod_{day}", "morning"),
        }
        for day in DAYS
        if st.session_state.get(f"chk_{day}", False)
    }

# ---------------------------------------------------------------------------
# Single-day regeneration
# ---------------------------------------------------------------------------

def _regen_single_day(
    day_plan: dict,
    schedule_day: dict,
    goals: dict | None,
    athlete_m: dict,
) -> dict:
    """Ask Claude for a fresh alternative workout, keeping the same constraints."""
    client = anthropic.Anthropic()
    sys_prompt = _build_system_prompt(athlete_m, goals)

    prompt = f"""\
Generate a fresh alternative workout for this training day.
Keep the same constraints but create a meaningfully different session.

CURRENT DAY (replace this):
{json.dumps(day_plan, indent=2)}

Hard constraints:
  Available: {schedule_day['minutes']} min
  Time of day: {schedule_day['time_of_day']}
  Indoor: {day_plan.get('indoor', False)}

Return a single JSON day object with keys:
  day, activity_type, duration_minutes, distance_km, intensity,
  time_of_day, description, indoor, flags, weather\
"""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=sys_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    result = parse_json_response(response.content[0].text)
    # Preserve structural fields the model might omit
    result.setdefault("day", day_plan["day"])
    result.setdefault("flags", day_plan.get("flags", []))
    result.setdefault("weather", day_plan.get("weather", {}))
    result.setdefault("indoor", day_plan.get("indoor", False))
    return result

# ---------------------------------------------------------------------------
# Reusable UI components
# ---------------------------------------------------------------------------

def _render_day_card(
    day: dict,
    athlete_m: dict,
    goals: dict | None,
    *,
    allow_regen: bool = True,
    readonly: bool = False,
) -> None:
    """Render one training day as a bordered card."""
    units = (goals or {}).get("units", "imperial")

    with st.container(border=True):
        info_col, btn_col = st.columns([5, 1])

        with info_col:
            badge = INTENSITY_BADGE.get(day.get("intensity", ""), "⚪ Unknown")
            indoor_tag = " · 🏠 Indoor" if day.get("indoor") else ""
            st.markdown(
                f"**{day['day'].capitalize()}** &nbsp;·&nbsp; "
                f"{day.get('activity_type', '')} &nbsp;·&nbsp; "
                f"{day.get('duration_minutes', '')} min &nbsp;·&nbsp; "
                f"{day.get('time_of_day', '').capitalize()} &nbsp;·&nbsp; "
                f"{badge}{indoor_tag}"
            )
            w = day.get("weather") or {}
            if w.get("conditions"):
                st.caption(
                    f"🌤 {w['conditions'].capitalize()}, "
                    f"{_fmt_temp(w.get('temp_max', '?'), units)}"
                    f"/{_fmt_temp(w.get('temp_min', '?'), units)}, "
                    f"humidity {w.get('humidity', 'n/a')}, "
                    f"precip {w.get('precipitation_chance', '?')}"
                )
            st.write(day.get("description", ""))

        if allow_regen and not readonly:
            with btn_col:
                day_name = day["day"].lower()
                if st.button("↺", key=f"regen_{day_name}", help="Regenerate this day"):
                    sched = {
                        "minutes":     st.session_state.get(f"min_{day_name}", 60),
                        "time_of_day": st.session_state.get(f"tod_{day_name}", "morning"),
                    }
                    with st.spinner(f"Regenerating {day['day']}…"):
                        new_day = _regen_single_day(day, sched, goals, athlete_m)
                    for i, d in enumerate(st.session_state.current_plan["days"]):
                        if d["day"].lower() == day_name:
                            st.session_state.current_plan["days"][i] = new_day
                            break
                    st.rerun()


def _render_last_week_summary() -> None:
    with st.expander("📊 Last week's training", expanded=False):
        acts = _load_last_week()
        if not acts:
            st.caption("No activities in the past 7 days.")
            return

        sport_totals: dict = defaultdict(lambda: {"sessions": 0, "km": 0.0, "min": 0})
        daily_min: dict = defaultdict(int)
        for a in acts:
            t = sport_totals[a["activity_type"]]
            t["sessions"] += 1
            t["km"] += a["distance_km"]
            t["min"] += a["duration_seconds"] // 60
            daily_min[str(a["date"])] += a["duration_seconds"] // 60

        metric_cols = st.columns(max(len(sport_totals), 1))
        for i, (sport, t) in enumerate(sorted(sport_totals.items())):
            with metric_cols[i % len(metric_cols)]:
                st.metric(
                    sport,
                    f"{t['sessions']}x · {t['km']:.0f} km",
                    f"{t['min']} min",
                )

        today = date.today()
        days_range = [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        chart_df = pd.DataFrame(
            {"minutes": [daily_min.get(d, 0) for d in days_range]},
            index=days_range,
        )
        st.bar_chart(chart_df, height=120, use_container_width=True)

# ---------------------------------------------------------------------------
# Coaching assessment banner
# ---------------------------------------------------------------------------

_SIGNAL_DOT = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}
_CRITERIA_META = {
    "volume":          "Volume",
    "sport_balance":   "Sport Balance",
    "progression":     "Progression",
    "event_readiness": "Event Readiness",
}


def _render_coaching_assessment(assessment: dict) -> None:
    """Compact one-row-per-criterion banner with signal dots."""
    rows = [(k, _CRITERIA_META[k]) for k in _CRITERIA_META if k in assessment]
    if not rows:
        return
    with st.container(border=True):
        st.caption("**Coaching overview**")
        for key, label in rows:
            c = assessment[key]
            dot = _SIGNAL_DOT.get(c.get("signal", ""), "⚪")
            explanation = c.get("explanation", "")
            suggestion = c.get("suggestion_or_affirmation", "")
            line = f"{dot} **{label}** — {explanation}"
            if suggestion:
                line += f" *{suggestion}*"
            st.markdown(line)


# ---------------------------------------------------------------------------
# Page: Weekly Plan
# ---------------------------------------------------------------------------

def _run_generation(schedule: dict, goal: str, recent_acts: list, athlete_m: dict) -> None:
    goals = st.session_state.goals
    units = (goals or {}).get("units", "imperial")

    progress = st.empty()

    def on_token(char_count: int) -> None:
        progress.caption(f"Thinking… ~{max(1, char_count // 4)} tokens")

    plan = generate_plan(
        schedule,
        goal,
        recent_activities=recent_acts,
        goals=goals,
        units=units,
        on_token=on_token,
    )
    progress.empty()
    st.session_state.current_plan = plan
    st.rerun()


def render_weekly_plan() -> None:
    st.title("Weekly Plan")
    _render_last_week_summary()

    recent_acts, athlete_m = _load_data(days=90)

    left, right = st.columns([1, 2], gap="large")

    # ── Left: schedule builder ──────────────────────────────────────────────
    with left:
        st.subheader("Schedule")

        for day in DAYS:
            st.checkbox(day.capitalize(), key=f"chk_{day}")
            if st.session_state.get(f"chk_{day}"):
                c1, c2 = st.columns([3, 2])
                with c1:
                    st.slider(
                        "Min",
                        15, 180,
                        step=5,
                        key=f"min_{day}",
                        label_visibility="collapsed",
                        format="%d min",
                    )
                with c2:
                    st.selectbox(
                        "Time",
                        TIME_OPTIONS,
                        key=f"tod_{day}",
                        label_visibility="collapsed",
                    )

        st.divider()
        st.text_area(
            "This week's notes",
            placeholder="Focus for this week, how you're feeling, anything to consider…",
            height=80,
            key="week_notes",
        )

        st.divider()
        schedule = _active_schedule()

        if not schedule:
            st.warning("Check at least one training day.")
        else:
            if st.button("Generate Plan", type="primary", use_container_width=True):
                goal = (
                    st.session_state.week_notes.strip()
                    or (st.session_state.goals or {}).get("objective")
                    or "maintain fitness"
                )
                _run_generation(schedule, goal, recent_acts, athlete_m)

    # ── Right: plan display ─────────────────────────────────────────────────
    with right:
        st.subheader("This Week")
        plan = st.session_state.current_plan

        if not plan:
            st.info("Configure your schedule on the left and click **Generate Plan**.")
        else:
            week_goal = plan.get("week_goal", "")
            if week_goal:
                st.markdown(f"_{week_goal}_")

            if plan.get("coaching_assessment"):
                _render_coaching_assessment(plan["coaching_assessment"])

            vs = plan.get("validation_summary", {})
            if vs.get("days_repaired") or vs.get("days_fallback"):
                st.caption(
                    f"✓ {vs.get('days_clean', 0)} clean &nbsp; "
                    f"🔧 {vs.get('days_repaired', 0)} repaired &nbsp; "
                    f"⚠️ {vs.get('days_fallback', 0)} fallback"
                )
            if plan.get("plan_id"):
                st.caption(f"Plan #{plan['plan_id']}")

            for day in plan.get("days", []):
                _render_day_card(day, athlete_m, st.session_state.goals)

            st.divider()
            if st.button("↺ Regenerate entire plan", use_container_width=True):
                goal = (
                    st.session_state.week_notes.strip()
                    or (st.session_state.goals or {}).get("objective")
                    or "maintain fitness"
                )
                _run_generation(_active_schedule(), goal, recent_acts, athlete_m)

# ---------------------------------------------------------------------------
# Page: Plan History
# ---------------------------------------------------------------------------

def render_plan_history() -> None:
    st.title("Plan History")
    plans = get_plans(limit=20)

    if not plans:
        st.info("No plans yet. Generate your first plan on the Weekly Plan page.")
        return

    _, athlete_m = _load_data(days=90)

    for p in plans:
        created = (p.get("created_at") or "")[:10]
        week    = p.get("week_start_date", "")
        goal_text = (p.get("goal_text") or "")[:60]
        rating  = p.get("rating")
        stars   = "★" * rating if rating else "—"
        label   = f"**{created}** · Week of {week} · _{goal_text}_ · {stars}"

        with st.expander(label, expanded=False):
            inner = p.get("plan") or {}
            for day in inner.get("days", []):
                _render_day_card(day, athlete_m, None, allow_regen=False, readonly=True)

            st.divider()
            if not rating:
                st.markdown("**Rate this plan:**")
                star_cols = st.columns(5)
                for n, col in enumerate(star_cols, 1):
                    with col:
                        if st.button("★" * n, key=f"rate_{p['id']}_{n}"):
                            rate_plan(p["id"], n)
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.caption(f"Your rating: {'★' * rating}")

# ---------------------------------------------------------------------------
# Page: Profile & Goals
# ---------------------------------------------------------------------------

def render_profile() -> None:
    st.title("Profile & Goals")

    goals = st.session_state.goals or {}

    # Initialise draft state from DB (once per session)
    if "events_draft" not in st.session_state:
        st.session_state.events_draft = list(goals.get("upcoming_events") or [])
    st.session_state.setdefault("editing_event_idx", None)

    # ── Main profile form ───────────────────────────────────────────────────
    with st.form("profile_form"):
        st.subheader("General")
        objective = st.text_area(
            "Objective",
            value=goals.get("objective", ""),
            placeholder="Describe your overall training goals this season…",
            height=100,
        )
        physical_notes = st.text_area(
            "Physical notes",
            value=goals.get("physical_notes", ""),
            placeholder="Injuries, fitness level, anything the coach should know…",
            height=80,
        )

        units_opts = ["Imperial (°F)", "Metric (°C)"]
        cur_units_label = "Imperial (°F)" if goals.get("units", "imperial") == "imperial" else "Metric (°C)"
        units_choice = st.radio(
            "Temperature units",
            units_opts,
            index=units_opts.index(cur_units_label),
            horizontal=True,
        )

        st.subheader("Sport preferences")
        prefs = goals.get("sport_preferences") or {}
        pc1, pc2 = st.columns(2)
        with pc1:
            cur_primary = prefs.get("primary_sport", "Cycling")
            primary_sport = st.selectbox(
                "Primary sport",
                SPORT_OPTIONS,
                index=SPORT_OPTIONS.index(cur_primary) if cur_primary in SPORT_OPTIONS else 0,
            )
        with pc2:
            secondary_options = ["None"] + SPORT_OPTIONS
            cur_secondary = prefs.get("secondary_sport", "None") or "None"
            secondary_sport = st.selectbox(
                "Secondary sport",
                secondary_options,
                index=secondary_options.index(cur_secondary)
                if cur_secondary in secondary_options else 0,
            )

        saved = st.form_submit_button("Save profile", type="primary")

    if saved:
        new_goals = {
            "objective":         objective,
            "physical_notes":    physical_notes,
            "units":             "imperial" if "Imperial" in units_choice else "metric",
            "sport_preferences": {
                "primary_sport":   primary_sport,
                "secondary_sport": secondary_sport if secondary_sport != "None" else "",
            },
            "upcoming_events": st.session_state.events_draft,
        }
        save_goals(new_goals)
        st.session_state.goals = get_goals()
        st.cache_data.clear()
        st.success("Profile saved.")

    # ── Upcoming events (dynamic list — must live outside the form) ─────────
    st.subheader("Upcoming events")

    if st.session_state.events_draft:
        for i, ev in enumerate(st.session_state.events_draft):
            days_until = None
            try:
                days_until = (date.fromisoformat(str(ev["date"])) - date.today()).days
            except (ValueError, KeyError):
                pass

            ec1, ec2, ec3, ec4, ec5, ec6 = st.columns([3, 2, 2, 3, 1, 1])
            ec1.markdown(f"**{ev.get('name', '')}**")
            ec2.markdown(ev.get("sport", ""))
            ec3.markdown(
                ev.get("date", "")
                + (f" · {days_until}d" if days_until is not None and days_until >= 0 else "")
            )
            ec4.markdown(ev.get("notes", ""))
            if ec5.button("✏️", key=f"edit_ev_{i}", help="Edit"):
                st.session_state.editing_event_idx = i
                st.rerun()
            if ec6.button("✕", key=f"del_ev_{i}", help="Remove"):
                st.session_state.events_draft.pop(i)
                if st.session_state.editing_event_idx == i:
                    st.session_state.editing_event_idx = None
                st.rerun()

            # Inline edit form for this event
            if st.session_state.editing_event_idx == i:
                with st.form(f"edit_event_{i}_form"):
                    fc1, fc2, fc3 = st.columns([2, 1, 1])
                    with fc1:
                        new_name = st.text_input("Name", value=ev.get("name", ""))
                    with fc2:
                        cur_sport = ev.get("sport", "Cycling")
                        new_sport = st.selectbox(
                            "Sport", SPORT_OPTIONS,
                            index=SPORT_OPTIONS.index(cur_sport) if cur_sport in SPORT_OPTIONS else 0,
                        )
                    with fc3:
                        try:
                            ev_date_val = date.fromisoformat(str(ev.get("date", date.today())))
                        except ValueError:
                            ev_date_val = date.today()
                        new_date = st.date_input("Date", value=ev_date_val)
                    new_notes = st.text_input("Notes", value=ev.get("notes", ""))
                    sc1, sc2 = st.columns(2)
                    with sc1:
                        if st.form_submit_button("Save", type="primary"):
                            if new_name.strip():
                                st.session_state.events_draft[i] = {
                                    "name":  new_name.strip(),
                                    "date":  str(new_date),
                                    "sport": new_sport,
                                    "notes": new_notes.strip(),
                                }
                                st.session_state.editing_event_idx = None
                                st.rerun()
                    with sc2:
                        if st.form_submit_button("Cancel"):
                            st.session_state.editing_event_idx = None
                            st.rerun()
    else:
        st.caption("No upcoming events added yet.")

    st.markdown("**Add event**")
    with st.form("add_event_form", clear_on_submit=True):
        fc1, fc2, fc3 = st.columns([3, 2, 2])
        with fc1:
            ev_name = st.text_input("Name", placeholder="Cascade Century")
        with fc2:
            ev_sport = st.selectbox("Sport", SPORT_OPTIONS)
        with fc3:
            ev_date = st.date_input("Date", value=date.today() + timedelta(days=60))
        ev_notes = st.text_input("Notes (optional)", placeholder="Target time, priority…")

        if st.form_submit_button("Add event"):
            if ev_name.strip():
                st.session_state.events_draft.append({
                    "name":  ev_name.strip(),
                    "date":  str(ev_date),
                    "sport": ev_sport,
                    "notes": ev_notes.strip(),
                })
                st.rerun()
            else:
                st.warning("Event name is required.")

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🚴 Training Coach")
    st.divider()
    page = st.radio(
        "page",
        ["Weekly Plan", "Plan History", "Profile & Goals"],
        label_visibility="collapsed",
    )
    st.divider()
    # TODO Phase 6: Replace with Strava OAuth flow for multi-user support.
    # For now, single-user mode reads STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET,
    # and STRAVA_REFRESH_TOKEN from the .env file.
    st.caption("🔒 Single-user · Strava via .env")

# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

if page == "Weekly Plan":
    render_weekly_plan()
elif page == "Plan History":
    render_plan_history()
else:
    render_profile()
