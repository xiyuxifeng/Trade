import { fetchRootJson } from './http';
import type { ArticleFilterOptionsResponse, ArticleListResponse, ArticleQualitySummaryResponse } from '@/types/articles';

export type ArticleListQuery = {
  page?: number;
  page_size?: number;
  author_id?: string;
  source?: string;
  trader_id?: string;
  published_after?: string;
  published_before?: string;
  processing_status?: 'all' | 'processed' | 'unprocessed' | 'failed' | 'manual_review_required' | 'ignored';
};

type ArticleFilterOptionsQuery = Omit<ArticleListQuery, 'page' | 'page_size'>;

export function listArticles(query: ArticleListQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchRootJson<ArticleListResponse>(`/articles${suffix}`);
}

export function listArticleFilterOptions(query: ArticleFilterOptionsQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchRootJson<ArticleFilterOptionsResponse>(`/articles/filter-options${suffix}`);
}

export function getArticleQualitySummary() {
  return fetchRootJson<ArticleQualitySummaryResponse>('/articles/quality');
}
