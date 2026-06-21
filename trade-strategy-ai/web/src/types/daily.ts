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

export type TradingDayPlanField = {
  state: 'ready' | 'degraded' | 'unavailable';
  summary: string;
  details: string[];
};

export type TradingPlanRuleDecision = DailyRuleDecision & {
  rule_title?: string | null;
};

export type TradingPlanCandidate = {
  symbol: string;
  name?: string | null;
  rank?: number | null;
  score?: number | null;
  note?: string | null;
  state: 'ready' | 'degraded' | 'unavailable';
};

export type TradingPlanSignal = {
  signal_id?: string | null;
  symbol: string;
  name?: string | null;
  side: 'BUY' | 'SELL' | 'HOLD';
  confidence?: number | null;
  confidence_label: string;
  state: 'ready' | 'degraded' | 'unavailable';
  entry_condition: string;
  invalidation_condition: string;
  stop_loss_take_profit: string;
  suggested_position: string;
  triggered_rule_version_ids: string[];
  degraded_inputs: string[];
  unresolved_inputs: string[];
};

export type TradingDayPlanTraceability = {
  trade_date: string;
  strategy_version_id: string;
  daily_rule_selection_id: string;
  dataset_snapshot_id: string;
  market_snapshot_id: string;
  market_state_id: string;
  current_market_state_label?: string | null;
  rule_applicability_profile_ids: string[];
  author_method_profile_version_id?: string | null;
  author_rule_profile_version_id?: string | null;
  author_validated_profile_version_id?: string | null;
  data_quality_state: string;
  readiness_status: string;
  selected_rules: TradingPlanRuleDecision[];
  reduced_rules: TradingPlanRuleDecision[];
  suspended_rules: TradingPlanRuleDecision[];
  degraded_inputs: string[];
  unresolved_inputs: string[];
};

export type TradingDayPlanResponse = {
  state: 'ready' | 'partial' | 'unavailable';
  plan_status: 'ready' | 'degraded' | 'blocked';
  generated: boolean;
  trade_date: string;
  happened: string;
  affected: string;
  repair_guidance: string;
  daily_strategy_instance_id?: string | null;
  trading_day_plan_id?: string | null;
  daily_rule_selection_id?: string | null;
  revision_no?: number | null;
  strategy_version_id?: string | null;
  instance_lifecycle_state?: string | null;
  plan_lifecycle_state?: string | null;
  approval_state: 'pending' | 'approved' | 'rejected';
  approved_by?: string | null;
  approved_at?: string | null;
  rejection_reason?: string | null;
  market_judgment: TradingDayPlanField;
  enabled_rules: TradingPlanRuleDecision[];
  reduced_rules: TradingPlanRuleDecision[];
  suspended_rules: TradingPlanRuleDecision[];
  candidate_symbols: TradingPlanCandidate[];
  candidate_symbols_state: TradingDayPlanField;
  signals: TradingPlanSignal[];
  entry_conditions: TradingDayPlanField;
  invalidation_conditions: TradingDayPlanField;
  stop_loss_take_profit: TradingDayPlanField;
  suggested_position: TradingDayPlanField;
  risk_warnings: TradingDayPlanField;
  confidence: TradingDayPlanField;
  traceability?: TradingDayPlanTraceability | null;
};

export type TradingDayPlanReviewRequest = {
  action: 'approve' | 'reject';
  reason?: string | null;
};
