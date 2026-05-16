import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { cleanup, screen, waitFor } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { listJobs } from '@/lib/api/jobs';
import { renderWithRouter } from '@/test/test-utils';
import { JobsPage } from './index';
import type { JobRecord } from '@/types/jobs';

vi.mock('@/lib/api/jobs', () => ({
  cancelJob: vi.fn(),
  createJob: vi.fn(),
  getJob: vi.fn(),
  getJobLogs: vi.fn(),
  listJobs: vi.fn(),
}));

const mockedListJobs = vi.mocked(listJobs);

beforeEach(() => {
  vi.restoreAllMocks();
  cleanup();
  window.localStorage.clear();
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

    renderWithRouter([{ path: '/jobs', element: <JobsPage /> }], ['/jobs']);

    expect(screen.getByText('最近任务')).toBeInTheDocument();
    expect(document.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);

    resolveJobs?.(makeListResponse([makeJob()]));
    expect(await screen.findByText('job-1')).toBeInTheDocument();
  });

  it('renders jobs, applies filters and navigates to the detail page', async () => {
    const user = userEvent.setup();
    const firstPage = makeListResponse(
      [
        makeJob({
          id: 'job-1',
          job_type: 'pipeline-run',
          status: 'success',
          created_by: 'alice',
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

    renderWithRouter(
      [
        { path: '/jobs', element: <JobsPage /> },
        { path: '/jobs/:jobId', element: <div>job detail page</div> },
      ],
      ['/jobs'],
    );

    expect(await screen.findByRole('heading', { name: '任务列表' })).toBeInTheDocument();
    expect(await screen.findByText('job-1')).toBeInTheDocument();
    expect(screen.getByText('pipeline-run')).toBeInTheDocument();

    await user.selectOptions(screen.getByRole('combobox'), 'failed');
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

  it('paginates the job list', async () => {
    const user = userEvent.setup();
    mockedListJobs.mockResolvedValue(
      makeListResponse([makeJob({ id: 'job-1' })], { count: 20, total: 25, skip: 0, limit: 20 }),
    );

    renderWithRouter([{ path: '/jobs', element: <JobsPage /> }], ['/jobs']);

    expect(await screen.findByRole('heading', { name: '任务列表' })).toBeInTheDocument();
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
    renderWithRouter([{ path: '/jobs', element: <JobsPage /> }], ['/jobs']);
    expect(await screen.findByText('暂无符合条件的任务。')).toBeInTheDocument();
  });

  it('shows error state', async () => {
    mockedListJobs.mockRejectedValueOnce(new ApiError(500, 'server exploded'));
    renderWithRouter([{ path: '/jobs', element: <JobsPage /> }], ['/jobs?refresh=1']);
    expect(await screen.findAllByText('上游服务不可用')).toHaveLength(2);
    expect(screen.getAllByText('稍后重试，或先确认上游服务状态。')).toHaveLength(2);
  });

  it('shows permission denied state', async () => {
    renderWithRouter(
      [{ path: '/jobs', element: <JobsPage /> }],
      ['/jobs'],
      {
        initialPrincipal: {
          role: 'anonymous',
          api_key_label: null,
          authenticated: false,
          source: 'anonymous',
        },
      },
    );
    expect(await screen.findByText('没有权限访问任务列表')).toBeInTheDocument();
  });
});
