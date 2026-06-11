import type { ReactNode } from 'react';
import { createBrowserRouter, Navigate, useLocation } from 'react-router-dom';
import { DashboardLayout } from '@/layouts/dashboard-layout';
import { useAuth } from '@/features/auth/auth-context';
import type { PrincipalRole } from '@/types/auth';
import { routeConfig } from './route-config';

export function RequireAuth({ children }: { children: ReactNode }) {
  const { principal, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return null;
  }

  if (!principal.authenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: {
            pathname: location.pathname,
            search: location.search,
            hash: location.hash,
          },
        }}
      />
    );
  }

  return children;
}

function RequireRole({ children, minRole }: { children: ReactNode; minRole: PrincipalRole }) {
  const { canAccess } = useAuth();

  if (!canAccess(minRole)) {
    return <Navigate to="/system/status" replace />;
  }

  return children;
}

const loginRoute = routeConfig.find((route) => route.path === '/login');
export const authenticatedRoutes = routeConfig
  .filter((route) => route.path !== '/login')
  .map(({ path, element, minRole }) => ({
    path,
    element: minRole ? <RequireRole minRole={minRole}>{element}</RequireRole> : element,
  }));

export const appRouter = createBrowserRouter([
  {
    path: '/login',
    element: loginRoute?.element,
  },
  {
    element: (
      <RequireAuth>
        <DashboardLayout />
      </RequireAuth>
    ),
    children: authenticatedRoutes,
  },
]);
