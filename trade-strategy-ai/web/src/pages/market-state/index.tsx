import { PageHeader } from '@/components/layout/page-header';
import { MarketStateCenter } from '@/features/market-state';

export function MarketStatePage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Market State" description="Build and inspect the current market state snapshot." />
      <MarketStateCenter />
    </main>
  );
}
