import { PageHeader } from '@/components/layout/page-header';
import { DataHealthCenter, OperationalDashboardCenter } from '@/features/data-health';

export function DataHealthPage() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="Data Ops"
        title="Operational Dashboard"
        description="Live failures, runtime, freshness, and report artifacts."
      />
      <OperationalDashboardCenter />
      <DataHealthCenter />
    </main>
  );
}
