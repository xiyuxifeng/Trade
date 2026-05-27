import { describe, expect, it } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { StrategyWorkspaceHistory } from './strategy-workspace-history';
import { renderWithRouter } from '@/test/test-utils';
import type { JobRecord } from '@/types/jobs';

const strategyJobs: JobRecord[] = [
  {
    id: 'job-snapshot-1',
    job_type: 'snapshot-build',
    status: 'success',
    params: { profile_id: 'default', date: '2026-05-16' },
    result: null,
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
    started_at: null,
    finished_at: null,
    audit_events: [],
    created_at: '2026-05-16T09:00:00Z',
    updated_at: '2026-05-16T09:00:00Z',
    runtime_state: null,
    config_snapshot_path: null,
    config_snapshot: null,
  },
  {
    id: 'job-strategy-2',
    job_type: 'run-after-close',
    status: 'success',
    params: { profile_id: 'default', as_of_date: '2026-05-16' },
    result: null,
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
    started_at: null,
    finished_at: null,
    audit_events: [],
    created_at: '2026-05-16T08:10:00Z',
    updated_at: '2026-05-16T08:10:00Z',
    runtime_state: null,
    config_snapshot_path: null,
    config_snapshot: null,
  },
  {
    id: 'job-strategy-1',
    job_type: 'strategy-build',
    status: 'failed',
    params: { profile_id: 'default', trader_id: 'trader_a', strategy_date: '2026-05-16' },
    result: null,
    error: { type: 'config_error', message: 'config missing' },
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
    started_at: null,
    finished_at: null,
    audit_events: [],
    created_at: '2026-05-15T08:10:00Z',
    updated_at: '2026-05-15T08:10:00Z',
    runtime_state: null,
    config_snapshot_path: null,
    config_snapshot: null,
  },
];

describe('StrategyWorkspaceHistory', () => {
  it('shows loading and empty states', () => {
    renderWithRouter(
      [
        {
          path: '/strategies',
          element: <StrategyWorkspaceHistory error={null} isLoading={true} jobs={[]} onRetry={() => undefined} />,
        },
      ],
      ['/strategies'],
    );

    expect(screen.getByText('正在加载策略任务历史')).toBeInTheDocument();
  });

  it('shows the empty state when there are no strategy jobs', () => {
    renderWithRouter(
      [
        {
          path: '/strategies',
          element: <StrategyWorkspaceHistory error={null} isLoading={false} jobs={[]} onRetry={() => undefined} />,
        },
      ],
      ['/strategies'],
    );

    expect(screen.getByText(/暂无策略任务/)).toBeInTheDocument();
  });

  it('navigates to job detail from a strategy job row', async () => {
    const user = userEvent.setup();

    const { router } = renderWithRouter(
      [
        {
          path: '/strategies',
          element: (
            <StrategyWorkspaceHistory error={null} isLoading={false} jobs={strategyJobs} onRetry={() => undefined} />
          ),
        },
        {
          path: '/jobs/:jobId',
          element: <div>job detail</div>,
        },
      ],
      ['/strategies'],
    );

    await user.click(screen.getByRole('button', { name: /job-strategy-2/ }));

    expect(router.state.location.pathname).toBe('/jobs/job-strategy-2');
  });

  it('shows error state', () => {
    renderWithRouter(
      [
        {
          path: '/strategies',
          element: <StrategyWorkspaceHistory error={new Error('加载失败')} isLoading={false} jobs={[]} onRetry={() => undefined} />,
        },
      ],
      ['/strategies'],
    );

    expect(screen.getByText('网络请求失败')).toBeInTheDocument();
    expect(screen.getByText('请确认网络连接后重试。')).toBeInTheDocument();
  });
});
