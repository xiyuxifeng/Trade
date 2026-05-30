import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';
import { buildMarketState, buildSampleClusters, listBehaviorRules } from './persona';

describe('persona api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('posts to the versioned ui endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ clusters_path: 'data/processed/persona/clusters.sample.json' }),
    } as Response);

    await buildSampleClusters();

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/persona/sample');
    expect(init?.method).toBe('POST');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('posts the market-state build request', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ snapshot_path: 'data/processed/market-state/latest.json' }),
    } as Response);

    await buildMarketState({ benchmark_symbol: '000300.SH', as_of: '2026-05-09', from_akshare: false, cache_csv: true });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/persona/market-state/build');
    expect(init?.method).toBe('POST');
    expect((init?.headers as Headers).get('Content-Type')).toBe('application/json');
  });

  it('loads the behavior rules preview from the readonly endpoint', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        schema_version: 'v1',
        title: '交易行为标签规则',
        description: '只读规则集',
        source_path: 'config/rules/behavior_rules.yaml',
        rule_count: 2,
        enabled_rule_count: 2,
        category_count: 1,
        categories: [{ name: '追涨类', rule_count: 2, enabled_rule_count: 2 }],
        rules: [],
      }),
    } as Response);

    await listBehaviorRules();

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/persona/rules');
    expect(init?.method).toBe('GET');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
  });
});
