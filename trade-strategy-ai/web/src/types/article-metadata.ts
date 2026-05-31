export type ArticleMetadataCandidate = {
  schema_version: string;
  score: number;
  score_reasons: string[];
  processed_at: string | null;
  provider: string | null;
  model: string | null;
  article_type: string | null;
  extraction_version: string | null;
  sentiment_score: number | null;
  confidence_score: number | null;
  extracted_concepts_count: number;
  trading_symbols_count: number;
  strategy_rules_count: number;
  preconditions_count: number;
  comment_insights_count: number;
  raw_llm_output_keys: number;
};

export type ArticleMetadataResolution = {
  article_id: string;
  selected_schema_version: string | null;
  selected_by: string | null;
  selected_at: string | null;
  selection_mode: string | null;
  selection_score: number | null;
  selection_reason: string | null;
  recommended_schema_version: string | null;
  recommended_score: number | null;
  recommended_reason: string | null;
  effective_schema_version: string | null;
  effective_score: number | null;
  effective_reason: string | null;
  warning: string | null;
  candidates: ArticleMetadataCandidate[];
};

export type ArticleMetadataResolutionListResponse = {
  items: ArticleMetadataResolution[];
};

export type ArticleMetadataSelectRequest = {
  selected_schema_version: string;
  selected_by?: string;
  selection_reason?: string | null;
};
