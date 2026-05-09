export type ReportKind = 'daily' | 'evaluation';

export type ReportSummaryItem = {
  as_of_date: string;
  file_path: string;
  file_size: number | null;
};

export type ReportListResponse = {
  status: string;
  count: number;
  total: number;
  skip: number;
  limit: number;
  reports: ReportSummaryItem[];
};

export type TradeEntry = {
  type: string;
  price: number | null;
  condition: string | null;
};

export type TradeIdea = {
  idea_id: string;
  trader_id: string;
  as_of_date: string;
  symbol: string;
  side: string;
  entry: TradeEntry;
  target_price: number | null;
  stop_loss_price: number | null;
  position_size: number | null;
  time_horizon: string | null;
  strategy_version_id: string | null;
  source_topic_ids: string[];
  evidence_refs: string[];
  decision_mode: string | null;
  source_recommendation_idx: number | null;
  rationale: string | null;
  invalidation: string | null;
  confidence: number | null;
  style_cluster_id: string | null;
  style_cluster_label: string | null;
  style_score: number | null;
  style_reasons: string[];
};

export type DailyReportDetail = {
  status: string;
  report: {
    report_id: string;
    as_of_date: string;
    generated_at: string;
    ideas: TradeIdea[];
    highlights: string[];
    risks: string[];
    strategy_version_ids: string[];
    market_universe_snapshot: Record<string, unknown> | null;
  };
};

export type IdeaEvaluation = {
  idea_id: string;
  symbol: string;
  entry_price: number | null;
  current_price: number | null;
  return_pct: number | null;
  status: string;
  notes: string[];
};

export type EvaluationResultDetail = {
  status: string;
  result: {
    result_id: string;
    as_of_date: string;
    generated_at: string;
    evaluations: IdeaEvaluation[];
    evidence_pack_refs: string[];
    failure_categories: string[];
    ranking_features: Record<string, unknown>;
    postmortem_notes: string[];
    summary: string[];
  };
};
