import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import type { WeeklySchedule } from '../types/schedule';

export function useSchedule() {
  return useQuery<WeeklySchedule>({
    queryKey: ['preferences', 'schedule'],
    queryFn: () => api.get('/preferences/schedule').then((r) => r.data),
    retry: false,
  });
}

export function useSaveSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (schedule: WeeklySchedule) =>
      api.put('/preferences/schedule', schedule).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['preferences', 'schedule'] }),
  });
}
