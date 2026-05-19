import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { SettingsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import {
  getSettingsConfig,
  getSettingsSchema,
  listSettingsBackups,
  restoreSettingsBackup,
  saveSettings,
  validateSettingsDraft,
} from '@/lib/api/settings';

vi.mock('@/lib/api/settings', () => ({
  getSettingsConfig: vi.fn(),
  getSettingsSchema: vi.fn(),
  listSettingsBackups: vi.fn(),
  restoreSettingsBackup: vi.fn(),
  saveSettings: vi.fn(),
  validateSettingsDraft: vi.fn(),
}));

const mockedGetSettingsConfig = vi.mocked(getSettingsConfig);
const mockedGetSettingsSchema = vi.mocked(getSettingsSchema);
const mockedListSettingsBackups = vi.mocked(listSettingsBackups);
const mockedRestoreSettingsBackup = vi.mocked(restoreSettingsBackup);
const mockedSaveSettings = vi.mocked(saveSettings);
const mockedValidateSettingsDraft = vi.mocked(validateSettingsDraft);

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('previews diff and saves the pending config section', async () => {
    const user = userEvent.setup();

    const sections = [
      { key: 'timezone', title: 'Timezone', summary: '时区', type: 'value', editable: true },
      { key: 'database', title: 'Database', summary: '数据库', type: 'object', editable: true },
      { key: 'api', title: 'API', summary: 'API 服务', type: 'object', editable: true },
    ];
    const config = {
      timezone: 'Asia/Shanghai',
      database: { url: 'postgresql://trade:***@localhost:5432/trade_strategy_ai', echo: false },
      api: { timeout_seconds: 300 },
    };

    mockedGetSettingsConfig.mockResolvedValue({
      config_path: 'config/app.yaml',
      config,
      sections,
    });
    mockedGetSettingsSchema.mockResolvedValue({
      config_path: 'config/app.yaml',
      sections,
    });
    mockedListSettingsBackups.mockResolvedValue({
      config_path: 'config/app.yaml',
      count: 1,
      items: [
        {
          path: '/tmp/backups/app.20260510-080000.yaml',
          name: 'app.20260510-080000.yaml',
          size_bytes: 2048,
          modified_at: '2026-05-10T08:00:00Z',
        },
      ],
    });
    mockedValidateSettingsDraft.mockResolvedValue({
      config_path: 'config/app.yaml',
      diff: { timezone: { before: 'Asia/Shanghai', after: 'Asia/Tokyo' } },
      masked_config: config,
    });
    mockedSaveSettings.mockResolvedValue({
      config_path: 'config/app.yaml',
      backup_path: '/tmp/backups/app.20260510-080001.yaml',
      config,
    });

    renderWithRouter(
      [{ path: '/settings', element: <SettingsPage /> }],
      ['/settings'],
      {
        initialPrincipal: {
          role: 'admin',
          api_key_label: 'Local Admin',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByRole('heading', { name: '配置管理' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '返回管理中心' })).toBeInTheDocument();
    expect(await screen.findByText('配置文件路径')).toBeInTheDocument();

    const editor = await screen.findByLabelText('Timezone');
    await user.clear(editor);
    await user.type(editor, 'Asia/Tokyo');

    await user.click(screen.getByRole('button', { name: '预览差异' }));

    await waitFor(() => {
      expect(mockedValidateSettingsDraft).toHaveBeenCalledWith({
        config_path: 'config/app.yaml',
        draft: { timezone: 'Asia/Tokyo' },
      });
    });

    expect(await screen.findByText('Validation diff')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '保存配置' }));
    expect(await screen.findByRole('heading', { name: 'Confirm save' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm save' }));

    await waitFor(() => {
      expect(mockedSaveSettings).toHaveBeenCalledWith({
        config_path: 'config/app.yaml',
        draft: { timezone: 'Asia/Tokyo' },
        confirmed: true,
      });
    });

    expect(await screen.findByText(/已保存，备份路径/)).toBeInTheDocument();
  });

  it('lists backups and restores a selected backup after confirmation', async () => {
    const user = userEvent.setup();

    const sections = [
      { key: 'timezone', title: 'Timezone', summary: '时区', type: 'value', editable: true },
    ];

    mockedGetSettingsConfig.mockResolvedValue({
      config_path: 'config/app.yaml',
      config: { timezone: 'Asia/Shanghai' },
      sections,
    });
    mockedGetSettingsSchema.mockResolvedValue({
      config_path: 'config/app.yaml',
      sections,
    });
    mockedListSettingsBackups.mockResolvedValue({
      config_path: 'config/app.yaml',
      count: 1,
      items: [
        {
          path: '/tmp/backups/app.20260510-080000.yaml',
          name: 'app.20260510-080000.yaml',
          size_bytes: 2048,
          modified_at: '2026-05-10T08:00:00Z',
        },
      ],
    });
    mockedRestoreSettingsBackup.mockResolvedValue({
      config_path: 'config/app.yaml',
      backup_path: '/tmp/backups/app.20260510-080000.yaml',
      config: { timezone: 'Asia/Shanghai' },
    });

    renderWithRouter(
      [{ path: '/settings', element: <SettingsPage /> }],
      ['/settings'],
      {
        initialPrincipal: {
          role: 'admin',
          api_key_label: 'Local Admin',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByRole('heading', { name: '配置管理' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Backup history' })).toBeInTheDocument();
    expect(await screen.findByText('app.20260510-080000.yaml')).toBeInTheDocument();
    await user.click(await screen.findByRole('button', { name: 'Restore' }));
    expect(await screen.findByRole('heading', { name: 'Confirm restore' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm restore' }));

    await waitFor(() => {
      expect(mockedRestoreSettingsBackup).toHaveBeenCalledWith({
        config_path: 'config/app.yaml',
        backup_path: '/tmp/backups/app.20260510-080000.yaml',
        confirmed: true,
      });
    });

    expect(await screen.findByText(/已从备份恢复/)).toBeInTheDocument();
  });

  it('disables save and restore actions for operator principals', async () => {
    const sections = [{ key: 'timezone', title: 'Timezone', summary: '时区', type: 'value', editable: true }];

    mockedGetSettingsConfig.mockResolvedValue({
      config_path: 'config/app.yaml',
      config: { timezone: 'Asia/Shanghai' },
      sections,
    });
    mockedGetSettingsSchema.mockResolvedValue({
      config_path: 'config/app.yaml',
      sections,
    });
    mockedListSettingsBackups.mockResolvedValue({
      config_path: 'config/app.yaml',
      count: 1,
      items: [
        {
          path: '/tmp/backups/app.20260510-080000.yaml',
          name: 'app.20260510-080000.yaml',
          size_bytes: 2048,
          modified_at: '2026-05-10T08:00:00Z',
        },
      ],
    });

    renderWithRouter(
      [{ path: '/settings', element: <SettingsPage /> }],
      ['/settings'],
      {
        initialPrincipal: {
          role: 'operator',
          api_key_label: 'Local Operator',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByRole('heading', { name: '没有权限访问配置管理' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回管理中心' })).toBeInTheDocument();
    expect(mockedGetSettingsConfig).not.toHaveBeenCalled();
    expect(mockedGetSettingsSchema).not.toHaveBeenCalled();
    expect(mockedListSettingsBackups).not.toHaveBeenCalled();
  });
});
