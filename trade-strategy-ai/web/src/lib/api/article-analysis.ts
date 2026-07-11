import { fetchJson } from './http';
import type {
  ArticleProcessingStatus,
  ArticleAnalysisDetail,
  ReviewExtractionItemRequest,
  RunArticleAnalysisRequest,
  UpdateArticleProcessingStatusRequest,
} from '@/types/article-analysis';

export function getArticleAnalysis(articleId: string, query: { article_revision_id?: string } = {}) {
  const params = new URLSearchParams();
  if (query.article_revision_id) {
    params.set('article_revision_id', query.article_revision_id);
  }
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<ArticleAnalysisDetail>(`/article-analysis/articles/${encodeURIComponent(articleId)}/analysis${suffix}`);
}

export function runArticleAnalysis(articleId: string, request: RunArticleAnalysisRequest = {}) {
  return fetchJson<ArticleAnalysisDetail>(`/article-analysis/articles/${encodeURIComponent(articleId)}/analysis`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}

export function reviewExtractionItem(articleId: string, itemId: string, request: ReviewExtractionItemRequest) {
  return fetchJson<ArticleAnalysisDetail>(
    `/article-analysis/articles/${encodeURIComponent(articleId)}/extraction-items/${encodeURIComponent(itemId)}/review`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
  );
}

export function updateArticleProcessingStatus(articleId: string, request: UpdateArticleProcessingStatusRequest) {
  return fetchJson<ArticleProcessingStatus>(`/article-analysis/articles/${encodeURIComponent(articleId)}/processing-status`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
