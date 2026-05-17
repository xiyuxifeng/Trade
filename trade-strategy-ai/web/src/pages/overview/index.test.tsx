import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { OverviewPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { useSystemStatus } from '@/features/system-status/use-system-status';
import { useRecentJobs } from '@/features/jobs/use-recent-jobs';
import { useRecentArtifacts } from '@/features/artifacts/use-recent-artifacts';
import { useDashboardAlertSummary } from '@/features/dashboard/use-dashboard-alert-summary';

vi.mock('@/features/system-status/use-system-status', () => ({
  useSystemStatus: vi.fn(),
}));

vi.mock('@/features/jobs/use-recent-jobs', () => ({
  useRecentJobs: vi.fn(),
}));

vi.mock('@/features/artifacts/use-recent-artifacts', () => ({
  useRecentArtifacts: vi.fn(),
}));

vi.mock('@/features/dashboard/use-dashboard-alert-summary', () => ({
  useDashboardAlertSummary: vi.fn(),
}));

const mockedUseSystemStatus = vi.mocked(useSystemStatus);
const mockedUseRecentJobs = vi.mocked(useRecentJobs);
const mockedUseRecentArtifacts = vi.mocked(useRecentArtifacts);
const mockedUseDashboardAlertSummary = vi.mocked(useDashboardAlertSummary);

function mockOverviewState(
  systemState: {
    data?: unknown;
    error?: unknown;
    isLoading?: boolean;
    isFetching?: boolean;
  } = {},
  jobsState: {
    data?: unknown;
    error?: unknown;
    isLoading?: boolean;
    isFetching?: boolean;
  } = {},
  artifactsState: {
    data?: unknown;
    error?: unknown;
    isLoading?: boolean;
    isFetching?: boolean;
  } = {},
  alertsState: {
    data?: unknown;
    error?: unknown;
    isLoading?: boolean;
    isFetching?: boolean;
  } = {},
) {
  mockedUseSystemStatus.mockReturnValue({
    data: systemState.data,
    error: systemState.error ?? null,
    isLoading: systemState.isLoading ?? false,
    isFetching: systemState.isFetching ?? false,
    refetch: vi.fn(),
  } as never);

  mockedUseRecentJobs.mockReturnValue({
    data: jobsState.data,
    error: jobsState.error ?? null,
    isLoading: jobsState.isLoading ?? false,
    isFetching: jobsState.isFetching ?? false,
    refetch: vi.fn(),
  } as never);

  mockedUseRecentArtifacts.mockReturnValue({
    data: artifactsState.data,
    error: artifactsState.error ?? null,
    isLoading: artifactsState.isLoading ?? false,
    isFetching: artifactsState.isFetching ?? false,
    refetch: vi.fn(),
  } as never);

  mockedUseDashboardAlertSummary.mockReturnValue({
    data: alertsState.data,
    error: alertsState.error ?? null,
    isLoading: alertsState.isLoading ?? false,
    isFetching: alertsState.isFetching ?? false,
    refetch: vi.fn(),
  } as never);
}

describe('OverviewPage', () => {
  it('renders a system-first dashboard with alert summaries', () => {
    mockOverviewState(
      {
        data: {
          status: 'ok',
          config_path: '/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/config/app.yaml',
          project_root: '/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai',
          run_mode: 'api',
          database: {
            name: 'primary',
            status: 'ok',
            latency_ms: 18,
            details: {},
            error: null,
          },
          directories: {},
          warnings: [],
        },
      },
      {
        data: {
          count: 2,
          total: 2,
          skip: 0,
          limit: 5,
          items: [
            {
              id: 'job-1',
              job_type: 'snapshot-build',
              status: 'failed',
              params: { trade_date: '2026-05-16' },
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
              started_at: '2026-05-16T09:00:00Z',
              finished_at: '2026-05-16T09:02:00Z',
              audit_events: [],
              created_at: '2026-05-16T09:00:00Z',
              updated_at: '2026-05-16T09:02:00Z',
            },
            {
              id: 'job-2',
              job_type: 'run-pre-market',
              status: 'success',
              params: { trade_date: '2026-05-16' },
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
              started_at: '2026-05-16T08:30:00Z',
              finished_at: '2026-05-16T08:35:00Z',
              audit_events: [],
              created_at: '2026-05-16T08:30:00Z',
              updated_at: '2026-05-16T08:35:00Z',
            },
          ],
        },
      },
      {
        data: {
          count: 1,
          total: 1,
          skip: 0,
          limit: 5,
          items: [
            {
              artifact_id: 'artifact-1',
              name: 'snapshot.summary.json',
              path: 'data/processed/snapshots/snapshot.summary.json',
              kind: 'json',
              source: 'job',
              exists: true,
              size_bytes: 2048,
              modified_at: '2026-05-16T09:02:00Z',
              previewable: true,
              job_id: 'job-1',
              metadata: {},
              preview: '{}',
              download_name: 'snapshot.summary.json',
            },
          ],
        },
      },
      {
        data: {
          count: 1,
          total: 1,
          items: [
            {
              id: 'alert-record-1',
              alert_id: 'alert-1',
              level: 'CRITICAL',
              title: '数据库离线',
              message: '主数据库连接失败。',
              channel: 'dingtalk',
              tags: ['database', 'critical'],
              status: 'pending',
              aggregated_count: 3,
              aggregation_key: 'database:connection',
              sent_at: '2026-05-16T09:01:00Z',
              acknowledged_at: null,
              resolved_at: null,
              alert_metadata: { source: 'health-check' },
              created_at: '2026-05-16T09:02:00Z',
            },
          ],
        },
      },
    );

    renderWithRouter([{ path: '/dashboard', element: <OverviewPage /> }], ['/dashboard']);

    expect(screen.getByText('运维总览')).toBeInTheDocument();
    expect(screen.getByText('系统健康')).toBeInTheDocument();
    expect(screen.getByText('数据库')).toBeInTheDocument();
    expect(screen.getByText('失败任务')).toBeInTheDocument();
    expect(screen.getByText('最近产物')).toBeInTheDocument();
    expect(screen.getByText('重点告警')).toBeInTheDocument();
    expect(screen.getByText('最近失败任务')).toBeInTheDocument();
    expect(screen.getByText('最近产物')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看告警详情：数据库离线' })).toHaveAttribute(
      'href',
      '/alerts/alert-record-1',
    );
    expect(screen.getByRole('link', { name: '任务中心' })).toHaveAttribute('href', '/jobs');
    expect(screen.getByRole('link', { name: '配置管理' })).toHaveAttribute('href', '/profiles');
    expect(screen.getByRole('link', { name: '策略工作台' })).toHaveAttribute('href', '/strategies');
  });

  it('surfaces empty states from the dashboard panels', () => {
    mockOverviewState(
      {
        data: {
          status: 'ok',
          config_path: '/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/config/app.yaml',
          project_root: '/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai',
          run_mode: 'api',
          database: {
            name: 'primary',
            status: 'ok',
            latency_ms: null,
            details: {},
            error: null,
          },
          directories: {},
          warnings: [],
        },
      },
      {
        data: {
          count: 0,
          total: 0,
          skip: 0,
          limit: 5,
          items: [],
        },
      },
      {
        data: {
          count: 0,
          total: 0,
          skip: 0,
          limit: 5,
          items: [],
        },
      },
      {
        data: {
          count: 0,
          total: 0,
          items: [],
        },
      },
    );

    renderWithRouter([{ path: '/dashboard', element: <OverviewPage /> }], ['/dashboard']);

    expect(screen.getByText('当前没有需要优先关注的告警。')).toBeInTheDocument();
    expect(screen.getByText('暂无最近任务。')).toBeInTheDocument();
    expect(screen.getByText('暂无最近产物。')).toBeInTheDocument();
  });

  it('surfaces panel errors without breaking the page shell', () => {
    mockOverviewState(
      {
        data: {
          status: 'ok',
          config_path: '/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/config/app.yaml',
          project_root: '/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai',
          run_mode: 'api',
          database: {
            name: 'primary',
            status: 'error',
            latency_ms: null,
            details: {},
            error: 'db down',
          },
          directories: {},
          warnings: ['config missing'],
        },
      },
      {
        data: {
          count: 0,
          total: 0,
          skip: 0,
          limit: 5,
          items: [],
        },
        error: new Error('recent jobs failed'),
      },
      {
        data: {
          count: 0,
          total: 0,
          skip: 0,
          limit: 5,
          items: [],
        },
        error: new Error('recent artifacts failed'),
      },
      {
        data: {
          count: 0,
          total: 0,
          items: [],
        },
        error: new Error('alert summary failed'),
      },
    );

    renderWithRouter([{ path: '/dashboard', element: <OverviewPage /> }], ['/dashboard']);

    expect(screen.getByText('部分总览数据加载失败')).toBeInTheDocument();
    expect(screen.getByText('recent jobs failed')).toBeInTheDocument();
    expect(screen.getByText('recent artifacts failed')).toBeInTheDocument();
    expect(screen.getByText('重点告警加载失败')).toBeInTheDocument();
  });
});
