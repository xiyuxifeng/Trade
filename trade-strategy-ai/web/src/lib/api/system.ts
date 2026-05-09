import type { SystemStatusResponse } from '@/types/system';
import { fetchJson } from './http';

export function getSystemStatus() {
  return fetchJson<SystemStatusResponse>('/system/status');
}
