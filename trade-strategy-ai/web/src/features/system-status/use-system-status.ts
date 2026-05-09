import { useQuery } from '@tanstack/react-query';
import { ApiError } from '@/lib/api/http';
import { getSystemStatus } from '@/lib/api/system';
import type { SystemStatusResponse } from '@/types/system';

export function useSystemStatus() {
  return useQuery<SystemStatusResponse, ApiError>({
    queryKey: ['system-status'],
    queryFn: getSystemStatus,
    staleTime: 15_000,
  });
}
