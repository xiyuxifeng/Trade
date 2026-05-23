import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArtifactPreview } from '@/components/artifacts/artifact-preview';
import { JsonViewer } from '@/components/kit';
import { PageHeader } from '@/components/layout/page-header';
import { ErrorState } from '@/components/state/ErrorState';
import { TraderIdSelect } from '@/components/inputs/trader-id-select';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { createJob } from '@/lib/api/jobs';
import {
  buildBacktestReproducibilityParams,
  buildBacktestRunParams,
  buildBacktestValidateRulesParams,
  downloadBacktestReport,
  downloadBacktestValidationReport,
  getBacktestResult,
  listBacktestResults,
} from '@/lib/api/backtests';
import { listBenchmarkOptions } from '@/lib/api/market';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { listStrategyVersions } from '@/lib/api/strategyStudio';
import type { BacktestJobSubmission, BacktestListItem, BacktestResultItem, BacktestResultsResponse } from '@/types/backtests';
import type { MarketBenchmarkOption } from '@/types/market';
import type { JobRecord, JobSubmissionRequest } from '@/types/jobs';
import type { ProfileRecord, ProfileDetailResponse } from '@/types/profile';
import type { StrategyVersionSummaryItem } from '@/types/strategyStudio';
import { selectLatestProfileSnapshot } from '@/features/strategy-workspace/strategy-workspace-utils';

const DEFAULT_BENCHMARK_SYMBOL = '000300.SH';

type BacktestFormState = {
  profileId: string;
  traderId: string;
  dateFrom: string;
  dateTo: string;
  strategyVersionId: string;
  symbols: string;
  benchmarkSymbol: string;
  mode: BacktestJobSubmission['mode'];
  configPath: string;
  useSnapshotOnly: boolean;
  scoringProfile: string;
};

type BacktestQueryState = {
  traderId: string;
  dateFrom: string;
  dateTo: string;
  skip: number;
  limit: number;
};

function formatPct(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'n/a';
  return `${(value * 100).toFixed(2)}%`;
}

function shiftDate(value: string, days: number) {
  return dayjs(value).subtract(days, 'day').format('YYYY-MM-DD');
}

function splitSymbols(value: string) {
  return value
    .split(/[\s,，]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function getSummary(value: BacktestListItem | BacktestResultItem | null | undefined) {
  if (!value || !value.summary || typeof value.summary !== 'object') return null;
  const summary = value.summary as Record<string, unknown>;
  return {
    total_days: typeof summary.total_days === 'number' ? summary.total_days : null,
    total_trades: typeof summary.total_trades === 'number' ? summary.total_trades : null,
    valid_trades: typeof summary.valid_trades === 'number' ? summary.valid_trades : null,
    skipped_trades: typeof summary.skipped_trades === 'number' ? summary.skipped_trades : null,
    win_rate: typeof summary.win_rate === 'number' ? summary.win_rate : null,
    avg_return_pct: typeof summary.avg_return_pct === 'number' ? summary.avg_return_pct : null,
  };
}

function getFingerprint(job: JobRecord | null | undefined) {
  const payload = job?.result && typeof job.result === 'object' ? (job.result as Record<string, unknown>) : null;
  const fingerprint = payload?.payload && typeof payload.payload === 'object' ? (payload.payload as Record<string, unknown>).fingerprint : null;
  return typeof fingerprint === 'string' ? fingerprint : null;
}

function getResultPayload(job: JobRecord | null | undefined) {
  const payload = job?.result && typeof job.result === 'object' ? (job.result as Record<string, unknown>) : null;
  return payload?.payload && typeof payload.payload === 'object' ? payload.payload : null;
}

function buildSubmission(form: BacktestFormState): BacktestJobSubmission {
  return {
    profileId: form.profileId,
    traderId: form.traderId.trim(),
    dateFrom: form.dateFrom,
    dateTo: form.dateTo,
    strategyVersionId: form.strategyVersionId.trim(),
    benchmarkSymbol: form.benchmarkSymbol,
    mode: form.mode,
    configPath: form.configPath.trim() || undefined,
    symbols: splitSymbols(form.symbols),
    useSnapshotOnly: form.useSnapshotOnly,
    scoringProfile: form.scoringProfile.trim() || 'stage5',
  };
}

function buildJobRequest(jobType: 'backtest-run' | 'backtest-validate-rules' | 'backtest-reproducibility-check', submission: BacktestJobSubmission): JobSubmissionRequest {
  const params =
    jobType === 'backtest-run'
      ? buildBacktestRunParams(submission)
      : jobType === 'backtest-validate-rules'
        ? buildBacktestValidateRulesParams(submission)
        : buildBacktestReproducibilityParams(submission);

  return {
    job_type: jobType,
    params,
    created_by: 'web',
    max_retries: 3,
    retry_backoff_seconds: 0,
    timeout_seconds: null,
  };
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-lg font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function ResultRow({
  item,
  active,
  onSelect,
}: {
  item: BacktestListItem;
  active: boolean;
  onSelect: () => void;
}) {
  const summary = getSummary(item);
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-2xl border p-4 text-left transition-colors cursor-pointer ${
        active ? 'border-sky-200 bg-sky-50' : 'border-slate-200 bg-white hover:border-sky-200 hover:bg-slate-50'
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">{item.result_id}</p>
          <p className="mt-1 break-all text-xs text-slate-500">
            {item.trader_id ?? '未知交易员'} · {item.date_from ?? 'n/a'} ~ {item.date_to ?? 'n/a'}
          </p>
        </div>
        <Badge variant="info">{summary?.total_trades ?? 0} 笔</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        {item.benchmark_symbol ? <span className="rounded-full border border-slate-200 px-2 py-1">Benchmark {item.benchmark_symbol}</span> : null}
        <span className="rounded-full border border-slate-200 px-2 py-1">胜率 {formatPct(summary?.win_rate)}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">平均收益 {formatPct(summary?.avg_return_pct)}</span>
      </div>
    </button>
  );
}

export function BacktestCenter() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { canAccess, principal } = useAuth();
  const today = useMemo(() => dayjs().format('YYYY-MM-DD'), []);
  const defaultStart = useMemo(() => shiftDate(today, 30), [today]);
  const canViewBacktest = canAccess('viewer');

  const [form, setForm] = useState<BacktestFormState>({
    profileId: '',
    traderId: '',
    dateFrom: defaultStart,
    dateTo: today,
    strategyVersionId: '',
    symbols: '',
    benchmarkSymbol: DEFAULT_BENCHMARK_SYMBOL,
    mode: 'full',
    configPath: '',
    useSnapshotOnly: true,
    scoringProfile: '',
  });
  const [resultQuery, setResultQuery] = useState<BacktestQueryState>({
    traderId: '',
    dateFrom: defaultStart,
    dateTo: today,
    skip: 0,
    limit: 8,
  });
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [lastJob, setLastJob] = useState<JobRecord | null>(null);

  const profilesQuery = useQuery({
    queryKey: ['backtest-center', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    enabled: canViewBacktest,
    staleTime: 60_000,
  });

  const strategyVersionsQuery = useQuery({
    queryKey: ['backtest-center', 'strategy-versions'],
    queryFn: () => listStrategyVersions({ skip: 0, limit: 100 }),
    enabled: canViewBacktest,
    staleTime: 60_000,
  });

  const resultsQuery = useQuery<BacktestResultsResponse, ApiError>({
    queryKey: ['backtest-center', 'results', resultQuery],
    queryFn: () =>
      listBacktestResults({
        trader_id: resultQuery.traderId || undefined,
        date_from: resultQuery.dateFrom || undefined,
        date_to: resultQuery.dateTo || undefined,
        skip: resultQuery.skip,
        limit: resultQuery.limit,
      }),
    enabled: canViewBacktest,
    staleTime: 10_000,
  });

  const results = useMemo(() => resultsQuery.data?.items ?? [], [resultsQuery.data?.items]);
  const profileItems = profilesQuery.data?.items ?? [];
  const strategyVersionItems = strategyVersionsQuery.data?.items ?? [];
  const filteredVersionItems = useMemo(
    () => strategyVersionItems.filter((item) => !form.traderId || item.trader_id === form.traderId),
    [form.traderId, strategyVersionItems],
  );

  useEffect(() => {
    if (!results.length) {
      setSelectedResultId(null);
      return;
    }
    if (!selectedResultId || !results.some((item) => item.result_id === selectedResultId)) {
      setSelectedResultId(results[0].result_id);
    }
  }, [results, selectedResultId]);

  const selectedResult = useMemo(
    () => results.find((item) => item.result_id === selectedResultId) ?? null,
    [results, selectedResultId],
  );

  useEffect(() => {
    if (!profileItems.length) {
      return;
    }
    if (!form.profileId || !profileItems.some((item) => item.profile_id === form.profileId)) {
      setForm((current) => ({ ...current, profileId: profileItems[0].profile_id }));
    }
  }, [form.profileId, profileItems]);

  useEffect(() => {
    if (!filteredVersionItems.length) {
      if (form.strategyVersionId) {
        setForm((current) => ({ ...current, strategyVersionId: '' }));
      }
      return;
    }
    if (!form.strategyVersionId || !filteredVersionItems.some((item) => item.version_id === form.strategyVersionId)) {
      setForm((current) => ({ ...current, strategyVersionId: filteredVersionItems[0].version_id }));
    }
  }, [filteredVersionItems, form.strategyVersionId]);

  const selectedProfileDetailQuery = useQuery<ProfileDetailResponse, ApiError>({
    queryKey: ['backtest-center', 'profile-detail', form.profileId],
    queryFn: () => getProfile(form.profileId),
    enabled: Boolean(form.profileId) && canViewBacktest,
    staleTime: 10_000,
  });

  const selectedProfileSnapshot = useMemo(
    () => selectLatestProfileSnapshot(selectedProfileDetailQuery.data ?? null),
    [selectedProfileDetailQuery.data],
  );
  const resolvedProfileConfigPath = selectedProfileSnapshot?.config_path?.trim() || 'config/app.yaml';

  useEffect(() => {
    setForm((current) => {
      if (current.configPath === resolvedProfileConfigPath) {
        return current;
      }
      return { ...current, configPath: resolvedProfileConfigPath };
    });
  }, [resolvedProfileConfigPath]);

  const detailQuery = useQuery({
    queryKey: ['backtest-center', 'detail', selectedResultId],
    queryFn: () => getBacktestResult(selectedResultId as string),
    enabled: Boolean(selectedResultId) && canViewBacktest,
  });

  const reportQuery = useQuery({
    queryKey: ['backtest-center', 'report', selectedResultId],
    queryFn: () => downloadBacktestReport(selectedResultId as string),
    enabled: Boolean(selectedResultId) && canViewBacktest,
  });

  const validationQuery = useQuery({
    queryKey: ['backtest-center', 'validation', selectedResultId],
    queryFn: () => downloadBacktestValidationReport(selectedResultId as string),
    enabled: Boolean(selectedResultId) && canViewBacktest,
  });

  const benchmarkOptionsQuery = useQuery({
    queryKey: ['backtest-center', 'benchmark-options'],
    queryFn: () => listBenchmarkOptions(50),
    enabled: canViewBacktest,
    staleTime: 60_000,
  });

  async function runBacktest(jobType: 'backtest-run' | 'backtest-validate-rules' | 'backtest-reproducibility-check') {
    setSubmissionError(null);
    const submission = buildSubmission(form);
    const params = buildJobRequest(jobType, submission);

    try {
      const result = await createJob(params);
      setLastJob((result as { job?: JobRecord }).job ?? null);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      await queryClient.invalidateQueries({ queryKey: ['backtest-center', 'results'] });
      setResultQuery({
        traderId: submission.traderId,
        dateFrom: submission.dateFrom,
        dateTo: submission.dateTo,
        skip: 0,
        limit: 8,
      });
    } catch (error) {
      setSubmissionError(error instanceof Error ? error.message : '回测任务提交失败');
    }
  }

  const selectedSummary = getSummary(detailQuery.data?.item ?? selectedResult);
  const fingerprint = getFingerprint(lastJob);
  const resultPayload = getResultPayload(lastJob);
  const benchmarkOptions = benchmarkOptionsQuery.data?.items ?? [];
  const profileConfigPathHint = selectedProfileSnapshot
    ? `已从最新快照解析配置路径：${selectedProfileSnapshot.config_path || 'config/app.yaml'}`
    : '配置路径将从所选 Profile 的最新快照自动解析。';

  if (!canViewBacktest) {
    return (
      <main className="page-stack">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-lg font-semibold text-slate-900">没有权限访问回测中心</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，查看回测至少需要 viewer 权限。</p>
        </section>
      </main>
    );
  }

  const submission = buildSubmission(form);
  const currentFilters = `交易员 ${resultQuery.traderId || '全部'} · ${resultQuery.dateFrom} ~ ${resultQuery.dateTo}`;

  return (
    <main className="page-stack">
      <div className="flex flex-wrap items-center justify-start gap-3">
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
          to="/backtest/regime"
        >
          进入 Regime 回测
        </Link>
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          to="/jobs"
        >
          打开任务中心
        </Link>
      </div>

      <PageHeader />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(320px,0.55fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="text-slate-950">回测参数</CardTitle>
                <CardDescription className="text-slate-600">选择 trader、日期范围、策略版本和运行模式。</CardDescription>
              </div>
              <Button
                variant="outline"
                className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                onClick={() => {
                  setResultQuery({
                    traderId: submission.traderId,
                    dateFrom: submission.dateFrom,
                    dateTo: submission.dateTo,
                    skip: 0,
                    limit: 8,
                  });
                }}
              >
                <RefreshCw className="mr-2 h-4 w-4" />
                按当前条件刷新
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Profile</span>
                <Select
                  aria-label="Profile"
                  className="border-slate-200 bg-white text-slate-900"
                  value={form.profileId}
                  onChange={(event) => setForm((current) => ({ ...current, profileId: event.target.value }))}
                  disabled={profilesQuery.isLoading || profileItems.length === 0}
                >
                  {profileItems.length === 0 ? <option value="">暂无可用 Profile</option> : null}
                  {profileItems.map((profile: ProfileRecord) => (
                    <option key={profile.profile_id} value={profile.profile_id}>
                      {profile.name} ({profile.profile_id})
                    </option>
                  ))}
                </Select>
                <p className="text-xs text-slate-500">{profileConfigPathHint}</p>
                {profilesQuery.isError ? <p className="text-xs text-rose-600">Profile 列表加载失败，请稍后重试。</p> : null}
                {selectedProfileDetailQuery.isError ? <p className="text-xs text-rose-600">Profile 详情加载失败，当前使用默认配置路径。</p> : null}
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">交易员 ID</span>
                <TraderIdSelect
                  ariaLabel="交易员 ID"
                  className="border-slate-200 bg-white text-slate-900"
                  onChange={(traderId) => setForm((current) => ({ ...current, traderId }))}
                  source="strategy"
                  value={form.traderId}
                />
                <p className="text-xs text-slate-500">来源于策略版本全量交易员集合，不再依赖当前页已加载的数据。</p>
                {strategyVersionsQuery.isError ? <p className="text-xs text-rose-600">策略版本列表加载失败，请稍后重试。</p> : null}
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">策略版本 ID</span>
                <Select
                  aria-label="策略版本 ID"
                  className="border-slate-200 bg-white text-slate-900"
                  value={form.strategyVersionId}
                  onChange={(event) => setForm((current) => ({ ...current, strategyVersionId: event.target.value }))}
                  disabled={strategyVersionsQuery.isLoading || filteredVersionItems.length === 0}
                >
                  {filteredVersionItems.length === 0 ? <option value="">暂无可用策略版本</option> : null}
                  {filteredVersionItems.map((item: StrategyVersionSummaryItem) => (
                    <option key={item.version_id} value={item.version_id}>
                      {item.version_id}
                    </option>
                  ))}
                </Select>
                <p className="text-xs text-slate-500">仅显示当前交易员下的版本。</p>
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">开始日期</span>
                <Input
                  aria-label="开始日期"
                  className="border-slate-200 bg-white text-slate-900"
                  type="date"
                  value={form.dateFrom}
                  onChange={(event) => setForm((current) => ({ ...current, dateFrom: event.target.value }))}
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">结束日期</span>
                <Input
                  aria-label="结束日期"
                  className="border-slate-200 bg-white text-slate-900"
                  type="date"
                  value={form.dateTo}
                  onChange={(event) => setForm((current) => ({ ...current, dateTo: event.target.value }))}
                />
              </label>
              <label className="space-y-2 md:col-span-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">标的列表</span>
                <Input
                  aria-label="标的列表"
                  className="border-slate-200 bg-white text-slate-900"
                  value={form.symbols}
                  onChange={(event) => setForm((current) => ({ ...current, symbols: event.target.value }))}
                  placeholder="000001.SZ, 000002.SZ"
                />
                <p className="text-xs text-slate-500">使用逗号或空格分隔，留空表示全部标的。</p>
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Benchmark</span>
                <Select
                  aria-label="Benchmark 选择"
                  className="border-slate-200 bg-white text-slate-900"
                  value={form.benchmarkSymbol}
                  onChange={(event) => setForm((current) => ({ ...current, benchmarkSymbol: event.target.value }))}
                  disabled={benchmarkOptionsQuery.isLoading && benchmarkOptions.length === 0}
                >
                  {benchmarkOptions.length === 0 ? (
                    <option value={DEFAULT_BENCHMARK_SYMBOL}>{`沪深300 (${DEFAULT_BENCHMARK_SYMBOL})`}</option>
                  ) : null}
                  {benchmarkOptions.map((item: MarketBenchmarkOption) => (
                    <option key={item.symbol} value={item.symbol}>
                      {item.name} ({item.symbol})
                    </option>
                  ))}
                </Select>
                <p className="text-xs text-slate-500">默认使用沪深300，可按回测口径切换指数基准。</p>
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">回测模式</span>
                <Select
                  aria-label="回测模式"
                  className="border-slate-200 bg-white text-slate-900"
                  value={form.mode}
                  onChange={(event) => setForm((current) => ({ ...current, mode: event.target.value as BacktestJobSubmission['mode'] }))}
                >
                  <option value="full">全量</option>
                  <option value="replay">重放</option>
                  <option value="rule_validation">规则验真</option>
                </Select>
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">评分口径</p>
                <p className="mt-2 text-sm font-medium text-slate-900">统一回测评分口径</p>
                <p className="mt-1 text-xs text-slate-500">按 MFE / MAE / return_pct 计算，并包含 T+1 与涨跌停约束。当前为固定口径，不提供切换。</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">快照模式</p>
                <p className="mt-2 text-sm font-medium text-slate-900">仅使用快照数据</p>
                <p className="mt-1 text-xs text-slate-500">该回测当前固定使用快照链路，不再提供切换。</p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <Button onClick={() => void runBacktest('backtest-run')}>运行回测</Button>
              <Button variant="outline" onClick={() => void runBacktest('backtest-validate-rules')}>
                验证规则
              </Button>
              <Button variant="secondary" onClick={() => void runBacktest('backtest-reproducibility-check')}>
                可复现性检查
              </Button>
            </div>

            {submissionError ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{submissionError}</div>
            ) : null}
            {benchmarkOptionsQuery.isError ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                Benchmark 选项加载失败，当前回退到默认沪深300。
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader>
              <CardTitle className="text-slate-950">最近运行</CardTitle>
              <CardDescription className="text-slate-600">提交后可在这里查看 fingerprint 和任务入口。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <MetricCard label="当前结果" value={selectedResult?.result_id ?? '未选择结果'} />
              <MetricCard label="当前 Benchmark" value={form.benchmarkSymbol || DEFAULT_BENCHMARK_SYMBOL} />
              <MetricCard label="最近 fingerprint" value={fingerprint ? `${fingerprint.slice(0, 16)}…` : '提交后可见'} />
              <MetricCard label="最近任务" value={lastJob?.id ?? '暂无'} />
              <div className="flex gap-2">
                <Button
                  className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  variant="outline"
                  disabled={!lastJob?.id}
                  onClick={() => {
                    if (lastJob?.id) navigate(`/jobs/${encodeURIComponent(lastJob.id)}`);
                  }}
                >
                  前往任务详情
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
              {resultPayload ? (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                  <p className="font-medium text-slate-900">最近结果已写入任务结果</p>
                  <p className="mt-1">fingerprint、summary 和 records 会跟随 Job Detail 一起保存。</p>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card className="border-slate-200 bg-white shadow-sm">
            <CardHeader>
              <CardTitle className="text-slate-950">结果摘要</CardTitle>
              <CardDescription className="text-slate-600">{currentFilters}</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 md:grid-cols-2">
              <MetricCard label="总结果数" value={resultsQuery.data?.total ?? 0} />
              <MetricCard label="当前页结果" value={results.length} />
              <MetricCard label="总交易数" value={selectedSummary?.total_trades ?? 'n/a'} />
              <MetricCard label="胜率" value={formatPct(selectedSummary?.win_rate)} />
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="text-slate-950">最近结果</CardTitle>
                <CardDescription className="text-slate-600">按当前查询条件列出最近的回测结果。</CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  variant="outline"
                  onClick={() =>
                    setResultQuery({
                      traderId: '',
                      dateFrom: defaultStart,
                      dateTo: today,
                      skip: 0,
                      limit: 8,
                    })
                  }
                >
                  重置查询
                </Button>
                <Button
                  className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  variant="outline"
                  onClick={() =>
                    setResultQuery({
                      traderId: resultQuery.traderId,
                      dateFrom: shiftDate(today, 30),
                      dateTo: today,
                      skip: 0,
                      limit: 8,
                    })
                  }
                >
                  最近 30 天
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {resultsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : resultsQuery.error ? (
              <ErrorState
                {...buildErrorRecoveryState(resultsQuery.error, 'backtest-results')}
                onRetry={() => {
                  void resultsQuery.refetch();
                }}
              />
            ) : !results.length ? (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                <p className="text-base font-semibold text-slate-950">当前筛选范围内暂无回测结果。</p>
                <p className="mt-2">你可以放宽日期范围、切换交易员，或者先运行一次回测。</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button variant="outline" onClick={() => setResultQuery({ traderId: '', dateFrom: defaultStart, dateTo: today, skip: 0, limit: 8 })}>
                    重置查询
                  </Button>
                  <Button variant="outline" onClick={() => setResultQuery({ traderId: '', dateFrom: shiftDate(today, 30), dateTo: today, skip: 0, limit: 8 })}>
                    最近 30 天
                  </Button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {results.map((item) => (
                  <ResultRow key={item.result_id} active={item.result_id === selectedResultId} item={item} onSelect={() => setSelectedResultId(item.result_id)} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="text-slate-950">结果工作区</CardTitle>
                <CardDescription className="text-slate-600">{selectedResult ? selectedResult.result_id : '选择一个结果查看详情。'}</CardDescription>
              </div>
              {selectedResult ? <Badge variant="info">{selectedResult.date_from ?? selectedResult.request_date_from} ~ {selectedResult.date_to ?? selectedResult.request_date_to}</Badge> : null}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedResult ? (
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">尚未选择任何回测结果。</div>
            ) : detailQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-64 w-full" />
              </div>
            ) : detailQuery.error ? (
              <ErrorState
                {...buildErrorRecoveryState(detailQuery.error, 'backtest-detail')}
                onRetry={() => {
                  void detailQuery.refetch();
                }}
              />
            ) : detailQuery.data ? (
              <Tabs defaultValue="summary" className="w-full">
                <TabsList className="flex flex-wrap">
                  <TabsTrigger value="summary">摘要</TabsTrigger>
                  <TabsTrigger value="report">报告</TabsTrigger>
                  <TabsTrigger value="validation">验真</TabsTrigger>
                  <TabsTrigger value="json">JSON</TabsTrigger>
                </TabsList>

                <TabsContent value="summary" className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <MetricCard label="总天数" value={selectedSummary?.total_days ?? 'n/a'} />
                    <MetricCard label="有效交易" value={selectedSummary?.valid_trades ?? 'n/a'} />
                    <MetricCard label="跳过交易" value={selectedSummary?.skipped_trades ?? 'n/a'} />
                    <MetricCard label="平均收益" value={formatPct(selectedSummary?.avg_return_pct)} />
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <h3 className="font-semibold text-slate-950">最近记录</h3>
                      <span className="text-xs text-slate-500">{detailQuery.data.item.records.length} 条</span>
                    </div>
                    {detailQuery.data.item.records.length ? (
                      <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white">
                        <table className="min-w-full divide-y divide-slate-200 text-sm">
                          <thead className="bg-slate-50 text-left text-xs uppercase tracking-[0.12em] text-slate-500">
                            <tr>
                              <th className="px-4 py-3">日期</th>
                              <th className="px-4 py-3">标的</th>
                              <th className="px-4 py-3">状态</th>
                              <th className="px-4 py-3">收益</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-200">
                            {detailQuery.data.item.records.slice(0, 6).map((record) => (
                              <tr key={`${record.trade_date}-${record.symbol}`}>
                                <td className="px-4 py-3 text-slate-700">{record.trade_date}</td>
                                <td className="px-4 py-3 text-slate-900">{record.symbol}</td>
                                <td className="px-4 py-3 text-slate-700">{record.status}</td>
                                <td className="px-4 py-3 text-slate-700">{formatPct(record.return_pct)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="mt-3 text-sm text-slate-600">暂无交易记录。</p>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="report">
                  {reportQuery.isLoading ? (
                    <Skeleton className="h-64 w-full" />
                  ) : reportQuery.error ? (
                    <ErrorState
                      {...buildErrorRecoveryState(reportQuery.error, 'backtest-report')}
                      onRetry={() => {
                        void reportQuery.refetch();
                      }}
                    />
                  ) : (
                    <ArtifactPreview kind="markdown" content={reportQuery.data ?? ''} title="回测报告" />
                  )}
                </TabsContent>

                <TabsContent value="validation">
                  {validationQuery.isLoading ? (
                    <Skeleton className="h-64 w-full" />
                  ) : validationQuery.error ? (
                    <ErrorState
                      {...buildErrorRecoveryState(validationQuery.error, 'backtest-validation')}
                      onRetry={() => {
                        void validationQuery.refetch();
                      }}
                    />
                  ) : (
                    <ArtifactPreview kind="markdown" content={validationQuery.data ?? ''} title="规则验真报告" />
                  )}
                </TabsContent>

                <TabsContent value="json">
                  <JsonViewer value={detailQuery.data.item} title="回测结果 JSON" />
                </TabsContent>
              </Tabs>
            ) : null}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
