export type AlertHistoryItem = {
  id: string;
  alert_id: string;
  level: string;
  title: string;
  message: string | null;
  channel: string;
  tags: string[];
  status: string;
  aggregated_count: number;
  aggregation_key: string | null;
  sent_at: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  alert_metadata: Record<string, unknown>;
  created_at: string;
};

export type AlertHistoryResponse = {
  count: number;
  total: number;
  items: AlertHistoryItem[];
};

export type AlertingStatusResponse = {
  enabled: boolean;
  channel: string;
  min_level: string;
  console_output: boolean;
  aggregation_window_minutes: number;
  aggregation_max_count: number;
  webhook_configured: boolean;
  channel_configured: boolean;
};

export type AlertHistoryQuery = {
  status?: string;
  level?: string;
  tag?: string;
  date_from?: string;
  date_to?: string;
  skip?: number;
  limit?: number;
};

export type AlertActionResponse = {
  status: string;
  id: string;
  new_status: string;
};
