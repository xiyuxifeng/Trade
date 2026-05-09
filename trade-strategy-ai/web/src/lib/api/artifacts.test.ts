import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from './http';
import { downloadArtifact } from './artifacts';

describe('artifacts api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('downloads artifacts through the authenticated ui api', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      blob: async () => new Blob(['artifact']),
    } as Response);

    await downloadArtifact('artifact-1');

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/artifacts/artifact-1/download');
    expect((init?.headers as Headers).get('Accept')).toBe('*/*');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});
