import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/http';
import { listArticleFilterOptions, listArticles } from '@/lib/api/articles';
import { listProfiles } from '@/lib/api/profiles';
import {
  getArticlePipeline,
  getArticlePipelineScheduleStatus,
} from '@/lib/api/pipelines';
import { renderWithRouter } from '@/test/test-utils';

import { ResearchAddPage, ResearchArticlesPage, ResearchResultsPage } from './index';

vi.mock('@/lib/api/articles', () => ({
  listArticleFilterOptions: vi.fn(),
  listArticles: vi.fn(),
}));

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
}));

vi.mock('@/lib/api/pipelines', () => ({
  getArticlePipeline: vi.fn(),
  getArticlePipelineScheduleStatus: vi.fn(),
  runArticlePipelineStep: vi.fn(),
  startArticlePipelineSchedule: vi.fn(),
  stopArticlePipelineSchedule: vi.fn(),
}));

const mockedListArticles = vi.mocked(listArticles);
const mockedListArticleFilterOptions = vi.mocked(listArticleFilterOptions);
const mockedListProfiles = vi.mocked(listProfiles);
const mockedGetArticlePipeline = vi.mocked(getArticlePipeline);
const mockedGetArticlePipelineScheduleStatus = vi.mocked(getArticlePipelineScheduleStatus);

function buildArticleList() {
  return {
    items: [
      {
        id: 'article-1',
        source: 'tgb',
        source_url: 'https://example.com/article-1',
        title: 'Article One',
        author_name: 'Alice',
        author_id: 'author-1',
        published_at: '2026-05-10T08:00:00Z',
        crawled_at: '2026-05-10T09:00:00Z',
        content_text: 'content',
        summary: 'summary',
        tags: ['trend'],
        content_hash: 'hash-1',
        view_count: 10,
        like_count: 2,
        bookmark_count: 1,
        comment_count: 3,
      },
    ],
    total: 1,
    page: 1,
    page_size: 10,
    pages: 1,
  };
}

function buildArticleFilterOptions() {
  return {
    author_ids: ['author-1'],
    sources: ['tgb'],
    trader_ids: ['trader_a'],
  };
}

async function expectNoForbiddenTerms() {
  for (const forbidden of ['Job', 'Workflow', 'Pipeline', 'Artifact', 'Provider', 'force', 'config_path', 'profile_id']) {
    expect(screen.queryByText(forbidden)).not.toBeInTheDocument();
  }
}

describe('research pages', () => {
  it('renders the article library in ready state without technical labels', async () => {
    mockedListArticles.mockResolvedValue(buildArticleList());
    mockedListArticleFilterOptions.mockResolvedValue(buildArticleFilterOptions());

    renderWithRouter([{ path: '/research/articles', element: <ResearchArticlesPage /> }], ['/research/articles']);

    expect(await screen.findByRole('heading', { name: '文章库' })).toBeInTheDocument();
    expect(screen.getByText('页面用途')).toBeInTheDocument();
    expect(screen.getByText('输入')).toBeInTheDocument();
    expect(screen.getByText('处理状态')).toBeInTheDocument();
    expect(screen.getByText('输出')).toBeInTheDocument();
    expect(screen.queryByText('下一步')).not.toBeInTheDocument();
    await expectNoForbiddenTerms();
  });

  it('shows loading for the article library while data is pending', async () => {
    mockedListArticles.mockReturnValue(new Promise(() => {}) as never);
    mockedListArticleFilterOptions.mockReturnValue(new Promise(() => {}) as never);

    renderWithRouter([{ path: '/research/articles', element: <ResearchArticlesPage /> }], ['/research/articles']);

    expect(await screen.findByText('页面内容正在获取中，请稍后再看。')).toBeInTheDocument();
    await expectNoForbiddenTerms();
  });

  it('shows empty state for the article library when no articles are available', async () => {
    mockedListArticles.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
      pages: 0,
    });
    mockedListArticleFilterOptions.mockResolvedValue(buildArticleFilterOptions());

    renderWithRouter([{ path: '/research/articles', element: <ResearchArticlesPage /> }], ['/research/articles']);

    expect(await screen.findByText('暂无内容')).toBeInTheDocument();
    await expectNoForbiddenTerms();
  });

  it('shows permission denied for add article when the operator profile cannot be loaded', async () => {
    mockedListProfiles.mockRejectedValueOnce(new ApiError(403, 'forbidden'));
    mockedGetArticlePipeline.mockResolvedValue({
      pipeline: {
        pipeline_id: 'article_pipeline',
        workflow_id: 'article_pipeline',
        job_type: 'pipeline-run',
        title: 'article_pipeline',
        description: 'desc',
        workflow: { workflow_id: 'article_pipeline', title: '文章处理链路', description: 'desc', job_type: 'pipeline-run', permissions: 'operator', steps: [] },
      },
    });
    mockedGetArticlePipelineScheduleStatus.mockResolvedValue({
      scheduler_started: false,
      schedule_time: null,
      force: false,
      profile_id: null,
    });

    renderWithRouter([{ path: '/research/add', element: <ResearchAddPage /> }], ['/research/add']);

    expect(await screen.findByText('当前账号没有查看这部分内容的权限。')).toBeInTheDocument();
    await expectNoForbiddenTerms();
  });

  it('shows unavailable for add article when the pipeline detail service is unavailable', async () => {
    mockedListProfiles.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 100,
      items: [
        {
          profile_id: 'default',
          name: 'Default Profile',
          environment: 'production',
          version: 1,
          sections: {},
          secret_refs: {},
          validation_status: 'validated',
          created_by: 'web',
          created_at: '2026-05-10T08:00:00Z',
          updated_at: '2026-05-10T08:00:00Z',
          archived_at: null,
        },
      ],
    });
    mockedGetArticlePipeline.mockRejectedValueOnce(new ApiError(503, 'service unavailable'));
    mockedGetArticlePipelineScheduleStatus.mockResolvedValue({
      scheduler_started: false,
      schedule_time: null,
      force: false,
      profile_id: null,
    });

    renderWithRouter([{ path: '/research/add', element: <ResearchAddPage /> }], ['/research/add']);

    expect(await screen.findByText('相关服务或数据暂时不可用。')).toBeInTheDocument();
    await expectNoForbiddenTerms();
  });

  it('renders partial extraction results when the detail panel cannot load', async () => {
    renderWithRouter(
      [{ path: '/research/results', element: <ResearchResultsPage availability="partial" /> }],
      ['/research/results'],
    );

    expect(await screen.findAllByText('部分完成')).toHaveLength(2);
    expect(screen.getByText('你看到的是当前可用的部分结果。')).toBeInTheDocument();
    await expectNoForbiddenTerms();
  });

  it('keeps extraction results on the workflow layout when availability is partial', async () => {
    renderWithRouter(
      [{ path: '/research/results', element: <ResearchResultsPage availability="partial" /> }],
      ['/research/results'],
    );

    expect(await screen.findByRole('heading', { name: '提取结果' })).toBeInTheDocument();
    expect(screen.getByText('输入')).toBeInTheDocument();
    expect(screen.getByText('处理状态')).toBeInTheDocument();
    expect(screen.getByText('输出')).toBeInTheDocument();
    expect(screen.getByText('下一步')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回研究中心' })).toHaveAttribute('href', '/research');
  });
});
