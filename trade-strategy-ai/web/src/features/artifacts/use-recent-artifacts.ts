import { useQuery } from '@tanstack/react-query';
import { ApiError } from '@/lib/api/http';
import { listArtifacts } from '@/lib/api/artifacts';
import type { ArtifactsListResponse } from '@/types/artifacts';

export function useRecentArtifacts() {
  return useQuery<ArtifactsListResponse, ApiError>({
    queryKey: ['recent-artifacts'],
    queryFn: () => listArtifacts({ limit: 5 }),
    staleTime: 15_000,
  });
}
