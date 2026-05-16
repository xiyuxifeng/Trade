import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from './http';
import { getProfile, getProfileSnapshot, importProfile, listProfiles } from './profiles';

describe('profiles api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('lists profiles through the authenticated ui api', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ count: 0, total: 0, skip: 0, limit: 20, items: [] }),
    } as Response);

    await expect(listProfiles()).resolves.toMatchObject({ items: [] });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/profiles');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('fetches a profile detail record', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        profile: {
          profile_id: 'default',
          name: 'Default Profile',
          environment: 'default',
          version: 1,
          sections: {},
          secret_refs: {},
          validation_status: 'validated',
          created_by: 'web',
          created_at: '2026-05-16T10:00:00Z',
          updated_at: '2026-05-16T10:00:00Z',
          archived_at: null,
        },
        linked_jobs: [],
        snapshots: [],
      }),
    } as Response);

    await expect(getProfile('default')).resolves.toMatchObject({
      profile: { profile_id: 'default' },
    });

    const [url] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/profiles/default');
  });

  it('posts a profile import request', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        created: true,
        profile: { profile_id: 'default' },
        snapshot: null,
      }),
    } as Response);

    await expect(
      importProfile({ profile_id: 'default', config_path: 'config/articles.yaml', created_by: 'web' }),
    ).resolves.toMatchObject({ created: true });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/profiles/import');
    expect(init?.method).toBe('POST');
    expect((init?.headers as Headers).get('Content-Type')).toBe('application/json');
    expect(init?.body).toBe(JSON.stringify({ profile_id: 'default', config_path: 'config/articles.yaml', created_by: 'web' }));
  });

  it('loads a profile snapshot detail view', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        profile: { profile_id: 'default' },
        snapshot: { snapshot_id: 'snapshot-1' },
        linked_job: null,
      }),
    } as Response);

    await expect(getProfileSnapshot('default', 'snapshot-1')).resolves.toMatchObject({
      snapshot: { snapshot_id: 'snapshot-1' },
    });

    const [url] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/profiles/default/snapshots/snapshot-1');
  });
});
