export type PersonaClustersResponse = {
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  base_dir: string;
  clusters_path: string;
  trader_count: number;
  clusters_count: number;
};

export type BehaviorRuleCondition = {
  field: string;
  op: string;
  value: string | number | boolean;
  expression: string;
};

export type BehaviorRuleRecord = {
  id: string;
  label: string;
  category: string;
  priority: number;
  enabled: boolean;
  description: string;
  signals: string[];
  conditions: BehaviorRuleCondition[];
  condition_summary: string;
};

export type BehaviorRuleCategorySummary = {
  name: string;
  rule_count: number;
  enabled_rule_count: number;
};

export type BehaviorRulesPreviewResponse = {
  schema_version: string;
  title: string;
  description: string;
  source_path: string;
  rule_count: number;
  enabled_rule_count: number;
  category_count: number;
  categories: BehaviorRuleCategorySummary[];
  rules: BehaviorRuleRecord[];
};
