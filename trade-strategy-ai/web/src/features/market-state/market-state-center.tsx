import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ApiError } from '@/lib/api/http';
import { formatLocalDateInputOffset } from '@/lib/date';
import { buildMarketState } from '@/lib/api/persona';
import type { MarketStateBuildResponse } from '@/types/market-state';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'MarketState 构建失败';
}

function SummaryCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

export function MarketStateCenter() {
  const [asOf, setAsOf] = useState(formatLocalDateInputOffset(0));
  const [fromAkshare, setFromAkshare] = useState(false);
  const [cacheCsv, setCacheCsv] = useState(true);
  const [result, setResult] = useState<MarketStateBuildResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      buildMarketState({
        as_of: asOf || null,
        from_akshare: fromAkshare,
        cache_csv: cacheCsv,
      }),
    onSuccess: (payload) => {
      setResult(payload);
    },
  });

  return (
    <section className="dashboard-grid">
      <Card className="xl:col-span-5">
        <CardHeader>
          <CardTitle>Build controls</CardTitle>
          <CardDescription>构建 MarketState 快照，默认优先使用现有 benchmark CSV，必要时可切换到 AkShare。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="space-y-2 text-sm text-slate-300">
            <span>As of</span>
            <Input value={asOf} onChange={(event) => setAsOf(event.target.value)} type="date" />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
              <input
                checked={fromAkshare}
                onChange={(event) => setFromAkshare(event.target.checked)}
                type="checkbox"
                className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-sky-500"
              />
              <span>Use AkShare</span>
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
              <input
                checked={cacheCsv}
                onChange={(event) => setCacheCsv(event.target.checked)}
                type="checkbox"
                className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-sky-500"
              />
              <span>Cache CSV</span>
            </label>
          </div>
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? 'Building...' : 'Build MarketState'}
          </Button>
          {mutation.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">
              {getErrorMessage(mutation.error)}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="xl:col-span-7">
        <CardHeader>
          <CardTitle>Snapshot output</CardTitle>
          <CardDescription>展示 MarketState 快照路径、来源和原始结构。</CardDescription>
        </CardHeader>
        <CardContent>
          {result ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="info">{result.source}</Badge>
                <Badge variant="success">{result.snapshot_path ?? result.market_state_path}</Badge>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <SummaryCard title="Snapshot" value={result.snapshot_path ?? result.market_state_path} accent="text-sky-300" />
                <SummaryCard title="Source" value={result.source} accent="text-emerald-300" />
                <SummaryCard title="Mode" value={fromAkshare ? 'AkShare' : 'Cache / CSV'} accent="text-amber-300" />
              </div>
              <pre className="max-h-[22rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
              构建完成后会在这里显示快照路径和 MarketState 预览。
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
