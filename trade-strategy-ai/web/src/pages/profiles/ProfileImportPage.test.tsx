import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { importProfile } from '@/lib/api/profiles';
import { ProfileImportPage } from './ProfileImportPage';

vi.mock('@/lib/api/profiles', () => ({
  getProfile: vi.fn(),
  getProfileSnapshot: vi.fn(),
  importProfile: vi.fn(),
  listProfiles: vi.fn(),
}));

const mockedImportProfile = vi.mocked(importProfile);

describe('ProfileImportPage', () => {
  it('submits an import request and shows the returned result', async () => {
    const user = userEvent.setup();

    mockedImportProfile.mockResolvedValue({
      created: true,
      profile: {
        profile_id: 'default',
        name: 'Default Profile',
        environment: 'production',
        version: 1,
        sections: {},
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T08:00:00Z',
        updated_at: '2026-05-16T08:00:00Z',
        archived_at: null,
      },
      snapshot: {
        snapshot_id: 'snapshot-1',
        profile_id: 'default',
        job_id: null,
        source: 'app.template.yaml',
        config_path: 'config/app.template.yaml',
        config_hash: 'hash-1',
        masked_snapshot: {},
        masked_sections: [],
        validation_status: 'validated',
        captured_at: '2026-05-16T08:00:00Z',
        snapshot_path: '/tmp/profile-snapshot.json',
      },
    });

    renderWithRouter([{ path: '/profiles/import', element: <ProfileImportPage /> }], ['/profiles/import']);

    expect(await screen.findByText(/如果系统状态页仍显示 default 兜底/)).toBeInTheDocument();
    await user.clear(screen.getByLabelText('配置 ID'));
    await user.type(screen.getByLabelText('配置 ID'), 'default');
    await user.selectOptions(screen.getByLabelText('导入模板'), 'app.template.yaml');
    await user.clear(screen.getByLabelText('创建者'));
    await user.type(screen.getByLabelText('创建者'), 'web');

    await user.click(screen.getByRole('button', { name: '保存并导入' }));

    await waitFor(() => {
      expect(mockedImportProfile).toHaveBeenCalledWith(
        expect.objectContaining({
          profile_id: 'default',
          source: 'app.template.yaml',
          created_by: 'web',
        }),
      );
    });

    expect(await screen.findByText('已创建正式配置。')).toBeInTheDocument();
    expect(screen.getByText(/快照：snapshot-1/)).toBeInTheDocument();
  });
});
