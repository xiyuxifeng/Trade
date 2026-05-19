import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowRight, ExternalLink } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from '@/components/ui/drawer';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { ArtifactPreview } from '@/components/artifacts/artifact-preview';
import { ApiError } from '@/lib/api/http';
import { downloadArtifact, getArtifact, listArtifacts } from '@/lib/api/artifacts';
import type { ArtifactRecord, ArtifactsListResponse } from '@/types/artifacts';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '产物数据加载失败';
}

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

function ArtifactCenterCard({
  artifact,
  onSelect,
}: {
  artifact: ArtifactRecord;
  onSelect: () => void;
}) {
  return (
    <Card className="border-slate-200 bg-white shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="break-all text-base text-slate-900">{artifact.title || artifact.name}</CardTitle>
              <Badge variant={artifact.previewable ? 'success' : 'warning'}>{artifact.kind}</Badge>
              {artifact.job_type ? <Badge variant="info">{artifact.job_type}</Badge> : null}
            </div>
            <CardDescription className="break-all text-slate-600">{artifact.name}</CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={onSelect} size="sm" variant="outline">
              查看详情
            </Button>
            {artifact.job_id ? (
              <Link
                className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/40"
                to={`/jobs/${artifact.job_id}`}
              >
                查看来源 Job
                <ExternalLink className="ml-1 h-4 w-4" />
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

export function ArtifactsPage() {
  const [kind, setKind] = useState('');
  const [jobType, setJobType] = useState('');
  const [date, setDate] = useState('');
  const [source, setSource] = useState('');
  const [query, setQuery] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const jobId = searchParams.get('jobId') ?? '';
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const artifactsQuery = useQuery<ArtifactsListResponse, ApiError>({
    queryKey: ['artifacts', { kind, jobType, date, source, query, jobId }],
    queryFn: () =>
      listArtifacts({
        kind: kind || undefined,
        source: source || undefined,
        job_type: jobType || undefined,
        date: date || undefined,
        job_id: jobId || undefined,
        q: query || undefined,
        limit: 50,
      }),
    staleTime: 10_000,
  });

  const detailQuery = useQuery({
    queryKey: ['artifact-detail', selectedArtifactId],
    queryFn: () => getArtifact(selectedArtifactId as string),
    enabled: Boolean(selectedArtifactId),
  });

  const downloadMutation = useMutation({
    mutationFn: async () => {
      if (!selectedArtifactId) throw new Error('No artifact selected');
      const blob = await downloadArtifact(selectedArtifactId);
      const detail = detailQuery.data;
      if (typeof window.URL.createObjectURL !== 'function') {
        return;
      }
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = detail?.download_name || detail?.name || 'artifact';
      a.click();
      window.URL.revokeObjectURL(url);
    },
    onMutate: () => {
      setDownloadError(null);
    },
    onError: (error) => {
      const status =
        error instanceof ApiError
          ? error.status
          : typeof error === 'object' && error !== null && 'status' in error && typeof (error as { status?: unknown }).status === 'number'
            ? (error as { status: number }).status
            : null;
      if (status === 403 || status === 401) {
        setDownloadError('没有权限下载该产物。');
        return;
      }
      if (status === 404) {
        setDownloadError('产物缺失或已被清理，无法下载。');
        return;
      }
      if (error instanceof Error) {
        setDownloadError(error.message);
        return;
      }
      setDownloadError('下载产物失败。');
    },
  });

  const selectedArtifact = detailQuery.data ?? null;
  const summary = useMemo(() => {
    const total = artifactsQuery.data?.total ?? 0;
    const previewable = artifactsQuery.data?.items.filter((item) => item.previewable).length ?? 0;
    const linkedJobs = artifactsQuery.data?.items.filter((item) => Boolean(item.job_id)).length ?? 0;
    const jobTypes = new Set(artifactsQuery.data?.items.map((item) => item.job_type).filter(Boolean) ?? []);
    return { total, previewable, linkedJobs, jobTypes: jobTypes.size };
  }, [artifactsQuery.data]);

  return (
    <main className="page-stack">
      {/* <PageHeader
        kicker="正式工作台"
        title="产物中心"
        description="跨 Job 检索、预览和下载正式产物。"
      /> */}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.55fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle className="text-slate-900">最近产物</CardTitle>
                <CardDescription className="text-slate-600">按 kind、job type、日期与文本关键字过滤。</CardDescription>
              </div>
              <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={() => artifactsQuery.refetch()} disabled={artifactsQuery.isFetching} variant="outline">
                {artifactsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="grid gap-3 md:grid-cols-4">
              <Input placeholder="搜索文本" value={query} onChange={(event) => setQuery(event.target.value)} />
              <Input placeholder="按 job type 过滤" value={jobType} onChange={(event) => setJobType(event.target.value)} />
              <Input placeholder="按日期过滤" value={date} onChange={(event) => setDate(event.target.value)} />
              <Select aria-label="Artifact kind" value={kind} onChange={(event) => setKind(event.target.value)}>
                <option value="">所有类型</option>
                <option value="html">html</option>
                <option value="json">json</option>
                <option value="yaml">yaml</option>
                <option value="markdown">markdown</option>
                <option value="csv">csv</option>
                <option value="text">text</option>
                <option value="parquet">parquet</option>
                <option value="tar.gz">tar.gz</option>
                <option value="zip">zip</option>
              </Select>
            </div>

            <div className="grid gap-3 md:grid-cols-4">
              <Input
                placeholder="按来源过滤"
                value={source}
                onChange={(event) => setSource(event.target.value)}
              />
              <Input
                placeholder="按任务 ID 过滤"
                value={jobId}
                onChange={(event) =>
                  setSearchParams((current) => {
                    const next = new URLSearchParams(current);
                    const value = event.target.value.trim();
                    if (value) {
                      next.set('jobId', value);
                    } else {
                      next.delete('jobId');
                    }
                    return next;
                  })
                }
              />
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">总计</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{summary.total}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">job types</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{summary.jobTypes}</p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">可预览</p>
                <p className="mt-2 text-2xl font-semibold text-sky-700">{summary.previewable}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">可回溯 Job</p>
                <p className="mt-2 text-2xl font-semibold text-emerald-700">{summary.linkedJobs}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 md:col-span-2 xl:col-span-2">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">说明</p>
                <p className="mt-2 text-sm text-slate-600">所有预览与下载均通过 UI BFF 进行，不直接暴露服务器绝对路径。</p>
              </div>
            </div>

            {artifactsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : artifactsQuery.error ? (
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                {getErrorMessage(artifactsQuery.error)}
              </div>
            ) : !artifactsQuery.data?.items.length ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
                暂无可显示的产物。
              </div>
            ) : (
              <div className="space-y-4">
                {artifactsQuery.data.items.map((artifact) => (
                  <ArtifactCenterCard
                    artifact={artifact}
                    key={artifact.artifact_id}
                    onSelect={() => {
                      setDownloadError(null);
                      setSelectedArtifactId(artifact.artifact_id);
                    }}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <CardTitle className="text-slate-900">使用说明</CardTitle>
            <CardDescription className="text-slate-600">预览、下载和回溯都从这里进入。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-600">
            <ul className="list-disc space-y-2 pl-5 text-slate-500">
              <li>优先通过 job type、日期和关键字定位最近产物。</li>
              <li>打开详情后可查看安全预览、元数据和下载入口。</li>
              <li>如果有来源 Job，可以直接跳转到对应 Job Detail。</li>
            </ul>
          </CardContent>
        </Card>
      </section>

      <Drawer
        open={Boolean(selectedArtifactId)}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedArtifactId(null);
            setDownloadError(null);
          }
        }}
      >
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>产物详情</DrawerTitle>
            <DrawerDescription>{selectedArtifact ? selectedArtifact.title || selectedArtifact.name : '未选择产物'}</DrawerDescription>
          </DrawerHeader>

          {detailQuery.isError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              {getErrorMessage(detailQuery.error)}
            </div>
          ) : !selectedArtifact ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : (
            <div className="grid gap-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">来源 Job</p>
                  <p className="mt-1 text-sm text-slate-900">{selectedArtifact.job_id ?? '无'}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">job type</p>
                  <p className="mt-1 text-sm text-slate-900">{selectedArtifact.job_type ?? '未知'}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">大小</p>
                  <p className="mt-1 text-sm text-slate-900">{formatBytes(selectedArtifact.size_bytes)}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">修改时间</p>
                  <p className="mt-1 text-sm text-slate-900">{formatTimestamp(selectedArtifact.modified_at)}</p>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">存储引用</p>
                <p className="mt-1 break-all text-sm text-slate-900">
                  {selectedArtifact.storage_ref?.relative_path ?? selectedArtifact.storage_ref?.logical_id ?? '未提供'}
                </p>
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-700">预览</p>
                {detailQuery.isLoading ? (
                  <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-500">预览加载中...</div>
                ) : (
                  <ArtifactPreview kind={selectedArtifact.kind} content={selectedArtifact.preview ?? ''} />
                )}
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-700">元数据</p>
                <pre className="max-h-52 overflow-auto rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-700">
                  {JSON.stringify(selectedArtifact.metadata, null, 2)}
                </pre>
              </div>

              {selectedArtifact.job_id ? (
                <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm text-slate-700">
                  <Link className="inline-flex items-center gap-1 text-sky-700 hover:underline" to={`/jobs/${selectedArtifact.job_id}`}>
                    查看来源 Job
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              ) : null}
            </div>
          )}

          {downloadError ? (
            <div
              className={`rounded-xl border p-3 text-sm ${
                downloadError.includes('权限')
                  ? 'border-amber-200 bg-amber-50 text-amber-800'
                  : 'border-rose-200 bg-rose-50 text-rose-700'
              }`}
            >
              {downloadError}
            </div>
          ) : null}

          <DrawerFooter>
            <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={() => setSelectedArtifactId(null)} variant="outline">
              关闭
            </Button>
            <Button onClick={() => downloadMutation.mutate()} disabled={downloadMutation.isPending || !selectedArtifact}>
              {downloadMutation.isPending ? '下载中' : '下载'}
            </Button>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </main>
  );
}
