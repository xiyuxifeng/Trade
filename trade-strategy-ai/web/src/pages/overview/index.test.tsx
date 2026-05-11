import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { OverviewPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { useSystemStatus } from '@/features/system-status/use-system-status';
import { useRecentJobs } from '@/features/jobs/use-recent-jobs';
import { useRecentArtifacts } from '@/features/artifacts/use-recent-artifacts';

vi.mock('@/features/system-status/use-system-status', () => ({
  useSystemStatus: vi.fn(),
}));

vi.mock('@/features/jobs/use-recent-jobs', () => ({
  useRecentJobs: vi.fn(),
}));

vi.mock('@/features/artifacts/use-recent-artifacts', () => ({
  useRecentArtifacts: vi.fn(),
}));

const mockedUseSystemStatus = vi.mocked(useSystemStatus);
const mockedUseRecentJobs = vi.mocked(useRecentJobs);
const mockedUseRecentArtifacts = vi.mocked(useRecentArtifacts);

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
}

describe('OverviewPage', () => {
  it('renders the operational overview with live summary cards', () => {
    mockOverviewState(
      {
        data: {
          status: 'ok',
          config_path: '/Users/wanghui/Documents/Claude/trade-strategy-ai/config/app.yaml',
          project_root: '/Users/wanghui/Documents/Claude/trade-strategy-ai',
          run_mode: 'api',
          database: {
            name: 'primary',
            status: 'ok',
            latency_ms: 18,
            details: {},
            error: null,
          },
          directories: {
            config: {
              path: '/Users/wanghui/Documents/Claude/trade-strategy-ai/config/app.yaml',
              exists: true,
            },
          },
          warnings: [],
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
              id: 'job-1',
              job_type: 'run-pre-market',
              status: 'success',
              params: { as_of: '2026-05-11' },
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
              started_at: '2026-05-11T01:00:00Z',
              finished_at: '2026-05-11T01:05:00Z',
              audit_events: [],
              created_at: '2026-05-11T01:00:00Z',
              updated_at: '2026-05-11T01:05:00Z',
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
              name: 'daily_report_2026-05-11.json',
              path: 'data/processed/reports/daily_report_2026-05-11.json',
              kind: 'report',
              source: 'job',
              exists: true,
              size_bytes: 2048,
              modified_at: '2026-05-11T01:05:00Z',
              previewable: true,
              job_id: 'job-1',
              metadata: {},
              preview: '{}',
              download_name: 'daily_report_2026-05-11.json',
            },
          ],
        },
      },
    );

    renderWithRouter([{ path: '/overview', element: <OverviewPage /> }], ['/overview']);

    expect(screen.getByText('Operations at a glance')).toBeInTheDocument();
    expect(screen.getByText('系统状态')).toBeInTheDocument();
    expect(screen.getByText('最近任务')).toBeInTheDocument();
    expect(screen.getByText('最近产物')).toBeInTheDocument();
    expect(screen.getByText('Why this layout')).toBeInTheDocument();
    expect(screen.getByText('关键目录检查通过。')).toBeInTheDocument();
  });

  it('surfaces empty states from the embedded panels', () => {
    mockOverviewState(
      {
        data: {
          status: 'ok',
          config_path: '/Users/wanghui/Documents/Claude/trade-strategy-ai/config/app.yaml',
          project_root: '/Users/wanghui/Documents/Claude/trade-strategy-ai',
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
    );

    renderWithRouter([{ path: '/overview', element: <OverviewPage /> }], ['/overview']);

    expect(screen.getByText('暂无最近任务。')).toBeInTheDocument();
    expect(screen.getByText('暂无最近产物。')).toBeInTheDocument();
  });

  it('surfaces panel errors without breaking the page shell', () => {
    mockOverviewState(
      {
        data: {
          status: 'ok',
          config_path: '/Users/wanghui/Documents/Claude/trade-strategy-ai/config/app.yaml',
          project_root: '/Users/wanghui/Documents/Claude/trade-strategy-ai',
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
    );

    renderWithRouter([{ path: '/overview', element: <OverviewPage /> }], ['/overview']);

    expect(screen.getByText('recent jobs failed')).toBeInTheDocument();
    expect(screen.getByText('recent artifacts failed')).toBeInTheDocument();
    expect(
      screen.getByText((content, element) => {
        return element?.tagName === 'P' && content.includes('发现') && content.includes('个目录异常');
      }),
    ).toBeInTheDocument();
  });
});
