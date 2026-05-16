import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import type { AlertHistoryItem } from '@/types/alerts';
import { useAlertDetail } from './use-alert-detail';

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

function AlertInlineError({ message }: { message: string }) {
  return <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{message}</div>;
}

function AlertEmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-500">
      <p className="text-base font-medium text-slate-900">{title}</p>
      <p className="mt-2">{description}</p>
    </div>
  );
}

function TimelineItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-900">{value}</span>
    </div>
  );
}

function AlertDetailSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-28 w-full rounded-2xl" />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <Skeleton className="h-[28rem] w-full rounded-2xl" />
        <Skeleton className="h-[28rem] w-full rounded-2xl" />
      </div>
    </div>
  );
}

function AlertNarrativeCard({ alert }: { alert: AlertHistoryItem }) {
  const mutationText =
    alert.status === 'resolved' ? '当前告警已解决。' : alert.status === 'acknowledged' ? '当前告警已确认。' : '当前告警仍需处理。';

  return (
    <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-slate-900">{alert.title}</CardTitle>
            <CardDescription className="mt-1 break-all">记录 {alert.id} · 告警 {alert.alert_id}</CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={statusVariant(alert.status)}>{alert.status}</Badge>
            <Badge variant={levelVariant(alert.level)}>{alert.level}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">告警消息</p>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{alert.message ?? '暂无可用消息。'}</p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">上下文摘要</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant="info">{alert.channel}</Badge>
            <Badge variant="default">x{alert.aggregated_count}</Badge>
            {alert.tags.length ? alert.tags.map((tag) => <Badge key={tag}>{tag}</Badge>) : <Badge>无标签</Badge>}
          </div>
        </div>

        <p className="text-sm text-slate-600">{mutationText}</p>
      </CardContent>
    </Card>
  );
}

function AlertTimelineCard({ alert }: { alert: AlertHistoryItem }) {
  return (
    <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
      <CardHeader>
        <CardTitle className="text-slate-900">时间线</CardTitle>
        <CardDescription>告警生成、确认和解决的时间顺序。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <TimelineItem label="创建时间" value={formatTimestamp(alert.created_at)} />
        <TimelineItem label="发送时间" value={formatTimestamp(alert.sent_at)} />
        <TimelineItem label="确认时间" value={formatTimestamp(alert.acknowledged_at)} />
        <TimelineItem label="解决时间" value={formatTimestamp(alert.resolved_at)} />
      </CardContent>
    </Card>
  );
}

function AlertMetadataCard({
  alert,
  onAcknowledge,
  onResolve,
  isAcknowledging,
  isResolving,
}: {
  alert: AlertHistoryItem;
  onAcknowledge: () => void;
  onResolve: () => void;
  isAcknowledging: boolean;
  isResolving: boolean;
}) {
  const tags = alert.tags.length ? alert.tags.join('，') : '无';

  return (
    <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
      <CardHeader>
        <CardTitle className="text-slate-900">元数据与操作</CardTitle>
        <CardDescription>查看来源、标签，并执行确认或解决。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">来源</p>
            <p className="mt-2 break-all text-sm text-slate-700">{alert.channel}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">标签</p>
            <p className="mt-2 text-sm text-slate-700">{tags}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">聚合键</p>
            <p className="mt-2 break-all text-sm text-slate-700">{alert.aggregation_key ?? '无'}</p>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button onClick={onAcknowledge} disabled={isAcknowledging || isResolving}>
            {isAcknowledging ? '确认中…' : '确认告警'}
          </Button>
          <Button variant="outline" onClick={onResolve} disabled={isAcknowledging || isResolving}>
            {isResolving ? '解决中…' : '解决告警'}
          </Button>
          <Link
            className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700"
            to="/alerts"
          >
            返回告警中心
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

export function AlertDetailPanel({ recordId }: { recordId: string }) {
  const { detailQuery, acknowledgeMutation, resolveMutation } = useAlertDetail(recordId);

  if (!recordId) {
    return (
      <main className="page-stack">
        <AlertEmptyState title="告警不存在" description="请返回 Dashboard 或告警中心重新选择一条记录。" />
      </main>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <main className="page-stack">
        <AlertDetailSkeleton />
      </main>
    );
  }

  const error = detailQuery.error;
  if (error) {
    if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
      return (
        <main className="page-stack">
          <AlertEmptyState title="没有权限查看告警详情" description="请确认你的 API Key 或登录状态后重试。" />
        </main>
      );
    }

    if (error instanceof ApiError && error.status === 404) {
      return (
        <main className="page-stack">
          <AlertEmptyState title="告警不存在" description="该告警记录可能已被删除或未同步到当前环境。" />
        </main>
      );
    }

    return (
      <main className="page-stack">
        <AlertInlineError message={error instanceof ApiError ? error.message : '告警详情加载失败'} />
      </main>
    );
  }

  const alert = detailQuery.data;
  if (!alert) {
    return (
      <main className="page-stack">
        <AlertEmptyState title="暂无告警详情" description="当前记录未返回可显示的数据。" />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <section className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="page-kicker">告警</p>
          <h1 className="text-3xl font-semibold text-slate-900">告警详情</h1>
          <p className="mt-2 text-sm text-slate-600">查看告警上下文、关联对象和处理动作。</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant={statusVariant(alert.status)}>{alert.status}</Badge>
          <Badge variant={levelVariant(alert.level)}>{alert.level}</Badge>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="space-y-6">
          <AlertNarrativeCard alert={alert} />
          <AlertTimelineCard alert={alert} />
        </div>
        <AlertMetadataCard
          alert={alert}
          onAcknowledge={() => acknowledgeMutation.mutate()}
          onResolve={() => resolveMutation.mutate()}
          isAcknowledging={acknowledgeMutation.isPending}
          isResolving={resolveMutation.isPending}
        />
      </section>

      {acknowledgeMutation.isSuccess ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">已确认告警。</div>
      ) : null}

      {resolveMutation.isSuccess ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">已解决告警。</div>
      ) : null}

      {acknowledgeMutation.error || resolveMutation.error ? (
        <AlertInlineError
          message={
            (acknowledgeMutation.error instanceof ApiError && acknowledgeMutation.error.message) ||
            (resolveMutation.error instanceof ApiError && resolveMutation.error.message) ||
            '告警操作失败'
          }
        />
      ) : null}
    </main>
  );
}
