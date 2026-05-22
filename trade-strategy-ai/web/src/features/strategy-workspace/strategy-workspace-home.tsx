import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, ErrorState, LoadingState, StatusBadge } from '@/components/kit';
import { listProfiles } from '@/lib/api/profiles';
import { listJobs } from '@/lib/api/jobs';
import { listStrategyVersions } from '@/lib/api/strategyStudio';
import { listOptimizeVersions } from '@/lib/api/optimize';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { formatLocalDateInputOffset } from '@/lib/date';
import { isWorkspacePermissionDenied } from './strategy-workspace-utils';
import type { JobRecord } from '@/types/jobs';
import type { ProfileRecord } from '@/types/profile';
import type { OptimizeVersionSummaryItem } from '@/types/optimize';
import type { StrategyVersionSummaryItem } from '@/types/strategyStudio';

const JOB_TYPES = {
  preMarket: 'run-pre-market',
  afterClose: 'run-after-close',
  strategyBuild: 'strategy-build',
} as const;

type QuickLink = {
  label: string;
  to: string;
  description: string;
};

function sortJobsByCreatedAtDesc(items: JobRecord[]) {
  return [...items].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function sortVersionsByStrategyDateDesc(items: Array<StrategyVersionSummaryItem | OptimizeVersionSummaryItem>) {
  return [...items].sort((left, right) => {
    const leftKey = `${left.strategy_date ?? ''} ${left.released_at ?? ''} ${left.version_id}`;
    const rightKey = `${right.strategy_date ?? ''} ${right.released_at ?? ''} ${right.version_id}`;
    return rightKey.localeCompare(leftKey);
  });
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

export function StrategyWorkspaceHomePage() {
  const navigate = useNavigate();
  const today = formatLocalDateInputOffset(0);
  const [selectedProfileId, setSelectedProfileId] = useState('');

  const profilesQuery = useQuery({
    queryKey: ['strategy-home', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  const profileItems = profilesQuery.data?.items ?? [];

  useEffect(() => {
    if (!selectedProfileId && profileItems.length > 0) {
      setSelectedProfileId(profileItems[0].profile_id);
    }
  }, [profileItems, selectedProfileId]);

  useEffect(() => {
    if (selectedProfileId && !profileItems.some((profile) => profile.profile_id === selectedProfileId)) {
      setSelectedProfileId(profileItems[0]?.profile_id ?? '');
    }
  }, [profileItems, selectedProfileId]);

  const selectedProfile = useMemo(
    () => profileItems.find((profile) => profile.profile_id === selectedProfileId) ?? null,
    [profileItems, selectedProfileId],
  );

  const latestProfileLabel = selectedProfile
    ? `${selectedProfile.name} · ${selectedProfile.profile_id}`
    : '未选择';

  const latestProfileDetail = selectedProfile
    ? `环境 ${selectedProfile.environment} · v${selectedProfile.version} · 更新于 ${new Intl.DateTimeFormat('zh-CN', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(selectedProfile.updated_at))}`
    : '请先选择可用 Profile';

  const preMarketJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', JOB_TYPES.preMarket],
    queryFn: () => listJobs({ job_type: JOB_TYPES.preMarket, limit: 5 }),
    staleTime: 30_000,
  });

  const afterCloseJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', JOB_TYPES.afterClose],
    queryFn: () => listJobs({ job_type: JOB_TYPES.afterClose, limit: 5 }),
    staleTime: 30_000,
  });

  const strategyBuildJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', JOB_TYPES.strategyBuild],
    queryFn: () => listJobs({ job_type: JOB_TYPES.strategyBuild, limit: 5 }),
    staleTime: 30_000,
  });

  const failedJobsQuery = useQuery({
    queryKey: ['strategy-home', 'jobs', 'failed'],
    queryFn: () => listJobs({ status: 'failed', limit: 5 }),
    staleTime: 30_000,
  });

  const strategyVersionsQuery = useQuery({
    queryKey: ['strategy-home', 'strategy-versions'],
    queryFn: () => listStrategyVersions({ limit: 5 }),
    staleTime: 30_000,
  });

  const candidateVersionsQuery = useQuery({
    queryKey: ['strategy-home', 'candidate-versions'],
    queryFn: () => listOptimizeVersions({ version_type: 'candidate', limit: 5 }),
    staleTime: 30_000,
  });

  const queryError =
    profilesQuery.error ??
    preMarketJobsQuery.error ??
    afterCloseJobsQuery.error ??
    strategyBuildJobsQuery.error ??
    failedJobsQuery.error ??
    strategyVersionsQuery.error ??
    candidateVersionsQuery.error;
  const permissionDenied = isWorkspacePermissionDenied(queryError);

  const isLoading =
    profilesQuery.isLoading ||
    preMarketJobsQuery.isLoading ||
    afterCloseJobsQuery.isLoading ||
    strategyBuildJobsQuery.isLoading ||
    failedJobsQuery.isLoading ||
    strategyVersionsQuery.isLoading ||
    candidateVersionsQuery.isLoading;

  const profileCount = profileItems.length;
  const failedJobCount = failedJobsQuery.data?.total ?? 0;
  const latestPreMarketJob = sortJobsByCreatedAtDesc(preMarketJobsQuery.data?.items ?? [])[0] ?? null;
  const latestAfterCloseJob = sortJobsByCreatedAtDesc(afterCloseJobsQuery.data?.items ?? [])[0] ?? null;
  const latestStrategyBuildJob = sortJobsByCreatedAtDesc(strategyBuildJobsQuery.data?.items ?? [])[0] ?? null;
  const latestFailedJob = sortJobsByCreatedAtDesc(failedJobsQuery.data?.items ?? [])[0] ?? null;
  const latestStrategyVersion = sortVersionsByStrategyDateDesc(strategyVersionsQuery.data?.items ?? [])[0] ?? null;
  const latestCandidateVersion = sortVersionsByStrategyDateDesc(candidateVersionsQuery.data?.items ?? [])[0] ?? null;

  const quickLinks: QuickLink[] = [
    { label: '盘前准备', to: '/strategies/pre-market', description: '构建候选池快照并运行盘前' },
    { label: '盘后复盘', to: '/strategies/after-close', description: '查看盘后结果、归因和产物' },
    { label: '构建策略版本', to: '/strategies/versions', description: '提交 strategy-build 并查看版本结果' },
    { label: '候选版本', to: '/strategies/candidates', description: '生成与审核候选版本' },
    { label: '规则选择', to: '/strategies/regime-selection', description: '查看策略规则选择与适用性' },
    { label: '运行历史', to: '/strategies/history', description: '查看最近策略执行历史' },
    { label: '任务中心', to: '/jobs', description: '查看任务状态、日志、产物与重试' },
  ];

  if (isLoading) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="策略工作台"
          description="策略首页只展示状态摘要和入口，不承担任务中心职责。"
        />
        <LoadingState label="正在加载策略摘要" description="正在读取 Profile、策略版本和最近任务。" />
      </main>
    );
  }

  if (queryError) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="策略工作台"
          description="策略首页只展示状态摘要和入口，不承担任务中心职责。"
        />
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'strategy')}
          onRetry={permissionDenied ? undefined : () => {
            void profilesQuery.refetch();
            void preMarketJobsQuery.refetch();
            void afterCloseJobsQuery.refetch();
            void strategyBuildJobsQuery.refetch();
            void failedJobsQuery.refetch();
            void strategyVersionsQuery.refetch();
            void candidateVersionsQuery.refetch();
          }}
          actions={[
            { label: '进入任务中心', to: '/jobs' },
            { label: '前往配置管理', to: '/profiles' },
          ]}
        />
      </main>
    );
  }

  if (profileCount === 0) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="策略工作台"
          description="策略首页只展示状态摘要和入口，不承担任务中心职责。"
        />
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
      <PageHeader
        kicker="策略"
        title="策略工作台"
        description="策略首页只展示状态摘要和入口，不承担任务中心职责。"
      />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              今日策略状态
            </Badge>
            <CardTitle className="mt-2 text-slate-950">Profile / 日期 / 关键状态</CardTitle>
            <CardDescription className="text-slate-600">
              首页只做状态摘要，所有执行动作都进入对应工作台或任务中心。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Profile</p>
                <Select aria-label="Profile" value={selectedProfileId} onChange={(event) => setSelectedProfileId(event.target.value)}>
                  {profileItems.map((profile) => (
                    <option key={profile.profile_id} value={profile.profile_id}>
                      {profile.name} · {profile.profile_id} · v{profile.version}
                    </option>
                  ))}
                </Select>
              </div>
              <SummaryTile
                detail={latestProfileDetail}
                label="当前 Profile"
                status={selectedProfile?.validation_status ?? 'validated'}
                value={latestProfileLabel}
              />
              <SummaryTile
                detail="默认使用当前日期作为策略首页的展示日期。"
                label="策略日期"
                value={today}
              />
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <SummaryTile
                detail={latestPreMarketJob ? `${latestPreMarketJob.id} · ${formatJobTime(latestPreMarketJob)}` : '尚无盘前执行记录。'}
                label="盘前状态"
                status={latestPreMarketJob?.status ?? 'pending'}
                value={latestPreMarketJob ? latestPreMarketJob.status : '暂无'}
              />
              <SummaryTile
                detail={latestAfterCloseJob ? `${latestAfterCloseJob.id} · ${formatJobTime(latestAfterCloseJob)}` : '尚无盘后执行记录。'}
                label="盘后状态"
                status={latestAfterCloseJob?.status ?? 'pending'}
                value={latestAfterCloseJob ? latestAfterCloseJob.status : '暂无'}
              />
              <SummaryTile
                detail={latestStrategyBuildJob ? `${latestStrategyBuildJob.id} · ${formatJobTime(latestStrategyBuildJob)}` : '尚无 strategy-build 记录。'}
                label="策略版本状态"
                status={latestStrategyBuildJob?.status ?? 'draft'}
                value={latestStrategyVersion ? `${latestStrategyVersion.version_id}` : '暂无版本'}
              />
              <SummaryTile
                detail={latestCandidateVersion ? `${latestCandidateVersion.version_id} · ${latestCandidateVersion.strategy_date}` : '尚无候选版本。'}
                label="候选版本状态"
                status={latestCandidateVersion?.status ?? 'draft'}
                value={latestCandidateVersion ? latestCandidateVersion.version_id : '暂无候选'}
              />
              <SummaryTile
                detail="跳转到任务中心查看失败原因、日志和重试。"
                label="最近失败任务"
                value={String(failedJobCount)}
              />
              <SummaryTile
                detail="策略首页只展示摘要，不承担任务中心职责。"
                label="任务中心"
                value="进入 /jobs"
              />
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              快捷入口
            </Badge>
            <CardTitle className="mt-2 text-slate-950">工作台入口</CardTitle>
            <CardDescription className="text-slate-600">
              这些入口会把用户带到对应的策略子页面或任务中心。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {quickLinks.map((item) => (
                <Link
                  key={item.label}
                  className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70"
                  to={item.to}
                >
                  <p className="text-sm font-medium text-slate-950">{item.label}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{item.description}</p>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <Card className="border-slate-200 bg-white shadow-sm xl:col-span-2">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              任务中心摘要
            </Badge>
            <CardTitle className="mt-2 text-slate-950">最近关键 Job</CardTitle>
            <CardDescription className="text-slate-600">
              这里仅展示摘要，详细日志、产物和失败重试仍归任务中心。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
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
              emptyLabel="暂无失败任务。"
              href="/jobs?status=failed"
              job={latestFailedJob}
              label={`最近失败任务（${failedJobCount}）`}
            />
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              版本概览
            </Badge>
            <CardTitle className="mt-2 text-slate-950">最新版本与候选</CardTitle>
            <CardDescription className="text-slate-600">展示最新策略版本与候选版本的整体状态。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">最新策略版本</p>
              <p className="mt-2 break-all text-sm font-semibold text-slate-950">{latestStrategyVersion?.version_id ?? '暂无版本'}</p>
              <p className="mt-1 text-sm text-slate-600">
                {latestStrategyVersion ? `${latestStrategyVersion.strategy_date} · ${latestStrategyVersion.version_type}` : '等待 strategy-build。'}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">最新候选版本</p>
              <p className="mt-2 break-all text-sm font-semibold text-slate-950">{latestCandidateVersion?.version_id ?? '暂无候选'}</p>
              <p className="mt-1 text-sm text-slate-600">
                {latestCandidateVersion ? `${latestCandidateVersion.strategy_date} · ${latestCandidateVersion.version_type}` : '等待候选版本生成。'}
              </p>
            </div>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}

function formatJobTime(job: JobRecord) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(job.created_at));
}
