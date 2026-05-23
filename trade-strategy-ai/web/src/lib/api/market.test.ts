import { describe, expect, it, vi } from 'vitest';
import {
  getMarketRegime,
  getMarketRegimeFeature,
  getOhlcvSchedulerStatus,
  listBenchmarkOptions,
  listMarketRegimeFeatures,
  listMarketRegimes,
  runOhlcvScheduler,
  stopOhlcvScheduler,
} from '@/lib/api/market';

describe('market api client', () => {
  it('builds regime feature list and detail urls', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response('{}', {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );

    await listMarketRegimeFeatures({
      tradeDate: '2026-05-16',
      market: 'CN',
      featureVersion: 'market-regime-features-v1',
      limit: 10,
      offset: 0,
    });
    await listBenchmarkOptions(20);
    await getOhlcvSchedulerStatus('default');
    await runOhlcvScheduler('default');
    await stopOhlcvScheduler('default');
    await listMarketRegimes({
      tradeDate: '2026-05-16',
      market: 'CN',
      regimeVersion: 'market-regime-v1',
      limit: 10,
      offset: 0,
    });
    await getMarketRegimeFeature('snap-001', 'market-regime-features-v1');
    await getMarketRegime('snap-001', 'market-regime-v1');

    const calls = vi.mocked(fetch).mock.calls.map(([url]) => String(url));
    expect(calls).toContain(
      '/api/ui/v1/market/regime-features?trade_date=2026-05-16&market=CN&feature_version=market-regime-features-v1&limit=10&offset=0',
    );
    expect(calls).toContain('/api/ui/v1/market/benchmark-options?limit=20');
    expect(calls).toContain('/api/ui/v1/market/ohlcv/status?profile_id=default');
    expect(calls).toContain('/api/ui/v1/market/ohlcv/run?profile_id=default');
    expect(calls).toContain('/api/ui/v1/market/ohlcv/stop?profile_id=default');
    expect(calls).toContain(
      '/api/ui/v1/market/regimes?trade_date=2026-05-16&market=CN&regime_version=market-regime-v1&limit=10&offset=0',
    );
    expect(calls).toContain(
      '/api/ui/v1/market/snapshots/snap-001/regime-features?feature_version=market-regime-features-v1',
    );
    expect(calls).toContain('/api/ui/v1/market/snapshots/snap-001/regime?regime_version=market-regime-v1');
  });
});
