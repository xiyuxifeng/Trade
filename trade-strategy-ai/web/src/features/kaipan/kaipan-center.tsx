import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { formatLocalDateInputOffset } from '@/lib/date';
import { kaipanFetch, kaipanNormalize, kaipanRun, kaipanStatus } from '@/lib/api/kaipan';
import type { KaipanFetchResponse, KaipanNormalizeResponse, KaipanRunResponse } from '@/types/kaipan';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Kaipan 数据加载失败';
}

function SummaryCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function ResultPanel({ title, payload }: { title: string; payload: unknown }) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-slate-200">{title}</p>
      <pre className="max-h-[18rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
        {JSON.stringify(payload, null, 2)}
      </pre>
    </div>
  );
}

export function KaipanCenter() {
  const [tradeDate, setTradeDate] = useState(formatLocalDateInputOffset(0));
  const [slot, setSlot] = useState('all');
  const [startScheduler, setStartScheduler] = useState(false);
  const [block, setBlock] = useState(false);
  const [fetchResult, setFetchResult] = useState<KaipanFetchResponse | null>(null);
  const [normalizeResult, setNormalizeResult] = useState<KaipanNormalizeResponse | null>(null);
  const [runResult, setRunResult] = useState<KaipanRunResponse | null>(null);

  const statusQuery = useQuery({
    queryKey: ['kaipan', 'status'],
    queryFn: () => kaipanStatus(),
    staleTime: 10_000,
  });

  const fetchMutation = useMutation({
    mutationFn: () => kaipanFetch({ trade_date: tradeDate || null, slot }),
    onSuccess: async (payload) => {
      setFetchResult(payload);
      await statusQuery.refetch();
    },
  });

  const normalizeMutation = useMutation({
    mutationFn: () => kaipanNormalize({ trade_date: tradeDate || null, slot }),
    onSuccess: async (payload) => {
      setNormalizeResult(payload);
      await statusQuery.refetch();
    },
  });

  const runMutation = useMutation({
    mutationFn: () => kaipanRun({ start_scheduler: startScheduler, block }),
    onSuccess: (payload) => {
      setRunResult(payload);
    },
  });

  const status = statusQuery.data ?? null;

  const latestSlot = useMemo(() => status?.latest_slot ?? 'n/a', [status]);
  const ingestionItems = ['MarketStockZDNum', 'ZhangTingExpression', 'DailyLimitIndex', 'WeightPerformance', 'GetFengKList'];

  return (
    <section className="dashboard-grid">
      <Card className="xl:col-span-7">
        <CardHeader>
          <CardTitle>Fetch and normalize</CardTitle>
          <CardDescription>输入交易日和 slot 后，先抓取，再按同样参数执行标准化。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm text-slate-300">
              <span>Trade date</span>
              <Input value={tradeDate} onChange={(event) => setTradeDate(event.target.value)} type="date" />
            </label>
            <label className="space-y-2 text-sm text-slate-300">
              <span>Slot</span>
              <Select value={slot} onChange={(event) => setSlot(event.target.value)}>
                <option value="all">all</option>
                <option value="09-25">09-25</option>
                <option value="17-30">17-30</option>
              </Select>
            </label>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => fetchMutation.mutate()} disabled={fetchMutation.isPending}>
              {fetchMutation.isPending ? 'Fetching...' : 'Fetch'}
            </Button>
            <Button variant="outline" onClick={() => normalizeMutation.mutate()} disabled={normalizeMutation.isPending}>
              {normalizeMutation.isPending ? 'Normalizing...' : 'Normalize'}
            </Button>
          </div>
          {fetchMutation.isError ? <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">{getErrorMessage(fetchMutation.error)}</div> : null}
          {normalizeMutation.isError ? <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">{getErrorMessage(normalizeMutation.error)}</div> : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <SummaryCard title="Trade date" value={tradeDate} accent="text-sky-300" />
            <SummaryCard title="Slot" value={slot} accent="text-emerald-300" />
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">10.5 ingestion</p>
            <p className="mt-2 text-sm text-slate-300">现有 /kaipan 入口会一并抓取并标准化以下新增接口，结果继续流入 snapshot / DB 链路。</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {ingestionItems.map((item) => (
                <span key={item} className="rounded-full border border-slate-800 bg-slate-900/80 px-3 py-1 text-xs text-slate-200">
                  {item}
                </span>
              ))}
            </div>
          </div>
          {fetchResult ? <ResultPanel title="Fetch result" payload={fetchResult} /> : null}
          {normalizeResult ? <ResultPanel title="Normalize result" payload={normalizeResult} /> : null}
        </CardContent>
      </Card>

      <Card className="xl:col-span-5">
        <CardHeader>
          <CardTitle>Status and run</CardTitle>
          <CardDescription>状态是只读的，run 则交给后端控制是否启动调度器。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {statusQuery.isLoading ? (
            <Skeleton className="h-32 rounded-2xl" />
          ) : statusQuery.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">
              {getErrorMessage(statusQuery.error)}
            </div>
          ) : (
            <div className="grid gap-3 md:grid-cols-2">
              <SummaryCard title="Latest slot" value={latestSlot} accent="text-sky-300" />
              <SummaryCard title="Raw base" value={status?.raw_base ?? 'n/a'} accent="text-amber-300" />
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
              <input
                checked={startScheduler}
                onChange={(event) => setStartScheduler(event.target.checked)}
                type="checkbox"
                className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-sky-500"
              />
              <span>Start scheduler</span>
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
              <input
                checked={block}
                onChange={(event) => setBlock(event.target.checked)}
                type="checkbox"
                className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-sky-500"
              />
              <span>Block</span>
            </label>
          </div>
          <Button onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
            {runMutation.isPending ? 'Running...' : 'Run Kaipan'}
          </Button>
          {runMutation.isError ? <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">{getErrorMessage(runMutation.error)}</div> : null}
          {runResult ? <ResultPanel title="Run result" payload={runResult} /> : null}
        </CardContent>
      </Card>
    </section>
  );
}
