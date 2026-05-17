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

