import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY, buildApiHeaders, fetchJson } from './http';

describe('http api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('injects the stored api key into shared headers', () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');

    const headers = buildApiHeaders({ Accept: 'application/json' });
    expect(headers.get('X-API-Key')).toBe('demo-key');
    expect(headers.get('Accept')).toBe('application/json');
  });

  it('sends the stored api key with fetchJson requests', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ status: 'ok' }),
    } as Response);

    await fetchJson('/system/status');

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/system/status');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});

