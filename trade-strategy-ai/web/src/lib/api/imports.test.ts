import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';
import { importTradeLogs, migrateCrawlState } from './imports';

describe('imports api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('posts to the versioned imports endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ rows_seen: 0, dry_run: true }),
    } as Response);

    const file = new File(['date,symbol,qty\n2026-05-09,000001.SZ,10\n'], 'sample.csv', { type: 'text/csv' });
    await importTradeLogs({ file, dryRun: true });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/imports/trade-logs');
    expect(init?.method).toBe('POST');
    expect(init?.body).toBeInstanceOf(FormData);
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('posts the crawl-state migration request', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ migrated: true }),
    } as Response);

    await migrateCrawlState({});

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/imports/crawl-state/migrate');
    expect(init?.method).toBe('POST');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('Content-Type')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});
