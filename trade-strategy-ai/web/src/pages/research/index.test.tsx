import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/lib/api/http';
import { getArticleAnalysis, reviewArticleCandidate } from '@/lib/api/article-analysis';
import { listArticleFilterOptions, listArticles } from '@/lib/api/articles';
import { listJobDefinitions, listJobs } from '@/lib/api/jobs';
import { listProfiles } from '@/lib/api/profiles';
import { runArticlePipeline, runArticlePipelineStep } from '@/lib/api/pipelines';
import { toast } from '@/components/ui/toast';
import {
  getArticlePipeline,
  getArticlePipelineScheduleStatus,
} from '@/lib/api/pipelines';
import { renderWithRouter } from '@/test/test-utils';
import type { PipelineRunResponse } from '@/types/pipeline';

import { ResearchAddPage, ResearchArticlesPage, ResearchResultsPage } from './index';

vi.mock('@/lib/api/articles', () => ({
  listArticleFilterOptions: vi.fn(),
  listArticles: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  cancelJob: vi.fn(),
  listJobDefinitions: vi.fn(),
  listJobs: vi.fn(),
  pauseJob: vi.fn(),
  resumeJob: vi.fn(),
  retryJob: vi.fn(),
}));

vi.mock('@/lib/api/article-analysis', () => ({
  getArticleAnalysis: vi.fn(),
  reviewArticleCandidate: vi.fn(),
  runArticleAnalysis: vi.fn(),
}));

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
}));

vi.mock('@/components/ui/toast', () => ({
  toast: vi.fn(),
}));

vi.mock('@/lib/api/pipelines', () => ({
  getArticlePipeline: vi.fn(),
  getArticlePipelineScheduleStatus: vi.fn(),
  runArticlePipelineStep: vi.fn(),
  runArticlePipeline: vi.fn(),
  startArticlePipelineSchedule: vi.fn(),
  stopArticlePipelineSchedule: vi.fn(),
}));

const mockedListArticles = vi.mocked(listArticles);
const mockedListArticleFilterOptions = vi.mocked(listArticleFilterOptions);
const mockedGetArticleAnalysis = vi.mocked(getArticleAnalysis);
const mockedReviewArticleCandidate = vi.mocked(reviewArticleCandidate);
const mockedListJobDefinitions = vi.mocked(listJobDefinitions);
const mockedListJobs = vi.mocked(listJobs);
const mockedListProfiles = vi.mocked(listProfiles);
const mockedRunArticlePipelineStep = vi.mocked(runArticlePipelineStep);
const mockedRunArticlePipeline = vi.mocked(runArticlePipeline);
const mockedGetArticlePipeline = vi.mocked(getArticlePipeline);
const mockedGetArticlePipelineScheduleStatus = vi.mocked(getArticlePipelineScheduleStatus);
const mockedToast = vi.mocked(toast);

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

function buildJobDefinitions() {
  return [
    {
      job_type: 'pipeline-run',
      title: '文章导入任务',
      service_name: 'jobs',
      handler_name: 'run',
      permission: 'operator',
      risk: 'medium',
      can_retry: true,
      can_pause: true,
      can_resume: true,
      can_cancel: true,
      can_run_concurrently: true,
      concurrency_group: 'articles',
      requires_confirmation: false,
      runnable: true,
      description: '导入文章并处理。',
      param_schema: {},
    },
  ];
}

function buildJobsList() {
  return {
    count: 1,
    total: 1,
    skip: 0,
    limit: 10,
    status_counts: {
      pending: 0,
      running: 1,
      paused: 0,
      success: 0,
      failed: 0,
      cancelled: 0,
    },
    items: [
      {
        id: 'job-1',
        job_type: 'pipeline-run',
        status: 'running',
        params: {},
        result: null,
        error: null,
        runtime_state: null,
        progress: {
          job_type: 'pipeline-run',
          stage: 'import',
          current: 1,
          total: 3,
          percent: 33,
          remaining: 2,
          updated_at: '2026-05-10T08:10:00Z',
          current_trade_date: null,
          current_slot: null,
          current_fetcher: null,
          current_dataset: null,
          current_step: 'import_article',
          status: 'running',
          error: null,
        },
        artifacts: [],
        created_by: 'web',
        idempotency_key: null,
        retry_count: 0,
        max_retries: 3,
        retry_backoff_seconds: 5,
        timeout_seconds: null,
        cancel_requested: false,
        cancel_requested_at: null,
        worker_id: null,
        lock_token: null,
        lock_acquired_at: null,
        heartbeat_at: null,
        scheduled_at: null,
        started_at: '2026-05-10T08:10:00Z',
        finished_at: null,
        audit_events: [],
        created_at: '2026-05-10T08:10:00Z',
        updated_at: '2026-05-10T08:10:00Z',
      },
    ],
  };
}

function buildArticleAnalysisDetail() {
  return {
    status: 'ready' as const,
    warning: null,
    message: null,
    article: {
      article_id: 'article-1',
      article_revision_id: 'revision-1',
      content_hash: 'hash-1',
      title: 'Article One',
      source: 'tgb',
      source_url: 'https://example.com/article-1',
      author_name: 'Alice',
      author_id: 'author-1',
      published_at: '2026-05-10T08:00:00Z',
      crawled_at: '2026-05-10T09:00:00Z',
      original_text: 'original',
      cleaned_content: 'cleaned',
      summary: 'summary',
      tags: ['trend'],
    },
    summary_provenance: {
      source: 'blog_article_current' as const,
      article_revision_id: 'revision-1',
      content_hash: 'hash-1',
      available: true,
      aligned: true,
      reason: null,
    },
    article_structure_provenance: {
      article_structure_id: 'structure-1',
      article_revision_id: 'revision-1',
      prompt_run_id: 'prompt-run-1',
      prompt_name: 'article_analysis_v1',
      prompt_version: 'v1',
      schema_name: 'article_analysis',
      schema_version: 'v1',
      available: true,
    },
    method_tags: ['trend'],
    explicit_facts: [{ fact: 'explicit' }],
    hypotheses: [{ hypothesis: 'inferred' }],
    missing_fields: {},
    prompt_trace: {
      run_id: 'prompt-run-1',
      prompt_name: 'article_analysis_v1',
      prompt_version: 'v1',
      schema_name: 'article_analysis',
      schema_version: 'v1',
      provider: 'openai',
      model: 'gpt-5',
      validation_state: 'valid',
      retry_count: 0,
      token_usage: {},
      cost_amount: null,
      cost_currency: null,
      started_at: '2026-05-10T10:00:00Z',
      completed_at: '2026-05-10T10:01:00Z',
    },
    candidates: [
      {
        candidate_id: 'candidate-1',
        candidate_index: 0,
        title: '突破规则',
        rule_type: 'entry',
        explicit_facts: { condition: 'breakout' },
        hypotheses: {},
        missing_fields: {},
        evidence: { quote: '突破' },
        data_dependencies: { ohlcv: true },
        backtestability_status: 'backtestable',
        kaipan_dependency: false,
        market_state_declaration_status: 'not_declared',
        automatic_review: {
          status: 'needs_human_review' as const,
          reasons: ['需要人工确认参数'],
          risk_level: 'medium' as const,
        },
        human_review: {
          review_state: 'pending',
          formal_rule_created: false,
          rule_version_id: null,
          formal_lifecycle_state: null,
          stage3_status: null,
        },
        governance: {
          algorithm_version: 'v1',
          exact_fingerprint: 'exact-1',
          family_fingerprint: 'family-1',
          family_key: 'breakout',
          exact_duplicate_of_rule_version_id: null,
          eligible_for_formal_version: true,
          eligible_for_backtest: true,
          related_rules: [],
        },
      },
    ],
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
    expect(screen.getByRole('heading', { name: '文章列表' })).toBeInTheDocument();
    expect(screen.queryByText('输入')).not.toBeInTheDocument();
    expect(screen.queryByText('处理状态')).not.toBeInTheDocument();
    expect(screen.queryByText('输出')).not.toBeInTheDocument();
    expect(screen.queryByText('返回文章条目、摘要、发布时间、标签和原文链接。')).not.toBeInTheDocument();
    expect(screen.queryByText('下一步')).not.toBeInTheDocument();
    await expectNoForbiddenTerms();
  });

  it('shows loading for the article library while data is pending', async () => {
    mockedListArticles.mockReturnValue(new Promise(() => {}) as never);
    mockedListArticleFilterOptions.mockReturnValue(new Promise(() => {}) as never);

    renderWithRouter([{ path: '/research/articles', element: <ResearchArticlesPage /> }], ['/research/articles']);

    expect(await screen.findByText('页面内容正在获取中，请稍后再看。')).toBeInTheDocument();
    expect(screen.queryByText('页面用途')).not.toBeInTheDocument();
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
    expect(screen.queryByText('页面用途')).not.toBeInTheDocument();
    await expectNoForbiddenTerms();
  });

  it('shows permission denied for add article when the operator profile cannot be loaded', async () => {
    mockedListJobDefinitions.mockResolvedValue(buildJobDefinitions());
    mockedListJobs.mockResolvedValue(buildJobsList());
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
    mockedListJobDefinitions.mockResolvedValue(buildJobDefinitions());
    mockedListJobs.mockResolvedValue(buildJobsList());
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

  it('renders add article with one-click card, collapsed step area and task management', async () => {
    mockedListJobDefinitions.mockResolvedValue(buildJobDefinitions());
    mockedListJobs.mockResolvedValue(buildJobsList());
    mockedRunArticlePipeline.mockResolvedValue({
      job: { id: 'job-pipeline-1', job_type: 'pipeline-run', status: 'pending' },
    } as PipelineRunResponse);
    mockedListProfiles.mockResolvedValue({
      count: 2,
      total: 2,
      skip: 0,
      limit: 100,
      items: [
        {
          profile_id: 'archived',
          name: 'Archived Profile',
          environment: 'production',
          version: 0,
          sections: {},
          secret_refs: {},
          validation_status: 'archived',
          created_by: 'web',
          created_at: '2026-05-09T08:00:00Z',
          updated_at: '2026-05-09T08:00:00Z',
          archived_at: '2026-05-09T08:00:00Z',
        },
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
    mockedGetArticlePipeline.mockResolvedValue({
      pipeline: {
        pipeline_id: 'article_pipeline',
        workflow_id: 'article_pipeline',
        job_type: 'pipeline-run',
        title: 'article_pipeline',
        description: 'desc',
        workflow: {
          workflow_id: 'article_pipeline',
          title: '文章处理链路',
          description: 'desc',
          job_type: 'pipeline-run',
          permissions: 'operator',
          steps: [
            {
              step_id: 'import_article',
              title: '导入单篇文章',
              description: '导入单篇文章并开始处理。',
              required_job_type: 'pipeline-run',
              parameters: ['source_url', 'dry_run'],
              risk: 'medium',
              requires_confirmation: false,
              param_schema: {
                description: '文章导入任务参数',
                allow_additional_fields: false,
                fields: {
                  source_url: { type: 'string', description: '文章链接', required: false, enum: [] },
                  dry_run: { type: 'boolean', description: '只校验不提交', default: false, required: false, enum: [] },
                },
              },
            },
          ],
        },
      },
    });
    mockedGetArticlePipelineScheduleStatus.mockResolvedValue({
      scheduler_started: false,
      schedule_time: null,
      force: false,
      profile_id: null,
    });

    renderWithRouter([{ path: '/research/add', element: <ResearchAddPage /> }], ['/research/add']);

    expect(await screen.findByRole('heading', { name: '开始添加' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText('页面内容正在获取中，请稍后再看。')).not.toBeInTheDocument();
    });
    expect(screen.getByText('一键处理未完成文章')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '开始一键处理' })).toBeInTheDocument();
    expect(screen.getByText('分步处理')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '任务管理' })).toBeInTheDocument();
    expect(screen.queryByText('页面用途')).not.toBeInTheDocument();
    expect(screen.queryByText('处理状态')).not.toBeInTheDocument();
    expect(screen.getByLabelText('当前配置')).toBeInTheDocument();
    expect(screen.getByLabelText('当前配置')).toHaveValue('default');
    expect(screen.queryByText('Archived Profile')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('任务')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('source_url')).not.toBeInTheDocument();
    expect(screen.queryByRole('checkbox', { name: 'dry_run' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '确认提交' })).not.toBeInTheDocument();
    expect(screen.queryByText('当前任务')).not.toBeInTheDocument();
    expect(screen.queryByText('最近任务数')).not.toBeInTheDocument();
  });

  it('expands step processing area and keeps the original step submission flow', async () => {
    const user = userEvent.setup();
    mockedListJobDefinitions.mockResolvedValue(buildJobDefinitions());
    mockedListJobs.mockResolvedValue(buildJobsList());
    mockedRunArticlePipeline.mockResolvedValue({
      job: { id: 'job-pipeline-1', job_type: 'pipeline-run', status: 'pending' },
    } as PipelineRunResponse);
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
    mockedGetArticlePipeline.mockResolvedValue({
      pipeline: {
        pipeline_id: 'article_pipeline',
        workflow_id: 'article_pipeline',
        job_type: 'pipeline-run',
        title: 'article_pipeline',
        description: 'desc',
        workflow: {
          workflow_id: 'article_pipeline',
          title: '文章处理链路',
          description: 'desc',
          job_type: 'pipeline-run',
          permissions: 'operator',
          steps: [
            {
              step_id: 'import_article',
              title: '导入单篇文章',
              description: '导入单篇文章并开始处理。',
              required_job_type: 'pipeline-run',
              parameters: ['source_url', 'dry_run'],
              risk: 'medium',
              requires_confirmation: false,
              param_schema: {
                description: '文章导入任务参数',
                allow_additional_fields: false,
                fields: {
                  source_url: { type: 'string', description: '文章链接', required: false, enum: [] },
                  dry_run: { type: 'boolean', description: '只校验不提交', default: false, required: false, enum: [] },
                },
              },
            },
          ],
        },
      },
    });
    mockedGetArticlePipelineScheduleStatus.mockResolvedValue({
      scheduler_started: false,
      schedule_time: null,
      force: false,
      profile_id: null,
    });
    mockedRunArticlePipelineStep.mockResolvedValue({
      job: { id: 'job-created-1', job_type: 'pipeline-run', status: 'pending' },
    } as PipelineRunResponse);

    renderWithRouter([{ path: '/research/add', element: <ResearchAddPage /> }], ['/research/add']);

    expect(await screen.findByRole('heading', { name: '开始添加' })).toBeInTheDocument();
    await user.click(screen.getByText('分步处理'));

    expect(await screen.findByLabelText('任务')).toBeInTheDocument();
    expect(await screen.findByLabelText('source_url')).toBeInTheDocument();
    expect(await screen.findByRole('checkbox', { name: 'dry_run' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '确认提交' })).toBeInTheDocument();
  });

  it('shows submitting state and success toast when add article is submitted', async () => {
    const user = userEvent.setup();
    let resolveSubmit: ((value: PipelineRunResponse) => void) | null = null;
    mockedListJobDefinitions.mockResolvedValue(buildJobDefinitions());
    mockedListJobs.mockResolvedValue(buildJobsList());
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
    mockedGetArticlePipeline.mockResolvedValue({
      pipeline: {
        pipeline_id: 'article_pipeline',
        workflow_id: 'article_pipeline',
        job_type: 'pipeline-run',
        title: 'article_pipeline',
        description: 'desc',
        workflow: {
          workflow_id: 'article_pipeline',
          title: '文章处理链路',
          description: 'desc',
          job_type: 'pipeline-run',
          permissions: 'operator',
          steps: [
            {
              step_id: 'import_article',
              title: '导入单篇文章',
              description: '导入单篇文章并开始处理。',
              required_job_type: 'pipeline-run',
              parameters: ['source_url'],
              risk: 'medium',
              requires_confirmation: false,
              param_schema: {
                description: '文章导入任务参数',
                allow_additional_fields: false,
                fields: {
                  source_url: { type: 'string', description: '文章链接', required: false, enum: [] },
                },
              },
            },
          ],
        },
      },
    });
    mockedGetArticlePipelineScheduleStatus.mockResolvedValue({
      scheduler_started: false,
      schedule_time: null,
      force: false,
      profile_id: null,
    });
    mockedRunArticlePipelineStep.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSubmit = resolve;
        }) as ReturnType<typeof runArticlePipelineStep>,
    );

    renderWithRouter([{ path: '/research/add', element: <ResearchAddPage /> }], ['/research/add']);

    expect(await screen.findByRole('heading', { name: '开始添加' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText('页面内容正在获取中，请稍后再看。')).not.toBeInTheDocument();
    });

    await user.click(screen.getByText('分步处理'));
    await user.type(screen.getByLabelText('source_url'), 'https://example.com/article-2');
    await user.click(screen.getByRole('button', { name: '确认提交' }));

    const submittingButton = screen.getByRole('button', { name: '提交中' });
    expect(submittingButton).toBeDisabled();
    expect(submittingButton.querySelector('.animate-spin')).not.toBeNull();

    expect(resolveSubmit).not.toBeNull();
    ((resolveSubmit as unknown) as (value: PipelineRunResponse) => void)({
      job: { id: 'job-created-1', job_type: 'pipeline-run', status: 'pending' },
      workflow: {
        workflow_id: 'article_pipeline',
        job_type: 'pipeline-run',
      },
    });

    await waitFor(() => {
      expect(mockedToast).toHaveBeenCalledWith({
        title: '文章已添加',
        description: '文章任务已创建，你可以在当前页面继续查看进度和管理任务。',
      });
    });
    expect(await screen.findByText('最近创建任务：job-created-1')).toBeInTheDocument();
  });

  it('keeps showing running pipeline jobs after refresh even when the default step uses a different job type', async () => {
    mockedListJobDefinitions.mockResolvedValue(buildJobDefinitions());
    mockedListJobs.mockImplementation(async (query) => {
      if (query?.job_type === 'crawl') {
        return {
          count: 0,
          total: 0,
          skip: 0,
          limit: 10,
          status_counts: {
            pending: 0,
            running: 0,
            paused: 0,
            success: 0,
            failed: 0,
            cancelled: 0,
          },
          items: [],
        };
      }
      return buildJobsList();
    });
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
    mockedGetArticlePipeline.mockResolvedValue({
      pipeline: {
        pipeline_id: 'article_pipeline',
        workflow_id: 'article_pipeline',
        job_type: 'pipeline-run',
        title: 'article_pipeline',
        description: 'desc',
        workflow: {
          workflow_id: 'article_pipeline',
          title: '文章处理链路',
          description: 'desc',
          job_type: 'pipeline-run',
          permissions: 'operator',
          steps: [
            {
              step_id: 'crawl_articles',
              title: '抓取文章',
              description: '抓取文章',
              required_job_type: 'crawl',
              parameters: [],
              risk: 'medium',
              requires_confirmation: false,
              param_schema: {
                description: '抓取参数',
                allow_additional_fields: false,
                fields: {},
              },
            },
            {
              step_id: 'process_articles',
              title: '处理文章任务',
              description: '处理文章',
              required_job_type: 'process',
              parameters: [],
              risk: 'medium',
              requires_confirmation: false,
              param_schema: {
                description: '处理参数',
                allow_additional_fields: false,
                fields: {},
              },
            },
          ],
        },
      },
    });
    mockedGetArticlePipelineScheduleStatus.mockResolvedValue({
      scheduler_started: false,
      schedule_time: null,
      force: false,
      profile_id: null,
    });

    renderWithRouter([{ path: '/research/add', element: <ResearchAddPage /> }], ['/research/add']);

    expect(await screen.findByRole('heading', { name: '开始添加' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText('页面内容正在获取中，请稍后再看。')).not.toBeInTheDocument();
    });

    expect(await screen.findByText('job-1')).toBeInTheDocument();
    expect(screen.getByText('运行中')).toBeInTheDocument();
  });

  it('renders partial extraction results when the detail panel cannot load', async () => {
    renderWithRouter(
      [{ path: '/research/results', element: <ResearchResultsPage availability="partial" /> }],
      ['/research/results'],
    );

    expect(await screen.findAllByText('部分完成')).toHaveLength(2);
    expect(screen.getByText('你看到的是当前可用的部分结果。')).toBeInTheDocument();
    expect(screen.queryByText('页面用途')).not.toBeInTheDocument();
    await expectNoForbiddenTerms();
  });

  it('keeps extraction results on the workflow layout when availability is partial', async () => {
    renderWithRouter(
      [{ path: '/research/results', element: <ResearchResultsPage availability="partial" /> }],
      ['/research/results'],
    );

    expect(await screen.findByRole('heading', { name: '提取结果' })).toBeInTheDocument();
    expect(screen.queryByText('页面用途')).not.toBeInTheDocument();
    expect(screen.queryByText('输入')).not.toBeInTheDocument();
    expect(screen.queryByText('处理状态')).not.toBeInTheDocument();
    expect(screen.queryByText('输出')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '文章分析与审核' })).toBeInTheDocument();
    expect(screen.getByText('下一步')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回研究中心' })).toHaveAttribute('href', '/research');
  });

  it('keeps extraction result review flows wired to the real actions', async () => {
    const user = userEvent.setup();
    const detail = buildArticleAnalysisDetail();
    mockedListArticles.mockResolvedValue(buildArticleList());
    mockedGetArticleAnalysis.mockResolvedValue(detail);
    mockedReviewArticleCandidate.mockResolvedValue(detail);

    renderWithRouter([{ path: '/research/results', element: <ResearchResultsPage /> }], ['/research/results']);

    expect((await screen.findAllByText('文章分析与审核')).length).toBeGreaterThan(0);
    await user.click(await screen.findByRole('button', { name: '人工批准为待回测规则' }));

    await waitFor(() => {
      expect(mockedReviewArticleCandidate).toHaveBeenCalledWith('article-1', 'candidate-1', {
        decision: 'approve',
        reason: '人工确认后进入待回测。',
      });
    });
  });
});
