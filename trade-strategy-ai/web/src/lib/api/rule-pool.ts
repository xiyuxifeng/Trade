import { fetchJson } from './http';
import type {
  RuleApplicabilityDetailResponse,
  RuleApplicabilityGenerateRequest,
  RuleApplicabilityListResponse,
  RuleApplicabilityReviewRequest,
  RulePoolBatchReviewRequest,
  RulePoolFilterOptionsResponse,
  RulePoolDetailResponse,
  RulePoolListResponse,
  RulePoolQuery,
  RulePoolReviewRequest,
} from '@/types/rule-pool';

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

export function listRulePool(query: RulePoolQuery = {}) {
  const suffix = buildQueryString(query);
  return fetchJson<RulePoolListResponse>(`/rule-pool${suffix ? `?${suffix}` : ''}`);
}

export function listRulePoolFilterOptions() {
  return fetchJson<RulePoolFilterOptionsResponse>('/rule-pool/filter-options');
}

export function getRulePoolRule(ruleId: string) {
  return fetchJson<RulePoolDetailResponse>(`/rule-pool/${ruleId}`);
}

export function reviewRulePoolRule(ruleId: string, request: RulePoolReviewRequest) {
  return fetchJson<Record<string, unknown>>(`/rule-pool/${ruleId}/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function reviewRulePoolBatch(request: RulePoolBatchReviewRequest) {
  return fetchJson<Record<string, unknown>>('/rule-pool/review-batch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function listRuleApplicabilityProfiles(ruleId: string, query: Record<string, string | number | boolean | undefined> = {}) {
  const suffix = buildQueryString(query);
  return fetchJson<RuleApplicabilityListResponse>(`/rule-pool/${ruleId}/applicability-profiles${suffix ? `?${suffix}` : ''}`);
}

export function getRuleApplicabilityProfile(ruleId: string, profileId: string) {
  return fetchJson<RuleApplicabilityDetailResponse>(`/rule-pool/${ruleId}/applicability-profiles/${profileId}`);
}

export function generateRuleApplicabilityProfile(ruleId: string, request: RuleApplicabilityGenerateRequest) {
  return fetchJson<RuleApplicabilityDetailResponse>(`/rule-pool/${ruleId}/applicability-profiles/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function reviewRuleApplicabilityProfile(ruleId: string, profileId: string, request: RuleApplicabilityReviewRequest) {
  return fetchJson<RuleApplicabilityDetailResponse>(`/rule-pool/${ruleId}/applicability-profiles/${profileId}/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
