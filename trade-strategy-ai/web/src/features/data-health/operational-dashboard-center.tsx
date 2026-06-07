import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatusBadge } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { getSystemDashboard, getSystemStatus } from '@/lib/api/system';
import type { SystemDashboardFailedJob, SystemDashboardResponse, SystemStatusResponse } from '@/types/system';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '健康仪表盘加载失败';
}

function SummaryCard({ title, value, detail }: { title: string; value: string | number; detail: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{detail}</p>
    </div>
  );
}

function SystemComponentRow({ label, status, detail }: { label: string; status?: string | null; detail?: string | null }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3">
      <div>
        <p className="font-medium text-slate-950">{label}</p>
        <p className="text-xs text-slate-500">{detail ?? 'n/a'}</p>
      </div>
      <StatusBadge value={status ?? 'n/a'} />
    </div>
  );
}

function FailedJobRow({ job }: { job: SystemDashboardFailedJob }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold text-slate-950">{job.id}</p>
          <p className="text-xs text-slate-500">{job.job_type}</p>
        </div>
        <StatusBadge value={job.status} />
      </div>
      <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
        <p>耗时：{job.duration_seconds ?? 'n/a'} s</p>
        <p>结束：{job.finished_at ?? 'n/a'}</p>
        <p className="md:col-span-2">错误：{job.error_message ?? 'n/a'}</p>
      </div>
    </div>
  );
}

function TraceRow({ jobId, method, path, clientHost }: { jobId: string; method?: string; path?: string; clientHost?: string | null }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="font-medium text-slate-950">{jobId}</p>
      <p className="mt-2 text-sm text-slate-700">
        {method ?? 'n/a'} {path ?? 'n/a'}
      </p>
      <p className="text-xs text-slate-500">client: {clientHost ?? 'n/a'}</p>
    </div>
  );
}

export function OperationalDashboardCenter() {
  const statusQuery = useQuery<SystemStatusResponse, ApiError>({
    queryKey: ['data-health', 'system-status'],
    queryFn: () => getSystemStatus(),
    staleTime: 10_000,
  });

  const dashboardQuery = useQuery<SystemDashboardResponse, ApiError>({
    queryKey: ['data-health', 'system-dashboard'],
    queryFn: () => getSystemDashboard(),
    staleTime: 10_000,
  });

  const status = statusQuery.data ?? null;
  const dashboard = dashboardQuery.data ?? null;

  const healthComponents = useMemo(
    () =>
      dashboard
        ? Object.entries(dashboard.health)
            .filter(([key, value]) => key !== 'overall' && key !== 'issues' && key !== 'database' && value && typeof value === 'object')
            .map(([key, value]) => ({ key, value: value as { status?: string; latency_ms?: number | null; error?: string | null } }))
        : [],
    [dashboard],
  );

  if (statusQuery.isLoading || dashboardQuery.isLoading) {
    return (
      <section className="space-y-4">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">Health Check Dashboard</CardTitle>
            <CardDescription className="text-slate-600">正在读取系统健康状态。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-10 w-56 bg-slate-100" />
            <Skeleton className="h-52 rounded-2xl bg-slate-100" />
          </CardContent>
        </Card>
      </section>
    );
  }

  if (statusQuery.isError || dashboardQuery.isError) {
    const error = statusQuery.error ?? dashboardQuery.error;
    return (
      <section className="space-y-4">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">Health Check Dashboard</CardTitle>
            <CardDescription className="text-slate-600">当前健康状态接口请求失败。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{getErrorMessage(error)}</div>
            <Button
              variant="outline"
              onClick={() => {
                void statusQuery.refetch();
                void dashboardQuery.refetch();
              }}
              disabled={statusQuery.isFetching || dashboardQuery.isFetching}
            >
              {statusQuery.isFetching || dashboardQuery.isFetching ? '重试中' : '重试'}
            </Button>
          </CardContent>
        </Card>
      </section>
    );
  }

  if (!status || !dashboard) {
    return (
      <section className="space-y-4">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-950">Health Check Dashboard</CardTitle>
            <CardDescription className="text-slate-600">暂无可显示的数据。</CardDescription>
          </CardHeader>
        </Card>
      </section>
    );
  }

  const freshnessSources = dashboard.freshness.sources ?? [];
  const failedJobs = dashboard.failed_jobs ?? [];
  const latestAlerts = dashboard.alerts.latest ?? [];
  const latestTraces = dashboard.traces ?? [];
  const configIssues = status.warnings ?? [];

  return (
    <section className="space-y-4">
      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-slate-950">Health Check Dashboard</CardTitle>
              <CardDescription className="text-slate-600">API、DB、worker、queue、provider、storage 与配置校验摘要。</CardDescription>
            </div>
            <Button
              variant="outline"
              onClick={() => {
                void statusQuery.refetch();
                void dashboardQuery.refetch();
              }}
              disabled={statusQuery.isFetching || dashboardQuery.isFetching}
            >
              {statusQuery.isFetching || dashboardQuery.isFetching ? '刷新中' : '刷新'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <SummaryCard title="API status" value={status.status} detail="系统状态接口返回值" />
            <SummaryCard title="DB status" value={status.database.status} detail={`latency ${status.database.latency_ms ?? 'n/a'} ms`} />
            <SummaryCard title="Worker status" value={dashboard.worker.status} detail={dashboard.worker.current_job_id ?? 'no current job'} />
            <SummaryCard title="Job queue" value={dashboard.status} detail="综合健康结果" />
          </div>

          {configIssues.length ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <p className="font-medium">配置 / 目录提醒</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {configIssues.map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="grid gap-4 xl:grid-cols-2">
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-900">健康组件</p>
              <div className="space-y-3">
                <SystemComponentRow label="数据库" status={status.database.status} detail={status.database.error ?? undefined} />
                {healthComponents.map((component) => (
                  <SystemComponentRow
                    key={component.key}
                    label={component.key}
                    status={component.value.status}
                    detail={component.value.error ?? component.value.latency_ms?.toString() ?? undefined}
                  />
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-900">关键目录</p>
              <div className="space-y-3">
                {Object.entries(status.directories).map(([key, item]) => (
                  <div key={key} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                    <div>
                      <p className="font-medium text-slate-950">{key}</p>
                      <p className="text-xs text-slate-500">{item.path}</p>
                    </div>
                    <Badge variant={item.exists ? 'success' : 'destructive'}>{item.exists ? 'exists' : 'missing'}</Badge>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-900">Recent critical failures</p>
              {failedJobs.length ? (
                failedJobs.map((job) => <FailedJobRow job={job} key={job.id} />)
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                  暂无失败任务。
                </div>
              )}
            </div>

            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-900">Freshness</p>
              {freshnessSources.length ? (
                <div className="space-y-3">
                  {freshnessSources.map((source) => (
                    <div key={source.source} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                      <div>
                        <p className="font-medium text-slate-950">{source.source}</p>
                        <p className="text-xs text-slate-500">{source.entity_type}</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-slate-700">{source.freshness_hours ?? 'n/a'} h</span>
                        <Badge variant={source.is_stale ? 'warning' : 'success'}>{source.is_stale ? 'stale' : 'fresh'}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                  暂无新鲜度数据。
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-900">Latest alerts</p>
              {latestAlerts.length ? (
                <div className="space-y-3">
                  {latestAlerts.map((alert, index) => (
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4" key={`${String(alert.title)}-${index}`}>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <p className="font-medium text-slate-950">{String(alert.title ?? 'alert')}</p>
                        <Badge variant={String(alert.level) === 'critical' ? 'destructive' : 'warning'}>{String(alert.level ?? 'info')}</Badge>
                      </div>
                      <p className="mt-2 text-sm text-slate-700">{String(alert.message ?? '')}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                  暂无告警。
                </div>
              )}
            </div>

            <div className="space-y-3">
              <p className="text-sm font-medium text-slate-900">Trace hints</p>
              {latestTraces.length ? (
                <div className="space-y-3">
                  {latestTraces.map((trace) => (
                    <TraceRow
                      key={trace.job_id}
                      jobId={trace.job_id}
                      method={trace.request_context?.method}
                      path={trace.request_context?.path}
                      clientHost={trace.request_context?.client_host}
                    />
                  ))}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
                  暂无追踪线索。
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
