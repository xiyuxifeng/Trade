import { fetchJson } from './http';
import type {
  RulePoolBatchReviewRequest,
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

