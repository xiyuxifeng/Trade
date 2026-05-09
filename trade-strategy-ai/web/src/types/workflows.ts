export type WorkflowStep = {
  step_id: string;
  title: string;
  description: string;
  required_job_type: string;
  parameters: string[];
  risk: string;
  requires_confirmation: boolean;
};

export type WorkflowDefinition = {
  workflow_id: string;
  title: string;
  description: string;
  job_type: string;
  permissions: string;
  job_definition: {
    job_type: string;
    summary: string;
    params_schema?: Record<string, unknown>;
  } | null;
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
};

export type WorkflowRunResponse = {
  workflow: WorkflowDefinition;
  job: Record<string, unknown>;
  job_dir?: string;
  log_path?: string;
  params_path?: string;
  result_path?: string;
  artifacts_path?: string;
};
