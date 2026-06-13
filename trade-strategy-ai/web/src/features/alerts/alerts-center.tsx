import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight, RefreshCw, Send } from 'lucide-react';
import { PageHeader } from '@/components/layout/page-header';
import { ErrorState } from '@/components/state/ErrorState';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import {
  acknowledgeAlert,
  getAlertingStatus,
  listAlertHistory,
  resolveAlert,
  sendTestAlert,
} from '@/lib/api/alerts';
import type { AlertHistoryItem, AlertingStatusResponse } from '@/types/alerts';

const PAGE_SIZE = 20;

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return '未记录';
  }
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function levelVariant(level: string) {
  if (level === 'CRITICAL') return 'destructive';
  if (level === 'WARNING') return 'warning';
  return 'info';
}

function statusVariant(status: string) {
  if (status === 'pending' || status === 'sent') return 'warning';
  if (status === 'acknowledged') return 'info';
  if (status === 'resolved') return 'success';
  return 'default';
}

function statusLabel(status: string) {
  if (status === 'pending') return '待发送';
  if (status === 'sent') return '已发送';
  if (status === 'acknowledged') return '已确认';
  if (status === 'resolved') return '已解决';
  return status;
}

function alertingStatusLabel(status: AlertingStatusResponse | undefined) {
  if (!status) return '加载中';
  if (!status.enabled) return '未启用';
  if (status.webhook_configured) return '已就绪';
  if (status.console_output) return '仅本地输出';
  return '未配置';
}

function AlertDetailDialog({
  alert,
  open,
  onOpenChange,
}: {
  alert: AlertHistoryItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const metadataText = alert ? JSON.stringify(alert.alert_metadata ?? {}, null, 2) : '';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>告警详情</DialogTitle>
          <DialogDescription>查看告警上下文、时间线和原始元数据。</DialogDescription>
        </DialogHeader>
        {alert ? (
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">标题</p>
                <p className="mt-2 text-sm font-medium text-slate-900">{alert.title}</p>
                <p className="mt-2 text-xs text-slate-500">记录 ID: {alert.alert_id}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">状态与级别</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Badge variant={levelVariant(alert.level)}>{alert.level}</Badge>
                  <Badge variant={statusVariant(alert.status)}>{statusLabel(alert.status)}</Badge>
                </div>
                <p className="mt-2 text-xs text-slate-500">通道: {alert.channel}</p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">时间线</p>
                <div className="mt-3 space-y-2 text-sm text-slate-700">
                  <p>创建: {formatTimestamp(alert.created_at)}</p>
                  <p>发送: {formatTimestamp(alert.sent_at)}</p>
                  <p>确认: {formatTimestamp(alert.acknowledged_at)}</p>
                  <p>解决: {formatTimestamp(alert.resolved_at)}</p>
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">聚合信息</p>
                <div className="mt-3 space-y-2 text-sm text-slate-700">
                  <p>聚合次数: {alert.aggregated_count}</p>
                  <p>聚合键: {alert.aggregation_key ?? '无'}</p>
                  <p>标签: {alert.tags.length ? alert.tags.join(' / ') : '无'}</p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">消息</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">
                {alert.message ?? '暂无详细消息。'}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">元数据</p>
              <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words text-xs leading-6 text-slate-700">
                {metadataText}
              </pre>
            </div>
          </div>
        ) : null}
        <DialogFooter>
          <DialogClose className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
            关闭
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AlertsLoadingState() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-36 w-full rounded-3xl" />
      <Skeleton className="h-12 w-full rounded-2xl" />
      <Skeleton className="h-72 w-full rounded-3xl" />
    </div>
  );
}

export function AlertsCenter() {
  const { canAccess, principal } = useAuth();
  const canManageAlerts = canAccess('operator');
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [detailAlert, setDetailAlert] = useState<AlertHistoryItem | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);

  const statusFilter = searchParams.get('status') ?? '';
  const levelFilter = searchParams.get('level') ?? '';
  const tagFilter = searchParams.get('tag') ?? '';
  const pageParam = Number.parseInt(searchParams.get('page') ?? '1', 10);
  const page = Number.isFinite(pageParam) && pageParam > 0 ? pageParam - 1 : 0;

  const statusQuery = useQuery({
    queryKey: ['alerts', 'status'],
    queryFn: getAlertingStatus,
    staleTime: 15_000,
  });

  const historyQuery = useQuery({
    queryKey: ['alerts', 'history', statusFilter, levelFilter, tagFilter, page],
    queryFn: () =>
      listAlertHistory({
        status: statusFilter || undefined,
        level: levelFilter || undefined,
        tag: tagFilter || undefined,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    staleTime: 15_000,
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (recordId: string) => acknowledgeAlert(recordId, principal.username || principal.api_key_label || 'web'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts', 'history'] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (recordId: string) => resolveAlert(recordId, principal.username || principal.api_key_label || 'web'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts', 'history'] });
    },
  });

  const testMutation = useMutation({
    mutationFn: sendTestAlert,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts', 'history'] });
    },
  });

  const history = historyQuery.data?.items ?? [];
  const total = historyQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.min(page + 1, totalPages);
  const alertingStatus = statusQuery.data;

  const summary = useMemo(() => {
    return history.reduce(
      (acc, item) => {
        acc.total += 1;
        if (item.status === 'pending' || item.status === 'sent') acc.pending += 1;
        if (item.status === 'acknowledged') acc.acknowledged += 1;
        if (item.status === 'resolved') acc.resolved += 1;
        if (item.level === 'CRITICAL') acc.critical += 1;
        if (item.level === 'WARNING') acc.warning += 1;
        return acc;
      },
      { total: 0, pending: 0, acknowledged: 0, resolved: 0, critical: 0, warning: 0 },
    );
  }, [history]);

  const error = statusQuery.error ?? historyQuery.error;

  function updateSearchParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    next.set('page', '1');
    setSearchParams(next, { replace: true });
  }

  function changePage(nextPage: number) {
    const next = new URLSearchParams(searchParams);
    next.set('page', String(nextPage));
    setSearchParams(next, { replace: true });
  }

  function openDetail(alert: AlertHistoryItem) {
    setDetailAlert(alert);
    setDetailOpen(true);
  }

  if (historyQuery.isLoading || statusQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="正式入口"
          title="告警中心"
          description="集中查看、确认和解决系统告警。"
        />
        <AlertsLoadingState />
      </main>
    );
  }

  if (error) {
    const message = error instanceof ApiError ? error.message : '告警中心加载失败';
    return (
      <main className="page-stack">
        <PageHeader
          kicker="正式入口"
          title="告警中心"
          description="集中查看、确认和解决系统告警。"
        />
        <ErrorState
          category="network error"
          title="告警中心加载失败"
          description="当前告警历史或告警状态接口请求失败。"
          suggestion="重试后查看系统管理页，确认告警服务和数据库是否正常。"
          detail={message}
          retryLabel={historyQuery.isFetching || statusQuery.isFetching ? '重试中' : '重试'}
          onRetry={() => {
            void Promise.all([statusQuery.refetch(), historyQuery.refetch()]);
          }}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="正式入口"
        title="告警中心"
        description="统一查看系统告警、确认处理结果，并发送测试告警验证配置。"
      />

      <section className="grid gap-4 xl:grid-cols-4">
        <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
          <CardHeader>
            <CardDescription>启用状态</CardDescription>
            <CardTitle className="text-slate-900">{alertingStatusLabel(alertingStatus)}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600">
            <Badge variant={alertingStatus?.enabled ? 'success' : 'warning'}>
              {alertingStatus?.enabled ? 'alerting.enabled=true' : 'alerting.enabled=false'}
            </Badge>
            <p>当前通道: {alertingStatus?.channel ?? '未配置'}</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
          <CardHeader>
            <CardDescription>告警通道</CardDescription>
            <CardTitle className="text-slate-900">{alertingStatus?.channel ?? '未配置'}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600">
            <p>Webhook: {alertingStatus?.webhook_configured ? '已配置' : '未配置'}</p>
            <p>控制台输出: {alertingStatus?.console_output ? '开启' : '关闭'}</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
          <CardHeader>
            <CardDescription>当前页摘要</CardDescription>
            <CardTitle className="text-slate-900">{summary.total} 条</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600">
            <p>待处理: {summary.pending}</p>
            <p>已确认: {summary.acknowledged}</p>
          </CardContent>
        </Card>
        <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
          <CardHeader>
            <CardDescription>高优先级</CardDescription>
            <CardTitle className="text-slate-900">{summary.critical + summary.warning}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600">
            <p>CRITICAL: {summary.critical}</p>
            <p>WARNING: {summary.warning}</p>
          </CardContent>
        </Card>
      </section>

      {!alertingStatus?.enabled ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="pt-6 text-sm leading-6 text-amber-900">
            当前告警功能未启用。请在交付配置中设置 <code>alerting.enabled=true</code> 后再使用测试告警和外部通知。
          </CardContent>
        </Card>
      ) : !alertingStatus.webhook_configured ? (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="pt-6 text-sm leading-6 text-amber-900">
            当前告警已启用，但还没有配置可用的 Webhook 通道。历史告警仍可查看，但测试告警和外部推送不会真正发送出去。
          </CardContent>
        </Card>
      ) : null}

      <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <CardTitle className="text-slate-900">过滤与操作</CardTitle>
            <CardDescription>通过状态、级别和标签筛选告警历史，必要时发送测试告警验证配置。</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={() => {
                void Promise.all([statusQuery.refetch(), historyQuery.refetch()]);
              }}
            >
              <RefreshCw className="h-4 w-4" />
              刷新
            </Button>
            <Button
              disabled={!canManageAlerts || !alertingStatus?.enabled || !alertingStatus.webhook_configured || testMutation.isPending}
              onClick={() => {
                void testMutation.mutateAsync();
              }}
            >
              <Send className="h-4 w-4" />
              {testMutation.isPending ? '发送中' : '发送测试告警'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-slate-700">状态</label>
            <Select value={statusFilter} onChange={(event) => updateSearchParam('status', event.target.value)}>
              <option value="">全部</option>
              <option value="pending">待发送</option>
              <option value="sent">已发送</option>
              <option value="acknowledged">已确认</option>
              <option value="resolved">已解决</option>
            </Select>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium text-slate-700">级别</label>
            <Select value={levelFilter} onChange={(event) => updateSearchParam('level', event.target.value)}>
              <option value="">全部</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="CRITICAL">CRITICAL</option>
            </Select>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-medium text-slate-700">标签</label>
            <Input
              placeholder="如 snapshot / backtest"
              value={tagFilter}
              onChange={(event) => updateSearchParam('tag', event.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
        <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <CardTitle className="text-slate-900">告警历史</CardTitle>
            <CardDescription>默认显示最新告警记录，支持逐条确认、解决和查看详情。</CardDescription>
          </div>
          <div className="text-sm text-slate-500">
            第 {currentPage} / {totalPages} 页，共 {total} 条
          </div>
        </CardHeader>
        <CardContent>
          {!history.length ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
              当前没有符合筛选条件的告警。
            </div>
          ) : (
            <>
              <div className="overflow-hidden rounded-2xl border border-slate-200">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>级别</TableHead>
                      <TableHead>标题</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>通道 / 标签</TableHead>
                      <TableHead>时间</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {history.map((alert) => (
                      <TableRow key={alert.id}>
                        <TableCell>
                          <div className="flex flex-wrap gap-2">
                            <Badge variant={levelVariant(alert.level)}>{alert.level}</Badge>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-medium text-slate-900">{alert.title}</p>
                            <p className="max-w-[36rem] truncate text-xs text-slate-500">{alert.message ?? '暂无详细消息。'}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusVariant(alert.status)}>{statusLabel(alert.status)}</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-2 text-xs text-slate-500">
                            <p>{alert.channel}</p>
                            <div className="flex flex-wrap gap-2">
                              {alert.tags.length ? alert.tags.map((tag) => (
                                <span key={tag} className="rounded-full border border-slate-200 px-2 py-1">
                                  {tag}
                                </span>
                              )) : <span className="text-slate-400">无标签</span>}
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1 text-xs text-slate-500">
                            <p>创建 {formatTimestamp(alert.created_at)}</p>
                            <p>发送 {formatTimestamp(alert.sent_at)}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => openDetail(alert)}
                            >
                              详情
                            </Button>
                            {canManageAlerts && alert.status !== 'acknowledged' && alert.status !== 'resolved' ? (
                              <Button
                                size="sm"
                                variant="secondary"
                                disabled={acknowledgeMutation.isPending || resolveMutation.isPending}
                                onClick={() => {
                                  void acknowledgeMutation.mutateAsync(alert.id);
                                }}
                              >
                                确认
                              </Button>
                            ) : null}
                            {canManageAlerts && alert.status !== 'resolved' ? (
                              <Button
                                size="sm"
                                disabled={acknowledgeMutation.isPending || resolveMutation.isPending}
                                onClick={() => {
                                  void resolveMutation.mutateAsync(alert.id);
                                }}
                              >
                                解决
                              </Button>
                            ) : null}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm text-slate-500">
                  当前页展示 {history.length} 条记录，支持继续翻页查看历史告警。
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    disabled={currentPage <= 1}
                    onClick={() => changePage(Math.max(1, currentPage - 1))}
                  >
                    上一页
                  </Button>
                  <Button
                    variant="outline"
                    disabled={currentPage >= totalPages}
                    onClick={() => changePage(Math.min(totalPages, currentPage + 1))}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm shadow-slate-200/40">
        <span>从首页的失败运行状态也可以进入这里继续处理。</span>
        <Link className="inline-flex items-center gap-2 font-medium text-sky-700 hover:text-sky-800" to="/">
          返回首页
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <AlertDetailDialog alert={detailAlert} open={detailOpen} onOpenChange={setDetailOpen} />
    </main>
  );
}
