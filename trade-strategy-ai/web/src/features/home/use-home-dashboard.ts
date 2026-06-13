import { useQuery } from '@tanstack/react-query';

import { getSystemDashboard } from '@/lib/api/system';

export function useHomeDashboard() {
  return useQuery({
    queryKey: ['system-dashboard'],
    queryFn: getSystemDashboard,
    staleTime: 30_000,
  });
}
