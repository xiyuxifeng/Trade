export type JobRecord = {
  id: string;
  job_type: string;
  status: string;
  params: Record<string, unknown>;
  result: unknown;
  error: unknown;
  artifacts: JobArtifactRef[];
  created_by: string;
  idempotency_key: string | null;
  retry_count: number;
  max_retries: number;
  retry_backoff_seconds: number;
  timeout_seconds: number | null;
  cancel_requested: boolean;
  cancel_requested_at: string | null;
  worker_id: string | null;
  lock_token: string | null;
  lock_acquired_at: string | null;
  heartbeat_at: string | null;
  scheduled_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type JobArtifactRef = {
  kind: string;
  path: string;
  metadata: Record<string, unknown>;
};

export type JobsListResponse = {
  count: number;
  total: number;
  skip: number;
  limit: number;
  items: JobRecord[];
};

export type JobDetailResponse = {
  job: JobRecord;
  job_dir: string;
  log_path: string;
  params_path: string;
  result_path: string;
  artifacts_path: string;
};

export type JobLogsResponse = {
  job_id: string;
  log_path: string;
  count: number;
  items: string[];
};

export type JobSubmissionRequest = {
  job_type: string;
  params?: Record<string, unknown>;
  created_by?: string;
  idempotency_key?: string | null;
  max_retries?: number;
  retry_backoff_seconds?: number;
  timeout_seconds?: number | null;
};
