import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';
import { listSignals } from './signals';

describe('signals api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('uses the versioned signals endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        config_path: 'config/app.yaml',
        base_dir: '/tmp/project',
        count: 1,
        signals: [],
      }),
    } as Response);

    await listSignals({ symbol: '000001.SZ', limit: 2 });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/signals?symbol=000001.SZ&limit=2');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});
