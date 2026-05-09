import { PageHeader } from '@/components/layout/page-header';
import { PersonaCenter } from '@/features/persona';

export function PersonaPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Persona" description="Generate sample persona clusters." />
      <PersonaCenter />
    </main>
  );
}
