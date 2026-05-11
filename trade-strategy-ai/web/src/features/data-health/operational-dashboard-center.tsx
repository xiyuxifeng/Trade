import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { getSystemDashboard } from '@/lib/api/system';
import type { SystemDashboardFailedJob, SystemDashboardResponse } from '@/types/system';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Operational Dashboard 加载失败';
}

function SummaryCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function FailedJobRow({ job }: { job: SystemDashboardFailedJob }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-100">{job.id}</p>
          <p className="text-xs text-slate-400">{job.job_type}</p>
        </div>
        <Badge variant="destructive">{job.status}</Badge>
      </div>
      <div className="mt-3 grid gap-2 text-sm text-slate-300 md:grid-cols-2">
        <p>耗时: {job.duration_seconds ?? 'n/a'} s</p>
        <p>结束: {job.finished_at ?? 'n/a'}</p>
        <p className="md:col-span-2">错误: {job.error_message ?? 'n/a'}</p>
      </div>
    </div>
  );
}

function SourceFreshnessRow({
  source,
  entityType,
  freshnessHours,
  isStale,
}: {
  source: string;
  entityType: string;
  freshnessHours: number | null | undefined;
  isStale: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3">
      <div>
        <p className="font-medium text-slate-100">{source}</p>
        <p className="text-xs text-slate-400">{entityType}</p>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm text-slate-300">{freshnessHours ?? 'n/a'} h</span>
        <Badge variant={isStale ? 'warning' : 'success'}>{isStale ? 'stale' : 'fresh'}</Badge>
      </div>
    </div>
  );
}

export function OperationalDashboardCenter() {
  const dashboardQuery = useQuery({
    queryKey: ['system', 'dashboard'],
    queryFn: () => getSystemDashboard(),
    staleTime: 10_000,
  });

  const dashboard = dashboardQuery.data ?? null;

  if (dashboardQuery.isLoading) {
    return (
      <section className="dashboard-grid">
        <Card className="xl:col-span-12">
          <CardHeader>
            <CardTitle>Operational Dashboard</CardTitle>
            <CardDescription>正在读取运维摘要。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-6 w-1/2" />
            <Skeleton className="h-40 w-full rounded-2xl" />
          </CardContent>
        </Card>
      </section>
    );
  }

  if (dashboardQuery.isError) {
    return (
      <section className="dashboard-grid">
        <Card className="xl:col-span-12">
          <CardHeader>
            <CardTitle>Operational Dashboard</CardTitle>
            <CardDescription>当前摘要接口请求失败。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
              {getErrorMessage(dashboardQuery.error)}
            </div>
            <Button variant="outline" onClick={() => dashboardQuery.refetch()} disabled={dashboardQuery.isFetching}>
              {dashboardQuery.isFetching ? '重试中' : '重试'}
            </Button>
          </CardContent>
        </Card>
      </section>
    );
  }

  if (!dashboard) {
    return (
      <section className="dashboard-grid">
        <Card className="xl:col-span-12">
          <CardHeader>
            <CardTitle>Operational Dashboard</CardTitle>
            <CardDescription>暂无可显示的数据。</CardDescription>
          </CardHeader>
        </Card>
      </section>
    );
  }

  const freshnessSources = dashboard.freshness.sources ?? [];
  const failedJobs = dashboard.failed_jobs ?? [];
  const latestAlerts = dashboard.alerts.latest ?? [];
  const latestTraces = dashboard.traces ?? [];
  const worker =
    dashboard.worker ?? {
      status: 'warning' as const,
      heartbeat_at: null,
      heartbeat_age_minutes: null,
      current_job_id: null,
    };

  return (
    <section className="dashboard-grid">
      <Card className="xl:col-span-12">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>Operational Dashboard</CardTitle>
              <CardDescription>最近失败任务、耗时、新鲜度、告警和追踪线索。</CardDescription>
            </div>
            <Button variant="outline" onClick={() => dashboardQuery.refetch()} disabled={dashboardQuery.isFetching}>
              {dashboardQuery.isFetching ? '刷新中' : '刷新'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <SummaryCard title="Failed jobs" value={failedJobs.length} accent="text-rose-300" />
            <SummaryCard title="Avg duration" value={dashboard.duration_summary.average_seconds ?? 'n/a'} accent="text-amber-300" />
            <SummaryCard title="Critical alerts" value={dashboard.alerts.critical} accent="text-fuchsia-300" />
            <SummaryCard title="Stale sources" value={freshnessSources.filter((item) => item.is_stale).length} accent="text-sky-300" />
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-200">Failed jobs</p>
              {failedJobs.length ? (
                failedJobs.map((job) => <FailedJobRow job={job} key={job.id} />)
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
                  暂无失败任务。
                </div>
              )}
            </div>

            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-200">Freshness</p>
              {freshnessSources.length ? (
                freshnessSources.map((source) => (
                  <SourceFreshnessRow
                    entityType={source.entity_type}
                    freshnessHours={source.freshness_hours}
                    isStale={source.is_stale}
                    key={source.source}
                    source={source.source}
                  />
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
                  暂无新鲜度数据。
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-200">Latest alerts</p>
              {latestAlerts.length ? (
                <div className="space-y-3">
                  {latestAlerts.map((alert, index) => (
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4" key={`${String(alert.title)}-${index}`}>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="font-medium text-slate-100">{String(alert.title ?? 'alert')}</p>
                        <Badge variant={String(alert.level) === 'critical' ? 'destructive' : 'warning'}>{String(alert.level ?? 'info')}</Badge>
                      </div>
                      <p className="mt-2 text-sm text-slate-300">{String(alert.message ?? '')}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
                  暂无告警。
                </div>
              )}
            </div>

            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-200">Trace hints</p>
              {latestTraces.length ? (
                <div className="space-y-3">
                  {latestTraces.map((trace) => (
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4" key={trace.job_id}>
                      <p className="font-medium text-slate-100">{trace.job_id}</p>
                      <p className="mt-2 text-sm text-slate-300">{trace.request_context?.method ?? 'n/a'} {trace.request_context?.path ?? 'n/a'}</p>
                      <p className="text-xs text-slate-500">client: {trace.request_context?.client_host ?? 'n/a'}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
                  暂无追踪线索。
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
            <p className="text-sm font-medium text-slate-200">Worker</p>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <SummaryCard title="Status" value={worker.status} accent="text-emerald-300" />
              <SummaryCard title="Heartbeat" value={worker.heartbeat_at ?? 'n/a'} accent="text-sky-300" />
              <SummaryCard title="Heartbeat age" value={worker.heartbeat_age_minutes ?? 'n/a'} accent="text-amber-300" />
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
