import { fetchJson } from './http';
import type { MarketStateBuildRequest, MarketStateBuildResponse } from '@/types/market-state';
import type { PersonaClustersResponse } from '@/types/persona';

export function buildSampleClusters() {
  return fetchJson<PersonaClustersResponse>('/persona/sample', {
    method: 'POST',
  });
}

export function buildMarketState(payload: MarketStateBuildRequest) {
  return fetchJson<MarketStateBuildResponse>('/persona/market-state/build', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}
