import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getCurrentPrincipal } from '@/lib/api/auth';
import type { CurrentPrincipal, PrincipalRole } from '@/types/auth';

type AuthContextValue = {
  principal: CurrentPrincipal;
  isLoading: boolean;
  isFetching: boolean;
  canAccess: (minRole: PrincipalRole) => boolean;
};

const ROLE_ORDER: Record<PrincipalRole, number> = {
  anonymous: 0,
  viewer: 1,
  operator: 2,
  admin: 3,
};

const anonymousPrincipal: CurrentPrincipal = {
  role: 'anonymous',
  api_key_label: null,
  authenticated: false,
  source: 'anonymous',
};

const AuthContext = createContext<AuthContextValue | null>(null);

function roleRank(role: PrincipalRole) {
  return ROLE_ORDER[role] ?? 0;
}

export function canAccessRole(role: PrincipalRole, minRole: PrincipalRole) {
  return roleRank(role) >= roleRank(minRole);
}

export function AuthProvider({
  children,
  initialPrincipal,
}: {
  children: ReactNode;
  initialPrincipal?: CurrentPrincipal | null;
}) {
  const principalQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getCurrentPrincipal,
    retry: false,
    staleTime: 60_000,
    enabled: initialPrincipal == null,
    initialData: initialPrincipal ?? undefined,
  });

  const principal = principalQuery.data ?? anonymousPrincipal;

  const value = useMemo<AuthContextValue>(
    () => ({
      principal,
      isLoading: principalQuery.isLoading,
      isFetching: principalQuery.isFetching,
      canAccess: (minRole: PrincipalRole) => canAccessRole(principal.role, minRole),
    }),
    [principal, principalQuery.isFetching, principalQuery.isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
