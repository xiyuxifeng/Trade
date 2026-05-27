import { fetchRootJson } from './http';
import type {
  AlertActionResponse,
  AlertHistoryQuery,
  AlertHistoryItem,
  AlertHistoryResponse,
  AlertingStatusResponse,
} from '@/types/alerts';

export function listAlertHistory(query: AlertHistoryQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchRootJson<AlertHistoryResponse>(`/alerts/history${suffix}`);
}

export function getAlertHistory(recordId: string) {
  return fetchRootJson<AlertHistoryItem>(`/alerts/history/${recordId}`);
}

export function getAlertingStatus() {
  return fetchRootJson<AlertingStatusResponse>('/alerts/status');
}

export function acknowledgeAlert(recordId: string, acknowledgedBy = 'web') {
  return fetchRootJson<AlertActionResponse>(`/alerts/${recordId}/acknowledge`, {
    method: 'POST',
    body: JSON.stringify({ acknowledged_by: acknowledgedBy }),
  });
}

export function resolveAlert(recordId: string, resolvedBy = 'web') {
  return fetchRootJson<AlertActionResponse>(`/alerts/${recordId}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ resolved_by: resolvedBy }),
  });
}

export function sendTestAlert() {
  return fetchRootJson<{ status: string; message: string }>('/alerts/test', {
    method: 'POST',
  });
}
