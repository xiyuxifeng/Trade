import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ArtifactRecord } from '@/types/artifacts';

type MarketWorkspaceArtifactsProps = {
  artifacts: ArtifactRecord[];
  loading: boolean;
};

function formatDate(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function MarketWorkspaceArtifacts({ artifacts, loading }: MarketWorkspaceArtifactsProps) {
  return (
    <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="text-slate-900">最近产物</CardTitle>
          <CardDescription className="text-slate-500">查看市场链路生成的快照、报告和导出文件。</CardDescription>
        </div>
        <Badge variant="info">{artifacts.length} 项</Badge>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            <div className="h-12 animate-pulse rounded-2xl bg-slate-100" />
            <div className="h-12 animate-pulse rounded-2xl bg-slate-100" />
          </div>
        ) : artifacts.length ? (
          <div className="space-y-3">
            {artifacts.map((artifact) => (
              <div key={artifact.artifact_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">{artifact.name}</p>
                    <p className="mt-1 text-sm text-slate-500">
                      {artifact.kind} · {artifact.source} · {formatDate(artifact.modified_at)}
                    </p>
                  </div>
                  <Badge variant={artifact.exists ? 'success' : 'destructive'}>{artifact.exists ? '可用' : '缺失'}</Badge>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
                  <span className="text-slate-500">Job：{artifact.job_id ?? '未关联'}</span>
                  <a className="font-medium text-sky-700 hover:text-sky-800" href="/artifacts">
                    打开产物中心
                  </a>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
            暂无最近产物。
          </p>
        )}
      </CardContent>
    </Card>
  );
}
