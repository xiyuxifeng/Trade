import { PageHeader } from '@/components/layout/page-header';
import { DataHealthCenter } from '@/features/data-health';

export function DataHealthPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Data Health" description="Inspect dashboard reports and operational alerts." />
      <DataHealthCenter />
    </main>
  );
}
