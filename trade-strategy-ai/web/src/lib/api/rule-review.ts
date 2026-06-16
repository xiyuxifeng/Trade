import { fetchJson } from './http';
import type {
  RuleReviewActionRequest,
  RuleReviewActionResult,
  RuleReviewCandidateDetail,
  RuleReviewCandidateListResponse,
} from '@/types/rule-review';

function buildQueryString(params: Record<string, string | boolean | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === false) {
      return;
    }
    query.set(key, String(value));
  });
  return query.toString();
}

export function listRuleReviewCandidates(params: {
  require_human_review_only?: boolean;
  automatic_review_status?: string;
} = {}) {
  const suffix = buildQueryString(params);
  return fetchJson<RuleReviewCandidateListResponse>(`/rule-review/candidates${suffix ? `?${suffix}` : ''}`);
}

export function getRuleReviewCandidate(candidateId: string) {
  return fetchJson<RuleReviewCandidateDetail>(`/rule-review/candidates/${candidateId}`);
}

export function submitRuleReviewAction(candidateId: string, request: RuleReviewActionRequest) {
  return fetchJson<RuleReviewActionResult>(`/rule-review/candidates/${candidateId}/actions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
