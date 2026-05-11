import { createBrowserRouter } from 'react-router-dom';
import { DashboardLayout } from '@/layouts/dashboard-layout';
import { ArtifactsPage } from '@/pages/artifacts';
import { BacktestsPage } from '@/pages/backtests';
import { AlertsPage } from '@/pages/alerts';
import { JobsPage } from '@/pages/jobs';
import { MarketPage } from '@/pages/market';
import { MarketStatePage } from '@/pages/market-state';
import { PersonaPage } from '@/pages/persona';
import { OpsPage } from '@/pages/ops';
import { OverviewPage } from '@/pages/overview';
import { DataHealthPage } from '@/pages/data-health';
import { ImportsPage } from '@/pages/imports';
import { ReportsPage } from '@/pages/reports';
import { SnapshotsPage } from '@/pages/snapshots';
import { SettingsPage } from '@/pages/settings';
import { SignalsPage } from '@/pages/signals';
import { KaipanPage } from '@/pages/kaipan';
import { StrategyStudioPage } from '@/pages/strategy-studio';
import { StrategiesPage } from '@/pages/strategies';
import { WorkflowsPage } from '@/pages/workflows';
import { LoginPage } from '@/pages/login';
import { UsersPage } from '@/pages/users';

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
        element: <OverviewPage />,
      },
      {
        path: 'jobs',
        element: <JobsPage />,
      },
      {
        path: 'workflows',
        element: <WorkflowsPage />,
      },
      {
        path: 'workflows/:workflowId',
        element: <WorkflowsPage />,
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
        path: 'snapshots',
        element: <SnapshotsPage />,
      },
      {
        path: 'strategies',
        element: <StrategiesPage />,
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
        path: 'reports',
        element: <ReportsPage />,
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
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
]);
