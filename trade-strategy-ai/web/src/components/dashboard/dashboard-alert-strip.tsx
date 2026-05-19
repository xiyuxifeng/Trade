import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { ErrorState } from '@/components/state/ErrorState';
import { useDashboardAlertSummary } from '@/features/dashboard/use-dashboard-alert-summary';
import type { AlertHistoryItem } from '@/types/alerts';

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '未记录';
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

function AlertChip({ alert }: { alert: AlertHistoryItem }) {
  return (
    <article
      className="flex min-w-[18rem] flex-1 flex-col gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/40"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-semibold text-slate-900">{alert.title}</p>
          <p className="break-all text-xs text-slate-500">记录 {alert.alert_id}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge variant={levelVariant(alert.level)}>{alert.level}</Badge>
          <Badge variant={statusVariant(alert.status)}>{alert.status}</Badge>
        </div>
      </div>
      <p className="line-clamp-2 text-sm text-slate-600">{alert.message ?? '暂无详细消息。'}</p>
      <div className="flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full border border-slate-200 px-2 py-1">{alert.channel}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">{formatTimestamp(alert.created_at)}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">x{alert.aggregated_count}</span>
      </div>
    </article>
  );
}

function AlertStripSkeleton() {
  return (
    <div className="grid gap-3 lg:grid-cols-3">
      <Skeleton className="h-32 w-full rounded-2xl" />
      <Skeleton className="h-32 w-full rounded-2xl" />
      <Skeleton className="h-32 w-full rounded-2xl" />
    </div>
  );
}

export function DashboardAlertStrip() {
  const { data, error, isLoading, refetch, isFetching } = useDashboardAlertSummary();

  if (isLoading) {
    return <AlertStripSkeleton />;
  }

  if (error) {
    const message = error instanceof ApiError ? error.message : '重点告警加载失败';
    return (
      <ErrorState
        category="network error"
        title="重点告警加载失败"
        description="当前告警摘要接口请求失败。"
        suggestion="重试后查看任务中心，确认是否已有新的失败任务或告警记录。"
        detail={message}
        retryLabel={isFetching ? '重试中' : '重试'}
        onRetry={() => {
          void refetch();
        }}
      />
    );
  }

  const alerts = data?.items ?? [];

  return (
    <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
      <CardHeader>
        <CardTitle className="text-slate-900">重点告警</CardTitle>
        <CardDescription>展示最重要的 3 到 5 条告警摘要，便于快速判断告警趋势。</CardDescription>
      </CardHeader>
      <CardContent>
        {!alerts.length ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
            当前没有需要优先关注的告警。
          </div>
        ) : (
          <div className="grid gap-3 xl:grid-cols-2">
            {alerts.map((alert) => (
              <AlertChip key={alert.id} alert={alert} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
