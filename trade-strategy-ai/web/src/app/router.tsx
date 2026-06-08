import type { ReactNode } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { DashboardLayout } from '@/layouts/dashboard-layout';
import {
  ArticlesPage,
  ArticleListPage,
  ArticleQualityPage,
  ArticleResultsPage,
  ArticleRunPage,
} from '@/pages/articles';
import { ArtifactDetailPage, ArtifactsPage } from '@/pages/artifacts';
import { BacktestPage } from '@/pages/backtest';
import { RegimeBacktestReportPage } from '@/pages/backtest/RegimeBacktestReportPage';
import { AlertsPage } from '@/pages/alerts';
import { DashboardPage } from '@/pages/dashboard';
import { JobsPage } from '@/pages/jobs';
import { JobDetailPage } from '@/pages/jobs/JobDetailPage';
import { MarketDatasetPage } from '@/pages/market/datasets';
import { MarketPage } from '@/pages/market';
import { MarketSnapshotsPage } from '@/pages/market/snapshots';
import { MarketKaipanPage } from '@/pages/market/kaipan';
import { MarketOhlcvPage } from '@/pages/market/ohlcv';
import { PersonaPage } from '@/pages/persona';
import { ProfileDetailPage } from '@/pages/profiles/ProfileDetailPage';
import { ProfileEditPage } from '@/pages/profiles/ProfileEditPage';
import { ProfileImportPage } from '@/pages/profiles/ProfileImportPage';
import { ProfileListPage } from '@/pages/profiles/ProfileListPage';
import { ProfileSnapshotPage } from '@/pages/profiles/ProfileSnapshotPage';
import { AuditPage } from '@/pages/system/AuditPage';
import { BackupPage } from '@/pages/system/BackupPage';
import { DatabaseMigrationPage } from '@/pages/system/DatabaseMigrationPage';
import { HealthPage } from '@/pages/system/HealthPage';
import { SystemPage } from '@/pages/system';
import { UsersPage } from '@/pages/system/UsersPage';
import { AfterClosePage, PreMarketPage } from '@/pages/strategies';
import { WorkflowsPage } from '@/pages/workflows';
import { LoginPage } from '@/pages/login';
import { RulePoolDetailPage, RulePoolPage } from '@/pages/rule-pool';
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
  { path: 'workflows/pre-market', element: <Navigate to="/strategies/pre-market" replace /> },
  { path: 'workflows/pre-market/run', element: <Navigate to="/strategies/pre-market" replace /> },
  { path: 'workflows/after-close', element: <Navigate to="/strategies/after-close" replace /> },
  { path: 'workflows/after-close/run', element: <Navigate to="/strategies/after-close" replace /> },
  { path: 'workflows/:workflowId/run', element: <WorkflowsPage /> },
  { path: 'articles', element: <ArticlesPage /> },
  { path: 'articles/run', element: <ArticleRunPage /> },
  { path: 'articles/list', element: <ArticleListPage /> },
  { path: 'articles/quality', element: <ArticleQualityPage /> },
  { path: 'articles/results', element: <ArticleResultsPage /> },
  { path: 'alerts', element: <AlertsPage /> },
  { path: 'backtest', element: <BacktestPage /> },
  { path: 'backtest/regime', element: <RegimeBacktestReportPage /> },
  { path: 'rule-pool', element: <RulePoolPage /> },
  { path: 'rule-pool/:ruleId', element: <RulePoolDetailPage /> },
  { path: 'artifacts', element: <ArtifactsPage /> },
  { path: 'artifacts/:artifactId', element: <ArtifactDetailPage /> },
  { path: 'market', element: <MarketPage /> },
  { path: 'market/snapshots', element: <MarketSnapshotsPage /> },
  { path: 'market/datasets', element: <MarketDatasetPage /> },
  { path: 'market/kaipan', element: <MarketKaipanPage /> },
  { path: 'market/ohlcv', element: <MarketOhlcvPage /> },
  { path: 'strategies', element: <Navigate to="/dashboard" replace /> },
  { path: 'persona', element: <PersonaPage /> },
  { path: 'strategies/pre-market', element: <PreMarketPage /> },
  { path: 'strategies/after-close', element: <AfterClosePage /> },
  { path: 'system', element: <SystemPage /> },
  { path: 'system/audit', element: <AuditPage /> },
  { path: 'system/users', element: <UsersPage /> },
  { path: 'system/health', element: <HealthPage /> },
  { path: 'system/db-migrate', element: <DatabaseMigrationPage /> },
  { path: 'system/backup', element: <BackupPage /> },
  { path: 'admin', element: <Navigate to="/system" replace /> },
  { path: 'admin/audit', element: <Navigate to="/system/audit" replace /> },
  { path: 'system/restore', element: <Navigate to="/system/backup" replace /> },
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
