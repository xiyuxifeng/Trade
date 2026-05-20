import type { ReactNode } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { DashboardLayout } from '@/layouts/dashboard-layout';
import { ArticlesPage } from '@/pages/articles';
import { ArtifactsPage } from '@/pages/artifacts';
import { BacktestPage } from '@/pages/backtest';
import { RegimeBacktestReportPage } from '@/pages/backtest/RegimeBacktestReportPage';
import { DashboardPage } from '@/pages/dashboard';
import { JobsPage } from '@/pages/jobs';
import { JobDetailPage } from '@/pages/jobs/JobDetailPage';
import { MarketDatasetPage } from '@/pages/market/datasets';
import { MarketPage } from '@/pages/market';
import { AdminPage } from '@/pages/admin';
import { AdminAuditPage } from '@/pages/admin/AuditPage';
import { ProfileDetailPage } from '@/pages/profiles/ProfileDetailPage';
import { ProfileEditPage } from '@/pages/profiles/ProfileEditPage';
import { ProfileImportPage } from '@/pages/profiles/ProfileImportPage';
import { ProfileListPage } from '@/pages/profiles/ProfileListPage';
import { ProfileSnapshotPage } from '@/pages/profiles/ProfileSnapshotPage';
import { SystemPage } from '@/pages/system';
import { RegimeRuleSelectionPage } from '@/pages/strategies/RegimeRuleSelectionPage';
import { StrategiesPage } from '@/pages/strategies';
import { WorkflowsPage } from '@/pages/workflows';
import { LoginPage } from '@/pages/login';
import { RulePoolPage } from '@/pages/rule-pool';
import { useAuth } from '@/features/auth/auth-context';

function RootRedirect() {
  return <Navigate to="/dashboard" replace />;
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { principal, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!principal.authenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function NotFoundPage() {
  return (
    <main className="page-stack">
      <section className="page-card">
        <p className="page-kicker">404</p>
        <h1>Page not found</h1>
        <p>The requested route is not available yet.</p>
      </section>
    </main>
  );
}

const dashboardLayoutRoutes = [
  { path: 'dashboard', element: <DashboardPage /> },
  { path: 'jobs', element: <JobsPage /> },
  { path: 'jobs/:jobId', element: <JobDetailPage /> },
  { path: 'profiles', element: <ProfileListPage /> },
  { path: 'profiles/import', element: <ProfileImportPage /> },
  { path: 'profiles/:profileId', element: <ProfileDetailPage /> },
  { path: 'profiles/:profileId/edit', element: <ProfileEditPage /> },
  { path: 'profiles/:profileId/snapshots/:snapshotId', element: <ProfileSnapshotPage /> },
  { path: 'workflows', element: <WorkflowsPage /> },
  { path: 'workflows/:workflowId/run', element: <WorkflowsPage /> },
  { path: 'articles', element: <ArticlesPage /> },
  { path: 'backtest', element: <BacktestPage /> },
  { path: 'backtest/regime', element: <RegimeBacktestReportPage /> },
  { path: 'rule-pool', element: <RulePoolPage /> },
  { path: 'artifacts', element: <ArtifactsPage /> },
  { path: 'market', element: <MarketPage /> },
  { path: 'market/datasets', element: <MarketDatasetPage /> },
  { path: 'strategies', element: <StrategiesPage /> },
  { path: 'strategies/regime-selection', element: <RegimeRuleSelectionPage /> },
  { path: 'system', element: <SystemPage /> },
  { path: 'admin', element: <AdminPage /> },
  { path: 'admin/audit', element: <AdminAuditPage /> },
  { path: 'settings', element: <Navigate to="/profiles" replace /> },
] as const;

export const appRouter = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: (
      <RequireAuth>
        <DashboardLayout />
      </RequireAuth>
    ),
    children: [
      { path: '/', element: <RootRedirect /> },
      ...dashboardLayoutRoutes,
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
