import { useState } from 'react';
import { ApiError } from '@/lib/api/http';
import { downloadArtifact } from '@/lib/api/artifacts';
import type { JobArtifactRef } from '@/types/jobs';
import { ArtifactList } from './artifact-list';

type ArtifactPanelProps = {
  artifacts: JobArtifactRef[];
};

export function ArtifactPanel({ artifacts }: ArtifactPanelProps) {
  const [expandedIds, setExpandedIds] = useState<string[]>([]);
  const [downloadingArtifactId, setDownloadingArtifactId] = useState<string | null>(null);
  const [downloadErrors, setDownloadErrors] = useState<Record<string, string>>({});

  if (!artifacts.length) {
    return <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">该任务未产生任何产物。</div>;
  }

  async function handleDownload(artifact: JobArtifactRef) {
    if (!artifact.safe_download_url) {
      setDownloadErrors((current) => ({
        ...current,
        [artifact.artifact_id]: '该产物缺少安全下载入口，可能已丢失或尚未生成。',
      }));
      return;
    }

    setDownloadingArtifactId(artifact.artifact_id);
    setDownloadErrors((current) => {
      const next = { ...current };
      delete next[artifact.artifact_id];
      return next;
    });

    try {
      const blob = await downloadArtifact(artifact.artifact_id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = artifact.title || artifact.artifact_id;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      const message =
        error instanceof ApiError && (error.status === 403 || error.status === 401)
          ? '没有权限下载该产物。'
          : error instanceof ApiError && error.status === 404
            ? '产物缺失或已被清理，无法下载。'
            : error instanceof Error
              ? error.message
              : '下载产物失败。';
      setDownloadErrors((current) => ({
        ...current,
        [artifact.artifact_id]: message,
      }));
    } finally {
      setDownloadingArtifactId((current) => (current === artifact.artifact_id ? null : current));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span>共 {artifacts.length} 个产物</span>
        <span>按步骤分组展示，下载使用后端安全入口</span>
      </div>

      <ArtifactList
        artifacts={artifacts}
        expandedIds={expandedIds}
        downloadingArtifactId={downloadingArtifactId}
        downloadErrors={downloadErrors}
        onDownloadArtifact={handleDownload}
        onToggleExpanded={(artifactId) =>
          setExpandedIds((current) =>
            current.includes(artifactId) ? current.filter((id) => id !== artifactId) : [...current, artifactId],
          )
        }
      />
    </div>
  );
}
