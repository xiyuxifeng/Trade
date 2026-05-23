import userEvent from '@testing-library/user-event';
import { within } from '@testing-library/react';
import { screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SystemManagementWorkspace } from './system-management-workspace';
import { renderWithRouter } from '@/test/test-utils';
import { createJob } from '@/lib/api/jobs';
import { createUser, deleteUser, listUsers, updateUser } from '@/lib/api/auth';
import { listJobAudits } from '@/lib/api/job-audits';
import { listPermissionDeniedLogs } from '@/lib/api/security-audits';
import { listProfiles } from '@/lib/api/profiles';
import { listRecoveryBackups, listRecoveryBackupTargets } from '@/lib/api/ops';

const navigateMock = vi.fn();

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

vi.mock('@/features/data-health', () => ({
  OperationalDashboardCenter: () => <div>dashboard-stub</div>,
}));

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
}));

vi.mock('@/lib/api/auth', () => ({
  getCurrentPrincipal: vi.fn(),
  createUser: vi.fn(),
  deleteUser: vi.fn(),
  listUsers: vi.fn(),
  updateUser: vi.fn(),
}));

vi.mock('@/lib/api/job-audits', () => ({
  listJobAudits: vi.fn(),
}));

vi.mock('@/lib/api/security-audits', () => ({
  listPermissionDeniedLogs: vi.fn(),
}));

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
}));

vi.mock('@/lib/api/ops', () => ({
  listRecoveryBackups: vi.fn(),
  listRecoveryBackupTargets: vi.fn(),
}));

const mockedCreateJob = vi.mocked(createJob);
const mockedCreateUser = vi.mocked(createUser);
const mockedDeleteUser = vi.mocked(deleteUser);
const mockedListUsers = vi.mocked(listUsers);
const mockedUpdateUser = vi.mocked(updateUser);
const mockedListJobAudits = vi.mocked(listJobAudits);
const mockedListPermissionDeniedLogs = vi.mocked(listPermissionDeniedLogs);
const mockedListProfiles = vi.mocked(listProfiles);
const mockedListRecoveryBackups = vi.mocked(listRecoveryBackups);
const mockedListRecoveryBackupTargets = vi.mocked(listRecoveryBackupTargets);

function seedWorkspaceData() {
  mockedListProfiles.mockResolvedValue({
    count: 2,
    total: 2,
    skip: 0,
    limit: 100,
    items: [
      {
        profile_id: 'profile-default',
        name: '默认配置',
        environment: 'production',
        version: 3,
        sections: {},
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-11T09:00:00Z',
        updated_at: '2026-05-11T09:00:00Z',
        archived_at: null,
      },
      {
        profile_id: 'profile-ops',
        name: '运维配置',
        environment: 'production',
        version: 1,
        sections: {},
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-11T09:00:00Z',
        updated_at: '2026-05-11T09:00:00Z',
        archived_at: null,
      },
    ],
  } as never);

  mockedListUsers.mockResolvedValue([
    {
      id: 'user-1',
      username: 'alice',
      role: 'admin',
      is_active: true,
      display_name: 'Alice',
      last_login_at: '2026-05-11T10:00:00Z',
      created_at: '2026-05-10T09:00:00Z',
    },
  ] as never);

  mockedListJobAudits.mockResolvedValue({
    items: [
      {
        id: 'audit-1',
        job_id: 'job-1',
        job_type: 'backup-data',
        actor: 'alice',
        operation: 'create',
        confirmed: true,
        event_at: '2026-05-11T10:00:00Z',
      },
    ],
    summary: { total: 1, high_risk_count: 1 },
  } as never);

  mockedListPermissionDeniedLogs.mockResolvedValue({
    items: [
      {
        id: 'denied-1',
        actor: 'bob',
        request_context: {
          request: {
            method: 'GET',
            path: '/api/ui/v1/secret',
          },
        },
        event_at: '2026-05-11T10:05:00Z',
      },
    ],
    summary: { total: 1 },
  } as never);

  mockedListRecoveryBackupTargets.mockResolvedValue({
    base_dir: 'trade-strategy-ai',
    backup_root: '/data/backups',
    count: 2,
    items: [
      {
        id: 'default',
        label: '默认备份目录',
        description: '默认白名单目录',
        path: '/data/backups/default',
        mode: 'auto',
      },
      {
        id: 'archive',
        label: '归档备份目录',
        description: '归档白名单目录',
        path: '/data/backups/archive',
        mode: 'path',
      },
    ],
  } as never);

  mockedListRecoveryBackups.mockResolvedValue({
    base_dir: 'trade-strategy-ai',
    backup_root: '/data/backups',
    count: 1,
    items: [
      {
        backup_id: 'backup-001',
        path: '/data/backups/default/backup-001',
        name: '2026-05-11-080000',
        size_bytes: 2048,
        modified_at: '2026-05-11T08:00:00Z',
        tables: ['jobs'],
        row_counts: { jobs: 2 },
        include_processed: true,
        processed_copied: true,
      },
    ],
  } as never);
}

beforeEach(() => {
  vi.clearAllMocks();
  navigateMock.mockReset();
  seedWorkspaceData();
  mockedCreateJob.mockImplementation(async () => ({
    created: true,
    job: { id: `job-${mockedCreateJob.mock.calls.length}` },
    job_dir: '/tmp/jobs/job-1',
    log_path: '/tmp/jobs/job-1/job.log',
    params_path: '/tmp/jobs/job-1/params.json',
    result_path: '/tmp/jobs/job-1/result.json',
    artifacts_path: '/tmp/jobs/job-1/artifacts.json',
  } as never));
  mockedCreateUser.mockResolvedValue({
    id: 'user-2',
    username: 'new-user',
    role: 'viewer',
    is_active: true,
    display_name: 'New User',
    last_login_at: null,
    created_at: '2026-05-11T09:30:00Z',
  } as never);
  mockedUpdateUser.mockResolvedValue({
    id: 'user-1',
    username: 'alice',
    role: 'operator',
    is_active: true,
    display_name: 'Alice Ops',
    last_login_at: '2026-05-11T10:00:00Z',
    created_at: '2026-05-10T09:00:00Z',
  } as never);
  mockedDeleteUser.mockResolvedValue({ message: 'deleted' } as never);
});

describe('SystemManagementWorkspace', () => {
  it('renders the system workspace and creates job-based operations from the selected profile', async () => {
    const user = userEvent.setup();

    renderWithRouter(
      [{ path: '/system', element: <SystemManagementWorkspace /> }],
      ['/system'],
      {
        initialPrincipal: {
          role: 'admin',
          api_key_label: 'Local Admin',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByText('dashboard-stub')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: '用户管理' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: '数据库迁移' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: '数据备份与恢复' })).toBeInTheDocument();

    const migrateButton = screen.getByRole('button', { name: '创建数据库迁移 Job' });
    await user.click(migrateButton);
    const migrateDialog = await screen.findByRole('dialog', { name: '确认创建数据库迁移 Job' });
    await user.click(within(migrateDialog).getByRole('button', { name: '确认创建' }));

    await waitFor(() =>
      expect(mockedCreateJob).toHaveBeenCalledWith({
        job_type: 'db-migrate',
        params: { profile_id: 'profile-default' },
        created_by: 'web',
        confirmed: true,
      }),
    );

    const backupTarget = screen
      .getAllByRole('combobox')
      .find((element) => element.textContent?.includes('归档备份目录')) as HTMLSelectElement | undefined;
    expect(backupTarget).toBeTruthy();
    await user.selectOptions(backupTarget as HTMLSelectElement, 'archive');
    await user.click(screen.getByRole('button', { name: '创建备份 Job' }));
    const backupDialog = await screen.findByRole('dialog', { name: '确认创建备份 Job' });
    await user.click(within(backupDialog).getByRole('button', { name: '确认创建' }));

    await waitFor(() =>
      expect(mockedCreateJob).toHaveBeenCalledWith({
        job_type: 'backup-data',
        params: {
          profile_id: 'profile-default',
          base_dir: 'trade-strategy-ai',
          backup_dir_id: 'archive',
          backup_dir: '/data/backups/archive',
          include_processed: true,
        },
        created_by: 'web',
        confirmed: true,
      }),
    );

    await user.click(screen.getByRole('button', { name: '恢复' }));
    const restoreDialog = await screen.findByRole('dialog', { name: '恢复备份 Job' });
    await user.click(within(restoreDialog).getByRole('checkbox', { name: 'force' }));
    await user.click(within(restoreDialog).getByRole('button', { name: '确认创建恢复 Job' }));

    await waitFor(() =>
      expect(mockedCreateJob).toHaveBeenCalledWith({
        job_type: 'restore-data',
        params: {
          profile_id: 'profile-default',
          base_dir: 'trade-strategy-ai',
          backup_id: 'backup-001',
          backup_dir: '/data/backups/default/backup-001',
          include_processed: true,
          force: true,
        },
        created_by: 'web',
        confirmed: true,
      }),
    );

    expect(navigateMock).toHaveBeenCalledWith('/jobs/job-1');
  });

  it('supports user creation, editing, and deletion without creating a job', async () => {
    const user = userEvent.setup();

    renderWithRouter(
      [{ path: '/system', element: <SystemManagementWorkspace /> }],
      ['/system'],
      {
        initialPrincipal: {
          role: 'admin',
          api_key_label: 'Local Admin',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByText('用户管理')).toBeInTheDocument();
    expect(screen.getByLabelText('用户名')).toHaveValue('');
    expect(screen.getByLabelText('用户名')).toHaveAttribute('autocomplete', 'off');
    expect(screen.getByLabelText('显示名称')).toHaveValue('');
    expect(screen.getByLabelText('显示名称')).toHaveAttribute('autocomplete', 'off');
    expect(screen.getByLabelText('密码')).toHaveValue('');
    expect(screen.getByLabelText('密码')).toHaveAttribute('autocomplete', 'new-password');

    await user.type(screen.getByLabelText('用户名'), 'new-user');
    await user.type(screen.getByLabelText('显示名称'), 'New User');
    await user.type(screen.getByLabelText('密码'), 'password123');
    await user.selectOptions(screen.getByLabelText('角色'), 'operator');
    await user.click(screen.getByRole('button', { name: '创建用户' }));

    await waitFor(() =>
      expect(mockedCreateUser).toHaveBeenCalledWith({
        username: 'new-user',
        password: 'password123',
        role: 'operator',
        display_name: 'New User',
      }),
    );
    expect(await screen.findByText('用户已创建')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '编辑' }));
    const passwordField = screen.getByLabelText('密码（留空则不修改）');
    await user.type(passwordField, 'new-password');
    await user.selectOptions(screen.getByLabelText('角色'), 'operator');
    await user.click(screen.getByRole('button', { name: '保存修改' }));

    await waitFor(() =>
      expect(mockedUpdateUser).toHaveBeenCalledWith('user-1', {
        role: 'operator',
        display_name: 'Alice',
        is_active: true,
        password: 'new-password',
      }),
    );
    expect(await screen.findByText('用户已更新')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '删除' }));
    const deleteDialog = await screen.findByRole('dialog', { name: '删除用户' });
    await user.click(within(deleteDialog).getByRole('button', { name: '确认删除' }));

    await waitFor(() => expect(mockedDeleteUser).toHaveBeenCalledWith('user-1'));
    expect(await screen.findByText('用户已删除')).toBeInTheDocument();
  });

  it('blocks access for non-admin principals', async () => {
    renderWithRouter(
      [{ path: '/system', element: <SystemManagementWorkspace /> }],
      ['/system'],
      {
        initialPrincipal: {
          role: 'operator',
          api_key_label: 'Local Operator',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByRole('heading', { name: '没有权限访问系统管理' })).toBeInTheDocument();
  });
});
