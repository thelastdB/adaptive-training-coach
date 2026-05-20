# eigentakt — Phase 7 Architecture
> FastAPI backend + React frontend replacing the Streamlit prototype.
> Canonical reference for all Claude Code sessions.

---

## Repository Structure

```
adaptive-training-coach/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py           # App init, CORS, router registration
│   │   ├── deps.py           # Shared dependencies (get_current_user)
│   │   ├── routers/
│   │   │   ├── auth.py       # /auth/*
│   │   │   ├── plan.py       # /plan/*
│   │   │   ├── activities.py # /activities/*
│   │   │   ├── goals.py      # /goals, /preferences/*
│   │   │   └── weather.py    # /weather
│   │   └── models/           # Pydantic request/response schemas
│   ├── Procfile              # Railway: uvicorn app.main:app ...
│   ├── railway.toml
│   └── requirements.txt
├── frontend/                 # React application
│   ├── src/
│   │   ├── styles/
│   │   │   ├── tokens.css    # All --et-* CSS custom properties
│   │   │   └── global.css    # Reset + base styles + fonts
│   │   ├── lib/
│   │   │   ├── api.ts        # Axios instance + JWT interceptor
│   │   │   └── auth.ts       # JWT helpers
│   │   ├── components/
│   │   │   ├── brand/        # Logo.tsx, Mark.tsx
│   │   │   ├── layout/       # AppShell, TopBar, Sidebar, BottomTabBar
│   │   │   ├── week/         # WeekView, WeekHeader, WeekGrid, DayColumn, AssessmentBanner
│   │   │   ├── cards/        # ActivityCard, EmptySlot, RestSlot, IntensityBadge
│   │   │   └── ui/           # Button, SplitButton, Dropdown, Tooltip
│   │   ├── hooks/
│   │   │   ├── usePlan.ts
│   │   │   ├── useActivities.ts
│   │   │   ├── useWeather.ts
│   │   │   └── useDragAndDrop.ts
│   │   ├── stores/
│   │   │   └── uiStore.ts    # Zustand: sidebar open, modals, drag state
│   │   └── pages/
│   │       ├── Landing.tsx
│   │       ├── Onboarding.tsx
│   │       ├── WeekView.tsx
│   │       ├── Goals.tsx
│   │       ├── WeeklyTemplate.tsx
│   │       └── Profile.tsx
│   ├── vercel.json
│   └── vite.config.ts
└── docs/
    └── phase7/
        ├── architecture.md   # this file
        ├── session1.md
        ├── session2.md
        ├── session3.md
        ├── session4.md
        └── session5.md
```

---

## API Surface

All endpoints are prefixed `/api/v1`. Auth is JWT Bearer token issued on Strava OAuth callback.

### Auth

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/strava` | Initiate Strava OAuth (redirect) |
| GET | `/auth/strava/callback` | OAuth callback — exchange code, return JWT |
| GET | `/auth/me` | Current user profile |
| POST | `/auth/logout` | Invalidate session |

### Activities

| Method | Path | Description |
|--------|------|-------------|
| GET | `/activities/sync` | Trigger Strava sync for current user |
| GET | `/activities` | Paginated activity list |
| GET | `/activities/summary` | HR zones, volume, fitness summary |

### Plan

| Method | Path | Description |
|--------|------|-------------|
| GET | `/plan/current` | Current week plan |
| POST | `/plan/generate` | Generate or regenerate plan |
| PATCH | `/plan/{week_id}/activity/{day}` | Move or edit a single activity |
| DELETE | `/plan/{week_id}/activity/{day}` | Remove an activity |
| POST | `/plan/{week_id}/evaluate` | Run eval framework, return scores |
| GET | `/plan/history` | Past weeks (paginated) |

### Goals & Preferences

| Method | Path | Description |
|--------|------|-------------|
| GET | `/goals` | Current goals + target events |
| PUT | `/goals` | Update goals |
| GET | `/preferences/schedule` | Weekly availability template |
| PUT | `/preferences/schedule` | Update weekly template |

### Weather

| Method | Path | Description |
|--------|------|-------------|
| GET | `/weather` | Current week forecast (used internally by plan generator) |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Returns `{ status: "ok" }` |

---

## Key Pydantic Models

```python
# plan.py models

class ActivityDay(BaseModel):
    day: str                    # "monday" ... "sunday"
    activity_type: str          # "run", "ride", "swim", "rest"
    duration_minutes: int
    intensity: str              # "easy", "moderate", "hard"
    description: str
    is_fixed: bool
    is_stale: bool
    weather_note: str | None

class PlanWeek(BaseModel):
    week_id: str
    week_start: date
    focus: str                  # e.g. "peak build"
    event_name: str | None
    days_to_event: int | None
    days: list[ActivityDay]
    assessment: Assessment

class Assessment(BaseModel):
    volume: Signal
    sport_balance: Signal
    progression: Signal
    event_readiness: Signal

class Signal(BaseModel):
    label: str
    text: str
    status: Literal["green", "amber", "red"]

# goals.py models

class Goal(BaseModel):
    type: Literal["target_event", "build_base", "return_to_training"]
    event: TargetEvent | None

class TargetEvent(BaseModel):
    name: str
    date: date
    sport: str
    distance_km: float | None

# preferences/schedule models

class DayAvailability(BaseModel):
    enabled: bool
    duration_minutes: int

class FixedCommitment(BaseModel):
    day: str
    time: str                   # "07:00"
    duration_minutes: int
    label: str

class WeeklySchedule(BaseModel):
    days: dict[str, DayAvailability]   # keyed by day name
    fixed_commitments: list[FixedCommitment]
```

---

## Frontend Architecture

### Stack

| Concern | Library |
|---------|---------|
| Build | Vite + React 18 + TypeScript |
| Routing | TanStack Router (file-based) |
| Server state | TanStack Query |
| Client state | Zustand |
| Drag-and-drop | @dnd-kit/core + @dnd-kit/sortable |
| HTTP | Axios |
| Styling | CSS custom properties (no Tailwind, no CSS-in-JS) |

### Route Map

```
/                       → Landing
/login                  → Strava connect page
/auth/callback          → OAuth callback handler (redirects to /app/week or /onboarding)
/onboarding             → Multi-step setup (shown once after first login)
/app                    → AppShell (redirect to /app/week)
/app/week               → WeekView (primary screen)
/app/week/:weekId       → Historical week (read-only)
/app/goals              → Goals settings
/app/schedule           → Weekly template settings
/app/profile            → Profile + account settings
```

### CSS Token Reference

All tokens sourced from `eigentakt_calendar_reference.html`. Canonical values:

```css
:root {
  --et-graphite:  #2C2C2A;
  --et-olive:     #4A5C3E;
  --et-olive-dk:  #3A4C2E;
  --et-bone:      #F5F2EC;
  --et-stone:     #6B6B67;
  --et-border:    #D8D4CC;
  --et-card:      #FFFFFF;
  --et-surface:   #EDE9E2;
  --et-amber:     #8A6020;
  --et-red:       #8B3A3A;
  --et-red-bg:    #F5EDED;
  --et-red-border:#D8B4B4;

  /* Signal colors */
  --et-signal-green:  #1E4A14;
  --et-signal-amber:  #5A3A08;
  --et-signal-red:    #5A1A1A;

  /* Intensity badge colors */
  --et-easy-bg:     #D0E8C8;
  --et-easy-text:   #1E4A14;
  --et-mod-bg:      #E8D8A8;
  --et-mod-text:    #5A3A08;
  --et-hard-bg:     #E8C0C0;
  --et-hard-text:   #5A1A1A;
}
```

### Typography

```css
/* Primary UI */
font-family: 'Geist', -apple-system, sans-serif;
/* weights: 400, 500, 600 */

/* Editorial / description text */
font-family: 'Lora', Georgia, serif;
/* weight: 400, italic */

/* Metrics / data */
font-family: 'Geist Mono', monospace;
/* weight: 400 */
```

### Logo SVG Paths (locked)

From `eigentakt_calendar_reference.html`:

```
viewBox: 0 0 160 220
Outer body:  M0,220 L160,220 L104,16 L56,16 Z    fill: --et-olive (light) / --et-bone (dark)
Top cap:     M56,16 L104,16 L98,0 L62,0 Z         fill: --et-olive-dk
Window void: M36,204 L124,204 L96,68 L64,68 Z    fill: background (cutout)
Pendulum:    line x1=80 y1=202 x2=100 y2=76       stroke: --et-olive, width 6
Weight:      rect x=94 y=86 width=13 height=13    fill: --et-olive, rotate 45deg
```

### Card States

| State | Border | Badge |
|-------|--------|-------|
| Default | `0.5px solid --et-border` | none |
| Fixed | `1px solid --et-olive` | lock icon top-right |
| Stale | `1px dashed --et-amber` | refresh badge top-right |
| Empty | `0.5px dashed #B8B4AC` | "Add or Generate" affordance |
| Rest | none | quiet "Rest" label |

---

## Mobile Breakpoints

- `max-width: 768px` — single column grid, hide sidebar, show BottomTabBar
- `max-width: 480px` — SplitButton collapses to wand icon only

---

## Drag-and-Drop Rules

- Fixed cards cannot be dragged
- Valid drop target: `--et-olive` border highlight
- Invalid drop target: `--et-amber` border highlight
- Cross-day drop: marks card stale, calls `PATCH /plan/{weekId}/activity/{day}`
- Mobile: tap-hold to lift (pointer/touch events), not HTML5 drag API

---

## Auth Flow

```
User → /login
     → GET /auth/strava (backend redirects to Strava)
     → Strava OAuth consent
     → GET /auth/strava/callback
     → Backend exchanges code, issues JWT
     → Redirect to /app/week (existing user) or /onboarding (new user)
```

JWT stored in `localStorage`. Axios interceptor attaches `Authorization: Bearer <token>` to all API requests. On 401, clear token and redirect to `/login`.

---

## Environment Variables

### Backend (Railway)

```
SUPABASE_URL
SUPABASE_KEY
STRAVA_CLIENT_ID
STRAVA_CLIENT_SECRET
JWT_SECRET
CORS_ORIGINS          # comma-separated, e.g. https://eigentakt.vercel.app
```

### Frontend (Vercel)

```
VITE_API_URL          # e.g. https://eigentakt-api.railway.app/api/v1
```

---

## Deployment

### Railway (FastAPI)

```toml
# railway.toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```

### Vercel (React)

```json
// vercel.json
{
  "rewrites": [
    { "source": "/app/:path*", "destination": "/index.html" },
    { "source": "/onboarding", "destination": "/index.html" },
    { "source": "/auth/:path*", "destination": "/index.html" }
  ]
}
```

---

## Design References

All design files live in `/design-reference/` in the repo root. Claude Code sessions should read these directly.

| File | Purpose |
|------|---------|
| `eigentakt_calendar_reference.html` | Primary UI baseline — tokens, card states, layout |
| `eigentakt_landing.html` | Landing page baseline |
| `eigentakt_onboarding.html` | Onboarding flow baseline |
| `eigentakt_goals_settings.html` | Goals page baseline |
| `eigentakt_weekly_template.html` | Weekly template page baseline |
| `eigentakt_profile_settings.html` | Profile page baseline |
| `eigentakt_mobile_spec.md` | Mobile layout rules |
| `eigentakt_brand_system.md` | Brand values, tone, motion direction |