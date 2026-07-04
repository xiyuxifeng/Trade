import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { EmptyState, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { createJob, listJobs } from '@/lib/api/jobs';
import { listBenchmarkOptions } from '@/lib/api/market';
import { listProfiles } from '@/lib/api/profiles';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { formatLocalDateInputOffset } from '@/lib/date';
import type { JobRecord } from '@/types/jobs';
import type { MarketBenchmarkOption } from '@/types/market';
import type { ProfileRecord } from '@/types/profile';
import { describeStrategyWorkspaceJobType, formatWorkspaceTimestamp, isWorkspacePermissionDenied } from './strategy-workspace-utils';

type SubmissionType = 'snapshot-build' | 'run-pre-market';

type StrategyPreMarketPageProps = {
  productMode?: boolean;
  navigationTarget?: string;
};

const DEFAULT_BENCHMARK_SYMBOL = '000300.SH';
const DEFAULT_BENCHMARK_NAME = '沪深300';

type SubmissionState = {
  jobType: SubmissionType;
  jobId: string;
};

function sortJobsByCreatedAtDesc(jobs: JobRecord[]) {
  return [...jobs].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function summarizeJobParams(job: JobRecord) {
  const params = job.params ?? {};
  const profileId = typeof params.profile_id === 'string' ? params.profile_id : null;
  const benchmarkSymbol = typeof params.benchmark_symbol === 'string' ? params.benchmark_symbol : null;
  const date = typeof params.date === 'string' ? params.date : null;
  const startDate = typeof params.start_date === 'string' ? params.start_date : null;
  const endDate = typeof params.end_date === 'string' ? params.end_date : null;
  const asOfDate = typeof params.as_of_date === 'string' ? params.as_of_date : null;

  return [
    profileId ? `画像 ${profileId}` : null,
    benchmarkSymbol ? `基准指数 ${benchmarkSymbol}` : null,
    date ? `日期 ${date}` : null,
    startDate && endDate ? `起始日期 ${startDate} ~ 结束日期 ${endDate}` : null,
    asOfDate ? `分析日期 ${asOfDate}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
}

function getJobErrorMessage() {
  return '任务失败，请稍后重试。';
}

function buildSnapshotParams({
  profileId,
  strategyDate,
  benchmarkSymbol,
  startDate,
  endDate,
  slot,
  snapshotType,
  force,
  offline,
}: {
  profileId: string;
  strategyDate: string;
  benchmarkSymbol: string;
  startDate: string;
  endDate: string;
  slot: string;
  snapshotType: string;
  force: boolean;
  offline: boolean;
}) {
  const resolvedBenchmarkSymbol = benchmarkSymbol.trim() || DEFAULT_BENCHMARK_SYMBOL;
  const params: Record<string, unknown> = {
    profile_id: profileId,
    slot,
    snapshot_type: snapshotType,
    force,
    offline,
    benchmark_symbol: resolvedBenchmarkSymbol,
  };

  if (startDate && endDate) {
    params.start_date = startDate;
    params.end_date = endDate;
  } else {
    params.date = strategyDate;
  }

  return params;
}

function buildRunParams({
  profileId,
  strategyDate,
  benchmarkSymbol,
  force,
  exportHtml,
}: {
  profileId: string;
  strategyDate: string;
  benchmarkSymbol: string;
  force: boolean;
  exportHtml: boolean;
}) {
  const resolvedBenchmarkSymbol = benchmarkSymbol.trim() || DEFAULT_BENCHMARK_SYMBOL;
  const params: Record<string, unknown> = {
    profile_id: profileId,
    as_of_date: strategyDate,
    force,
    export_html: exportHtml,
    benchmark_symbol: resolvedBenchmarkSymbol,
  };

  return params;
}

export function StrategyPreMarketPage({ productMode = false, navigationTarget = '/daily' }: StrategyPreMarketPageProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const today = useMemo(() => formatLocalDateInputOffset(0), []);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [strategyDate, setStrategyDate] = useState(today);
  const [benchmarkSymbol, setBenchmarkSymbol] = useState(DEFAULT_BENCHMARK_SYMBOL);
  const [snapshotStartDate, setSnapshotStartDate] = useState('');
  const [snapshotEndDate, setSnapshotEndDate] = useState('');
  const [snapshotSlot, setSnapshotSlot] = useState('17-30');
  const [snapshotType, setSnapshotType] = useState('all');
  const [snapshotForce, setSnapshotForce] = useState(false);
  const [snapshotOffline, setSnapshotOffline] = useState(false);
  const [runForce, setRunForce] = useState(false);
  const [runExportHtml, setRunExportHtml] = useState(false);
  const [submissionState, setSubmissionState] = useState<SubmissionState | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const profilesQuery = useQuery({
    queryKey: ['strategy-pre-market', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  const benchmarkOptionsQuery = useQuery({
    queryKey: ['strategy-pre-market', 'benchmark-options'],
    queryFn: () => listBenchmarkOptions(50),
    staleTime: 30_000,
  });

  const snapshotJobsQuery = useQuery({
    queryKey: ['strategy-pre-market', 'jobs', 'snapshot-build'],
    queryFn: () => listJobs({ job_type: 'snapshot-build', limit: 10 }),
    staleTime: 15_000,
  });

  const runJobsQuery = useQuery({
    queryKey: ['strategy-pre-market', 'jobs', 'run-pre-market'],
    queryFn: () => listJobs({ job_type: 'run-pre-market', limit: 10 }),
    staleTime: 15_000,
  });

  const profileItems = profilesQuery.data?.items ?? [];
  const benchmarkOptions = useMemo(() => {
    const items = benchmarkOptionsQuery.data?.items ?? [];
    const defaultSymbol = '000300.SH';
    if (items.some((item) => item.symbol === defaultSymbol)) {
      return items;
    }
    if (!benchmarkOptionsQuery.error) {
      return items;
    }
    return [
      {
        symbol: defaultSymbol,
        code: '000300',
        market: 'SH',
        name: DEFAULT_BENCHMARK_NAME,
        security_type: 'index',
      } satisfies MarketBenchmarkOption,
      ...items,
    ];
  }, [benchmarkOptionsQuery.data?.items, benchmarkOptionsQuery.error]);
  const jobs = useMemo(
    () => sortJobsByCreatedAtDesc([...(snapshotJobsQuery.data?.items ?? []), ...(runJobsQuery.data?.items ?? [])]),
    [runJobsQuery.data?.items, snapshotJobsQuery.data?.items],
  );
  useEffect(() => {
    if (!selectedProfileId && profileItems.length > 0) {
      setSelectedProfileId(profileItems[0].profile_id);
      return;
    }
    if (selectedProfileId && !profileItems.some((profile) => profile.profile_id === selectedProfileId)) {
      setSelectedProfileId(profileItems[0]?.profile_id ?? '');
    }
  }, [profileItems, selectedProfileId]);

  const loading = profilesQuery.isLoading || benchmarkOptionsQuery.isLoading || snapshotJobsQuery.isLoading || runJobsQuery.isLoading;
  const error = profilesQuery.error ?? snapshotJobsQuery.error ?? runJobsQuery.error;
  const permissionDenied = isWorkspacePermissionDenied(error);

  const submissionMutation = useMutation({
    mutationFn: async ({
      jobType,
      params,
    }: {
      jobType: SubmissionType;
      params: Record<string, unknown>;
    }) => {
      return createJob({
        job_type: jobType,
        params,
        created_by: 'web',
      });
    },
    onSuccess: async (result, variables) => {
      setSubmissionError(null);
      setSubmissionState({
        jobType: variables.jobType,
        jobId: result.job.id,
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['strategy-pre-market', 'jobs'] }),
        queryClient.invalidateQueries({ queryKey: ['jobs'] }),
      ]);
    },
    onError: (submitError) => {
      const message = submitError instanceof Error ? submitError.message : '盘前任务提交失败';
      setSubmissionError(message);
    },
  });

  const handleSubmitSnapshot = () => {
    if (!selectedProfileId || benchmarkOptions.length === 0) {
      return;
    }
    setSubmissionError(null);
    setSubmissionState(null);
    void submissionMutation.mutateAsync({
      jobType: 'snapshot-build',
      params: buildSnapshotParams({
        profileId: selectedProfileId,
        strategyDate,
        benchmarkSymbol,
        startDate: snapshotStartDate,
        endDate: snapshotEndDate,
        slot: snapshotSlot,
        snapshotType,
        force: snapshotForce,
        offline: snapshotOffline,
      }),
    });
  };

  const handleSubmitRun = () => {
    if (!selectedProfileId || benchmarkOptions.length === 0) {
      return;
    }
    setSubmissionError(null);
    setSubmissionState(null);
    void submissionMutation.mutateAsync({
      jobType: 'run-pre-market',
      params: buildRunParams({
        profileId: selectedProfileId,
        strategyDate,
        benchmarkSymbol,
        force: runForce,
        exportHtml: runExportHtml,
      }),
    });
  };

  if (productMode) {
    const selectedProfile = profileItems.find((profile) => profile.profile_id === selectedProfileId) ?? profileItems[0] ?? null;
    const latestSnapshotJob = snapshotJobsQuery.data?.items?.[0] ?? null;
    const latestRunJob = runJobsQuery.data?.items?.[0] ?? null;
    const hasPartialBenchmarkFallback = Boolean(benchmarkOptionsQuery.error);
    const queryState = loading
      ? 'loading'
      : permissionDenied
        ? 'permission_denied'
        : error
          ? 'error'
          : hasPartialBenchmarkFallback
            ? 'partial'
            : profileItems.length === 0
              ? 'empty'
              : benchmarkOptions.length === 0
                ? 'unavailable'
              : 'ready';

    return (
      <ProductPageAdapter
        title="今日盘前"
        queryState={queryState}
        purpose="根据今日画像、市场上下文和最新盘前结果，整理可执行的盘前分析。"
        inputDescription="需要当前可用画像、执行日期和基准指数。"
        processingDescription="系统会先整理盘前市场数据，再提交今日盘前分析。"
        outputDescription="输出今日盘前分析结果、最近提交状态和下一步操作。"
        input={
          <div className="grid gap-3 md:grid-cols-3">
            <label className="space-y-2 text-sm text-slate-700">
              <span>目标画像</span>
              <Select aria-label="目标画像" value={selectedProfileId} onChange={(event) => setSelectedProfileId(event.target.value)}>
                {profileItems.map((profile: ProfileRecord) => (
                  <option key={profile.profile_id} value={profile.profile_id}>
                    {profile.name}
                  </option>
                ))}
              </Select>
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>执行日期</span>
              <Input aria-label="执行日期" type="date" value={strategyDate} onChange={(event) => setStrategyDate(event.target.value)} />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span>基准指数</span>
              <Select aria-label="基准指数" value={benchmarkSymbol} onChange={(event) => setBenchmarkSymbol(event.target.value)}>
                {benchmarkOptions.map((item: MarketBenchmarkOption) => (
                  <option key={item.symbol} value={item.symbol}>
                    {item.name}
                  </option>
                ))}
              </Select>
            </label>
          </div>
        }
        businessAction={{ label: '开始盘前分析', onClick: handleSubmitRun }}
        stateTitle={hasPartialBenchmarkFallback ? '部分完成' : undefined}
        stateDescription={hasPartialBenchmarkFallback ? '基准指数选项暂时缺失，页面已回退到默认基准。' : undefined}
        impact={hasPartialBenchmarkFallback ? '你仍然可以继续查看和提交盘前分析，但部分基准选项不可见。' : undefined}
        recoveryAction={
          hasPartialBenchmarkFallback
            ? { label: '返回今日总览', to: navigationTarget }
            : queryState !== 'ready'
              ? { label: '返回今日总览', to: navigationTarget }
              : undefined
        }
        result={
          <div className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">目标画像</p>
                <p className="mt-2 text-sm font-medium text-slate-950">{selectedProfile?.name ?? '未选择'}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">执行日期</p>
                <p className="mt-2 text-sm font-medium text-slate-950">{strategyDate || '未选择'}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">基准指数</p>
                <p className="mt-2 text-sm font-medium text-slate-950">
                  {benchmarkOptionsQuery.error
                    ? '默认基准，其他选项暂不可用'
                    : benchmarkOptions.find((item) => item.symbol === benchmarkSymbol)?.name ?? '未选择'}
                </p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <button
                className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-left text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={!selectedProfileId || submissionMutation.isPending}
                onClick={handleSubmitSnapshot}
                type="button"
              >
                整理今日盘前数据
              </button>
              <a
                className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
                href={navigationTarget}
              >
                返回今日总览
              </a>
            </div>

            <div className="space-y-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">最近盘前分析</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {latestRunJob ? <StatusBadge value={latestRunJob.status} /> : <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200">暂无记录</span>}
                  <span className="text-sm text-slate-600">
                    {latestRunJob ? formatWorkspaceTimestamp(latestRunJob.created_at) : '暂无最近结果'}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  {latestRunJob?.result && typeof latestRunJob.result === 'object' && Array.isArray((latestRunJob.result as { summary?: string[] }).summary)
                    ? (latestRunJob.result as { summary?: string[] }).summary!.slice(0, 2).join(' · ')
                    : '提交今日盘前分析后，这里会展示最近结果。'}
                </p>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">最近市场数据整理</p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {latestSnapshotJob ? <StatusBadge value={latestSnapshotJob.status} /> : <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200">暂无记录</span>}
                  <span className="text-sm text-slate-600">
                    {latestSnapshotJob ? formatWorkspaceTimestamp(latestSnapshotJob.created_at) : '暂无最近结果'}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  {latestSnapshotJob?.status === 'success'
                    ? '市场上下文已整理完成。'
                    : latestSnapshotJob?.status === 'failed'
                      ? '市场数据整理失败，请查看影响后重试。'
                      : latestSnapshotJob
                        ? '市场数据正在整理，完成前不会显示为可用。'
                        : '整理今日盘前数据后，这里会展示最近状态。'}
                </p>
              </div>
            </div>
          </div>
        }
      />
    );
  }

  if (loading) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="盘前分析"
          title="盘前分析"
          description="盘前分析页通过画像与市场上下文生成当天的关注建议。"
          actionLabel="返回概览"
          onAction={() => {
            navigate('/daily');
          }}
        />
        <LoadingState label="正在加载盘前分析" description="正在读取画像、盘前任务和最近执行记录。" />
      </main>
    );
  }

  if (error) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="盘前分析"
          title="盘前分析"
          description="盘前分析页通过画像与市场上下文生成当天的关注建议。"
          actionLabel="返回概览"
          onAction={() => {
            navigate('/daily');
          }}
        />
        <ErrorState
          {...buildErrorRecoveryState(error, 'strategy')}
          onRetry={permissionDenied ? undefined : () => void Promise.all([profilesQuery.refetch(), snapshotJobsQuery.refetch(), runJobsQuery.refetch()])}
          actions={[
            { label: '查看任务列表', to: '/system/jobs' },
            { label: '前往配置管理', to: '/profiles' },
          ]}
        />
      </main>
    );
  }

  if (profileItems.length === 0) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="盘前分析"
          title="盘前分析"
          description="盘前分析页通过画像与市场上下文生成当天的关注建议。"
          actionLabel="返回概览"
          onAction={() => {
            navigate('/daily');
          }}
        />
        <EmptyState
          title="暂无可用画像。"
          description="请先导入或创建正式画像，再返回盘前分析页提交盘前准备与盘前分析任务。"
          actionLabel="前往配置管理"
          onAction={() => navigate('/profiles')}
        />
      </main>
    );
  }

  return (
      <main className="page-stack">
        <PageHeader
          kicker="盘前分析"
          title="盘前分析"
          description="盘前分析页通过画像与市场上下文生成当天的关注建议。"
          actionLabel="返回概览"
          onAction={() => {
            navigate('/daily');
        }}
      />

      {submissionError ? (
        <ErrorState
          category="job failed"
          title="盘前任务提交失败"
          description="提交执行任务时返回了错误。"
          suggestion="请先查看错误详情，再确认是否重新提交。"
          detail={submissionError}
          actions={[
            { label: '查看任务列表', to: '/system/jobs' },
            { label: '前往配置管理', to: '/profiles' },
          ]}
        />
      ) : null}

      {submissionState ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <p className="font-medium">
              {submissionState.jobType === 'snapshot-build' ? '市场上下文准备已提交' : '盘前分析已提交'}
          </p>
          <p className="mt-1 break-all">Job ID: {submissionState.jobId}</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Link className="font-medium text-emerald-900 underline underline-offset-4" to={`/system/jobs/${submissionState.jobId}`}>
              查看任务详情
            </Link>
            <Link className="font-medium text-emerald-900 underline underline-offset-4" to="/system/jobs">
              进入任务列表
            </Link>
          </div>
        </div>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
              <Badge variant="info" className="w-fit">
                基础设置
              </Badge>
              <CardTitle className="mt-2 text-slate-950">画像、分析日期和基准指数</CardTitle>
              <CardDescription className="text-slate-600">
              基准指数默认选中沪深300，可在页面下拉中手动切换。
              </CardDescription>
            </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">画像</p>
                <Select aria-label="画像" value={selectedProfileId} onChange={(event) => setSelectedProfileId(event.target.value)}>
                  {profileItems.map((profile: ProfileRecord) => (
                    <option key={profile.profile_id} value={profile.profile_id}>
                      {profile.name} · {profile.profile_id} · v{profile.version}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">分析日期</p>
                <Input aria-label="分析日期" type="date" value={strategyDate} onChange={(event) => setStrategyDate(event.target.value)} />
              </div>
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">基准指数选择</p>
                <Select aria-label="基准指数选择" value={benchmarkSymbol} onChange={(event) => setBenchmarkSymbol(event.target.value)}>
                  {benchmarkOptions.map((item: MarketBenchmarkOption) => (
                    <option key={item.symbol} value={item.symbol}>
                      {item.name} ({item.symbol})
                    </option>
                  ))}
                </Select>
                <p className="text-xs text-slate-500">页面默认选中沪深300；如需其他口径，可在这里切换。</p>
                {benchmarkOptionsQuery.isError ? (
                  <p className="text-xs text-amber-600">基准指数选项加载失败，当前回退到默认沪深300。</p>
                ) : null}
              </div>
            </div>

          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              流程入口
            </Badge>
            <CardTitle className="mt-2 text-slate-950">市场上下文准备与任务中心</CardTitle>
            <CardDescription className="text-slate-600">执行结果、日志、产物和失败重试都在任务列表和任务详情查看。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Link className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70" to="/system/jobs">
              <p className="text-sm font-medium text-slate-950">进入任务列表</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">查看所有任务、日志、产物与重试。</p>
            </Link>
            <Link
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70"
              to="/system/jobs?job_type=snapshot-build"
            >
              <p className="text-sm font-medium text-slate-950">查看市场上下文准备</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">只看最近的市场上下文准备任务。</p>
            </Link>
            <Link
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70"
              to="/system/jobs?job_type=run-pre-market"
            >
              <p className="text-sm font-medium text-slate-950">查看盘前分析</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">只看最近的盘前分析任务。</p>
            </Link>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              市场上下文准备
            </Badge>
            <CardTitle className="mt-2 text-slate-950">提交市场上下文准备</CardTitle>
            <CardDescription className="text-slate-600">
              分析日期、起始日期、结束日期、时段、快照类型、强制、离线都可直接提交。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-700">
                <span>起始日期</span>
                <Input aria-label="起始日期" type="date" value={snapshotStartDate} onChange={(event) => setSnapshotStartDate(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>结束日期</span>
                <Input aria-label="结束日期" type="date" value={snapshotEndDate} onChange={(event) => setSnapshotEndDate(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>时段</span>
                <Input aria-label="时段" value={snapshotSlot} onChange={(event) => setSnapshotSlot(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>快照类型</span>
                <Select aria-label="快照类型" value={snapshotType} onChange={(event) => setSnapshotType(event.target.value)}>
                  <option value="all">全量</option>
                  <option value="hot_topics">热点主题</option>
                  <option value="topic_constituents">主题成分</option>
                  <option value="strong_symbols">强势标的</option>
                </Select>
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="强制提交"
                  checked={snapshotForce}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  type="checkbox"
                  onChange={(event) => setSnapshotForce(event.target.checked)}
                />
                <span>强制</span>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="离线模式"
                  checked={snapshotOffline}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  type="checkbox"
                  onChange={(event) => setSnapshotOffline(event.target.checked)}
                />
                <span>离线</span>
              </label>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              该动作会默认使用当前“分析日期”，如果“起始日期”和“结束日期”同时填写则优先提交区间市场上下文准备。
            </div>

            <Button
              className="w-full bg-sky-500 text-slate-950 hover:bg-sky-400"
              disabled={!selectedProfileId || submissionMutation.isPending}
              onClick={handleSubmitSnapshot}
            >
              {submissionMutation.isPending ? '提交中' : '提交市场上下文准备'}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              市场上下文准备
            </Badge>
            <CardTitle className="mt-2 text-slate-950">提交盘前分析</CardTitle>
            <CardDescription className="text-slate-600">分析日期、强制、导出网页为盘前分析的正式参数。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">分析日期</p>
              <p className="mt-2 break-all text-base font-semibold text-slate-950">{strategyDate || '未选择'}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">盘前分析默认采用当前的分析日期。</p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="强制执行"
                  checked={runForce}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  type="checkbox"
                  onChange={(event) => setRunForce(event.target.checked)}
                />
                <span>强制</span>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="导出网页"
                  checked={runExportHtml}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  type="checkbox"
                  onChange={(event) => setRunExportHtml(event.target.checked)}
                />
                <span>导出网页</span>
              </label>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              提交后会生成盘前日报结果，执行状态、日志与产物继续在任务列表和任务详情中查看。
            </div>

            <Button
              className="w-full bg-sky-500 text-slate-950 hover:bg-sky-400"
              disabled={!selectedProfileId || submissionMutation.isPending}
              onClick={handleSubmitRun}
            >
              {submissionMutation.isPending ? '提交中' : '提交盘前分析'}
            </Button>
          </CardContent>
        </Card>
      </section>

        <SectionCard
        title="最近任务"
        description="这里只展示与盘前分析相关的最近任务，详细日志、产物和失败重试都以任务列表为准。"
      >
        {jobs.length ? (
          <div className="grid gap-3">
            {jobs.slice(0, 8).map((job) => (
              <Link
                key={job.id}
                className="rounded-2xl border border-slate-200 bg-white p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70"
                to={`/system/jobs/${job.id}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-base font-medium text-slate-950">{job.id}</p>
                    <p className="mt-1 text-sm text-slate-600">{describeStrategyWorkspaceJobType(job.job_type)}</p>
                  </div>
                  <StatusBadge value={job.status} />
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span className="rounded-full border border-slate-200 px-2 py-1">{summarizeJobParams(job) || '参数待查看'}</span>
                  <span className="rounded-full border border-slate-200 px-2 py-1">创建于 {formatWorkspaceTimestamp(job.created_at)}</span>
                </div>
                {job.error ? (
                  <p className="mt-3 text-sm text-rose-700">
                    {getJobErrorMessage()}
                  </p>
                ) : null}
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="暂无盘前任务。"
            description="提交市场上下文准备或盘前分析后，这里会显示最近任务。"
            actionLabel="查看任务列表"
            onAction={() => {
              navigate('/system/jobs');
            }}
          />
        )}
      </SectionCard>
    </main>
  );
}
