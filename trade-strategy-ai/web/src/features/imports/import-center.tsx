import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { ApiError } from '@/lib/api/http';
import { importTradeLogs, migrateCrawlState } from '@/lib/api/imports';
import type { ImportTradeLogsResponse, MigrateCrawlStateResponse } from '@/types/imports';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '导入任务失败';
}

function SummaryCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function ImportResultCard({ result }: { result: ImportTradeLogsResponse | null }) {
  if (!result) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
        上传一次交易日志后，这里会显示 rows_seen、stored_count 和校验问题。
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="success">{result.file_kind}</Badge>
        <Badge variant={result.dry_run ? 'warning' : 'info'}>{result.dry_run ? 'dry-run' : 'write'}</Badge>
        <Badge variant="info">{result.source}</Badge>
      </div>
      <div className="grid gap-3 md:grid-cols-4">
        <SummaryCard title="Rows seen" value={result.rows_seen} accent="text-sky-300" />
        <SummaryCard title="Stored" value={result.stored_count} accent="text-emerald-300" />
        <SummaryCard title="Invalid" value={result.invalid} accent="text-amber-300" />
        <SummaryCard title="Duplicates" value={result.duplicates} accent="text-fuchsia-300" />
      </div>
      <pre className="max-h-[18rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
        {JSON.stringify(result, null, 2)}
      </pre>
    </div>
  );
}

function CrawlStateResultCard({ result }: { result: MigrateCrawlStateResponse | null }) {
  if (!result) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center text-sm text-slate-500">
        点击迁移按钮后，这里会显示 migrated / skipped 结果。
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <SummaryCard title="Migrated" value={result.migrated} accent="text-sky-300" />
        <SummaryCard title="Skipped" value={result.skipped} accent="text-amber-300" />
      </div>
      <pre className="max-h-[18rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
        {JSON.stringify(result, null, 2)}
      </pre>
    </div>
  );
}

export function ImportCenter() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dryRun, setDryRun] = useState(true);
  const [source, setSource] = useState('csv_import');
  const [importResult, setImportResult] = useState<ImportTradeLogsResponse | null>(null);
  const [crawlResult, setCrawlResult] = useState<MigrateCrawlStateResponse | null>(null);

  const importMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) {
        throw new Error('请选择要上传的文件');
      }
      return importTradeLogs({ file: selectedFile, dryRun, source });
    },
    onSuccess: (payload) => {
      setImportResult(payload);
    },
  });

  const migrateMutation = useMutation({
    mutationFn: () => migrateCrawlState({}),
    onSuccess: (payload) => {
      setCrawlResult(payload);
    },
  });

  const selectedFileLabel = useMemo(() => selectedFile?.name ?? '未选择文件', [selectedFile]);

  return (
    <section className="dashboard-grid">
      <Card className="xl:col-span-6">
        <CardHeader>
          <CardTitle>Trade log import</CardTitle>
          <CardDescription>上传 CSV / Excel / HTML / PDF 文件，先在后端临时落盘，再通过 dry-run 预览结果。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="space-y-2 text-sm text-slate-300">
            <span>File</span>
            <Input
              type="file"
              accept=".csv,.xls,.xlsx,.xlsm,.html,.htm,.pdf"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Selected: {selectedFileLabel}</p>
          <label className="space-y-2 text-sm text-slate-300">
            <span>Source</span>
            <Select value={source} onChange={(event) => setSource(event.target.value)}>
              <option value="csv_import">csv_import</option>
              <option value="excel_import">excel_import</option>
              <option value="html_import">html_import</option>
              <option value="pdf_import">pdf_import</option>
            </Select>
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-sm text-slate-300">
            <input
              checked={dryRun}
              onChange={(event) => setDryRun(event.target.checked)}
              type="checkbox"
              className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-sky-500"
            />
            <span>Dry run</span>
          </label>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => importMutation.mutate()} disabled={importMutation.isPending}>
              {importMutation.isPending ? 'Importing...' : 'Import trade logs'}
            </Button>
            <Button variant="outline" onClick={() => migrateMutation.mutate()} disabled={migrateMutation.isPending}>
              {migrateMutation.isPending ? 'Migrating...' : 'Migrate crawl state'}
            </Button>
          </div>
          {importMutation.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">
              {getErrorMessage(importMutation.error)}
            </div>
          ) : null}
          {migrateMutation.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-6 text-sm text-red-200">
              {getErrorMessage(migrateMutation.error)}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="xl:col-span-6">
        <CardHeader>
          <CardTitle>Import result</CardTitle>
          <CardDescription>查看解析统计、dry-run 结果和临时文件路径。</CardDescription>
        </CardHeader>
        <CardContent>
          <ImportResultCard result={importResult} />
        </CardContent>
      </Card>

      <Card className="xl:col-span-12">
        <CardHeader>
          <CardTitle>Crawl state migration</CardTitle>
          <CardDescription>迁移 crawl state.json 到数据库，结果卡只展示迁移摘要，不展示敏感上下文。</CardDescription>
        </CardHeader>
        <CardContent>
          <CrawlStateResultCard result={crawlResult} />
        </CardContent>
      </Card>
    </section>
  );
}
