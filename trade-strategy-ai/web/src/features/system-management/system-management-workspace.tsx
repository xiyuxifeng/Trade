import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { ConfirmDialog, EmptyState, ErrorState, LoadingState, SectionCard } from '@/components/kit';
import { OperationalDashboardCenter } from '@/features/data-health';
import { useAuth } from '@/features/auth/auth-context';
import { listRecoveryBackupTargets, listRecoveryBackups } from '@/lib/api/ops';
import { createUser, deleteUser, listUsers, updateUser } from '@/lib/api/auth';
import { listJobAudits } from '@/lib/api/job-audits';
import { listPermissionDeniedLogs } from '@/lib/api/security-audits';
import { listProfiles } from '@/lib/api/profiles';
import { createJob } from '@/lib/api/jobs';
import { ApiError } from '@/lib/api/http';
import type { RecoveryBackupItem, RecoveryBackupTarget } from '@/types/ops';
import type { ProfileRecord } from '@/types/profile';
import type { UserRecord } from '@/lib/api/auth';

type UserFormState = {
  username: string;
  display_name: string;
  role: string;
  password: string;
  is_active: boolean;
};

type BackupFormState = {
  profile_id: string;
  backup_dir_id: string;
  include_processed: boolean;
};

type RestoreFormState = {
  profile_id: string;
  include_processed: boolean;
  force: boolean;
};

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '请求失败';
}

function roleBadge(role: string) {
  if (role === 'admin') return 'destructive';
  if (role === 'operator') return 'warning';
  return 'info';
}

function backupStatusLabel(item: RecoveryBackupItem) {
  if (item.processed_copied) {
    return '已包含 processed';
  }
  return '未包含 processed';
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function StatCard({ label, value, hint }: { label: string; value: string | number; hint: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{hint}</p>
    </div>
  );
}

function UserManagementSection() {
  const queryClient = useQueryClient();
  const usersQuery = useQuery({
    queryKey: ['system-users'],
    queryFn: () => listUsers(),
    staleTime: 30_000,
  });
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<UserRecord | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [form, setForm] = useState<UserFormState>({
    username: '',
    display_name: '',
    role: 'viewer',
    password: '',
    is_active: true,
  });

  useEffect(() => {
    if (!editingUser) {
      return;
    }
    setForm({
      username: editingUser.username,
      display_name: editingUser.display_name ?? '',
      role: editingUser.role,
      password: '',
      is_active: editingUser.is_active,
    });
  }, [editingUser]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingUser) {
        return updateUser(editingUser.id, {
          role: form.role,
          display_name: form.display_name.trim() || undefined,
          is_active: form.is_active,
          password: form.password.trim() || undefined,
        });
      }

      if (!form.username.trim()) {
        throw new Error('用户名不能为空');
      }
      if (!form.password.trim()) {
        throw new Error('密码不能为空');
      }

      return createUser({
        username: form.username.trim(),
        password: form.password,
        role: form.role,
        display_name: form.display_name.trim() || undefined,
      });
    },
    onSuccess: async () => {
      setStatusMessage(editingUser ? '用户已更新' : '用户已创建');
      setErrorMessage(null);
      setEditingUser(null);
      setForm({
        username: '',
        display_name: '',
        role: 'viewer',
        password: '',
        is_active: true,
      });
      await queryClient.invalidateQueries({ queryKey: ['system-users'] });
    },
    onError: (error: unknown) => {
      setErrorMessage(getErrorMessage(error));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: async () => {
      setDeleteTarget(null);
      setStatusMessage('用户已删除');
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ['system-users'] });
    },
    onError: (error: unknown) => {
      setErrorMessage(getErrorMessage(error));
    },
  });

  if (usersQuery.isLoading) {
    return <LoadingState label="加载用户管理" description="正在读取当前系统用户列表。" />;
  }

  if (usersQuery.error) {
    return (
      <ErrorState
        category="permission denied"
        title="用户管理加载失败"
        description="用户列表接口请求失败。"
        suggestion="请重试或确认当前身份是否具备 admin 权限。"
        detail={getErrorMessage(usersQuery.error)}
        onRetry={() => {
          void usersQuery.refetch();
        }}
      />
    );
  }

  const users = usersQuery.data ?? [];

  return (
    <SectionCard
      title="用户管理"
      description="添加或删除用户，修改用户权限、启用状态和密码。"
      action={
        <Button
          variant="outline"
          onClick={() => {
            setEditingUser(null);
            setForm({
              username: '',
              display_name: '',
              role: 'viewer',
              password: '',
              is_active: true,
            });
          }}
        >
          <Plus className="mr-2 h-4 w-4" />
          新建用户
        </Button>
      }
    >
      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <StatCard label="用户总数" value={users.length} hint="当前系统中的所有账号" />
            <StatCard
              label="管理员"
              value={users.filter((user) => user.role === 'admin').length}
              hint="具备高权限管理能力的账号"
            />
            <StatCard
              label="活跃用户"
              value={users.filter((user) => user.is_active).length}
              hint="当前未禁用的账号"
            />
          </div>

          {statusMessage ? (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{statusMessage}</div>
          ) : null}
          {errorMessage ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{errorMessage}</div>
          ) : null}

          <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium text-slate-950">{editingUser ? '编辑用户' : '新增用户'}</p>
                <p className="text-sm text-slate-600">保存后会直接写入用户表，不会创建 Job。</p>
              </div>
              {editingUser ? (
                <Button
                  variant="outline"
                  onClick={() => {
                    setEditingUser(null);
                    setForm({
                      username: '',
                      display_name: '',
                      role: 'viewer',
                      password: '',
                      is_active: true,
                    });
                  }}
                >
                  取消编辑
                </Button>
              ) : null}
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-600">
                <span>用户名</span>
                <Input
                  disabled={Boolean(editingUser)}
                  placeholder="例如 alice"
                  value={form.username}
                  onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                />
              </label>
              <label className="space-y-2 text-sm text-slate-600">
                <span>显示名称</span>
                <Input
                  placeholder="例如 Alice"
                  value={form.display_name}
                  onChange={(event) => setForm((current) => ({ ...current, display_name: event.target.value }))}
                />
              </label>
              <label className="space-y-2 text-sm text-slate-600">
                <span>角色</span>
                <Select value={form.role} onChange={(event) => setForm((current) => ({ ...current, role: event.target.value }))}>
                  <option value="viewer">viewer</option>
                  <option value="operator">operator</option>
                  <option value="admin">admin</option>
                </Select>
              </label>
              <label className="space-y-2 text-sm text-slate-600">
                <span>密码{editingUser ? '（留空则不修改）' : ''}</span>
                <Input
                  type="password"
                  placeholder="至少 6 位"
                  value={form.password}
                  onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                />
              </label>
            </div>

            <label className="flex items-center gap-3 text-sm text-slate-700">
              <input
                checked={form.is_active}
                onChange={(event) => setForm((current) => ({ ...current, is_active: event.target.checked }))}
                type="checkbox"
              />
              账号启用
            </label>

            <div className="flex flex-wrap gap-3">
              <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? '保存中' : editingUser ? '保存修改' : '创建用户'}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setEditingUser(null);
                  setForm({
                    username: '',
                    display_name: '',
                    role: 'viewer',
                    password: '',
                    is_active: true,
                  });
                }}
              >
                重置
              </Button>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          {users.length ? (
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">用户</th>
                    <th className="px-4 py-3 font-medium">角色</th>
                    <th className="px-4 py-3 font-medium">状态</th>
                    <th className="px-4 py-3 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr className="border-t border-slate-200" key={user.id}>
                      <td className="px-4 py-3">
                        <p className="font-medium text-slate-950">{user.username}</p>
                        <p className="text-xs text-slate-500">{user.display_name ?? '未设置显示名称'}</p>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={roleBadge(user.role)}>{user.role}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={user.is_active ? 'success' : 'warning'}>{user.is_active ? 'active' : 'disabled'}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            variant="outline"
                            onClick={() => setEditingUser(user)}
                          >
                            编辑
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => setDeleteTarget(user)}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            删除
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="暂无用户" description="当前系统没有可管理的用户记录。" />
          )}
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteTarget(null);
          }
        }}
        title="删除用户"
        description="删除后会清除该用户会话，操作不可撤销。"
        confirmLabel="确认删除"
        onConfirm={async () => {
          if (!deleteTarget) {
            return;
          }
          await deleteMutation.mutateAsync(deleteTarget.id);
        }}
      >
        {deleteTarget ? (
          <div className="space-y-2">
            <p>用户名：{deleteTarget.username}</p>
            <p>角色：{deleteTarget.role}</p>
          </div>
        ) : null}
      </ConfirmDialog>
    </SectionCard>
  );
}

function AuditSummarySection() {
  const jobAuditQuery = useQuery({
    queryKey: ['system-job-audits'],
    queryFn: () => listJobAudits({ skip: 0, limit: 5 }),
    staleTime: 30_000,
  });
  const deniedQuery = useQuery({
    queryKey: ['system-permission-denied'],
    queryFn: () => listPermissionDeniedLogs({ skip: 0, limit: 5 }),
    staleTime: 30_000,
  });

  if (jobAuditQuery.isLoading || deniedQuery.isLoading) {
    return <LoadingState label="加载权限与审计" description="正在读取最近的审计记录。" />;
  }

  if (jobAuditQuery.error || deniedQuery.error) {
    return (
      <ErrorState
        category="permission denied"
        title="权限与审计加载失败"
        description="审计摘要接口请求失败。"
        suggestion="请重试或跳转到完整审计中心。"
        detail={getErrorMessage(jobAuditQuery.error ?? deniedQuery.error)}
        actions={[{ label: '打开完整审计中心', to: '/admin/audit' }]}
        onRetry={() => {
          void jobAuditQuery.refetch();
          void deniedQuery.refetch();
        }}
      />
    );
  }

  const jobAudits = jobAuditQuery.data?.items ?? [];
  const deniedLogs = deniedQuery.data?.items ?? [];

  return (
    <SectionCard
      title="权限与审计"
      description="查看最近的 Job 审计和拒绝访问记录。完整明细仍可进入审计中心。"
      action={
        <Link className="inline-flex items-center gap-2 text-sm font-medium text-slate-700 hover:text-slate-950" to="/admin/audit">
          打开完整审计中心
          <ArrowRight className="h-4 w-4" />
        </Link>
      }
    >
      <div className="grid gap-3 md:grid-cols-3">
        <StatCard label="Job 审计" value={jobAuditQuery.data?.summary.total ?? 0} hint="最近的结构化审计事件" />
        <StatCard label="拒绝访问" value={deniedQuery.data?.summary.total ?? 0} hint="权限不足或访问被拒绝的记录" />
        <StatCard
          label="高风险操作"
          value={jobAuditQuery.data?.summary.high_risk_count ?? 0}
          hint="需要重点关注的变更"
        />
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-900">最近 Job 审计</p>
          {jobAudits.length ? (
            <div className="space-y-3">
              {jobAudits.map((item) => (
                <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-slate-950">{item.job_type}</p>
                      <p className="text-xs text-slate-500">{item.actor} · {item.operation}</p>
                    </div>
                    <Badge variant={item.confirmed ? 'success' : 'warning'}>
                      {item.confirmed ? 'confirmed' : 'pending'}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs text-slate-500">{formatTime(item.event_at)}</p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无审计事件" description="当前筛选范围内没有 Job 审计记录。" />
          )}
        </div>

        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-900">最近拒绝访问</p>
          {deniedLogs.length ? (
            <div className="space-y-3">
              {deniedLogs.map((item) => (
                <div key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="font-medium text-slate-950">{item.actor}</p>
                  <p className="mt-2 text-sm text-slate-700">
                    {item.request_context.request.method ?? 'n/a'} {item.request_context.request.path ?? 'n/a'}
                  </p>
                  <p className="text-xs text-slate-500">{formatTime(item.event_at)}</p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无拒绝访问记录" description="当前筛选范围内没有权限拒绝事件。" />
          )}
        </div>
      </div>
    </SectionCard>
  );
}

function DatabaseMigrationSection() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const profilesQuery = useQuery({
    queryKey: ['system-profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 100 }),
    staleTime: 30_000,
  });
  const [profileId, setProfileId] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const profiles = profilesQuery.data?.items ?? [];

  useEffect(() => {
    if (!profiles.length) return;
    setProfileId((current) => current || profiles[0].profile_id);
  }, [profiles]);

  const mutation = useMutation({
    mutationFn: async () =>
      createJob({
        job_type: 'db-migrate',
        params: {
          profile_id: profileId,
        },
        created_by: 'web',
        confirmed: true,
      }),
    onSuccess: async (data) => {
      setStatusMessage('数据库迁移 Job 已创建');
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      if (data.job?.id) {
        navigate(`/jobs/${encodeURIComponent(data.job.id)}`);
      }
    },
    onError: (error: unknown) => {
      setErrorMessage(getErrorMessage(error));
    },
  });

  if (profilesQuery.isLoading) {
    return <LoadingState label="加载数据库迁移" description="正在读取可用的 Profile。" />;
  }

  if (profilesQuery.error) {
    return (
      <ErrorState
        category="permission denied"
        title="数据库迁移加载失败"
        description="Profile 列表接口请求失败。"
        suggestion="请重试，或先确认当前身份具备 admin 权限。"
        detail={getErrorMessage(profilesQuery.error)}
        onRetry={() => {
          void profilesQuery.refetch();
        }}
      />
    );
  }

  return (
    <SectionCard
      title="数据库迁移"
      description="提交高风险 Job 并跳转 Job Detail。"
    >
      {statusMessage ? (
        <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{statusMessage}</div>
      ) : null}
      {errorMessage ? (
        <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{errorMessage}</div>
      ) : null}
      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto]">
        <label className="space-y-2 text-sm text-slate-600">
          <span>Profile</span>
          <Select value={profileId} onChange={(event) => setProfileId(event.target.value)}>
            {profiles.map((profile: ProfileRecord) => (
              <option key={profile.profile_id} value={profile.profile_id}>
                {profile.name} ({profile.profile_id})
              </option>
            ))}
          </Select>
        </label>
        <div className="flex items-end">
          <Button onClick={() => setConfirmOpen(true)} disabled={mutation.isPending || !profileId}>
            {mutation.isPending ? '提交中' : '创建数据库迁移 Job'}
          </Button>
        </div>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="确认创建数据库迁移 Job"
        description="数据库迁移属于高风险操作，提交后会进入 Job Center。"
        confirmLabel="确认创建"
        onConfirm={async () => {
          await mutation.mutateAsync();
        }}
      >
        <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
          当前选择的 Profile：<span className="font-medium text-slate-950">{profileId || '未选择'}</span>
        </div>
      </ConfirmDialog>
    </SectionCard>
  );
}

function BackupManagementSection() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const profilesQuery = useQuery({
    queryKey: ['system-profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 100 }),
    staleTime: 30_000,
  });
  const backupTargetsQuery = useQuery({
    queryKey: ['system-backup-targets'],
    queryFn: () => listRecoveryBackupTargets(),
    staleTime: 30_000,
  });
  const backupsQuery = useQuery({
    queryKey: ['system-backups'],
    queryFn: () => listRecoveryBackups(),
    staleTime: 30_000,
  });
  const [backupForm, setBackupForm] = useState<BackupFormState>({
    profile_id: '',
    backup_dir_id: 'default',
    include_processed: true,
  });
  const [restoreForm, setRestoreForm] = useState<RestoreFormState>({
    profile_id: '',
    include_processed: true,
    force: false,
  });
  const [restoreTarget, setRestoreTarget] = useState<RecoveryBackupItem | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [backupConfirmOpen, setBackupConfirmOpen] = useState(false);

  const profiles = profilesQuery.data?.items ?? [];
  const backupTargets = backupTargetsQuery.data?.items ?? [];

  useEffect(() => {
    if (!profiles.length) return;
    setBackupForm((current) => ({
      ...current,
      profile_id: current.profile_id || profiles[0].profile_id,
    }));
    setRestoreForm((current) => ({
      ...current,
      profile_id: current.profile_id || profiles[0].profile_id,
    }));
  }, [profiles]);

  const createMutation = useMutation({
    mutationFn: async () => {
      const backupTarget = backupTargets.find((item) => item.id === backupForm.backup_dir_id) ?? backupTargets[0];
      if (!backupTarget) {
        throw new Error('没有可用的备份白名单目录');
      }
      const backupDir = backupTarget.id === 'default' ? undefined : backupTarget.path;
      return createJob({
        job_type: 'backup-data',
        params: {
          profile_id: backupForm.profile_id,
          base_dir: 'trade-strategy-ai',
          backup_dir_id: backupForm.backup_dir_id,
          backup_dir: backupDir,
          include_processed: backupForm.include_processed,
        },
        created_by: 'web',
        confirmed: true,
      });
    },
    onSuccess: async (data) => {
      setStatusMessage('备份 Job 已创建');
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      await queryClient.invalidateQueries({ queryKey: ['system-backups'] });
      if (data.job?.id) {
        navigate(`/jobs/${encodeURIComponent(data.job.id)}`);
      }
    },
    onError: (error: unknown) => {
      setErrorMessage(getErrorMessage(error));
    },
  });

  const restoreMutation = useMutation({
    mutationFn: async () => {
      if (!restoreTarget) {
        throw new Error('请选择要恢复的备份');
      }
      return createJob({
        job_type: 'restore-data',
        params: {
          profile_id: restoreForm.profile_id,
          base_dir: 'trade-strategy-ai',
          backup_id: restoreTarget.backup_id,
          backup_dir: restoreTarget.path,
          include_processed: restoreForm.include_processed,
          force: restoreForm.force,
        },
        created_by: 'web',
        confirmed: true,
      });
    },
    onSuccess: async (data) => {
      setStatusMessage('恢复 Job 已创建');
      setErrorMessage(null);
      setRestoreTarget(null);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      if (data.job?.id) {
        navigate(`/jobs/${encodeURIComponent(data.job.id)}`);
      }
    },
    onError: (error: unknown) => {
      setErrorMessage(getErrorMessage(error));
    },
  });

  if (profilesQuery.isLoading || backupTargetsQuery.isLoading || backupsQuery.isLoading) {
    return <LoadingState label="加载备份与恢复" description="正在读取 profile、备份目录和已有备份包。" />;
  }

  if (profilesQuery.error || backupTargetsQuery.error || backupsQuery.error) {
    return (
      <ErrorState
        category="permission denied"
        title="备份与恢复加载失败"
        description="备份列表或 profile 列表接口请求失败。"
        suggestion="请重试，或先确认当前账号具备 admin 权限。"
        detail={getErrorMessage(profilesQuery.error ?? backupTargetsQuery.error ?? backupsQuery.error)}
        onRetry={() => {
          void profilesQuery.refetch();
          void backupTargetsQuery.refetch();
          void backupsQuery.refetch();
        }}
      />
    );
  }

  return (
    <SectionCard
      title="数据备份与恢复"
      description="通过受限目录创建备份，并使用备份 ID 恢复。这里创建 Job 并跳转 Job Detail。"
      action={
        <Button
          variant="outline"
          onClick={() => {
            void profilesQuery.refetch();
            void backupTargetsQuery.refetch();
            void backupsQuery.refetch();
          }}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      }
    >
      {statusMessage ? (
        <div className="mb-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">{statusMessage}</div>
      ) : null}
      {errorMessage ? (
        <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{errorMessage}</div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <StatCard label="备份包" value={backupsQuery.data?.count ?? 0} hint="可用于恢复的备份目录" />
            <StatCard label="Profile" value={profiles.length} hint="可选的配置 Profile" />
            <StatCard label="白名单目录" value={backupTargets.length} hint="允许写入备份的目录" />
          </div>

          <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="font-medium text-slate-950">创建备份 Job</p>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-600 md:col-span-2">
                <span>Profile</span>
                <Select value={backupForm.profile_id} onChange={(event) => setBackupForm((current) => ({ ...current, profile_id: event.target.value }))}>
                  {profiles.map((profile: ProfileRecord) => (
                    <option key={profile.profile_id} value={profile.profile_id}>
                      {profile.name} ({profile.profile_id})
                    </option>
                  ))}
                </Select>
              </label>
              <label className="space-y-2 text-sm text-slate-600 md:col-span-2">
                <span>备份目录白名单</span>
                <Select
                  value={backupForm.backup_dir_id}
                  onChange={(event) => setBackupForm((current) => ({ ...current, backup_dir_id: event.target.value }))}
                >
                  {backupTargets.map((target: RecoveryBackupTarget) => (
                    <option key={target.id} value={target.id}>
                      {target.label} ({target.path})
                    </option>
                  ))}
                </Select>
                <p className="text-xs text-slate-500">不再接受任意绝对路径输入，只能从后端白名单中选择。</p>
              </label>
              <label className="flex items-center gap-3 text-sm text-slate-700 md:col-span-2">
                <input
                  checked={backupForm.include_processed}
                  onChange={(event) => setBackupForm((current) => ({ ...current, include_processed: event.target.checked }))}
                  type="checkbox"
                />
                include_processed
              </label>
            </div>
            <div className="flex flex-wrap gap-3">
              <Button
                onClick={() => setBackupConfirmOpen(true)}
                disabled={createMutation.isPending || !backupForm.profile_id || !backupTargets.length}
              >
                {createMutation.isPending ? '提交中' : '创建备份 Job'}
              </Button>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="rounded-2xl border border-slate-200 bg-white">
            <div className="border-b border-slate-200 px-4 py-3">
              <p className="font-medium text-slate-950">已有备份</p>
              <p className="text-xs text-slate-500">恢复 Job 使用 backup_id，不直接暴露路径输入。</p>
            </div>
            <div className="space-y-3 p-4">
              {backupsQuery.data?.items.length ? (
                backupsQuery.data.items.map((item) => (
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4" key={item.backup_id}>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-slate-950">{item.name}</p>
                        <p className="text-xs text-slate-500">{formatTime(item.modified_at)}</p>
                      </div>
                      <Badge variant="info">{backupStatusLabel(item)}</Badge>
                    </div>
                    <div className="mt-3 grid gap-2 text-sm text-slate-700">
                      <p>tables: {item.tables.join(', ') || 'n/a'}</p>
                      <p>rows: {Object.entries(item.row_counts).map(([key, value]) => `${key}=${value}`).join(', ') || 'n/a'}</p>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Button
                        onClick={() => {
                          setRestoreTarget(item);
                          setRestoreForm((current) => ({
                            ...current,
                            profile_id: current.profile_id || backupForm.profile_id || profiles[0]?.profile_id || '',
                            force: current.force,
                          }));
                        }}
                        variant="outline"
                      >
                        恢复
                      </Button>
                    </div>
                  </div>
                ))
              ) : (
                <EmptyState title="暂无备份" description="当前目录中还没有可恢复的备份包。" />
              )}
            </div>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={backupConfirmOpen}
        onOpenChange={setBackupConfirmOpen}
        title="确认创建备份 Job"
        description="备份属于高风险操作，提交后会进入 Job Center。"
        confirmLabel="确认创建"
        onConfirm={async () => {
          await createMutation.mutateAsync();
        }}
      >
        <div className="space-y-2 text-sm text-slate-700">
          <p>Profile：{backupForm.profile_id || '未选择'}</p>
          <p>include_processed：{backupForm.include_processed ? 'true' : 'false'}</p>
        </div>
      </ConfirmDialog>

      <ConfirmDialog
        open={Boolean(restoreTarget)}
        onOpenChange={(open) => {
          if (!open) {
            setRestoreTarget(null);
          }
        }}
        title="恢复备份 Job"
        description="恢复会覆盖当前项目状态，必须先确认。"
        confirmLabel="确认创建恢复 Job"
        onConfirm={async () => {
          await restoreMutation.mutateAsync();
        }}
      >
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Backup ID</p>
              <p className="mt-2 break-all text-sm font-medium text-slate-900">{restoreTarget?.backup_id}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Profile</p>
              <Select
                className="mt-2"
                value={restoreForm.profile_id}
                onChange={(event) => setRestoreForm((current) => ({ ...current, profile_id: event.target.value }))}
              >
                {profiles.map((profile: ProfileRecord) => (
                  <option key={profile.profile_id} value={profile.profile_id}>
                    {profile.name} ({profile.profile_id})
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input
              checked={restoreForm.include_processed}
              onChange={(event) => setRestoreForm((current) => ({ ...current, include_processed: event.target.checked }))}
              type="checkbox"
            />
            include_processed
          </label>
          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input
              checked={restoreForm.force}
              onChange={(event) => setRestoreForm((current) => ({ ...current, force: event.target.checked }))}
              type="checkbox"
            />
            force
          </label>
        </div>
      </ConfirmDialog>
    </SectionCard>
  );
}

export function SystemManagementWorkspace() {
  const { canAccess } = useAuth();
  const canManage = canAccess('admin');

  if (!canManage) {
    return (
      <ErrorState
        category="permission denied"
        title="没有权限访问系统管理"
        description="系统管理只对 admin 可见。"
        suggestion="请切换到管理员账号后重试，或返回管理中心。"
        actions={[{ label: '返回管理中心', to: '/admin' }]}
      />
    );
  }

  return (
    <div className="space-y-6">
      <OperationalDashboardCenter />
      <div className="grid gap-6 xl:grid-cols-2">
        <AuditSummarySection />
        <UserManagementSection />
      </div>
      <DatabaseMigrationSection />
      <BackupManagementSection />
    </div>
  );
}
