import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useRecentArtifacts } from '@/features/artifacts/use-recent-artifacts';

function formatBytes(bytes: number | null | undefined) {
  if (bytes == null) return '未知大小';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatTimestamp(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

export function DashboardRecentArtifactsPanel() {
  const { data, error, isLoading, isFetching, refetch } = useRecentArtifacts();

  return (
    <Card className="flex h-[min(72vh,44rem)] flex-col overflow-hidden border-slate-200 bg-white shadow-sm shadow-slate-200/40">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-slate-900">最近运行产出</CardTitle>
            <CardDescription>快速检查最近生成的输出是否可预览。</CardDescription>
          </div>
          <button
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-sky-300 hover:bg-sky-50"
            onClick={() => refetch()}
            type="button"
          >
            {isFetching ? '刷新中' : '刷新'}
          </button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 space-y-3 overflow-y-auto pr-1">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full rounded-2xl" />
            <Skeleton className="h-20 w-full rounded-2xl" />
            <Skeleton className="h-20 w-full rounded-2xl" />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error.message}
          </div>
        ) : !data?.items.length ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">暂无最近运行产出。</div>
        ) : (
          data.items.map((artifact) => (
            <article
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-300 hover:bg-sky-50/70"
              key={artifact.artifact_id}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-slate-900">{artifact.name}</p>
                  <p className="break-all text-xs text-slate-500">{artifact.path}</p>
                </div>
                <Badge variant={artifact.previewable ? 'success' : 'warning'}>{artifact.kind}</Badge>
              </div>
              <div className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                <div>来源：{artifact.source}</div>
                <div>大小：{formatBytes(artifact.size_bytes)}</div>
                <div>修改时间：{formatTimestamp(artifact.modified_at)}</div>
                <div className="md:text-right">
                  <Link className="font-medium text-sky-700 hover:underline" to="/system/runs">
                    查看运行产出
                  </Link>
                </div>
              </div>
            </article>
          ))
        )}
      </CardContent>
    </Card>
  );
}
