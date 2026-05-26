import { fetchJson } from './http';
import type {
  ArticlePipelineScheduleRequest,
  ArticlePipelineScheduleState,
  ArticlePipelineStepRunRequest,
  ArticlePipelineRunRequest,
  PipelineDetailResponse,
  PipelineRunResponse,
} from '@/types/pipeline';

export function getArticlePipeline() {
  return fetchJson<PipelineDetailResponse>('/pipelines/article_pipeline');
}

export function runArticlePipeline(request: ArticlePipelineRunRequest) {
  return fetchJson<PipelineRunResponse>('/pipelines/article_pipeline/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function runArticlePipelineStep(stepId: string, request: ArticlePipelineStepRunRequest) {
  return fetchJson<PipelineRunResponse>(`/pipelines/article_pipeline/steps/${encodeURIComponent(stepId)}/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function getArticlePipelineScheduleStatus() {
  return fetchJson<ArticlePipelineScheduleState>('/pipelines/article_pipeline/schedule/status');
}

export function startArticlePipelineSchedule(request: ArticlePipelineScheduleRequest) {
  return fetchJson<ArticlePipelineScheduleState>('/pipelines/article_pipeline/schedule/start', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function stopArticlePipelineSchedule(request: ArticlePipelineScheduleRequest) {
  return fetchJson<ArticlePipelineScheduleState>('/pipelines/article_pipeline/schedule/stop', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
