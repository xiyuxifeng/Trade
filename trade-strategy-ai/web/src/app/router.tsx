import { createBrowserRouter } from 'react-router-dom';
import { DashboardLayout } from '@/layouts/dashboard-layout';
import { ArtifactsPage } from '@/pages/artifacts';
import { BacktestsPage } from '@/pages/backtests';
import { BacktestPage } from '@/pages/backtest';
import { AlertsPage } from '@/pages/alerts';
import { AlertDetailPage } from '@/pages/alerts/AlertDetailPage';
import { ArticlesPage } from '@/pages/articles';
import { AdminPage } from '@/pages/admin';
import { DashboardPage } from '@/pages/dashboard';
import { JobsPage } from '@/pages/jobs';
import { JobDetailPage } from '@/pages/jobs/JobDetailPage';
import { ProfileDetailPage } from '@/pages/profiles/ProfileDetailPage';
import { ProfileEditPage } from '@/pages/profiles/ProfileEditPage';
import { ProfileImportPage } from '@/pages/profiles/ProfileImportPage';
import { ProfileListPage } from '@/pages/profiles/ProfileListPage';
import { ProfileSnapshotPage } from '@/pages/profiles/ProfileSnapshotPage';
import { MarketPage } from '@/pages/market';
import { MarketDatasetPage } from '@/pages/market/datasets';
import { MarketStatePage } from '@/pages/market-state';
import { PersonaPage } from '@/pages/persona';
import { OpsPage } from '@/pages/ops';
import { DataHealthPage } from '@/pages/data-health';
import { ImportsPage } from '@/pages/imports';
import { ReportsPage } from '@/pages/reports';
import { SnapshotsPage } from '@/pages/snapshots';
import { RulePoolPage } from '@/pages/rule-pool';
import { SettingsPage } from '@/pages/settings';
import { SignalsPage } from '@/pages/signals';
import { KaipanPage } from '@/pages/kaipan';
import { StrategyStudioPage } from '@/pages/strategy-studio';
import { StrategiesPage } from '@/pages/strategies';
import { LegacyCompatibilityPage } from '@/pages/legacy';
import { WorkflowsPage } from '@/pages/workflows';
import { LoginPage } from '@/pages/login';
import { UsersPage } from '@/pages/users';
import { Navigate, useParams } from 'react-router-dom';

function DashboardRedirect() {
  return <Navigate to="/dashboard" replace />;
}

function WorkflowLegacyRedirect() {
  const params = useParams<{ workflowId?: string }>();
  const workflowId = params.workflowId?.trim();
  return workflowId ? <Navigate to={`/workflows/${workflowId}/run`} replace /> : <Navigate to="/workflows" replace />;
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

export const appRouter = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <DashboardLayout />,
    children: [
      {
        path: '/',
        element: <DashboardRedirect />,
      },
      {
        path: 'overview',
        element: <DashboardRedirect />,
      },
      {
        path: 'dashboard',
        element: <DashboardPage />,
      },
      {
        path: 'jobs',
        element: <JobsPage />,
      },
      {
        path: 'jobs/:jobId',
        element: <JobDetailPage />,
      },
      {
        path: 'profiles',
        element: <ProfileListPage />,
      },
      {
        path: 'profiles/import',
        element: <ProfileImportPage />,
      },
      {
        path: 'profiles/:profileId',
        element: <ProfileDetailPage />,
      },
      {
        path: 'profiles/:profileId/edit',
        element: <ProfileEditPage />,
      },
      {
        path: 'profiles/:profileId/snapshots/:snapshotId',
        element: <ProfileSnapshotPage />,
      },
      {
        path: 'workflows',
        element: <WorkflowsPage />,
      },
      {
        path: 'workflows/:workflowId',
        element: <WorkflowLegacyRedirect />,
      },
      {
        path: 'workflows/:workflowId/run',
        element: <WorkflowsPage />,
      },
      {
        path: 'articles',
        element: <ArticlesPage />,
      },
      {
        path: 'backtest',
        element: <BacktestPage />,
      },
      {
        path: 'rule-pool',
        element: <RulePoolPage />,
      },
      {
        path: 'artifacts',
        element: <ArtifactsPage />,
      },
      {
        path: 'market',
        element: <MarketPage />,
      },
      {
        path: 'market/datasets',
        element: <MarketDatasetPage />,
      },
      {
        path: 'strategies',
        element: <StrategiesPage />,
      },
      {
        path: 'snapshots',
        element: <SnapshotsPage />,
      },
      {
        path: 'strategy-studio',
        element: <StrategyStudioPage />,
      },
      {
        path: 'signals',
        element: <SignalsPage />,
      },
      {
        path: 'persona',
        element: <PersonaPage />,
      },
      {
        path: 'market-state',
        element: <MarketStatePage />,
      },
      {
        path: 'imports',
        element: <ImportsPage />,
      },
      {
        path: 'kaipan',
        element: <KaipanPage />,
      },
      {
        path: 'data-health',
        element: <DataHealthPage />,
      },
      {
        path: 'backtests',
        element: <BacktestsPage />,
      },
      {
        path: 'alerts',
        element: <AlertsPage />,
      },
      {
        path: 'alerts/:recordId',
        element: <AlertDetailPage />,
      },
      {
        path: 'reports',
        element: <ReportsPage />,
      },
      {
        path: 'admin',
        element: <AdminPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: 'users',
        element: <UsersPage />,
      },
      {
        path: 'ops',
        element: <OpsPage />,
      },
      {
        path: 'legacy/*',
        element: <LegacyCompatibilityPage />,
      },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
]);
