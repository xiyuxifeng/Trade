import { createBrowserRouter } from 'react-router-dom';
import { DashboardLayout } from '@/layouts/dashboard-layout';
import { ArtifactsPage } from '@/pages/artifacts';
import { BacktestsPage } from '@/pages/backtests';
import { JobsPage } from '@/pages/jobs';
import { MarketPage } from '@/pages/market';
import { OpsPage } from '@/pages/ops';
import { OverviewPage } from '@/pages/overview';
import { ReportsPage } from '@/pages/reports';
import { SnapshotsPage } from '@/pages/snapshots';
import { SettingsPage } from '@/pages/settings';
import { StrategiesPage } from '@/pages/strategies';
import { WorkflowsPage } from '@/pages/workflows';

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
        path: 'backtests',
        element: <BacktestsPage />,
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
