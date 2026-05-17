import type { JobAuditDetailResponse, JobAuditListResponse } from '@/types/job-audits';
import { fetchJson } from './http';

type JobAuditsQuery = {
  actor?: string;
  job_type?: string;
  operation?: string;
  start_date?: string;
  end_date?: string;
  confirmed?: boolean | null;
  skip?: number;
  limit?: number;
};

export function listJobAudits(query: JobAuditsQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<JobAuditListResponse>(`/job-audits${suffix}`);
}

export function getJobAuditDetail(jobId: string) {
  return fetchJson<JobAuditDetailResponse>(`/job-audits/${jobId}`);
}
