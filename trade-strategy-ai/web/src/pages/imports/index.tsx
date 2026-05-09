import { PageHeader } from '@/components/layout/page-header';
import { ImportCenter } from '@/features/imports';

export function ImportsPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Imports" description="Upload trade logs and migrate crawl state with audit-friendly previews." />
      <ImportCenter />
    </main>
  );
}
