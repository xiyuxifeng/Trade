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

export type SystemStatusResponse = {
  status: 'ok';
  config_path: string;
  project_root: string;
  run_mode: string;
  database: DatabaseHealthStatus;
  directories: Record<string, SystemDirectoryStatus>;
  warnings: string[];
};
