import type {
  SystemDashboardResponse,
  SystemDataOperationListResponse,
  SystemDataOperationMutationResponse,
  SystemDataOperationRequest,
  SystemDataReadinessResponse,
  SystemDataScheduleResponse,
  SystemStatusResponse,
} from '@/types/system';
import { fetchJson } from './http';

export function getSystemStatus() {
  return fetchJson<SystemStatusResponse>('/system/status');
}

export function getSystemDashboard() {
  return fetchJson<SystemDashboardResponse>('/system/dashboard');
}

export function getSystemDataReadiness() {
  return fetchJson<SystemDataReadinessResponse>('/system/data/readiness');
}

export function getSystemDataSchedule() {
  return fetchJson<SystemDataScheduleResponse>('/system/data/schedule');
}

export function listSystemDataOperations(limit = 20, offset = 0) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return fetchJson<SystemDataOperationListResponse>(`/system/data/operations?${query.toString()}`);
}

export function createSystemDataOperation(payload: SystemDataOperationRequest) {
  return fetchJson<SystemDataOperationMutationResponse>('/system/data/operations', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function cancelSystemDataOperation(operationId: string, reason?: string) {
  return fetchJson<SystemDataOperationMutationResponse>(`/system/data/operations/${operationId}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

export function retrySystemDataOperation(operationId: string, reason?: string) {
  return fetchJson<SystemDataOperationMutationResponse>(`/system/data/operations/${operationId}/retry`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

export function resumeSystemDataOperation(operationId: string) {
  return fetchJson<SystemDataOperationMutationResponse>(`/system/data/operations/${operationId}/resume`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}
