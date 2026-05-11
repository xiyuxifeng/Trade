import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ApiError } from '@/lib/api/http';
import { formatLocalDateInputOffset } from '@/lib/date';
import { getOhlcv, listSymbols } from '@/lib/api/market';
import { PageHeader } from '@/components/layout/page-header';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '市场数据加载失败';
}

function formatDate(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatNumber(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: 4,
  }).format(value);
}

function formatCompactDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
  }).format(new Date(value));
}

type CandlePoint = {
  x: number;
  highY: number;
  lowY: number;
  bodyY: number;
  bodyHeight: number;
  up: boolean;
  label: string;
  open: number;
  high: number;
  low: number;
  close: number;
};

type CandleChart = {
  width: number;
  height: number;
  minPrice: number;
  maxPrice: number;
  candles: CandlePoint[];
};

function buildCandleChart(rows: Array<{
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}>): CandleChart | null {
  if (!rows.length) return null;

  const width = 800;
  const height = 320;
  const padding = { top: 20, right: 20, bottom: 36, left: 56 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const minPrice = Math.min(...rows.map((row) => row.low));
  const maxPrice = Math.max(...rows.map((row) => row.high));
  const priceRange = maxPrice - minPrice || 1;
  const step = plotWidth / rows.length;

  const scaleY = (value: number) =>
    padding.top + ((maxPrice - value) / priceRange) * plotHeight;

  return {
    width,
    height,
    minPrice,
    maxPrice,
    candles: rows.map((row, index) => {
      const x = padding.left + step * index + step / 2;
      const openY = scaleY(row.open);
      const closeY = scaleY(row.close);
      const highY = scaleY(row.high);
      const lowY = scaleY(row.low);
      const bodyY = Math.min(openY, closeY);
      const bodyHeight = Math.max(1, Math.abs(closeY - openY));

      return {
        x,
        highY,
        lowY,
        bodyY,
        bodyHeight,
        up: row.close >= row.open,
        label: formatCompactDate(row.time),
        open: row.open,
        high: row.high,
        low: row.low,
        close: row.close,
      };
    }),
  };
}

function MarketSymbolButton({
  symbol,
  active,
  onSelect,
}: {
  symbol: string;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={`w-full rounded-xl border px-3 py-3 text-left transition-colors ${
        active
          ? 'border-sky-500/40 bg-sky-500/10 text-sky-100'
          : 'border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
      }`}
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium">{symbol}</p>
        {active ? <Badge variant="info">已选择</Badge> : null}
      </div>
    </button>
  );
}

export function MarketPage() {
  const [searchText, setSearchText] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [startDate, setStartDate] = useState(formatLocalDateInputOffset(-30));
  const [endDate, setEndDate] = useState(formatLocalDateInputOffset(0));
  const [submittedQuery, setSubmittedQuery] = useState<{
    symbol: string;
    startDate: string;
    endDate: string;
  } | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const symbolsQuery = useQuery({
    queryKey: ['market-symbols', searchText],
    queryFn: () => listSymbols(searchText || undefined, 100),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!selectedSymbol && symbolsQuery.data?.items.length) {
      setSelectedSymbol(symbolsQuery.data.items[0]);
    }
  }, [selectedSymbol, symbolsQuery.data?.items]);

  const ohlcvQuery = useQuery({
    queryKey: ['market-ohlcv', submittedQuery],
    queryFn: () => getOhlcv(submittedQuery?.symbol ?? '', submittedQuery?.startDate ?? '', submittedQuery?.endDate ?? ''),
    enabled: Boolean(submittedQuery),
    staleTime: 15_000,
  });

  const summary = useMemo(() => {
    const symbols = symbolsQuery.data?.items ?? [];
    const rows = ohlcvQuery.data?.items ?? [];
    const high = rows.length ? Math.max(...rows.map((row) => row.high)) : null;
    const low = rows.length ? Math.min(...rows.map((row) => row.low)) : null;
    const lastClose = rows.length ? rows[rows.length - 1].close : null;
    return {
      symbolsCount: symbolsQuery.data?.count ?? symbols.length,
      selectedSymbol: selectedSymbol || '未选择',
      rowCount: ohlcvQuery.data?.count ?? rows.length,
      high,
      low,
      lastClose,
    };
  }, [ohlcvQuery.data, selectedSymbol, symbolsQuery.data]);

  const chart = useMemo(() => buildCandleChart(ohlcvQuery.data?.items ?? []), [ohlcvQuery.data?.items]);

  const handleRunQuery = () => {
    if (!selectedSymbol) {
      setFormError('请先选择一个 symbol。');
      return;
    }
    if (startDate > endDate) {
      setFormError('开始日期不能晚于结束日期。');
      return;
    }

    setFormError(null);
    setSubmittedQuery({
      symbol: selectedSymbol,
      startDate,
      endDate,
    });
  };

  return (
    <main className="page-stack">
      <PageHeader
        kicker="行情"
        title="市场数据中心"
        description="搜索标的，选择目标，并从 UI BFF 检查 OHLCV 历史记录。"
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(280px,0.7fr)_minmax(0,1.3fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>标的浏览器</CardTitle>
                <CardDescription>在查询历史记录前，找到并选择一个标的。</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => symbolsQuery.refetch()} disabled={symbolsQuery.isFetching}>
                {symbolsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              placeholder="搜索标的 (symbol)"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
            />

            {symbolsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : symbolsQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(symbolsQuery.error)}
              </div>
            ) : !symbolsQuery.data?.items.length ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                暂无匹配标的。
              </div>
            ) : (
              <div className="space-y-2">
                {symbolsQuery.data.items.map((symbol) => (
                  <MarketSymbolButton
                    active={symbol === selectedSymbol}
                    key={symbol}
                    onSelect={() => setSelectedSymbol(symbol)}
                    symbol={symbol}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>OHLCV 查询</CardTitle>
              <CardDescription>选择一个标的，设置日期范围，然后运行查询。</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px]">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">当前选择标的</p>
                  <p className="mt-1 text-sm text-slate-100">{selectedSymbol || '请选择左侧标的'}</p>
                </div>
                <Select value={selectedSymbol} onChange={(event) => setSelectedSymbol(event.target.value)}>
                  <option value="">选择</option>
                  {symbolsQuery.data?.items.map((symbol) => (
                    <option key={symbol} value={symbol}>
                      {symbol}
                    </option>
                  ))}
                </Select>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <Input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
                <Input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
              </div>

              {formError ? (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                  {formError}
                </div>
              ) : null}

              <div className="flex flex-wrap gap-3">
                <Button onClick={handleRunQuery} disabled={!selectedSymbol}>
                  查询 OHLCV
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    if (!selectedSymbol) return;
                    setSubmittedQuery({
                      symbol: selectedSymbol,
                      startDate,
                      endDate,
                    });
                  }}
                  disabled={!selectedSymbol}
                >
                  重新查询
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">标的总数</p>
              <p className="mt-2 text-2xl font-semibold text-slate-100">{summary.symbolsCount}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">已选择</p>
              <p className="mt-2 break-all text-xl font-semibold text-sky-300">{summary.selectedSymbol}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">数据行数</p>
              <p className="mt-2 text-2xl font-semibold text-slate-100">{summary.rowCount}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">最新收盘价</p>
              <p className="mt-2 text-2xl font-semibold text-amber-300">
                {summary.lastClose == null ? '—' : formatNumber(summary.lastClose)}
              </p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">价格范围</p>
              <p className="mt-2 text-xl font-semibold text-slate-100">
                {summary.low == null || summary.high == null ? '—' : `${formatNumber(summary.low)} - ${formatNumber(summary.high)}`}
              </p>
            </div>
          </div>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>OHLCV 历史</CardTitle>
                  <CardDescription>
                    {ohlcvQuery.data ? `${ohlcvQuery.data.symbol} · ${ohlcvQuery.data.count} 行数据` : '查询结果将显示在这里。'}
                  </CardDescription>
                </div>
                {ohlcvQuery.data ? <Badge variant="info">{ohlcvQuery.data.start_date} ~ {ohlcvQuery.data.end_date}</Badge> : null}
              </div>
            </CardHeader>
            <CardContent>
              {ohlcvQuery.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-14 w-full" />
                  <Skeleton className="h-14 w-full" />
                  <Skeleton className="h-14 w-full" />
                </div>
              ) : ohlcvQuery.error ? (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                  {getErrorMessage(ohlcvQuery.error)}
                </div>
              ) : !ohlcvQuery.data?.items.length ? (
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                  尚未查询到 OHLCV 数据。
                </div>
              ) : (
                <div className="space-y-6">
                  <section className="space-y-4">
                    <div className="flex flex-wrap items-end justify-between gap-3">
                      <div>
                        <h3 className="text-base font-semibold text-slate-100">K线图</h3>
                        <p className="text-sm text-slate-400">
                          {ohlcvQuery.data.symbol} · {ohlcvQuery.data.count} rows
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge>{ohlcvQuery.data.start_date}</Badge>
                        <Badge>{ohlcvQuery.data.end_date}</Badge>
                      </div>
                    </div>

                    {chart ? (
                      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-950 to-slate-900/70">
                        <svg
                          aria-label="K线图"
                          className="h-[22rem] w-full"
                          preserveAspectRatio="none"
                          role="img"
                          viewBox={`0 0 ${chart.width} ${chart.height}`}
                        >
                          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
                            const y = 20 + ratio * 264;
                            return <line key={ratio} x1="56" x2={chart.width - 20} y1={y} y2={y} stroke="rgba(148, 163, 184, 0.12)" strokeDasharray="4 6" />;
                          })}
                          {chart.candles.map((candle, index) => {
                            const candleWidth = Math.max(4, (chart.width - 76) / chart.candles.length * 0.48);
                            const selectedColor = candle.up ? 'rgba(74, 222, 128, 0.95)' : 'rgba(248, 113, 113, 0.95)';
                            const fillColor = candle.up ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.72)';
                            const showLabel = index === 0 || index === Math.floor(chart.candles.length / 2) || index === chart.candles.length - 1;

                            return (
                              <g key={candle.label}>
                                <line
                                  x1={candle.x}
                                  x2={candle.x}
                                  y1={candle.highY}
                                  y2={candle.lowY}
                                  stroke={selectedColor}
                                  strokeWidth="2"
                                />
                                <rect
                                  x={candle.x - candleWidth / 2}
                                  y={candle.bodyY}
                                  width={candleWidth}
                                  height={candle.bodyHeight}
                                  rx="3"
                                  fill={fillColor}
                                  stroke={selectedColor}
                                  strokeWidth="1"
                                />
                                {showLabel ? (
                                  <text
                                    x={candle.x}
                                    y={chart.height - 10}
                                    fill="rgba(148, 163, 184, 0.92)"
                                    fontSize="12"
                                    textAnchor="middle"
                                  >
                                    {candle.label}
                                  </text>
                                ) : null}
                              </g>
                            );
                          })}
                          <text x="16" y="28" fill="rgba(148, 163, 184, 0.9)" fontSize="12">
                            {formatNumber(chart.maxPrice)}
                          </text>
                          <text x="16" y="292" fill="rgba(148, 163, 184, 0.9)" fontSize="12">
                            {formatNumber(chart.minPrice)}
                          </text>
                        </svg>
                      </div>
                    ) : null}
                  </section>

                  <section className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <h3 className="text-base font-semibold text-slate-100">OHLCV 明细</h3>
                        <p className="text-sm text-slate-400">用于逐日核对图表和成交量。</p>
                      </div>
                    </div>
                    <div className="overflow-hidden rounded-2xl border border-slate-800">
                      <Table>
                        <TableHeader className="bg-slate-950/80">
                          <TableRow>
                            <TableHead>时间</TableHead>
                            <TableHead>开盘价</TableHead>
                            <TableHead>最高价</TableHead>
                            <TableHead>最低价</TableHead>
                            <TableHead>收盘价</TableHead>
                            <TableHead>成交量</TableHead>
                            <TableHead>成交额</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {ohlcvQuery.data.items.map((row) => {
                            const up = row.close >= row.open;
                            return (
                              <TableRow key={row.time}>
                                <TableCell>{formatDate(row.time)}</TableCell>
                                <TableCell>{formatNumber(row.open)}</TableCell>
                                <TableCell>{formatNumber(row.high)}</TableCell>
                                <TableCell>{formatNumber(row.low)}</TableCell>
                                <TableCell className={up ? 'text-emerald-300' : 'text-rose-300'}>
                                  {formatNumber(row.close)}
                                </TableCell>
                                <TableCell>{formatNumber(row.volume)}</TableCell>
                                <TableCell>{row.turnover == null ? '—' : formatNumber(row.turnover)}</TableCell>
                              </TableRow>
                            );
                          })}
                        </TableBody>
                      </Table>
                    </div>
                  </section>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
