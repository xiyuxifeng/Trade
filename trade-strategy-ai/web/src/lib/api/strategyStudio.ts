import { fetchJson } from './http';
import type {
  ActiveTraderFilterRequest,
  CandidateCreateRequest,
  CandidateCreateResponse,
  RulePoolBatchReviewRequest,
  RulePoolDetailResponse,
  RulePoolListResponse,
  RulePoolReviewRequest,
  RuleValidationItem,
  StrategyVersionDetailResponse,
  StrategyVersionListResponse,
} from '@/types/strategyStudio';

type StrategyVersionQuery = {
  trader_id?: string;
  status?: string;
  version_type?: string;
  date_from?: string;
  date_to?: string;
  skip?: number;
  limit?: number;
};

type RulePoolQuery = {
  status?: string;
  rule_type?: string;
  mapping_status?: string;
  source_type?: string;
  instrument_focus?: string;
  skip_no_mapped?: boolean;
  skip?: number;
  limit?: number;
};

type RuleValidationAdviceRequest = RuleValidationItem[];

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

export function listStrategyVersions(query: StrategyVersionQuery = {}) {
  const suffix = buildQueryString(query);
  return fetchJson<StrategyVersionListResponse>(`/strategy-studio/versions${suffix ? `?${suffix}` : ''}`);
}

export function getStrategyVersion(versionId: string) {
  return fetchJson<StrategyVersionDetailResponse>(`/strategy-studio/versions/${versionId}`);
}

export function adviseRuleValidations(request: RuleValidationAdviceRequest) {
  return fetchJson<{ count: number; rule_ids: string[] }>('/strategy-studio/optimize/advise-rule-validations', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function filterActiveTraders(request: ActiveTraderFilterRequest) {
  return fetchJson<Record<string, unknown>>('/strategy-studio/optimize/filter-active-traders', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function createCandidateVersion(request: CandidateCreateRequest) {
  return fetchJson<CandidateCreateResponse>('/strategy-studio/optimize/create-candidate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function listStrategyRules(query: RulePoolQuery = {}) {
  const suffix = buildQueryString(query);
  return fetchJson<RulePoolListResponse>(`/strategy-studio/rule-pool${suffix ? `?${suffix}` : ''}`);
}

export function getStrategyRule(ruleId: string) {
  return fetchJson<RulePoolDetailResponse>(`/strategy-studio/rule-pool/${ruleId}`);
}

export function reviewStrategyRule(ruleId: string, request: RulePoolReviewRequest) {
  return fetchJson<Record<string, unknown>>(`/strategy-studio/rule-pool/${ruleId}/review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function reviewStrategyRuleBatch(request: RulePoolBatchReviewRequest) {
  return fetchJson<Record<string, unknown>>('/strategy-studio/rule-pool/review-batch', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
