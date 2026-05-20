import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type { PlanWeek } from '../types/plan';

export function usePlanWeek(weekId: string) {
  return useQuery<PlanWeek>({
    queryKey: ['plan', weekId],
    queryFn: () => api.get(`/plan/${weekId}`).then((r) => r.data),
    retry: false,
  });
}

export function usePlan() {
  return useQuery<PlanWeek>({
    queryKey: ['plan', 'current'],
    queryFn: () => api.get('/plan/current').then((r) => r.data),
    retry: false,
  });
}

export function useGeneratePlan() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mode?: 'fill' | 'fresh') =>
      api.post('/plan/generate', mode ? { mode } : {}).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plan', 'current'] }),
  });
}

export function useMoveActivity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      weekId,
      toDay,
      fromDay,
    }: {
      weekId: number;
      toDay: string;
      fromDay: string;
    }) =>
      api
        .patch(`/plan/${weekId}/activity/${toDay}`, { from_day: fromDay })
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plan', 'current'] }),
  });
}
