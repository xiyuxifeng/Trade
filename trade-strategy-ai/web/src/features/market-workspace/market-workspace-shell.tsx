import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { PageHeader } from '@/components/layout/page-header';
import { ErrorState } from '@/components/state/ErrorState';
import { formatLocalDateInputOffset } from '@/lib/date';
import { createJob, listJobs } from '@/lib/api/jobs';
import { listArtifacts } from '@/lib/api/artifacts';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import type { JobRecord } from '@/types/jobs';
import { MarketWorkspaceSummary } from './market-workspace-summary';
import { MarketWorkspaceRunners, type MarketWorkspaceRunner } from './market-workspace-runners';
import { MarketWorkspaceRecentJobs } from './market-workspace-recent-jobs';
import { MarketWorkspaceErrors } from './market-workspace-errors';
import { MarketWorkspaceArtifacts } from './market-workspace-artifacts';

const RUNTIME_JOB_TYPES = new Set([
  'kaipan-fetch',
  'kaipan-normalize',
  'kaipan-run',
  'ohlcv-crawl',
  'market-state-build',
  'snapshot-build',
]);

const RUNNERS: MarketWorkspaceRunner[] = [
  {
    jobType: 'kaipan-fetch',
    title: 'Kaipan 抓取',
    description: '抓取指定交易日的 Kaipan 原始数据。',
    badge: '抓取',
  },
  {
    jobType: 'kaipan-normalize',
    title: 'Kaipan 归一化',
    description: '把抓取结果整理成统一的市场数据输入。',
    badge: '清洗',
  },
  {
    jobType: 'kaipan-run',
    title: 'Kaipan 一键运行',
    description: '一次性构建抓取计划或启动调度器。',
    badge: '调度',
  },
  {
    jobType: 'ohlcv-crawl',
    title: 'OHLCV 抓取',
    description: '抓取标的的日线历史数据，供市场浏览和回溯使用。',
    badge: '行情',
  },
  {
    jobType: 'market-state-build',
    title: '市场状态构建',
    description: '生成当天的 Market State 快照。',
    badge: '状态',
  },
  {
    jobType: 'snapshot-build',
    title: '快照构建',
    description: '构建结构化 Market Snapshot，并输出 summary / quality report。',
    badge: '快照',
  },
];

function buildJobParams(jobType: string, form: WorkspaceFormState) {
  const symbols = form.symbols
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);

  const base = {
    config_path: form.configPath,
    trade_date: form.tradeDate,
    slot: form.slot,
  };

  if (jobType === 'kaipan-fetch' || jobType === 'kaipan-normalize') {
    return base;
  }

  if (jobType === 'kaipan-run') {
    return {
      ...base,
      mode: form.mode,
      symbols,
      start_date: form.startDate,
      end_date: form.endDate,
      limit: form.limit,
      date: form.snapshotDate,
      as_of: form.asOf,
      dest: form.dest,
      from_akshare: form.fromAkshare,
      cache_csv: form.cacheCsv,
      snapshot_type: form.snapshotType,
      force: form.force,
      offline: form.offline,
      start_scheduler: form.startScheduler,
      block: form.block,
    };
  }

  if (jobType === 'ohlcv-crawl') {
    return {
      config_path: form.configPath,
      mode: form.mode,
      symbols,
      start_date: form.startDate,
      end_date: form.endDate,
      limit: form.limit,
    };
  }

  if (jobType === 'market-state-build') {
    return {
      config_path: form.configPath,
      as_of: form.asOf,
      dest: form.dest,
      from_akshare: form.fromAkshare,
      cache_csv: form.cacheCsv,
    };
  }

  return {
    config_path: form.configPath,
    date: form.snapshotDate,
    start_date: form.startDate,
    end_date: form.endDate,
    slot: form.slot,
    snapshot_type: form.snapshotType,
    force: form.force,
    offline: form.offline,
  };
}

function formatDate(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function classifyJobError(job: JobRecord) {
  const error = job.error;
  const rawType = typeof error === 'string' ? '' : error?.type ?? '';
  const rawMessage = typeof error === 'string' ? error : error?.message ?? '';
  const text = `${rawType} ${rawMessage}`.toLowerCase();
  if (text.includes('permission') || text.includes('config')) return '配置错误';
  if (text.includes('provider') || text.includes('api') || text.includes('kaipan')) return 'provider 错误';
  if (text.includes('data') || text.includes('empty') || text.includes('missing')) return '数据错误';
  return '系统错误';
}

type WorkspaceFormState = {
  configPath: string;
  tradeDate: string;
  slot: string;
  mode: string;
  snapshotDate: string;
  startDate: string;
  endDate: string;
  asOf: string;
  dest: string;
  symbols: string;
  limit: number;
  snapshotType: string;
  force: boolean;
  offline: boolean;
  fromAkshare: boolean;
  cacheCsv: boolean;
  startScheduler: boolean;
  block: boolean;
};

export function MarketWorkspaceShell() {
  const [form, setForm] = useState<WorkspaceFormState>({
    configPath: 'config/app.yaml',
    tradeDate: formatLocalDateInputOffset(0),
    slot: '17-30',
    mode: 'incremental',
    snapshotDate: formatLocalDateInputOffset(0),
    startDate: formatLocalDateInputOffset(-30),
    endDate: formatLocalDateInputOffset(0),
    asOf: formatLocalDateInputOffset(0),
    dest: 'data/processed/persona/market_state.json',
    symbols: '',
    limit: 100,
    snapshotType: 'all',
    force: false,
    offline: false,
    fromAkshare: false,
    cacheCsv: true,
    startScheduler: false,
    block: false,
  });
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [submissionJobId, setSubmissionJobId] = useState<string | null>(null);
  const [submittingJobType, setSubmittingJobType] = useState<string | null>(null);

  const jobsQuery = useQuery({
    queryKey: ['market-workspace-jobs'],
    queryFn: () => listJobs({ limit: 20 }),
    staleTime: 30_000,
  });

  const artifactsQuery = useQuery({
    queryKey: ['market-workspace-artifacts'],
    queryFn: () => listArtifacts({ limit: 12 }),
    staleTime: 30_000,
  });

  const runMutation = useMutation({
    mutationFn: async (jobType: string) => {
      setSubmittingJobType(jobType);
      return createJob({
        job_type: jobType,
        created_by: 'web',
        params: buildJobParams(jobType, form),
      });
    },
    onSuccess: (result, jobType) => {
      setSubmissionJobId(result.job.id);
      setSubmissionMessage(`已提交 ${jobType}，可打开 Job 详情查看进度。`);
    },
    onSettled: () => {
      setSubmittingJobType(null);
    },
  });

  const marketJobs = useMemo(
    () => (jobsQuery.data?.items ?? []).filter((job) => RUNTIME_JOB_TYPES.has(job.job_type)),
    [jobsQuery.data?.items],
  );
  const failedJobs = useMemo(() => marketJobs.filter((job) => job.status === 'failed'), [marketJobs]);
  const artifacts = artifactsQuery.data?.items ?? [];
  const jobsError = jobsQuery.error ? buildErrorRecoveryState(jobsQuery.error, 'market') : null;
  const artifactsError = artifactsQuery.error ? buildErrorRecoveryState(artifactsQuery.error, 'market') : null;

  const updateForm = (patch: Partial<WorkspaceFormState>) => {
    setForm((current) => ({ ...current, ...patch }));
  };

  return (
    <main className="page-stack">
      <PageHeader
        kicker="市场数据"
        title="市场数据工作台"
        description="在 Web 中运行和查看市场数据链路，保持与正式交付版一致的浅色中文工作台风格。"
      />

      {submissionMessage ? (
        <Card className="border-sky-200 bg-sky-50 text-sky-900 shadow-sm">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <p className="font-medium">{submissionMessage}</p>
              <p className="text-sm text-sky-700">任务已通过 Job Center 创建，不需要 CLI。</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {submissionJobId ? (
                <a
                  className="inline-flex h-10 items-center justify-center rounded-lg border border-sky-200 bg-white px-4 text-sm font-medium text-sky-800 transition-colors hover:bg-sky-50"
                  href={`/jobs/${submissionJobId}`}
                >
                  打开 Job 详情
                </a>
              ) : null}
              <Button variant="outline" className="border-sky-200 bg-white text-sky-800 hover:bg-sky-50" onClick={() => setSubmissionMessage(null)}>
                关闭
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <MarketWorkspaceSummary
        taskCount={RUNNERS.length}
        recentJobCount={marketJobs.length}
        failedJobCount={failedJobs.length}
        artifactCount={artifacts.length}
      />

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
          <CardHeader>
            <CardTitle className="text-slate-900">运行参数</CardTitle>
            <CardDescription className="text-slate-500">这些参数会被运行按钮复用，提交时仍走 Job Center。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">配置路径</span>
              <Input value={form.configPath} onChange={(event) => updateForm({ configPath: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">交易日期</span>
              <Input type="date" value={form.tradeDate} onChange={(event) => updateForm({ tradeDate: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">时间槽</span>
              <Select value={form.slot} onChange={(event) => updateForm({ slot: event.target.value })}>
                <option value="all">all</option>
                <option value="09-25">09-25</option>
                <option value="17-30">17-30</option>
              </Select>
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">抓取模式</span>
              <Select value={form.mode} onChange={(event) => updateForm({ mode: event.target.value })}>
                <option value="incremental">incremental</option>
                <option value="full">full</option>
              </Select>
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">快照日期</span>
              <Input type="date" value={form.snapshotDate} onChange={(event) => updateForm({ snapshotDate: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">市场状态日期</span>
              <Input type="date" value={form.asOf} onChange={(event) => updateForm({ asOf: event.target.value })} />
            </label>
            <label className="space-y-2 md:col-span-2">
              <span className="text-sm font-medium text-slate-700">标的列表（逗号或换行分隔）</span>
              <Textarea
                value={form.symbols}
                onChange={(event) => updateForm({ symbols: event.target.value })}
                placeholder="000001.SZ, 600000.SH"
                rows={3}
              />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">开始日期</span>
              <Input type="date" value={form.startDate} onChange={(event) => updateForm({ startDate: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">结束日期</span>
              <Input type="date" value={form.endDate} onChange={(event) => updateForm({ endDate: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">输出路径</span>
              <Input value={form.dest} onChange={(event) => updateForm({ dest: event.target.value })} />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-medium text-slate-700">抓取上限</span>
              <Input
                type="number"
                min={1}
                max={500}
                value={form.limit}
                onChange={(event) => updateForm({ limit: Number(event.target.value) || 1 })}
              />
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
              <input type="checkbox" checked={form.force} onChange={(event) => updateForm({ force: event.target.checked })} />
              强制执行
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
              <input type="checkbox" checked={form.offline} onChange={(event) => updateForm({ offline: event.target.checked })} />
              离线模式
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
              <input type="checkbox" checked={form.fromAkshare} onChange={(event) => updateForm({ fromAkshare: event.target.checked })} />
              从 AkShare 构建
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
              <input type="checkbox" checked={form.cacheCsv} onChange={(event) => updateForm({ cacheCsv: event.target.checked })} />
              缓存 CSV
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
              <input type="checkbox" checked={form.startScheduler} onChange={(event) => updateForm({ startScheduler: event.target.checked })} />
              启动调度器
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-700">
              <input type="checkbox" checked={form.block} onChange={(event) => updateForm({ block: event.target.checked })} />
              阻塞运行
            </label>
          </CardContent>
        </Card>

        <div className="space-y-6">
          {jobsError ? (
            <ErrorState
              {...jobsError}
              onRetry={() => {
                void jobsQuery.refetch();
              }}
            />
          ) : (
            <MarketWorkspaceErrors failedJobs={failedJobs.slice(0, 3)} />
          )}
          {artifactsError ? (
            <ErrorState
              {...artifactsError}
              onRetry={() => {
                void artifactsQuery.refetch();
              }}
            />
          ) : (
            <MarketWorkspaceArtifacts artifacts={artifacts.slice(0, 6)} loading={artifactsQuery.isLoading} />
          )}
        </div>
      </section>

      <MarketWorkspaceRunners
        runners={RUNNERS}
        submittingJobType={submittingJobType}
        onRun={(jobType) => {
          setSubmissionMessage(null);
          runMutation.mutate(jobType);
        }}
      />

      {jobsError ? (
        <ErrorState
          {...jobsError}
          onRetry={() => {
            void jobsQuery.refetch();
          }}
          className="mt-2"
        />
      ) : (
        <MarketWorkspaceRecentJobs jobs={marketJobs.slice(0, 8)} loading={jobsQuery.isLoading} />
      )}

      <section className="grid gap-4 md:grid-cols-2">
        <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
          <CardHeader>
            <CardTitle className="text-slate-900">快捷入口</CardTitle>
            <CardDescription className="text-slate-500">不改变主流程，只提供常用页面跳转。</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            {[
              { label: 'Kaipan', href: '/kaipan' },
              { label: '市场状态', href: '/market-state' },
              { label: '快照中心', href: '/snapshots' },
              { label: '任务中心', href: '/jobs' },
              { label: '产物中心', href: '/artifacts' },
            ].map((item) => (
              <a
                key={item.href}
                className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                href={item.href}
              >
                {item.label}
              </a>
            ))}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
          <CardHeader>
            <CardTitle className="text-slate-900">工作台说明</CardTitle>
            <CardDescription className="text-slate-500">市场数据工作台只负责提交和复盘，不承担 provider 实现。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600">
            <p>1. 通过 Job Center 提交任务，避免 CLI 和 UI 之间出现两套正式入口。</p>
            <p>2. 最近任务和产物都可以直接跳转到 Job / Artifact 详情页。</p>
            <p>3. 失败时优先看配置、provider、数据和系统分类。</p>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
