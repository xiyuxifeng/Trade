import { useMemo, useState } from 'react';
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
import { listSignals } from '@/lib/api/signals';
import type { SignalItem } from '@/types/signals';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '信号数据加载失败';
}

function formatConfidence(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function SummaryCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function SignalDetails({ signal }: { signal: SignalItem | null }) {
  if (!signal) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center">
        <p className="text-sm font-medium text-slate-200">暂无选中信号</p>
        <p className="mt-2 text-sm text-slate-500">筛选后会在这里显示最靠前的一条信号。</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="font-medium text-slate-100">{signal.signal_id}</p>
            <p className="text-sm text-slate-500">{signal.symbol} · {signal.side}</p>
          </div>
          <Badge variant="info">{formatConfidence(signal.confidence)}</Badge>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <SummaryCard title="Trader" value={signal.trader_id ?? 'n/a'} />
          <SummaryCard title="Strategy" value={signal.strategy_version_id ?? 'n/a'} />
        </div>
        <p className="mt-4 text-sm text-slate-400">{signal.context_summary}</p>
      </div>
      <pre className="max-h-[20rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
        {JSON.stringify(signal, null, 2)}
      </pre>
    </div>
  );
}

export function SignalsCenter() {
  const [symbol, setSymbol] = useState('');
  const [since, setSince] = useState(formatLocalDateInputOffset(-30));
  const [limit, setLimit] = useState(20);

  const signalsQuery = useQuery({
    queryKey: ['signals', symbol, since, limit],
    queryFn: () =>
      listSignals({
        symbol: symbol || undefined,
        since: since || undefined,
        limit,
      }),
    staleTime: 10_000,
  });

  const signals = signalsQuery.data?.signals ?? [];
  const latestSignal = signals[0] ?? null;
  const traders = useMemo(() => new Set(signals.map((item) => item.trader_id).filter(Boolean)).size, [signals]);
  const maxConfidence = useMemo(
    () => (signals.length ? Math.max(...signals.map((item) => item.confidence)) : 0),
    [signals],
  );

  return (
    <section className="dashboard-grid">
      <Card className="xl:col-span-12">
        <CardHeader>
          <CardTitle>Signal filters</CardTitle>
          <CardDescription>按符号、日期和数量筛选信号，直接查看上下文摘要和原始负载。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <label className="space-y-2 text-sm text-slate-300">
              <span>Symbol</span>
              <Input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="000001.SZ" />
            </label>
            <label className="space-y-2 text-sm text-slate-300">
              <span>Since</span>
              <Input value={since} onChange={(event) => setSince(event.target.value)} type="date" />
            </label>
            <label className="space-y-2 text-sm text-slate-300">
              <span>Limit</span>
              <Select value={String(limit)} onChange={(event) => setLimit(Number(event.target.value) || 20)}>
                {[20, 50, 100, 200].map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
            </label>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button onClick={() => signalsQuery.refetch()}>Refresh</Button>
            <p className="text-sm text-slate-500">
              {signalsQuery.isFetching ? '正在刷新信号列表...' : signalsQuery.data ? `最后更新 ${signals.length} 条信号` : '首次加载中...'}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card className="xl:col-span-12">
        <CardHeader>
          <CardTitle>Signal overview</CardTitle>
          <CardDescription>概览卡用于快速判断当前信号密度与置信度。</CardDescription>
        </CardHeader>
        <CardContent>
          {signalsQuery.isLoading ? (
            <div className="grid gap-4 md:grid-cols-3">
              <Skeleton className="h-24 rounded-2xl" />
              <Skeleton className="h-24 rounded-2xl" />
              <Skeleton className="h-24 rounded-2xl" />
            </div>
          ) : signalsQuery.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">
              {getErrorMessage(signalsQuery.error)}
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              <SummaryCard title="Signals" value={signalsQuery.data?.count ?? 0} accent="text-sky-300" />
              <SummaryCard title="Traders" value={traders} accent="text-emerald-300" />
              <SummaryCard title="Max confidence" value={signals.length ? formatConfidence(maxConfidence) : 'n/a'} accent="text-amber-300" />
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="xl:col-span-7">
        <CardHeader>
          <CardTitle>Signal list</CardTitle>
          <CardDescription>按时间顺序展示最近信号与其上下文摘要。</CardDescription>
        </CardHeader>
        <CardContent>
          {signalsQuery.isLoading ? (
            <Skeleton className="h-80 rounded-2xl" />
          ) : signalsQuery.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">
              {getErrorMessage(signalsQuery.error)}
            </div>
          ) : (
            <div className="overflow-hidden rounded-2xl border border-slate-800">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Side</TableHead>
                    <TableHead>Confidence</TableHead>
                    <TableHead>Summary</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {signals.map((signal) => (
                    <TableRow key={signal.signal_id}>
                      <TableCell className="font-medium text-slate-100">{signal.signal_id}</TableCell>
                      <TableCell>{signal.symbol}</TableCell>
                      <TableCell>
                        <Badge variant="info">{signal.side}</Badge>
                      </TableCell>
                      <TableCell>{formatConfidence(signal.confidence)}</TableCell>
                      <TableCell className="max-w-[18rem] text-slate-400">{signal.context_summary}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="xl:col-span-5">
        <CardHeader>
          <CardTitle>Latest signal</CardTitle>
          <CardDescription>用于快速检查最近一次生成的上下文与原始数据。</CardDescription>
        </CardHeader>
        <CardContent>
          {signalsQuery.isLoading ? (
            <Skeleton className="h-80 rounded-2xl" />
          ) : (
            <SignalDetails signal={latestSignal} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}
