import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { DashboardStatusSummary } from './dashboard-status-summary';
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

describe('DashboardStatusSummary', () => {
  it('shows the bootstrap warning when only the fallback default profile is active', async () => {
    mockedUseSystemStatus.mockReturnValue({
      data: {
        status: 'ok',
        profile_id: 'default',
        profile_snapshot_id: null,
        profile_context: {
          profile_id: null,
          profile_snapshot_id: null,
          source: 'unset',
        },
        project_root: '/tmp',
        run_mode: 'web',
        database: { name: 'db', status: 'ok' },
        directories: {},
        warnings: [],
      },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);
    mockedUseRecentJobs.mockReturnValue({
      data: { items: [] },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);
    mockedUseRecentArtifacts.mockReturnValue({
      data: { items: [] },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);
    mockedUseDashboardAlertSummary.mockReturnValue({
      data: { items: [] },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);

    renderWithRouter([{ path: '/', element: <DashboardStatusSummary /> }], ['/']);

    expect(await screen.findByText('当前使用的是兜底 default Profile')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '去导入正式配置' })).toBeInTheDocument();
  });

  it('does not show the warning for a real profile', async () => {
    mockedUseSystemStatus.mockReturnValue({
      data: {
        status: 'ok',
        profile_id: 'preview-demo',
        profile_snapshot_id: 'snapshot-1',
        profile_context: {
          profile_id: 'preview-demo',
          profile_snapshot_id: 'snapshot-1',
          source: 'env',
        },
        project_root: '/tmp',
        run_mode: 'web',
        database: { name: 'db', status: 'ok' },
        directories: {},
        warnings: [],
      },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);
    mockedUseRecentJobs.mockReturnValue({
      data: { items: [] },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);
    mockedUseRecentArtifacts.mockReturnValue({
      data: { items: [] },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);
    mockedUseDashboardAlertSummary.mockReturnValue({
      data: { items: [] },
      error: null,
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);

    renderWithRouter([{ path: '/', element: <DashboardStatusSummary /> }], ['/']);

    expect(screen.queryByText('当前使用的是兜底 default Profile')).not.toBeInTheDocument();
    expect(await screen.findByText('系统健康')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看全部告警' })).toHaveAttribute('href', '/alerts');
  });
});
