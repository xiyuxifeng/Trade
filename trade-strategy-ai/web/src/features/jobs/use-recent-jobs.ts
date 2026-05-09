import { useQuery } from '@tanstack/react-query';
import { ApiError } from '@/lib/api/http';
import { listJobs } from '@/lib/api/jobs';
import type { JobsListResponse } from '@/types/jobs';

export function useRecentJobs() {
  return useQuery<JobsListResponse, ApiError>({
    queryKey: ['recent-jobs'],
    queryFn: () => listJobs({ limit: 5 }),
    staleTime: 15_000,
  });
}
