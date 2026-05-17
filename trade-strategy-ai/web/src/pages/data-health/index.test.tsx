import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { DataHealthPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { buildDashboardReport } from '@/lib/api/dataHealth';
import { getSystemDashboard, getSystemStatus } from '@/lib/api/system';

vi.mock('@/lib/api/dataHealth', () => ({
  buildDashboardReport: vi.fn(),
}));

vi.mock('@/lib/api/system', () => ({
  getSystemDashboard: vi.fn(),
  getSystemStatus: vi.fn(),
}));

const mockedBuildDashboardReport = vi.mocked(buildDashboardReport);
const mockedGetSystemDashboard = vi.mocked(getSystemDashboard);
const mockedGetSystemStatus = vi.mocked(getSystemStatus);

describe('DataHealthPage', () => {
  it('renders the health dashboard and report panel', async () => {
    mockedGetSystemStatus.mockResolvedValue({
      status: 'ok',
      config_path: 'config/app.yaml',
      project_root: '/project',
      run_mode: 'web',
      database: { name: 'database', status: 'ok', latency_ms: 3.2 },
      directories: { data: { path: '/project/data', exists: true }, logs: { path: '/project/logs', exists: true } },
      warnings: [],
    });
    mockedGetSystemDashboard.mockResolvedValue({
      status: 'partial',
      generated_at: '2026-05-11T09:10:00Z',
      config_path: 'config/app.yaml',
      health: { overall: 'healthy', issues: [], database: { name: 'database', status: 'ok', latency_ms: 3.2 }, provider: { name: 'provider', status: 'ok', latency_ms: 4.1 } },
      worker: { status: 'ok', heartbeat_at: '2026-05-11T09:05:30Z', heartbeat_age_minutes: 4.5, current_job_id: 'job-running-1' },
      failed_jobs: [{ id: 'job-failed-1', job_type: 'run_after_close', status: 'failed', duration_seconds: 180, error_message: 'boom' }],
      duration_summary: { average_seconds: 240, p95_seconds: 300, recent_jobs: [] },
      freshness: { sources: [{ source: 'market_data', entity_type: 'market', freshness_hours: 24, is_stale: true }] },
      alerts: { critical: 1, warning: 0, latest: [{ level: 'critical', title: 'stale market data', message: 'market data is stale' }] },
      traces: [{ job_id: 'job-failed-1', request_context: { path: '/api/ui/v1/jobs', method: 'POST', client_host: '127.0.0.1' } }],
      report: {},
    });
    mockedBuildDashboardReport.mockResolvedValue({
      config_path: 'config/app.yaml',
      report: { title: 'Daily Health' },
      html_path: '/tmp/project/data/processed/dashboard/dashboard.html',
      critical_alerts: 0,
      exit_code: 0,
    });

    renderWithRouter([{ path: '/data-health', element: <DataHealthPage /> }], ['/data-health']);

    expect(await screen.findByRole('heading', { name: 'Health Check Dashboard', level: 1 })).toBeInTheDocument();
    expect((await screen.findAllByText('job-failed-1')).length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText('stale market data')).toBeInTheDocument();
    expect(
      await screen.findByText('/tmp/project/data/processed/dashboard/dashboard.html', { selector: 'p' }),
    ).toBeInTheDocument();
    expect(await screen.findByTestId('data-health-json')).toHaveTextContent('dashboard.html');
  });
});
