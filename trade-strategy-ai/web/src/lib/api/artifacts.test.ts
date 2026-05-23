import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from './http';
import { downloadArtifact, listArtifactFilterOptions } from './artifacts';

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

  it('loads artifact filter options through the authenticated ui api', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        status: 'success',
        kinds: ['html'],
        sources: ['jobs'],
        job_types: ['strategy-build'],
        job_ids: ['job-1'],
      }),
    } as Response);

    await listArtifactFilterOptions();

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/artifacts/filter-options');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});
