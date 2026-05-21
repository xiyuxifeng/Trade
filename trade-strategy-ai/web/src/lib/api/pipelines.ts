import { fetchJson } from './http';
import type {
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
