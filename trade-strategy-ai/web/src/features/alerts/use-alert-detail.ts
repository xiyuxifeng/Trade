import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/lib/api/http';
import { acknowledgeAlert, getAlertHistory, resolveAlert } from '@/lib/api/alerts';
import type { AlertHistoryItem } from '@/types/alerts';

export function useAlertDetail(recordId: string) {
  const queryClient = useQueryClient();

  const detailQuery = useQuery<AlertHistoryItem, ApiError>({
    queryKey: ['alerts', 'detail', recordId],
    queryFn: () => getAlertHistory(recordId),
    enabled: Boolean(recordId),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: () => acknowledgeAlert(recordId, 'web'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: () => resolveAlert(recordId, 'web'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  return {
    detailQuery,
    acknowledgeMutation,
    resolveMutation,
  };
}

