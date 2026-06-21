export type StrategyStatusState =
  | 'ready'
  | 'loading'
  | 'empty'
  | 'error'
  | 'partial'
  | 'permission_denied'
  | 'unavailable'
  | 'draft'
  | 'pending_review'
  | 'published'
  | 'archived';

export type StrategyCurrentStatus = {
  is_current: boolean;
  current_version_id?: string | null;
  previous_current_version_id?: string | null;
};

export type StrategyVersionSnapshot = {
  strategy_version_id: string;
  strategy_id: string;
  business_key: string;
  title: string;
  version_no: number;
  lifecycle_state: string;
  lifecycle_label: string;
  validation_summary?: StrategyValidationSummary | null;
  current_status: StrategyCurrentStatus;
};

export type StrategyRevisionProposal = {
  proposal_id: string;
  proposal_type: 'strategy_revision';
  lifecycle_state: string;
  lifecycle_label: string;
  revision_no: number;
  rationale: string;
  trigger_type?: string | null;
  confidence: number | null;
  evidence_state: string;
  evidence_label: string;
  affected_strategy_version: StrategyVersionSnapshot;
  base_version_id?: string | null;
  accepted_draft_version_id?: string | null;
  proposed_changes: Record<string, unknown>;
  evidence: {
    dataset_snapshot_id?: string | null;
    market_snapshot_ids?: string[];
    rule_applicability_profile_ids?: string[];
    backtest_run_ids?: string[];
    backtest_result_ids?: string[];
    evidence_fingerprint?: string | null;
    [key: string]: unknown;
  };
  created_at?: string | null;
  updated_at?: string | null;
  available_actions: string[];
  partial_reasons: string[];
  limitations: string[];
};

export type StrategyRevisionProposalListResponse = {
  state: 'ready' | 'empty' | 'partial';
  count: number;
  items: StrategyRevisionProposal[];
};

export type StrategyRevisionProposalDetailResponse = StrategyRevisionProposal;

export type StrategyRevisionProposalReviewRequest = {
  action: 'start_review' | 'return_to_draft' | 'reject' | 'archive' | 'supersede';
  reason?: string | null;
  superseded_by_proposal_id?: string | null;
};

export type StrategyRevisionProposalAcceptRequest = {
  reason?: string | null;
  linked_draft_version_id?: string | null;
};

export type StrategyRevisionProposalAcceptResponse = StrategyRevisionProposal;

export type StrategyValidationSummary = {
  state: string;
  label: string;
  reviewer_decision: string;
  reviewer_decision_label: string;
  checked_at?: string | null;
  checked_by?: string | null;
  reason?: string | null;
  dataset_binding: {
    state: string;
    dataset_snapshot_id?: string | null;
    market_state_definition_version?: string | null;
  };
  market_snapshot_binding: {
    state: string;
    market_snapshot_ids: string[];
  };
  backtest: {
    state: string;
    out_of_sample_state: string;
    backtest_run_ids: string[];
    backtest_result_ids: string[];
    requested_level?: string | null;
    effective_level?: string | null;
    annual_return?: number | null;
    max_drawdown?: number | null;
    win_rate?: number | null;
  };
  rule_applicability: {
    state: string;
    covered_rule_count: number;
    total_rule_count: number;
    coverage_ratio: number;
    uncovered_rule_version_ids?: string[];
  };
  sample_coverage: {
    state: string;
    sample_count?: number | null;
    insufficient_sample: boolean;
  };
  data_quality: {
    state: string;
    warnings: string[];
    limitations: string[];
  };
};

export type StrategyVersion = {
  strategy_version_id: string;
  strategy_id: string;
  business_key: string;
  title: string;
  summary?: string | null;
  version_no: number;
  lifecycle_state: string;
  lifecycle_label: string;
  review_status: string;
  status_state: string;
  schema_version: string;
  quality_status: string;
  rule_pool: Array<{
    rule_version_id: string;
    title?: string | null;
    base_weight?: number | null;
    status?: string | null;
    configuration_json: Record<string, unknown>;
  }>;
  profiles: {
    author_method_profile_version_id?: string | null;
    author_rule_profile_version_id?: string | null;
    author_validated_profile_version_id?: string | null;
  };
  policies: {
    risk_policy_json: Record<string, unknown>;
    selection_policy_json: Record<string, unknown>;
    universe_json: Record<string, unknown>;
  };
  evidence: {
    dataset_snapshot_id?: string | null;
    market_snapshot_ids: string[];
    rule_applicability_profile_ids: string[];
    backtest_run_ids: string[];
    backtest_result_ids: string[];
    evidence_fingerprint?: string | null;
  };
  current_status: StrategyCurrentStatus;
  validation: StrategyValidationSummary;
  published_at?: string | null;
  partial_reasons: string[];
  limitations: string[];
};

export type StrategyListResponse = {
  state: 'ready' | 'empty' | 'partial';
  current_strategy: { business_key: string; current_version_id: string } | null;
  items: StrategyVersion[];
  count: number;
};

export type StrategyDraftOptionsResponse = {
  rule_options: Array<{
    rule_version_id: string;
    title: string;
    rule_type?: string;
    canonical_fingerprint?: string | null;
  }>;
  author_profile_options: {
    method: Array<{ author_profile_version_id: string; label: string; author_id?: string | null }>;
    rule: Array<{ author_profile_version_id: string; label: string; author_id?: string | null }>;
    validated: Array<{ author_profile_version_id: string; label: string; author_id?: string | null }>;
  };
  dataset_options: Array<{ dataset_snapshot_id: string; label: string; content_fingerprint?: string | null }>;
  market_snapshot_options: Array<{ market_snapshot_id: string; label: string; content_fingerprint?: string | null }>;
  rule_applicability_options: Array<{ applicability_profile_id: string; label: string; dataset_snapshot_id?: string | null }>;
};

export type StrategyDraftRequest = {
  strategy_id?: string | null;
  business_key: string;
  schema_version: string;
  title: string;
  summary?: string | null;
  rule_memberships: Array<{
    rule_version_id: string;
    base_weight?: number | null;
    status?: string | null;
    configuration_json: Record<string, unknown>;
  }>;
  author_method_profile_version_id: string;
  author_rule_profile_version_id: string;
  author_validated_profile_version_id: string;
  risk_policy_json: Record<string, unknown>;
  selection_policy_json: Record<string, unknown>;
  universe_json: Record<string, unknown>;
  evidence_json: Record<string, unknown>;
};

export type StrategyTransitionRequest = {
  reason?: string | null;
};

export type StrategyTransitionResponse = {
  strategy_version_id: string;
  lifecycle_state: string;
};

export type StrategyValidationRequest = {
  reason?: string | null;
};

export type StrategyRollbackRequest = {
  reason: string;
};

export type StrategyComparisonResponse = {
  state: 'ready' | 'unavailable';
  current_version: Partial<StrategyVersion> | null;
  candidate_version: Partial<StrategyVersion>;
  delta: {
    rule_count_change: number;
    rule_weight_changes: number;
    annual_return_change?: number | null;
    max_drawdown_change?: number | null;
  };
};

export type StrategyDiffResponse = {
  state: 'ready' | 'unavailable';
  base_version: Partial<StrategyVersion> | null;
  target_version: Partial<StrategyVersion>;
  changes: Array<{
    field: string;
    label: string;
    before: unknown;
    after: unknown;
  }>;
  summary?: {
    rule_weight_changes: number;
  };
};
