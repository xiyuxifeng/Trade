export type StrategyVersionSummaryItem = {
  version_id: string;
  trader_id: string;
  strategy_date: string;
  status: string;
  version_type: string;
  parent_version_id: string | null;
  recommendations_count: number;
  source_article_ids_count: number;
  released_at: string | null;
  has_rules_snapshot: boolean;
};

export type StrategyRecommendationItem = {
  symbol: string;
  decision: string;
  confidence: number;
  entry_price: number | null;
  target_price: number | null;
  stop_loss_price: number | null;
  volume: number | null;
  rationale: string | null;
  evidence_refs: string[];
};

export type StrategyVersionDetailItem = {
  version_id: string;
  trader_id: string;
  strategy_date: string;
  status: string;
  version_type: string;
  parent_version_id: string | null;
  recommendations: StrategyRecommendationItem[];
  source_article_ids: string[];
  evidence_refs: string[];
  notes: string | null;
  released_at: string | null;
  rules_snapshot: Array<Record<string, unknown>>;
  regime_selection?: Record<string, unknown> | null;
};

export type StrategyVersionListResponse = {
  status: string;
  count: number;
  total: number;
  skip: number;
  limit: number;
  items: StrategyVersionSummaryItem[];
};

export type StrategyVersionDetailResponse = {
  status: string;
  item: StrategyVersionDetailItem;
};

export type RuleValidationItem = {
  trader_id: string;
  strategy_version_id: string;
  rule_id: string;
  rule_text: string;
  programmable: boolean;
  validation_status: 'validated' | 'unsupported_rule' | 'missing_field' | 'missing_snapshot' | 'invalid_rule';
  hit_count: number;
  sample_count: number;
  hit_rate: number | null;
  posterior_return_mean: number | null;
  posterior_return_median: number | null;
  notes: string[];
  result_version: string;
};

export type ActiveTraderFilterConfig = {
  min_win_rate: number;
  min_trades: number;
  bayesian_alpha: number;
  baseline_win_rate: number;
  min_rule_hit_rate: number | null;
  min_score: number;
};

export type ActiveTraderFilterRequest = {
  backtest_results: Array<{
    trader_id: string;
    date_from: string;
    date_to: string;
    summary: {
      total_days: number;
      total_trades: number;
      valid_trades: number;
      skipped_trades: number;
      win_rate: number | null;
      avg_return_pct: number | null;
    };
  }>;
  rule_validations?: Record<string, RuleValidationItem[]>;
  config?: Partial<ActiveTraderFilterConfig>;
};

export type StrategyAdjustmentItem = {
  trader_id: string;
  rule_id: string;
  current_status: string;
  suggestion: string;
  confidence: number;
  basis: string;
};

export type CandidateRecommendationItem = StrategyRecommendationItem;

export type CandidateCreateRequest = {
  parent_version_id: string;
  trader_id: string;
  strategy_date: string;
  adjustments: StrategyAdjustmentItem[];
  recommendations: CandidateRecommendationItem[];
  notes?: string | null;
};

export type CandidateCreateResponse = {
  status: string;
  item: StrategyVersionDetailItem;
};

export type RuleSummaryItem = {
  rule_id: string;
  source_type: string;
  rule_type: string;
  instrument_focus: string;
  mapping_status: string;
  review_status: string;
  initial_confidence: number;
  validated_confidence: number | null;
  backtest_result: Record<string, unknown> | null;
  backtest_hits: number;
  backtest_misses: number;
  backtest_samples: number;
  mapped: boolean;
  created_at: string | null;
};

export type RuleDetailItem = RuleSummaryItem & {
  id: string | null;
  source_article_ids: string[];
  extraction_layer: Record<string, unknown>;
  mapped_by: string | null;
  mapped_at: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  backtest_triggered_at: string | null;
  used_in_prediction: boolean;
  prediction_count: number;
  last_used_at: string | null;
  updated_at: string | null;
};

export type RulePoolListResponse = {
  status: string;
  count: number;
  total: number;
  skip: number;
  limit: number;
  items: RuleSummaryItem[];
};

export type RulePoolDetailResponse = {
  status: string;
  item: RuleDetailItem;
};

export type RulePoolReviewRequest = {
  decision: 'approve' | 'reject' | 'pending';
  force?: boolean;
  reviewed_by?: string;
};

export type RulePoolBatchReviewRequest = {
  decision: 'approve' | 'reject' | 'pending';
  status?: 'pending' | 'approved' | 'rejected';
  limit?: number;
  force?: boolean;
  reviewed_by?: string;
};
