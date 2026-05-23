import { fetchJson } from './http';
import type { TraderOptionsResponse, TraderOptionsSource } from '@/types/traders';

type TraderOptionsQuery = {
  source?: TraderOptionsSource;
};

export function listTraderOptions(query: TraderOptionsQuery = {}) {
  const params = new URLSearchParams();
  if (query.source) {
    params.set('source', query.source);
  }
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<TraderOptionsResponse>(`/traders${suffix}`);
}
