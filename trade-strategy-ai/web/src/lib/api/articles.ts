import { fetchJson } from './http';
import type { ArticleListResponse } from '@/types/articles';

type ArticleListQuery = {
  page?: number;
  page_size?: number;
  author_id?: string;
  source?: string;
  trader_id?: string;
  published_after?: string;
  published_before?: string;
};

export function listArticles(query: ArticleListQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<ArticleListResponse>(`/articles${suffix}`);
}

