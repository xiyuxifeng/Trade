import type {
  SystemCostControlSummaryResponse,
  SystemDashboardResponse,
  SystemDataOperationListResponse,
  SystemDataOperationMutationResponse,
  SystemDataOperationRequest,
  SystemDataReadinessResponse,
  SystemRolloutSummaryResponse,
  SystemDataScheduleResponse,
  SystemRunTraceListResponse,
  SystemStatusResponse,
} from '@/types/system';
import { fetchJson } from './http';

export function getSystemStatus() {
  return fetchJson<SystemStatusResponse>('/system/status');
}

export function getSystemDashboard() {
  return fetchJson<SystemDashboardResponse>('/system/dashboard');
}

export function listSystemRunTraces({
  limit = 20,
  cursor,
  status = 'all',
  businessType = 'all',
  dateFrom,
  dateTo,
}: {
  limit?: number;
  cursor?: string;
  status?: 'all' | 'needs_attention' | 'failed' | 'partial' | 'ready';
  businessType?: 'all' | 'data' | 'prompt' | 'backtest' | 'pre-market' | 'after-close' | 'daily-rule-selection' | 'trading-plan' | 'system-job';
  dateFrom?: string;
  dateTo?: string;
} = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    status,
    business_type: businessType,
  });
  if (cursor) query.set('cursor', cursor);
  if (dateFrom) query.set('date_from', dateFrom);
  if (dateTo) query.set('date_to', dateTo);
  return fetchJson<SystemRunTraceListResponse>(`/system/runs?${query.toString()}`);
}

export function getSystemCostControlSummary() {
  return fetchJson<SystemCostControlSummaryResponse>('/system/cost-control');
}

export function getSystemRolloutSummary() {
  return fetchJson<SystemRolloutSummaryResponse>('/system/rollout');
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
