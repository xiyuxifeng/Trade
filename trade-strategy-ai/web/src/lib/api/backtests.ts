import { API_KEY_STORAGE_KEY } from './http';
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

function buildHeaders(accept: string) {
  const headers: Record<string, string> = {
    Accept: accept,
  };
  if (typeof window !== 'undefined') {
    const apiKey = window.localStorage.getItem(API_KEY_STORAGE_KEY);
    if (apiKey) {
      headers['X-API-Key'] = apiKey;
    }
  }
  return headers;
}

async function fetchRootJson<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: buildHeaders('application/json'),
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'Backtest request failed');
  }
  return (await response.json()) as T;
}

async function fetchRootText(path: string): Promise<string> {
  const response = await fetch(path, {
    headers: buildHeaders('text/markdown, text/plain;q=0.9, */*;q=0.8'),
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'Backtest report load failed');
  }
  return response.text();
}

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
    mode: submission.mode,
    config_path: submission.configPath,
  };
}

export function buildBacktestValidateRulesParams(submission: BacktestJobSubmission): Record<string, unknown> {
  return {
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    config_path: submission.configPath,
  };
}

export function buildBacktestReproducibilityParams(submission: BacktestJobSubmission): Record<string, unknown> {
  return buildBacktestRunParams(submission);
}

export type { BacktestSummary };
