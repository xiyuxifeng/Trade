import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { SystemStatusPanel } from './system-status-panel';
import { useSystemStatus } from './use-system-status';

vi.mock('./use-system-status', () => ({
  useSystemStatus: vi.fn(),
}));

const mockedUseSystemStatus = vi.mocked(useSystemStatus);

describe('SystemStatusPanel', () => {
  it('shows the bootstrap warning when the runtime profile is the fallback default', async () => {
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

    renderWithRouter([{ path: '/system', element: <SystemStatusPanel /> }], ['/system']);

    expect(await screen.findByText('当前使用的是兜底 default Profile')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '去导入正式配置' })).toBeInTheDocument();
  });

  it('does not show the warning for a real runtime profile', async () => {
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

    renderWithRouter([{ path: '/system', element: <SystemStatusPanel /> }], ['/system']);

    expect(screen.queryByText('当前使用的是兜底 default Profile')).not.toBeInTheDocument();
    expect(await screen.findByText('Profile')).toBeInTheDocument();
  });
});
