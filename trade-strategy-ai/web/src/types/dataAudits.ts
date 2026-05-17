export type DataAuditItem = {
  id: string;
  event_type: string;
  actor: string;
  entity_type: string;
  entity_id: string | null;
  dataset_version: string | null;
  source: string;
  payload: Record<string, unknown>;
  event_at: string;
  created_at: string;
  updated_at: string;
};

export type DataAuditsResponse = {
  filters: {
    event_type: string | null;
    actor: string | null;
    source: string | null;
    entity_type: string | null;
    start_date: string | null;
    end_date: string | null;
  };
  summary: {
    total: number;
    event_type_counts: Record<string, number>;
    entity_type_counts: Record<string, number>;
    source_counts: Record<string, number>;
  };
  page: {
    total: number;
    skip: number;
    limit: number;
    count: number;
  };
  items: DataAuditItem[];
};
