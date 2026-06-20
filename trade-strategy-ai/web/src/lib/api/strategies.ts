import { fetchJson } from './http';
import type {
  StrategyDraftOptionsResponse,
  StrategyDraftRequest,
  StrategyListResponse,
  StrategyTransitionRequest,
  StrategyTransitionResponse,
  StrategyVersion,
} from '@/types/strategies';

export function listStrategies() {
  return fetchJson<StrategyListResponse>('/strategies', { method: 'GET' });
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
