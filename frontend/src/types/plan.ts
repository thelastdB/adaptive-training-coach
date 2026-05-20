export type Intensity = 'easy' | 'moderate' | 'hard';
export type SignalStatus = 'green' | 'amber' | 'red';

export interface ActivityDay {
  day: string;
  activity_type: string;
  duration_minutes: number;
  intensity: Intensity;
  description: string;
  is_fixed: boolean;
  is_stale: boolean;
  weather_note?: string;
  time_of_day?: string;
}

export interface Signal {
  label: string;
  text: string;
  status: SignalStatus;
}

export interface Assessment {
  volume: Signal;
  sport_balance: Signal;
  progression: Signal;
  event_readiness: Signal;
}

// Field names match the API's ComputedPlanWeek response exactly.
// Previously used week_id/week_start (aspirational names), but the API
// returns id (integer PK) and week_start_date (ISO date string).
export interface PlanWeek {
  id: number;
  week_start_date: string;
  focus: string;
  event_name?: string | null;
  days_to_event?: number | null;
  days: ActivityDay[];
  assessment: Assessment | null;
}
