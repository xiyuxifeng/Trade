import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { buildDashboardReport } from '@/lib/api/dataHealth';
import type { DashboardReportResponse } from '@/types/dataHealth';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Dashboard 报告加载失败';
}

function SummaryCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function ReportPanel({ report }: { report: DashboardReportResponse | null }) {
  if (!report) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
        页面加载后会自动构建 dashboard report。
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="success">{report.critical_alerts} critical alerts</Badge>
        <Badge variant="info">exit {report.exit_code}</Badge>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <SummaryCard
          title="HTML path"
          value={report.html_path ?? 'n/a'}
          accent="text-sky-300"
        />
        <SummaryCard title="Report keys" value={Object.keys(report.report).length} accent="text-emerald-300" />
      </div>
      <pre
        className="max-h-[24rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200"
        data-testid="data-health-json"
      >
        {JSON.stringify(report, null, 2)}
      </pre>
    </div>
  );
}

export function DataHealthCenter() {
  const reportQuery = useQuery({
    queryKey: ['data-health', 'dashboard'],
    queryFn: () => buildDashboardReport(),
    staleTime: 10_000,
  });

  const report = reportQuery.data ?? null;

  return (
    <section className="dashboard-grid">
      <Card className="xl:col-span-12">
        <CardHeader>
          <CardTitle>Dashboard report</CardTitle>
          <CardDescription>读取后端生成的 dashboard 报告和 HTML 产物路径，便于快速确认数据健康状况。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={() => reportQuery.refetch()} disabled={reportQuery.isFetching}>
              {reportQuery.isFetching ? 'Refreshing...' : 'Refresh dashboard'}
            </Button>
            <p className="text-sm text-slate-500">
              {reportQuery.isLoading ? '正在加载 dashboard...' : '报告只读展示，不在前端执行任何写入。'}
            </p>
          </div>
          {reportQuery.isLoading ? (
            <Skeleton className="h-80 rounded-2xl" />
          ) : reportQuery.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">
              {getErrorMessage(reportQuery.error)}
            </div>
          ) : (
            <ReportPanel report={report} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}
