import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { getProfileSnapshot } from '@/lib/api/profiles';
import { ProfileSnapshotPage } from './ProfileSnapshotPage';

vi.mock('@/lib/api/profiles', () => ({
  getProfile: vi.fn(),
  getProfileSnapshot: vi.fn(),
  importProfile: vi.fn(),
  listProfiles: vi.fn(),
}));

const mockedGetProfileSnapshot = vi.mocked(getProfileSnapshot);

describe('ProfileSnapshotPage', () => {
  it('renders the read-only snapshot viewer in chinese', async () => {
    mockedGetProfileSnapshot.mockResolvedValue({
      profile: {
        profile_id: 'default',
        name: '默认配置',
        environment: 'production',
        version: 2,
        sections: {},
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T08:00:00Z',
        updated_at: '2026-05-16T08:30:00Z',
        archived_at: null,
      },
      snapshot: {
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
      linked_job: null,
    });

    renderWithRouter(
      [{ path: '/profiles/:profileId/snapshots/:snapshotId', element: <ProfileSnapshotPage /> }],
      ['/profiles/default/snapshots/snapshot-1'],
    );

    expect(await screen.findByRole('heading', { name: '配置快照' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('脱敏快照内容')).toBeInTheDocument();
      expect(screen.getByText(/snapshot-1/)).toBeInTheDocument();
    });
  });
});
