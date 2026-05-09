import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
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
import { PageHeader } from '@/components/layout/page-header';

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

function ArtifactCard({
  artifact,
  onSelect,
}: {
  artifact: ArtifactRecord;
  onSelect: () => void;
}) {
  return (
    <button className="text-left" onClick={onSelect} type="button">
      <Card className="h-full cursor-pointer transition-colors hover:border-sky-500/25 hover:bg-slate-900/70">
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>{artifact.name}</CardTitle>
              <CardDescription className="break-all">{artifact.path}</CardDescription>
            </div>
            <Badge variant={artifact.previewable ? 'success' : 'warning'}>{artifact.kind}</Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-300">
          <div className="grid gap-2 md:grid-cols-2">
            <div>Source: {artifact.source}</div>
            <div>Size: {formatBytes(artifact.size_bytes)}</div>
            <div>Modified: {formatTimestamp(artifact.modified_at)}</div>
            <div>Job: {artifact.job_id || 'none'}</div>
          </div>
        </CardContent>
      </Card>
    </button>
  );
}

export function ArtifactsPage() {
  const [kind, setKind] = useState('');
  const [source, setSource] = useState('');
  const [query, setQuery] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const jobId = searchParams.get('jobId') ?? '';
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);

  const artifactsQuery = useQuery<ArtifactsListResponse, ApiError>({
    queryKey: ['artifacts', { kind, source, query, jobId }],
    queryFn: () =>
      listArtifacts({
        kind: kind || undefined,
        source: source || undefined,
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
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = detail?.download_name || detail?.name || 'artifact';
      a.click();
      window.URL.revokeObjectURL(url);
    },
  });

  const selectedArtifact = detailQuery.data ?? null;
  const summary = useMemo(() => {
    const total = artifactsQuery.data?.total ?? 0;
    const previewable = artifactsQuery.data?.items.filter((item) => item.previewable).length ?? 0;
    const htmlCount = artifactsQuery.data?.items.filter((item) => item.kind === 'html').length ?? 0;
    return { total, previewable, htmlCount };
  }, [artifactsQuery.data]);

  return (
    <main className="page-stack">
      <PageHeader
        kicker="Artifacts"
        title="Artifact center"
        description="Inspect generated outputs, open previews, and download files from the UI BFF."
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.6fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Recent artifacts</CardTitle>
                <CardDescription>Filter by source, kind, or text query.</CardDescription>
              </div>
              <Button variant="outline" onClick={() => artifactsQuery.refetch()} disabled={artifactsQuery.isFetching}>
                {artifactsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-4">
              <Input placeholder="Search text" value={query} onChange={(event) => setQuery(event.target.value)} />
              <Input placeholder="Filter by source" value={source} onChange={(event) => setSource(event.target.value)} />
              <Input
                placeholder="Filter by job id"
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
              <Select value={kind} onChange={(event) => setKind(event.target.value)}>
                <option value="">All kinds</option>
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

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Total</p>
                <p className="mt-2 text-2xl font-semibold text-slate-100">{summary.total}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Previewable</p>
                <p className="mt-2 text-2xl font-semibold text-sky-300">{summary.previewable}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">HTML</p>
                <p className="mt-2 text-2xl font-semibold text-amber-300">{summary.htmlCount}</p>
              </div>
            </div>

            {artifactsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : artifactsQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(artifactsQuery.error)}
              </div>
            ) : !artifactsQuery.data?.items.length ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                暂无可显示的产物。
              </div>
            ) : (
              <div className="grid gap-4">
                {artifactsQuery.data.items.map((artifact) => (
                  <ArtifactCard
                    artifact={artifact}
                    key={artifact.artifact_id}
                    onSelect={() => setSelectedArtifactId(artifact.artifact_id)}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Usage notes</CardTitle>
            <CardDescription>Preview and download use the same authenticated UI BFF.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <ul className="list-disc space-y-2 pl-5 text-slate-400">
              <li>Open any previewable artifact to inspect its rendered preview.</li>
              <li>Download happens via authenticated fetch, not a bare public URL.</li>
              <li>Artifact records are filtered by the same search terms used in the UI BFF.</li>
            </ul>
          </CardContent>
        </Card>
      </section>

      <Drawer open={Boolean(selectedArtifactId)} onOpenChange={(open) => !open && setSelectedArtifactId(null)}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Artifact details</DrawerTitle>
            <DrawerDescription>
              {selectedArtifact ? selectedArtifact.name : 'No artifact selected'}
            </DrawerDescription>
          </DrawerHeader>

          {!selectedArtifact ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : (
            <div className="grid gap-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Path</p>
                  <p className="mt-1 break-all text-sm text-slate-100">{selectedArtifact.path}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Source</p>
                  <p className="mt-1 text-sm text-slate-100">{selectedArtifact.source}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Size</p>
                  <p className="mt-1 text-sm text-slate-100">{formatBytes(selectedArtifact.size_bytes)}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Modified</p>
                  <p className="mt-1 text-sm text-slate-100">{formatTimestamp(selectedArtifact.modified_at)}</p>
                </div>
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-200">Preview</p>
                {detailQuery.isLoading ? (
                  <div className="rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-sm text-slate-400">
                    Loading preview...
                  </div>
                ) : detailQuery.error ? (
                  <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                    {getErrorMessage(detailQuery.error)}
                  </div>
                ) : (
                  <ArtifactPreview kind={selectedArtifact.kind} content={selectedArtifact.preview ?? ''} />
                )}
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-200">Metadata</p>
                <pre className="max-h-52 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                  {JSON.stringify(selectedArtifact.metadata, null, 2)}
                </pre>
              </div>
            </div>
          )}

          <DrawerFooter>
            <Button variant="outline" onClick={() => setSelectedArtifactId(null)}>
              Close
            </Button>
            <Button
              onClick={() => downloadMutation.mutate()}
              disabled={downloadMutation.isPending || !selectedArtifact}
            >
              {downloadMutation.isPending ? 'Downloading' : 'Download'}
            </Button>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </main>
  );
}
