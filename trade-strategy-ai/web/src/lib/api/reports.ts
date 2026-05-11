import { buildApiHeaders } from './http';
import type {
  DailyReportDetail,
  EvaluationResultDetail,
  ReportListResponse,
  ReportKind,
} from '@/types/reports';

export function listDailyReports(skip = 0, limit = 50) {
  const params = new URLSearchParams({
    skip: String(skip),
    limit: String(limit),
  });
  return fetchRootJson<ReportListResponse>(`/reports/daily?${params.toString()}`);
}

export function getDailyReport(date: string) {
  return fetchRootJson<DailyReportDetail>(`/reports/daily/${date}`);
}

export async function downloadDailyReportHtml(date: string) {
  return fetchReportHtml('daily', date);
}

export function listEvaluationReports(skip = 0, limit = 50) {
  const params = new URLSearchParams({
    skip: String(skip),
    limit: String(limit),
  });
  return fetchRootJson<ReportListResponse>(`/reports/evaluation?${params.toString()}`);
}

export function getEvaluationReport(date: string) {
  return fetchRootJson<EvaluationResultDetail>(`/reports/evaluation/${date}`);
}

export async function downloadEvaluationHtml(date: string) {
  return fetchReportHtml('evaluation', date);
}

async function fetchReportHtml(kind: ReportKind, date: string) {
  const headers = buildApiHeaders();
  headers.set('Accept', 'text/html');

  const response = await fetch(`/reports/${kind}/${date}/html`, {
    headers,
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'Report HTML load failed');
  }
  return response.text();
}

async function fetchRootJson<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = buildApiHeaders(init?.headers);
  headers.set('Accept', 'application/json');

  const response = await fetch(path, {
    ...init,
    headers,
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'Report request failed');
  }
  return (await response.json()) as T;
}
