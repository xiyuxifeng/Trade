import { describe, expect, it, vi } from 'vitest';
import { listMarketSnapshots, listMarketDatasets, getMarketSnapshotQuality } from '@/lib/api/market';

describe('market workspace api contract', () => {
  it('builds the market snapshot and dataset urls', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response('{}', {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    ));

    await listMarketSnapshots({ tradeDate: '2026-05-16', market: 'cn', limit: 10, offset: 0 });
    await listMarketDatasets({ tradeDate: '2026-05-16', market: 'cn', limit: 10, offset: 0 });
    await getMarketSnapshotQuality('snapshot-001');

    const calls = vi.mocked(fetch).mock.calls.map(([url]) => String(url));
    expect(calls).toContain('/api/ui/v1/market/snapshots?trade_date=2026-05-16&market=cn&limit=10&offset=0');
    expect(calls).toContain('/api/ui/v1/market/datasets?trade_date=2026-05-16&market=cn&limit=10&offset=0');
    expect(calls).toContain('/api/ui/v1/market/snapshots/snapshot-001/quality');
  });
});
