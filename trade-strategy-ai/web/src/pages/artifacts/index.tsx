import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Search } from 'lucide-react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, ErrorState, LoadingState } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { listArtifactFilterOptions, listArtifacts } from '@/lib/api/artifacts';
import type { ArtifactRecord, ArtifactsListResponse } from '@/types/artifacts';

const DEFAULT_KIND_OPTIONS = ['html', 'json', 'yaml', 'markdown', 'csv', 'text', 'parquet', 'tar.gz', 'zip'];
const DEFAULT_LIMIT = 50;

function formatBytes(bytes: number | null | undefined) {
  if (bytes == null) return '未知大小';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTimestamp(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function mapLabel(value: string, mapping: Record<string, string>) {
  return mapping[value] || value;
}

const JOB_TYPE_LABELS: Record<string, string> = {
  'snapshot-build': '市场上下文准备',
  'strategy-build': '策略构建',
  'run-pre-market': '盘前运行',
  'run-after-close': '盘后运行',
  'rule-pool-backtest': '规则池回测',
  'rule-review': '规则审核',
  'candidate-review': '候选审核',
  'optimize-create-candidate': '候选生成',
};

function SummaryTile({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-base font-semibold text-slate-950">{value ?? 'n/a'}</p>
    </div>
  );
}

function ArtifactListItem({
  artifact,
  onOpenDetail,
}: {
  artifact: ArtifactRecord;
  onOpenDetail: () => void;
}) {
  return (
    <Card className="border-slate-200 bg-white shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="break-all text-base text-slate-900">{artifact.title || artifact.name}</CardTitle>
              <Badge variant={artifact.previewable ? 'success' : 'warning'}>{artifact.kind}</Badge>
              {artifact.job_type ? <Badge variant="info">{mapLabel(artifact.job_type, JOB_TYPE_LABELS)}</Badge> : null}
            </div>
            <CardDescription className="break-all text-slate-600">{artifact.name}</CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={onOpenDetail} size="sm" variant="outline">
              查看详情
            </Button>
            {artifact.job_id ? (
              <Link
                className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/40"
                to={`/system/jobs/${artifact.job_id}`}
              >
                查看来源 Job
                <ArrowRight className="ml-1 h-4 w-4" />
              </Link>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent className="grid gap-3 text-sm text-slate-600 md:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">来源</p>
          <p className="mt-1 break-all text-slate-900">{artifact.source}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">任务</p>
          <p className="mt-1 break-all text-slate-900">{artifact.job_id ?? '无'}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">修改时间</p>
          <p className="mt-1 break-all text-slate-900">{formatTimestamp(artifact.modified_at)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">大小</p>
          <p className="mt-1 break-all text-slate-900">{formatBytes(artifact.size_bytes)}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function FilterSelect({
  label,
  ariaLabel,
  value,
  onChange,
  options,
  optionLabels,
  placeholder = '全部',
  disabled = false,
}: {
  label: string;
  ariaLabel: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
  optionLabels?: Record<string, string>;
  placeholder?: string;
  disabled?: boolean;
}) {
  return (
    <label className="space-y-2 text-sm text-slate-700">
      <span className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</span>
      <Select
        aria-label={ariaLabel}
        className="border-slate-200 bg-white text-slate-900"
        disabled={disabled}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {mapLabel(option, optionLabels ?? {})}
            {optionLabels?.[option] ? ` (${option})` : ''}
          </option>
        ))}
      </Select>
    </label>
  );
}

function JobIdSelect({
  value,
  onChange,
  options,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  disabled?: boolean;
}) {
  const normalized = value.trim().toLowerCase();
  const filteredOptions = useMemo(() => {
    if (!normalized) {
      return options;
    }
    return options.filter((option) => option.toLowerCase().includes(normalized));
  }, [normalized, options]);

  return (
    <div className="space-y-2 text-sm text-slate-700">
      <span className="text-xs uppercase tracking-[0.16em] text-slate-500">任务 ID</span>
      <Input
        aria-label="任务 ID"
        autoComplete="off"
        className="border-slate-200 bg-white text-slate-900"
        disabled={disabled}
        list="artifact-job-id-options"
        placeholder="输入或选择 Job ID"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <datalist id="artifact-job-id-options">
        {filteredOptions.length ? (
          filteredOptions.map((option) => <option key={option} value={option} />)
        ) : (
          <option value="" />
        )}
      </datalist>
    </div>
  );
}

export function ArtifactsPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialKind = searchParams.get('kind') ?? '';
  const initialSource = searchParams.get('source') ?? '';
  const initialJobType = searchParams.get('jobType') ?? searchParams.get('job_type') ?? '';
  const initialJobId = searchParams.get('jobId') ?? searchParams.get('job_id') ?? '';
  const initialDate = searchParams.get('date') ?? '';
  const [draftFilters, setDraftFilters] = useState({
    kind: initialKind,
    source: initialSource,
    jobType: initialJobType,
    jobId: initialJobId,
    date: initialDate,
  });
  const [appliedFilters, setAppliedFilters] = useState({
    kind: initialKind,
    source: initialSource,
    jobType: initialJobType,
    jobId: initialJobId,
    date: initialDate,
  });
  const filterOptionsQuery = useQuery({
    queryKey: ['artifacts', 'filter-options'],
    queryFn: () => listArtifactFilterOptions(),
    staleTime: 60_000,
  });

  const artifactsQuery = useQuery<ArtifactsListResponse, ApiError>({
    queryKey: ['artifacts', appliedFilters],
    queryFn: () =>
      listArtifacts({
        kind: appliedFilters.kind || undefined,
        source: appliedFilters.source || undefined,
        job_type: appliedFilters.jobType || undefined,
        date: appliedFilters.date || undefined,
        job_id: appliedFilters.jobId || undefined,
        limit: DEFAULT_LIMIT,
      }),
    staleTime: 10_000,
  });

  const filterOptions = filterOptionsQuery.data ?? {
    status: 'success',
    kinds: DEFAULT_KIND_OPTIONS,
    sources: [],
    job_types: [],
    job_ids: [],
  };

  const artifacts = artifactsQuery.data?.items ?? [];
  const summary = useMemo(
    () => ({
      total: artifactsQuery.data?.total ?? 0,
      pageCount: artifacts.length,
      previewable: artifacts.filter((item) => item.previewable).length,
      linkedJobs: artifacts.filter((item) => Boolean(item.job_id)).length,
      jobTypes: new Set(artifacts.map((item) => item.job_type).filter(Boolean) ?? []).size,
    }),
    [artifacts, artifactsQuery.data?.total],
  );

  return (
    <main className="page-stack">
      <PageHeader
        kicker="正式工作台"
        title="产物中心"
        description="跨 Job 检索、预览和下载正式产物。"
      />

      <section className="grid gap-6">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-900">筛选条件</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {filterOptionsQuery.isLoading ? (
              <LoadingState label="正在加载筛选选项" description="稍后会展示可选的 kind、来源、job type 和 Job ID。" />
            ) : filterOptionsQuery.error ? (
              <ErrorState
                {...buildErrorRecoveryState(filterOptionsQuery.error, 'artifact-filter-options')}
                onRetry={() => void filterOptionsQuery.refetch()}
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <FilterSelect
                  label="产物类型"
                  ariaLabel="产物类型"
                  value={draftFilters.kind}
                  onChange={(value) => setDraftFilters((current) => ({ ...current, kind: value }))}
                  options={filterOptions.kinds.length ? filterOptions.kinds : DEFAULT_KIND_OPTIONS}
                  disabled={artifactsQuery.isFetching}
                />
                <FilterSelect
                  label="来源"
                  ariaLabel="来源"
                  value={draftFilters.source}
                  onChange={(value) => setDraftFilters((current) => ({ ...current, source: value }))}
                  options={filterOptions.sources}
                  disabled={artifactsQuery.isFetching}
                />
                <FilterSelect
                  label="Job Type"
                  ariaLabel="Job Type"
                  value={draftFilters.jobType}
                  onChange={(value) => setDraftFilters((current) => ({ ...current, jobType: value }))}
                  options={filterOptions.job_types}
                  optionLabels={JOB_TYPE_LABELS}
                  disabled={artifactsQuery.isFetching}
                />
                <JobIdSelect
                  value={draftFilters.jobId}
                  onChange={(value) => setDraftFilters((current) => ({ ...current, jobId: value }))}
                  options={filterOptions.job_ids}
                  disabled={artifactsQuery.isFetching}
                />
                <label className="space-y-2 text-sm text-slate-700">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">日期</span>
                  <Input
                    type="date"
                    value={draftFilters.date}
                    onChange={(event) => setDraftFilters((current) => ({ ...current, date: event.target.value }))}
                  />
                </label>
              </div>
            )}
            <div className="flex flex-wrap items-center justify-start gap-2">
              <Button
                className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                disabled={artifactsQuery.isFetching}
                onClick={() => {
                  setDraftFilters({
                    kind: '',
                    source: '',
                    jobType: '',
                    jobId: '',
                    date: '',
                  });
                  setAppliedFilters({
                    kind: '',
                    source: '',
                    jobType: '',
                    jobId: '',
                    date: '',
                  });
                  setSearchParams({});
                }}
                variant="outline"
              >
                重置
              </Button>
              <Button
                onClick={() => {
                  const nextFilters = { ...draftFilters };
                  setAppliedFilters(nextFilters);
                  const nextSearchParams = new URLSearchParams();
                  if (nextFilters.kind) nextSearchParams.set('kind', nextFilters.kind);
                  if (nextFilters.source) nextSearchParams.set('source', nextFilters.source);
                  if (nextFilters.jobType) nextSearchParams.set('jobType', nextFilters.jobType);
                  if (nextFilters.jobId) nextSearchParams.set('jobId', nextFilters.jobId);
                  if (nextFilters.date) nextSearchParams.set('date', nextFilters.date);
                  setSearchParams(nextSearchParams);
                }}
              >
                <Search className="h-4 w-4" />
                搜索
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="text-slate-900">最近产物</CardTitle>
              </div>
              <Badge variant="info" className="rounded-full px-3 py-1 text-xs">
                总计 {summary.total}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
              <SummaryTile label="结果数" value={summary.pageCount} />
              <SummaryTile label="总计" value={summary.total} />
              <SummaryTile label="可预览" value={summary.previewable} />
              <SummaryTile label="可回溯 Job" value={summary.linkedJobs} />
              <SummaryTile label="Job Type 数" value={summary.jobTypes} />
            </div>

            {artifactsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : artifactsQuery.error ? (
              <ErrorState
                {...buildErrorRecoveryState(artifactsQuery.error, 'artifacts')}
                onRetry={() => void artifactsQuery.refetch()}
              />
            ) : !artifacts.length ? (
              <EmptyState title="暂无可显示的产物。" description="调整筛选条件后再搜索，或等待新的 Job 生成产物。"/>
            ) : (
              <div className="max-h-[60vh] space-y-4 overflow-y-auto pr-1">
                {artifacts.map((artifact) => (
                  <ArtifactListItem
                    artifact={artifact}
                    key={artifact.artifact_id}
                    onOpenDetail={() => navigate(`/artifacts/${artifact.artifact_id}`)}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}

export { ArtifactDetailPage } from './ArtifactDetailPage';
