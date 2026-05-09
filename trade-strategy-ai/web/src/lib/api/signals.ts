import { fetchJson } from './http';
import type { SignalListParams, SignalListResponse } from '@/types/signals';

function buildQueryString(params: SignalListParams = {}) {
  const query = new URLSearchParams();
  if (params.symbol) query.set('symbol', params.symbol);
  if (params.since) query.set('since', params.since);
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  return query.toString();
}

export function listSignals(params: SignalListParams = {}) {
  const suffix = buildQueryString(params);
  return fetchJson<SignalListResponse>(suffix ? `/signals?${suffix}` : '/signals');
}
