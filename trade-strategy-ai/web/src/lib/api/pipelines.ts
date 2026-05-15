import { fetchJson } from './http';
import type { PipelineDetailResponse, PipelineRunRequest, PipelineRunResponse } from '@/types/pipeline';

export function getArticlePipeline() {
  return fetchJson<PipelineDetailResponse>('/pipelines/article_pipeline');
}

export function runArticlePipeline(request: PipelineRunRequest) {
  return fetchJson<PipelineRunResponse>('/pipelines/article_pipeline/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
