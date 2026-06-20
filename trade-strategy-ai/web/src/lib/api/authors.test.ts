import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';
import { createAuthorMethodProfileDraft, listAuthorProfiles } from './authors';

describe('authors api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('loads formal author profile versions from the ui endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ state: 'empty', items: [], count: 0 }),
    } as Response);

    await listAuthorProfiles();

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/authors/profiles');
    expect(init?.method).toBe('GET');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('creates author method profile drafts from structured article results', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ author_profile_version_id: 'apv-1' }),
    } as Response);

    await createAuthorMethodProfileDraft({
      author_id: 'author-1',
      article_structure_ids: ['structure-1', 'structure-2'],
      evidence_from: '2026-01-01',
      evidence_to: '2026-01-10',
      effective_from: '2026-01-11',
      reason: '生成草稿',
    });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/authors/method-profiles/drafts');
    expect(init?.method).toBe('POST');
  });
});
