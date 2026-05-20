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

export interface PlanWeek {
  week_id: string;
  week_start: string;
  focus: string;
  event_name?: string;
  days_to_event?: number;
  days: ActivityDay[];
  assessment: Assessment;
}
