import type { ArtifactsListResponse } from '@/types/artifacts';
import { fetchBlob, fetchJson } from './http';

type ArtifactsQuery = {
  kind?: string;
  source?: string;
  job_id?: string;
  q?: string;
  skip?: number;
  limit?: number;
};

export function listArtifacts(query: ArtifactsQuery = {}) {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      return;
    }
    params.set(key, String(value));
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<ArtifactsListResponse>(`/artifacts${suffix}`);
}

export function getArtifact(artifactId: string) {
  return fetchJson<{
    artifact_id: string;
    name: string;
    path: string;
    kind: string;
    source: string;
    exists: boolean;
    size_bytes: number | null;
    modified_at: string | null;
    previewable: boolean;
    job_id: string | null;
    metadata: Record<string, unknown>;
    preview?: string;
    download_name?: string;
  }>(`/artifacts/${artifactId}`);
}

export async function downloadArtifact(artifactId: string) {
  return fetchBlob(`/artifacts/${artifactId}/download`);
}
