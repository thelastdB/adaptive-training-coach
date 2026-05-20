export interface DayAvailability {
  enabled: boolean;
  duration_minutes: number;
}

export interface FixedCommitment {
  day: string;
  time: string;
  duration_minutes: number;
  label: string;
}

export interface WeeklySchedule {
  days: Record<string, DayAvailability>;
  fixed_commitments: FixedCommitment[];
}
