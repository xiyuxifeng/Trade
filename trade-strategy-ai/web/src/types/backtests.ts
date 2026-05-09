export type BacktestSummary = {
  total_days: number;
  total_trades: number;
  valid_trades: number;
  skipped_trades: number;
  win_rate: number | null;
  avg_return_pct: number | null;
};

export type BacktestListItem = {
  result_id: string;
  trader_id: string | null;
  date_from: string | null;
  date_to: string | null;
  request_date_from?: string | null;
  request_date_to?: string | null;
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
  result_version: string;
  summary: BacktestSummary | null;
  records: BacktestTradeRecord[];
  trader_id?: string;
  date_from?: string;
  date_to?: string;
};

export type BacktestResultResponse = {
  status: string;
  item: BacktestResultItem;
};

export type BacktestJobSubmission = {
  traderId: string;
  dateFrom: string;
  dateTo: string;
  strategyVersionId: string;
  mode: 'full' | 'replay' | 'rule_validation';
  configPath: string;
};
