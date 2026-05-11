import { describe, expect, it, vi } from 'vitest';
import { getSystemDashboard } from './system';
import { fetchJson } from './http';

vi.mock('./http', () => ({
  fetchJson: vi.fn(),
}));

describe('getSystemDashboard', () => {
  it('calls the dashboard endpoint', async () => {
    vi.mocked(fetchJson).mockResolvedValueOnce({
      status: 'ok',
      generated_at: '2026-05-11T09:00:00Z',
      health: { database: { status: 'ok' } },
      failed_jobs: [],
      duration_summary: { average_seconds: null, p95_seconds: null, recent_jobs: [] },
      freshness: { sources: [] },
      alerts: { critical: 0, warning: 0, latest: [] },
      traces: [],
    });

    await getSystemDashboard();

    expect(fetchJson).toHaveBeenCalledWith('/system/dashboard');
  });
});
