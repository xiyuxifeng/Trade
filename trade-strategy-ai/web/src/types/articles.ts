export type ArticleRecord = {
  id: string;
  source: string;
  source_url: string;
  title: string;
  author_name: string | null;
  author_id: string | null;
  published_at: string | null;
  crawled_at: string;
  content_text: string;
  summary: string | null;
  tags: string[];
  content_hash: string | null;
  view_count: number;
  like_count: number;
  bookmark_count: number;
  comment_count: number;
};

export type ArticleListResponse = {
  items: ArticleRecord[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type ArticleFilterOptionsResponse = {
  author_ids: string[];
  sources: string[];
  trader_ids: string[];
};
