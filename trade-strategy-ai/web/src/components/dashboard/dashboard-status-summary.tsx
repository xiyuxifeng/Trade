import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { ErrorState } from '@/components/state/ErrorState';
import { useRecentArtifacts } from '@/features/artifacts/use-recent-artifacts';
import { useRecentJobs } from '@/features/jobs/use-recent-jobs';
import { useDashboardAlertSummary } from '@/features/dashboard/use-dashboard-alert-summary';
import { useSystemStatus } from '@/features/system-status/use-system-status';

function MetricCard({
  label,
  value,
  note,
  tone = 'text-slate-100',
}: {
  label: string;
  value: string | number;
  note?: string;
  tone?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/40">
      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${tone}`}>{value}</p>
      {note ? <p className="mt-2 text-xs text-slate-500">{note}</p> : null}
    </div>
  );
}

function LoadingGrid() {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Skeleton className="h-28 w-full rounded-2xl" />
      <Skeleton className="h-28 w-full rounded-2xl" />
      <Skeleton className="h-28 w-full rounded-2xl" />
      <Skeleton className="h-28 w-full rounded-2xl" />
    </section>
  );
}

export function DashboardStatusSummary() {
  const systemStatus = useSystemStatus();
  const recentJobs = useRecentJobs();
  const recentArtifacts = useRecentArtifacts();
  const alertSummary = useDashboardAlertSummary();
  const reloadAll = async () => {
    await Promise.all([systemStatus.refetch(), recentJobs.refetch(), recentArtifacts.refetch(), alertSummary.refetch()]);
  };

  if (systemStatus.isLoading || recentJobs.isLoading || recentArtifacts.isLoading || alertSummary.isLoading) {
    return <LoadingGrid />;
  }

  const system = systemStatus.data;
  const jobs = recentJobs.data?.items ?? [];
  const artifacts = recentArtifacts.data?.items ?? [];
  const alerts = alertSummary.data?.items ?? [];
  const error =
    systemStatus.error || recentJobs.error || recentArtifacts.error || alertSummary.error;

  const failedJobs = jobs.filter((job) => job.status === 'failed').length;
  const acknowledgedJobs = jobs.filter((job) => job.status === 'success').length;
  const warnings = system?.warnings?.length ?? 0;
  const databaseStatus = system?.database.status ?? 'unknown';

  return (
    <section className="space-y-4">
      {error ? (
        <ErrorState
          category="network error"
          title="部分总览数据加载失败"
          description={error instanceof ApiError ? error.message : '系统总览存在部分数据异常。'}
          suggestion="重新加载总览数据，或先前往任务中心和产物中心确认相关结果是否已经生成。"
          actions={[
            { label: '任务中心', to: '/jobs' },
            { label: '产物中心', to: '/artifacts' },
          ]}
          onRetry={() => {
            void reloadAll();
          }}
        />
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="系统健康"
          value={system?.status ?? 'unknown'}
          note={system?.run_mode ? `运行模式 · ${system.run_mode}` : '系统总览状态'}
          tone={system?.status === 'ok' ? 'text-emerald-600' : system?.status === 'warning' ? 'text-amber-600' : 'text-rose-600'}
        />
        <MetricCard
          label="数据库"
          value={databaseStatus}
          note={system?.database.latency_ms != null ? `延迟 ${system.database.latency_ms} ms` : '数据库健康状态'}
          tone={databaseStatus === 'ok' ? 'text-emerald-600' : databaseStatus === 'warning' ? 'text-amber-600' : 'text-rose-600'}
        />
        <MetricCard label="失败任务" value={failedJobs} note={`成功任务 ${acknowledgedJobs}`} tone={failedJobs ? 'text-rose-600' : 'text-slate-900'} />
        <MetricCard label="产物数量" value={artifacts.length} note={artifacts[0]?.kind ? `最新类型 · ${artifacts[0].kind}` : '暂无最新产物'} tone="text-sky-600" />
        <MetricCard label="告警摘要" value={alerts.length} note="重点告警状态栏会显示这些记录" tone={alerts.length ? 'text-amber-600' : 'text-slate-900'} />
        <MetricCard label="目录提示" value={warnings} note={warnings ? '有目录需要检查' : '关键目录正常'} tone={warnings ? 'text-amber-600' : 'text-emerald-600'} />
        <MetricCard
          label="配置"
          value={system?.config_path ? '已加载' : '未知'}
          note={system?.config_path ? '当前配置文件已识别' : '未识别配置文件'}
          tone="text-slate-900"
        />
        <MetricCard
          label="工作流"
          value={jobs[0]?.job_type ?? '暂无'}
          note={jobs[0]?.id ? `最近任务 ${jobs[0].id}` : '暂无最近任务'}
          tone="text-violet-600"
        />
      </div>
    </section>
  );
}

export function DashboardQuickLinks() {
  return (
    <Card className="border-slate-200 bg-white shadow-sm shadow-slate-200/40">
      <CardHeader>
        <CardTitle className="text-slate-900">快速入口</CardTitle>
        <CardDescription>低优先级辅助入口，不打断系统状态扫描。</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-3">
          {[
            { label: '任务中心', path: '/jobs' },
            { label: '配置管理', path: '/profiles' },
            { label: '市场数据', path: '/market' },
            { label: '策略工作台', path: '/strategies' },
            { label: '系统审计', path: '/system/audit' },
            { label: '产物中心', path: '/artifacts' },
          ].map((item) => (
            <Link
              className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-sky-300 hover:bg-sky-50 hover:text-sky-700"
              key={item.path}
              to={item.path}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
