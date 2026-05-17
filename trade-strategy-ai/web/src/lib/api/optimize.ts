import { fetchJson } from './http';
import type {
  OptimizeActiveTraderFilterRequest,
  OptimizeCandidateCreateRequest,
  OptimizeCandidateCreateResponse,
  OptimizeRuleValidationItem,
  OptimizeVersionDetailResponse,
  OptimizeVersionListResponse,
  OptimizeVersionQuery,
} from '@/types/optimize';

function buildQueryString(params: Record<string, string | number | boolean | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === false) {
      return;
    }
    query.set(key, String(value));
  });
  return query.toString();
}

export function listOptimizeVersions(query: OptimizeVersionQuery = {}) {
  const suffix = buildQueryString(query);
  return fetchJson<OptimizeVersionListResponse>(`/optimize/versions${suffix ? `?${suffix}` : ''}`);
}

export function getOptimizeVersion(versionId: string) {
  return fetchJson<OptimizeVersionDetailResponse>(`/optimize/versions/${versionId}`);
}

export function adviseOptimizeRuleValidations(request: OptimizeRuleValidationItem[]) {
  return fetchJson<{ count: number; rule_ids: string[] }>('/optimize/advise-rule-validations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function filterOptimizeActiveTraders(request: OptimizeActiveTraderFilterRequest) {
  return fetchJson<Record<string, unknown>>('/optimize/filter-active-traders', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function createOptimizeCandidateVersion(request: OptimizeCandidateCreateRequest) {
  return fetchJson<OptimizeCandidateCreateResponse>('/optimize/create-candidate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

