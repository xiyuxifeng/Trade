import type { ArtifactsListResponse } from '@/types/artifacts';
import { API_KEY_STORAGE_KEY, fetchJson, getApiBaseUrl } from './http';

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
  const headers = new Headers();
  headers.set('Accept', '*/*');
  if (typeof window !== 'undefined') {
    const apiKey = window.localStorage.getItem(API_KEY_STORAGE_KEY);
    if (apiKey) {
      headers.set('X-API-Key', apiKey);
    }
  }

  const response = await fetch(`${getApiBaseUrl()}/artifacts/${artifactId}/download`, {
    headers,
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'Download failed');
  }
  return response.blob();
}
