import { afterEach, describe, expect, it, vi } from 'vitest';
import { listPermissionDeniedLogs } from './security-audits';

describe('security audits api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it('calls the canonical permission denied endpoint with filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        filters: {
          actor: 'viewer',
          source: 'ui',
          path: '/api/ui/v1/job-audits',
          start_date: '2026-05-17',
          end_date: '2026-05-17',
        },
        summary: {
          total: 1,
          unique_actors: 1,
          unique_paths: 1,
          source_counts: { ui: 1 },
        },
        page: { total: 1, skip: 0, limit: 20, count: 1 },
        items: [],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');

    await listPermissionDeniedLogs({
      actor: 'viewer',
      source: 'ui',
      path: '/api/ui/v1/job-audits',
      start_date: '2026-05-17',
      end_date: '2026-05-17',
      skip: 0,
      limit: 20,
    });

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/security/permission-denied?actor=viewer&source=ui&path=%2Fapi%2Fui%2Fv1%2Fjob-audits&start_date=2026-05-17&end_date=2026-05-17&skip=0&limit=20');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});
