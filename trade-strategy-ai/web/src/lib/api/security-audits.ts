import type { PermissionDeniedLogResponse } from '@/types/security-audits';
import { fetchJson } from './http';

type PermissionDeniedLogQuery = {
  actor?: string;
  source?: string;
  path?: string;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
};

export function listPermissionDeniedLogs(query: PermissionDeniedLogQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<PermissionDeniedLogResponse>(`/security/permission-denied${suffix}`);
}
