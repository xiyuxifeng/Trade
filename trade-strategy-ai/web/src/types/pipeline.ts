import type { WorkflowStep } from './workflows';

export type PipelineParamsSchemaField = {
  type: string;
  description?: string;
  required?: boolean;
  enum?: string[];
};

export type PipelineWorkflowDefinition = {
  workflow_id: string;
  title: string;
  description: string;
  job_type: string;
  permissions?: string;
  job_definition?: {
    job_type: string;
    risk?: string;
    requires_confirmation?: boolean;
    params_schema?: {
      description?: string;
      allow_additional_fields?: boolean;
      fields?: Record<string, PipelineParamsSchemaField>;
    };
  };
  steps: WorkflowStep[];
};

export type PipelineSummary = {
  pipeline_id: string;
  workflow_id: string;
  job_type: string;
  title: string;
  description: string;
};

export type PipelineDetail = PipelineSummary & {
  workflow: PipelineWorkflowDefinition;
};

export type PipelineListResponse = {
  count: number;
  items: PipelineSummary[];
};

export type PipelineDetailResponse = {
  pipeline: PipelineDetail;
};

export type PipelineRunRequest = {
  params: Record<string, unknown>;
  created_by?: string;
  idempotency_key?: string | null;
  confirmed?: boolean;
};

export type ArticlePipelineRunParams = {
  profile_id: string;
  max_articles?: number;
  force?: boolean;
  skip_crawl?: boolean;
  from_step?: string;
  use_db?: boolean;
  cleanup?: boolean;
  rebuild_pending?: boolean;
  retry_failed?: boolean;
};

export type ArticlePipelineRunRequest = {
  params: ArticlePipelineRunParams;
  created_by?: string;
  idempotency_key?: string | null;
  confirmed?: boolean;
};

export type ArticlePipelineStepRunRequest = {
  params: Record<string, unknown>;
  created_by?: string;
  idempotency_key?: string | null;
  confirmed?: boolean;
};

export type ArticlePipelineScheduleRequest = {
  profile_id?: string;
  schedule_time?: string;
  force?: boolean;
};

export type ArticlePipelineScheduleState = {
  scheduler_started: boolean;
  schedule_time: string | null;
  force: boolean;
  profile_id: string | null;
};

export type PipelineRunResponse = {
  workflow: {
    workflow_id: string;
    job_type: string;
  };
  job: {
    id: string;
    job_type: string;
    status: string;
  };
};
