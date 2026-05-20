import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { AuditPage } from './AuditPage';
import { BackupPage } from './BackupPage';
import { DatabaseMigrationPage } from './DatabaseMigrationPage';
import { HealthPage } from './HealthPage';
import { RestorePage } from './RestorePage';
import { UsersPage } from './UsersPage';

vi.mock('@/features/admin-audit/admin-audit-workspace', () => ({
  AdminAuditWorkspace: () => <div>audit-workspace</div>,
}));

vi.mock('@/features/system-management/system-management-workspace', () => ({
  BackupManagementSection: () => <div>backup-section</div>,
  DatabaseMigrationSection: () => <div>database-section</div>,
  UserManagementSection: () => <div>user-section</div>,
}));

vi.mock('@/features/data-health', () => ({
  OperationalDashboardCenter: () => <div>health-section</div>,
}));

describe('system detail pages', () => {
  it('renders the audit page wrapper', async () => {
    renderWithRouter([{ path: '/system/audit', element: <AuditPage /> }], ['/system/audit'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByText('audit-workspace')).toBeInTheDocument();
  });

  it('renders the users page wrapper', async () => {
    renderWithRouter([{ path: '/system/users', element: <UsersPage /> }], ['/system/users'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '用户管理' })).toBeInTheDocument();
    expect(screen.getByText('user-section')).toBeInTheDocument();
  });

  it('renders the health page wrapper', async () => {
    renderWithRouter([{ path: '/system/health', element: <HealthPage /> }], ['/system/health'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '系统健康检查' })).toBeInTheDocument();
    expect(screen.getByText('health-section')).toBeInTheDocument();
  });

  it('renders the migration page wrapper', async () => {
    renderWithRouter(
      [{ path: '/system/db-migrate', element: <DatabaseMigrationPage /> }],
      ['/system/db-migrate'],
      {
        initialPrincipal: {
          role: 'admin',
          api_key_label: 'Local Admin',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByRole('heading', { name: '数据库迁移' })).toBeInTheDocument();
    expect(screen.getByText('database-section')).toBeInTheDocument();
  });

  it('renders the backup page wrapper', async () => {
    renderWithRouter([{ path: '/system/backup', element: <BackupPage /> }], ['/system/backup'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '数据备份' })).toBeInTheDocument();
    expect(screen.getByText('backup-section')).toBeInTheDocument();
  });

  it('renders the restore page wrapper', async () => {
    renderWithRouter([{ path: '/system/restore', element: <RestorePage /> }], ['/system/restore'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '数据恢复' })).toBeInTheDocument();
    expect(screen.getByText('backup-section')).toBeInTheDocument();
  });
});
