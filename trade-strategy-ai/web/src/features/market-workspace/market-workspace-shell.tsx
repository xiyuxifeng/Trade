import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/components/ui/toast';
import { PageHeader } from '@/components/layout/page-header';
import { ErrorState } from '@/components/state/ErrorState';
import { formatLocalDateInputOffset } from '@/lib/date';
import { createJob, listJobs } from '@/lib/api/jobs';
import { listArtifacts } from '@/lib/api/artifacts';
import {
  getOhlcvSchedulerStatus,
  getStockInfoStatus,
  listBenchmarkOptions,
  refreshStockInfo,
  runOhlcvScheduler,
  stopOhlcvScheduler,
} from '@/lib/api/market';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { kaipanRun, kaipanStatus, kaipanStop } from '@/lib/api/kaipan';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { MarketWorkspaceSummary } from './market-workspace-summary';
import { MarketWorkspaceRunners, type MarketWorkspaceRunner } from './market-workspace-runners';
import { MarketWorkspaceRecentJobs } from './market-workspace-recent-jobs';
import { MarketWorkspaceErrors } from './market-workspace-errors';
import { MarketWorkspaceArtifacts } from './market-workspace-artifacts';
import { DataHealthCenter } from '@/features/data-health';
import type { ProfileDetailResponse, ProfileRecord } from '@/types/profile';
import type { KaipanStatusResponse } from '@/types/kaipan';
import type { OhlcvSchedulerStatusResponse, StockInfoStatusResponse } from '@/types/market';

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
    description: '抓取指定交易日期范围的 Kaipan 原始数据。',
    badge: '抓取',
  },
  {
    jobType: 'kaipan-normalize',
    title: 'Kaipan 归一化',
    description: '把抓取结果整理成统一的市场数据输入，并显示单日/范围进度。',
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
    description: '生成当天的市场状态快照。',
    badge: '状态',
  },
  {
    jobType: 'snapshot-build',
    title: '市场上下文构建',
    description: '构建统一市场上下文快照，并输出摘要和质量报告。',
    badge: '上下文',
  },
];

type MarketWorkspaceMode = 'all' | 'kaipan' | 'ohlcv';

type MarketWorkspaceShellProps = {
  mode?: MarketWorkspaceMode;
};

type MarketWorkspaceModeConfig = {
  title: string;
  description: string;
  paramsTitle: string;
  paramsDescription: string;
  jobFilter: Set<string>;
  submissionHint: string;
  showQuickLinks: boolean;
  showDataHealthCenter: boolean;
  showOhlcvCards: boolean;
};

const MARKET_WORKSPACE_MODE_CONFIG: Record<MarketWorkspaceMode, MarketWorkspaceModeConfig> = {
  all: {
    title: '市场上下文工作台',
    description: '在 Web 中运行和查看市场上下文链路，保持与正式交付版一致的浅色中文工作台风格。',
    paramsTitle: '运行参数',
    paramsDescription: '这些参数会被运行按钮复用，提交时仍走 Job Center。',
    jobFilter: RUNTIME_JOB_TYPES,
    submissionHint: '操作已完成。',
    showQuickLinks: true,
    showDataHealthCenter: false,
    showOhlcvCards: false,
  },
  kaipan: {
    title: '市场数据健康',
    description: '查看 Kaipan 抓取、归一化与数据健康状态。',
    paramsTitle: '任务参数',
    paramsDescription: '只保留 Kaipan 抓取和归一化需要的参数，使用交易日期范围和 slot 提交。',
    jobFilter: new Set(['kaipan-fetch', 'kaipan-normalize', 'kaipan-run']),
    submissionHint: '调度器由当前后台进程管理，不依赖 Job Center。',
    showQuickLinks: false,
    showDataHealthCenter: true,
    showOhlcvCards: false,
  },
  ohlcv: {
    title: 'OHLCV 行情',
    description: '抓取和回灌 OHLCV 行情，并查看最近任务与调度状态。',
    paramsTitle: '抓取参数',
    paramsDescription: '保留 OHLCV 抓取和回灌需要的参数。',
    jobFilter: new Set(['ohlcv-crawl']),
    submissionHint: 'OHLCV 调度器由当前后台进程管理，不依赖 Job Center。',
    showQuickLinks: false,
    showDataHealthCenter: false,
    showOhlcvCards: true,
  },
};

function ProfileField({
  id,
  label,
  profileId,
  onChange,
  loading,
  items,
  profileListError,
  profileDetailError,
}: {
  id: string;
  label: string;
  profileId: string;
  onChange: (value: string) => void;
  loading: boolean;
  items: ProfileRecord[];
  profileListError: boolean;
  profileDetailError: boolean;
}) {
  return (
    <label className="space-y-2" htmlFor={id}>
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <Select id={id} value={profileId} onChange={(event) => onChange(event.target.value)} disabled={loading}>
        {items.length === 0 ? <option value="">暂无可用 Profile</option> : null}
        {items.map((profile) => (
          <option key={profile.profile_id} value={profile.profile_id}>
            {profile.name} ({profile.profile_id})
          </option>
        ))}
      </Select>
      <p className="text-xs text-slate-500">
        配置上下文将从所选 Profile 的最新 snapshot 自动解析。
      </p>
      {profileListError ? <p className="text-xs text-rose-600">Profile 列表加载失败，请稍后重试。</p> : null}
      {profileDetailError ? <p className="text-xs text-rose-600">Profile 详情加载失败，提交时仍以 Profile 为准。</p> : null}
    </label>
  );
}

function buildJobParams(jobType: string, form: WorkspaceFormState, mode: MarketWorkspaceMode) {
  const symbols = form.symbols
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);

  const base = {
    profile_id: form.profileId,
    trade_date: form.tradeDate,
    slot: form.slot,
  };

  if (jobType === 'kaipan-fetch' || jobType === 'kaipan-normalize') {
    return mode === 'kaipan'
      ? {
          profile_id: form.kaipanProfileId,
          start_date: form.startDate,
          end_date: form.endDate,
          slot: form.slot,
        }
      : base;
  }

  if (jobType === 'kaipan-run') {
    return mode === 'kaipan'
      ? {
          profile_id: form.kaipanProfileId,
          start_scheduler: true,
          block: false,
        }
      : {
          profile_id: form.profileId,
          trade_date: form.tradeDate,
          slot: form.slot,
          mode: form.mode,
          symbols,
          start_date: form.startDate,
          end_date: form.endDate,
          limit: form.limit,
        };
  }

  if (jobType === 'ohlcv-crawl') {
    if (mode === 'ohlcv') {
      const params: Record<string, unknown> = {
        profile_id: form.ohlcvProfileId,
        mode: form.mode,
        symbols,
        start_date: form.startDate,
        end_date: form.endDate,
      };
      if (form.limit !== '') {
        params.limit = form.limit;
      }
      return params;
    }
    return {
      profile_id: form.profileId,
      mode: form.mode,
      symbols,
      start_date: form.startDate,
      end_date: form.endDate,
      limit: form.limit === '' ? undefined : form.limit,
    };
  }

  if (jobType === 'market-state-build') {
    return {
      profile_id: form.profileId,
      benchmark_symbol: form.benchmarkSymbol,
      as_of: form.asOf,
      dest: form.dest,
      from_akshare: form.fromAkshare,
      cache_csv: form.cacheCsv,
    };
  }

  return {
    profile_id: form.profileId,
    benchmark_symbol: form.benchmarkSymbol,
    date: form.snapshotDate,
    start_date: form.startDate,
    end_date: form.endDate,
    slot: form.slot,
    snapshot_type: form.snapshotType,
    force: form.force,
    offline: form.offline,
  };
}

type WorkspaceFormState = {
  profileId: string;
  ohlcvProfileId: string;
  kaipanProfileId: string;
  tradeDate: string;
  slot: string;
  mode: string;
  snapshotDate: string;
  startDate: string;
  endDate: string;
  asOf: string;
  dest: string;
  symbols: string;
  limit: number | '';
  snapshotType: string;
  force: boolean;
  offline: boolean;
  fromAkshare: boolean;
  cacheCsv: boolean;
  benchmarkSymbol: string;
};

export function MarketWorkspaceShell() {
  return <MarketWorkspaceShellInner mode="all" />;
}

export function MarketKaipanWorkspaceShell() {
  return <MarketWorkspaceShellInner mode="kaipan" />;
}

export function MarketOhlcvWorkspaceShell() {
  return <MarketWorkspaceShellInner mode="ohlcv" />;
}

function MarketWorkspaceShellInner({ mode = 'all' }: MarketWorkspaceShellProps) {
  const modeConfig = MARKET_WORKSPACE_MODE_CONFIG[mode];
  const [form, setForm] = useState<WorkspaceFormState>({
    profileId: '',
    ohlcvProfileId: '',
    kaipanProfileId: '',
    tradeDate: formatLocalDateInputOffset(0),
    slot: '17-30',
    mode: 'incremental',
    snapshotDate: formatLocalDateInputOffset(0),
    startDate: formatLocalDateInputOffset(-30),
    endDate: formatLocalDateInputOffset(0),
    asOf: formatLocalDateInputOffset(0),
    dest: 'data/processed/persona/market_state.json',
    symbols: '',
    limit: '',
    snapshotType: 'all',
    force: false,
    offline: false,
    fromAkshare: false,
    cacheCsv: true,
    benchmarkSymbol: '000300.SH',
  });
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [submissionJobId, setSubmissionJobId] = useState<string | null>(null);
  const [submittingJobType, setSubmittingJobType] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const benchmarkOptionsQuery = useQuery({
    queryKey: ['market-workspace-benchmark-options'],
    queryFn: () => listBenchmarkOptions(20),
    staleTime: 30_000,
  });
  const benchmarkOptions = benchmarkOptionsQuery.data?.items ?? [];
  const stockInfoStatusQuery = useQuery<StockInfoStatusResponse>({
    queryKey: ['market-workspace', 'stock-info-status'],
    queryFn: () => getStockInfoStatus(7),
    enabled: mode === 'ohlcv',
    staleTime: 10_000,
  });
  const stockInfoStatus = stockInfoStatusQuery.data;
  const stockInfoNeedsRefresh = Boolean(stockInfoStatus?.needs_refresh);
  const stockInfoStatusMessage = stockInfoStatus?.message ?? '正在检查基础信息是否可用于 OHLCV 抓取。';
  const stockInfoRefreshMutation = useMutation({
    mutationFn: async () => refreshStockInfo(7),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['market-workspace', 'stock-info-status'] });
      void queryClient.invalidateQueries({ queryKey: ['market-workspace-benchmark-options'] });
      setSubmissionMessage('基础信息已刷新，可继续运行 OHLCV 抓取。');
      setSubmissionJobId(null);
    },
  });

  const kaipanProfilesQuery = useQuery({
    queryKey: ['market-workspace', 'kaipan-profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    enabled: mode === 'kaipan',
    staleTime: 30_000,
  });
  const kaipanProfileItems = kaipanProfilesQuery.data?.items ?? [];
  const allProfilesQuery = useQuery({
    queryKey: ['market-workspace', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    enabled: mode === 'all',
    staleTime: 30_000,
  });
  const allProfileItems = allProfilesQuery.data?.items ?? [];

  useEffect(() => {
    if (mode !== 'all' || !allProfileItems.length) {
      return;
    }
    if (!form.profileId || !allProfileItems.some((item: ProfileRecord) => item.profile_id === form.profileId)) {
      setForm((current) => ({ ...current, profileId: allProfileItems[0].profile_id }));
    }
  }, [allProfileItems, form.profileId, mode]);

  const selectedAllProfileDetailQuery = useQuery<ProfileDetailResponse, Error>({
    queryKey: ['market-workspace', 'profile-detail', form.profileId],
    queryFn: () => getProfile(form.profileId),
    enabled: mode === 'all' && Boolean(form.profileId),
    staleTime: 30_000,
  });
  useEffect(() => {
    if (mode !== 'kaipan' || !kaipanProfileItems.length) {
      return;
    }
    if (!form.kaipanProfileId || !kaipanProfileItems.some((item: ProfileRecord) => item.profile_id === form.kaipanProfileId)) {
      setForm((current) => ({ ...current, kaipanProfileId: kaipanProfileItems[0].profile_id }));
    }
  }, [form.kaipanProfileId, kaipanProfileItems, mode]);

  const selectedKaipanProfileDetailQuery = useQuery<ProfileDetailResponse, Error>({
    queryKey: ['market-workspace', 'kaipan-profile-detail', form.kaipanProfileId],
    queryFn: () => getProfile(form.kaipanProfileId),
    enabled: mode === 'kaipan' && Boolean(form.kaipanProfileId),
    staleTime: 30_000,
  });

  const ohlcvProfilesQuery = useQuery({
    queryKey: ['market-workspace', 'ohlcv-profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    enabled: mode === 'ohlcv',
    staleTime: 30_000,
  });
  const ohlcvProfileItems = ohlcvProfilesQuery.data?.items ?? [];
  useEffect(() => {
    if (mode !== 'ohlcv' || !ohlcvProfileItems.length) {
      return;
    }
    if (!form.ohlcvProfileId || !ohlcvProfileItems.some((item: ProfileRecord) => item.profile_id === form.ohlcvProfileId)) {
      setForm((current) => ({ ...current, ohlcvProfileId: ohlcvProfileItems[0].profile_id }));
    }
  }, [form.ohlcvProfileId, mode, ohlcvProfileItems]);
  const selectedOhlcvProfileDetailQuery = useQuery<ProfileDetailResponse, Error>({
    queryKey: ['market-workspace', 'ohlcv-profile-detail', form.ohlcvProfileId],
    queryFn: () => getProfile(form.ohlcvProfileId),
    enabled: mode === 'ohlcv' && Boolean(form.ohlcvProfileId),
    staleTime: 30_000,
  });
  const [kaipanSchedulerStartedOverride, setKaipanSchedulerStartedOverride] = useState<boolean | null>(null);
  const kaipanSchedulerQuery = useQuery<KaipanStatusResponse>({
    queryKey: ['market-workspace', 'kaipan-status', form.kaipanProfileId],
    queryFn: () => kaipanStatus(form.kaipanProfileId),
    enabled: mode === 'kaipan' && Boolean(form.kaipanProfileId),
    staleTime: 10_000,
  });
  const kaipanSchedulerStarted = kaipanSchedulerStartedOverride ?? kaipanSchedulerQuery.data?.scheduler_started ?? false;
  const kaipanSchedulerScheduleLabel = useMemo(() => {
    const preMarket = kaipanSchedulerQuery.data?.scheduler_pre_market ?? '9:25';
    const postClose = kaipanSchedulerQuery.data?.scheduler_post_close ?? '17:30';
    return `${preMarket} / ${postClose}`;
  }, [kaipanSchedulerQuery.data?.scheduler_post_close, kaipanSchedulerQuery.data?.scheduler_pre_market]);
  const [ohlcvSchedulerStartedOverride, setOhlcvSchedulerStartedOverride] = useState<boolean | null>(null);
  const ohlcvSchedulerQuery = useQuery<OhlcvSchedulerStatusResponse>({
    queryKey: ['market-workspace', 'ohlcv-status', form.ohlcvProfileId],
    queryFn: () => getOhlcvSchedulerStatus(form.ohlcvProfileId),
    enabled: mode === 'ohlcv' && Boolean(form.ohlcvProfileId),
    staleTime: 10_000,
  });
  const ohlcvSchedulerStarted = ohlcvSchedulerStartedOverride ?? ohlcvSchedulerQuery.data?.scheduler_started ?? false;
  const ohlcvSchedulerScheduleLabel = useMemo(() => {
    const preMarket = ohlcvSchedulerQuery.data?.scheduler_pre_market ?? '9:25';
    const postClose = ohlcvSchedulerQuery.data?.scheduler_post_close ?? '17:30';
    return `${preMarket} / ${postClose}`;
  }, [ohlcvSchedulerQuery.data?.scheduler_post_close, ohlcvSchedulerQuery.data?.scheduler_pre_market]);

  const jobsQuery = useQuery({
    queryKey: ['market-workspace-jobs'],
    queryFn: () => listJobs({ limit: 20 }),
    staleTime: 30_000,
    refetchInterval: (query) => {
      const items = (query.state.data?.items ?? []) as Array<{ status?: string }>;
      return items.some((item) => item.status === 'running' || item.status === 'pending') ? 5000 : false;
    },
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
        params: buildJobParams(jobType, form, mode),
      });
    },
    onSuccess: (result, jobType) => {
      setSubmissionJobId(result.job.id);
      if (jobType === 'kaipan-fetch' || jobType === 'kaipan-normalize') {
        const title = jobType === 'kaipan-fetch' ? 'Kaipan 抓取任务已提交' : 'Kaipan 归一化任务已提交';
        setSubmissionMessage(`${title}，Job ${result.job.id} 已创建，可打开 Job 详情查看进度。`);
        toast({
          title,
          description: `Job ${result.job.id} 已创建，可打开 Job 详情查看进度。`,
        });
        return;
      }
      setSubmissionMessage(`任务已生成：${jobType}，可打开 Job 详情查看进度。`);
    },
    onError: (error, jobType) => {
      const message = error instanceof Error ? error.message : '提交失败，请稍后重试。';
      const title =
        jobType === 'kaipan-fetch'
          ? 'Kaipan 抓取任务提交失败'
          : jobType === 'kaipan-normalize'
            ? 'Kaipan 归一化任务提交失败'
            : `任务 ${jobType} 提交失败`;
      setSubmissionJobId(null);
      setSubmissionMessage(`${title}：${message}`);
      toast({
        title,
        description: message,
      });
    },
    onSettled: () => {
      setSubmittingJobType(null);
    },
  });

  const schedulerToggleMutation = useMutation({
    mutationFn: async () => {
      if (kaipanSchedulerStarted) {
        return kaipanStop(form.kaipanProfileId);
      }
      return kaipanRun({ start_scheduler: true, block: false }, form.kaipanProfileId);
    },
    onSuccess: (result) => {
      const started = Boolean(result.started ?? result.scheduler_started);
      setKaipanSchedulerStartedOverride(started);
      void queryClient.invalidateQueries({ queryKey: ['market-workspace', 'kaipan-status', form.kaipanProfileId] });
      if (!started) {
        setSubmissionMessage('Kaipan 调度器已停止。');
        setSubmissionJobId(null);
        return;
      }
      setSubmissionMessage(`Kaipan 调度器已启动，定时 ${result.pre_market} / ${result.post_close}。`);
      setSubmissionJobId(null);
    },
  });
  const ohlcvSchedulerToggleMutation = useMutation({
    mutationFn: async () => {
      if (ohlcvSchedulerStarted) {
        return stopOhlcvScheduler(form.ohlcvProfileId);
      }
      return runOhlcvScheduler(form.ohlcvProfileId);
    },
    onSuccess: (result) => {
      const started = Boolean(result.started);
      setOhlcvSchedulerStartedOverride(started);
      void queryClient.invalidateQueries({ queryKey: ['market-workspace', 'ohlcv-status', form.ohlcvProfileId] });
      if (!started) {
        setSubmissionMessage('OHLCV 调度器已停止。');
        setSubmissionJobId(null);
        return;
      }
      setSubmissionMessage(`OHLCV 调度器已启动，定时 ${result.pre_market} / ${result.post_close}。`);
      setSubmissionJobId(null);
    },
  });

  const visibleRunnerTypes = useMemo(() => modeConfig.jobFilter, [modeConfig.jobFilter]);

  const visibleRunners = useMemo(() => {
    const scheduleLabel = kaipanSchedulerScheduleLabel;
    const schedulerStateLabel = kaipanSchedulerStarted ? '已启动' : '未启动';
    return RUNNERS.filter((runner) => visibleRunnerTypes.has(runner.jobType)).map((runner) =>
      runner.jobType === 'kaipan-run'
        ? {
            ...runner,
            description: `调度时间：${scheduleLabel}，当前状态：${schedulerStateLabel}。`,
          }
        : runner,
    );
  }, [kaipanSchedulerScheduleLabel, kaipanSchedulerStarted, visibleRunnerTypes]);

  const marketJobs = useMemo(
    () => (jobsQuery.data?.items ?? []).filter((job) => visibleRunnerTypes.has(job.job_type)),
    [jobsQuery.data?.items, visibleRunnerTypes],
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
      <PageHeader kicker="市场上下文" title={modeConfig.title} description={modeConfig.description} />

      {submissionMessage ? (
        <Card className="border-sky-200 bg-sky-50 text-sky-900 shadow-sm">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <p className="font-medium">{submissionMessage}</p>
              <p className="text-sm text-sky-700">{submissionJobId ? '任务已通过 Job Center 创建，不需要 CLI。' : modeConfig.submissionHint}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {submissionJobId ? (
                <a
                  className="inline-flex h-10 items-center justify-center rounded-lg border border-sky-200 bg-white px-4 text-sm font-medium text-sky-800 transition-colors hover:bg-sky-50"
                  href={`/system/jobs/${submissionJobId}`}
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
        taskCount={visibleRunners.length}
        recentJobCount={marketJobs.length}
        failedJobCount={failedJobs.length}
        artifactCount={artifacts.length}
      />

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
          <CardHeader>
            <CardTitle className="text-slate-900">{modeConfig.paramsTitle}</CardTitle>
            <CardDescription className="text-slate-500">{modeConfig.paramsDescription}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            {mode === 'all' ? (
              <div className="md:col-span-2">
                <ProfileField
                  id="all-profile"
                  label="Profile"
                  profileId={form.profileId}
                  onChange={(value) => updateForm({ profileId: value })}
                  loading={allProfilesQuery.isLoading}
                  items={allProfileItems}
                  profileListError={allProfilesQuery.isError}
                  profileDetailError={selectedAllProfileDetailQuery.isError}
                />
              </div>
            ) : null}
            {mode === 'kaipan' || mode === 'all' ? (
              <>
                {mode === 'kaipan' ? (
                  <ProfileField
                    id="kaipan-profile"
                    label="Profile"
                    profileId={form.kaipanProfileId}
                    onChange={(value) => updateForm({ kaipanProfileId: value })}
                    loading={kaipanProfilesQuery.isLoading}
                    items={kaipanProfileItems}
                    profileListError={kaipanProfilesQuery.isError}
                    profileDetailError={selectedKaipanProfileDetailQuery.isError}
                  />
                ) : null}
                {mode === 'kaipan' ? (
                  <>
                    <label className="space-y-2">
                      <span className="text-sm font-medium text-slate-700">开始日期</span>
                      <Input type="date" value={form.startDate} onChange={(event) => updateForm({ startDate: event.target.value })} />
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm font-medium text-slate-700">结束日期</span>
                      <Input type="date" value={form.endDate} onChange={(event) => updateForm({ endDate: event.target.value })} />
                    </label>
                    <label className="space-y-2">
                      <span className="text-sm font-medium text-slate-700">时间槽</span>
                      <Select value={form.slot} onChange={(event) => updateForm({ slot: event.target.value })}>
                        <option value="all">all</option>
                        <option value="09-25">09-25</option>
                        <option value="17-30">17-30</option>
                      </Select>
                    </label>
                    <p className="md:col-span-2 rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-xs leading-6 text-slate-500">
                      Kaipan 以交易日期范围运行进度，范围按交易日展开；如果开始日期和结束日期相同，就只会处理当天。当前调度器状态：{kaipanSchedulerStarted ? '已启动' : '未启动'}，时间：{kaipanSchedulerScheduleLabel}。
                    </p>
                  </>
                ) : (
                  <>
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
                  </>
                )}
              </>
            ) : null}
            {mode === 'ohlcv' || mode === 'all' ? (
              <>
                {mode === 'ohlcv' ? (
                  <ProfileField
                    id="ohlcv-profile"
                    label="Profile"
                    profileId={form.ohlcvProfileId}
                    onChange={(value) => updateForm({ ohlcvProfileId: value })}
                    loading={ohlcvProfilesQuery.isLoading}
                    items={ohlcvProfileItems}
                    profileListError={ohlcvProfilesQuery.isError}
                    profileDetailError={selectedOhlcvProfileDetailQuery.isError}
                  />
                ) : null}
                <label className="space-y-2">
                  <span className="text-sm font-medium text-slate-700">任务模式</span>
                  <Select value={form.mode} onChange={(event) => updateForm({ mode: event.target.value })}>
                    <option value="incremental">增量</option>
                    <option value="full">区间回灌</option>
                  </Select>
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
                  <span className="text-sm font-medium text-slate-700">抓取上限</span>
                  <Input
                    type="number"
                    min={1}
                    max={500}
                    value={form.limit}
                    onChange={(event) => updateForm({ limit: event.target.value === '' ? '' : Number(event.target.value) || 1 })}
                  />
                  <p className="text-xs text-slate-500">留空表示全量抓取。</p>
                </label>
              </>
            ) : null}
            {mode === 'all' ? (
              <>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-slate-700">快照日期</span>
                  <Input type="date" value={form.snapshotDate} onChange={(event) => updateForm({ snapshotDate: event.target.value })} />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-slate-700">市场状态日期</span>
                  <Input type="date" value={form.asOf} onChange={(event) => updateForm({ asOf: event.target.value })} />
                </label>
                <label className="space-y-2">
                  <span className="text-sm font-medium text-slate-700">基准指数</span>
                  <Select value={form.benchmarkSymbol} onChange={(event) => updateForm({ benchmarkSymbol: event.target.value })}>
                    {benchmarkOptions.length === 0 ? (
                      <option value={form.benchmarkSymbol}>{form.benchmarkSymbol}</option>
                    ) : (
                      benchmarkOptions.map((item) => (
                        <option key={item.symbol} value={item.symbol}>
                          {item.name} ({item.symbol})
                        </option>
                      ))
                    )}
                  </Select>
                </label>
                <label className="space-y-2 md:col-span-2">
                  <span className="text-sm font-medium text-slate-700">输出路径</span>
                  <Input value={form.dest} onChange={(event) => updateForm({ dest: event.target.value })} />
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
              </>
            ) : null}
          </CardContent>
        </Card>

        {modeConfig.showOhlcvCards ? (
          <div className="space-y-4">
            <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
              <CardHeader>
                <CardTitle className="text-slate-900">基础信息预检</CardTitle>
                <CardDescription className="text-slate-500">
                  OHLCV 抓取前先检查基础信息是否覆盖常用 benchmark 且更新时间在 7 天内。若过期或缺失，请先刷新再继续。
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-xs leading-6 text-slate-600">
                  <p>状态：{stockInfoStatusQuery.isLoading ? '检查中' : stockInfoStatusQuery.isError ? '检查失败' : stockInfoStatus?.is_fresh ? '可直接用于 OHLCV 抓取' : '需要刷新'}</p>
                  <p>说明：{stockInfoStatusMessage}</p>
                  <p>
                    数据量：{stockInfoStatus?.stock_count ?? 0} 条股票，{stockInfoStatus?.index_count ?? 0} 条指数，benchmark 覆盖 {stockInfoStatus?.benchmark_count ?? 0}/
                    {stockInfoStatus?.expected_benchmark_count ?? 0}。
                  </p>
                  <p>最近更新时间：{stockInfoStatus?.latest_updated_at ?? '暂无'}</p>
                </div>
                {stockInfoStatusQuery.isError ? (
                  <p className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-3 text-xs leading-6 text-rose-700">
                    基础信息状态检查失败，请先点击“检查并更新基础信息”重新获取状态，再运行 OHLCV 抓取。
                  </p>
                ) : null}
                {stockInfoNeedsRefresh ? (
                  <p className="rounded-2xl border border-amber-200 bg-amber-50 px-3 py-3 text-xs leading-6 text-amber-700">
                    基础信息已过期或缺少 benchmark，OHLCV 抓取前建议先刷新。
                  </p>
                ) : null}
                <div className="flex flex-wrap items-center gap-3">
                  <Button
                    variant="outline"
                    className="border-slate-200 bg-white text-slate-800 hover:bg-slate-50"
                    onClick={() => {
                      stockInfoRefreshMutation.mutate();
                    }}
                    disabled={stockInfoRefreshMutation.isPending}
                  >
                    {stockInfoRefreshMutation.isPending ? '刷新中' : '检查并更新基础信息'}
                  </Button>
                  <p className="text-xs leading-6 text-slate-500">这个按钮只刷新基础信息，不会创建 Job。</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
              <CardHeader>
                <CardTitle className="text-slate-900">OHLCV 抓取</CardTitle>
                <CardDescription className="text-slate-500">
                  直接使用左侧抓取参数提交 `ohlcv-crawl`。如果基础信息未通过预检，请先刷新再提交。
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 text-xs leading-6 text-slate-500">
                  当前抓取模式：{form.mode === 'incremental' ? '增量' : '区间回灌'}，标的数：
                  {form.symbols.trim() ? form.symbols.split(/[\n,]/).map((item) => item.trim()).filter(Boolean).length : 0}，时间范围：
                  {form.startDate} ~ {form.endDate}。
                </div>
                <Button
                  className="w-full bg-sky-500 text-slate-950 hover:bg-sky-400"
                  disabled={submittingJobType === 'ohlcv-crawl' || stockInfoStatusQuery.isLoading || stockInfoStatusQuery.isError || stockInfoNeedsRefresh}
                  onClick={() => {
                    setSubmissionMessage(null);
                    runMutation.mutate('ohlcv-crawl');
                  }}
                >
                  {submittingJobType === 'ohlcv-crawl' ? '提交中' : '运行 OHLCV 抓取'}
                </Button>
              </CardContent>
            </Card>

            <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
              <CardHeader>
                <CardTitle className="text-slate-900">OHLCV 调度器</CardTitle>
                <CardDescription className="text-slate-500">
                  OHLCV 调度器按配置中的时间自动运行：{ohlcvSchedulerScheduleLabel}。当前状态：{ohlcvSchedulerStarted ? '已启动' : '未启动'}。
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-xs leading-6 text-slate-500">
                  调度器会在盘前和盘后按配置时间自动执行增量抓取，手动抓取仍然保留为独立入口。最近数据：
                  {ohlcvSchedulerQuery.data?.latest_trade_date ?? '暂无'}，记录数：{ohlcvSchedulerQuery.data?.latest_record_count ?? 0}。
                </p>
                <Button
                  className="w-full"
                  onClick={() => {
                    ohlcvSchedulerToggleMutation.mutate();
                  }}
                  disabled={ohlcvSchedulerToggleMutation.isPending}
                >
                  {ohlcvSchedulerToggleMutation.isPending ? '处理中' : ohlcvSchedulerStarted ? '停止调度器' : '启动调度器'}
                </Button>
              </CardContent>
              {ohlcvSchedulerQuery.isError ? <p className="px-6 pb-4 text-xs text-rose-600">OHLCV 调度器状态加载失败，请稍后重试。</p> : null}
            </Card>
          </div>
        ) : (
          <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
            <CardHeader>
              <CardTitle className="text-slate-900">流程入口</CardTitle>
              <CardDescription className="text-slate-500">不改变主流程，只提供常用页面跳转。</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3">
              <a className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70" href="/market/snapshots">
                <p className="text-sm font-medium text-slate-950">市场上下文快照</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">查看市场上下文快照列表和构建入口。</p>
              </a>
              <a className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70" href="/market/datasets">
                <p className="text-sm font-medium text-slate-950">市场数据集</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">查看数据集浏览和详情。</p>
              </a>
              <a className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-200 hover:bg-sky-50/70" href="/market/kaipan">
                <p className="text-sm font-medium text-slate-950">市场数据健康</p>
                <p className="mt-1 text-sm leading-6 text-slate-600">进入 Kaipan 抓取与调度页面。</p>
              </a>
            </CardContent>
          </Card>
        )}
      </section>

      {modeConfig.showOhlcvCards ? (
        <section className="space-y-4">
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
          <MarketWorkspaceRecentJobs jobs={marketJobs.slice(0, 8)} loading={jobsQuery.isLoading} compact />
          {artifactsError ? (
            <ErrorState
              {...artifactsError}
              onRetry={() => {
                void artifactsQuery.refetch();
              }}
            />
          ) : (
            <MarketWorkspaceArtifacts artifacts={artifacts.slice(0, 6)} loading={artifactsQuery.isLoading} compact />
          )}
        </section>
      ) : (
        <>
          <MarketWorkspaceRunners
            runners={visibleRunners}
            submittingJobType={submittingJobType}
            kaipanSchedulerControlEnabled={mode === 'kaipan'}
            kaipanSchedulerStarted={kaipanSchedulerStarted}
            kaipanSchedulerToggling={schedulerToggleMutation.isPending}
            onKaipanSchedulerToggle={mode === 'kaipan' ? () => schedulerToggleMutation.mutate() : undefined}
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

          {modeConfig.showDataHealthCenter ? (
            <section className="grid gap-4 xl:grid-cols-2">
              <DataHealthCenter />
              {artifactsError ? (
                <ErrorState
                  {...artifactsError}
                  onRetry={() => {
                    void artifactsQuery.refetch();
                  }}
                />
              ) : (
                <MarketWorkspaceArtifacts artifacts={artifacts.slice(0, 6)} loading={artifactsQuery.isLoading} compact />
              )}
            </section>
          ) : null}
        </>
      )}

      {modeConfig.showQuickLinks ? (
        <section className="grid gap-4 md:grid-cols-2">
          <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
            <CardHeader>
              <CardTitle className="text-slate-900">快捷入口</CardTitle>
              <CardDescription className="text-slate-500">不改变主流程，只提供常用页面跳转。</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              {[
                { label: '市场上下文快照', href: '/market/snapshots' },
                { label: '数据集', href: '/market/datasets' },
                { label: '市场数据健康', href: '/market/kaipan' },
                { label: 'OHLCV 行情', href: '/market/ohlcv' },
                { label: '盘前分析', href: '/strategies/pre-market' },
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
              <CardDescription className="text-slate-500">市场上下文工作台只负责提交和复盘，不承担 provider 实现。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-slate-600">
              <p>1. 通过 Job Center 提交任务，避免 CLI 和 UI 之间出现两套正式入口。</p>
              <p>2. 最近任务和产物都可以直接跳转到 Job / Artifact 详情页。</p>
              <p>3. 失败时优先看配置、provider、数据和系统分类。</p>
            </CardContent>
          </Card>
        </section>
      ) : null}
    </main>
  );
}
