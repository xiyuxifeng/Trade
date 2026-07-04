import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { cleanup, screen, waitFor } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { listJobs, listJobDefinitions, createJob, validateJobSubmission } from '@/lib/api/jobs';
import { renderWithRouter } from '@/test/test-utils';
import { JobNewPage, JobsPage } from './index';
import type { JobRecord } from '@/types/jobs';

vi.mock('@/lib/api/jobs', () => ({
  cancelJob: vi.fn(),
  createJob: vi.fn(),
  getJob: vi.fn(),
  getJobLogs: vi.fn(),
  getJobDefinition: vi.fn(),
  listJobDefinitions: vi.fn(),
  pauseJob: vi.fn(),
  resumeJob: vi.fn(),
  retryJob: vi.fn(),
  validateJobSubmission: vi.fn(),
  listJobs: vi.fn(),
}));

const mockedListJobs = vi.mocked(listJobs);
const mockedListJobDefinitions = vi.mocked(listJobDefinitions);
const mockedCreateJob = vi.mocked(createJob);
const mockedValidateJobSubmission = vi.mocked(validateJobSubmission);

beforeEach(() => {
  vi.restoreAllMocks();
  cleanup();
  window.localStorage.clear();
  mockedListJobDefinitions.mockResolvedValue([]);
});

function makeJob(overrides: Partial<JobRecord> = {}): JobRecord {
  return {
    id: 'job-1',
    job_type: 'pipeline-run',
    status: 'success',
    params: { config_path: 'config/app.yaml' },
    result: null,
    error: null,
    artifacts: [],
    created_by: 'web',
    idempotency_key: null,
    retry_count: 0,
    max_retries: 3,
    retry_backoff_seconds: 0,
    timeout_seconds: null,
    cancel_requested: false,
    cancel_requested_at: null,
    worker_id: 'worker-1',
    lock_token: null,
    lock_acquired_at: null,
    heartbeat_at: null,
    scheduled_at: null,
    started_at: '2026-05-09T08:00:00Z',
    finished_at: '2026-05-09T08:05:00Z',
    audit_events: [],
    created_at: '2026-05-09T08:00:00Z',
    updated_at: '2026-05-09T08:05:00Z',
    runtime_state: null,
    config_snapshot_path: null,
    config_snapshot: null,
    ...overrides,
  };
}

function makeListResponse(items: JobRecord[], overrides: Partial<{ count: number; total: number; skip: number; limit: number }> = {}) {
  const total = overrides.total ?? items.length;
  return {
    count: overrides.count ?? items.length,
    total,
    skip: overrides.skip ?? 0,
    limit: overrides.limit ?? 20,
    items,
  };
}

describe('JobsPage', () => {
  it('shows a loading state before the first response arrives', async () => {
    let resolveJobs: ((value: ReturnType<typeof makeListResponse>) => void) | null = null;
    mockedListJobs.mockReturnValue(
      new Promise((resolve) => {
        resolveJobs = resolve;
      }) as Promise<ReturnType<typeof makeListResponse>>,
    );

    renderWithRouter([{ path: '/system/jobs', element: <JobsPage /> }], ['/system/jobs']);

    expect(screen.getByText('最近任务')).toBeInTheDocument();
    expect(document.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);

    if (resolveJobs) {
      const nextResolve = resolveJobs as (value: ReturnType<typeof makeListResponse>) => void;
      nextResolve(makeListResponse([makeJob()]));
    }
    expect(await screen.findByText('job-1')).toBeInTheDocument();
    expect(screen.queryByText('操作说明')).not.toBeInTheDocument();
  });

  it('renders jobs, applies filters and navigates to the detail page', async () => {
    const user = userEvent.setup();
    const firstPage = makeListResponse(
      [
        makeJob({
          id: 'job-1',
          job_type: 'pipeline-run',
          status: 'running',
          created_by: 'alice',
          progress: {
            job_type: 'kaipan-fetch',
            stage: 'normalize',
            current: 2,
            total: 4,
            percent: 50,
            remaining: 2,
            current_trade_date: '2026-05-09',
            current_slot: '09-25',
            current_fetcher: null,
            current_dataset: 'hot_topics',
            current_step: 'normalize:hot_topics',
            status: 'success',
            error: null,
            updated_at: '2026-05-09T08:01:00Z',
          },
        }),
      ],
      { count: 1, total: 1, skip: 0, limit: 20 },
    );
    const filteredPage = makeListResponse(
      [
        makeJob({
          id: 'job-2',
          job_type: 'article-pipeline',
          status: 'failed',
          created_by: 'bob',
          started_at: '2026-05-10T08:00:00Z',
          finished_at: '2026-05-10T08:05:00Z',
        }),
      ],
      { count: 1, total: 1, skip: 0, limit: 20 },
    );

    mockedListJobs.mockResolvedValueOnce(firstPage).mockResolvedValueOnce(filteredPage);
    mockedListJobDefinitions.mockResolvedValue([
      {
        job_type: 'pipeline-run',
        title: 'Pipeline Run',
        service_name: 'pipeline',
        handler_name: 'pipeline_run',
        permission: 'operator',
        risk: 'medium',
        can_retry: true,
        can_pause: true,
        can_resume: true,
        can_cancel: true,
        can_run_concurrently: false,
        concurrency_group: 'pipeline',
        requires_confirmation: false,
        runnable: true,
        description: 'desc',
        param_schema: {},
      },
      {
        job_type: 'article-pipeline',
        title: 'Article Pipeline',
        service_name: 'pipeline',
        handler_name: 'article_pipeline',
        permission: 'operator',
        risk: 'medium',
        can_retry: true,
        can_pause: false,
        can_resume: false,
        can_cancel: true,
        can_run_concurrently: false,
        concurrency_group: 'pipeline',
        requires_confirmation: false,
        runnable: true,
        description: 'desc',
        param_schema: {},
      },
    ]);

    renderWithRouter(
      [
        { path: '/system/jobs', element: <JobsPage /> },
        { path: '/system/jobs/:jobId', element: <div>job detail page</div> },
      ],
      ['/system/jobs'],
    );

    expect(await screen.findByRole('heading', { name: '最近任务' })).toBeInTheDocument();
    expect(await screen.findByText('job-1')).toBeInTheDocument();
    expect(screen.getAllByText('Pipeline Run').length).toBeGreaterThan(0);
    expect(screen.getByText('normalize:hot_topics')).toBeInTheDocument();
    expect(screen.getByText('步骤进度 2 / 4 · 50%')).toBeInTheDocument();
    expect(screen.getByText('当前步骤已完成，任务终态请看上方 Job 状态。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '暂停' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '取消' })).toBeInTheDocument();

    await user.selectOptions(screen.getByDisplayValue('所有状态'), 'failed');
    await waitFor(() => {
      expect(mockedListJobs).toHaveBeenLastCalledWith({
        status: 'failed',
        job_type: undefined,
        created_by: undefined,
        skip: 0,
        limit: 20,
      });
    });

    await user.click(screen.getByRole('button', { name: '查看详情' }));
    expect(await screen.findByText('job detail page')).toBeInTheDocument();
  });

  it('initializes filters from query params and keeps the list aligned', async () => {
    mockedListJobDefinitions.mockResolvedValueOnce([
      {
        job_type: 'run-pre-market',
        title: '盘前执行',
        service_name: 'run',
        handler_name: 'run_pre_market',
        permission: 'operator',
        risk: 'medium',
        can_retry: true,
        can_pause: false,
        can_resume: false,
        can_cancel: true,
        can_run_concurrently: false,
        concurrency_group: 'run',
        requires_confirmation: false,
        runnable: true,
        description: 'desc',
        param_schema: {},
      },
    ]);
    mockedListJobs.mockResolvedValueOnce(
      makeListResponse([makeJob({ id: 'job-query-1', job_type: 'run-pre-market', status: 'failed', created_by: 'web' })], {
        count: 1,
        total: 1,
        skip: 20,
        limit: 20,
      }),
    );

    renderWithRouter([{ path: '/system/jobs', element: <JobsPage /> }], ['/system/jobs?status=failed&job_type=run-pre-market&created_by=web&page=2']);

    expect(await screen.findByRole('heading', { name: '最近任务' })).toBeInTheDocument();
    expect(screen.getByDisplayValue('失败')).toHaveValue('failed');
    await screen.findAllByText('盘前执行');
    await waitFor(() => {
      expect(screen.getByLabelText('按任务类型过滤')).toHaveValue('run-pre-market');
    });
    expect(screen.getByPlaceholderText('按创建者过滤')).toHaveValue('web');
    await waitFor(() => {
      expect(mockedListJobs).toHaveBeenLastCalledWith({
        status: 'failed',
        job_type: 'run-pre-market',
        created_by: 'web',
        skip: 20,
        limit: 20,
      });
    });
    expect(await screen.findByText('job-query-1')).toBeInTheDocument();
  });

  it('paginates the job list', async () => {
    const user = userEvent.setup();
    mockedListJobs.mockResolvedValue(
      makeListResponse([makeJob({ id: 'job-1' })], { count: 20, total: 25, skip: 0, limit: 20 }),
    );

    renderWithRouter([{ path: '/system/jobs', element: <JobsPage /> }], ['/system/jobs']);

    expect(await screen.findByRole('heading', { name: '最近任务' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '下一页' }));

    await waitFor(() => {
      expect(mockedListJobs).toHaveBeenLastCalledWith({
        status: undefined,
        job_type: undefined,
        created_by: undefined,
        skip: 20,
        limit: 20,
      });
    });
  });

  it('shows empty state', async () => {
    mockedListJobs.mockResolvedValueOnce(makeListResponse([], { count: 0, total: 0, skip: 0, limit: 20 }));
    renderWithRouter([{ path: '/system/jobs', element: <JobsPage /> }], ['/system/jobs']);
    expect(await screen.findByText('暂无符合条件的任务。')).toBeInTheDocument();
  });

  it('shows error state', async () => {
    mockedListJobs.mockRejectedValueOnce(new ApiError(500, 'server exploded'));
    renderWithRouter([{ path: '/system/jobs', element: <JobsPage /> }], ['/system/jobs?refresh=1']);
    expect(await screen.findByText('上游服务不可用')).toBeInTheDocument();
    expect(screen.getByText('稍后重试，或先确认上游服务状态。')).toBeInTheDocument();
  });

  it('shows permission denied state', async () => {
    renderWithRouter(
      [{ path: '/system/jobs', element: <JobsPage /> }],
      ['/system/jobs'],
      {
        initialPrincipal: {
          role: 'anonymous',
          api_key_label: null,
          authenticated: false,
          source: 'anonymous',
        },
      },
    );
    expect(await screen.findByText('没有权限访问任务中心')).toBeInTheDocument();
  });

  it('creates an advanced job from /system/jobs/new after validation and navigates to detail', async () => {
    const user = userEvent.setup();
    mockedListJobDefinitions.mockResolvedValueOnce([
      {
        job_type: 'run-pre-market',
        title: '生成盘前计划',
        service_name: 'run',
        handler_name: 'run_pre_market',
        permission: 'operator',
        risk: 'medium',
        can_retry: true,
        can_pause: false,
        can_resume: false,
        can_cancel: true,
        can_run_concurrently: false,
        concurrency_group: 'run',
        requires_confirmation: false,
        runnable: true,
        description: '生成盘前计划',
        param_schema: {
          fields: {
            profile_id: { type: 'string', description: 'Profile ID', required: true },
            as_of_date: { type: 'date', description: '执行日期', required: true },
          },
        },
      },
    ]);
    mockedValidateJobSubmission.mockResolvedValueOnce({
      params: { profile_id: 'default', as_of_date: '2026-07-04' },
      warnings: [],
      definition: {} as never,
    });
    mockedCreateJob.mockResolvedValueOnce({
      created: true,
      job: makeJob({ id: 'job-created', job_type: 'run-pre-market' }),
      job_dir: '',
      log_path: '',
      params_path: '',
      result_path: '',
      artifacts_path: '',
    });

    const { router } = renderWithRouter(
      [
        { path: '/system/jobs/new', element: <JobNewPage /> },
        { path: '/system/jobs/:jobId', element: <div>created detail</div> },
      ],
      ['/system/jobs/new'],
    );

    expect(await screen.findByRole('heading', { name: '新建任务' })).toBeInTheDocument();
    await user.selectOptions(await screen.findByLabelText('选择任务类型'), 'run-pre-market');
    await user.clear(screen.getByPlaceholderText('profile_id'));
    await user.type(screen.getByPlaceholderText('profile_id'), 'default');
    await user.clear(screen.getByPlaceholderText('as_of_date'));
    await user.type(screen.getByPlaceholderText('as_of_date'), '2026-07-04');
    await user.click(screen.getByRole('button', { name: '创建任务' }));

    await waitFor(() => {
      expect(mockedValidateJobSubmission).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'run-pre-market',
          params: { profile_id: 'default', as_of_date: '2026-07-04' },
        }),
        expect.anything(),
      );
    });
    expect(await screen.findByText('created detail')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/system/jobs/job-created');
  });
});
