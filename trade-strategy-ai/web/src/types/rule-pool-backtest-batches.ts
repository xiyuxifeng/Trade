export type RulePoolBacktestBatchRunCreateRequest = {
  ruleIds: string[];
  batchSize: number;
  startDate: string;
  endDate: string;
  minConfidence?: number;
  marketRegimeVersion?: string;
  marketStateVersion?: string;
  profileId?: string;
};

export type RulePoolBacktestBatch = {
  batch_id: string;
  batch_run_id: string;
  batch_index: number;
  rule_ids: string[];
  rule_count: number;
  job_id: string | null;
  status: string;
  result: Record<string, unknown> | null;
  result_artifact_id: string | null;
  error: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type RulePoolBacktestBatchRun = {
  batch_run_id: string;
  status: string;
  start_date: string;
  end_date: string;
  min_confidence: number;
  market_regime_version: string | null;
  profile_id: string | null;
  selected_rule_count: number;
  batch_size: number;
  created_by: string | null;
  merged_result_id: string | null;
  config: Record<string, unknown>;
  fingerprint: string;
  batches: RulePoolBacktestBatch[];
  created_at: string | null;
  updated_at: string | null;
  merged_result?: RulePoolBacktestMergedResult;
};

export type RulePoolBacktestBatchRunListResponse = {
  items: RulePoolBacktestBatchRun[];
  count: number;
  total: number;
  skip: number;
  limit: number;
};

export type RulePoolBacktestMergedResult = {
  result_id: string;
  batch_run_id: string;
  status: string;
  summary: {
    total_days?: number;
    total_trades?: number;
    valid_trades?: number;
    skipped_trades?: number;
  };
  records: Array<Record<string, unknown>>;
  rule_results: Array<{
    rule_id: string;
    batch_id: string;
    batch_index: number;
    batch_run_id: string;
    job_id: string | null;
    source_result_reference: string;
    market_state_metrics: unknown;
  }>;
  rule_regime_metrics: Record<string, unknown>;
  provenance: Record<string, unknown>;
};
