import { fetchJson } from './http';
import type { DataAuditsResponse } from '@/types/dataAudits';

type DataAuditQuery = {
  event_type?: string;
  actor?: string;
  source?: string;
  entity_type?: string;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
};

export function listDataAudits(query: DataAuditQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<DataAuditsResponse>(`/data-audits${suffix}`);
}
