export type JobRecord = {
  id: string;
  job_type: string;
  status: string;
  params: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: JobError | string | null;
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
  audit_events: JobAuditEvent[];
  created_at: string;
  updated_at: string;
  config_snapshot_path?: string | null;
  config_snapshot?: JobConfigSnapshot | null;
};

export type JobAuditEvent = {
  id: string;
  job_id: string;
  operation: string;
  actor: string;
  source: string;
  params_summary: Record<string, unknown>;
  payload: Record<string, unknown>;
  event_at: string;
  created_at: string;
  updated_at: string;
};

export type JobArtifactRef = {
  artifact_id: string;
  job_id: string;
  workflow_id: string | null;
  step_id: string | null;
  kind: string;
  title: string;
  summary: string | null;
  safe_download_url: string | null;
  download_token: string | null;
  size_bytes: number | null;
  created_at: string;
  visibility: 'public' | 'internal' | 'private';
  metadata: Record<string, unknown>;
  storage_ref: {
    source: 'file' | 'db' | 'external';
    logical_id: string;
    relative_path: string | null;
    uri: string | null;
    metadata: Record<string, unknown>;
  } | null;
};

export type JobConfigSnapshot = {
  config_snapshot_id: string;
  job_id: string | null;
  config_path: string;
  config_source: string;
  config_hash: string;
  masked_snapshot: Record<string, unknown>;
  captured_at: string;
  snapshot_path: string;
  profile_id?: string | null;
  validation_status?: string | null;
  masked_sections?: string[] | null;
  missing_fields?: string[] | null;
  invalid_fields?: string[] | null;
};

export type JobError = {
  type?: string;
  message?: string;
  detail?: string | Record<string, unknown> | null;
  request_id?: string | null;
  code?: string | null;
  retryable?: boolean | null;
  metadata?: Record<string, unknown>;
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
  confirmed?: boolean;
};
