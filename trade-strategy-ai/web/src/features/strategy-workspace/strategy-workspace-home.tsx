import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, ErrorState, LoadingState, StatusBadge } from '@/components/kit';
import { listProfiles } from '@/lib/api/profiles';
import { listJobs } from '@/lib/api/jobs';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { formatLocalDateInputOffset } from '@/lib/date';
import { isWorkspacePermissionDenied } from './strategy-workspace-utils';
import type { JobRecord } from '@/types/jobs';

type QuickLink = {
  label: string;
  to: string;
  description: string;
};

function sortJobsByCreatedAtDesc(items: JobRecord[]) {
  return [...items].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function SummaryTile({
  label,
  value,
  detail,
  status,
}: {
  label: string;
  value: string;
  detail?: string;
  status?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
        {status ? <StatusBadge value={status} /> : null}
      </div>
      <p className="mt-2 break-all text-base font-semibold text-slate-950">{value}</p>
      {detail ? <p className="mt-2 text-sm leading-6 text-slate-600">{detail}</p> : null}
    </div>
  );
}

function JobSummaryRow({
  label,
  job,
  href,
  emptyLabel,
}: {
  label: string;
  job: JobRecord | null;
  href: string;
  emptyLabel: string;
}) {
  return (
    <Link
      className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white px-4 py-3 transition-colors hover:border-sky-200 hover:bg-sky-50/60"
      to={href}
    >
      <div className="min-w-0">
        <p className="text-sm font-medium text-slate-950">{label}</p>
        <p className="mt-1 truncate text-sm text-slate-600">{job ? `${job.id} · ${job.job_type}` : emptyLabel}</p>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        {job ? <StatusBadge value={job.status} /> : <Badge variant="default">暂无</Badge>}
        <span className="text-xs text-slate-500">{job ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(job.created_at)) : '等待执行'}</span>
      </div>
    </Link>
  );
}

function FlowLinkTile({ item }: { item: QuickLink }) {
  return (
    <Link
      className="rounded-2xl border border-slate-200 bg-white p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70"
      to={item.to}
    >
      <p className="text-sm font-medium text-slate-950">{item.label}</p>
      <p className="mt-1 text-sm leading-6 text-slate-600">{item.description}</p>
    </Link>
  );
}

export function StrategyWorkspaceHomePage() {
  const navigate = useNavigate();
  const today = formatLocalDateInputOffset(0);
  const pageDescription =
    '策略工作台用于管理每日策略运行、策略版本构建和策略优化。日常使用优先进入盘前准备和盘后复盘；当 Profile、规则池、市场状态或候选版本变化时，再构建新的策略版本。';

  const profilesQuery = useQuery({
    queryKey: ['strategy-home', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  const profileItems = profilesQuery.data?.items ?? [];

  const currentProfile = useMemo(() => profileItems[0] ?? null, [profileItems]);

  const currentProfileLabel = currentProfile
    ? `${currentProfile.name} · ${currentProfile.profile_id}`
    : '未选择';

  const currentProfileDetail = currentProfile
    ? `环境 ${currentProfile.environment} · v${currentProfile.version} · 更新于 ${new Intl.DateTimeFormat('zh-CN', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(currentProfile.updated_at))}`
    : '请先导入或创建正式 Profile';

  const snapshotBuildJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', 'snapshot-build'],
    queryFn: () => listJobs({ job_type: 'snapshot-build', limit: 5 }),
    staleTime: 30_000,
  });

  const preMarketJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', 'run-pre-market'],
    queryFn: () => listJobs({ job_type: 'run-pre-market', limit: 5 }),
    staleTime: 30_000,
  });

  const afterCloseJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', 'run-after-close'],
    queryFn: () => listJobs({ job_type: 'run-after-close', limit: 5 }),
    staleTime: 30_000,
  });

  const strategyBuildJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', 'strategy-build'],
    queryFn: () => listJobs({ job_type: 'strategy-build', limit: 5 }),
    staleTime: 30_000,
  });

  const snapshotBuildFailedJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', 'failed', 'snapshot-build'],
    queryFn: () => listJobs({ job_type: 'snapshot-build', status: 'failed', limit: 5 }),
    staleTime: 30_000,
  });

  const preMarketFailedJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', 'failed', 'run-pre-market'],
    queryFn: () => listJobs({ job_type: 'run-pre-market', status: 'failed', limit: 5 }),
    staleTime: 30_000,
  });

  const afterCloseFailedJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', 'failed', 'run-after-close'],
    queryFn: () => listJobs({ job_type: 'run-after-close', status: 'failed', limit: 5 }),
    staleTime: 30_000,
  });

  const strategyBuildFailedJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', 'failed', 'strategy-build'],
    queryFn: () => listJobs({ job_type: 'strategy-build', status: 'failed', limit: 5 }),
    staleTime: 30_000,
  });

  const queryError =
    profilesQuery.error ??
    snapshotBuildJobsQuery.error ??
    preMarketJobsQuery.error ??
    afterCloseJobsQuery.error ??
    strategyBuildJobsQuery.error ??
    snapshotBuildFailedJobsQuery.error ??
    preMarketFailedJobsQuery.error ??
    afterCloseFailedJobsQuery.error ??
    strategyBuildFailedJobsQuery.error;
  const permissionDenied = isWorkspacePermissionDenied(queryError);

  const isLoading =
    profilesQuery.isLoading ||
    snapshotBuildJobsQuery.isLoading ||
    preMarketJobsQuery.isLoading ||
    afterCloseJobsQuery.isLoading ||
    strategyBuildJobsQuery.isLoading ||
    snapshotBuildFailedJobsQuery.isLoading ||
    preMarketFailedJobsQuery.isLoading ||
    afterCloseFailedJobsQuery.isLoading ||
    strategyBuildFailedJobsQuery.isLoading;

  const profileCount = profileItems.length;
  const latestSnapshotBuildJob = sortJobsByCreatedAtDesc(snapshotBuildJobsQuery.data?.items ?? [])[0] ?? null;
  const latestPreMarketJob = sortJobsByCreatedAtDesc(preMarketJobsQuery.data?.items ?? [])[0] ?? null;
  const latestAfterCloseJob = sortJobsByCreatedAtDesc(afterCloseJobsQuery.data?.items ?? [])[0] ?? null;
  const latestStrategyBuildJob = sortJobsByCreatedAtDesc(strategyBuildJobsQuery.data?.items ?? [])[0] ?? null;
  const failedJobs = [
    ...(snapshotBuildFailedJobsQuery.data?.items ?? []),
    ...(preMarketFailedJobsQuery.data?.items ?? []),
    ...(afterCloseFailedJobsQuery.data?.items ?? []),
    ...(strategyBuildFailedJobsQuery.data?.items ?? []),
  ];
  const failedJobCount =
    (snapshotBuildFailedJobsQuery.data?.total ?? 0) +
    (preMarketFailedJobsQuery.data?.total ?? 0) +
    (afterCloseFailedJobsQuery.data?.total ?? 0) +
    (strategyBuildFailedJobsQuery.data?.total ?? 0);
  const latestFailedJob = sortJobsByCreatedAtDesc(failedJobs)[0] ?? null;

  const todayRunLinks: QuickLink[] = [
    { label: '盘前准备', to: '/strategies/pre-market', description: '构建候选池快照并运行盘前' },
    { label: '盘后复盘', to: '/strategies/after-close', description: '查看盘后结果、归因和产物' },
  ];

  const strategyBuildLinks: QuickLink[] = [
    { label: '规则选择', to: '/strategies/regime-selection', description: '根据当前 Market Regime 选择适用规则' },
    { label: '构建策略版本', to: '/strategies/versions', description: '提交 strategy-build 并查看版本结果' },
  ];

  const strategyOptimizationLinks: QuickLink[] = [
    { label: '候选版本', to: '/strategies/candidates', description: '生成与审核候选版本' },
  ];

  const traceLinks: QuickLink[] = [{ label: '运行历史', to: '/strategies/history', description: '查看最近策略执行历史' }];

  if (isLoading) {
    return (
      <main className="page-stack">
        <PageHeader kicker="策略" title="策略工作台" description={pageDescription} />
        <LoadingState label="正在加载策略摘要" description="正在读取 Profile、策略版本和最近任务。" />
      </main>
    );
  }

  if (queryError) {
    return (
      <main className="page-stack">
        <PageHeader kicker="策略" title="策略工作台" description={pageDescription} />
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'strategy')}
          onRetry={permissionDenied ? undefined : () => {
            void profilesQuery.refetch();
            void snapshotBuildJobsQuery.refetch();
            void preMarketJobsQuery.refetch();
            void afterCloseJobsQuery.refetch();
            void strategyBuildJobsQuery.refetch();
            void snapshotBuildFailedJobsQuery.refetch();
            void preMarketFailedJobsQuery.refetch();
            void afterCloseFailedJobsQuery.refetch();
            void strategyBuildFailedJobsQuery.refetch();
          }}
          actions={[{ label: '前往配置管理', to: '/profiles' }]}
        />
      </main>
    );
  }

  if (profileCount === 0) {
    return (
      <main className="page-stack">
        <PageHeader kicker="策略" title="策略工作台" description={pageDescription} />
        <EmptyState
          title="暂无可用 Profile。"
          description="请先导入或创建正式 Profile，再返回策略首页查看摘要与入口。"
          actionLabel="前往配置管理"
          onAction={() => navigate('/profiles')}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader kicker="策略" title="策略工作台" description={pageDescription} />

      <section className="grid gap-4">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              今日运行
            </Badge>
            <CardTitle className="mt-2 text-slate-950">日常使用从这里开始</CardTitle>
            <CardDescription className="text-slate-600">
              日常使用从这里开始；不一定每天都需要重新构建策略版本。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <SummaryTile
                detail={currentProfileDetail}
                label="当前 Profile"
                status={currentProfile?.validation_status ?? 'validated'}
                value={currentProfileLabel}
              />
              <SummaryTile
                detail="默认使用当前日期作为策略首页的展示日期。"
                label="策略日期"
                value={today}
              />
              <SummaryTile label="失败任务总数" value={String(failedJobCount)} />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {todayRunLinks.map((item) => (
                <FlowLinkTile key={item.label} item={item} />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              策略构建
            </Badge>
            <CardTitle className="mt-2 text-slate-950">规则选择 / 构建策略版本</CardTitle>
            <CardDescription className="text-slate-600">
              当规则、Profile、Snapshot 或 Market Regime 变化时使用。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              {strategyBuildLinks.map((item) => (
                <FlowLinkTile key={item.label} item={item} />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              策略优化
            </Badge>
            <CardTitle className="mt-2 text-slate-950">候选版本</CardTitle>
            <CardDescription className="text-slate-600">
              候选版本审核通过后会成为 released 策略版本，用于后续构建和运行选择。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              {strategyOptimizationLinks.map((item) => (
                <FlowLinkTile key={item.label} item={item} />
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              追踪与排查
            </Badge>
            <CardTitle className="mt-2 text-slate-950">运行历史</CardTitle>
            <CardDescription className="text-slate-600">
              查看 strategy-build、run-pre-market、run-after-close 等任务，作为排查入口。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              {traceLinks.map((item) => (
                <FlowLinkTile key={item.label} item={item} />
              ))}
            </div>
            <div className="space-y-3">
              <JobSummaryRow
                emptyLabel="尚无 snapshot-build 任务。"
                href="/jobs?job_type=snapshot-build"
                job={latestSnapshotBuildJob}
                label="最新 snapshot-build Job"
              />
              <JobSummaryRow
                emptyLabel="尚无盘前任务。"
                href="/jobs?job_type=run-pre-market"
                job={latestPreMarketJob}
                label="最新盘前 Job"
              />
              <JobSummaryRow
                emptyLabel="尚无盘后任务。"
                href="/jobs?job_type=run-after-close"
                job={latestAfterCloseJob}
                label="最新盘后 Job"
              />
              <JobSummaryRow
                emptyLabel="尚无 strategy-build 任务。"
                href="/jobs?job_type=strategy-build"
                job={latestStrategyBuildJob}
                label="最新 strategy-build Job"
              />
              <JobSummaryRow
                emptyLabel="暂无失败任务。"
                href="/strategies/history?status=failed"
                job={latestFailedJob}
                label={`最近失败任务（${failedJobCount}）`}
              />
            </div>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
