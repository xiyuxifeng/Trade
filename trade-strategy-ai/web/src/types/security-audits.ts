export type PermissionDeniedLogSummary = {
  total: number;
  unique_actors: number;
  unique_paths: number;
  source_counts: Record<string, number>;
};

export type PermissionDeniedLogItem = {
  id: string;
  event_type: string;
  actor: string;
  entity_type: string;
  entity_id: string | null;
  dataset_version: string | null;
  source: string;
  request_context: {
    request: {
      method: string | null;
      path: string | null;
    };
    response: {
      status_code: number | null;
      detail: unknown;
    };
    principal: {
      role: string | null;
      api_key_label: string | null;
      authenticated: boolean | null;
      source: string | null;
    };
  };
  payload: Record<string, unknown>;
  event_at: string;
  created_at: string;
  updated_at: string;
};

export type PermissionDeniedLogResponse = {
  filters: {
    actor: string | null;
    source: string | null;
    path: string | null;
    start_date: string | null;
    end_date: string | null;
  };
  summary: PermissionDeniedLogSummary;
  page: {
    total: number;
    skip: number;
    limit: number;
    count: number;
  };
  items: PermissionDeniedLogItem[];
};
