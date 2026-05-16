import { useQuery } from '@tanstack/react-query';
import { ApiError } from '@/lib/api/http';
import { listAlertHistory } from '@/lib/api/alerts';
import type { AlertHistoryItem, AlertHistoryResponse } from '@/types/alerts';

function scoreAlert(alert: AlertHistoryItem) {
  const statusScore = (() => {
    if (alert.status === 'pending' || alert.status === 'sent') return 3;
    if (alert.status === 'acknowledged') return 2;
    if (alert.status === 'resolved') return 1;
    return 0;
  })();
  const levelScore = (() => {
    if (alert.level === 'CRITICAL') return 3;
    if (alert.level === 'WARNING') return 2;
    if (alert.level === 'INFO') return 1;
    return 0;
  })();
  return statusScore * 10 + levelScore;
}

function sortDashboardAlerts(items: AlertHistoryItem[]) {
  return [...items].sort((left, right) => {
    const scoreDiff = scoreAlert(right) - scoreAlert(left);
    if (scoreDiff !== 0) return scoreDiff;

    const rightTime = right.created_at ?? right.sent_at ?? '';
    const leftTime = left.created_at ?? left.sent_at ?? '';
    const timeDiff = rightTime.localeCompare(leftTime);
    if (timeDiff !== 0) return timeDiff;

    return right.id.localeCompare(left.id);
  });
}

export function useDashboardAlertSummary() {
  return useQuery<AlertHistoryResponse, ApiError>({
    queryKey: ['dashboard-alert-summary'],
    queryFn: () => listAlertHistory({ limit: 10, skip: 0 }),
    staleTime: 15_000,
    select: (data) => ({
      ...data,
      items: sortDashboardAlerts(data.items).slice(0, 5),
    }),
  });
}

