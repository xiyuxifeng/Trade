import { fetchJson } from './http';
import type {
  DailyRuleSelectionResponse,
  PreMarketReadinessResponse,
  TradingDayPlanResponse,
  TradingDayPlanReviewRequest,
} from '@/types/daily';

export function getPreMarketReadiness(tradeDate: string) {
  const params = new URLSearchParams({ trade_date: tradeDate });
  return fetchJson<PreMarketReadinessResponse>(`/daily/pre-market/readiness?${params.toString()}`, { method: 'GET' });
}

export function getDailyRuleSelection(tradeDate: string) {
  const params = new URLSearchParams({ trade_date: tradeDate });
  return fetchJson<DailyRuleSelectionResponse>(`/daily/pre-market/rule-selection?${params.toString()}`, { method: 'GET' });
}

export function getTradingDayPlan(tradeDate: string) {
  const params = new URLSearchParams({ trade_date: tradeDate });
  return fetchJson<TradingDayPlanResponse>(`/daily/pre-market/plan?${params.toString()}`, { method: 'GET' });
}

export function reviewTradingDayPlan(tradeDate: string, request: TradingDayPlanReviewRequest) {
  const params = new URLSearchParams({ trade_date: tradeDate });
  return fetchJson<TradingDayPlanResponse>(`/daily/pre-market/plan/review?${params.toString()}`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
