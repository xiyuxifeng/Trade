import type { JobRecord } from '@/types/jobs';

export type WorkflowParamField = {
  type: string;
  description: string;
  required: boolean;
  default?: unknown;
  enum: string[];
};

export type WorkflowParamSchema = {
  description: string;
  fields: Record<string, WorkflowParamField>;
  allow_additional_fields: boolean;
};

export type WorkflowJobDefinition = {
  job_type: string;
  title: string;
  description: string;
  summary: string;
  permission: string;
  risk: string;
  can_retry: boolean;
  can_run_concurrently: boolean;
  concurrency_group: string;
  requires_confirmation: boolean;
  runnable: boolean;
  params_schema?: WorkflowParamSchema;
};

export type WorkflowStep = {
  step_id: string;
  title: string;
  description: string;
  required_job_type: string;
  parameters: string[];
  param_schema: WorkflowParamSchema;
  risk: string;
  requires_confirmation: boolean;
};

export type WorkflowDefinition = {
  workflow_id: string;
  title: string;
  description: string;
  job_type: string;
  permissions: string;
  job_definition: WorkflowJobDefinition | null;
  steps: WorkflowStep[];
};

export type WorkflowsListResponse = {
  count: number;
  items: WorkflowDefinition[];
};

export type WorkflowDetailResponse = {
  workflow: WorkflowDefinition;
};

export type WorkflowRunRequest = {
  params: Record<string, unknown>;
  created_by?: string;
  idempotency_key?: string;
  confirmed?: boolean;
};

export type WorkflowRunResponse = {
  workflow: WorkflowDefinition;
  job: JobRecord;
  job_dir?: string;
  log_path?: string;
  params_path?: string;
  result_path?: string;
  artifacts_path?: string;
};
