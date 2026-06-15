import { fetchJson } from './http';
import type {
  ArticleAnalysisDetail,
  ReviewArticleCandidateRequest,
  RunArticleAnalysisRequest,
} from '@/types/article-analysis';

export function getArticleAnalysis(articleId: string, query: { article_revision_id?: string } = {}) {
  const params = new URLSearchParams();
  if (query.article_revision_id) {
    params.set('article_revision_id', query.article_revision_id);
  }
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<ArticleAnalysisDetail>(`/article-metadata/articles/${encodeURIComponent(articleId)}/analysis${suffix}`);
}

export function runArticleAnalysis(articleId: string, request: RunArticleAnalysisRequest = {}) {
  return fetchJson<ArticleAnalysisDetail>(`/article-metadata/articles/${encodeURIComponent(articleId)}/analysis`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function reviewArticleCandidate(articleId: string, candidateId: string, request: ReviewArticleCandidateRequest) {
  return fetchJson<ArticleAnalysisDetail>(
    `/article-metadata/articles/${encodeURIComponent(articleId)}/candidates/${encodeURIComponent(candidateId)}/review`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
  );
}
