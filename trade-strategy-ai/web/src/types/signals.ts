export type SignalListParams = {
  symbol?: string;
  since?: string;
  limit?: number;
};

export type SignalItem = {
  signal_id: string;
  symbol: string;
  side: string;
  confidence: number;
  timestamp: string;
  trader_id: string | null;
  strategy_version_id: string | null;
  context: Record<string, unknown> | unknown[] | string | null;
  context_summary: string;
};

export type SignalListResponse = {
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  base_dir: string;
  count: number;
  signals: SignalItem[];
};
