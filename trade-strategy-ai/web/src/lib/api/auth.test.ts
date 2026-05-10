import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getCurrentPrincipal } from './auth';

describe('auth api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('loads the current principal from the ui auth endpoint', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        role: 'operator',
        api_key_label: 'Local Operator',
        authenticated: true,
        source: 'api_key',
      }),
    } as Response);

    await expect(getCurrentPrincipal()).resolves.toEqual({
      role: 'operator',
      api_key_label: 'Local Operator',
      authenticated: true,
      source: 'api_key',
    });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/auth/me');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
  });
});
