import { fetchJson } from './http';
import type { DailyRuleSelectionResponse, PreMarketReadinessResponse } from '@/types/daily';

export function getPreMarketReadiness(tradeDate: string) {
  const params = new URLSearchParams({ trade_date: tradeDate });
  return fetchJson<PreMarketReadinessResponse>(`/daily/pre-market/readiness?${params.toString()}`, { method: 'GET' });
}

export function getDailyRuleSelection(tradeDate: string) {
  const params = new URLSearchParams({ trade_date: tradeDate });
  return fetchJson<DailyRuleSelectionResponse>(`/daily/pre-market/rule-selection?${params.toString()}`, { method: 'GET' });
}
