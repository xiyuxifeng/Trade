import { PageHeader } from '@/components/layout/page-header';
import { PersonaCenter } from '@/features/persona';

export function PersonaPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="数据运维" title="画像中心" description="生成样本画像聚类。" />
      <PersonaCenter />
    </main>
  );
}
