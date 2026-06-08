import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { HistoryPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listJobs } from '@/lib/api/jobs';

vi.mock('@/lib/api/jobs', () => ({
  listJobs: vi.fn(),
}));

const mockedListJobs = vi.mocked(listJobs);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('HistoryPage', () => {
  it('filters strategy jobs by status, type and date', async () => {
    const user = userEvent.setup();

    mockedListJobs.mockResolvedValue({
      count: 3,
      total: 3,
      skip: 0,
      limit: 200,
      items: [
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
          started_at: '2026-05-15T02:00:00Z',
          finished_at: '2026-05-15T02:05:00Z',
          audit_events: [],
          created_at: '2026-05-15T02:00:00Z',
          updated_at: '2026-05-15T02:05:00Z',
        },
        {
          id: 'job-build-1',
          job_type: 'strategy-build',
          status: 'success',
          params: { profile_id: 'default', strategy_date: '2026-05-16' },
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
          worker_id: null,
          lock_token: null,
          lock_acquired_at: null,
          heartbeat_at: null,
          scheduled_at: null,
          started_at: '2026-05-16T03:00:00Z',
          finished_at: '2026-05-16T03:05:00Z',
          audit_events: [],
          created_at: '2026-05-16T03:00:00Z',
          updated_at: '2026-05-16T03:05:00Z',
        },
        {
          id: 'job-pre-1',
          job_type: 'run-pre-market',
          status: 'failed',
          params: { profile_id: 'default', as_of_date: '2026-05-17' },
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
          worker_id: null,
          lock_token: null,
          lock_acquired_at: null,
          heartbeat_at: null,
          scheduled_at: null,
          started_at: '2026-05-17T03:00:00Z',
          finished_at: '2026-05-17T03:05:00Z',
          audit_events: [],
          created_at: '2026-05-17T03:00:00Z',
          updated_at: '2026-05-17T03:05:00Z',
        },
        {
          id: 'job-post-1',
          job_type: 'run-after-close',
          status: 'success',
          params: { profile_id: 'default', as_of_date: '2026-05-18' },
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
          worker_id: null,
          lock_token: null,
          lock_acquired_at: null,
          heartbeat_at: null,
          scheduled_at: null,
          started_at: '2026-05-18T03:00:00Z',
          finished_at: '2026-05-18T03:05:00Z',
          audit_events: [],
          created_at: '2026-05-18T03:00:00Z',
          updated_at: '2026-05-18T03:05:00Z',
        },
      ],
    } as never);

    renderWithRouter([{ path: '/strategies/history', element: <HistoryPage /> }], ['/strategies/history']);

    expect(await screen.findByRole('heading', { name: '运行历史' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '返回任务中心' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /job-build-1/ })).toBeInTheDocument();
    expect(await screen.findByRole('combobox', { name: '状态' })).toHaveValue('');
    expect(screen.getByRole('combobox', { name: '状态' })).toHaveValue('');
    expect(screen.getByRole('combobox', { name: '类型' })).toHaveValue('');
    expect(screen.getByRole('button', { name: '搜索' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重置' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /job-build-1/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /job-snapshot-1/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /job-pre-1/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /job-post-1/ })).toBeInTheDocument();

    await user.selectOptions(screen.getByRole('combobox', { name: '状态' }), 'failed');

    expect(screen.getByRole('button', { name: /job-build-1/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /job-post-1/ })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '搜索' }));

    expect(screen.getByRole('button', { name: /job-pre-1/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /job-build-1/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /job-post-1/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '重置' }));
    await user.click(screen.getByRole('button', { name: '搜索' }));

    expect(screen.getByRole('button', { name: /job-build-1/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /job-post-1/ })).toBeInTheDocument();
  });
});
