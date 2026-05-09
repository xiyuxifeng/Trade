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
        {active ? <Badge variant="info">Selected</Badge> : null}
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
        kicker="Market"
        title="Market data center"
        description="Search symbols, pick a target, and inspect OHLCV history from the UI BFF."
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(280px,0.7fr)_minmax(0,1.3fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Symbol browser</CardTitle>
                <CardDescription>Find and pick a symbol before querying history.</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => symbolsQuery.refetch()} disabled={symbolsQuery.isFetching}>
                {symbolsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              placeholder="Search symbol"
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
                暂无匹配 symbol。
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
              <CardTitle>OHLCV query</CardTitle>
              <CardDescription>Select a symbol, set a date range, then run the query.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_160px]">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Selected symbol</p>
                  <p className="mt-1 text-sm text-slate-100">{selectedSymbol || '请选择左侧 symbol'}</p>
                </div>
                <Select value={selectedSymbol} onChange={(event) => setSelectedSymbol(event.target.value)}>
                  <option value="">Select</option>
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

          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Symbols</p>
              <p className="mt-2 text-2xl font-semibold text-slate-100">{summary.symbolsCount}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Selected</p>
              <p className="mt-2 break-all text-xl font-semibold text-sky-300">{summary.selectedSymbol}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Rows</p>
              <p className="mt-2 text-2xl font-semibold text-slate-100">{summary.rowCount}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Last close</p>
              <p className="mt-2 text-2xl font-semibold text-amber-300">
                {summary.lastClose == null ? '—' : formatNumber(summary.lastClose)}
              </p>
            </div>
          </div>

          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>OHLCV history</CardTitle>
                  <CardDescription>
                    {ohlcvQuery.data ? `${ohlcvQuery.data.symbol} · ${ohlcvQuery.data.count} rows` : 'Query results will appear here.'}
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
                <div className="overflow-hidden rounded-2xl border border-slate-800">
                  <Table>
                    <TableHeader className="bg-slate-950/80">
                      <TableRow>
                        <TableHead>Time</TableHead>
                        <TableHead>Open</TableHead>
                        <TableHead>High</TableHead>
                        <TableHead>Low</TableHead>
                        <TableHead>Close</TableHead>
                        <TableHead>Volume</TableHead>
                        <TableHead>Turnover</TableHead>
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
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
