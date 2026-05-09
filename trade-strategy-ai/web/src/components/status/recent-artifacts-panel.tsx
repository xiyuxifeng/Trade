import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { cn } from '@/lib/utils';
import { useRecentArtifacts } from '@/features/artifacts/use-recent-artifacts';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '无法加载最近产物';
}

function formatBytes(bytes: number | null | undefined) {
  if (bytes == null) {
    return '未知大小';
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTimestamp(value: string | null) {
  if (!value) {
    return '未记录';
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function RecentArtifactsPanel() {
  const { data, error, isLoading, isFetching, refetch } = useRecentArtifacts();

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>最近产物</CardTitle>
            <CardDescription>展示可预览和可下载的最新输出。</CardDescription>
          </div>
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? '刷新中' : '刷新'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {getErrorMessage(error)}
          </div>
        ) : !data?.items.length ? (
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
            暂无最近产物。
          </div>
        ) : (
          data.items.map((artifact) => (
            <article
              className={cn(
                'cursor-pointer rounded-2xl border border-slate-800 bg-slate-950/60 p-4 transition-colors hover:border-sky-500/25 hover:bg-slate-900/70',
              )}
              key={artifact.artifact_id}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="font-medium text-slate-100">{artifact.name}</p>
                  <p className="text-xs text-slate-400 break-all">{artifact.path}</p>
                </div>
                <Badge variant={artifact.previewable ? 'success' : 'warning'}>
                  {artifact.kind}
                </Badge>
              </div>

              <div className="mt-3 grid gap-2 text-xs text-slate-400 md:grid-cols-2">
                <div>
                  <span className="text-slate-500">Source:</span> {artifact.source}
                </div>
                <div>
                  <span className="text-slate-500">Size:</span> {formatBytes(artifact.size_bytes)}
                </div>
                <div>
                  <span className="text-slate-500">Modified:</span> {formatTimestamp(artifact.modified_at)}
                </div>
                <div>
                  <span className="text-slate-500">Job:</span> {artifact.job_id || 'none'}
                </div>
              </div>
            </article>
          ))
        )}
      </CardContent>
    </Card>
  );
}
