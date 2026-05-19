import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { OpsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { createRecoveryBackup, listRecoveryBackups, recoverStaleJobs, restoreRecoveryBackup } from '@/lib/api/ops';
import { getSystemDashboard, getSystemStatus } from '@/lib/api/system';
import { listJobs } from '@/lib/api/jobs';
import { listDataAudits } from '@/lib/api/data-audits';
import type { CurrentPrincipal } from '@/types/auth';

vi.mock('@/lib/api/ops', () => ({
  createRecoveryBackup: vi.fn(),
  listRecoveryBackups: vi.fn(),
  recoverStaleJobs: vi.fn(),
  restoreRecoveryBackup: vi.fn(),
}));

vi.mock('@/lib/api/system', () => ({
  getSystemDashboard: vi.fn(),
  getSystemStatus: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  listJobs: vi.fn(),
}));

vi.mock('@/lib/api/data-audits', () => ({
  listDataAudits: vi.fn(),
}));

const mockedListRecoveryBackups = vi.mocked(listRecoveryBackups);
const mockedCreateRecoveryBackup = vi.mocked(createRecoveryBackup);
const mockedRecoverStaleJobs = vi.mocked(recoverStaleJobs);
const mockedRestoreRecoveryBackup = vi.mocked(restoreRecoveryBackup);
const mockedGetSystemStatus = vi.mocked(getSystemStatus);
const mockedGetSystemDashboard = vi.mocked(getSystemDashboard);
const mockedListJobs = vi.mocked(listJobs);
const mockedListDataAudits = vi.mocked(listDataAudits);

describe('OpsPage', () => {
  const principal: CurrentPrincipal = {
    role: 'admin',
    api_key_label: 'Local Admin',
    authenticated: true,
    source: 'api_key',
    username: 'admin',
  };

  beforeEach(() => {
    vi.clearAllMocks();
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
      health: {
        overall: 'partial',
        issues: ['worker stale'],
        database: { name: 'database', status: 'ok', latency_ms: 3.2 },
        provider: { name: 'provider', status: 'warning', latency_ms: 7.1 },
        storage: { name: 'storage', status: 'ok', latency_ms: 4.1 },
      },
      worker: { status: 'warning', heartbeat_at: '2026-05-11T09:05:30Z', heartbeat_age_minutes: 12, current_job_id: 'job-running-1' },
      failed_jobs: [{ id: 'job-failed-1', job_type: 'run_after_close', status: 'failed', duration_seconds: 180, error_message: 'boom' }],
      duration_summary: { average_seconds: 240, p95_seconds: 300, recent_jobs: [] },
      freshness: { sources: [{ source: 'market_data', entity_type: 'market', freshness_hours: 24, is_stale: true }] },
      alerts: { critical: 1, warning: 0, latest: [{ level: 'critical', title: 'stale market data', message: 'market data is stale' }] },
      traces: [{ job_id: 'job-failed-1', request_context: { path: '/api/ui/v1/jobs', method: 'POST', client_host: '127.0.0.1' } }],
      report: {},
    });
    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 20,
      items: [
        {
          id: 'job-running-1',
          job_type: 'crawl',
          status: 'running',
          params: {},
          result: null,
          error: null,
          artifacts: [],
          created_by: 'web',
          idempotency_key: null,
          retry_count: 0,
          max_retries: 3,
          retry_backoff_seconds: 30,
          timeout_seconds: null,
          cancel_requested: false,
          cancel_requested_at: null,
          worker_id: 'worker-1',
          lock_token: 'lock-1',
          lock_acquired_at: '2026-05-11T09:00:00Z',
          heartbeat_at: '2026-05-11T09:00:00Z',
          scheduled_at: '2026-05-11T09:00:00Z',
          started_at: '2026-05-11T09:00:00Z',
          finished_at: null,
          audit_events: [],
          created_at: '2026-05-11T09:00:00Z',
          updated_at: '2026-05-11T09:00:00Z',
          config_snapshot_path: null,
          config_snapshot: null,
        },
      ],
    });
    mockedListRecoveryBackups.mockResolvedValue({
      base_dir: '/project',
      backup_root: '/project/data/backups',
      count: 1,
      items: [
        {
          path: '/project/data/backups/20260511-080000',
          name: '20260511-080000',
          size_bytes: 4096,
          modified_at: '2026-05-11T08:00:00Z',
          tables: ['jobs', 'artifacts'],
          row_counts: { jobs: 1, artifacts: 2 },
          include_processed: true,
          processed_copied: true,
        },
      ],
    });
    mockedListDataAudits.mockResolvedValue({
      filters: { event_type: null, actor: null, source: null, entity_type: 'backup', start_date: null, end_date: null },
      summary: { total: 1, event_type_counts: { backup_project_state: 1 }, entity_type_counts: { backup: 1 }, source_counts: { ui: 1 } },
      page: { total: 1, skip: 0, limit: 10, count: 1 },
      items: [
        {
          id: 'audit-1',
          event_type: 'backup_project_state',
          actor: 'ui.ops',
          entity_type: 'backup',
          entity_id: '20260511-080000',
          dataset_version: '20260511-080000',
          source: 'ui',
          payload: { tables: ['jobs'], processed_copied: true },
          event_at: '2026-05-11T08:00:00Z',
          created_at: '2026-05-11T08:00:00Z',
          updated_at: '2026-05-11T08:00:00Z',
        },
      ],
    });
  });

  it('renders the ops console and supports recovery actions', async () => {
    const user = userEvent.setup();
    mockedCreateRecoveryBackup.mockResolvedValue({
      backup_dir: '/project/data/backups/20260511-120000',
      tables: ['jobs', 'artifacts'],
      row_counts: { jobs: 1, artifacts: 2 },
      include_processed: true,
      processed_copied: true,
    });
    mockedRestoreRecoveryBackup.mockResolvedValue({
      backup_dir: '/project/data/backups/20260511-080000',
      tables: ['jobs', 'artifacts'],
      row_counts: { jobs: 1, artifacts: 2 },
      include_processed: true,
      processed_restored: true,
    });
    mockedRecoverStaleJobs.mockResolvedValue({
      count: 1,
      job_ids: ['job-running-1'],
      stale_before: '2026-05-11T08:50:00Z',
      stale_before_minutes: 12,
    });

    renderWithRouter([{ path: '/ops', element: <OpsPage /> }], ['/ops'], { initialPrincipal: principal });

    expect(await screen.findByRole('heading', { name: 'Admin Ops Console' })).toBeInTheDocument();
    expect(await screen.findByText('/project/data/backups/20260511-080000')).toBeInTheDocument();
    expect(await screen.findByText('job-running-1')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '开始备份' }));
    await user.click(screen.getByRole('button', { name: 'Confirm backup' }));
    await waitFor(() => {
      expect(mockedCreateRecoveryBackup).toHaveBeenCalledWith({ include_processed: true });
    });

    await user.click(screen.getByRole('button', { name: '回收 stale jobs' }));
    const recoveryInput = screen.getByLabelText('Recovery confirmation');
    await user.type(recoveryInput, 'RECOVER');
    await user.click(screen.getByRole('button', { name: 'Confirm recovery' }));
    await waitFor(() => {
      expect(mockedRecoverStaleJobs).toHaveBeenCalledWith({ stale_before_minutes: 10 });
    });

    const restoreButton = screen.getAllByRole('button', { name: '恢复' })[0];
    await user.click(restoreButton);
    expect(await screen.findByRole('heading', { name: 'Confirm restore' })).toBeInTheDocument();
    const confirmInput = screen.getByLabelText('Restore confirmation');
    await user.type(confirmInput, 'RESTORE');
    await user.click(screen.getByRole('button', { name: 'Confirm restore' }));

    await waitFor(() => {
      expect(mockedRestoreRecoveryBackup).toHaveBeenCalledWith({
        backup_path: '/project/data/backups/20260511-080000',
        include_processed: true,
        confirmed: true,
      });
    });
  });

  it('disables recovery actions for operator principals', async () => {
    renderWithRouter([{ path: '/ops', element: <OpsPage /> }], ['/ops'], {
      initialPrincipal: {
        role: 'operator',
        api_key_label: 'Local Operator',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByText('没有权限访问运维中心')).toBeInTheDocument();
    expect(screen.getByText('当前身份需要 admin 权限。')).toBeInTheDocument();
  });
});
