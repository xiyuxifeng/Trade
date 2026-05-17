import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/page-header';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { getSystemDashboard, getSystemStatus } from '@/lib/api/system';
import { createRecoveryBackup, listRecoveryBackups, recoverStaleJobs, restoreRecoveryBackup } from '@/lib/api/ops';
import { listJobs } from '@/lib/api/jobs';
import { listDataAudits } from '@/lib/api/data-audits';
import type { DataAuditItem, DataAuditsResponse } from '@/types/dataAudits';
import type { JobRecord } from '@/types/jobs';
import type { RecoveryBackupItem, RecoveryBackupsResponse } from '@/types/ops';
import type { SystemDashboardResponse, SystemStatusResponse } from '@/types/system';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '运维中心加载失败';
}

function formatBytes(bytes: number | null | undefined) {
  if (bytes == null) return '未知';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatNumber(value: number | null | undefined) {
  if (value == null) return 'n/a';
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function getStatusVariant(status: string | null | undefined) {
  const normalized = String(status ?? '').toLowerCase();
  if (normalized === 'ok' || normalized === 'healthy' || normalized === 'success') return 'success';
  if (normalized === 'warning' || normalized === 'partial') return 'warning';
  if (normalized === 'error' || normalized === 'failed' || normalized === 'critical') return 'destructive';
  return 'info';
}

function PanelCard({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Card className="border-slate-200 bg-white shadow-sm">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-slate-950">{title}</CardTitle>
            <CardDescription className="text-slate-600">{description}</CardDescription>
          </div>
          {action}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function SummaryTile({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-lg font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{detail}</p>
    </div>
  );
}

function StatusBadge({ value }: { value: string | null | undefined }) {
  return <Badge variant={getStatusVariant(value)}>{value ?? 'n/a'}</Badge>;
}

function BackupPackageCard({
  item,
  disabled,
  onRestore,
}: {
  item: RecoveryBackupItem;
  disabled: boolean;
  onRestore: () => void;
}) {
  const tableNames = item.tables.length ? item.tables.join(', ') : '无表信息';

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-slate-300">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-950">{item.name}</p>
          <p className="mt-1 break-all text-xs text-slate-500">{item.path}</p>
        </div>
        <Badge variant={item.processed_copied ? 'success' : 'warning'}>{formatBytes(item.size_bytes)}</Badge>
      </div>

      <div className="mt-3 grid gap-2 text-sm text-slate-700">
        <p>更新时间：{formatTimestamp(item.modified_at)}</p>
        <p>包含表：{tableNames}</p>
        <p>
          processed：{item.include_processed ? '包含' : '未包含'}，状态：{item.processed_copied ? '已复制' : '未复制'}
        </p>
        <p>artifacts：{item.artifacts_copied ? '已复制' : '未复制'}</p>
        <p>总行数：{Object.values(item.row_counts).reduce((sum, value) => sum + value, 0)}</p>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {item.tables.slice(0, 4).map((table) => (
          <Badge key={table} variant="info">
            {table}
          </Badge>
        ))}
      </div>

      <div className="mt-4 flex justify-end">
        <Button size="sm" variant="outline" onClick={onRestore} disabled={disabled}>
          恢复
        </Button>
      </div>
    </div>
  );
}

function AuditHistoryRow({ item }: { item: DataAuditItem }) {
  const payload = item.payload as Record<string, unknown>;
  const processedKey = payload.processed_restored ?? payload.processed_copied;
  const tableCount = Array.isArray(payload.tables) ? payload.tables.length : 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-950">{item.event_type}</p>
          <p className="mt-1 text-xs text-slate-500">{item.actor} · {item.source} · {formatTimestamp(item.event_at)}</p>
        </div>
        <Badge variant="info">{item.entity_id ?? 'n/a'}</Badge>
      </div>
      <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
        <p>实体：{item.entity_type}</p>
        <p>dataset：{item.dataset_version ?? 'n/a'}</p>
        <p>表数：{tableCount}</p>
        <p>processed：{processedKey === true ? '是' : processedKey === false ? '否' : 'n/a'}</p>
      </div>
    </div>
  );
}

function JobRow({ job, staleBeforeMinutes }: { job: JobRecord; staleBeforeMinutes: number }) {
  const heartbeatAt = job.heartbeat_at ? new Date(job.heartbeat_at) : null;
  const heartbeatAgeMinutes = heartbeatAt ? (Date.now() - heartbeatAt.getTime()) / 60000 : null;
  const stale = heartbeatAgeMinutes == null || heartbeatAgeMinutes >= staleBeforeMinutes;

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-950">{job.id}</p>
          <p className="mt-1 text-xs text-slate-500">{job.job_type} · {job.created_by}</p>
        </div>
        <Badge variant={stale ? 'warning' : 'success'}>{stale ? 'stale candidate' : 'fresh'}</Badge>
      </div>
      <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
        <p>状态：{job.status}</p>
        <p>心跳：{formatTimestamp(job.heartbeat_at)}</p>
        <p>重试：{job.retry_count}/{job.max_retries}</p>
        <p>调度：{formatTimestamp(job.scheduled_at)}</p>
      </div>
    </div>
  );
}

export function RecoveryCenter() {
  const queryClient = useQueryClient();
  const { canAccess } = useAuth();
  const canManageRecovery = canAccess('admin');

  if (!canManageRecovery) {
    return (
      <main className="page-stack">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <p className="text-lg font-semibold text-slate-950">没有权限访问运维中心</p>
            <p className="mt-2 text-sm text-slate-600">当前身份需要 admin 权限。</p>
          </CardContent>
        </Card>
      </main>
    );
  }

  const [includeProcessed, setIncludeProcessed] = useState(true);
  const [backupConfirmOpen, setBackupConfirmOpen] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState<RecoveryBackupItem | null>(null);
  const [restoreToken, setRestoreToken] = useState('');
  const [staleConfirmOpen, setStaleConfirmOpen] = useState(false);
  const [staleToken, setStaleToken] = useState('');
  const [staleBeforeMinutes, setStaleBeforeMinutes] = useState(10);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const systemStatusQuery = useQuery<SystemStatusResponse, ApiError>({
    queryKey: ['ops-system-status'],
    queryFn: () => getSystemStatus(),
    staleTime: 10_000,
  });

  const dashboardQuery = useQuery<SystemDashboardResponse, ApiError>({
    queryKey: ['ops-system-dashboard'],
    queryFn: () => getSystemDashboard(),
    staleTime: 10_000,
  });

  const jobsQuery = useQuery({
    queryKey: ['ops-running-jobs'],
    queryFn: () => listJobs({ status: 'running', limit: 20 }),
    staleTime: 10_000,
  });

  const backupsQuery = useQuery<RecoveryBackupsResponse, ApiError>({
    queryKey: ['ops-recovery-backups'],
    queryFn: () => listRecoveryBackups(),
    staleTime: 10_000,
  });

  const auditsQuery = useQuery<DataAuditsResponse, ApiError>({
    queryKey: ['ops-data-audits'],
    queryFn: () => listDataAudits({ entity_type: 'backup', limit: 10 }),
    staleTime: 10_000,
  });

  const latestBackup = useMemo(() => backupsQuery.data?.items[0] ?? null, [backupsQuery.data?.items]);
  const backupCount = backupsQuery.data?.count ?? 0;
  const runningJobs = jobsQuery.data?.items ?? [];
  const staleCandidates = useMemo(() => {
    const now = Date.now();
    return runningJobs.filter((job) => {
      if (!job.heartbeat_at) return true;
      return (now - new Date(job.heartbeat_at).getTime()) / 60000 >= staleBeforeMinutes;
    });
  }, [runningJobs, staleBeforeMinutes]);
  const recentFailures = dashboardQuery.data?.failed_jobs ?? [];
  const healthEntries = Object.entries(dashboardQuery.data?.health ?? {})
    .filter(([key, value]) => key !== 'overall' && key !== 'issues' && value && typeof value === 'object')
    .map(([key, value]) => ({ key, value: value as { status?: string; latency_ms?: number | null; error?: string | null } }));

  const createMutation = useMutation({
    mutationFn: async () => createRecoveryBackup({ include_processed: includeProcessed }),
    onSuccess: async (data) => {
      setStatusMessage(`已创建项目备份：${data.backup_dir}`);
      setBackupConfirmOpen(false);
      await queryClient.invalidateQueries({ queryKey: ['ops-recovery-backups'] });
      await queryClient.invalidateQueries({ queryKey: ['ops-data-audits'] });
    },
    onError: (error) => setStatusMessage(getErrorMessage(error)),
  });

  const restoreMutation = useMutation({
    mutationFn: async () => {
      if (!restoreTarget) throw new Error('未选择备份包');
      return restoreRecoveryBackup({
        backup_path: restoreTarget.path,
        include_processed: true,
        confirmed: true,
      });
    },
    onSuccess: async (data) => {
      setStatusMessage(`已恢复备份：${data.backup_dir}`);
      setRestoreTarget(null);
      setRestoreToken('');
      await queryClient.invalidateQueries({ queryKey: ['ops-recovery-backups'] });
      await queryClient.invalidateQueries({ queryKey: ['ops-data-audits'] });
      await queryClient.invalidateQueries({ queryKey: ['ops-system-dashboard'] });
    },
    onError: (error) => setStatusMessage(getErrorMessage(error)),
  });

  const staleMutation = useMutation({
    mutationFn: async () => recoverStaleJobs({ stale_before_minutes: staleBeforeMinutes }),
    onSuccess: async (data) => {
      setStatusMessage(`已回收 stale jobs：${data.count} 个`);
      setStaleConfirmOpen(false);
      setStaleToken('');
      await queryClient.invalidateQueries({ queryKey: ['ops-running-jobs'] });
      await queryClient.invalidateQueries({ queryKey: ['ops-system-dashboard'] });
    },
    onError: (error) => setStatusMessage(getErrorMessage(error)),
  });

  const restoreReady = restoreToken.trim() === 'RESTORE';
  const staleReady = staleToken.trim() === 'RECOVER';

  return (
    <main className="page-stack">
      <PageHeader
        kicker="管理与运维"
        title="Admin Ops Console"
        description="管理员只读观测与受控恢复入口，统一承载系统概览、stale job 回收、备份和恢复。"
      />

      {statusMessage ? (
        <Card className="border-emerald-200 bg-emerald-50 shadow-sm">
          <CardContent className="p-4 text-sm text-emerald-900">{statusMessage}</CardContent>
        </Card>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryTile label="备份包" value={`${backupCount}`} detail="当前可恢复的项目快照数量" />
        <SummaryTile
          label="最新快照"
          value={latestBackup?.name ?? '无'}
          detail={latestBackup ? formatTimestamp(latestBackup.modified_at) : '尚未生成项目快照'}
        />
        <SummaryTile
          label="运行中 Job"
          value={`${runningJobs.length}`}
          detail={`${staleCandidates.length} 个需要回收确认`}
        />
        <SummaryTile
          label="最近失败"
          value={`${recentFailures.length}`}
          detail="需要优先定位的关键失败任务"
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <PanelCard
          title="系统概览"
          description="只读显示 API、数据库、工作线程、目录和健康摘要。"
          action={
            <Button variant="outline" onClick={() => {
              void systemStatusQuery.refetch();
              void dashboardQuery.refetch();
            }} disabled={systemStatusQuery.isFetching || dashboardQuery.isFetching}>
              {systemStatusQuery.isFetching || dashboardQuery.isFetching ? '刷新中' : '刷新'}
            </Button>
          }
        >
          {systemStatusQuery.isLoading || dashboardQuery.isLoading ? (
            <Skeleton className="h-64 rounded-2xl bg-slate-100" />
          ) : systemStatusQuery.isError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{getErrorMessage(systemStatusQuery.error)}</div>
          ) : systemStatusQuery.data ? (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">基础状态</p>
                <div className="grid gap-3 text-sm text-slate-700">
                  <p>配置：{systemStatusQuery.data.config_path}</p>
                  <p>运行模式：{systemStatusQuery.data.run_mode}</p>
                  <p>项目根目录：{systemStatusQuery.data.project_root}</p>
                  <div className="flex items-center gap-2">
                    <span>数据库：</span>
                    <StatusBadge value={systemStatusQuery.data.database.status} />
                    <span className="text-xs text-slate-500">latency {formatNumber(systemStatusQuery.data.database.latency_ms)} ms</span>
                  </div>
                </div>
              </div>

              <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">关键目录</p>
                <div className="space-y-2 text-sm text-slate-700">
                  {Object.entries(systemStatusQuery.data.directories).map(([key, item]) => (
                    <div key={key} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2">
                      <div>
                        <p className="font-medium text-slate-950">{key}</p>
                        <p className="text-xs text-slate-500">{item.path}</p>
                      </div>
                      <Badge variant={item.exists ? 'success' : 'destructive'}>{item.exists ? 'exists' : 'missing'}</Badge>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:col-span-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">健康组件</p>
                {dashboardQuery.isError ? (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                    {getErrorMessage(dashboardQuery.error)}
                  </div>
                ) : null}
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="text-sm font-medium text-slate-950">整体状态</p>
                    <p className="mt-2 text-sm text-slate-600">{dashboardQuery.data?.health.overall ?? 'n/a'}</p>
                  </div>
                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="text-sm font-medium text-slate-950">问题数量</p>
                    <p className="mt-2 text-sm text-slate-600">{dashboardQuery.data?.health.issues?.length ?? 0}</p>
                  </div>
                  {healthEntries.map((entry) => (
                    <div key={entry.key} className="rounded-xl border border-slate-200 bg-white p-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium text-slate-950">{entry.key}</p>
                        <Badge variant={getStatusVariant(entry.value.status)}>{entry.value.status ?? 'n/a'}</Badge>
                      </div>
                      <p className="mt-2 text-xs text-slate-500">
                        latency {formatNumber(entry.value.latency_ms)} ms
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              暂无系统状态数据。
            </div>
          )}
        </PanelCard>

        <PanelCard title="Stale Job Recovery" description="按心跳超时阈值识别并回收运行中 Job。">
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-slate-950">当前阈值</p>
                <Badge variant="info">{staleBeforeMinutes} min</Badge>
              </div>
              <p className="mt-2 text-sm text-slate-600">基于 Job 心跳时间筛选 stale candidates，再通过受控确认执行回收。</p>
              <div className="mt-3 flex gap-3">
                <Input
                  className="max-w-32"
                  min={1}
                  max={1440}
                  onChange={(event) => setStaleBeforeMinutes(Number(event.target.value) || 10)}
                  type="number"
                  value={staleBeforeMinutes}
                />
                <Button disabled={!canManageRecovery || staleMutation.isPending} onClick={() => setStaleConfirmOpen(true)}>
                  回收 stale jobs
                </Button>
              </div>
              {!canManageRecovery ? <p className="mt-2 text-xs text-slate-500">仅 admin 可执行回收。</p> : null}
            </div>

            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-900">stale candidates</p>
              {jobsQuery.isLoading ? (
                <Skeleton className="h-36 rounded-2xl bg-slate-100" />
              ) : jobsQuery.isError ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{getErrorMessage(jobsQuery.error)}</div>
              ) : staleCandidates.length ? (
                staleCandidates.map((job) => <JobRow job={job} key={job.id} staleBeforeMinutes={staleBeforeMinutes} />)
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                  暂无 stale candidates。
                </div>
              )}
            </div>
          </div>
        </PanelCard>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <PanelCard
          title="备份 / 恢复"
          description="项目快照只通过确认后的 Job 流程执行，不直接拼接路径。"
          action={
            <Button disabled={!canManageRecovery || createMutation.isPending} onClick={() => setBackupConfirmOpen(true)}>
              开始备份
            </Button>
          }
        >
          <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="space-y-4">
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  checked={includeProcessed}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  disabled={!canManageRecovery || createMutation.isPending}
                  onChange={(event) => setIncludeProcessed(event.target.checked)}
                  type="checkbox"
                />
                <span>
                  <span className="block font-medium text-slate-950">包含处理后的数据</span>
                  <span className="block text-xs text-slate-500">同时备份 `data/processed`，便于完整回滚。</span>
                </span>
              </label>

              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                备份和恢复都会写入审计历史，恢复前需要显式确认。
              </div>

              <div className="space-y-2 text-sm text-slate-700">
                <p>备份根目录：{backupsQuery.data?.backup_root ?? 'data/backups'}</p>
                <p>最后一次备份：{latestBackup ? formatTimestamp(latestBackup.modified_at) : '暂无'}</p>
              </div>
            </div>

            <div className="space-y-3">
              {backupsQuery.isLoading ? (
                <Skeleton className="h-72 rounded-2xl bg-slate-100" />
              ) : backupsQuery.isError ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{getErrorMessage(backupsQuery.error)}</div>
              ) : backupsQuery.data?.items.length ? (
                <div className="space-y-3">
                  {backupsQuery.data.items.map((item) => (
                    <BackupPackageCard
                      item={item}
                      key={item.path}
                      disabled={!canManageRecovery || restoreMutation.isPending}
                      onRestore={() => {
                        setRestoreTarget(item);
                        setRestoreToken('');
                      }}
                    />
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                  暂无备份包。
                </div>
              )}
            </div>
          </div>
        </PanelCard>

        <PanelCard title="审计历史" description="查看 backup / restore / recovery 相关的可追溯记录。">
          <div className="space-y-3">
            {auditsQuery.isLoading ? (
              <Skeleton className="h-64 rounded-2xl bg-slate-100" />
            ) : auditsQuery.isError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{getErrorMessage(auditsQuery.error)}</div>
            ) : auditsQuery.data?.items.length ? (
              auditsQuery.data.items.map((item) => <AuditHistoryRow item={item} key={item.id} />)
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                暂无审计历史。
              </div>
            )}
          </div>
        </PanelCard>
      </section>

      <Dialog open={backupConfirmOpen} onOpenChange={setBackupConfirmOpen}>
        <DialogContent className="border-slate-200 bg-white text-slate-950">
          <DialogHeader>
            <DialogTitle>Confirm backup</DialogTitle>
            <DialogDescription>创建备份会写入项目级快照和审计历史。</DialogDescription>
          </DialogHeader>
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            该操作会将当前数据库、Job 元数据和部分目录内容收口到项目备份中。
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBackupConfirmOpen(false)} disabled={createMutation.isPending}>
              取消
            </Button>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending || !canManageRecovery}
            >
              {createMutation.isPending ? '备份中' : 'Confirm backup'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={Boolean(restoreTarget)}
        onOpenChange={(open) => {
          if (!open) {
            setRestoreTarget(null);
            setRestoreToken('');
          }
        }}
      >
        <DialogContent className="border-slate-200 bg-white text-slate-950">
          <DialogHeader>
            <DialogTitle>Confirm restore</DialogTitle>
            <DialogDescription>恢复会覆盖当前数据库和相关目录，请先确认目标快照。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">backup path</p>
              <p className="mt-2 break-all font-medium text-slate-950">{restoreTarget?.path}</p>
            </div>
            <label className="block text-sm text-slate-700">
              <span className="mb-2 block font-medium text-slate-950">Restore confirmation</span>
              <Input
                aria-label="Restore confirmation"
                autoComplete="off"
                className="bg-white"
                onChange={(event) => setRestoreToken(event.target.value)}
                placeholder="输入 RESTORE"
                value={restoreToken}
              />
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreTarget(null)} disabled={restoreMutation.isPending}>
              取消
            </Button>
            <Button
              onClick={() => restoreMutation.mutate()}
              disabled={restoreMutation.isPending || !canManageRecovery || !restoreReady}
            >
              {restoreMutation.isPending ? '恢复中' : 'Confirm restore'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={staleConfirmOpen}
        onOpenChange={(open) => {
          setStaleConfirmOpen(open);
          if (!open) {
            setStaleToken('');
          }
        }}
      >
        <DialogContent className="border-slate-200 bg-white text-slate-950">
          <DialogHeader>
            <DialogTitle>Confirm stale recovery</DialogTitle>
            <DialogDescription>确认后会将超过阈值的 running Job 标记为 failed，并记录审计。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              当前候选数量：{staleCandidates.length}
            </div>
            <label className="block text-sm text-slate-700">
              <span className="mb-2 block font-medium text-slate-950">Recovery confirmation</span>
              <Input
                aria-label="Recovery confirmation"
                autoComplete="off"
                className="bg-white"
                onChange={(event) => setStaleToken(event.target.value)}
                placeholder="输入 RECOVER"
                value={staleToken}
              />
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStaleConfirmOpen(false)} disabled={staleMutation.isPending}>
              取消
            </Button>
            <Button
              onClick={() => staleMutation.mutate()}
              disabled={staleMutation.isPending || !canManageRecovery || !staleReady}
            >
              {staleMutation.isPending ? '回收中' : 'Confirm recovery'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
