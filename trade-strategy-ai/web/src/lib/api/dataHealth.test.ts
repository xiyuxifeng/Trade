import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';
import { buildDashboardReport } from './dataHealth';

describe('data health api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('uses the versioned dashboard endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        config_path: 'config/app.yaml',
        report: { title: 'Daily Health' },
        html_path: '/tmp/project/data/processed/dashboard/dashboard.html',
        critical_alerts: 0,
        exit_code: 0,
      }),
    } as Response);

    await buildDashboardReport();

    const [url, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/data-health/dashboard');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});
