import { fetchJson, fetchRootJson, fetchRootText } from './http';
import type {
  BacktestJobSubmission,
  BacktestResultResponse,
  BacktestResultsResponse,
  BacktestSummary,
  FormalApplicabilityDraftRequest,
  FormalApplicabilityProfile,
  FormalApplicabilityReviewRequest,
  FormalBacktestDependencyResult,
  FormalBacktestResult,
  FormalBacktestRun,
  FormalBacktestRunCreateRequest,
  FormalBacktestSelection,
} from '@/types/backtests';

type BacktestResultsQuery = {
  trader_id?: string;
  date_from?: string;
  date_to?: string;
  skip?: number;
  limit?: number;
};

export function listBacktestResults(query: BacktestResultsQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchRootJson<BacktestResultsResponse>(`/backtest_results/${suffix}`);
}

export function getBacktestResult(resultId: string) {
  return fetchRootJson<BacktestResultResponse>(`/backtest_results/${resultId}`);
}

export function downloadBacktestReport(resultId: string) {
  return fetchRootText(`/backtest_results/${resultId}/report`);
}

export function downloadBacktestValidationReport(resultId: string) {
  return fetchRootText(`/backtest_results/${resultId}/validate_rules`);
}

export function checkFormalBacktestDependencies(selection: FormalBacktestSelection) {
  return fetchJson<FormalBacktestDependencyResult>('/rules/backtests/dependency-check', {
    method: 'POST',
    body: JSON.stringify(selection),
  });
}

export function createFormalBacktestRun(request: FormalBacktestRunCreateRequest) {
  return fetchJson<FormalBacktestRun>('/rules/backtests/runs', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export function getFormalBacktestRun(runId: string) {
  return fetchJson<FormalBacktestRun>(`/rules/backtests/runs/${runId}`);
}

export function executeFormalBacktestRun(runId: string) {
  return fetchJson<FormalBacktestResult>(`/rules/backtests/runs/${runId}/execute`, {
    method: 'POST',
  });
}

export function getFormalBacktestResult(runId: string) {
  return fetchJson<FormalBacktestResult>(`/rules/backtests/runs/${runId}/result`);
}

export function generateFormalApplicabilityProfileDraft(runId: string, request: FormalApplicabilityDraftRequest) {
  return fetchJson<FormalApplicabilityProfile>(`/rules/backtests/runs/${runId}/applicability-profiles`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export function reviewFormalApplicabilityProfile(profileId: string, request: FormalApplicabilityReviewRequest) {
  return fetchJson<FormalApplicabilityProfile>(`/rules/backtests/applicability-profiles/${profileId}/review`, {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export function buildBacktestRunParams(submission: BacktestJobSubmission): Record<string, unknown> {
  const params: Record<string, unknown> = {
    profile_id: submission.profileId || undefined,
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  };
  return params;
}

export function buildBacktestValidateRulesParams(submission: BacktestJobSubmission): Record<string, unknown> {
  const params: Record<string, unknown> = {
    profile_id: submission.profileId || undefined,
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  };
  return params;
}

export function buildBacktestReproducibilityParams(submission: BacktestJobSubmission): Record<string, unknown> {
  return buildBacktestRunParams(submission);
}

export type RulePoolBacktestSubmission = {
  ruleId?: string;
  startDate: string;
  endDate: string;
  minConfidence?: number;
  marketRegimeVersion?: string;
};

export function buildRulePoolBacktestParams(submission: RulePoolBacktestSubmission): Record<string, unknown> {
  return {
    rule_id: submission.ruleId || undefined,
    start_date: submission.startDate,
    end_date: submission.endDate,
    min_confidence: submission.minConfidence ?? 0.5,
    market_regime_version: submission.marketRegimeVersion || 'market-regime-v3',
  };
}

export type { BacktestSummary };
