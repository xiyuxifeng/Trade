import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/layout/page-header';
import { ArtifactPreview } from '@/components/artifacts/artifact-preview';
import { ApiError } from '@/lib/api/http';
import {
  downloadDailyReportHtml,
  downloadEvaluationHtml,
  getDailyReport,
  getEvaluationReport,
  listDailyReports,
  listEvaluationReports,
} from '@/lib/api/reports';
import type { DailyReportDetail, EvaluationResultDetail, ReportKind, ReportSummaryItem } from '@/types/reports';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) return '当前账号没有权限查看报表。';
    if (error.status === 404) return '未找到可用的报表数据。';
    return '报表数据加载失败，请稍后重试。';
  }
  if (error instanceof Error) return '报表数据加载失败，请稍后重试。';
  return '报表数据加载失败，请稍后重试。';
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatBytes(bytes: number | null | undefined) {
  if (bytes == null) return '未知大小';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function sortReportsDesc(reports: ReportSummaryItem[]) {
  return [...reports].sort((left, right) => right.as_of_date.localeCompare(left.as_of_date));
}

function kindLabel(kind: ReportKind) {
  return kind === 'daily' ? '盘前日报' : '盘后考核';
}

function ReportListItem({
  report,
  active,
  onSelect,
}: {
  report: ReportSummaryItem;
  active: boolean;
  onSelect: () => void;
}) {
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
        <div>
          <p className="font-medium">{report.as_of_date}</p>
          <p className="mt-1 break-all text-xs text-slate-500">{report.file_path}</p>
        </div>
        <Badge variant={active ? 'info' : 'default'}>{formatBytes(report.file_size)}</Badge>
      </div>
    </button>
  );
}

function DailyDetails({ detail }: { detail: DailyReportDetail }) {
  const report = detail.report;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4" data-testid="daily-report-id">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">报告 ID</p>
          <p className="mt-2 break-all text-sm text-slate-100">{report.report_id}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">生成时间</p>
          <p className="mt-2 text-sm text-slate-100">{formatTimestamp(report.generated_at)}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">交易想法</p>
          <p className="mt-2 text-2xl font-semibold text-slate-100">{report.ideas.length}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">策略版本</p>
          <p className="mt-2 text-2xl font-semibold text-slate-100">{report.strategy_version_ids.length}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
          <h4 className="text-sm font-semibold text-slate-100">核心亮点</h4>
          {report.highlights.length ? (
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              {report.highlights.map((item) => (
                <li key={item} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2">
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-400">暂无核心亮点。</p>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
          <h4 className="text-sm font-semibold text-slate-100">风险提示</h4>
          {report.risks.length ? (
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              {report.risks.map((item) => (
                <li key={item} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2">
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-400">暂无风险提示。</p>
          )}
        </div>
      </div>
    </div>
  );
}

function EvaluationDetails({ detail }: { detail: EvaluationResultDetail }) {
  const result = detail.result;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4" data-testid="evaluation-result-id">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">结果 ID</p>
          <p className="mt-2 break-all text-sm text-slate-100">{result.result_id}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">生成时间</p>
          <p className="mt-2 text-sm text-slate-100">{formatTimestamp(result.generated_at)}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">评估项</p>
          <p className="mt-2 text-2xl font-semibold text-slate-100">{result.evaluations.length}</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">证据包</p>
          <p className="mt-2 text-2xl font-semibold text-slate-100">{result.evidence_pack_refs.length}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
          <h4 className="text-sm font-semibold text-slate-100">总结</h4>
          {result.summary.length ? (
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              {result.summary.map((item) => (
                <li key={item} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2">
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-400">暂无总结。</p>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
          <h4 className="text-sm font-semibold text-slate-100">失败分类</h4>
          {result.failure_categories.length ? (
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              {result.failure_categories.map((item) => (
                <li key={item} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2">
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-400">暂无失败分类。</p>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
          <h4 className="text-sm font-semibold text-slate-100">复盘说明</h4>
          {result.postmortem_notes.length ? (
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              {result.postmortem_notes.map((item) => (
                <li key={item} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2">
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-400">暂无复盘说明。</p>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
          <h4 className="text-sm font-semibold text-slate-100">评分特征</h4>
          <pre
            className="mt-3 max-h-64 overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200"
            data-testid="daily-report-ranking-json"
          >
            {JSON.stringify(result.ranking_features, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}

export function ReportCenter() {
  const [kind, setKind] = useState<ReportKind>('daily');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [previewMode, setPreviewMode] = useState<'html' | 'json'>('html');

  const dailyReportsQuery = useQuery({
    queryKey: ['reports', 'daily'],
    queryFn: () => listDailyReports(0, 50),
    staleTime: 10_000,
  });

  const evaluationReportsQuery = useQuery({
    queryKey: ['reports', 'evaluation'],
    queryFn: () => listEvaluationReports(0, 50),
    staleTime: 10_000,
  });

  const reports = useMemo(() => {
    const items = kind === 'daily' ? dailyReportsQuery.data?.reports ?? [] : evaluationReportsQuery.data?.reports ?? [];
    return sortReportsDesc(items);
  }, [dailyReportsQuery.data?.reports, evaluationReportsQuery.data?.reports, kind]);

  useEffect(() => {
    if (!reports.length) {
      setSelectedDate(null);
      return;
    }
    if (!selectedDate || !reports.some((report) => report.as_of_date === selectedDate)) {
      setSelectedDate(reports[0].as_of_date);
    }
  }, [reports, selectedDate]);

  const selectedReport = useMemo(
    () => reports.find((report) => report.as_of_date === selectedDate) ?? null,
    [reports, selectedDate],
  );

  const detailQuery = useQuery<DailyReportDetail | EvaluationResultDetail, ApiError>({
    queryKey: ['reports', kind, selectedDate, 'detail'],
    queryFn: async () => {
      if (!selectedDate) {
        throw new Error('No report selected');
      }
      return kind === 'daily' ? getDailyReport(selectedDate) : getEvaluationReport(selectedDate);
    },
    enabled: Boolean(selectedDate),
  });

  const htmlQuery = useQuery({
    queryKey: ['reports', kind, selectedDate, 'html'],
    queryFn: () => {
      if (!selectedDate) {
        throw new Error('No report selected');
      }
      return kind === 'daily' ? downloadDailyReportHtml(selectedDate) : downloadEvaluationHtml(selectedDate);
    },
    enabled: Boolean(selectedDate) && previewMode === 'html',
    staleTime: 10_000,
  });

  const summary = useMemo(() => {
    const total = reports.length;
    const htmlReady = selectedDate ? 1 : 0;
    return {
      total,
      selectedDate: selectedDate || '未选择',
      htmlReady,
      kindLabel: kindLabel(kind),
    };
  }, [kind, reports.length, selectedDate]);

  const detail = detailQuery.data;
  const previewHtml = htmlQuery.data ?? '<div style="padding:24px;font-family:sans-serif;color:#0f172a">网页预览加载中...</div>';

  return (
    <main className="page-stack">
      <PageHeader
        kicker="报告"
        title="报告中心"
        description="浏览盘前报告和收盘后的评估记录，支持 HTML 和 JSON 视图。"
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(320px,0.8fr)_minmax(0,1.2fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>报告类别</CardTitle>
                <CardDescription>在盘前和收盘记录之间切换。</CardDescription>
              </div>
              <Button
                variant="outline"
                onClick={() => {
                  dailyReportsQuery.refetch();
                  evaluationReportsQuery.refetch();
                }}
                disabled={dailyReportsQuery.isFetching || evaluationReportsQuery.isFetching}
              >
                {dailyReportsQuery.isFetching || evaluationReportsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <button
                className={`rounded-2xl border p-4 text-left transition-colors ${
                  kind === 'daily'
                    ? 'border-sky-500/40 bg-sky-500/10 text-sky-100'
                    : 'border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
                }`}
                onClick={() => {
                  setKind('daily');
                  setPreviewMode('html');
                  setSelectedDate(null);
                }}
                type="button"
              >
                <p className="text-sm font-medium">{kindLabel('daily')}</p>
                <p className="mt-1 text-xs text-slate-400">{dailyReportsQuery.data?.count ?? 0} 个项目</p>
              </button>
              <button
                className={`rounded-2xl border p-4 text-left transition-colors ${
                  kind === 'evaluation'
                    ? 'border-sky-500/40 bg-sky-500/10 text-sky-100'
                    : 'border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
                }`}
                onClick={() => {
                  setKind('evaluation');
                  setPreviewMode('html');
                  setSelectedDate(null);
                }}
                type="button"
              >
                <p className="text-sm font-medium">{kindLabel('evaluation')}</p>
                <p className="mt-1 text-xs text-slate-400">{evaluationReportsQuery.data?.count ?? 0} 个项目</p>
              </button>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">总计</p>
                <p className="mt-2 text-2xl font-semibold text-slate-100">{summary.total}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">已选日期</p>
                <p className="mt-2 text-sm font-semibold text-sky-300">{summary.selectedDate}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">预览就绪</p>
                <p className="mt-2 text-2xl font-semibold text-slate-100">{summary.htmlReady}</p>
              </div>
            </div>

            {kind === 'daily' ? (
              dailyReportsQuery.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : dailyReportsQuery.error ? (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                  {getErrorMessage(dailyReportsQuery.error)}
                </div>
              ) : !reports.length ? (
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                  暂无盘前日报。
                </div>
              ) : (
                <div className="space-y-3">
                  {reports.map((report) => (
                    <ReportListItem
                      active={report.as_of_date === selectedDate}
                      key={report.as_of_date}
                      onSelect={() => {
                        setSelectedDate(report.as_of_date);
                        setPreviewMode('html');
                      }}
                      report={report}
                    />
                  ))}
                </div>
              )
            ) : evaluationReportsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : evaluationReportsQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(evaluationReportsQuery.error)}
              </div>
            ) : !reports.length ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                暂无盘后考核。
              </div>
            ) : (
              <div className="space-y-3">
                {reports.map((report) => (
                  <ReportListItem
                    active={report.as_of_date === selectedDate}
                    key={report.as_of_date}
                    onSelect={() => {
                      setSelectedDate(report.as_of_date);
                      setPreviewMode('html');
                    }}
                    report={report}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>{kindLabel(kind)}</CardTitle>
                <CardDescription>
                  {selectedReport ? `${selectedReport.as_of_date} · ${selectedReport.file_path}` : '请选择一条报表记录。'}
                </CardDescription>
              </div>
              {selectedReport ? <Badge variant="info">{selectedReport.as_of_date}</Badge> : null}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedDate ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                当前分类下没有可展示的报表。
              </div>
            ) : detailQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-64 w-full" />
              </div>
            ) : detailQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(detailQuery.error)}
              </div>
            ) : detail ? (
              <div className="space-y-4">
                <Tabs className="w-full" defaultValue="html" onValueChange={(value) => setPreviewMode(value as 'html' | 'json')} value={previewMode}>
                  <TabsList>
                    <TabsTrigger value="html">网页预览</TabsTrigger>
                    <TabsTrigger value="json">结构化详情</TabsTrigger>
                  </TabsList>

                  <TabsContent value="html">
                    {htmlQuery.isLoading ? (
                      <div className="space-y-3">
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-[30rem] w-full" />
                      </div>
                    ) : htmlQuery.error ? (
                      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                        {getErrorMessage(htmlQuery.error)}
                      </div>
                    ) : (
                      <ArtifactPreview content={previewHtml} kind="html" title="网页预览" />
                    )}
                  </TabsContent>

                  <TabsContent value="json">
                    <pre
                      className="max-h-[36rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200"
                      data-testid="report-detail-json"
                    >
                      {JSON.stringify(detail, null, 2)}
                    </pre>
                  </TabsContent>
                </Tabs>

                {kind === 'daily' ? <DailyDetails detail={detail as DailyReportDetail} /> : <EvaluationDetails detail={detail as EvaluationResultDetail} />}
              </div>
            ) : null}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
