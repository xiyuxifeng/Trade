import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { archiveProfile, getProfileEdit, updateProfile, validateProfileUpdate } from '@/lib/api/profiles';
import { ProfileEditPage } from './ProfileEditPage';

vi.mock('@/lib/api/profiles', () => ({
  archiveProfile: vi.fn(),
  getProfile: vi.fn(),
  getProfileEdit: vi.fn(),
  getProfileSnapshot: vi.fn(),
  importProfile: vi.fn(),
  listProfiles: vi.fn(),
  updateProfile: vi.fn(),
  validateProfileUpdate: vi.fn(),
}));

const mockedGetProfileEdit = vi.mocked(getProfileEdit);
const mockedValidateProfileUpdate = vi.mocked(validateProfileUpdate);
const mockedUpdateProfile = vi.mocked(updateProfile);
const mockedArchiveProfile = vi.mocked(archiveProfile);

describe('ProfileEditPage', () => {
  it('renders the edit workspace and section editors', async () => {
    mockedGetProfileEdit.mockResolvedValue({
      profile: {
        profile_id: 'default',
        name: '默认配置',
        environment: 'production',
        version: 2,
        sections: { app: { timezone: 'Asia/Shanghai' }, market: { enabled: true } },
        secret_refs: { 'app.api_key': 'masked' },
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T08:00:00Z',
        updated_at: '2026-05-16T08:30:00Z',
        archived_at: null,
      },
      draft: {
        name: '默认配置',
        environment: 'production',
        sections: { app: { timezone: 'Asia/Shanghai' }, market: { enabled: true } },
      },
      preview: {
        profile_id: 'default',
        name: '默认配置',
        environment: 'production',
        version: 3,
        sections: { app: { timezone: 'Asia/Shanghai' }, market: { enabled: true } },
        secret_refs: { 'app.api_key': 'masked' },
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T08:00:00Z',
        updated_at: '2026-05-16T08:30:00Z',
        archived_at: null,
      },
      section_guide: [
        {
          key: 'app',
          title: 'App',
          description: '应用分区',
          source: '当前 Profile 版本',
          default_value: { timezone: 'Asia/Shanghai' },
          current_value: { timezone: 'Asia/Shanghai' },
          draft_value: { timezone: 'Asia/Shanghai' },
        },
        {
          key: 'market',
          title: 'Market',
          description: '市场分区',
          source: '当前 Profile 版本',
          default_value: { enabled: true },
          current_value: { enabled: true },
          draft_value: { enabled: true },
        },
      ],
      validation: { valid: true, issues: [], next_version: 3, validation_status: 'validated' },
    } as unknown as GetProfileEditResponse);
    mockedValidateProfileUpdate.mockResolvedValue({
      profile: { profile_id: 'default' },
      draft: { name: '默认配置', environment: 'production', sections: {} },
      preview: { profile_id: 'default' },
      section_guide: [],
      validation: { valid: true, issues: [], next_version: 3, validation_status: 'validated' },
    } as unknown as ValidateProfileUpdateResponse);
    mockedUpdateProfile.mockResolvedValue({
      profile: { profile_id: 'default', validation_status: 'validated' },
      snapshot: { snapshot_id: 'snapshot-2' },
      validation: { valid: true, issues: [], next_version: 3, validation_status: 'validated' },
    } as unknown as UpdateProfileResponse);

    renderWithRouter([{ path: '/profiles/:profileId/edit', element: <ProfileEditPage /> }], ['/profiles/default/edit']);

    expect(await screen.findByText('配置编辑')).toBeInTheDocument();
    expect(screen.getByText('基础信息')).toBeInTheDocument();
    expect(screen.getByText('保存新版本')).toBeInTheDocument();
    expect(screen.getByText('校验配置')).toBeInTheDocument();
    expect(screen.getByText('App')).toBeInTheDocument();
    expect(screen.getByText('Market')).toBeInTheDocument();
    expect(mockedValidateProfileUpdate).not.toHaveBeenCalled();
  });

  it('shows validation issues without attempting to save invalid content', async () => {
    mockedGetProfileEdit.mockResolvedValue({
      profile: {
        profile_id: 'default',
        name: '默认配置',
        environment: 'production',
        version: 2,
        sections: { app: { timezone: 'Asia/Shanghai' } },
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T08:00:00Z',
        updated_at: '2026-05-16T08:30:00Z',
        archived_at: null,
      },
      draft: {
        name: '默认配置',
        environment: 'production',
        sections: { app: { timezone: 'Asia/Shanghai' } },
      },
      preview: {
        profile_id: 'default',
        name: '默认配置',
        environment: 'production',
        version: 3,
        sections: { app: { timezone: 'Asia/Shanghai' } },
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T08:00:00Z',
        updated_at: '2026-05-16T08:30:00Z',
        archived_at: null,
      },
      section_guide: [
        {
          key: 'app',
          title: 'App',
          description: '应用分区',
          source: '当前 Profile 版本',
          default_value: { timezone: 'Asia/Shanghai' },
          current_value: { timezone: 'Asia/Shanghai' },
          draft_value: { timezone: 'Asia/Shanghai' },
        },
      ],
      validation: { valid: false, issues: [{ field: 'environment', message: '运行环境不能为空' }], next_version: 3, validation_status: 'invalid_config' },
    } as unknown as GetProfileEditResponse);

    renderWithRouter([{ path: '/profiles/:profileId/edit', element: <ProfileEditPage /> }], ['/profiles/default/edit']);

    expect(await screen.findByText('运行环境不能为空')).toBeInTheDocument();
    expect(mockedValidateProfileUpdate).not.toHaveBeenCalled();
    expect(mockedUpdateProfile).not.toHaveBeenCalled();
    expect(mockedArchiveProfile).not.toHaveBeenCalled();
  });
});
type GetProfileEditResponse = Awaited<ReturnType<typeof getProfileEdit>>;
type ValidateProfileUpdateResponse = Awaited<ReturnType<typeof validateProfileUpdate>>;
type UpdateProfileResponse = Awaited<ReturnType<typeof updateProfile>>;
