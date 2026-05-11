import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { OpsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { createRecoveryBackup, listRecoveryBackups, restoreRecoveryBackup } from '@/lib/api/ops';

vi.mock('@/lib/api/ops', () => ({
  createRecoveryBackup: vi.fn(),
  listRecoveryBackups: vi.fn(),
  restoreRecoveryBackup: vi.fn(),
}));

const mockedListRecoveryBackups = vi.mocked(listRecoveryBackups);
const mockedCreateRecoveryBackup = vi.mocked(createRecoveryBackup);
const mockedRestoreRecoveryBackup = vi.mocked(restoreRecoveryBackup);

describe('OpsPage', () => {
  it('renders the recovery center and lists available backups', async () => {
    mockedListRecoveryBackups.mockResolvedValue({
      base_dir: '/project',
      count: 1,
      items: [
        {
          path: '/project/data/backups/20260511-080000',
          name: '20260511-080000',
          size_bytes: 4096,
          modified_at: '2026-05-11T08:00:00Z',
          tables: ['jobs', 'artifacts'],
          row_counts: { jobs: 1, artifacts: 2 },
          include_processed: true,
          processed_copied: true,
        },
      ],
    });

    renderWithRouter([{ path: '/ops', element: <OpsPage /> }], ['/ops'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: 'Recovery Center' })).toBeInTheDocument();
    expect(await screen.findByText('/project/data/backups/20260511-080000')).toBeInTheDocument();
    expect(screen.getByText('项目级备份、恢复和回滚演练入口。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create backup' })).toBeEnabled();
  });

  it('creates a project backup and restores after typed confirmation', async () => {
    const user = userEvent.setup();

    mockedListRecoveryBackups.mockResolvedValue({
      base_dir: '/project',
      count: 1,
      items: [
        {
          path: '/project/data/backups/20260511-080000',
          name: '20260511-080000',
          size_bytes: 4096,
          modified_at: '2026-05-11T08:00:00Z',
          tables: ['jobs', 'artifacts'],
          row_counts: { jobs: 1, artifacts: 2 },
          include_processed: true,
          processed_copied: true,
        },
      ],
    });
    mockedCreateRecoveryBackup.mockResolvedValue({
      backup_dir: '/project/data/backups/20260511-120000',
      tables: ['jobs', 'artifacts'],
      row_counts: { jobs: 1, artifacts: 2 },
      include_processed: true,
      processed_copied: true,
    });
    mockedRestoreRecoveryBackup.mockResolvedValue({
      backup_dir: '/project/data/backups/20260511-080000',
      tables: ['jobs', 'artifacts'],
      row_counts: { jobs: 1, artifacts: 2 },
      include_processed: true,
      processed_restored: true,
    });

    renderWithRouter([{ path: '/ops', element: <OpsPage /> }], ['/ops'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    await user.click(await screen.findByRole('button', { name: 'Create backup' }));
    await user.click(screen.getByRole('button', { name: 'Confirm backup' }));

    await waitFor(() => {
      expect(mockedCreateRecoveryBackup).toHaveBeenCalledWith({ include_processed: true });
    });

    await user.click(await screen.findByRole('button', { name: 'Restore' }));
    expect(await screen.findByRole('heading', { name: 'Confirm project restore' })).toBeInTheDocument();
    const confirmInput = screen.getByLabelText('Restore confirmation');
    await user.type(confirmInput, 'RESTORE');
    await user.click(screen.getByRole('button', { name: 'Confirm restore' }));

    await waitFor(() => {
      expect(mockedRestoreRecoveryBackup).toHaveBeenCalledWith({
        backup_path: '/project/data/backups/20260511-080000',
        include_processed: true,
        confirmed: true,
      });
    });
  });

  it('disables recovery actions for operator principals', async () => {
    mockedListRecoveryBackups.mockResolvedValue({
      base_dir: '/project',
      count: 0,
      items: [],
    });

    renderWithRouter([{ path: '/ops', element: <OpsPage /> }], ['/ops'], {
      initialPrincipal: {
        role: 'operator',
        api_key_label: 'Local Operator',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: 'Recovery Center' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Create backup' })).toBeDisabled();
    expect(await screen.findByText('仅 admin 可执行项目级备份与恢复。')).toBeInTheDocument();
  });
});
