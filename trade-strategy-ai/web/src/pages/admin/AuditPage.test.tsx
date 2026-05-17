import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { getJobAuditDetail, listJobAudits } from '@/lib/api/job-audits';
import { renderWithRouter } from '@/test/test-utils';
import { AdminAuditPage } from './AuditPage';

vi.mock('@/lib/api/job-audits', () => ({
  getJobAuditDetail: vi.fn(),
  listJobAudits: vi.fn(),
}));

const mockedListJobAudits = vi.mocked(listJobAudits);
const mockedGetJobAuditDetail = vi.mocked(getJobAuditDetail);

describe('AdminAuditPage', () => {
  it('renders audit list and job detail for admin principals', async () => {
    mockedListJobAudits.mockResolvedValue({
      filters: {
        actor: null,
        job_type: null,
        operation: null,
        start_date: null,
        end_date: null,
        confirmed: null,
      },
      summary: {
        total: 1,
        confirmed_count: 1,
        high_risk_count: 1,
        unique_jobs: 1,
        operation_counts: { create: 1 },
      },
      page: { total: 1, skip: 0, limit: 20, count: 1 },
      items: [
        {
          id: 'audit-1',
          job_id: 'job-1',
          job_type: 'pipeline-run',
          job_status: 'success',
          created_by: 'web',
          operation: 'create',
          actor: 'web',
          source: 'ui',
          confirmed: true,
          params_summary: { config_path: 'config/app.yaml' },
          payload: { request_context: { confirmed: true } },
          event_at: '2026-05-17T00:00:00+00:00',
          created_at: '2026-05-17T00:00:00+00:00',
          updated_at: '2026-05-17T00:00:00+00:00',
        },
      ],
    });
    mockedGetJobAuditDetail.mockResolvedValue({
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
        artifacts: [
          {
            artifact_id: 'artifact-1',
            job_id: 'job-1',
            workflow_id: null,
            step_id: null,
            kind: 'report',
            title: '回测报告',
            summary: 'report',
            safe_download_url: '/api/ui/v1/artifacts/artifact-1/download',
            download_token: null,
            size_bytes: 1024,
            created_at: '2026-05-17T00:02:00+00:00',
            visibility: 'internal',
            metadata: {},
            storage_ref: null,
          },
        ],
      },
      summary: {
        event_count: 2,
        confirmed_count: 1,
        high_risk_count: 1,
        has_artifacts: true,
      },
      request_context: { channel: 'ui', path: '/api/ui/v1/jobs', confirmed: true },
      items: [
        {
          id: 'audit-1',
          job_id: 'job-1',
          job_type: 'pipeline-run',
          job_status: 'success',
          created_by: 'web',
          operation: 'create',
          actor: 'web',
          source: 'ui',
          confirmed: true,
          params_summary: { config_path: 'config/app.yaml' },
          payload: { request_context: { confirmed: true } },
          event_at: '2026-05-17T00:00:00+00:00',
          created_at: '2026-05-17T00:00:00+00:00',
          updated_at: '2026-05-17T00:00:00+00:00',
        },
      ],
    });

    renderWithRouter([{ path: '/admin/audit', element: <AdminAuditPage /> }], ['/admin/audit'], {
      initialPrincipal: {
        role: 'admin',
        api_key_label: 'Local Admin',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByRole('heading', { name: '权限与审计' })).toBeInTheDocument();
    expect(await screen.findByText('回测报告')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '打开 Job 详情' })).toBeInTheDocument();
    expect(screen.getAllByText('已确认').length).toBeGreaterThan(0);
  });

  it('renders permission denied state for non-admin principals', async () => {
    mockedListJobAudits.mockResolvedValue({
      filters: {
        actor: null,
        job_type: null,
        operation: null,
        start_date: null,
        end_date: null,
        confirmed: null,
      },
      summary: {
        total: 0,
        confirmed_count: 0,
        high_risk_count: 0,
        unique_jobs: 0,
        operation_counts: {},
      },
      page: { total: 0, skip: 0, limit: 20, count: 0 },
      items: [],
    });
    mockedGetJobAuditDetail.mockRejectedValue(new ApiError(403, 'forbidden'));

    renderWithRouter([{ path: '/admin/audit', element: <AdminAuditPage /> }], ['/admin/audit'], {
      initialPrincipal: {
        role: 'viewer',
        api_key_label: 'Local Viewer',
        authenticated: true,
        source: 'api_key',
      },
    });

    expect(await screen.findByText('没有权限访问审计中心')).toBeInTheDocument();
  });
});
