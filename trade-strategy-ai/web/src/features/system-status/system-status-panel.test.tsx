import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithRouter } from '@/test/test-utils';
import { SystemStatusPanel } from './system-status-panel';
import { useSystemStatus } from './use-system-status';
import { ApiError } from '@/lib/api/http';

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

  it('renders user-friendly product-mode error copy and keeps diagnostics for operators', async () => {
    const user = userEvent.setup();
    mockedUseSystemStatus.mockReturnValue({
      data: null,
      error: new ApiError(503, 'service unavailable', { request_id: 'trace-001' }),
      isLoading: false,
      isFetching: false,
      refetch: vi.fn(),
    } as never);

    renderWithRouter([{ path: '/system', element: <SystemStatusPanel productMode /> }], ['/system'], {
      initialPrincipal: {
        role: 'operator',
        api_key_label: 'Local Operator',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByText('系统状态接口请求失败。')).toBeInTheDocument();
    expect(screen.getByText('当前无法确认服务、配置和关键依赖是否支持后续业务操作。')).toBeInTheDocument();
    expect(screen.getByText('请先刷新系统状态；如果多次失败，请联系管理员检查系统服务。')).toBeInTheDocument();
    expect(screen.queryByText('service unavailable')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '查看运维诊断详情' }));
    expect(screen.getByText(/trace-001/)).toBeInTheDocument();
  });
});
