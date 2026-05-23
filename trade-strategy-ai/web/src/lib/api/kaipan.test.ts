import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';
import { kaipanFetch, kaipanNormalize, kaipanRun, kaipanStatus, kaipanStop } from './kaipan';

describe('kaipan api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('uses the versioned status endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ latest_slot: '2026-05-09_17-30', scheduler_started: true }),
    } as Response);

    await kaipanStatus();

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/kaipan/status');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('posts the fetch request', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ slot_results: {} }),
    } as Response);

    await kaipanFetch({ slot: 'all' });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/kaipan/fetch?slot=all');
    expect(init?.method).toBe('POST');
  });

  it('posts normalize and run requests', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [] }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ started: false }),
      } as Response);

    await kaipanNormalize({ slot: 'all' });
    await kaipanRun({ start_scheduler: false });

    const [normalizeUrl, normalizeInit] = vi.mocked(fetch).mock.calls[0] ?? [];
    const [runUrl, runInit] = vi.mocked(fetch).mock.calls[1] ?? [];
    expect(normalizeUrl).toBe('/api/ui/v1/kaipan/normalize');
    expect(normalizeInit?.method).toBe('POST');
    expect(runUrl).toBe('/api/ui/v1/kaipan/run');
    expect(runInit?.method).toBe('POST');
  });

  it('posts stop request', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ started: false }),
    } as Response);

    await kaipanStop();

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/kaipan/stop');
    expect(init?.method).toBe('POST');
  });
});
