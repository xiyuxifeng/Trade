import { useMemo } from 'react';
import type { JobArtifactRef } from '@/types/jobs';
import { ArtifactCard } from './artifact-card';

type ArtifactListProps = {
  artifacts: JobArtifactRef[];
  expandedIds: string[];
  onToggleExpanded: (artifactId: string) => void;
  onDownloadArtifact: (artifact: JobArtifactRef) => void;
  downloadingArtifactId: string | null;
  downloadErrors: Record<string, string>;
};

type ArtifactGroup = {
  key: string;
  title: string;
  items: JobArtifactRef[];
};

function groupArtifacts(artifacts: JobArtifactRef[]): ArtifactGroup[] {
  const groups = new Map<string, ArtifactGroup>();
  const orderedGroups: ArtifactGroup[] = [];

  for (const artifact of artifacts) {
    const key = artifact.step_id?.trim() || '__ungrouped__';
    let group = groups.get(key);
    if (!group) {
      group = {
        key,
        title: artifact.step_id?.trim() ? `步骤 ${artifact.step_id.trim()}` : '未关联步骤',
        items: [],
      };
      groups.set(key, group);
      orderedGroups.push(group);
    }
    group.items.push(artifact);
  }

  return orderedGroups;
}

export function ArtifactList({
  artifacts,
  expandedIds,
  onToggleExpanded,
  onDownloadArtifact,
  downloadingArtifactId,
  downloadErrors,
}: ArtifactListProps) {
  const groups = useMemo(() => groupArtifacts(artifacts), [artifacts]);

  return (
    <div className="space-y-4">
      {groups.map((group) => (
        <section className="space-y-3" key={group.key}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-medium text-slate-100">{group.title}</p>
            <p className="text-xs text-slate-500">{group.items.length} 个产物</p>
          </div>
          <div className="space-y-3">
            {group.items.map((artifact) => {
              const expanded = expandedIds.includes(artifact.artifact_id);
              return (
                <ArtifactCard
                  artifact={artifact}
                  expanded={expanded}
                  key={artifact.artifact_id}
                  onDownload={() => onDownloadArtifact(artifact)}
                  downloadPending={downloadingArtifactId === artifact.artifact_id}
                  downloadError={downloadErrors[artifact.artifact_id] ?? null}
                  onToggleExpanded={() => onToggleExpanded(artifact.artifact_id)}
                />
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
