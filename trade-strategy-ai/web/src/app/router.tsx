import type { ReactNode } from 'react';
import { createBrowserRouter, Navigate, useLocation } from 'react-router-dom';
import { DashboardLayout } from '@/layouts/dashboard-layout';
import { useAuth } from '@/features/auth/auth-context';
import { BusinessPageShell } from '@/components/layout/business-page-shell';
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
    return (
      <BusinessPageShell
        title="当前账号无权访问"
        purpose="保护仅限管理员使用的系统管理能力。"
        inputDescription="需要管理员账号才能查看此页面。"
        processingDescription="系统已完成当前账号的权限检查。"
        outputDescription="此页面仅向管理员开放。"
        availability="permission_denied"
        stateDescription="此页面仅向管理员开放。"
        impact="当前账号无法查看页面内容，也不能执行其中的高风险操作。"
        recoveryAction={{ label: '返回系统状态', to: '/system/status' }}
      />
    );
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
