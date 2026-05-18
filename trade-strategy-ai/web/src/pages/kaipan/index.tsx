import { PageHeader } from '@/components/layout/page-header';
import { KaipanCenter } from '@/features/kaipan';

export function KaipanPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Kaipan" description="Trigger fetch, normalize, status, and run flows, including the 10.5 ingestion preset." />
      <KaipanCenter />
    </main>
  );
}
