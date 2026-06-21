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
