import type { JobsListResponse } from '@/types/jobs';
import { fetchJson } from './http';

type JobsQuery = {
  status?: string;
  job_type?: string;
  created_by?: string;
  skip?: number;
  limit?: number;
};

export function listJobs(query: JobsQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<JobsListResponse>(`/jobs${suffix}`);
}
