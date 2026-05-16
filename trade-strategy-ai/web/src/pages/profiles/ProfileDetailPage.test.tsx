import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { renderWithRouter } from '@/test/test-utils';
import { getProfile } from '@/lib/api/profiles';
import { ProfileDetailPage } from './ProfileDetailPage';

vi.mock('@/lib/api/profiles', () => ({
  getProfile: vi.fn(),
  getProfileSnapshot: vi.fn(),
  importProfile: vi.fn(),
  listProfiles: vi.fn(),
}));

const mockedGetProfile = vi.mocked(getProfile);

describe('ProfileDetailPage', () => {
  it('renders the profile detail, sections, linked jobs and snapshots', async () => {
    mockedGetProfile.mockResolvedValue({
      profile: {
        profile_id: 'default',
        name: '默认配置',
        environment: 'production',
        version: 2,
        sections: { app: { timezone: 'Asia/Shanghai' }, market: { enabled: true } },
        secret_refs: { 'app.api_key': 'masked', 'market.token': 'masked' },
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T08:00:00Z',
        updated_at: '2026-05-16T08:30:00Z',
        archived_at: null,
      },
      linked_jobs: [
        {
          job_id: 'job-1',
          job_type: 'pipeline-run',
          status: 'success',
          created_at: '2026-05-16T08:05:00Z',
          updated_at: '2026-05-16T08:10:00Z',
        },
      ],
      snapshots: [
        {
          snapshot_id: 'snapshot-1',
          profile_id: 'default',
          job_id: 'job-1',
          source: 'config/articles.yaml',
          config_path: 'config/articles.yaml',
          config_hash: 'hash-1',
          masked_snapshot: { app: { api_key: '***' } },
          masked_sections: ['app'],
          validation_status: 'validated',
          captured_at: '2026-05-16T08:06:00Z',
          snapshot_path: '/tmp/profile-snapshot.json',
        },
      ],
    });

    renderWithRouter([{ path: '/profiles/:profileId', element: <ProfileDetailPage /> }], ['/profiles/default']);

    expect(await screen.findByText('默认配置')).toBeInTheDocument();
    expect(screen.getByText('配置管理')).toBeInTheDocument();
    expect(screen.getByText('编辑配置')).toBeInTheDocument();
    expect(screen.getByText('配置分区')).toBeInTheDocument();
    expect(screen.getByText('脱敏字段')).toBeInTheDocument();
    expect(screen.getByText('关联任务')).toBeInTheDocument();
    expect(screen.getByText('历史快照')).toBeInTheDocument();
    expect(screen.getByText('snapshot-1')).toBeInTheDocument();
  });

  it('shows a recovery error state when the profile is missing', async () => {
    mockedGetProfile.mockRejectedValueOnce(new ApiError(404, 'missing'));

    renderWithRouter([{ path: '/profiles/:profileId', element: <ProfileDetailPage /> }], ['/profiles/missing']);

    expect(await screen.findByText('配置不存在')).toBeInTheDocument();
    expect(screen.getByText('请检查配置 ID 是否正确，或返回配置列表查看可用配置。')).toBeInTheDocument();
  });
});
