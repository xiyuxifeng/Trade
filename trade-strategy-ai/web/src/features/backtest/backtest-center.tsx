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
import { JsonViewer, LoadingState } from '@/components/kit';
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
import { listArticleMetadataSummary } from '@/lib/api/article-metadata';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import type { BacktestJobSubmission, BacktestListItem, BacktestResultItem, BacktestResultsResponse } from '@/types/backtests';
import type { ArticleMetadataResolutionListResponse } from '@/types/article-metadata';
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

function getSubmissionErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) return '当前账号没有权限提交回测任务。';
    if (error.status === 400) return '回测参数不完整或不合法，请检查后重试。';
    if (error.status === 404) return '未找到可用的回测数据，请返回上一步重新选择。';
    return '回测任务提交失败，请稍后重试。';
  }

  return '回测任务提交失败，请稍后重试。';
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
        {item.benchmark_symbol ? <span className="rounded-full border border-slate-200 px-2 py-1">基准指数 {item.benchmark_symbol}</span> : null}
        <span className="rounded-full border border-slate-200 px-2 py-1">胜率 {formatPct(summary?.win_rate)}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">平均收益 {formatPct(summary?.avg_return_pct)}</span>
      </div>
    </button>
  );
}

export function BacktestCenter({ productMode = false }: { productMode?: boolean } = {}) {
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
  const [submittingJobType, setSubmittingJobType] = useState<'backtest-run' | 'backtest-validate-rules' | 'backtest-reproducibility-check' | null>(null);
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [submissionJobId, setSubmissionJobId] = useState<string | null>(null);
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
  const selectedStrategyVersionDetailQuery = useQuery({
    queryKey: ['backtest-center', 'strategy-version-detail', form.strategyVersionId],
    queryFn: () => getStrategyVersion(form.strategyVersionId),
    enabled: Boolean(form.strategyVersionId) && canViewBacktest,
    staleTime: 30_000,
  });
  const selectedStrategyVersionDetail = selectedStrategyVersionDetailQuery.data?.item ?? null;
  const sourceArticleIds = selectedStrategyVersionDetail?.source_article_ids ?? [];
  const sourceMetadataQuery = useQuery<ArticleMetadataResolutionListResponse>({
    queryKey: ['backtest-center', 'source-article-metadata', selectedStrategyVersionDetail?.version_id, sourceArticleIds.join(',')],
    queryFn: () => listArticleMetadataSummary(sourceArticleIds),
    enabled: Boolean(selectedStrategyVersionDetail && sourceArticleIds.length > 0) && canViewBacktest,
    staleTime: 30_000,
  });
  const sourceMetadataById = useMemo(
    () => new Map((sourceMetadataQuery.data?.items ?? []).map((item) => [item.article_id, item])),
    [sourceMetadataQuery.data?.items],
  );
  function renderScoreReasons(reasons: string[] | undefined | null) {
    if (!reasons || reasons.length === 0) {
      return <p className="mt-2 text-xs text-slate-500">暂无评分原因。</p>;
    }
    return (
      <div className="mt-2 flex flex-wrap gap-2">
        {reasons.slice(0, 4).map((reason) => (
          <span key={reason} className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-600">
            {reason}
          </span>
        ))}
        {reasons.length > 4 ? <span className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-500">+{reasons.length - 4}</span> : null}
      </div>
    );
  }

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
    setSubmissionMessage(null);
    setSubmissionJobId(null);
    setSubmittingJobType(jobType);
    const submission = buildSubmission(form);
    const params = buildJobRequest(jobType, submission);

    try {
      const result = await createJob(params);
      const job = (result as { job?: JobRecord }).job ?? null;
      setLastJob(job);
      setSubmissionJobId(job?.id ?? null);
      if (job?.id) {
        setSubmissionMessage(`回测任务已提交，Job ${job.id} 已创建，可打开 Job 详情查看进度。`);
      }
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
      setSubmissionError(getSubmissionErrorMessage(error));
      setSubmissionMessage(null);
      setSubmissionJobId(null);
    } finally {
      setSubmittingJobType(null);
    }
  }

  const selectedSummary = getSummary(detailQuery.data?.item ?? selectedResult);
  const fingerprint = getFingerprint(lastJob);
  const resultPayload = getResultPayload(lastJob);
  const benchmarkOptions = benchmarkOptionsQuery.data?.items ?? [];
  const profileConfigPathHint = selectedProfileSnapshot
    ? `已绑定最新画像快照：${selectedProfileSnapshot.snapshot_id}`
    : '配置上下文将从所选画像的最新快照自动解析。';

  if (!canViewBacktest) {
    return (
      <main className="page-stack">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-lg font-semibold text-slate-900">没有权限访问回测与画像</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，查看回测至少需要 viewer 权限。</p>
        </section>
      </main>
    );
  }

  const submission = buildSubmission(form);
  const currentFilters = `交易员 ${resultQuery.traderId || '全部'} · ${resultQuery.dateFrom} ~ ${resultQuery.dateTo}`;

  if (productMode) {
    const unavailableInput =
      profilesQuery.isLoading
      || strategyVersionsQuery.isLoading
      || benchmarkOptionsQuery.isLoading
      || !form.profileId
      || !form.strategyVersionId
      || benchmarkOptions.length === 0;

    return (
      <div className="space-y-4">
        {submissionError ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
            <p className="font-medium">回测提交失败</p>
            <p className="mt-1">{submissionError}</p>
          </div>
        ) : null}
        {submissionMessage ? (
          <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900">
            回测已提交。结果生成后会自动进入最近结果列表。
          </div>
        ) : null}
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2 text-sm text-slate-700">
            <span>画像</span>
            <Select
              aria-label="画像"
              value={form.profileId}
              onChange={(event) => setForm((current) => ({ ...current, profileId: event.target.value }))}
            >
              {profileItems.length === 0 ? <option value="">暂无可用画像</option> : null}
              {profileItems.map((profile) => (
                <option key={profile.profile_id} value={profile.profile_id}>
                  {profile.name}
                </option>
              ))}
            </Select>
          </label>
          <label className="space-y-2 text-sm text-slate-700">
            <span>规则版本</span>
            <Select
              aria-label="规则版本"
              value={form.strategyVersionId}
              onChange={(event) => setForm((current) => ({ ...current, strategyVersionId: event.target.value }))}
            >
              {filteredVersionItems.length === 0 ? <option value="">暂无可用规则版本</option> : null}
              {filteredVersionItems.map((item) => (
                <option key={item.version_id} value={item.version_id}>
                  {item.strategy_date} · {item.status}
                </option>
              ))}
            </Select>
          </label>
          <label className="space-y-2 text-sm text-slate-700">
            <span>开始日期</span>
            <Input type="date" value={form.dateFrom} onChange={(event) => setForm((current) => ({ ...current, dateFrom: event.target.value }))} />
          </label>
          <label className="space-y-2 text-sm text-slate-700">
            <span>结束日期</span>
            <Input type="date" value={form.dateTo} onChange={(event) => setForm((current) => ({ ...current, dateTo: event.target.value }))} />
          </label>
          <label className="space-y-2 text-sm text-slate-700 md:col-span-2">
            <span>基准指数</span>
            <Select
              aria-label="基准指数选择"
              value={form.benchmarkSymbol}
              onChange={(event) => setForm((current) => ({ ...current, benchmarkSymbol: event.target.value }))}
            >
              {benchmarkOptions.length === 0 ? <option value="">暂无可用基准</option> : null}
              {benchmarkOptions.map((item) => (
                <option key={item.symbol} value={item.symbol}>
                  {item.name}
                </option>
              ))}
            </Select>
          </label>
        </div>
        <Button disabled={Boolean(submittingJobType) || unavailableInput} onClick={() => void runBacktest('backtest-run')}>
          {submittingJobType ? '提交中' : '开始回测'}
        </Button>
        <div className="rounded-2xl border border-slate-200 bg-white p-4">
          <p className="font-medium text-slate-950">最近回测结果</p>
          {resultsQuery.isLoading ? (
            <LoadingState label="正在加载回测结果" description="正在读取已保存的真实结果。" />
          ) : results.length ? (
            <div className="mt-3 space-y-3">
              {results.map((item) => (
                <ResultRow key={item.result_id} active={item.result_id === selectedResultId} item={item} onSelect={() => setSelectedResultId(item.result_id)} />
              ))}
            </div>
          ) : (
            <p className="mt-2 text-sm text-slate-600">当前范围暂无回测结果，不会显示为零或成功。</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <main className="page-stack">
      {submissionMessage ? (
        <Card className="border-sky-200 bg-sky-50 text-sky-900 shadow-sm">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div>
              <p className="font-medium">{submissionMessage}</p>
              <p className="text-sm text-sky-700">
                {submissionJobId ? '任务已通过 Job Center 创建，不需要 CLI。' : '任务已进入 Job Center。'}
              </p>
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
      {submissionError ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          回测任务提交失败：{submissionError}
        </div>
      ) : null}

      <div className="flex flex-wrap items-center justify-start gap-3">
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
          to="/backtest/regime"
        >
          进入市场状态回测
        </Link>
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          to="/system/jobs"
        >
          打开任务中心
        </Link>
      </div>

      <PageHeader
        kicker="回测与画像"
        title="回测与画像"
        description="验证规则可信度，并沉淀交易员画像。"
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(320px,0.55fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="text-slate-950">回测参数</CardTitle>
                <CardDescription className="text-slate-600">选择交易员、日期范围、规则版本和运行模式。</CardDescription>
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
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">画像</span>
                <Select
                  aria-label="画像"
                  className="border-slate-200 bg-white text-slate-900"
                  value={form.profileId}
                  onChange={(event) => setForm((current) => ({ ...current, profileId: event.target.value }))}
                  disabled={profilesQuery.isLoading || profileItems.length === 0}
                >
                  {profileItems.length === 0 ? <option value="">暂无可用画像</option> : null}
                  {profileItems.map((profile: ProfileRecord) => (
                    <option key={profile.profile_id} value={profile.profile_id}>
                      {profile.name} ({profile.profile_id})
                    </option>
                  ))}
                </Select>
                <p className="text-xs text-slate-500">{profileConfigPathHint}</p>
                {profilesQuery.isError ? <p className="text-xs text-rose-600">画像列表加载失败，请稍后重试。</p> : null}
                {selectedProfileDetailQuery.isError ? <p className="text-xs text-rose-600">画像详情加载失败，当前无法预览最新快照。</p> : null}
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
                <p className="text-xs text-slate-500">来源于规则版本全集，不再依赖当前页已加载的数据。</p>
                {strategyVersionsQuery.isError ? <p className="text-xs text-rose-600">规则版本列表加载失败，请稍后重试。</p> : null}
              </label>
              <label className="space-y-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">规则版本 ID</span>
                <Select
                  aria-label="规则版本 ID"
                  className="border-slate-200 bg-white text-slate-900"
                  value={form.strategyVersionId}
                  onChange={(event) => setForm((current) => ({ ...current, strategyVersionId: event.target.value }))}
                  disabled={strategyVersionsQuery.isLoading || filteredVersionItems.length === 0}
                >
                  {filteredVersionItems.length === 0 ? <option value="">暂无可用规则版本</option> : null}
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
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">基准指数</span>
                <Select
                  aria-label="基准指数选择"
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
                <p className="text-xs text-slate-500">默认使用沪深300，可按回测口径切换基准指数。</p>
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
                  <option value="rule_validation">规则验证</option>
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
              <Button disabled={Boolean(submittingJobType)} onClick={() => void runBacktest('backtest-run')}>
                {submittingJobType === 'backtest-run' ? '提交中' : '运行回测'}
              </Button>
              <Button
                variant="outline"
                disabled={Boolean(submittingJobType)}
                onClick={() => void runBacktest('backtest-validate-rules')}
              >
                {submittingJobType === 'backtest-validate-rules' ? '提交中' : '验证规则'}
              </Button>
              <Button
                variant="secondary"
                disabled={Boolean(submittingJobType)}
                onClick={() => void runBacktest('backtest-reproducibility-check')}
              >
                {submittingJobType === 'backtest-reproducibility-check' ? '提交中' : '可复现性检查'}
              </Button>
            </div>

              {selectedStrategyVersionDetail ? (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">规则版本来源</p>
                      <p className="mt-2 text-sm font-medium text-slate-900">{selectedStrategyVersionDetail.version_id}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        交易员 {selectedStrategyVersionDetail.trader_id} · 分析日期 {selectedStrategyVersionDetail.strategy_date} · 状态 {selectedStrategyVersionDetail.status}
                      </p>
                      <p className="mt-2 text-xs text-slate-500">
                        这里仅展示该规则版本引用的来源文章版本信息；回测仍只消费已选中的规则版本，不在此处切换版本。
                      </p>
                    </div>
                    <Badge variant="info">{sourceArticleIds.length} 篇来源文章</Badge>
                  </div>
                <div className="mt-4 space-y-3">
                  {selectedStrategyVersionDetail.source_article_ids.length ? (
                    selectedStrategyVersionDetail.source_article_ids.slice(0, 5).map((articleId) => {
                      const resolution = sourceMetadataById.get(articleId);
                      const selectedCandidate = resolution?.candidates.find((candidate) => candidate.schema_version === resolution.selected_schema_version);
                      const recommendedCandidate = resolution?.candidates.find((candidate) => candidate.schema_version === resolution.recommended_schema_version);
                      return (
                        <div key={articleId} className="rounded-xl border border-slate-200 bg-white p-3">
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div>
                              <p className="text-sm font-medium text-slate-950">{articleId}</p>
                              <p className="mt-1 text-xs text-slate-500">
                                当前版本：{resolution?.selected_schema_version ?? '未记录'} · 推荐版本：{resolution?.recommended_schema_version ?? '未记录'}
                              </p>
                            </div>
                            <Badge variant={resolution?.selection_mode === 'manual' ? 'warning' : 'info'}>
                              {resolution?.selection_mode === 'manual' ? '手动选择' : '自动推荐'}
                            </Badge>
                          </div>
                          <p className="mt-2 text-xs leading-6 text-slate-500">
                            {resolution?.selection_reason ?? resolution?.recommended_reason ?? '暂无来源版本说明'}
                          </p>
                          <div className="mt-3 grid gap-3 md:grid-cols-2">
                            <div>
                              <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">当前版本评分原因</p>
                              {renderScoreReasons(selectedCandidate?.score_reasons)}
                            </div>
                            <div>
                              <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">推荐版本评分原因</p>
                              {renderScoreReasons(recommendedCandidate?.score_reasons)}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-sm text-slate-600">该规则版本没有来源文章。</p>
                  )}
                </div>
                {sourceMetadataQuery.isLoading ? <p className="mt-3 text-xs text-slate-500">正在读取来源文章版本信息…</p> : null}
                {sourceMetadataQuery.error ? <p className="mt-3 text-xs text-rose-600">来源文章版本信息加载失败，请稍后重试。</p> : null}
              </div>
            ) : null}

            <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-medium text-slate-950">高级功能：候选版本</p>
                    <Badge variant="info">独立页面</Badge>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">
                    候选版本生成与审核已经拆到独立页面，主回测页只保留一个轻入口。
                  </p>
                </div>
                <Link
                  className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
                  to="/backtest/candidates"
                >
                  打开候选页面
                </Link>
              </div>
            </div>

            {benchmarkOptionsQuery.isError ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                基准指数选项加载失败，当前回退到默认沪深300。
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
              <MetricCard label="当前基准指数" value={form.benchmarkSymbol || DEFAULT_BENCHMARK_SYMBOL} />
              <MetricCard label="最近 fingerprint" value={fingerprint ? `${fingerprint.slice(0, 16)}…` : '提交后可见'} />
              <MetricCard label="最近任务" value={lastJob?.id ?? '暂无'} />
              <div className="flex gap-2">
                <Button
                  className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  variant="outline"
                  disabled={!lastJob?.id}
                  onClick={() => {
                    if (lastJob?.id) navigate(`/system/jobs/${encodeURIComponent(lastJob.id)}`);
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
