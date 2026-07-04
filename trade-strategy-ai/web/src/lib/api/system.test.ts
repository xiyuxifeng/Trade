import { describe, expect, it, vi } from 'vitest';
import { getSystemDashboard, listSystemRunTraces } from './system';
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

describe('listSystemRunTraces', () => {
  it('calls the system runs endpoint with filters and cursor pagination', async () => {
    vi.mocked(fetchJson).mockResolvedValueOnce({
      summary: {
        overall_status: 'ready',
        headline: '最近运行状态正常。',
        reason: '没有待处理项。',
        impact: '不阻断用户。',
        counts: { total: 0, needs_attention: 0, ready: 0, partial: 0, failed: 0 },
        next_action: { label: '查看运行与告警', target_path: '/system/runs' },
      },
      needs_attention: [],
      history: { groups: [], page: { limit: 5, has_more: false, next_cursor: null, total_filtered: 0 } },
      filters: { applied: { status: 'all', business_type: 'all', date_from: null, date_to: null } },
    });

    await listSystemRunTraces({
      limit: 5,
      cursor: 'cursor-1',
      status: 'needs_attention',
      businessType: 'data',
      dateFrom: '2026-07-04',
      dateTo: '2026-07-05',
    });

    expect(fetchJson).toHaveBeenCalledWith(
      '/system/runs?limit=5&status=needs_attention&business_type=data&cursor=cursor-1&date_from=2026-07-04&date_to=2026-07-05',
    );
  });
});
