import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { DashboardRecentJobsPanel } from './dashboard-recent-jobs';
import { useRecentJobs } from '@/features/jobs/use-recent-jobs';

vi.mock('@/features/jobs/use-recent-jobs', () => ({
  useRecentJobs: vi.fn(),
}));

const mockedUseRecentJobs = vi.mocked(useRecentJobs);

describe('DashboardRecentJobsPanel', () => {
  it('shows failed jobs when failures exist', async () => {
    mockedUseRecentJobs.mockReturnValue({
      data: {
        items: [
          {
            id: 'job-failed-1',
            job_type: 'market-snapshot-build',
            status: 'failed',
            params: {},
            result: null,
            error: { message: 'boom' },
            runtime_state: null,
            artifacts: [],
            created_by: 'system',
            idempotency_key: null,
            retry_count: 0,
            max_retries: 3,
            retry_backoff_seconds: 30,
            timeout_seconds: null,
            cancel_requested: false,
            cancel_requested_at: null,
            worker_id: null,
            lock_token: null,
            lock_acquired_at: null,
            heartbeat_at: null,
            scheduled_at: null,
            started_at: '2026-06-01T01:00:00Z',
            finished_at: '2026-06-01T01:05:00Z',
            audit_events: [],
            created_at: '2026-06-01T01:00:00Z',
            updated_at: '2026-06-01T01:05:00Z',
          },
          {
            id: 'job-success-1',
            job_type: 'market-snapshot-build',
            status: 'success',
            params: {},
            result: {},
            error: null,
            runtime_state: null,
            artifacts: [],
            created_by: 'system',
            idempotency_key: null,
            retry_count: 0,
            max_retries: 3,
            retry_backoff_seconds: 30,
            timeout_seconds: null,
            cancel_requested: false,
            cancel_requested_at: null,
            worker_id: null,
            lock_token: null,
            lock_acquired_at: null,
            heartbeat_at: null,
            scheduled_at: null,
            started_at: '2026-06-01T00:00:00Z',
            finished_at: '2026-06-01T00:30:00Z',
            audit_events: [],
            created_at: '2026-06-01T00:00:00Z',
            updated_at: '2026-06-01T00:30:00Z',
          },
        ],
      },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);

    renderWithRouter([{ path: '/', element: <DashboardRecentJobsPanel /> }], ['/']);

    expect(await screen.findByRole('heading', { name: '最近任务' })).toBeInTheDocument();
    expect(screen.getByText('job-failed-1')).toBeInTheDocument();
    expect(screen.queryByText('job-success-1')).not.toBeInTheDocument();
  });

  it('shows recent jobs when there are no failures', async () => {
    mockedUseRecentJobs.mockReturnValue({
      data: {
        items: [
          {
            id: 'job-success-1',
            job_type: 'market-snapshot-build',
            status: 'success',
            params: {},
            result: {},
            error: null,
            runtime_state: null,
            artifacts: [],
            created_by: 'system',
            idempotency_key: null,
            retry_count: 0,
            max_retries: 3,
            retry_backoff_seconds: 30,
            timeout_seconds: null,
            cancel_requested: false,
            cancel_requested_at: null,
            worker_id: null,
            lock_token: null,
            lock_acquired_at: null,
            heartbeat_at: null,
            scheduled_at: null,
            started_at: '2026-06-01T00:00:00Z',
            finished_at: '2026-06-01T00:30:00Z',
            audit_events: [],
            created_at: '2026-06-01T00:00:00Z',
            updated_at: '2026-06-01T00:30:00Z',
          },
        ],
      },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);

    renderWithRouter([{ path: '/', element: <DashboardRecentJobsPanel /> }], ['/']);

    expect(await screen.findByRole('heading', { name: '最近任务' })).toBeInTheDocument();
    expect(screen.getByText('job-success-1')).toBeInTheDocument();
    expect(screen.getByText('当前没有失败任务，以上显示最近运行记录。')).toBeInTheDocument();
  });
});
