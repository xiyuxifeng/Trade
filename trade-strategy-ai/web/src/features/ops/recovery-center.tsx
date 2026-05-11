import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { createRecoveryBackup, listRecoveryBackups, restoreRecoveryBackup } from '@/lib/api/ops';
import type { RecoveryBackupItem, RecoveryBackupsResponse } from '@/types/ops';
import { PageHeader } from '@/components/layout/page-header';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '恢复中心加载失败';
}

function formatBytes(bytes: number | null | undefined) {
  if (bytes == null) return '未知';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTimestamp(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
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
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 transition-colors hover:border-slate-700">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-100">{item.name}</p>
          <p className="mt-1 break-all text-xs text-slate-500">{item.path}</p>
        </div>
        <Badge variant={item.processed_copied ? 'success' : 'warning'}>{formatBytes(item.size_bytes)}</Badge>
      </div>

      <div className="mt-3 grid gap-2 text-sm text-slate-300">
        <p>更新时间：{formatTimestamp(item.modified_at)}</p>
        <p>包含表：{tableNames}</p>
        <p>
          processed：{item.include_processed ? '包含' : '未包含'}，状态：{item.processed_copied ? '已复制' : '未复制'}
        </p>
        <p>artifacts：{item.artifacts_copied ? '已复制' : '未复制'}</p>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {item.tables.slice(0, 4).map((table) => (
          <Badge key={table} variant="info">
            {table}
          </Badge>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-xs text-slate-500">行数: {Object.values(item.row_counts).reduce((sum, value) => sum + value, 0)}</p>
        <Button variant="destructive" size="sm" onClick={onRestore} disabled={disabled}>
          恢复 (Restore)
        </Button>
      </div>
    </div>
  );
}

function SummaryTile({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <Card className="border-slate-800 bg-slate-950/70">
      <CardContent className="p-4">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
        <p className="mt-2 text-2xl font-semibold text-slate-100">{value}</p>
        <p className="mt-1 text-sm text-slate-400">{detail}</p>
      </CardContent>
    </Card>
  );
}

export function RecoveryCenter() {
  const queryClient = useQueryClient();
  const { canAccess } = useAuth();
  const canManageRecovery = canAccess('admin');
  const [includeProcessed, setIncludeProcessed] = useState(true);
  const [backupConfirmOpen, setBackupConfirmOpen] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState<RecoveryBackupItem | null>(null);
  const [restoreToken, setRestoreToken] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const backupsQuery = useQuery<RecoveryBackupsResponse, ApiError>({
    queryKey: ['ops-recovery-backups'],
    queryFn: () => listRecoveryBackups(),
    staleTime: 10_000,
  });

  const latestBackup = useMemo(() => backupsQuery.data?.items[0] ?? null, [backupsQuery.data?.items]);
  const backupCount = backupsQuery.data?.count ?? 0;

  const createMutation = useMutation({
    mutationFn: async () => createRecoveryBackup({ include_processed: includeProcessed }),
    onSuccess: async (data) => {
      setStatusMessage(`已创建项目备份：${data.backup_dir}`);
      setBackupConfirmOpen(false);
      await queryClient.invalidateQueries({ queryKey: ['ops-recovery-backups'] });
    },
    onError: (error) => {
      setStatusMessage(getErrorMessage(error));
    },
  });

  const restoreMutation = useMutation({
    mutationFn: async () => {
      if (!restoreTarget) {
        throw new Error('未选择备份包');
      }
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
    },
    onError: (error) => {
      setStatusMessage(getErrorMessage(error));
    },
  });

  const restoreReady = restoreToken.trim() === 'RESTORE';

  return (
    <main className="page-stack">
      <PageHeader
        kicker="运维"
        title="恢复中心 (Recovery Center)"
        description="项目级备份、恢复和回滚演练入口。"
      />

      {statusMessage ? (
        <Card className="border-emerald-500/30 bg-emerald-500/10">
          <CardContent className="p-4 text-sm text-emerald-100">{statusMessage}</CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <SummaryTile label="备份包" value={`${backupCount}`} detail="当前可恢复的项目快照数量" />
        <SummaryTile
          label="最新快照"
          value={latestBackup?.name ?? '无'}
          detail={latestBackup ? formatTimestamp(latestBackup.modified_at) : '尚未生成项目快照'}
        />
        <SummaryTile
          label="备份根目录"
          value={backupsQuery.data?.backup_root ?? 'data/backups'}
          detail="所有项目级备份都会落在该目录下"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_1.4fr]">
        <Card className="border-slate-800 bg-slate-950/70">
          <CardHeader>
            <CardTitle>项目备份</CardTitle>
            <CardDescription>创建数据库、Job 元数据和 processed 目录的项目级快照。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <label className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm text-slate-200">
              <input
                checked={includeProcessed}
                className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-sky-400 focus:ring-sky-400"
                disabled={!canManageRecovery || createMutation.isPending}
                onChange={(event) => setIncludeProcessed(event.target.checked)}
                type="checkbox"
              />
              <span>
                <span className="block font-medium text-slate-100">包含处理后的数据 (Include processed data)</span>
                <span className="block text-xs text-slate-400">同时备份 `data/processed` 目录，便于完整回滚。</span>
              </span>
            </label>

            <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
              备份操作会记录审计事件，并为恢复提供可追踪的清单 (manifest)。
            </div>

            <div className="flex flex-wrap gap-3">
              <Button disabled={!canManageRecovery || createMutation.isPending} onClick={() => setBackupConfirmOpen(true)}>
                开始项目备份
              </Button>
              <Button
                variant="outline"
                disabled={backupsQuery.isFetching}
                onClick={() => backupsQuery.refetch()}
              >
                {backupsQuery.isFetching ? '刷新中' : '刷新列表'}
              </Button>
            </div>

            {!canManageRecovery ? (
              <p className="text-sm text-slate-500">仅 admin 可执行项目级备份与恢复。</p>
            ) : null}
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/70">
          <CardHeader>
            <CardTitle>回滚演练</CardTitle>
            <CardDescription>发布失败时按这个顺序恢复：先找回最近快照，再复核健康检查。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
              <p className="font-medium text-slate-100">1. 先创建一份新备份</p>
              <p className="mt-1 text-slate-400">确保当前状态已进入 data/backups，避免回滚时找不到基线。</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
              <p className="font-medium text-slate-100">2. 在测试环境恢复</p>
              <p className="mt-1 text-slate-400">恢复前必须显式确认，恢复后检查仪表盘 (Dashboard) 与任务 (Jobs) 状态。</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
              <p className="font-medium text-slate-100">3. 生产发布失败时回滚</p>
              <p className="mt-1 text-slate-400">立即恢复上一份快照，并重新执行健康检查与关键流程验收。</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-slate-800 bg-slate-950/70">
        <CardHeader>
          <CardTitle>备份包列表</CardTitle>
          <CardDescription>选择任意项目快照执行恢复，恢复操作仅对 admin 开放。</CardDescription>
        </CardHeader>
        <CardContent>
          {backupsQuery.isLoading ? (
            <div className="grid gap-4 md:grid-cols-2">
              <Skeleton className="h-40 rounded-2xl bg-slate-900" />
              <Skeleton className="h-40 rounded-2xl bg-slate-900" />
            </div>
          ) : backupsQuery.error ? (
            <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
              {getErrorMessage(backupsQuery.error)}
            </div>
          ) : !backupsQuery.data?.items.length ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 text-sm text-slate-400">
              暂无项目快照，先创建一个备份再进行恢复演练。
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {backupsQuery.data.items.map((item) => (
                <BackupPackageCard
                  key={item.path}
                  disabled={!canManageRecovery}
                  item={item}
                  onRestore={() => {
                    setRestoreTarget(item);
                    setRestoreToken('');
                  }}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={backupConfirmOpen} onOpenChange={setBackupConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm backup</DialogTitle>
            <DialogDescription>创建备份会把当前项目状态写入 data/backups。恢复前可先执行一次。</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBackupConfirmOpen(false)} disabled={createMutation.isPending}>
              Cancel
            </Button>
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !canManageRecovery}>
              {createMutation.isPending ? 'Creating' : 'Confirm backup'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={Boolean(restoreTarget)} onOpenChange={(open) => !open && setRestoreTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认项目恢复</DialogTitle>
            <DialogDescription>恢复会覆盖数据库和 processed 目录。请输入 RESTORE 继续。</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
              <p className="font-medium">危险操作</p>
              <p className="mt-1 break-all text-xs text-rose-100/80">{restoreTarget?.path}</p>
            </div>
            <label className="block text-sm text-slate-300">
              <span className="mb-2 block">恢复确认 (Restore confirmation)</span>
              <Input
                autoComplete="off"
                disabled={restoreMutation.isPending || !canManageRecovery}
                onChange={(event) => setRestoreToken(event.target.value)}
                placeholder="键入 RESTORE"
                value={restoreToken}
              />
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRestoreTarget(null)} disabled={restoreMutation.isPending}>
              取消
            </Button>
            <Button
              variant="destructive"
              disabled={restoreMutation.isPending || !canManageRecovery || !restoreReady}
              onClick={() => restoreMutation.mutate()}
            >
              {restoreMutation.isPending ? '正在恢复' : '确认恢复'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
