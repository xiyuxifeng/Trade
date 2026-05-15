import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { ArticlesPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { getArticlePipeline, runArticlePipeline } from '@/lib/api/pipelines';
import { listJobs } from '@/lib/api/jobs';

vi.mock('@/lib/api/pipelines', () => ({
  getArticlePipeline: vi.fn(),
  runArticlePipeline: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  cancelJob: vi.fn(),
  createJob: vi.fn(),
  getJob: vi.fn(),
  getJobLogs: vi.fn(),
  listJobs: vi.fn(),
}));

const mockedGetArticlePipeline = vi.mocked(getArticlePipeline);
const mockedRunArticlePipeline = vi.mocked(runArticlePipeline);
const mockedListJobs = vi.mocked(listJobs);

function buildPipelineDetail(overrides?: Partial<Record<string, unknown>>) {
  return {
    pipeline: {
      pipeline_id: 'article_pipeline',
      workflow_id: 'pipeline',
      job_type: 'pipeline-run',
      title: 'article_pipeline',
      description: '串联抓取、清洗、抽取、聚类与回归验证。',
      workflow: {
        workflow_id: 'pipeline',
        title: '数据 Pipeline',
        description: '串联抓取、清洗、抽取、聚类与回归验证。',
        job_type: 'pipeline-run',
        permissions: 'operator',
        job_definition: {
          job_type: 'pipeline-run',
          risk: 'medium',
          requires_confirmation: false,
          params_schema: {
            description: 'Pipeline 参数',
            allow_additional_fields: false,
            fields: {
              config_path: {
                type: 'path',
                description: '配置文件路径',
                required: true,
                enum: [],
              },
            },
          },
        },
        steps: [],
        ...(overrides?.workflow as Record<string, unknown> | undefined),
      },
      ...(overrides ?? {}),
    },
  };
}

function buildRecentJob(status: string) {
  return {
    id: `job-${status}`,
    job_type: 'pipeline-run',
    status,
    params: { config_path: 'config/articles.yaml' },
    result: null,
    error: status === 'failed' ? { message: 'boom' } : null,
    artifacts: [],
    audit_events: [],
    created_by: 'web',
    idempotency_key: null,
    retry_count: 0,
    max_retries: 3,
    retry_backoff_seconds: 0,
    timeout_seconds: null,
    cancel_requested: false,
    cancel_requested_at: null,
    worker_id: null,
    lock_token: null,
    lock_acquired_at: null,
    heartbeat_at: null,
    scheduled_at: null,
    started_at: null,
    finished_at: null,
    created_at: '2026-05-10T08:00:00Z',
    updated_at: '2026-05-10T08:00:00Z',
  };
}

describe('ArticlesPage', () => {
  it('renders the pipeline summary and recent jobs', async () => {
    mockedGetArticlePipeline.mockResolvedValue(buildPipelineDetail());
    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 5,
      items: [buildRecentJob('success')],
    });

    renderWithRouter([{ path: '/articles', element: <ArticlesPage /> }], ['/articles']);

    expect(await screen.findByText('article_pipeline')).toBeInTheDocument();
    expect(screen.getAllByText('串联抓取、清洗、抽取、聚类与回归验证。').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('config_path')).toBeInTheDocument();
    expect(screen.getByText('最近 article_pipeline jobs')).toBeInTheDocument();
    expect(screen.getByText('成功')).toBeInTheDocument();
  });

  it('shows validation feedback when the run form is empty', async () => {
    const user = userEvent.setup();
    mockedGetArticlePipeline.mockResolvedValue(buildPipelineDetail());
    mockedListJobs.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 5,
      items: [],
    });

    renderWithRouter([{ path: '/articles', element: <ArticlesPage /> }], ['/articles']);

    expect(await screen.findByText('article_pipeline')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '运行 article_pipeline' }));

    expect(
      await screen.findByText('请输入 config_path 或 Profile 值。', { selector: '#article-pipeline-value-error' }),
    ).toBeInTheDocument();
  });

  it('submits article_pipeline and navigates to the created job detail', async () => {
    const user = userEvent.setup();
    mockedGetArticlePipeline.mockResolvedValue(buildPipelineDetail());
    mockedListJobs.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 5,
      items: [],
    });
    mockedRunArticlePipeline.mockResolvedValue({
      workflow: { workflow_id: 'pipeline', job_type: 'pipeline-run' },
      job: { id: 'job-article-1', job_type: 'pipeline-run', status: 'pending' },
    });

    renderWithRouter(
      [
        { path: '/articles', element: <ArticlesPage /> },
        { path: '/jobs/:jobId', element: <div>job detail page</div> },
      ],
      ['/articles'],
    );

    expect(await screen.findByText('article_pipeline')).toBeInTheDocument();
    await user.type(screen.getByLabelText('config_path'), 'config/articles.yaml');
    await user.click(screen.getByRole('button', { name: '运行 article_pipeline' }));

    await waitFor(() => {
      expect(mockedRunArticlePipeline).toHaveBeenCalledWith({
        params: { config_path: 'config/articles.yaml' },
        created_by: 'web',
        confirmed: false,
      });
    });
    expect(await screen.findByText('job detail page')).toBeInTheDocument();
  });

  it('shows an API unavailable state and can retry', async () => {
    const user = userEvent.setup();
    mockedGetArticlePipeline.mockRejectedValueOnce(new Error('pipeline api unavailable'));
    mockedGetArticlePipeline.mockResolvedValue(buildPipelineDetail());
    mockedListJobs.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 5,
      items: [],
    });

    renderWithRouter([{ path: '/articles', element: <ArticlesPage /> }], ['/articles']);

    expect(await screen.findByText('pipeline api unavailable')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '重试' }));

    expect(await screen.findByText('article_pipeline')).toBeInTheDocument();
  });
});
