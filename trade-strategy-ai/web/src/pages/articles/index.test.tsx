import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { act, screen, waitFor } from '@testing-library/react';
import { ArticleListPage, ArticleQualityPage, ArticleResultsPage, ArticleRunPage, ArticlesPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { getArticleAnalysis, reviewArticleCandidate } from '@/lib/api/article-analysis';
import { getArticleQualitySummary, listArticleFilterOptions, listArticles } from '@/lib/api/articles';
import { listProfiles } from '@/lib/api/profiles';
import {
  getArticlePipeline,
  getArticlePipelineScheduleStatus,
  runArticlePipelineStep,
  startArticlePipelineSchedule,
  stopArticlePipelineSchedule,
} from '@/lib/api/pipelines';
import { toast } from '@/components/ui/toast';
import type { PipelineDetailResponse } from '@/types/pipeline';

vi.mock('@/lib/api/articles', () => ({
  getArticleQualitySummary: vi.fn(),
  listArticleFilterOptions: vi.fn(),
  listArticles: vi.fn(),
}));

vi.mock('@/lib/api/article-analysis', () => ({
  getArticleAnalysis: vi.fn(),
  reviewArticleCandidate: vi.fn(),
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

vi.mock('@/components/ui/toast', () => ({
  toast: vi.fn(),
}));

const mockedListProfiles = vi.mocked(listProfiles);
const mockedGetArticleAnalysis = vi.mocked(getArticleAnalysis);
const mockedReviewArticleCandidate = vi.mocked(reviewArticleCandidate);
const mockedGetArticleQualitySummary = vi.mocked(getArticleQualitySummary);
const mockedListArticleFilterOptions = vi.mocked(listArticleFilterOptions);
const mockedListArticles = vi.mocked(listArticles);
const mockedGetArticlePipeline = vi.mocked(getArticlePipeline);
const mockedGetArticlePipelineScheduleStatus = vi.mocked(getArticlePipelineScheduleStatus);
const mockedRunArticlePipelineStep = vi.mocked(runArticlePipelineStep);
const mockedStartArticlePipelineSchedule = vi.mocked(startArticlePipelineSchedule);
const mockedStopArticlePipelineSchedule = vi.mocked(stopArticlePipelineSchedule);
const mockedToast = vi.mocked(toast);

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

function buildArticlePipelineDetail() {
  return {
    pipeline: {
      pipeline_id: 'article_pipeline',
      workflow_id: 'article_pipeline',
      job_type: 'pipeline-run',
      title: 'article_pipeline',
      description: '通过 Workflow/Job 体系运行文章处理主链路。',
      workflow: {
        workflow_id: 'article_pipeline',
        title: '文章处理链路',
        description: '把文章抓取、清洗、处理和回归验收收敛为第一条可交付业务切片。',
        job_type: 'pipeline-run',
        permissions: 'operator',
        steps: [
          {
            step_id: 'crawl',
            title: '抓取文章',
            description: '抓取并整理文章原始数据。',
            required_job_type: 'crawl',
            parameters: ['profile_id', 'max_articles', 'force'],
            param_schema: {
              description: '抓取参数',
              allow_additional_fields: false,
              fields: {
                max_articles: {
                  type: 'integer',
                  description: '最多文章数',
                  required: false,
                  default: null,
                  enum: [],
                },
                force: {
                  type: 'boolean',
                  description: '是否强制执行',
                  required: false,
                  default: false,
                  enum: [],
                },
              },
            },
            risk: 'low',
            requires_confirmation: false,
          },
          {
            step_id: 'clean',
            title: '清洗文章',
            description: '对抓取结果做清洗、去重和格式归一化。',
            required_job_type: 'clean',
            parameters: ['profile_id', 'max_articles', 'force', 'use_db'],
            param_schema: {
              description: '清洗参数',
              allow_additional_fields: false,
              fields: {
                max_articles: {
                  type: 'integer',
                  description: '最多处理文章数',
                  required: false,
                  default: null,
                  enum: [],
                },
                force: {
                  type: 'boolean',
                  description: '是否强制执行',
                  required: false,
                  default: false,
                  enum: [],
                },
                use_db: {
                  type: 'boolean',
                  description: '是否使用数据库链路',
                  required: false,
                  default: false,
                  enum: [],
                },
              },
            },
            risk: 'medium',
            requires_confirmation: false,
          },
          {
            step_id: 'validate',
            title: '校验文章',
            description: '对清洗后的文章进行质量校验和可抽取性标记。',
            required_job_type: 'validate',
            parameters: ['profile_id', 'max_articles', 'force'],
            param_schema: {
              description: '校验参数',
              allow_additional_fields: false,
              fields: {
                max_articles: {
                  type: 'integer',
                  description: '最多处理文章数',
                  required: false,
                  default: null,
                  enum: [],
                },
                force: {
                  type: 'boolean',
                  description: '是否强制执行',
                  required: false,
                  default: false,
                  enum: [],
                },
              },
            },
            risk: 'medium',
            requires_confirmation: false,
          },
          {
            step_id: 'store',
            title: '入库文章',
            description: '将校验后的文章写入数据库并生成后续处理任务。',
            required_job_type: 'store',
            parameters: ['profile_id', 'force', 'use_db'],
            param_schema: {
              description: '入库参数',
              allow_additional_fields: false,
              fields: {
                force: {
                  type: 'boolean',
                  description: '是否强制执行',
                  required: false,
                  default: false,
                  enum: [],
                },
                use_db: {
                  type: 'boolean',
                  description: '是否使用数据库链路',
                  required: false,
                  default: false,
                  enum: [],
                },
              },
            },
            risk: 'medium',
            requires_confirmation: false,
          },
          {
            step_id: 'process',
            title: '处理文章任务',
            description: '消费待处理任务并生成结构化结果。',
            required_job_type: 'process',
            parameters: ['profile_id', 'force', 'retry_failed', 'use_db'],
            param_schema: {
              description: '处理参数',
              allow_additional_fields: false,
              fields: {
                force: {
                  type: 'boolean',
                  description: '是否强制执行',
                  required: false,
                  default: false,
                  enum: [],
                },
                retry_failed: {
                  type: 'boolean',
                  description: '是否重试失败任务',
                  required: false,
                  default: false,
                  enum: [],
                },
                use_db: {
                  type: 'boolean',
                  description: '是否使用数据库链路',
                  required: false,
                  default: false,
                  enum: [],
                },
              },
            },
            risk: 'medium',
            requires_confirmation: false,
          },
        ],
      },
    },
  } as PipelineDetailResponse;
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

function buildArticleAnalysisDetail(articleId: string) {
  return {
    status: 'ready' as const,
    message: null,
    article: {
      article_id: articleId,
      article_revision_id: 'revision-1',
      content_hash: 'hash-1',
      title: articleId === 'article-2' ? 'Article Two' : 'Article One',
      source: articleId === 'article-2' ? 'xhs' : 'tgb',
      source_url: `https://example.com/${articleId}`,
      author_name: articleId === 'article-2' ? 'Bob' : 'Alice',
      author_id: articleId === 'article-2' ? 'author-2' : 'author-1',
      published_at: '2026-05-11T08:00:00Z',
      crawled_at: '2026-05-11T09:00:00Z',
      original_text: '原始正文',
      cleaned_content: '清洗后正文',
      summary: 'summary two',
      tags: ['momentum'],
    },
    summary_provenance: {
      source: 'article_revision_source_payload' as const,
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
      prompt_version: 'article_analysis_v1',
      schema_name: 'article_analysis_v1',
      schema_version: 'article_analysis_v1',
      available: true,
    },
    method_tags: ['突破'],
    explicit_facts: [{ claim: '放量突破介入', source: 'explicit' }],
    hypotheses: [{ hypothesis: '可能偏强势行情' }],
    missing_fields: { stop_loss: 'unknown' },
    prompt_trace: {
      run_id: 'run-1',
      prompt_name: 'article_analysis_v1',
      prompt_version: 'article_analysis_v1',
      schema_name: 'article_analysis_v1',
      schema_version: 'article_analysis_v1',
      provider: 'openai',
      model: 'gpt-5.4',
      validation_state: 'valid',
      retry_count: 0,
      token_usage: { total_tokens: 42 },
      cost_amount: null,
      cost_currency: null,
      started_at: null,
      completed_at: null,
    },
    candidates: [
      {
        candidate_id: 'candidate-1',
        candidate_index: 0,
        title: '放量突破介入',
        rule_type: 'entry',
        explicit_facts: { holding_period: 'intraday' },
        hypotheses: { note: '可能需要量比确认' },
        missing_fields: { stop_loss: 'unknown' },
        evidence: { items: [{ quote: '放量突破介入' }] },
        data_dependencies: { required: ['ohlcv_1d'] },
        backtestability_status: 'executable',
        kaipan_dependency: false,
        market_state_declaration_status: 'not_declared',
        automatic_review: {
          status: 'pending_backtest' as const,
          reasons: ['证据、条件和动作完整，可进入待回测'],
          risk_level: 'low' as const,
        },
        human_review: {
          review_state: 'auto_review',
          formal_rule_created: false,
          rule_version_id: null,
          formal_lifecycle_state: null,
          stage3_status: null,
        },
        governance: {
          algorithm_version: 'rule-fingerprint-v1',
          exact_fingerprint: 'f'.repeat(64),
          family_fingerprint: 'a'.repeat(64),
          family_key: `family:${'a'.repeat(64)}`,
          exact_duplicate_of_rule_version_id: null,
          eligible_for_formal_version: true,
          eligible_for_backtest: true,
          related_rules: [],
        },
      },
    ],
  };
}

describe('ArticlesPage', () => {
  it('renders workspace entry cards that link to article subpages', async () => {
    renderWithRouter([{ path: '/articles', element: <ArticlesPage /> }], ['/articles']);

    expect(await screen.findByRole('heading', { name: '文章与规则' })).toBeInTheDocument();
    expect(screen.getByText('请选择一个入口开始导入文章并提取规则。')).toBeInTheDocument();
    expect(screen.queryByText('迁移说明')).not.toBeInTheDocument();
    expect(screen.queryByText('导出入口')).not.toBeInTheDocument();
    expect(screen.queryByText('当前状态')).not.toBeInTheDocument();
    expect(screen.queryByText('维护边界')).not.toBeInTheDocument();
    expect(screen.getByText(/从 Profile 触发文章抓取、清洗、校验、入库和结果回看的一条完整流程。/)).toBeInTheDocument();
    expect(screen.getByText('文章浏览与筛选。')).toBeInTheDocument();
    expect(screen.getByText('文章数据质量概览。')).toBeInTheDocument();
    expect(screen.getByText('文章结构化产物。')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '进入抓取与处理' })).toHaveAttribute('href', '/articles/run');
    expect(screen.getByRole('link', { name: '进入文章列表' })).toHaveAttribute('href', '/articles/list');
    expect(screen.getByRole('link', { name: '进入数据质量' })).toHaveAttribute('href', '/articles/quality');
    expect(screen.getByRole('link', { name: '进入处理结果' })).toHaveAttribute('href', '/articles/results');
    expect(screen.queryByLabelText('config_path')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '运行 article_pipeline' })).not.toBeInTheDocument();
  });

  it('renders step-based run form and submits selected step params', async () => {
    const user = userEvent.setup();
    mockedToast.mockReset();
    mockedListProfiles.mockResolvedValue(buildProfileList());
    mockedGetArticlePipeline.mockResolvedValue(buildArticlePipelineDetail());
    mockedGetArticlePipelineScheduleStatus.mockResolvedValue({
      scheduler_started: false,
      schedule_time: null,
      force: false,
      profile_id: null,
    });
    let resolveRunStep:
      | ((value: {
          workflow: { workflow_id: string; job_type: string };
          job: { id: string; job_type: string; status: string };
        }) => void)
      | undefined;
    mockedRunArticlePipelineStep.mockReturnValue(
      new Promise((resolve) => {
        resolveRunStep = resolve;
      }) as never,
    );

    renderWithRouter([{ path: '/articles/run', element: <ArticleRunPage /> }, { path: '/system/jobs/:jobId', element: <div>job detail page</div> }], ['/articles/run']);

    expect(await screen.findByRole('heading', { name: '文章导入与处理' })).toBeInTheDocument();
    expect(await screen.findByLabelText('Profile')).toBeInTheDocument();
    expect(screen.getByLabelText('Profile')).toHaveValue('default');
    expect(await screen.findByLabelText('Step')).toBeInTheDocument();
    expect(screen.queryByLabelText('config_path')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('profile_id')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('use_db')).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Step'), 'clean');
    expect(screen.queryByLabelText('use_db')).not.toBeInTheDocument();

    await user.click(screen.getByLabelText('force'));

    await user.click(screen.getByRole('button', { name: '运行步骤 Job' }));

    expect(screen.getByRole('button', { name: '提交中' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '提交中' })).toHaveAttribute('aria-busy', 'true');

    await waitFor(() => {
      expect(mockedRunArticlePipelineStep).toHaveBeenCalledWith('clean', {
        params: expect.objectContaining({
          profile_id: 'default',
          force: true,
          use_db: true,
        }),
        created_by: 'web',
        confirmed: false,
      });
    });

    await act(async () => {
      resolveRunStep?.({
        workflow: { workflow_id: 'article_pipeline', job_type: 'clean' },
        job: { id: 'job-article-1', job_type: 'clean', status: 'pending' },
      });
    });

    await waitFor(() => {
      expect(mockedToast).toHaveBeenCalledWith({
        title: '文章抓取任务已提交',
        description: 'Job job-article-1 已创建，正在打开详情页。',
      });
    });

    expect(await screen.findByText('job detail page')).toBeInTheDocument();
  });

  it('starts and stops the article pipeline schedule', async () => {
    const user = userEvent.setup();
    mockedListProfiles.mockResolvedValue(buildProfileList());
    mockedGetArticlePipeline.mockResolvedValue(buildArticlePipelineDetail());
    mockedGetArticlePipelineScheduleStatus
      .mockResolvedValueOnce({
        scheduler_started: false,
        schedule_time: null,
        force: false,
        profile_id: null,
      })
      .mockResolvedValueOnce({
        scheduler_started: true,
        schedule_time: '07:30',
        force: true,
        profile_id: 'default',
      })
      .mockResolvedValueOnce({
        scheduler_started: false,
        schedule_time: '07:30',
        force: true,
        profile_id: 'default',
      });
    mockedStartArticlePipelineSchedule.mockResolvedValue({
      scheduler_started: true,
      schedule_time: '07:30',
      force: true,
      profile_id: 'default',
    });
    mockedStopArticlePipelineSchedule.mockResolvedValue({
      scheduler_started: false,
      schedule_time: '07:30',
      force: true,
      profile_id: 'default',
    });

    renderWithRouter([{ path: '/articles/run', element: <ArticleRunPage /> }], ['/articles/run']);

    expect(await screen.findByRole('heading', { name: '文章导入与处理' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '启动定时任务' })).toBeInTheDocument();

    await user.clear(screen.getByLabelText('触发时间'));
    await user.type(screen.getByLabelText('触发时间'), '07:30');
    await user.click(screen.getByLabelText('Force'));
    await user.click(screen.getByRole('button', { name: '启动定时任务' }));

    await waitFor(() => {
      expect(mockedStartArticlePipelineSchedule).toHaveBeenCalledWith({
        profile_id: 'default',
        schedule_time: '07:30',
        force: true,
      });
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '停止定时任务' })).toBeEnabled();
    });

    await user.click(screen.getByRole('button', { name: '停止定时任务' }));

    await waitFor(() => {
      expect(mockedStopArticlePipelineSchedule).toHaveBeenCalledWith({
        profile_id: 'default',
      });
    });
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

  it('renders the quality page with full profile-scoped quality metrics', async () => {
    mockedGetArticleQualitySummary.mockResolvedValue({
      profile_id: 'default',
      profile_snapshot_id: 'snapshot-1',
      trader_ids: ['trader_a', 'trader_b'],
      author_ids: ['author-4'],
      total: 3,
      with_summary: 2,
      with_tags: 2,
      with_hash: 3,
      with_author: 3,
      latest_crawled_at: '2026-05-10T10:30:00Z',
    });

    renderWithRouter([{ path: '/articles/quality', element: <ArticleQualityPage /> }], ['/articles/quality']);

    expect(await screen.findByRole('heading', { name: '数据质量' })).toBeInTheDocument();
    expect(await screen.findByText('Profile ID')).toBeInTheDocument();
    expect(await screen.findByText('Profile 作用域')).toBeInTheDocument();
    expect(screen.getByText('质量概览')).toBeInTheDocument();
    expect(screen.queryByText('最近一次文章 Job')).not.toBeInTheDocument();
  });

  it('renders the results page with single-article analysis and review detail', async () => {
    mockedListArticles.mockResolvedValue(buildArticleList());
    mockedGetArticleAnalysis.mockImplementation(async (articleId: string) => buildArticleAnalysisDetail(articleId));

    renderWithRouter([{ path: '/articles/results', element: <ArticleResultsPage /> }], ['/articles/results']);

    expect(await screen.findByRole('heading', { name: '文章分析与审核' })).toBeInTheDocument();
    expect((await screen.findAllByText('Article One')).length).toBeGreaterThan(0);
    expect(await screen.findByText('当前文章详情')).toBeInTheDocument();
    expect(await screen.findByText('结构化摘要')).toBeInTheDocument();
    expect(await screen.findByText('候选规则与审核')).toBeInTheDocument();
    expect(await screen.findByText('待回测')).toBeInTheDocument();
    expect(await screen.findByText('原始原文')).toBeInTheDocument();
    expect(await screen.findByText('清洗后内容')).toBeInTheDocument();
  });

  it('filters processed and unprocessed articles on the results page', async () => {
    const user = userEvent.setup();
    mockedListArticles.mockImplementation(async (query?: any) => {
      const processingStatus = query?.processing_status ?? 'all';
      if (processingStatus === 'processed') {
        return {
          items: [
            {
              ...buildArticleList().items[0],
              id: 'processed-article',
              title: 'Processed Article',
            },
          ],
          total: 1,
          page: 1,
          page_size: 8,
          pages: 1,
        };
      }
      if (processingStatus === 'unprocessed') {
        return {
          items: [
            {
              ...buildArticleList().items[0],
              id: 'unprocessed-article',
              title: 'Unprocessed Article',
            },
          ],
          total: 1,
          page: 1,
          page_size: 8,
          pages: 1,
        };
      }
      return {
        items: [
          {
            ...buildArticleList().items[0],
            id: 'processed-article',
            title: 'Processed Article',
          },
          {
            ...buildArticleList().items[0],
            id: 'unprocessed-article',
            title: 'Unprocessed Article',
          },
        ],
        total: 2,
        page: 1,
        page_size: 8,
        pages: 1,
      };
    });
    mockedGetArticleAnalysis.mockImplementation(async (articleId: string) => ({
      ...buildArticleAnalysisDetail(articleId),
      article: {
        ...buildArticleAnalysisDetail(articleId).article,
        title: `Analysis ${articleId}`,
      },
    }));

    renderWithRouter([{ path: '/articles/results', element: <ArticleResultsPage /> }], ['/articles/results']);

    expect(await screen.findByText('Processed Article')).toBeInTheDocument();
    expect(screen.getByText('Unprocessed Article')).toBeInTheDocument();
    expect(mockedListArticles).toHaveBeenCalledWith({ page: 1, page_size: 8, processing_status: 'all' });

    await user.click(screen.getByRole('button', { name: '已处理' }));
    expect(await screen.findByText('Processed Article')).toBeInTheDocument();
    expect(screen.queryByText('Unprocessed Article')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(mockedListArticles).toHaveBeenCalledWith({ page: 1, page_size: 8, processing_status: 'processed' });
    });

    await user.click(screen.getByRole('button', { name: '未处理' }));
    expect(await screen.findByText('Unprocessed Article')).toBeInTheDocument();
    expect(screen.queryByText('Processed Article')).not.toBeInTheDocument();
    await waitFor(() => {
      expect(mockedListArticles).toHaveBeenCalledWith({ page: 1, page_size: 8, processing_status: 'unprocessed' });
    });
  });

  it('runs review action from the results page', async () => {
    const user = userEvent.setup();
    mockedListArticles.mockResolvedValue(buildArticleList());
    mockedGetArticleAnalysis.mockImplementation(async (articleId: string) => buildArticleAnalysisDetail(articleId));
    mockedReviewArticleCandidate.mockResolvedValue({
      ...buildArticleAnalysisDetail('article-1'),
      candidates: [{
        ...buildArticleAnalysisDetail('article-1').candidates[0],
        human_review: {
          review_state: 'approved',
          formal_rule_created: true,
          rule_version_id: 'rule-version-1',
          formal_lifecycle_state: 'draft',
          stage3_status: 'pending_backtest',
        },
      }],
    });

    renderWithRouter([{ path: '/articles/results', element: <ArticleResultsPage /> }], ['/articles/results']);

    await screen.findByText('候选规则与审核');
    await user.click(screen.getByRole('button', { name: '人工批准为待回测规则' }));

    await waitFor(() => {
      expect(mockedReviewArticleCandidate).toHaveBeenCalledWith('article-1', 'candidate-1', {
        decision: 'approve',
        reason: '人工确认后进入待回测。',
      });
    });
    expect(await screen.findByText('人工审核结果已保存。')).toBeInTheDocument();
  });

});
