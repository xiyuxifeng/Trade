import { fetchJson } from './http';
import type {
  AfterCloseProposalAcceptRequest,
  AfterCloseProposalCollectionResponse,
  AfterCloseProposalReviewRequest,
  AfterCloseReviewResponse,
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

export function getAfterCloseReview(tradingDayPlanId: string, postMarketReviewId?: string | null) {
  const params = new URLSearchParams({ trading_day_plan_id: tradingDayPlanId });
  if (postMarketReviewId) {
    params.set('post_market_review_id', postMarketReviewId);
  }
  return fetchJson<AfterCloseReviewResponse>(`/daily/after-close/review?${params.toString()}`, { method: 'GET' });
}

export function generateAfterCloseProposals(postMarketReviewId: string) {
  return fetchJson<AfterCloseProposalCollectionResponse>('/daily/after-close/proposals/generate', {
    method: 'POST',
    body: JSON.stringify({ post_market_review_id: postMarketReviewId }),
  });
}

export function listAfterCloseProposals(postMarketReviewId: string) {
  const params = new URLSearchParams({ post_market_review_id: postMarketReviewId, limit: '20' });
  return fetchJson<AfterCloseProposalCollectionResponse>(`/daily/after-close/proposals?${params.toString()}`, { method: 'GET' });
}

export function reviewAfterCloseProposal(proposalId: string, request: AfterCloseProposalReviewRequest) {
  return fetchJson(`/daily/after-close/proposals/${proposalId}/review`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export function acceptAfterCloseProposalToDraft(proposalId: string, request: AfterCloseProposalAcceptRequest) {
  return fetchJson(`/daily/after-close/proposals/${proposalId}/accept-to-draft`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}
