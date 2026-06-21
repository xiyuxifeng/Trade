import { fetchJson } from './http';
import type {
  StrategyRevisionProposalAcceptRequest,
  StrategyRevisionProposalAcceptResponse,
  StrategyRevisionProposalDetailResponse,
  StrategyRevisionProposalListResponse,
  StrategyRevisionProposalReviewRequest,
  StrategyComparisonResponse,
  StrategyDiffResponse,
  StrategyDraftOptionsResponse,
  StrategyDraftRequest,
  StrategyListResponse,
  StrategyRollbackRequest,
  StrategyTransitionRequest,
  StrategyTransitionResponse,
  StrategyValidationRequest,
  StrategyVersion,
} from '@/types/strategies';

export function listStrategies() {
  return fetchJson<StrategyListResponse>('/strategies', { method: 'GET' });
}

export function listStrategyRevisionProposals() {
  return fetchJson<StrategyRevisionProposalListResponse>('/strategies/proposals', {
    method: 'GET',
  });
}

export function getStrategyRevisionProposal(proposalId: string) {
  return fetchJson<StrategyRevisionProposalDetailResponse>(`/strategies/proposals/${proposalId}`, { method: 'GET' });
}

export function getStrategyDraftOptions() {
  return fetchJson<StrategyDraftOptionsResponse>('/strategies/draft-options', { method: 'GET' });
}

export function createStrategyDraft(payload: StrategyDraftRequest) {
  return fetchJson<StrategyVersion>('/strategies', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function submitStrategyReview(versionId: string, payload: StrategyTransitionRequest) {
  return fetchJson<StrategyTransitionResponse>(`/strategies/${versionId}/submit-review`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function publishStrategy(versionId: string, payload: StrategyTransitionRequest) {
  return fetchJson<StrategyTransitionResponse>(`/strategies/${versionId}/publish`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function validateStrategyVersion(versionId: string, payload: StrategyValidationRequest) {
  return fetchJson<StrategyVersion>(`/strategies/${versionId}/validate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function compareStrategyVersion(versionId: string) {
  return fetchJson<StrategyComparisonResponse>(`/strategies/${versionId}/comparison`, { method: 'GET' });
}

export function diffStrategyVersion(versionId: string, baseVersionId?: string) {
  const suffix = baseVersionId ? `?base_version_id=${encodeURIComponent(baseVersionId)}` : '';
  return fetchJson<StrategyDiffResponse>(`/strategies/${versionId}/diff${suffix}`, { method: 'GET' });
}

export function rollbackStrategyVersion(versionId: string, payload: StrategyRollbackRequest) {
  return fetchJson<StrategyVersion>(`/strategies/${versionId}/rollback`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function reviewStrategyRevisionProposal(proposalId: string, payload: StrategyRevisionProposalReviewRequest) {
  return fetchJson<StrategyRevisionProposalDetailResponse>(`/strategies/proposals/${proposalId}/review`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function acceptStrategyRevisionProposalToDraft(
  proposalId: string,
  payload: StrategyRevisionProposalAcceptRequest,
) {
  return fetchJson<StrategyRevisionProposalAcceptResponse>(`/strategies/proposals/${proposalId}/accept-to-draft`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
