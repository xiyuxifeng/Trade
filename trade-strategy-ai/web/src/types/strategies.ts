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
