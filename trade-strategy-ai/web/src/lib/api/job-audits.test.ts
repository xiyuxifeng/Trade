import { afterEach, describe, expect, it, vi } from 'vitest';
import { getJobAuditDetail, listJobAudits } from './job-audits';

describe('job audits api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it('calls the canonical job-audits endpoint with filters', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        filters: {
          actor: 'web',
          job_type: 'pipeline-run',
          operation: 'create',
          start_date: '2026-05-17',
          end_date: '2026-05-17',
          confirmed: true,
        },
        summary: {
          total: 1,
          confirmed_count: 1,
          high_risk_count: 1,
          unique_jobs: 1,
          operation_counts: { create: 1 },
        },
        page: { total: 1, skip: 0, limit: 20, count: 1 },
        items: [],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');

    await listJobAudits({
      actor: 'web',
      job_type: 'pipeline-run',
      operation: 'create',
      start_date: '2026-05-17',
      end_date: '2026-05-17',
      confirmed: true,
      skip: 0,
      limit: 20,
    });

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe('/api/ui/v1/job-audits?actor=web&job_type=pipeline-run&operation=create&start_date=2026-05-17&end_date=2026-05-17&confirmed=true&skip=0&limit=20');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('loads a job audit detail from the canonical endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        job: {
          id: 'job-1',
          job_type: 'pipeline-run',
          status: 'success',
          created_by: 'web',
          retry_count: 0,
          max_retries: 3,
          retry_backoff_seconds: 0,
          timeout_seconds: null,
          cancel_requested: false,
          cancel_requested_at: null,
          worker_id: 'worker-1',
          lock_acquired_at: null,
          heartbeat_at: null,
          scheduled_at: null,
          started_at: '2026-05-17T00:00:00+00:00',
          finished_at: '2026-05-17T00:02:00+00:00',
          created_at: '2026-05-17T00:00:00+00:00',
          updated_at: '2026-05-17T00:02:00+00:00',
          artifacts: [],
        },
        summary: {
          event_count: 2,
          confirmed_count: 1,
          high_risk_count: 1,
          has_artifacts: false,
        },
        request_context: { channel: 'ui' },
        items: [],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);

    await getJobAuditDetail('job-1');

    expect(fetchMock).toHaveBeenCalledWith('/api/ui/v1/job-audits/job-1', expect.any(Object));
  });
});
