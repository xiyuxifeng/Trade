import { buildApiHeaders, fetchJson, getApiBaseUrl } from './http';
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
  return fetchJson<ReportListResponse>(`/reports/daily?${params.toString()}`);
}

export function getDailyReport(date: string) {
  return fetchJson<DailyReportDetail>(`/reports/daily/${date}`);
}

export async function downloadDailyReportHtml(date: string) {
  return fetchReportHtml('daily', date);
}

export function listEvaluationReports(skip = 0, limit = 50) {
  const params = new URLSearchParams({
    skip: String(skip),
    limit: String(limit),
  });
  return fetchJson<ReportListResponse>(`/reports/evaluation?${params.toString()}`);
}

export function getEvaluationReport(date: string) {
  return fetchJson<EvaluationResultDetail>(`/reports/evaluation/${date}`);
}

export async function downloadEvaluationHtml(date: string) {
  return fetchReportHtml('evaluation', date);
}

async function fetchReportHtml(kind: ReportKind, date: string) {
  const headers = buildApiHeaders();
  headers.set('Accept', 'text/html');

  const response = await fetch(`${getApiBaseUrl()}/reports/${kind}/${date}/html`, {
    headers,
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'Report HTML load failed');
  }
  return response.text();
}
