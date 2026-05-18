import { fetchRootJson, fetchRootText } from './http';
import type {
  BacktestJobSubmission,
  BacktestResultResponse,
  BacktestResultsResponse,
  BacktestSummary,
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

export function buildBacktestRunParams(submission: BacktestJobSubmission): Record<string, unknown> {
  return {
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    config_path: submission.configPath,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  };
}

export function buildBacktestValidateRulesParams(submission: BacktestJobSubmission): Record<string, unknown> {
  return {
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    config_path: submission.configPath,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  };
}

export function buildBacktestReproducibilityParams(submission: BacktestJobSubmission): Record<string, unknown> {
  return buildBacktestRunParams(submission);
}

export type { BacktestSummary };
