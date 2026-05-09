import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ApiError } from '@/lib/api/http';
import { buildSampleClusters } from '@/lib/api/persona';
import type { PersonaClustersResponse } from '@/types/persona';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Persona 样例生成失败';
}

function SummaryCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

export function PersonaCenter() {
  const [result, setResult] = useState<PersonaClustersResponse | null>(null);

  const mutation = useMutation({
    mutationFn: () => buildSampleClusters(),
    onSuccess: (payload) => {
      setResult(payload);
    },
  });

  return (
    <section className="dashboard-grid">
      <Card className="xl:col-span-5">
        <CardHeader>
          <CardTitle>Generate sample clusters</CardTitle>
          <CardDescription>生成可运行的 Persona 样例聚类文件，便于验证聚类和 MarketState 的输入链路。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending ? 'Generating...' : 'Generate sample clusters'}
          </Button>
          {mutation.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">
              {getErrorMessage(mutation.error)}
            </div>
          ) : null}
          {result ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <SummaryCard title="Traders" value={result.trader_count} accent="text-sky-300" />
              <SummaryCard title="Clusters" value={result.clusters_count} accent="text-emerald-300" />
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-6 text-sm text-slate-500">
              点击按钮后，会在后端生成 clusters.sample.json。
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="xl:col-span-7">
        <CardHeader>
          <CardTitle>Sample output</CardTitle>
          <CardDescription>展示生成文件路径与聚类结果快照。</CardDescription>
        </CardHeader>
        <CardContent>
          {result ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="success">{result.trader_count} traders</Badge>
                <Badge variant="info">{result.clusters_count} clusters</Badge>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">clusters_path</p>
                <p className="mt-2 break-all text-sm text-slate-100">{result.clusters_path}</p>
              </div>
              <pre className="max-h-[22rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
              Sample clusters 生成后会显示在这里。
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}
