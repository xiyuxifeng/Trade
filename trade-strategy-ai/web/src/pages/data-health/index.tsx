import { PageHeader } from '@/components/layout/page-header';
import { DataHealthCenter, OperationalDashboardCenter } from '@/features/data-health';

export function DataHealthPage() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="数据运维"
        title="运维仪表盘"
        description="实时故障、运行时间、数据新鲜度和报告产物。"
      />
      <OperationalDashboardCenter />
      <DataHealthCenter />
    </main>
  );
}
