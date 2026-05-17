import type { JobArtifactRef } from '@/types/jobs';

export type JobAuditSummary = {
  total: number;
  confirmed_count: number;
  high_risk_count: number;
  unique_jobs: number;
  operation_counts: Record<string, number>;
};

export type JobAuditListItem = {
  id: string;
  job_id: string;
  job_type: string;
  job_status: string;
  created_by: string | null;
  operation: string;
  actor: string;
  source: string;
  confirmed: boolean | null;
  params_summary: Record<string, unknown>;
  payload: Record<string, unknown>;
  event_at: string;
  created_at: string;
  updated_at: string;
};

export type JobAuditListResponse = {
  filters: {
    actor: string | null;
    job_type: string | null;
    operation: string | null;
    start_date: string | null;
    end_date: string | null;
    confirmed: boolean | null;
  };
  summary: JobAuditSummary;
  page: {
    total: number;
    skip: number;
    limit: number;
    count: number;
  };
  items: JobAuditListItem[];
};

export type JobAuditJobSummary = {
  id: string;
  job_type: string;
  status: string;
  created_by: string | null;
  retry_count: number;
  max_retries: number;
  retry_backoff_seconds: number;
  timeout_seconds: number | null;
  cancel_requested: boolean;
  cancel_requested_at: string | null;
  worker_id: string | null;
  lock_acquired_at: string | null;
  heartbeat_at: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
  artifacts: JobArtifactRef[];
};

export type JobAuditDetailResponse = {
  job: JobAuditJobSummary;
  summary: {
    event_count: number;
    confirmed_count: number;
    high_risk_count: number;
    has_artifacts: boolean;
  };
  request_context: Record<string, unknown>;
  items: JobAuditListItem[];
};
