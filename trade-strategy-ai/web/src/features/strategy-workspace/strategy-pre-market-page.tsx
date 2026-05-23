import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
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
import { formatWorkspaceTimestamp, isWorkspacePermissionDenied } from './strategy-workspace-utils';

type SubmissionType = 'snapshot-build' | 'run-pre-market';

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
    profileId ? `profile ${profileId}` : null,
    benchmarkSymbol ? `benchmark ${benchmarkSymbol}` : null,
    date ? `date ${date}` : null,
    startDate && endDate ? `${startDate} ~ ${endDate}` : null,
    asOfDate ? `as_of ${asOfDate}` : null,
  ]
    .filter(Boolean)
    .join(' · ');
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
  const params: Record<string, unknown> = {
    profile_id: profileId,
    slot,
    snapshot_type: snapshotType,
    force,
    offline,
  };

  if (benchmarkSymbol.trim()) {
    params.benchmark_symbol = benchmarkSymbol.trim();
  }

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
  const params: Record<string, unknown> = {
    profile_id: profileId,
    as_of_date: strategyDate,
    force,
    export_html: exportHtml,
  };

  if (benchmarkSymbol.trim()) {
    params.benchmark_symbol = benchmarkSymbol.trim();
  }

  return params;
}

export function StrategyPreMarketPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const today = useMemo(() => formatLocalDateInputOffset(0), []);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [strategyDate, setStrategyDate] = useState(today);
  const [benchmarkSymbol, setBenchmarkSymbol] = useState('');
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
  }, [benchmarkOptionsQuery.data?.items]);
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

  const loading = profilesQuery.isLoading || snapshotJobsQuery.isLoading || runJobsQuery.isLoading;
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
    if (!selectedProfileId) {
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
    if (!selectedProfileId) {
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

  if (loading) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="盘前准备"
          description="盘前准备页通过 Profile 与快照构建、盘前运行承接正式提交。"
          actionLabel="返回策略工作台"
          onAction={() => {
            navigate('/strategies');
          }}
        />
        <LoadingState label="正在加载盘前准备" description="正在读取 Profile、盘前任务和最近执行记录。" />
      </main>
    );
  }

  if (error) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="盘前准备"
          description="盘前准备页通过 Profile 与快照构建、盘前运行承接正式提交。"
          actionLabel="返回策略工作台"
          onAction={() => {
            navigate('/strategies');
          }}
        />
        <ErrorState
          {...buildErrorRecoveryState(error, 'strategy')}
          onRetry={permissionDenied ? undefined : () => void Promise.all([profilesQuery.refetch(), snapshotJobsQuery.refetch(), runJobsQuery.refetch()])}
          actions={[
            { label: '查看任务列表', to: '/jobs' },
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
          kicker="策略"
          title="盘前准备"
          description="盘前准备页通过 Profile 与快照构建、盘前运行承接正式提交。"
          actionLabel="返回策略工作台"
          onAction={() => {
            navigate('/strategies');
          }}
        />
        <EmptyState
          title="暂无可用 Profile。"
          description="请先导入或创建正式 Profile，再返回盘前准备页提交 snapshot-build 与 run-pre-market。"
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
        title="盘前准备"
        description="盘前准备页通过 Profile 与快照构建、盘前运行承接正式提交。"
        actionLabel="返回策略工作台"
        onAction={() => {
          navigate('/strategies');
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
            { label: '查看任务列表', to: '/jobs' },
            { label: '前往配置管理', to: '/profiles' },
          ]}
        />
      ) : null}

      {submissionState ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <p className="font-medium">
            {submissionState.jobType === 'snapshot-build' ? '快照构建已提交' : '盘前运行已提交'}
          </p>
          <p className="mt-1 break-all">Job ID: {submissionState.jobId}</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Link className="font-medium text-emerald-900 underline underline-offset-4" to={`/jobs/${submissionState.jobId}`}>
              查看任务详情
            </Link>
            <Link className="font-medium text-emerald-900 underline underline-offset-4" to="/jobs">
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
            <CardTitle className="mt-2 text-slate-950">Profile / 策略日期 / Benchmark</CardTitle>
            <CardDescription className="text-slate-600">
              `benchmark_symbol` 为空时会由后端按 Profile 默认值补齐，Web 只保留 Profile 入口。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Profile</p>
                <Select aria-label="Profile" value={selectedProfileId} onChange={(event) => setSelectedProfileId(event.target.value)}>
                  {profileItems.map((profile: ProfileRecord) => (
                    <option key={profile.profile_id} value={profile.profile_id}>
                      {profile.name} · {profile.profile_id} · v{profile.version}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Strategy date</p>
                <Input aria-label="Strategy date" type="date" value={strategyDate} onChange={(event) => setStrategyDate(event.target.value)} />
              </div>
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Benchmark 选择</p>
                <Select aria-label="Benchmark 选择" value={benchmarkSymbol} onChange={(event) => setBenchmarkSymbol(event.target.value)}>
                  <option value="">自动从 Profile 读取</option>
                  {benchmarkOptions.map((item: MarketBenchmarkOption) => (
                    <option key={item.symbol} value={item.symbol}>
                      {item.name} ({item.symbol})
                    </option>
                  ))}
                </Select>
                <p className="text-xs text-slate-500">可手动选择指数基准；留空时由后端按 Profile 默认值补齐。</p>
                {benchmarkOptionsQuery.isError ? (
                  <p className="text-xs text-amber-600">Benchmark 选项加载失败，当前回退到默认沪深300。</p>
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
            <CardTitle className="mt-2 text-slate-950">快照构建与 Job 工作台</CardTitle>
            <CardDescription className="text-slate-600">执行结果、日志、产物和失败重试都在任务列表和任务详情查看。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <Link className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70" to="/jobs">
              <p className="text-sm font-medium text-slate-950">进入任务列表</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">查看所有任务、日志、产物与重试。</p>
            </Link>
            <Link
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70"
              to="/jobs?job_type=snapshot-build"
            >
              <p className="text-sm font-medium text-slate-950">查看 snapshot-build</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">只看最近的快照构建任务。</p>
            </Link>
            <Link
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70"
              to="/jobs?job_type=run-pre-market"
            >
              <p className="text-sm font-medium text-slate-950">查看 run-pre-market</p>
              <p className="mt-1 text-sm leading-6 text-slate-600">只看最近的盘前运行任务。</p>
            </Link>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              snapshot-build
            </Badge>
            <CardTitle className="mt-2 text-slate-950">提交快照构建</CardTitle>
            <CardDescription className="text-slate-600">
              `date / start_date / end_date / slot / snapshot_type / force / offline` 都可直接提交。
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-700">
                <span>Start date</span>
                <Input aria-label="Snapshot start date" type="date" value={snapshotStartDate} onChange={(event) => setSnapshotStartDate(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>End date</span>
                <Input aria-label="Snapshot end date" type="date" value={snapshotEndDate} onChange={(event) => setSnapshotEndDate(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>Slot</span>
                <Input aria-label="Snapshot slot" value={snapshotSlot} onChange={(event) => setSnapshotSlot(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>Snapshot type</span>
                <Select aria-label="Snapshot type" value={snapshotType} onChange={(event) => setSnapshotType(event.target.value)}>
                  <option value="all">all</option>
                  <option value="hot_topics">hot_topics</option>
                  <option value="topic_constituents">topic_constituents</option>
                  <option value="strong_symbols">strong_symbols</option>
                </Select>
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="Snapshot force"
                  checked={snapshotForce}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  type="checkbox"
                  onChange={(event) => setSnapshotForce(event.target.checked)}
                />
                <span>Force</span>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="Snapshot offline"
                  checked={snapshotOffline}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  type="checkbox"
                  onChange={(event) => setSnapshotOffline(event.target.checked)}
                />
                <span>Offline</span>
              </label>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              该动作会默认使用当前 `Strategy date`，如果 `Start date` 和 `End date` 同时填写则优先提交区间快照。
            </div>

            <Button
              className="w-full bg-sky-500 text-slate-950 hover:bg-sky-400"
              disabled={!selectedProfileId || submissionMutation.isPending}
              onClick={handleSubmitSnapshot}
            >
              {submissionMutation.isPending ? '提交中' : '提交快照构建'}
            </Button>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              run-pre-market
            </Badge>
            <CardTitle className="mt-2 text-slate-950">提交盘前运行</CardTitle>
            <CardDescription className="text-slate-600">`as_of_date / force / export_html` 为盘前运行的正式参数。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">as_of_date</p>
              <p className="mt-2 break-all text-base font-semibold text-slate-950">{strategyDate || '未选择'}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">盘前运行默认采用当前的 Strategy date。</p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="Run force"
                  checked={runForce}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  type="checkbox"
                  onChange={(event) => setRunForce(event.target.checked)}
                />
                <span>Force</span>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  aria-label="Export HTML"
                  checked={runExportHtml}
                  className="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-400"
                  type="checkbox"
                  onChange={(event) => setRunExportHtml(event.target.checked)}
                />
                <span>Export HTML</span>
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
              {submissionMutation.isPending ? '提交中' : '提交盘前运行'}
            </Button>
          </CardContent>
        </Card>
      </section>

      <SectionCard
        title="最近任务"
        description="这里只展示与盘前相关的最近任务，详细日志、产物和失败重试都以任务列表为准。"
      >
        {jobs.length ? (
          <div className="grid gap-3">
            {jobs.slice(0, 8).map((job) => (
              <Link
                key={job.id}
                className="rounded-2xl border border-slate-200 bg-white p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70"
                to={`/jobs/${job.id}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-base font-medium text-slate-950">{job.id}</p>
                    <p className="mt-1 text-sm text-slate-600">{job.job_type}</p>
                  </div>
                  <StatusBadge value={job.status} />
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span className="rounded-full border border-slate-200 px-2 py-1">{summarizeJobParams(job) || '参数待查看'}</span>
                  <span className="rounded-full border border-slate-200 px-2 py-1">创建于 {formatWorkspaceTimestamp(job.created_at)}</span>
                </div>
                {job.error ? (
                  <p className="mt-3 text-sm text-rose-700">
                    {typeof job.error === 'string' ? job.error : job.error.message ?? '任务失败'}
                  </p>
                ) : null}
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState
            title="暂无盘前任务。"
            description="提交 snapshot-build 或 run-pre-market 后，这里会显示最近任务。"
            actionLabel="查看任务列表"
            onAction={() => {
              navigate('/jobs');
            }}
          />
        )}
      </SectionCard>
    </main>
  );
}
