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

export type AutomaticReview = {
  status: 'pending_backtest' | 'needs_human_review' | 'suggested_reject';
  reasons: string[];
  risk_level: 'low' | 'medium' | 'high';
};

export type HumanReview = {
  review_state: string;
  formal_rule_created: boolean;
  rule_version_id: string | null;
  formal_lifecycle_state: string | null;
  stage3_status: string | null;
};

export type ArticleAnalysisCandidate = {
  candidate_id: string;
  candidate_index: number;
  title: string;
  rule_type: string;
  explicit_facts: Record<string, unknown>;
  hypotheses: Record<string, unknown>;
  missing_fields: Record<string, unknown>;
  evidence: Record<string, unknown>;
  data_dependencies: Record<string, unknown>;
  backtestability_status: string;
  kaipan_dependency: boolean;
  market_state_declaration_status: string;
  automatic_review: AutomaticReview;
  human_review: HumanReview;
};

export type ArticleAnalysisArticle = {
  article_id: string;
  article_revision_id: string;
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
  method_tags: string[];
  explicit_facts: Array<Record<string, unknown>>;
  hypotheses: Array<Record<string, unknown>>;
  missing_fields: Record<string, unknown>;
  prompt_trace: ArticleAnalysisTrace;
  candidates: ArticleAnalysisCandidate[];
};

export type RunArticleAnalysisRequest = {
  article_revision_id?: string | null;
};

export type ReviewArticleCandidateRequest = {
  decision: 'approve' | 'reject';
  reason?: string | null;
  article_revision_id?: string | null;
};
