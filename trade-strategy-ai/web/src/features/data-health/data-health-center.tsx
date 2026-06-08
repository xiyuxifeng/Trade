import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { buildDashboardReport } from '@/lib/api/dataHealth';
import type { DashboardReportResponse } from '@/types/dataHealth';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) return '当前账号没有权限查看数据健康报告。';
    return '数据健康报告加载失败，请稍后重试。';
  }
  if (error instanceof Error) return '数据健康报告加载失败，请稍后重试。';
  return '数据健康报告加载失败，请稍后重试。';
}

function SummaryCard({
  title,
  value,
  valueClassName = 'text-slate-950',
}: {
  title: string;
  value: string | number;
  valueClassName?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-1 font-semibold ${valueClassName}`}>{value}</p>
    </div>
  );
}

function formatRelativeHtmlPath(htmlPath: string | null | undefined) {
  const rawPath = htmlPath?.trim();
  if (!rawPath) {
    return 'n/a';
  }
  const relativePath = rawPath.split('trade-strategy-ai/').pop();
  return relativePath ?? rawPath;
}

function ReportPanel({ report }: { report: DashboardReportResponse | null }) {
  if (!report) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500">
        页面加载后会自动构建 dashboard report。
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="success">{report.critical_alerts} critical alerts</Badge>
        <Badge variant="info">exit {report.exit_code}</Badge>
      </div>
      <div className="space-y-3">
        <SummaryCard title="HTML path" value={formatRelativeHtmlPath(report.html_path)} valueClassName="break-words font-mono text-sm text-sky-700" />
        <SummaryCard title="Report keys" value={Object.keys(report.report).length} valueClassName="text-xl text-emerald-700" />
      </div>
      <details className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">查看原始 JSON</summary>
        <pre
          className="mt-3 max-h-64 overflow-auto rounded-xl border border-slate-200 bg-white p-3 text-xs text-slate-700"
          data-testid="data-health-json"
        >
          {JSON.stringify(report, null, 2)}
        </pre>
      </details>
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
    <section className="space-y-4">
      <Card className="border-slate-200 bg-white shadow-sm">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="text-slate-950">数据健康报告</CardTitle>
              <CardDescription className="text-slate-600">
                读取后端生成的数据健康报告和 HTML 产物路径，便于快速确认数据健康状况。
              </CardDescription>
            </div>
            <Button variant="outline" onClick={() => reportQuery.refetch()} disabled={reportQuery.isFetching}>
              {reportQuery.isFetching ? '刷新中' : '刷新'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm text-slate-600">
              {reportQuery.isLoading ? '正在加载报告...' : '报告只读展示，不在前端执行任何写入。'}
            </p>
          </div>
          {reportQuery.isLoading ? (
            <Skeleton className="h-80 rounded-2xl bg-slate-100" />
          ) : reportQuery.isError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-6 text-sm text-rose-700">
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
