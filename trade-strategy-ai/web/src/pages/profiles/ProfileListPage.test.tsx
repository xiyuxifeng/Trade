import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { listProfiles } from '@/lib/api/profiles';
import { ProfileListPage } from './ProfileListPage';

vi.mock('@/lib/api/profiles', () => ({
  getProfile: vi.fn(),
  getProfileSnapshot: vi.fn(),
  importProfile: vi.fn(),
  listProfiles: vi.fn(),
}));

const mockedListProfiles = vi.mocked(listProfiles);

describe('ProfileListPage', () => {
  it('renders list, filters and chinese actions', async () => {
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
          version: 1,
          sections: { app: { timezone: 'Asia/Shanghai' } },
          secret_refs: { 'app.api_key': 'masked' },
          validation_status: 'validated',
          created_by: 'web',
          created_at: '2026-05-16T08:00:00Z',
          updated_at: '2026-05-16T08:30:00Z',
          archived_at: null,
        },
      ],
    });

    renderWithRouter([{ path: '/profiles', element: <ProfileListPage /> }], ['/profiles']);

    expect(await screen.findByText('配置管理工作台')).toBeInTheDocument();
    expect(await screen.findByText('配置列表')).toBeInTheDocument();
    expect(await screen.findByText('默认配置')).toBeInTheDocument();
    expect(screen.getAllByText('已校验').length).toBeGreaterThan(0);
  });

  it('shows an empty state and a retryable error state', async () => {
    mockedListProfiles.mockResolvedValueOnce({
      count: 0,
      total: 0,
      skip: 0,
      limit: 50,
      items: [],
    });

    renderWithRouter([{ path: '/profiles', element: <ProfileListPage /> }], ['/profiles']);

    expect(await screen.findByText('暂无配置')).toBeInTheDocument();
  });

  it('shows a retryable error state', async () => {
    mockedListProfiles.mockRejectedValueOnce(new Error('boom'));

    renderWithRouter([{ path: '/profiles', element: <ProfileListPage /> }], ['/profiles']);

    expect(await screen.findByText('网络请求失败')).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: '查看技术详情' }));
    await waitFor(() => {
      expect(screen.getByText(/boom/)).toBeInTheDocument();
    });
  });
});
