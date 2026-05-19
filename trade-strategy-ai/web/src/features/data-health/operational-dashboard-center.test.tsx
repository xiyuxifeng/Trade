import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { OperationalDashboardCenter } from './operational-dashboard-center';
import { renderWithRouter } from '@/test/test-utils';
import { getSystemDashboard, getSystemStatus } from '@/lib/api/system';
import type { SystemStatusResponse } from '@/types/system';

vi.mock('@/lib/api/system', () => ({
  getSystemDashboard: vi.fn(),
  getSystemStatus: vi.fn(),
}));

const mockedGetSystemDashboard = vi.mocked(getSystemDashboard);
const mockedGetSystemStatus = vi.mocked(getSystemStatus);

describe('OperationalDashboardCenter', () => {
  it('renders operational summary data', async () => {
    mockedGetSystemDashboard.mockResolvedValue({
      status: 'partial',
      generated_at: '2026-05-11T09:10:00Z',
      health: { overall: 'healthy', issues: [], database: { name: 'database', status: 'ok', latency_ms: 3.2 } },
      worker: { status: 'ok', heartbeat_at: '2026-05-11T09:05:30Z', heartbeat_age_minutes: 4.5, current_job_id: 'job-running-1' },
      failed_jobs: [
        {
          id: 'job-failed-1',
          job_type: 'run_after_close',
          status: 'failed',
          duration_seconds: 180,
          error_message: 'boom',
        },
      ],
      duration_summary: { average_seconds: 240, p95_seconds: 300, recent_jobs: [] },
      freshness: {
        sources: [
          { source: 'market_data', entity_type: 'market', freshness_hours: 24, is_stale: true },
        ],
      },
      alerts: {
        critical: 1,
        warning: 0,
        latest: [{ level: 'critical', title: 'stale market data', message: 'market data is stale' }],
      },
      traces: [
        {
          job_id: 'job-failed-1',
          request_context: { path: '/api/ui/v1/jobs', method: 'POST', client_host: '127.0.0.1' },
        },
      ],
    } as never);
    const systemStatusResponse: SystemStatusResponse = {
      status: 'ok',
      run_mode: 'production',
      database: { name: 'database', status: 'ok', latency_ms: 3.2, error: null },
      config_path: 'config/app.yaml',
      project_root: '/repo',
      directories: {},
      warnings: [],
    };
    mockedGetSystemStatus.mockResolvedValue(systemStatusResponse);

    renderWithRouter([{ path: '/data-health', element: <OperationalDashboardCenter /> }], ['/data-health']);

    expect(await screen.findByText('Health Check Dashboard')).toBeInTheDocument();
    expect((await screen.findAllByText('job-failed-1')).length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText('stale market data')).toBeInTheDocument();
    expect(await screen.findByText('market_data')).toBeInTheDocument();
    expect(await screen.findByText('client: 127.0.0.1')).toBeInTheDocument();
  });
});
