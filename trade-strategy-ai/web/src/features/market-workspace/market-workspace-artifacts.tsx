import { SectionCard, StatusBadge, LoadingState, EmptyState } from '@/components/kit';
import type { ArtifactRecord } from '@/types/artifacts';

type MarketWorkspaceArtifactsProps = {
  artifacts: ArtifactRecord[];
  loading: boolean;
  compact?: boolean;
};

function formatDate(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function MarketWorkspaceArtifacts({ artifacts, loading, compact = false }: MarketWorkspaceArtifactsProps) {
  return (
    <SectionCard
      title="最近产物"
      description="查看市场链路生成的快照、报告和导出文件。"
      action={<StatusBadge value="info" label={`${artifacts.length} 项`} />}
    >
      {loading ? (
        <LoadingState label="正在加载最近产物" description="稍后会显示市场链路生成的快照、报告和导出文件。" />
      ) : artifacts.length ? (
        <div className={compact ? 'max-h-72 space-y-2 overflow-auto pr-1' : 'space-y-3'}>
          {artifacts.map((artifact) => (
            <div key={artifact.artifact_id} className={compact ? 'rounded-2xl border border-slate-200 bg-slate-50 p-3' : 'rounded-2xl border border-slate-200 bg-slate-50 p-4'}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className={compact ? 'text-sm font-medium text-slate-900' : 'font-medium text-slate-900'}>{artifact.name}</p>
                  <p className={compact ? 'mt-1 text-xs text-slate-500' : 'mt-1 text-sm text-slate-500'}>
                    {artifact.kind} · {artifact.source} · {formatDate(artifact.modified_at)}
                  </p>
                </div>
                <StatusBadge value={artifact.exists ? 'success' : 'failed'} label={artifact.exists ? '可用' : '缺失'} />
              </div>
              <div className={compact ? 'mt-2 flex flex-wrap items-center gap-2 text-xs' : 'mt-3 flex flex-wrap items-center gap-3 text-sm'}>
                <span className="text-slate-500">Job：{artifact.job_id ?? '未关联'}</span>
                <a className="font-medium text-sky-700 hover:text-sky-800" href="/artifacts">
                  打开产物中心
                </a>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="暂无最近产物。" description="当市场链路生成产物后，这里会显示最新记录。" />
      )}
    </SectionCard>
  );
}
