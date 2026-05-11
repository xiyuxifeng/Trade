import type { SystemDashboardResponse, SystemStatusResponse } from '@/types/system';
import { fetchJson } from './http';

export function getSystemStatus() {
  return fetchJson<SystemStatusResponse>('/system/status');
}

export function getSystemDashboard() {
  return fetchJson<SystemDashboardResponse>('/system/dashboard');
}
