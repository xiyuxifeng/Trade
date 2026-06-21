import { fetchJson } from './http';
import type { PreMarketReadinessResponse } from '@/types/daily';

export function getPreMarketReadiness(tradeDate: string) {
  const params = new URLSearchParams({ trade_date: tradeDate });
  return fetchJson<PreMarketReadinessResponse>(`/daily/pre-market/readiness?${params.toString()}`, { method: 'GET' });
}
