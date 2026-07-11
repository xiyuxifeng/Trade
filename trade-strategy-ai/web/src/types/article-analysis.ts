export type PrimaryExtractionType =
  | 'executable_rule'
  | 'rule_candidate'
  | 'research_hypothesis'
  | 'semantic_experience'
  | 'risk_control_hint'
  | 'data_requirement_hint'
  | 'unusable_noise';

export type ArticleAnalysisTrace = {
  run_id: string | null;
  prompt_name: string | null;
  prompt_version: string | null;
  schema_name: string | null;
  schema_version: string | null;
  provider: string | null;
  model: string | null;
  validation_state: string | null;
  retry_count: number;
  token_usage: Record<string, unknown>;
  cost_amount: number | null;
  cost_currency: string | null;
  started_at: string | null;
  completed_at: string | null;
};

export type ExtractionEligibility = {
  eligible: boolean;
  reason: string;
  required_next_step: string;
  blocked_by: string[];
};

export type ArticleExtractionItem = {
  item_id: string;
  item_index: number;
  article_id: string;
  article_revision_id: string | null;
  article_structure_id: string;
  prompt_run_id: string;
  primary_type: PrimaryExtractionType;
  secondary_tags: string[];
  display_title: string;
  display_summary: string;
  source_evidence: Record<string, unknown>;
  taxonomy_payload: Record<string, unknown>;
  confidence: Record<string, unknown>;
  quality_state: string;
  review_destination: string;
  review_state: string;
  backtest_eligibility: ExtractionEligibility;
  promotion_eligibility: ExtractionEligibility;
  provenance: Record<string, unknown>;
  rule_version_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ArticleAnalysisArticle = {
  article_id: string;
  article_revision_id: string;
  content_hash: string;
  title: string;
  source: string;
  source_url: string;
  author_name: string | null;
  author_id: string | null;
  published_at: string | null;
  crawled_at: string;
  original_text: string;
  cleaned_content: string;
  summary: string | null;
  tags: string[];
};

export type ArticleAnalysisDetail = {
  status: 'ready' | 'partial' | 'empty';
  message: string | null;
  article: ArticleAnalysisArticle;
  summary_provenance: {
    source: 'article_revision_source_payload' | 'blog_article_current' | 'unavailable';
    article_revision_id: string;
    content_hash: string;
    available: boolean;
    aligned: boolean;
    reason: string | null;
  };
  article_structure_provenance: {
    article_structure_id: string | null;
    article_revision_id: string | null;
    prompt_run_id: string | null;
    prompt_name: string | null;
    prompt_version: string | null;
    schema_name: string | null;
    schema_version: string | null;
    available: boolean;
  };
  method_tags: string[];
  explicit_facts: Array<Record<string, unknown>>;
  hypotheses: Array<Record<string, unknown>>;
  missing_fields: Record<string, unknown>;
  prompt_trace: ArticleAnalysisTrace;
  taxonomy_version: string | null;
  extraction_summary: {
    total: number;
    by_primary_type: Record<string, number>;
    by_destination: Record<string, number>;
    by_quality_state: Record<string, number>;
    by_review_state: Record<string, number>;
  };
  extraction_items: ArticleExtractionItem[];
};

export type RunArticleAnalysisRequest = { article_revision_id?: string | null };
export type ReviewExtractionItemRequest = {
  decision: 'accept' | 'reject';
  reason?: string | null;
  article_revision_id?: string | null;
};
export type UpdateArticleProcessingStatusRequest = {
  action: 'ignored' | 'manual_review_required';
  note?: string | null;
};
export type ArticleProcessingStatus = {
  article_id: string;
  processing_status: 'ignored' | 'manual_review_required';
  processing_note: string | null;
  processing_updated_at: string;
  processing_updated_by: string;
};
