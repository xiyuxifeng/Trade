import { fetchRootJson, fetchRootText } from './http';
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
  return fetchRootText(`/reports/${kind}/${date}/html`);
}
