import { PageHeader } from '@/components/layout/page-header';
import { DashboardAlertStrip } from '@/components/dashboard/dashboard-alert-strip';
import { DashboardQuickLinks, DashboardStatusSummary } from '@/components/dashboard/dashboard-status-summary';
import { DashboardRecentArtifactsPanel } from '@/components/dashboard/dashboard-recent-artifacts';
import { DashboardRecentJobsPanel } from '@/components/dashboard/dashboard-recent-jobs';

export function OverviewRoute() {
  return (
    <main className="page-stack">
      {/* <PageHeader
        kicker="概览"
        title="运维总览"
        description="系统状态优先的正式工作台入口。"
      /> */}

      <section className="space-y-4">
        <DashboardStatusSummary />
        <DashboardAlertStrip />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <DashboardRecentJobsPanel />
        <DashboardRecentArtifactsPanel />
      </section>

      <DashboardQuickLinks />
    </main>
  );
}
