export type SymbolListResponse = {
  count: number;
  items: string[];
};

export type OhlcvRow = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  turnover?: number | null;
};

export type OhlcvResponse = {
  symbol: string;
  start_date: string;
  end_date: string;
  count: number;
  items: OhlcvRow[];
};

export type MarketQueryPage = {
  total: number;
  limit: number;
  offset: number;
  count: number;
};

export type MarketQueryError = {
  type: string;
  message: string;
  detail: string | null;
  metadata: Record<string, unknown>;
};

export type MarketSnapshotListItem = {
  snapshot_id: string;
  trade_date: string | null;
  market: string;
  data_version: string;
  quality_status: string;
  created_at: string | null;
  section_count: number;
  available_section_count: number;
  partial_section_count: number;
  missing_section_count: number;
  profile_id: string | null;
};

export type MarketSnapshotSectionSummary = {
  id: string;
  snapshot_id: string;
  section_id: string;
  provider: string | null;
  source_time: string | null;
  record_count: number;
  missing_reason: string | null;
  quality_status: string;
  section_version: string | null;
  storage_ref: Record<string, unknown>;
};

export type MarketSnapshotItemSummary = {
  id: string;
  snapshot_id: string;
  section_id: string;
  dataset_id: string | null;
  symbol: string | null;
  item_key: string;
  item_type: string | null;
  source_time: string | null;
  quality_status: string;
  payload_json: Record<string, unknown>;
};

export type MarketSnapshotListResponse = {
  filters: Record<string, unknown>;
  page: MarketQueryPage;
  items: MarketSnapshotListItem[];
};

export type MarketSnapshotDetailResponse = {
  snapshot: MarketSnapshotListItem;
  sections: MarketSnapshotSectionSummary[];
  item_count: number;
  quality_report: Record<string, unknown> | null;
  dataset: Record<string, unknown> | null;
  warnings: string[];
};

export type MarketSnapshotSectionListResponse = {
  snapshot_id: string;
  page: MarketQueryPage;
  items: MarketSnapshotSectionSummary[];
};

export type MarketSnapshotSectionResponse = {
  snapshot_id: string;
  section: MarketSnapshotSectionSummary;
  page: MarketQueryPage;
  items: MarketSnapshotItemSummary[];
  filters: Record<string, unknown>;
};

export type MarketDatasetSummary = {
  id: string;
  dataset_id: string;
  dataset_type: string;
  trade_date: string;
  market: string;
  source: string | null;
  storage_ref: Record<string, unknown>;
  snapshot_id: string | null;
  profile_id: string | null;
  quality_status: string;
  created_at: string | null;
  updated_at: string | null;
};

export type MarketDatasetListResponse = {
  filters: Record<string, unknown>;
  page: MarketQueryPage;
  items: MarketDatasetSummary[];
};

export type MarketDatasetDetailResponse = {
  dataset: MarketDatasetSummary;
  snapshot: MarketSnapshotListItem | null;
  page: MarketQueryPage;
  items: MarketSnapshotItemSummary[];
  warnings: string[];
};

export type MarketSnapshotQualityResponse = {
  quality_report: Record<string, unknown>;
};
