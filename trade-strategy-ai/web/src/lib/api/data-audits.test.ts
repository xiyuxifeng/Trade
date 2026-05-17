import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from './http';
import { listDataAudits } from './data-audits';

describe('Data audits API client contract', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('uses the data audits endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        filters: { event_type: null, actor: null, source: null, entity_type: 'backup', start_date: null, end_date: null },
        summary: { total: 0, event_type_counts: {}, entity_type_counts: {}, source_counts: {} },
        page: { total: 0, skip: 0, limit: 10, count: 0 },
        items: [],
      }),
    } as Response);

    await listDataAudits({ entity_type: 'backup', limit: 10 });

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/data-audits?entity_type=backup&limit=10');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});

