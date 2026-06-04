import { fetchJson } from './http';
import type {
  ArticleMetadataListResponse,
  ArticleMetadataResolution,
  ArticleMetadataResolutionListResponse,
  ArticleMetadataSelectRequest,
} from '@/types/article-metadata';

export function listArticleMetadataSummary(articleIds: string[]) {
  const params = new URLSearchParams();
  articleIds.forEach((articleId) => {
    if (articleId && articleId.trim()) {
      params.append('article_ids', articleId.trim());
    }
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<ArticleMetadataResolutionListResponse>(`/article-metadata/summary${suffix}`);
}

export function listArticleMetadataArticles(query: {
  page?: number;
  page_size?: number;
  selection_status?: 'all' | 'selected' | 'unselected';
  search?: string;
} = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<ArticleMetadataListResponse>(`/article-metadata/articles${suffix}`);
}

export function getArticleMetadataSummary(articleId: string) {
  return fetchJson<ArticleMetadataResolution>(`/article-metadata/articles/${encodeURIComponent(articleId)}`);
}

export function selectArticleMetadataVersion(articleId: string, request: ArticleMetadataSelectRequest) {
  return fetchJson<ArticleMetadataResolution>(`/article-metadata/articles/${encodeURIComponent(articleId)}/select`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
