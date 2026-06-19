export type BacktestSummary = {
  total_days: number;
  total_trades: number;
  valid_trades: number;
  skipped_trades: number;
  win_rate: number | null;
  avg_return_pct: number | null;
};

export type RegimeBacktestMetric = {
  regime_label: string;
  sample_count: number;
  win_trades: number;
  loss_trades: number;
  win_rate: number | null;
  avg_return: number | null;
  avg_win_return: number | null;
  avg_loss_return: number | null;
  max_drawdown: number | null;
  profit_factor: number | null;
  confidence: number;
  low_sample: boolean;
};

export type BacktestListItem = {
  result_id: string;
  trader_id: string | null;
  date_from: string | null;
  date_to: string | null;
  request_date_from?: string | null;
  request_date_to?: string | null;
  benchmark_symbol?: string | null;
  regime_version?: string | null;
  source_feature_version?: string | null;
  summary: BacktestSummary | Record<string, unknown>;
};

export type BacktestResultsResponse = {
  status: string;
  count: number;
  total: number;
  skip: number;
  limit: number;
  items: BacktestListItem[];
};

export type BacktestTradeRecord = {
  trade_date: string;
  trader_id: string;
  strategy_version_id: string;
  symbol: string;
  status: 'open' | 'closed' | 'skipped' | 'invalid';
  entry_price: number | null;
  exit_price: number | null;
  entry_date: string | null;
  exit_date: string | null;
  return_pct: number | null;
  mfe: number | null;
  mae: number | null;
  volume: number | null;
  is_valid_lot_size: boolean | null;
  skip_reason: string | null;
  evidence_refs: string[];
};

export type BacktestResultItem = {
  request_trader_id: string;
  request_date_from: string;
  request_date_to: string;
  benchmark_symbol?: string | null;
  regime_version?: string | null;
  source_feature_version?: string | null;
  result_version: string;
  summary: BacktestSummary | null;
  records: BacktestTradeRecord[];
  regime_metrics?: RegimeBacktestMetric[];
  rule_regime_metrics?: Record<string, RegimeBacktestMetric[]>;
  trader_id?: string;
  date_from?: string;
  date_to?: string;
};

export type BacktestResultResponse = {
  status: string;
  item: BacktestResultItem;
};

export type BacktestJobSubmission = {
  profileId: string;
  traderId: string;
  dateFrom: string;
  dateTo: string;
  strategyVersionId: string;
  benchmarkSymbol?: string;
  marketRegimeVersion?: string;
  mode: 'full' | 'replay' | 'rule_validation';
  symbols: string[];
  useSnapshotOnly: boolean;
  scoringProfile: string;
};

export type FormalBacktestLevel = 'level_1' | 'level_2' | 'level_3';

export type FormalBacktestSelection = {
  rule_version_id?: string | null;
  rule_family_id?: string | null;
  date_from: string;
  date_to: string;
  universe: Record<string, unknown>;
  benchmark_symbol: string;
  mode: 'full' | 'replay' | 'rule_validation';
  requested_level: FormalBacktestLevel;
  profile_id?: string | null;
};

export type FormalBacktestDependencyResult = {
  business_state: string;
  canonical_state: string;
  can_create_run: boolean;
  requested_level: FormalBacktestLevel;
  effective_level: FormalBacktestLevel | 'unavailable';
  selection: FormalBacktestSelection;
  coverage: Record<string, Record<string, unknown>>;
  unavailable_reasons: Array<{ code: string; message: string }>;
  limitations: string[];
  next_actions: string[];
  canonical_ids?: Record<string, unknown>;
  fingerprints?: Record<string, unknown>;
};

export type FormalBacktestRunCreateRequest = {
  selection: FormalBacktestSelection;
  reason?: string | null;
};

export type FormalBacktestRun = {
  run_id: string;
  status: string;
  business_status: string;
  rule_version_id?: string | null;
  rule_family_id?: string | null;
  frozen_rule_version_ids: string[];
  dataset_snapshot_id: string;
  request_fingerprint: string;
  reproducibility_fingerprint: string;
  snapshot_only: boolean;
  progress: Record<string, unknown>;
  limitations: string[];
  next_actions: string[];
};

export type FormalMarketStateMetric = {
  market_state_label: string;
  market_state_model_version?: string | null;
  market_state_source_version?: string | null;
  eligible_sample_count: number;
  evaluated_sample_count: number;
  unavailable_sample_count: number;
  invalid_sample_count: number;
  conflict_sample_count: number;
  hit_trade_count: number;
  avg_return?: number | null;
  total_return?: number | null;
  win_rate?: number | null;
  max_drawdown?: number | null;
  coverage?: number | null;
  warnings: string[];
  result_fingerprint?: string | null;
};

export type FormalBacktestResult = {
  result_id: string;
  run_id: string;
  status: string;
  requested_level: FormalBacktestLevel;
  effective_level: FormalBacktestLevel | 'unavailable';
  market_state_model_version?: string | null;
  market_state_source_version?: string | null;
  market_state_result_version: string;
  overall_metrics: Record<string, unknown>;
  per_market_state_metrics: FormalMarketStateMetric[];
  sample_state_counts: Record<string, number>;
  coverage: Record<string, Record<string, unknown>>;
  warnings: string[];
  limitations: string[];
  result_fingerprint: string;
  reproducibility_fingerprint: string;
};
