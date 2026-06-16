export type RuleReviewAutomaticReview = {
  status: string;
  label: string;
  risk_level: string;
  reasons: string[];
  requires_human_review: boolean;
  blocked_reason?: string | null;
};

export type RuleReviewCandidateListItem = {
  candidate_id: string;
  title: string;
  source_article_title: string;
  automatic_review: RuleReviewAutomaticReview;
  current_review_state: string;
  lifecycle_state: string;
  allowed_actions: Array<{ key: string; label: string }>;
};

export type RuleReviewCandidateListResponse = {
  count: number;
  total: number;
  items: RuleReviewCandidateListItem[];
};

export type RuleReviewCandidateDetail = {
  candidate_id: string;
  title: string;
  source_article: {
    article_id?: string;
    title: string;
    source_url?: string;
    summary: string | null;
    summary_status?: string;
    summary_reason?: string | null;
    published_at?: string | null;
    article_revision_id?: string;
  };
  automatic_review: RuleReviewAutomaticReview;
  current_review_state: string;
  current_lifecycle_state: string | null;
  missing_fields: string[];
  data_dependencies: string[];
  evidence?: Record<string, unknown>;
  governance: {
    related_rules: Array<{
      relation: string;
      title: string;
      conflict_reasons?: string[];
      parameter_differences?: Record<string, unknown>;
    }>;
  };
  lifecycle: {
    allowed_next_actions?: Array<{ key: string; label: string }>;
  };
  history: Array<Record<string, unknown>>;
  allowed_actions: Array<{ key: string; label: string }>;
  rule_version_id: string | null;
};

export type RuleReviewActionRequest = {
  action: string;
  reason: string;
  correlation_id: string;
  edits?: Record<string, unknown>;
};

export type RuleReviewActionResult = {
  candidate_id: string;
  current_review_state: string;
  current_lifecycle_state: string | null;
  rule_version_id: string | null;
  last_action: string;
  allowed_actions: Array<{ key: string; label: string }>;
};
