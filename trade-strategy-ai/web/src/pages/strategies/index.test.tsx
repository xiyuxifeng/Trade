import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { StrategiesPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listProfiles } from '@/lib/api/profiles';
import { listJobs } from '@/lib/api/jobs';

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  listJobs: vi.fn(),
}));

const mockedListProfiles = vi.mocked(listProfiles);
const mockedListJobs = vi.mocked(listJobs);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('StrategiesPage', () => {
  it('renders the strategy summary home with real shortcuts and job filters', async () => {
    mockedListProfiles.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [
        {
          profile_id: 'default',
          name: '默认配置',
          environment: 'production',
          version: 3,
          sections: {},
          secret_refs: {},
          validation_status: 'validated',
          created_by: 'web',
          created_at: '2026-05-16T00:00:00Z',
          updated_at: '2026-05-16T00:00:00Z',
          archived_at: null,
        },
      ],
    } as never);
    mockedListJobs
      .mockResolvedValueOnce({
        count: 1,
        total: 1,
        skip: 0,
        limit: 5,
        items: [
          {
            id: 'job-snapshot-1',
            job_type: 'snapshot-build',
            status: 'success',
            params: {},
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
            started_at: '2026-05-22T00:30:00Z',
            finished_at: '2026-05-22T00:35:00Z',
            audit_events: [],
            created_at: '2026-05-22T00:30:00Z',
            updated_at: '2026-05-22T00:35:00Z',
          },
        ],
      } as never)
      .mockResolvedValueOnce({
        count: 1,
        total: 1,
        skip: 0,
        limit: 5,
        items: [
          {
            id: 'job-pre-1',
            job_type: 'run-pre-market',
            status: 'success',
            params: {},
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
            started_at: '2026-05-22T01:00:00Z',
            finished_at: '2026-05-22T01:05:00Z',
            audit_events: [],
            created_at: '2026-05-22T01:00:00Z',
            updated_at: '2026-05-22T01:05:00Z',
          },
        ],
      } as never)
      .mockResolvedValueOnce({
        count: 1,
        total: 1,
        skip: 0,
        limit: 5,
        items: [
          {
            id: 'job-post-1',
            job_type: 'run-after-close',
            status: 'running',
            params: {},
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
            started_at: '2026-05-22T02:00:00Z',
            finished_at: null,
            audit_events: [],
            created_at: '2026-05-22T02:00:00Z',
            updated_at: '2026-05-22T02:00:00Z',
          },
        ],
      } as never)
      .mockResolvedValueOnce({
        count: 1,
        total: 1,
        skip: 0,
        limit: 5,
        items: [
          {
            id: 'job-build-1',
            job_type: 'strategy-build',
            status: 'success',
            params: {},
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
            started_at: '2026-05-22T03:00:00Z',
            finished_at: '2026-05-22T03:10:00Z',
            audit_events: [],
            created_at: '2026-05-22T03:00:00Z',
            updated_at: '2026-05-22T03:10:00Z',
          },
        ],
      } as never)
      .mockResolvedValueOnce({
        count: 1,
        total: 1,
        skip: 0,
        limit: 5,
        items: [
          {
            id: 'job-failed-1',
            job_type: 'snapshot-build',
            status: 'failed',
            params: {},
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
            started_at: '2026-05-22T03:30:00Z',
            finished_at: '2026-05-22T03:35:00Z',
            audit_events: [],
            created_at: '2026-05-22T03:30:00Z',
            updated_at: '2026-05-22T03:35:00Z',
          },
        ],
      } as never)
      .mockResolvedValueOnce({
        count: 1,
        total: 1,
        skip: 0,
        limit: 5,
        items: [
          {
            id: 'job-failed-2',
            job_type: 'run-pre-market',
            status: 'failed',
            params: {},
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
            started_at: '2026-05-22T04:00:00Z',
            finished_at: '2026-05-22T04:05:00Z',
            audit_events: [],
            created_at: '2026-05-22T04:00:00Z',
            updated_at: '2026-05-22T04:05:00Z',
          },
        ],
      } as never)
      .mockResolvedValueOnce({ count: 0, total: 0, skip: 0, limit: 5, items: [] } as never)
      .mockResolvedValueOnce({ count: 0, total: 0, skip: 0, limit: 5, items: [] } as never);

    renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);

    expect(await screen.findByRole('heading', { name: '策略工作台' })).toBeInTheDocument();
    expect(
      screen.getByText(
        '策略工作台用于管理每日策略运行、策略版本构建和策略优化。日常使用优先进入盘前准备和盘后复盘；当 Profile、规则池、市场状态或候选版本变化时，再构建新的策略版本。',
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText('今日运行')).toBeInTheDocument();
    expect(screen.getByText('策略构建')).toBeInTheDocument();
    expect(screen.getByText('策略优化')).toBeInTheDocument();
    expect(screen.getByText('追踪与排查')).toBeInTheDocument();
    expect(await screen.findByText('默认配置 · default')).toBeInTheDocument();
    expect(screen.queryByText('config_path')).not.toBeInTheDocument();
    expect(screen.getByText('最近失败任务（2）')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /盘前准备/ })).toHaveAttribute('href', '/strategies/pre-market');
    expect(screen.getByRole('link', { name: /盘后复盘/ })).toHaveAttribute('href', '/strategies/after-close');
    expect(screen.getByRole('link', { name: /规则选择/ })).toHaveAttribute('href', '/strategies/regime-selection');
    expect(screen.getByRole('link', { name: /构建策略版本/ })).toHaveAttribute('href', '/strategies/versions');
    expect(screen.getByRole('link', { name: /候选版本/ })).toHaveAttribute('href', '/strategies/candidates');
    expect(screen.getByRole('link', { name: /运行历史/ })).toHaveAttribute('href', '/strategies/history');
    expect(screen.getByRole('link', { name: /最新 snapshot-build Job/ })).toHaveAttribute('href', '/jobs?job_type=snapshot-build');
    expect(screen.getByRole('link', { name: /最新盘前 Job/ })).toHaveAttribute('href', '/jobs?job_type=run-pre-market');
    expect(screen.getByRole('link', { name: /最新盘后 Job/ })).toHaveAttribute('href', '/jobs?job_type=run-after-close');
    expect(screen.getByRole('link', { name: /最近失败任务/ })).toHaveAttribute('href', '/strategies/history?status=failed');
  });

  it('shows a shared recovery error when summary lookup fails', async () => {
    mockedListProfiles.mockRejectedValueOnce(new ApiError(403, 'forbidden'));
    mockedListJobs.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 5,
      items: [],
    } as never);

    renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);

    expect(await screen.findByText('没有权限访问策略工作台')).toBeInTheDocument();
    expect(screen.getByText('请切换到有权限的账号，或联系管理员调整权限。')).toBeInTheDocument();
  });
});
