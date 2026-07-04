export type ApiErrorPayload = {
  detail?: string;
  message?: string;
  error?: string;
  [key: string]: unknown;
};

export type ApiErrorShape = {
  status: number;
  message: string;
  payload?: ApiErrorPayload;
};

export type SystemDirectoryStatus = {
  path: string;
  exists: boolean;
};

export type DatabaseHealthStatus = {
  name: string;
  status: 'ok' | 'warning' | 'error';
  latency_ms?: number | null;
  details?: Record<string, unknown>;
  error?: string | null;
};

export type SystemHealthComponentStatus = {
  name: string;
  status: 'ok' | 'warning' | 'error';
  latency_ms?: number | null;
  details?: Record<string, unknown>;
  error?: string | null;
};

export type SystemStatusResponse = {
  status: 'ok';
  profile_context?: {
    profile_id: string | null;
    profile_snapshot_id: string | null;
    source: 'env' | 'unset';
  };
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  project_root: string;
  run_mode: string;
  database: DatabaseHealthStatus;
  directories: Record<string, SystemDirectoryStatus>;
  warnings: string[];
};

export type SystemDashboardFailedJob = {
  id: string;
  job_type: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  duration_seconds?: number | null;
  error_message?: string | null;
  heartbeat_at?: string | null;
};

export type HomeBusinessStatusValue =
  | 'ready'
  | 'pending'
  | 'complete'
  | 'blocked'
  | 'partial'
  | 'unavailable';

export type HomeBusinessStatus = {
  status: HomeBusinessStatusValue;
  value: string | number | boolean | null;
  label: string;
  detail: string;
  source: string;
  updated_at: string | null;
  target_path: string;
  unavailable_reason: string | null;
};

export type SystemDashboardResponse = {
  status: 'ok' | 'partial' | 'error';
  generated_at: string;
  business_date: string | null;
  is_trading_day: boolean | null;
  latest_trading_day: string | null;
  business_status: Record<string, HomeBusinessStatus>;
  next_action: {
    id: string;
    label: string;
    target_path: string;
  };
  profile_id?: string | null;
  profile_snapshot_id?: string | null;
  health: {
    overall: string;
    issues: string[];
    database?: SystemHealthComponentStatus;
    [key: string]: unknown;
  };
  worker: {
    status: 'ok' | 'warning' | 'error';
    heartbeat_at: string | null;
    heartbeat_age_minutes: number | null;
    current_job_id: string | null;
  };
  failed_jobs: SystemDashboardFailedJob[];
  duration_summary: {
    average_seconds: number | null;
    p95_seconds: number | null;
    recent_jobs: Array<{
      id: string;
      job_type: string;
      duration_seconds: number | null;
    }>;
  };
  freshness: {
    sources: Array<{
      source: string;
      entity_type: string;
      last_updated?: string | null;
      freshness_hours?: number | null;
      is_stale: boolean;
    }>;
  };
  alerts: {
    critical: number;
    warning: number;
    latest: Array<Record<string, unknown>>;
  };
  traces: Array<{
    job_id: string;
    request_context: {
      path?: string;
      method?: string;
      client_host?: string | null;
    } | null;
  }>;
  report?: Record<string, unknown>;
};

export type SystemDataReadinessStatus =
  | 'ready'
  | 'running'
  | 'missing'
  | 'partial'
  | 'unavailable'
  | 'invalid'
  | 'conflict'
  | 'insufficient_coverage'
  | 'failed'
  | 'cancelled';

export type SystemDataRepairStep = {
  action: string;
  label: string;
  reason: string;
  target_trade_date: string;
};

export type SystemDataReadinessResponse = {
  profile_id: string | null;
  market: string;
  timezone: string;
  status: SystemDataReadinessStatus;
  summary: string;
  phase: string;
  target_trade_date: string;
  latest_update_at: string | null;
  latest_successful_update_at: string | null;
  repair_available: boolean;
  repair_plan: {
    status: string;
    steps: SystemDataRepairStep[];
  };
  facts: {
    latest_ohlcv_trade_date: string | null;
    latest_indicator_trade_date: string | null;
    dataset_snapshot_status: string;
    pre_market_snapshot_status: string;
    post_close_snapshot_status: string;
    market_state_status: string;
    missing_coverages: string[];
    unavailable_reasons: string[];
  };
};

export type SystemDataScheduleResponse = {
  timezone: string;
  entries: Array<{
    key: string;
    label: string;
    window_start: string;
    window_end: string;
    dependency_order: string[];
  }>;
};

export type SystemDataOperation = {
  operation_id: string;
  label: string;
  action: string;
  status: string;
  target_trade_date: string | null;
  created_at: string | null;
  updated_at: string | null;
  cancel_requested: boolean;
  action_level?: 'notify_only' | 'automatic_retry' | 'admin_approval_required';
  impact?: string;
  repair_guidance?: string;
  admin_details?: {
    run_id: string;
    idempotency_key: string | null;
    operation_fingerprint: string | null;
    retry_policy: {
      retry_count: number;
      max_retries: number;
      backoff_seconds: number;
      retry_after_max_requires_admin: boolean;
    };
    attempt_history: Array<Record<string, unknown>>;
    failure_evidence?: Record<string, unknown> | null;
    last_safe_checkpoint?: Record<string, unknown> | null;
  };
};

export type SystemDataOperationListResponse = {
  count: number;
  items: SystemDataOperation[];
};

export type SystemDataOperationRequest = {
  action: string;
  profile_id?: string | null;
  target_trade_date?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  schedule_key?: string | null;
};

export type SystemDataOperationMutationResponse = {
  created?: boolean;
  operation?: SystemDataOperation;
  [key: string]: unknown;
};

export type SystemRunTraceStep = {
  step_id: string;
  business_label: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  error: string | null;
  retry_count: number | null;
  input_references: Array<{ type: string; id: string; label: string }>;
  output_references: Array<{ type: string; id: string; label: string }>;
  repair_guidance: string;
};

export type SystemPromptCallTrace = {
  run_id: string;
  provider: string | null;
  model: string;
  prompt_version: string;
  schema_version: string;
  input_hash: string;
  validation_state: string;
  retry_count: number;
  tokens: Record<string, number | string>;
  cost: {
    amount: number | null;
    currency: string | null;
  };
  started_at: string | null;
  completed_at: string | null;
  linked_business_object: {
    object_type: string;
    object_id: string | null;
    version_id: string | null;
  };
};

export type SystemDataFetchTrace = {
  source: string;
  provider: string | null;
  snapshot_id?: string | null;
  content_fingerprint?: string | null;
  date_range: {
    date_from: string | null;
    date_to: string | null;
  };
  trade_date: string | null;
  slot: string | null;
  coverage: unknown;
  captured_at: string | null;
  available_at: string | null;
  effective_at: string | null;
  quality_status: string;
  missing_ranges: unknown[];
  repair_guidance: string;
};

export type SystemBacktestTrace = {
  dataset_snapshot_id: string;
  data_fingerprints: {
    dataset: string;
    market_snapshots: string[];
  };
  rule_version: {
    rule_version_id: string | null;
    rule_version_no: number | null;
    rule_version_fingerprint: string | null;
  };
  market_state_model_version: string | null;
  code_version: string;
  decision_time_policy: string;
  reproducibility_fingerprint: string;
  coverage: unknown;
  limitations: string[];
};

export type SystemRunTraceItem = {
  run_id: string;
  business_label: string;
  business_type: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  happened: string;
  reason: string;
  affected: string;
  impact: string;
  blocks_user: boolean;
  repair_guidance: string;
  next_action: {
    label: string;
    target_path: string;
  };
  safe_next_action: {
    label: string;
    target_path: string;
  };
  attempt: {
    attempt_id: string;
    retry_count: number | null;
    state: string;
  };
  steps: SystemRunTraceStep[];
  prompt_calls: SystemPromptCallTrace[];
  data_fetches: SystemDataFetchTrace[];
  backtests: SystemBacktestTrace[];
  linked_records: Array<{ type: string; id: string; label: string }>;
  admin_diagnostics: {
    technical_status: string;
    linked_ids?: Record<string, string[]>;
    payload_fingerprints?: Record<string, string | boolean>;
    raw_metadata?: Record<string, unknown>;
  } | null;
};

export type SystemRunsOverviewSummary = {
  overall_status: 'ready' | 'needs_attention';
  headline: string;
  reason: string;
  impact: string;
  counts: {
    total: number;
    needs_attention: number;
    ready: number;
    partial: number;
    failed: number;
  };
  next_action: {
    label: string;
    target_path: string;
  };
};

export type SystemRunTraceListResponse = {
  summary: SystemRunsOverviewSummary;
  needs_attention: SystemRunTraceItem[];
  history: {
    groups: Array<{
      group_key: string;
      label: string;
      items: SystemRunTraceItem[];
    }>;
    page: {
      limit: number;
      has_more: boolean;
      next_cursor: string | null;
      total_filtered: number;
    };
  };
  filters: {
    applied: {
      status: string;
      business_type: string;
      date_from: string | null;
      date_to: string | null;
    };
    available_statuses?: string[];
    available_business_types?: string[];
  };
};

export type SystemCostControlSummaryResponse = {
  generated_at: string;
  llm_cost_summary: {
    currency: string;
    total_cost: number;
    prompt_run_count: number;
    total_tokens: number;
  };
  budget_warning: {
    status: 'ok' | 'warning';
    message: string;
    enforcement: 'notify_only';
    affected_flows: string[];
  };
  concurrency_limits: Array<{
    task_type: string;
    label: string;
    limit: number;
  }>;
  retry_caps: Array<{
    task_type: string;
    label: string;
    max_retries: number;
  }>;
  prompt_cache_samples: Array<{
    prompt_name: string;
    prompt_version: string;
    schema_version: string;
    model: string;
    input_hash: string;
    retry_count: number;
    cache_status: string;
    invalidation_reasons: string[];
    content_hash_status: string;
    article_revision_id: string | null;
    content_hash: string | null;
  }>;
  backtest_reuse_samples: Array<{
    run_id: string;
    reuse_status: string;
    invalidation_reasons: string[];
    metric_cache_status: string;
    calculation_version: string;
  }>;
  incremental_profile_samples: Array<{
    profile_kind: string;
    author_id: string;
    update_scope: string;
    status: string;
    invalidation_reasons: string[];
  }>;
};

export type SystemRolloutState = {
  state: 'legacy_new_comparison' | 'new_read_only' | 'limited_enablement' | 'new_default' | 'legacy_read_only' | 'retired';
  label: string;
  description: string;
};

export type SystemRolloutSummaryResponse = {
  generated_at: string;
  supported_rollout_states: SystemRolloutState[];
  items: Array<{
    migration_id: string;
    label: string;
    domain: 'database' | 'prompt' | 'batch' | 'routes';
    current_state: SystemRolloutState['state'];
    state_label: string;
    formal_source: string;
    legacy_mode: string;
    duplicate_formal_source_detected: boolean;
    happened: string;
    affected: string;
    repair_guidance: string;
    comparison?: {
      status: 'ready' | 'partial' | 'unavailable';
      pre_counts?: Record<string, number> | null;
      post_counts?: Record<string, number> | null;
      rejected_rows?: number | null;
      conflicted_rows?: number | null;
      legacy_prompt_count?: number;
      raw_output_count?: number;
      current_contract?: {
        prompt_name: string;
        prompt_version: string;
        schema_version: string;
      } | null;
      job_status?: string | null;
      processed_count?: number | null;
      quality_stats?: Record<string, unknown> | null;
      legacy_routes_retired?: boolean;
      legacy_write_enabled?: boolean;
    };
    rollback_or_recovery?: {
      status: 'ready' | 'partial' | 'unavailable';
      mode: string;
      evidence_file_names?: string[];
      no_silent_data_loss?: boolean | null;
      rejected_rows?: number | null;
      conflicted_rows?: number | null;
      current_contract?: {
        prompt_name: string;
        prompt_version: string;
        schema_version: string;
      } | null;
      selected_previous_contract?: {
        prompt_name: string;
        prompt_version: string;
        schema_version: string;
      } | null;
      raw_output_preserved?: boolean;
      legacy_runtime_dispositions?: string[];
      idempotency_key?: string | null;
      resume_point?: string | null;
      processed_items?: Array<Record<string, unknown>>;
      rejected_or_conflicted_items?: string[] | null;
      legacy_routes_retired?: boolean;
      stage12_required_for_retirement?: boolean;
    };
  }>;
};
