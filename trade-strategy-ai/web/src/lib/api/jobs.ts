import type {
  JobDefinitionSummary,
  JobDetailResponse,
  JobLogsResponse,
  JobSubmissionRequest,
  JobsListResponse,
} from '@/types/jobs';
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

export function listJobDefinitions() {
  return fetchJson<JobDefinitionSummary[]>(`/jobs/definitions`);
}

export function getJobDefinition(jobType: string) {
  return fetchJson<JobDefinitionSummary>(`/jobs/definitions/${encodeURIComponent(jobType)}`);
}

export function getJob(jobId: string) {
  return fetchJson<JobDetailResponse>(`/jobs/${jobId}`);
}

export function getJobLogs(jobId: string) {
  return fetchJson<JobLogsResponse>(`/jobs/${jobId}/logs`);
}

export function cancelJob(jobId: string, reason?: string) {
  return fetchJson<JobDetailResponse>(`/jobs/${jobId}/cancel`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ reason }),
  });
}

export function pauseJob(jobId: string, reason?: string) {
  return fetchJson<JobDetailResponse>(`/jobs/${jobId}/pause`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ reason }),
  });
}

export function resumeJob(jobId: string) {
  return fetchJson<JobDetailResponse>(`/jobs/${jobId}/resume`, {
    method: 'POST',
  });
}

export function retryJob(jobId: string, reason?: string) {
  return fetchJson<JobDetailResponse>(`/jobs/${jobId}/retry`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ reason }),
  });
}

export function validateJobSubmission(request: JobSubmissionRequest) {
  return fetchJson<{ params: Record<string, unknown>; definition: JobDefinitionSummary; warnings: string[] }>(
    '/jobs/validate',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
  );
}

export function createJob(request: JobSubmissionRequest) {
  return fetchJson<{ created: boolean; job: JobDetailResponse['job']; job_dir: string; log_path: string; params_path: string; result_path: string; artifacts_path: string }>(
    '/jobs',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
  );
}
