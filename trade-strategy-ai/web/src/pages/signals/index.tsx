import { PageHeader } from '@/components/layout/page-header';
import { SignalsCenter } from '@/features/signals';

export function SignalsPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Signals" description="Browse and filter strategy signals." />
      <SignalsCenter />
    </main>
  );
}
