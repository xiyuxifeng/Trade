import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ArtifactPreview } from '@/components/artifacts/artifact-preview';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, ErrorState, JsonViewer, LoadingState, SectionCard } from '@/components/kit';
import { TraderIdSelect } from '@/components/inputs/trader-id-select';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { downloadBacktestReport, getBacktestResult, listBacktestResults } from '@/lib/api/backtests';
import type { BacktestListItem, BacktestResultItem, BacktestResultsResponse, RegimeBacktestMetric } from '@/types/backtests';

type RegimeBacktestQueryState = {
  traderId: string;
  dateFrom: string;
  dateTo: string;
  limit: number;
};

function formatPct(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return value.toLocaleString('zh-CN');
}

function formatMetricValue(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${value.toFixed(2)}`;
}

function shiftDate(value: string, days: number) {
  return dayjs(value).subtract(days, 'day').format('YYYY-MM-DD');
}

function getSummary(value: BacktestListItem | BacktestResultItem | null | undefined) {
  if (!value || !value.summary || typeof value.summary !== 'object') {
    return null;
  }
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

function getRegimeMetrics(value: BacktestResultItem | null | undefined): RegimeBacktestMetric[] {
  return value?.regime_metrics ?? [];
}

function getRuleRegimeMetrics(value: BacktestResultItem | null | undefined) {
  return value?.rule_regime_metrics ?? {};
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
      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
        active ? 'border-sky-200 bg-sky-50' : 'border-slate-200 bg-white hover:border-sky-200 hover:bg-slate-50'
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">{item.result_id}</p>
          <p className="mt-1 text-xs text-slate-500">
            {item.trader_id ?? '未知交易员'} · {item.date_from ?? 'n/a'} ~ {item.date_to ?? 'n/a'}
          </p>
        </div>
        <Badge variant="info">{summary?.total_trades ?? 0} 笔</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        {item.benchmark_symbol ? <span className="rounded-full border border-slate-200 px-2 py-1">Benchmark {item.benchmark_symbol}</span> : null}
        {item.regime_version ? <span className="rounded-full border border-slate-200 px-2 py-1">Regime {item.regime_version}</span> : null}
        {item.source_feature_version ? <span className="rounded-full border border-slate-200 px-2 py-1">Feature {item.source_feature_version}</span> : null}
        <span className="rounded-full border border-slate-200 px-2 py-1">胜率 {formatPct(summary?.win_rate)}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">平均收益 {formatPct(summary?.avg_return_pct)}</span>
      </div>
    </button>
  );
}

function SummaryCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-lg font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function RegimeMetricsTable({ metrics }: { metrics: RegimeBacktestMetric[] }) {
  if (!metrics.length) {
    return <EmptyState title="暂无分 regime 数据" description="当前回测结果没有 regime 分桶信息，可能仍是旧版本或样本不足。" />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <table className="w-full border-collapse text-left text-sm">
        <thead className="bg-slate-50 text-slate-600">
          <tr>
            <th className="px-4 py-3 font-medium">Regime</th>
            <th className="px-4 py-3 font-medium">样本</th>
            <th className="px-4 py-3 font-medium">胜率</th>
            <th className="px-4 py-3 font-medium">平均收益</th>
            <th className="px-4 py-3 font-medium">平均盈</th>
            <th className="px-4 py-3 font-medium">平均亏</th>
            <th className="px-4 py-3 font-medium">最大回撤</th>
            <th className="px-4 py-3 font-medium">PF</th>
            <th className="px-4 py-3 font-medium">置信度</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((metric) => (
            <tr key={metric.regime_label} className="border-t border-slate-100">
              <td className="px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-slate-950">{metric.regime_label}</span>
                  {metric.low_sample ? <Badge variant="warning">低样本</Badge> : <Badge variant="success">稳定</Badge>}
                </div>
              </td>
              <td className="px-4 py-3 text-slate-700">{formatNumber(metric.sample_count)}</td>
              <td className="px-4 py-3 text-slate-700">{formatPct(metric.win_rate)}</td>
              <td className="px-4 py-3 text-slate-700">{formatPct(metric.avg_return)}</td>
              <td className="px-4 py-3 text-slate-700">{formatPct(metric.avg_win_return)}</td>
              <td className="px-4 py-3 text-slate-700">{formatPct(metric.avg_loss_return)}</td>
              <td className="px-4 py-3 text-slate-700">{formatPct(metric.max_drawdown)}</td>
              <td className="px-4 py-3 text-slate-700">{formatMetricValue(metric.profit_factor)}</td>
              <td className="px-4 py-3 text-slate-700">{formatPct(metric.confidence)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RuleRegimeBlock({ ruleId, metrics }: { ruleId: string; metrics: RegimeBacktestMetric[] }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-950">{ruleId}</h4>
        <Badge variant="info">{metrics.length} 个 regime</Badge>
      </div>
      <div className="mt-4 space-y-3">
        {metrics.map((metric) => (
          <div key={`${ruleId}-${metric.regime_label}`} className="rounded-2xl border border-slate-100 bg-slate-50 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium text-slate-950">{metric.regime_label}</span>
              {metric.low_sample ? <Badge variant="warning">低样本</Badge> : <Badge variant="success">稳定</Badge>}
              <Badge variant="info">{formatNumber(metric.sample_count)} 样本</Badge>
            </div>
            <div className="mt-2 grid gap-2 text-sm text-slate-600 sm:grid-cols-2 xl:grid-cols-4">
              <span>胜率 {formatPct(metric.win_rate)}</span>
              <span>平均收益 {formatPct(metric.avg_return)}</span>
              <span>最大回撤 {formatPct(metric.max_drawdown)}</span>
              <span>置信度 {formatPct(metric.confidence)}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function RuleRegimeBreakdown({ ruleMetrics }: { ruleMetrics: Record<string, RegimeBacktestMetric[]> }) {
  const entries = Object.entries(ruleMetrics);
  if (!entries.length) {
    return <EmptyState title="暂无规则分桶数据" description="当前回测结果没有按规则分桶的 regime metrics。" />;
  }

  return (
    <div className="space-y-4">
      {entries.map(([ruleId, metrics]) => (
        <RuleRegimeBlock key={ruleId} ruleId={ruleId} metrics={metrics} />
      ))}
    </div>
  );
}

export function RegimeBacktestReportWorkspace() {
  const navigate = useNavigate();
  const today = useMemo(() => dayjs().format('YYYY-MM-DD'), []);
  const defaultStart = useMemo(() => shiftDate(today, 30), [today]);
  const [filters, setFilters] = useState<RegimeBacktestQueryState>({
    traderId: '',
    dateFrom: defaultStart,
    dateTo: today,
    limit: 10,
  });
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);

  const resultsQuery = useQuery<BacktestResultsResponse, ApiError>({
    queryKey: ['regime-backtest-report', 'results', filters],
    queryFn: () =>
      listBacktestResults({
        trader_id: filters.traderId || undefined,
        date_from: filters.dateFrom || undefined,
        date_to: filters.dateTo || undefined,
        limit: filters.limit,
        skip: 0,
      }),
    staleTime: 15_000,
  });

  const results = useMemo(() => resultsQuery.data?.items ?? [], [resultsQuery.data?.items]);

  useEffect(() => {
    if (!results.length) {
      setSelectedResultId(null);
      return;
    }
    if (!selectedResultId || !results.some((item) => item.result_id === selectedResultId)) {
      setSelectedResultId(results[0].result_id);
    }
  }, [results, selectedResultId]);

  const selectedResultIdResolved = selectedResultId ?? results[0]?.result_id ?? null;

  const detailQuery = useQuery({
    queryKey: ['regime-backtest-report', 'detail', selectedResultIdResolved],
    queryFn: () => getBacktestResult(selectedResultIdResolved as string),
    enabled: Boolean(selectedResultIdResolved),
  });

  const reportQuery = useQuery({
    queryKey: ['regime-backtest-report', 'markdown', selectedResultIdResolved],
    queryFn: () => downloadBacktestReport(selectedResultIdResolved as string),
    enabled: Boolean(selectedResultIdResolved),
  });

  const queryError = resultsQuery.error ?? detailQuery.error;
  const permissionDenied = queryError instanceof ApiError && (queryError.status === 401 || queryError.status === 403);

  if (queryError) {
    return (
      <main className="page-stack">
        <div className="flex flex-wrap items-center justify-start gap-3">
          <Link
            className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
            to="/backtest"
          >
            返回回测中心
          </Link>
        </div>
        <PageHeader kicker="正式入口" title="Regime Backtest Report" description="展示不同 market regime 下的回测表现。" />
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'backtest')}
          onRetry={
            permissionDenied
              ? undefined
              : () => {
                  void resultsQuery.refetch();
                  void detailQuery.refetch();
                }
          }
        />
      </main>
    );
  }

  const detail = detailQuery.data?.item ?? null;
  const summary = detail ? getSummary(detail) : null;
  const regimeMetrics = getRegimeMetrics(detail);
  const ruleMetrics = getRuleRegimeMetrics(detail);

  return (
    <main className="page-stack">
      <div className="flex flex-wrap items-center justify-start gap-3">
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
          to="/backtest"
        >
          返回回测中心
        </Link>
      </div>
      <PageHeader description="在同一份 canonical backtest result 上查看 overall metrics、per-regime metrics 和 per-rule per-regime breakdown。" />

      <section className="grid gap-6 xl:grid-cols-[minmax(320px,0.42fr)_minmax(0,1fr)]">
        <SectionCard
          title="结果筛选"
          description="按交易员和日期范围定位 regime-aware 回测结果。"
          action={
            <Button variant="outline" className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={() => void resultsQuery.refetch()}>
              刷新
            </Button>
          }
        >
          <div className="grid gap-4">
            <label className="space-y-2 text-sm text-slate-700">
              <span className="text-xs uppercase tracking-[0.16em] text-slate-500">交易员 ID</span>
              <TraderIdSelect
                ariaLabel="交易员 ID"
                className="border-slate-200 bg-white text-slate-900"
                onChange={(traderId) => setFilters((current) => ({ ...current, traderId }))}
                source="backtest"
                value={filters.traderId}
              />
            </label>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-700">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">开始日期</span>
                <Input
                  aria-label="开始日期"
                  type="date"
                  className="border-slate-200 bg-white text-slate-900"
                  value={filters.dateFrom}
                  onChange={(event) => setFilters((current) => ({ ...current, dateFrom: event.target.value }))}
                />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">结束日期</span>
                <Input
                  aria-label="结束日期"
                  type="date"
                  className="border-slate-200 bg-white text-slate-900"
                  value={filters.dateTo}
                  onChange={(event) => setFilters((current) => ({ ...current, dateTo: event.target.value }))}
                />
              </label>
            </div>
            <label className="space-y-2 text-sm text-slate-700">
              <span className="text-xs uppercase tracking-[0.16em] text-slate-500">返回条数</span>
              <Select
                aria-label="返回条数"
                className="border-slate-200 bg-white text-slate-900"
                value={String(filters.limit)}
                onChange={(event) => setFilters((current) => ({ ...current, limit: Number(event.target.value) }))}
              >
                <option value="5">5</option>
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="50">50</option>
              </Select>
            </label>
          </div>
        </SectionCard>

        <SectionCard title="最近结果" description="默认展示最新的回测结果，点击即可切换。">
          {resultsQuery.isLoading ? (
            <div className="space-y-3">
              <LoadingState label="正在加载回测结果" description="加载 recent regime-aware backtest results..." />
              <Skeleton className="h-24 w-full rounded-2xl" />
              <Skeleton className="h-24 w-full rounded-2xl" />
            </div>
          ) : results.length ? (
            <div className="space-y-3">
              {results.map((item) => (
                <ResultRow key={item.result_id} item={item} active={item.result_id === selectedResultIdResolved} onSelect={() => setSelectedResultId(item.result_id)} />
              ))}
            </div>
          ) : (
            <EmptyState
              title="当前筛选范围内暂无回测结果"
              description="请调整日期范围或交易员条件后再试。"
              actionLabel="重置查询"
              onAction={() =>
                setFilters({
                  traderId: '',
                  dateFrom: defaultStart,
                  dateTo: today,
                  limit: 10,
                })
              }
            />
          )}
        </SectionCard>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.62fr)]">
        <SectionCard
          title="整体与分 regime 表现"
          description="展示 canonical backtest result 的 overall metrics 与 regime breakdown。"
          action={
            <div className="flex flex-wrap gap-2">
              {selectedResultIdResolved ? (
                <Button variant="outline" className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={() => navigate(`/jobs/${selectedResultIdResolved}`)}>
                  打开 Job
                </Button>
              ) : null}
              <Button variant="outline" className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={() => void detailQuery.refetch()}>
                刷新详情
              </Button>
            </div>
          }
        >
          {!detail ? (
            <LoadingState label="等待选择回测结果" description="从左侧列表中选择一条结果。" />
          ) : (
            <div className="space-y-6">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <SummaryCard label="Benchmark" value={detail.benchmark_symbol ?? 'n/a'} />
                <SummaryCard label="Regime Version" value={detail.regime_version ?? 'n/a'} />
                <SummaryCard label="Source Feature Version" value={detail.source_feature_version ?? 'n/a'} />
                <SummaryCard label="总天数" value={summary ? formatNumber(summary.total_days) : 'n/a'} />
                <SummaryCard label="总交易数" value={summary ? formatNumber(summary.total_trades) : 'n/a'} />
                <SummaryCard label="胜率" value={summary ? formatPct(summary.win_rate) : 'n/a'} />
              </div>

              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <SummaryCard label="有效交易" value={summary ? formatNumber(summary.valid_trades) : 'n/a'} />
                <SummaryCard label="跳过交易" value={summary ? formatNumber(summary.skipped_trades) : 'n/a'} />
                <SummaryCard label="平均收益" value={summary ? formatPct(summary.avg_return_pct) : 'n/a'} />
                <SummaryCard label="结果版本" value={detail.result_version} />
              </div>

              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-950">Per Regime Metrics</h3>
                    <p className="mt-1 text-sm text-slate-600">每个 market regime 的样本量、收益和置信度。</p>
                  </div>
                  <Badge variant="info">{regimeMetrics.length} 个 regime</Badge>
                </div>
                <RegimeMetricsTable metrics={regimeMetrics} />
              </div>

              <div className="space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-slate-950">Per Rule / Per Regime</h3>
                    <p className="mt-1 text-sm text-slate-600">单条规则在不同 market regime 下的表现拆分。</p>
                  </div>
                  <Badge variant="info">{Object.keys(ruleMetrics).length} 条规则</Badge>
                </div>
                <RuleRegimeBreakdown ruleMetrics={ruleMetrics} />
              </div>
            </div>
          )}
        </SectionCard>

        <SectionCard title="报告与原始 JSON" description="同一份结果可以在 markdown 报告和结构化 JSON 之间切换。">
          <Tabs defaultValue="report">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="report">Markdown</TabsTrigger>
              <TabsTrigger value="json">JSON</TabsTrigger>
            </TabsList>
            <TabsContent value="report" className="mt-4">
              {reportQuery.isLoading ? (
                <LoadingState label="正在加载报告" description="正在渲染市场状态回测报告…" />
              ) : (
                <ArtifactPreview kind="markdown" content={reportQuery.data ?? ''} title="Regime Backtest Report" />
              )}
            </TabsContent>
            <TabsContent value="json" className="mt-4">
              <JsonViewer value={detail ?? {}} title="回测结果 JSON" />
            </TabsContent>
          </Tabs>
        </SectionCard>
      </section>
    </main>
  );
}
