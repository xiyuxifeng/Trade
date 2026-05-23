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
  id?: string | null;
  source_article_ids?: string[];
  extraction_layer?: Record<string, unknown>;
  mapped_by?: string | null;
  mapped_at?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  backtest_triggered_at?: string | null;
  used_in_prediction?: boolean;
  prediction_count?: number;
  last_used_at?: string | null;
  updated_at?: string | null;
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

export type RuleApplicabilityRegimeItem = {
  regime_label: string;
  decision: string;
  score: number;
  sample_count: number;
  win_rate: number | null;
  avg_return: number | null;
  avg_win_return: number | null;
  avg_loss_return: number | null;
  max_drawdown: number | null;
  profit_factor: number | null;
  confidence: number;
  low_sample: boolean;
  reason: string;
  evidence: string[];
};

export type RuleApplicabilityProfileItem = {
  profile_id: string;
  rule_id: string;
  profile_version: string;
  source_backtest_id: string;
  source_rule_version: string | null;
  market_regime_version: string | null;
  source_feature_version: string | null;
  review_status: string;
  min_sample_count: number;
  confidence: number;
  applicable_regimes: RuleApplicabilityRegimeItem[];
  blocked_regimes: RuleApplicabilityRegimeItem[];
  neutral_regimes: RuleApplicabilityRegimeItem[];
  best_market_conditions: Record<string, unknown>;
  worst_market_conditions: Record<string, unknown>;
  summary: Record<string, unknown>;
  storage_ref: Record<string, unknown>;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string | null;
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

export type RulePoolFilterOptionsResponse = {
  status: string;
  review_statuses: string[];
  mapping_statuses: string[];
  source_types: string[];
  rule_types: string[];
  instrument_focuses: string[];
};

export type RulePoolDetailResponse = {
  status: string;
  item: RuleDetailItem;
};

export type RuleApplicabilityListResponse = {
  status: string;
  count: number;
  total: number;
  skip: number;
  limit: number;
  items: RuleApplicabilityProfileItem[];
};

export type RuleApplicabilityDetailResponse = {
  status: string;
  item: RuleApplicabilityProfileItem;
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

export type RulePoolQuery = {
  status?: string;
  rule_type?: string;
  mapping_status?: string;
  source_type?: string;
  instrument_focus?: string;
  skip_no_mapped?: boolean;
  skip?: number;
  limit?: number;
};

export type RuleApplicabilityGenerateRequest = {
  source_backtest_id: string;
  profile_version?: string;
  min_sample_count?: number;
  review_status?: 'draft' | 'reviewed' | 'active' | 'archived';
  reviewed_by?: string;
};

export type RuleApplicabilityReviewRequest = {
  review_status: 'draft' | 'reviewed' | 'active' | 'archived';
  reviewed_by?: string;
};
