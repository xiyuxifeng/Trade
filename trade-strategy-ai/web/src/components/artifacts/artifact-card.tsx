import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArtifactPreview } from '@/components/artifacts/artifact-preview';
import type { JobArtifactRef } from '@/types/jobs';
import { Link } from 'react-router-dom';
import { buildArtifactPreviewPayload, formatBytes, formatTimestamp, getVisibilityLabel, stringifyJson } from './artifact-utils';

function kindVariant(kind: string) {
  if (kind === 'json' || kind === 'csv' || kind === 'markdown') {
    return 'info';
  }
  if (kind === 'report' || kind === 'snapshot') {
    return 'success';
  }
  if (kind === 'log') {
    return 'warning';
  }
  return 'default';
}

type ArtifactCardProps = {
  artifact: JobArtifactRef;
  expanded: boolean;
  onToggleExpanded: () => void;
  onDownload?: () => void;
  downloadPending?: boolean;
  downloadError?: string | null;
};

export function ArtifactCard({
  artifact,
  expanded,
  onToggleExpanded,
  onDownload,
  downloadPending = false,
  downloadError = null,
}: ArtifactCardProps) {
  const missingDownload = !artifact.safe_download_url;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="break-all font-medium text-slate-900">{artifact.title}</p>
            <Badge variant={kindVariant(artifact.kind)}>{artifact.kind}</Badge>
            <Badge variant={artifact.visibility === 'public' ? 'success' : artifact.visibility === 'private' ? 'destructive' : 'warning'}>
              {getVisibilityLabel(artifact.visibility)}
            </Badge>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            {artifact.step_id ? `step ${artifact.step_id}` : '未关联步骤'}
            {artifact.workflow_id ? ` · workflow ${artifact.workflow_id}` : ''}
          </p>
          <p className="mt-2 text-sm text-slate-600">{artifact.summary ?? '暂无摘要。'}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" onClick={onToggleExpanded}>
            {expanded ? '收起预览' : '预览'}
          </Button>
          <Button variant="outline" size="sm" onClick={onDownload} disabled={missingDownload || downloadPending}>
            {downloadPending ? '下载中' : missingDownload ? '下载不可用' : '下载'}
          </Button>
          {artifact.job_id ? (
            <Link
              className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-transparent px-3 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/40"
              to={`/system/jobs/${artifact.job_id}`}
            >
              查看来源 Job
            </Link>
          ) : null}
        </div>
      </div>

      {missingDownload ? (
        <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          该产物缺少安全下载入口，可能已丢失或尚未生成。
        </div>
      ) : null}

      {downloadError ? (
        <div
          className={`mt-3 rounded-xl border p-3 text-sm ${
            downloadError.includes('权限') || downloadError.includes('forbidden')
              ? 'border-amber-200 bg-amber-50 text-amber-800'
              : 'border-rose-200 bg-rose-50 text-rose-800'
          }`}
        >
          {downloadError}
        </div>
      ) : null}

      <div className="mt-3 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">创建时间</p>
          <p className="mt-1 break-all text-sm text-slate-900">{formatTimestamp(artifact.created_at)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">大小</p>
          <p className="mt-1 break-all text-sm text-slate-900">{formatBytes(artifact.size_bytes)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">可见性</p>
          <p className="mt-1 break-all text-sm text-slate-900">{getVisibilityLabel(artifact.visibility)}</p>
        </div>
      </div>

      {expanded ? (
        <div className="mt-4 grid gap-4">
          <div className="rounded-xl border border-slate-200 bg-white p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">JSON 预览</p>
            <p className="mt-1 text-xs text-slate-500">仅展示脱敏后的元数据和存储引用。</p>
            <div className="mt-3">
              <ArtifactPreview
                kind="json"
                content={stringifyJson(buildArtifactPreviewPayload(artifact))}
                title={`${artifact.title} JSON 预览`}
              />
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
