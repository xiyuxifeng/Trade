/**
 * Deprecated legacy backtest workspace implementation.
 *
 * This file is intentionally kept for reference and should not be wired into
 * routes or page exports. The active backtest workspace is
 * `web/src/features/backtest/backtest-center.tsx`.
 */
import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/layout/page-header';
import { TraderIdSelect } from '@/components/inputs/trader-id-select';
import { ArtifactPreview } from '@/components/artifacts/artifact-preview';
import { ApiError } from '@/lib/api/http';
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
import type { JobSubmissionRequest } from '@/types/jobs';
import type { BacktestJobSubmission, BacktestListItem, BacktestResultItem, BacktestResultsResponse } from '@/types/backtests';
import type { MarketBenchmarkOption } from '@/types/market';

const DEFAULT_SCORING_PROFILE = 'stage5';
const DEFAULT_BENCHMARK_SYMBOL = '000300.SH';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '回测数据加载失败';
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatPct(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'n/a';
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'n/a';
  return value.toLocaleString('zh-CN');
}

function shiftDate(value: string, days: number) {
  return dayjs(value).subtract(days, 'day').format('YYYY-MM-DD');
}

function statusTone(status: string) {
  if (status === 'closed' || status === 'validated') return 'text-emerald-300';
  if (status === 'skipped' || status === 'missing_field' || status === 'missing_snapshot') return 'text-amber-300';
  if (status === 'invalid' || status === 'unsupported_rule' || status === 'invalid_rule') return 'text-rose-300';
  return 'text-slate-300';
}

function sortResultsDesc(items: BacktestListItem[]) {
  return [...items].sort((left, right) => {
    const rightDate = right.date_to ?? right.date_from ?? '';
    const leftDate = left.date_to ?? left.date_from ?? '';
    const dateDiff = rightDate.localeCompare(leftDate);
    if (dateDiff !== 0) return dateDiff;
    return right.result_id.localeCompare(left.result_id);
  });
}

function toJobSubmission(form: BacktestJobFormState): BacktestJobSubmission {
  return {
    profileId: form.profileId,
    traderId: form.traderId,
    dateFrom: form.dateFrom,
    dateTo: form.dateTo,
    strategyVersionId: form.strategyVersionId,
    benchmarkSymbol: form.benchmarkSymbol,
    mode: form.mode,
    symbols: form.symbols,
    useSnapshotOnly: form.useSnapshotOnly,
    scoringProfile: form.scoringProfile,
  };
}

type BacktestJobFormState = {
  profileId: string;
  traderId: string;
  dateFrom: string;
  dateTo: string;
  strategyVersionId: string;
  mode: 'full' | 'replay' | 'rule_validation';
  symbols: string[];
  benchmarkSymbol: string;
  useSnapshotOnly: boolean;
  scoringProfile: string;
};

function SummaryCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function BacktestSparkline({ records }: { records: BacktestResultItem['records'] }) {
  const series = records
    .map((record, index) => ({ index, value: record.return_pct }))
    .filter((item): item is { index: number; value: number } => typeof item.value === 'number');

  if (!series.length) {
    return <p className="text-sm text-slate-400">暂无可视化收益率序列。</p>;
  }

  const values = series.map((item) => item.value);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 0);
  const width = 640;
  const height = 200;
  const paddingX = 24;
  const paddingY = 20;
  const usableWidth = width - paddingX * 2;
  const usableHeight = height - paddingY * 2;
  const span = max - min || 1;
  const points = series.map((item, index) => {
    const x = paddingX + (usableWidth * index) / Math.max(series.length - 1, 1);
    const y = paddingY + ((max - item.value) / span) * usableHeight;
    return { x, y };
  });
  const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ');

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-100">收益率曲线</h4>
        <Badge variant="info">{series.length} 个样本</Badge>
      </div>
      <svg aria-label="收益率曲线" className="mt-4 h-52 w-full" viewBox={`0 0 ${width} ${height}`}>
        <defs>
          <linearGradient id="backtest-line" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#22c55e" />
          </linearGradient>
        </defs>
        <line x1={paddingX} x2={width - paddingX} y1={height - paddingY} y2={height - paddingY} stroke="rgba(148,163,184,0.18)" />
        <path d={path} fill="none" stroke="url(#backtest-line)" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        {points.map((point, index) => (
          <circle key={`${point.x}-${point.y}-${index}`} cx={point.x} cy={point.y} r="4" fill="#22c55e" />
        ))}
      </svg>
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
  const summary = item.summary as Partial<BacktestSummaryShape> & Record<string, unknown>;
  const totalTrades = typeof summary.total_trades === 'number' ? summary.total_trades : null;
  const winRate = typeof summary.win_rate === 'number' ? summary.win_rate : null;

  return (
    <button
      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
        active
          ? 'border-sky-500/40 bg-sky-500/10 text-sky-100'
          : 'border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
      }`}
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-medium">{item.result_id}</p>
          <p className="text-xs text-slate-500">
            {item.trader_id ?? '未知交易员'} · {item.date_from ?? 'n/a'} ~ {item.date_to ?? 'n/a'}
          </p>
        </div>
        <Badge variant={active ? 'info' : 'default'}>{totalTrades !== null ? `${totalTrades} 笔交易` : '回测'}</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        {item.benchmark_symbol ? <span className="rounded-full border border-slate-800/80 px-2 py-1">Benchmark {item.benchmark_symbol}</span> : null}
        {winRate !== null ? <span className="rounded-full border border-slate-800/80 px-2 py-1">胜率 {formatPct(winRate)}</span> : null}
        <span className="rounded-full border border-slate-800/80 px-2 py-1">{formatTimestamp(item.date_to ?? item.date_from)}</span>
      </div>
    </button>
  );
}

type BacktestSummaryShape = {
  total_days: number;
  total_trades: number;
  valid_trades: number;
  skipped_trades: number;
  win_rate: number | null;
  avg_return_pct: number | null;
};

function DetailSummary({ detail }: { detail: BacktestResultItem }) {
  const summary = detail.summary;
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="backtest-detail-summary">
      <SummaryCard title="Benchmark" value={detail.benchmark_symbol ?? 'n/a'} accent="text-sky-300" />
      <SummaryCard title="总天数" value={summary ? formatNumber(summary.total_days) : 'n/a'} accent="text-sky-300" />
      <SummaryCard title="总交易数" value={summary ? formatNumber(summary.total_trades) : 'n/a'} />
      <SummaryCard title="有效交易" value={summary ? formatNumber(summary.valid_trades) : 'n/a'} accent="text-emerald-300" />
      <SummaryCard title="跳过交易" value={summary ? formatNumber(summary.skipped_trades) : 'n/a'} />
      <SummaryCard title="胜率" value={summary ? formatPct(summary.win_rate) : 'n/a'} accent="text-emerald-300" />
      <SummaryCard title="平均收益" value={summary ? formatPct(summary.avg_return_pct) : 'n/a'} />
      <SummaryCard
        title="有效占比"
        value={summary && summary.total_trades ? formatPct(summary.valid_trades / summary.total_trades) : 'n/a'}
        accent="text-sky-300"
      />
    </div>
  );
}

export function BacktestsCenter() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const today = useMemo(() => dayjs().format('YYYY-MM-DD'), []);
  const defaultStart = useMemo(() => dayjs().subtract(30, 'day').format('YYYY-MM-DD'), []);

  const [traderId, setTraderId] = useState('');
  const [dateFrom, setDateFrom] = useState(defaultStart);
  const [dateTo, setDateTo] = useState(today);
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(50);
  const [strategyVersionId, setStrategyVersionId] = useState('');
  const [benchmarkSymbol, setBenchmarkSymbol] = useState(DEFAULT_BENCHMARK_SYMBOL);
  const [mode, setMode] = useState<'full' | 'replay' | 'rule_validation'>('full');
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [submittedJobId, setSubmittedJobId] = useState<string | null>(null);
  const [submittedJobType, setSubmittedJobType] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [reportViewMode, setReportViewMode] = useState<'preview' | 'raw'>('preview');
  const [validationViewMode, setValidationViewMode] = useState<'preview' | 'raw'>('preview');

  function resetFilters() {
    setTraderId('');
    setDateFrom(defaultStart);
    setDateTo(today);
    setSkip(0);
    setLimit(50);
  }

  function applyQuickRange(days: number) {
    setDateFrom(shiftDate(today, days));
    setDateTo(today);
    setSkip(0);
  }

  const resultsQuery = useQuery<BacktestResultsResponse, Error>({
    queryKey: ['backtests', 'results', traderId, dateFrom, dateTo, skip, limit],
    queryFn: () =>
      listBacktestResults({
        trader_id: traderId || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        skip,
        limit,
      }),
    staleTime: 10_000,
  });

  const results = useMemo(() => sortResultsDesc(resultsQuery.data?.items ?? []), [resultsQuery.data?.items]);

  useEffect(() => {
    if (!results.length) {
      setSelectedResultId(null);
      return;
    }
    if (!selectedResultId || !results.some((item) => item.result_id === selectedResultId)) {
      setSelectedResultId(results[0].result_id);
    }
  }, [results, selectedResultId]);

  useEffect(() => {
    setReportViewMode('preview');
    setValidationViewMode('preview');
  }, [selectedResultId]);

  const selectedResult = useMemo(
    () => results.find((item) => item.result_id === selectedResultId) ?? null,
    [results, selectedResultId],
  );

  const detailQuery = useQuery({
    queryKey: ['backtests', 'detail', selectedResultId],
    queryFn: () => getBacktestResult(selectedResultId as string),
    enabled: Boolean(selectedResultId),
  });

  const reportQuery = useQuery({
    queryKey: ['backtests', 'report', selectedResultId],
    queryFn: () => downloadBacktestReport(selectedResultId as string),
    enabled: Boolean(selectedResultId),
  });

  const validationQuery = useQuery({
    queryKey: ['backtests', 'validation', selectedResultId],
    queryFn: () => downloadBacktestValidationReport(selectedResultId as string),
    enabled: Boolean(selectedResultId),
  });

  const benchmarkOptionsQuery = useQuery({
    queryKey: ['backtests', 'benchmark-options'],
    queryFn: () => listBenchmarkOptions(50),
    staleTime: 60_000,
  });
  const benchmarkOptions = benchmarkOptionsQuery.data?.items ?? [];

  async function submitJob(jobType: 'backtest-run' | 'backtest-validate-rules' | 'backtest-reproducibility-check') {
    const submission = toJobSubmission({
      profileId: '',
      traderId,
      dateFrom,
      dateTo,
      strategyVersionId,
      benchmarkSymbol,
      mode,
      symbols: [],
      useSnapshotOnly: true,
      scoringProfile: DEFAULT_SCORING_PROFILE,
    });
    const params =
      jobType === 'backtest-run'
        ? buildBacktestRunParams(submission)
        : jobType === 'backtest-validate-rules'
          ? buildBacktestValidateRulesParams(submission)
          : buildBacktestReproducibilityParams(submission);

    const request: JobSubmissionRequest = {
      job_type: jobType,
      params,
      created_by: 'web',
      max_retries: 3,
      retry_backoff_seconds: 0,
      timeout_seconds: null,
    };

    setIsSubmitting(true);
    setSubmissionError(null);
    try {
      const result = await createJob(request);
      setSubmittedJobId(result.job?.id ?? null);
      setSubmittedJobType(jobType);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
    } catch (error) {
      setSubmissionError(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  const summary = useMemo(() => {
    const total = resultsQuery.data?.total ?? 0;
    const selectedSummary = detailQuery.data?.item.summary ?? null;
    return {
      total,
      selectedTrades: selectedSummary?.total_trades ?? 0,
      selectedValidTrades: selectedSummary?.valid_trades ?? 0,
      selectedSkippedTrades: selectedSummary?.skipped_trades ?? 0,
      selectedWinRate: selectedSummary?.win_rate ?? null,
      selectedAvgReturn: selectedSummary?.avg_return_pct ?? null,
      selectedTotalDays: selectedSummary?.total_days ?? 0,
    };
  }, [detailQuery.data?.item.summary, resultsQuery.data?.total]);

  const detail = detailQuery.data?.item ?? null;
  const reportText = reportQuery.data ?? '';
  const validationText = validationQuery.data ?? '';

  function downloadTextFile(filename: string, content: string) {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    window.URL.revokeObjectURL(url);
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="回测"
        title="回测中心"
        description="浏览存储的回测结果，提交回测相关任务，并检查报告、规则验证和复现性检查。"
        actionLabel="打开任务"
        onAction={() => navigate('/jobs')}
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(360px,0.92fr)_minmax(0,1.08fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>任务提交</CardTitle>
                  <CardDescription>从同一控制界面提交回测、规则验证和复现性任务。</CardDescription>
                </div>
                <Button variant="outline" onClick={() => resultsQuery.refetch()} disabled={resultsQuery.isFetching}>
                  {resultsQuery.isFetching ? '刷新中' : '刷新'}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">交易员 ID</span>
                  <TraderIdSelect
                    ariaLabel="交易员 ID"
                    className="border-slate-700 bg-slate-950 text-slate-100"
                    onChange={setTraderId}
                    source="all"
                    value={traderId}
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">策略版本</span>
                  <Input value={strategyVersionId} onChange={(event) => setStrategyVersionId(event.target.value)} placeholder="sv-1" />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">开始日期</span>
                  <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">结束日期</span>
                  <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
                </label>
                <label className="space-y-2 text-sm text-slate-300 md:col-span-2">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">模式</span>
                  <Select value={mode} onChange={(event) => setMode(event.target.value as BacktestJobSubmission['mode'])}>
                    <option value="full">全量 (full)</option>
                    <option value="replay">重放 (replay)</option>
                    <option value="rule_validation">规则验真 (rule_validation)</option>
                  </Select>
                </label>
                <label className="space-y-2 text-sm text-slate-300 md:col-span-2">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Benchmark</span>
                  <Select value={benchmarkSymbol} onChange={(event) => setBenchmarkSymbol(event.target.value)}>
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
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">快捷范围</span>
                <Button size="sm" variant="outline" onClick={() => applyQuickRange(7)}>
                  7天
                </Button>
                <Button size="sm" variant="outline" onClick={() => applyQuickRange(30)}>
                  30天
                </Button>
                <Button size="sm" variant="outline" onClick={() => applyQuickRange(90)}>
                  90天
                </Button>
                <Button size="sm" variant="ghost" onClick={resetFilters}>
                  重置筛选
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <Button onClick={() => submitJob('backtest-run')} disabled={isSubmitting}>
                  运行回测
                </Button>
                <Button variant="outline" onClick={() => submitJob('backtest-validate-rules')} disabled={isSubmitting}>
                  验证规则
                </Button>
                <Button variant="secondary" onClick={() => submitJob('backtest-reproducibility-check')} disabled={isSubmitting}>
                  复现性检查
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <SummaryCard title="结果总数" value={summary.total} accent="text-sky-300" />
                <SummaryCard title="选中交易数" value={summary.selectedTrades} />
                <SummaryCard title="选中胜率" value={summary.selectedWinRate !== null ? formatPct(summary.selectedWinRate) : 'n/a'} accent="text-emerald-300" />
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">跳过 (Skip)</span>
                  <Input
                    type="number"
                    min={0}
                    value={skip}
                    onChange={(event) => setSkip(Number(event.target.value) || 0)}
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">限制 (Limit)</span>
                  <Input
                    type="number"
                    min={1}
                    max={100}
                    value={limit}
                    onChange={(event) => setLimit(Math.max(1, Number(event.target.value) || 50))}
                  />
                </label>
              </div>

              {submissionError ? (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                  {submissionError}
                </div>
              ) : null}

              {benchmarkOptionsQuery.isError ? (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
                  Benchmark 选项加载失败，当前回退到默认沪深300。
                </div>
              ) : null}

              {submittedJobId ? (
                <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                  任务 {submittedJobType} 已提交: {submittedJobId}
                  <div className="mt-3">
                    <Button size="sm" variant="outline" onClick={() => navigate(`/jobs?jobId=${encodeURIComponent(submittedJobId)}`)}>
                      在任务中心查看
                    </Button>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>结果列表</CardTitle>
                  <CardDescription>按交易员和日期范围筛选。</CardDescription>
                </div>
                <div className="text-right text-xs text-slate-500">
                  <p>{resultsQuery.data ? `总计 ${resultsQuery.data.total} / 显示 ${results.length}` : '等待结果加载'}</p>
                  {traderId || dateFrom !== defaultStart || dateTo !== today || skip !== 0 || limit !== 50 ? (
                    <p className="mt-1 max-w-sm">{[traderId ? `交易员: ${traderId}` : null, `日期: ${dateFrom} ~ ${dateTo}`, skip ? `跳过: ${skip}` : null, limit !== 50 ? `限制: ${limit}` : null].filter(Boolean).join(' · ')}</p>
                  ) : (
                    <p className="mt-1">无活跃筛选。</p>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {resultsQuery.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ) : resultsQuery.error ? (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                  {getErrorMessage(resultsQuery.error)}
                </div>
              ) : !results.length ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 text-sm text-slate-400">
                  <p className="text-base font-medium text-slate-200">当前筛选范围内暂无回测结果。</p>
                  <p className="mt-2">你可以放宽日期范围、切换交易员，或者直接重置筛选条件后重新查询。</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button size="sm" onClick={resetFilters}>
                      重置筛选
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => applyQuickRange(30)}>
                      最近 30 天
                    </Button>
                  </div>
                </div>
              ) : (
                results.map((item) => (
                  <ResultRow
                    key={item.result_id}
                    active={item.result_id === selectedResultId}
                    item={item}
                    onSelect={() => setSelectedResultId(item.result_id)}
                  />
                ))
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>结果工作区</CardTitle>
                <CardDescription>
                  {selectedResult ? `${selectedResult.result_id} · ${selectedResult.trader_id ?? '未知交易员'}` : '选择一个结果以查看详情。'}
                </CardDescription>
              </div>
              {selectedResult ? (
                <Badge variant="info">
                  {selectedResult.date_from ?? selectedResult.request_date_from} ~ {selectedResult.date_to ?? selectedResult.request_date_to}
                </Badge>
              ) : null}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedResult ? (
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                尚未选择任何回测结果。
              </div>
            ) : detailQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-[28rem] w-full" />
              </div>
            ) : detailQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(detailQuery.error)}
              </div>
            ) : detail ? (
              <Tabs defaultValue="summary" className="w-full">
                <TabsList className="flex flex-wrap">
                  <TabsTrigger value="summary">摘要</TabsTrigger>
                  <TabsTrigger value="records">记录</TabsTrigger>
                  <TabsTrigger value="report">报告</TabsTrigger>
                  <TabsTrigger value="validation">验真</TabsTrigger>
                  <TabsTrigger value="json">JSON</TabsTrigger>
                </TabsList>

                <TabsContent value="summary" className="space-y-4">
                  <div className="grid gap-3 md:grid-cols-3">
                    <SummaryCard title="选中天数" value={formatNumber(summary.selectedTotalDays)} accent="text-sky-300" />
                    <SummaryCard title="选中交易数" value={formatNumber(summary.selectedTrades)} />
                    <SummaryCard
                      title="有效 / 跳过"
                      value={`${formatNumber(summary.selectedValidTrades)} / ${formatNumber(summary.selectedSkippedTrades)}`}
                      accent="text-emerald-300"
                    />
                  </div>
                  <DetailSummary detail={detail} />
                  <BacktestSparkline records={detail.records} />
                </TabsContent>

                <TabsContent value="records">
                  {detail.records.length ? (
                    <div className="overflow-hidden rounded-2xl border border-slate-800">
                      <table className="min-w-full divide-y divide-slate-800 text-sm">
                        <thead className="bg-slate-950/80 text-left text-slate-400">
                          <tr>
                            <th className="px-4 py-3">日期</th>
                            <th className="px-4 py-3">代码</th>
                            <th className="px-4 py-3">状态</th>
                            <th className="px-4 py-3">收益</th>
                            <th className="px-4 py-3">凭据</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 bg-slate-950/50">
                          {detail.records.map((record) => (
                            <tr key={`${record.trade_date}-${record.symbol}`}>
                              <td className="px-4 py-3 text-slate-200">{record.trade_date}</td>
                              <td className="px-4 py-3 text-slate-100">{record.symbol}</td>
                              <td className={`px-4 py-3 font-medium ${statusTone(record.status)}`}>{record.status}</td>
                              <td className="px-4 py-3 text-slate-200">{formatPct(record.return_pct)}</td>
                              <td className="px-4 py-3 text-slate-400">{record.evidence_refs.length}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">暂无交易记录。</p>
                  )}
                </TabsContent>

                <TabsContent value="report">
                  {reportQuery.isLoading ? (
                    <Skeleton className="h-64 w-full" />
                  ) : reportQuery.error ? (
                    <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                      {getErrorMessage(reportQuery.error)}
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <Tabs
                          aria-label="回测报告视图切换"
                          className="w-auto"
                          value={reportViewMode}
                          onValueChange={(value) => setReportViewMode(value as 'preview' | 'raw')}
                        >
                          <TabsList>
                            <TabsTrigger value="preview">预览</TabsTrigger>
                            <TabsTrigger value="raw">原文</TabsTrigger>
                          </TabsList>
                        </Tabs>
                        <Button
                          variant="outline"
                          onClick={() => downloadTextFile(`${selectedResult?.result_id ?? 'backtest'}-report.md`, reportText)}
                          disabled={!reportText}
                        >
                          下载原文
                        </Button>
                      </div>
                      {reportViewMode === 'preview' ? (
                        <ArtifactPreview kind="markdown" content={reportText} title="回测报告" />
                      ) : (
                        <pre
                          className="max-h-[40rem] overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-200"
                          data-testid="backtest-report-raw"
                        >
                          {reportText || '暂无回测报告。'}
                        </pre>
                      )}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="validation">
                  {validationQuery.isLoading ? (
                    <Skeleton className="h-64 w-full" />
                  ) : validationQuery.error ? (
                    <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                      {getErrorMessage(validationQuery.error)}
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <Tabs
                          aria-label="规则验真报告视图切换"
                          className="w-auto"
                          value={validationViewMode}
                          onValueChange={(value) => setValidationViewMode(value as 'preview' | 'raw')}
                        >
                          <TabsList>
                            <TabsTrigger value="preview">预览</TabsTrigger>
                            <TabsTrigger value="raw">原文</TabsTrigger>
                          </TabsList>
                        </Tabs>
                        <Button
                          variant="outline"
                          onClick={() => downloadTextFile(`${selectedResult?.result_id ?? 'backtest'}-validation.md`, validationText)}
                          disabled={!validationText}
                        >
                          下载原文
                        </Button>
                      </div>
                      {validationViewMode === 'preview' ? (
                        <ArtifactPreview kind="markdown" content={validationText} title="规则验真报告" />
                      ) : (
                        <pre
                          className="max-h-[40rem] overflow-auto whitespace-pre-wrap rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-200"
                          data-testid="backtest-validation-raw"
                        >
                          {validationText || '暂无规则验真报告。'}
                        </pre>
                      )}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="json">
                  <pre
                    className="max-h-[40rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200"
                    data-testid="backtest-detail-json"
                  >
                    {JSON.stringify(detail, null, 2)}
                  </pre>
                </TabsContent>
              </Tabs>
            ) : null}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
