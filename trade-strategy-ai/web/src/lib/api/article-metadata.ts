import { fetchJson } from './http';
import type {
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
