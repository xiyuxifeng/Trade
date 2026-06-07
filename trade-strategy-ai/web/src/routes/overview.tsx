import { PageHeader } from '@/components/layout/page-header';
import { DashboardQuickLinks, DashboardStatusSummary } from '@/components/dashboard/dashboard-status-summary';
import { DashboardRecentArtifactsPanel } from '@/components/dashboard/dashboard-recent-artifacts';
import { DashboardRecentJobsPanel } from '@/components/dashboard/dashboard-recent-jobs';

export function OverviewRoute() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="概览"
        title="从文章到复盘的主工作台"
        description="先进入主流程，再查看任务、市场和配置管理。"
      />

      <DashboardQuickLinks />

      <section className="space-y-4">
        <DashboardStatusSummary />
      </section>

      <section className="grid gap-6 xl:grid-cols-2">
        <DashboardRecentJobsPanel />
        <DashboardRecentArtifactsPanel />
      </section>
    </main>
  );
}
