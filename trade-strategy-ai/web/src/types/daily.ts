export type PreMarketCheckStatus = 'ready' | 'degraded' | 'blocked';
export type PreMarketPageState = 'ready' | 'partial' | 'unavailable' | 'empty';
export type PreMarketReadinessStatus = 'ready' | 'degraded' | 'blocked';

export type PreMarketRepairAction = {
  label: string;
  to: string;
};

export type PreMarketCheck = {
  code: string;
  label: string;
  status: PreMarketCheckStatus;
  happened: string;
  affected: string;
  repair_guidance: string;
  can_proceed_in_degraded_mode: boolean;
  traceability: Record<string, unknown>;
};

export type PreMarketTraceability = {
  trade_date: string;
  strategy_version_id?: string | null;
  dataset_snapshot_id?: string | null;
  market_snapshot_id?: string | null;
  market_state_id?: string | null;
  rule_applicability_profile_ids: string[];
  author_method_profile_version_id?: string | null;
  author_rule_profile_version_id?: string | null;
  author_validated_profile_version_id?: string | null;
  data_quality_state: string;
};

export type PreMarketReadinessResponse = {
  state: PreMarketPageState;
  readiness_status: PreMarketReadinessStatus;
  trade_date: string;
  slot: string;
  summary_title: string;
  happened: string;
  affected: string;
  repair_guidance: string;
  can_proceed: boolean;
  can_proceed_in_degraded_mode: boolean;
  checks: PreMarketCheck[];
  traceability: PreMarketTraceability;
  repair_actions: PreMarketRepairAction[];
  warnings: string[];
};

export type DailyRuleDecision = {
  rule_version_id: string;
  strategy_rule_membership_id?: string | null;
  decision: 'selected' | 'reduced' | 'suspended';
  controlling_priority_tier: string;
  controlling_priority_label: string;
  evidence_ids: string[];
  quality_states: string[];
  reason_tiers: string[];
  reason_list: string[];
  degraded_inputs: string[];
  unresolved_inputs: string[];
};

export type DailyRuleSelectionTraceability = PreMarketTraceability & {
  readiness_status: string;
};

export type DailyRuleSelectionResponse = {
  state: 'ready' | 'partial' | 'unavailable';
  selection_status: 'ready' | 'degraded' | 'blocked';
  generated: boolean;
  trade_date: string;
  happened: string;
  affected: string;
  repair_guidance: string;
  daily_rule_selection_id?: string | null;
  revision_no?: number | null;
  strategy_version_id: string;
  quality_status: string;
  readiness_status: string;
  enabled_rules: DailyRuleDecision[];
  reduced_rules: DailyRuleDecision[];
  suspended_rules: DailyRuleDecision[];
  traceability: DailyRuleSelectionTraceability;
  degraded_inputs: string[];
  unresolved_inputs: string[];
};
