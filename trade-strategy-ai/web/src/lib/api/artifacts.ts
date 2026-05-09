import type { ArtifactsListResponse } from '@/types/artifacts';
import { fetchJson } from './http';

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
