export type MarketStateBuildRequest = {
  benchmark_symbol: string;
  as_of?: string | null;
  from_akshare?: boolean;
  cache_csv?: boolean;
};

export type MarketStateBuildResponse = {
  config_path: string;
  base_dir: string;
  market_state_path: string;
  snapshot_path?: string;
  source: string;
  benchmark_symbol?: string;
  market_state: Record<string, unknown>;
};
