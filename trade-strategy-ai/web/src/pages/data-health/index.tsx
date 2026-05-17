import { PageHeader } from '@/components/layout/page-header';
import { DataHealthCenter, OperationalDashboardCenter } from '@/features/data-health';

export function DataHealthPage() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="数据运维"
        title="Health Check Dashboard"
        description="系统状态、健康组件、数据新鲜度和报告产物的正式查看入口。"
      />
      <OperationalDashboardCenter />
      <DataHealthCenter />
    </main>
  );
}
