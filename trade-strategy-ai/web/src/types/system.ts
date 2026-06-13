export type ApiErrorPayload = {
  detail?: string;
  message?: string;
  error?: string;
  [key: string]: unknown;
};

export type ApiErrorShape = {
  status: number;
  message: string;
  payload?: ApiErrorPayload;
};

export type SystemDirectoryStatus = {
  path: string;
  exists: boolean;
};

export type DatabaseHealthStatus = {
  name: string;
  status: 'ok' | 'warning' | 'error';
  latency_ms?: number | null;
  details?: Record<string, unknown>;
  error?: string | null;
};

export type SystemHealthComponentStatus = {
  name: string;
  status: 'ok' | 'warning' | 'error';
  latency_ms?: number | null;
  details?: Record<string, unknown>;
  error?: string | null;
};

export type SystemStatusResponse = {
  status: 'ok';
  profile_context?: {
    profile_id: string | null;
    profile_snapshot_id: string | null;
    source: 'env' | 'unset';
  };
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  project_root: string;
  run_mode: string;
  database: DatabaseHealthStatus;
  directories: Record<string, SystemDirectoryStatus>;
  warnings: string[];
};

export type SystemDashboardFailedJob = {
  id: string;
  job_type: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  error_message?: string | null;
  heartbeat_at?: string | null;
};

export type HomeBusinessStatusValue =
  | 'ready'
  | 'pending'
  | 'complete'
  | 'blocked'
  | 'partial'
  | 'unavailable';

export type HomeBusinessStatus = {
  status: HomeBusinessStatusValue;
  value: string | number | boolean | null;
  label: string;
  detail: string;
  source: string;
  updated_at: string | null;
  target_path: string;
  unavailable_reason: string | null;
};

export type SystemDashboardResponse = {
  status: 'ok' | 'partial' | 'error';
  generated_at: string;
  business_date: string | null;
  is_trading_day: boolean | null;
  latest_trading_day: string | null;
  business_status: Record<string, HomeBusinessStatus>;
  next_action: {
    id: string;
    label: string;
    target_path: string;
  };
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  health: {
    overall: string;
    issues: string[];
    database?: SystemHealthComponentStatus;
    [key: string]: unknown;
  };
  worker: {
    status: 'ok' | 'warning' | 'error';
    heartbeat_at: string | null;
    heartbeat_age_minutes: number | null;
    current_job_id: string | null;
  };
  failed_jobs: SystemDashboardFailedJob[];
  duration_summary: {
    average_seconds: number | null;
    p95_seconds: number | null;
    recent_jobs: Array<{
      id: string;
      job_type: string;
      duration_seconds: number | null;
    }>;
  };
  freshness: {
    sources: Array<{
      source: string;
      entity_type: string;
      last_updated?: string | null;
      freshness_hours?: number | null;
      is_stale: boolean;
    }>;
  };
  alerts: {
    critical: number;
    warning: number;
    latest: Array<Record<string, unknown>>;
  };
  traces: Array<{
    job_id: string;
    request_context: {
      path?: string;
      method?: string;
      client_host?: string | null;
    } | null;
  }>;
  report?: Record<string, unknown>;
};
