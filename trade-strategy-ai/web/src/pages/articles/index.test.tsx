import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { ArticleJobsPage, ArticleListPage, ArticleMaintenancePage, ArticleQualityPage, ArticleResultsPage, ArticleRunPage, ArticlesPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listArticleFilterOptions, listArticles } from '@/lib/api/articles';
import { listJobs } from '@/lib/api/jobs';
import { listProfiles } from '@/lib/api/profiles';
import { runArticlePipeline } from '@/lib/api/pipelines';

vi.mock('@/lib/api/articles', () => ({
  listArticleFilterOptions: vi.fn(),
  listArticles: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  listJobs: vi.fn(),
}));

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
}));

vi.mock('@/lib/api/pipelines', () => ({
  getArticlePipeline: vi.fn(),
  runArticlePipeline: vi.fn(),
}));

const mockedListProfiles = vi.mocked(listProfiles);
const mockedListArticleFilterOptions = vi.mocked(listArticleFilterOptions);
const mockedListArticles = vi.mocked(listArticles);
const mockedListJobs = vi.mocked(listJobs);
const mockedRunArticlePipeline = vi.mocked(runArticlePipeline);

function buildProfileList() {
  return {
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
  };
}

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
        content_text: 'hello article content',
        summary: 'summary one',
        tags: ['trend', 'alpha'],
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
    author_ids: ['author-1', 'author-2'],
    sources: ['tgb', 'xhs'],
    trader_ids: ['trader_a', 'trader_b'],
  };
}

function buildJobList() {
  return {
    count: 1,
    total: 1,
    skip: 0,
    limit: 10,
    items: [
      {
        id: 'job-article-1',
        job_type: 'pipeline-run',
        status: 'success',
        params: { profile_id: 'default', from_step: 'process' },
        result: {
          workflow_run: {
            workflow_id: 'article_pipeline',
            workflow_params: { profile_id: 'default' },
            run_context: { status: 'success', duration_ms: 1250 },
            step_results: [
              { step_name: 'clean' },
              {
                step_name: 'process',
                output_json: {
                  extracted_concepts: ['macd'],
                  trading_symbols: ['AAPL'],
                  strategy_rules: ['rule-1'],
                  preconditions: ['trend'],
                  comment_insights: ['bullish'],
                  sentiment_score: 0.8,
                  confidence_score: 0.9,
                },
              },
            ],
          },
        },
        error: null,
        artifacts: [],
        created_by: 'web',
        idempotency_key: null,
        retry_count: 0,
        max_retries: 0,
        retry_backoff_seconds: 0,
        timeout_seconds: null,
        cancel_requested: false,
        cancel_requested_at: null,
        worker_id: null,
        lock_token: null,
        lock_acquired_at: null,
        heartbeat_at: null,
        scheduled_at: null,
        started_at: '2026-05-10T08:00:00Z',
        finished_at: '2026-05-10T08:20:00Z',
        audit_events: [],
        created_at: '2026-05-10T08:00:00Z',
        updated_at: '2026-05-10T08:20:00Z',
      },
    ],
  };
}

describe('ArticlesPage', () => {
  it('renders workspace entry cards that link to article subpages', async () => {
    renderWithRouter([{ path: '/articles', element: <ArticlesPage /> }], ['/articles']);

    expect(await screen.findByRole('heading', { name: '文章工作台' })).toBeInTheDocument();
    expect(screen.getByText('请选择一个入口开始处理文章数据。')).toBeInTheDocument();
    expect(screen.queryByText('迁移说明')).not.toBeInTheDocument();
    expect(screen.queryByText('导出入口')).not.toBeInTheDocument();
    expect(screen.queryByText('当前状态')).not.toBeInTheDocument();
    expect(screen.queryByText('维护边界')).not.toBeInTheDocument();
    expect(screen.getByText(/从 Profile 触发文章抓取、清洗、校验、入库和结果回看的一条完整流程。/)).toBeInTheDocument();
    expect(screen.getByText('文章浏览与筛选。')).toBeInTheDocument();
    expect(screen.getByText('文章数据质量概览。')).toBeInTheDocument();
    expect(screen.getByText('文章结构化产物。')).toBeInTheDocument();
    expect(screen.getByText('文章维护操作。')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '进入抓取与处理' })).toHaveAttribute('href', '/articles/run');
    expect(screen.getByRole('link', { name: '进入文章列表' })).toHaveAttribute('href', '/articles/list');
    expect(screen.getByRole('link', { name: '进入数据质量' })).toHaveAttribute('href', '/articles/quality');
    expect(screen.getByRole('link', { name: '进入最近任务' })).toHaveAttribute('href', '/articles/jobs');
    expect(screen.getByRole('link', { name: '进入处理结果' })).toHaveAttribute('href', '/articles/results');
    expect(screen.getByRole('link', { name: '进入高级维护' })).toHaveAttribute('href', '/articles/maintenance');
    expect(screen.queryByLabelText('config_path')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '运行 article_pipeline' })).not.toBeInTheDocument();
  });

  it('renders a profile-only run form and submits profile_id', async () => {
    const user = userEvent.setup();
    mockedListProfiles.mockResolvedValue(buildProfileList());
    mockedRunArticlePipeline.mockResolvedValue({
      workflow: { workflow_id: 'article_pipeline', job_type: 'pipeline-run' },
      job: { id: 'job-article-1', job_type: 'pipeline-run', status: 'pending' },
    });

    renderWithRouter([{ path: '/articles/run', element: <ArticleRunPage /> }, { path: '/jobs/:jobId', element: <div>job detail page</div> }], ['/articles/run']);

    expect(await screen.findByRole('heading', { name: '抓取与处理' })).toBeInTheDocument();
    expect(await screen.findByLabelText('Profile')).toBeInTheDocument();
    expect(screen.getByLabelText('Profile')).toHaveValue('default');
    expect(screen.queryByLabelText('config_path')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '运行抓取与处理' }));

    await waitFor(() => {
      expect(mockedRunArticlePipeline).toHaveBeenCalledWith({
        params: { profile_id: 'default' },
        created_by: 'web',
        confirmed: false,
      });
    });

    expect(await screen.findByText('job detail page')).toBeInTheDocument();
  });

  it('renders the article list page with table data and filters', async () => {
    mockedListArticles.mockResolvedValue(buildArticleList());
    mockedListArticleFilterOptions.mockResolvedValue(buildArticleFilterOptions());

    renderWithRouter([{ path: '/articles/list', element: <ArticleListPage /> }], ['/articles/list']);

    expect(await screen.findByRole('heading', { name: '文章列表' })).toBeInTheDocument();
    expect(await screen.findByText('Article One')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Author ID' })).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'Source' })).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'Trader ID' })).toHaveValue('');
    expect(screen.getByRole('combobox', { name: 'Author ID' })).toHaveTextContent('author-1');
    expect(screen.getByRole('combobox', { name: 'Source' })).toHaveTextContent('tgb');
    expect(screen.getByRole('combobox', { name: 'Trader ID' })).toHaveTextContent('trader_a');
    expect(screen.getByRole('link', { name: '查看' })).toHaveAttribute('href', 'https://example.com/article-1');
  });

  it('shows a return action when the article list fails to load', async () => {
    mockedListArticles.mockRejectedValueOnce(new Error('load failed'));
    mockedListArticleFilterOptions.mockResolvedValue(buildArticleFilterOptions());

    renderWithRouter([{ path: '/articles/list', element: <ArticleListPage /> }], ['/articles/list']);

    expect(await screen.findByRole('heading', { name: '文章列表加载失败' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '返回文章列表' })).toBeInTheDocument();
  });

  it('renders the recent job page with article pipeline jobs', async () => {
    mockedListJobs.mockResolvedValue(buildJobList());

    renderWithRouter([{ path: '/articles/jobs', element: <ArticleJobsPage /> }, { path: '/jobs/:jobId', element: <div>job detail page</div> }], ['/articles/jobs']);

    expect(await screen.findByRole('heading', { name: '最近任务' })).toBeInTheDocument();
    expect(await screen.findByText('job-article-1')).toBeInTheDocument();
    expect(screen.getByText(/Profile:\s*default/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '打开 Job Detail' })).toBeInTheDocument();
  });

  it('renders the quality page with coverage metrics and latest job output', async () => {
    mockedListArticles.mockResolvedValue(buildArticleList());
    mockedListJobs.mockResolvedValue(buildJobList());

    renderWithRouter([{ path: '/articles/quality', element: <ArticleQualityPage /> }], ['/articles/quality']);

    expect(await screen.findByRole('heading', { name: '数据质量' })).toBeInTheDocument();
    expect(await screen.findByText('job-article-1')).toBeInTheDocument();
    expect(screen.getByText('最近一次文章 Job')).toBeInTheDocument();
  });

  it('renders the results page with structured process output', async () => {
    mockedListArticles.mockResolvedValue(buildArticleList());
    mockedListJobs.mockResolvedValue(buildJobList());

    renderWithRouter([{ path: '/articles/results', element: <ArticleResultsPage /> }], ['/articles/results']);

    expect(await screen.findByRole('heading', { name: '处理结果' })).toBeInTheDocument();
    expect(await screen.findByText('Article One')).toBeInTheDocument();
    expect(screen.getByText('Process Output')).toBeInTheDocument();
    expect(screen.getByText('最新 process 输出')).toBeInTheDocument();
  });

  it('renders the maintenance page and submits maintenance options', async () => {
    const user = userEvent.setup();
    mockedListProfiles.mockResolvedValue(buildProfileList());
    mockedRunArticlePipeline.mockResolvedValue({
      workflow: { workflow_id: 'article_pipeline', job_type: 'pipeline-run' },
      job: { id: 'job-maintenance-1', job_type: 'pipeline-run', status: 'pending' },
    });

    renderWithRouter(
      [{ path: '/articles/maintenance', element: <ArticleMaintenancePage /> }, { path: '/jobs/:jobId', element: <div>job detail page</div> }],
      ['/articles/maintenance'],
    );

    expect(await screen.findByRole('heading', { name: '高级维护' })).toBeInTheDocument();
    expect(await screen.findByLabelText('Profile')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: '从指定步骤开始' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /导出/i })).not.toBeInTheDocument();
    expect(screen.queryByText('Hash：')).not.toBeInTheDocument();

    await user.selectOptions(screen.getByRole('combobox', { name: '从指定步骤开始' }), 'process');
    expect(screen.getByLabelText('new_version')).toBeInTheDocument();
    expect(screen.queryByLabelText('max_articles')).not.toBeInTheDocument();

    await user.click(screen.getByLabelText('重建 pending tasks'));
    await user.click(screen.getByRole('button', { name: '运行维护' }));

    await waitFor(() => {
      expect(mockedRunArticlePipeline).toHaveBeenCalledWith({
        params: {
          profile_id: 'default',
          from_step: 'process',
          force: true,
          skip_crawl: true,
          use_db: true,
          rebuild_pending: true,
        },
        created_by: 'web',
        confirmed: false,
      });
    });

    expect(await screen.findByText('job detail page')).toBeInTheDocument();
  });
});
