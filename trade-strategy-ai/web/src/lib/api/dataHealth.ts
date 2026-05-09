import { fetchJson } from './http';
import type { DashboardReportResponse } from '@/types/dataHealth';

export function buildDashboardReport() {
  return fetchJson<DashboardReportResponse>('/data-health/dashboard');
}
