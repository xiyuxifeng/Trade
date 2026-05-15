import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { getJob, getJobLogs } from '@/lib/api/jobs';
import { renderWithRouter } from '@/test/test-utils';
import { JobDetailPage } from './JobDetailPage';

vi.mock('@/lib/api/jobs', () => ({
  cancelJob: vi.fn(),
  createJob: vi.fn(),
  getJob: vi.fn(),
  getJobLogs: vi.fn(),
  listJobs: vi.fn(),
}));

const mockedGetJob = vi.mocked(getJob);
const mockedGetJobLogs = vi.mocked(getJobLogs);

describe('JobDetailPage', () => {
  it('renders job detail sections, artifacts and config snapshot', async () => {
    mockedGetJob.mockResolvedValue({
      job: {
        id: 'job-1',
        job_type: 'pipeline-run',
        status: 'running',
        params: { config_path: '/Users/example/project/config/app.yaml', force: true },
        result: { message: 'ok' },
        error: { type: 'runner_error', message: 'handler failed' },
        artifacts: [
          {
            artifact_id: 'artifact-1',
            job_id: 'job-1',
            workflow_id: null,
            step_id: 'pipeline-run',
            kind: 'report',
            title: '执行报告',
            summary: '运行结果摘要',
            safe_download_url: '/api/ui/v1/artifacts/artifact-1/download',
            download_token: null,
            size_bytes: 1024,
            created_at: '2026-05-09T08:05:00Z',
            visibility: 'internal',
            metadata: { source: 'job' },
            storage_ref: null,
          },
        ],
        created_by: 'web',
        idempotency_key: 'key-1',
        retry_count: 1,
        max_retries: 3,
        retry_backoff_seconds: 0,
        timeout_seconds: null,
        cancel_requested: false,
        cancel_requested_at: null,
        worker_id: 'worker-1',
        lock_token: 'lock-1',
        lock_acquired_at: '2026-05-09T08:00:00Z',
        heartbeat_at: '2026-05-09T08:01:00Z',
        scheduled_at: null,
        started_at: '2026-05-09T08:00:00Z',
        finished_at: null,
        audit_events: [
          {
            id: 'audit-1',
            job_id: 'job-1',
            operation: 'create',
            actor: 'web',
            source: 'ui',
            params_summary: { config_path: '/Users/example/project/config/app.yaml' },
            payload: { details: { request_context: { channel: 'ui' } } },
            event_at: '2026-05-09T08:00:00Z',
            created_at: '2026-05-09T08:00:00Z',
            updated_at: '2026-05-09T08:00:00Z',
          },
          {
            id: 'audit-2',
            job_id: 'job-1',
            operation: 'start',
            actor: 'worker-1',
            source: 'runner',
            params_summary: { config_path: '/Users/example/project/config/app.yaml' },
            payload: { details: { worker_id: 'worker-1' } },
            event_at: '2026-05-09T08:00:10Z',
            created_at: '2026-05-09T08:00:10Z',
            updated_at: '2026-05-09T08:00:10Z',
          },
        ],
        created_at: '2026-05-09T08:00:00Z',
        updated_at: '2026-05-09T08:01:00Z',
        config_snapshot_path: '/tmp/job-1/config_snapshot.json',
        config_snapshot: {
          config_snapshot_id: 'snapshot-1',
          job_id: 'job-1',
          config_path: '/Users/example/project/config/app.yaml',
          config_source: '/Users/example/project/config/app.yaml',
          config_hash: 'hash-1',
          masked_snapshot: { app: { api_key: '***' } },
          captured_at: '2026-05-09T07:55:00Z',
          snapshot_path: '/tmp/job-1/config_snapshot.json',
        },
      },
      job_dir: '/tmp/job-1',
      log_path: '/tmp/job-1/job.log',
      params_path: '/tmp/job-1/params.json',
      result_path: '/tmp/job-1/result.json',
      artifacts_path: '/tmp/job-1/artifacts.json',
    });
    mockedGetJobLogs.mockResolvedValue({
      job_id: 'job-1',
      log_path: '/tmp/job-1/job.log',
      count: 2,
      items: ['job started', 'processing...'],
    });

    renderWithRouter([{ path: '/jobs/:jobId', element: <JobDetailPage /> }], ['/jobs/job-1']);

    expect(await screen.findByText('执行报告')).toBeInTheDocument();
    expect(await screen.findByText('任务仍在运行，页面会自动刷新状态。')).toBeInTheDocument();
    expect(screen.getByText('脱敏配置快照')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '预览' })).toBeInTheDocument();
  });

  it('renders not found and permission denied states', async () => {
    mockedGetJob.mockRejectedValueOnce(new ApiError(404, 'job not found'));

    renderWithRouter([{ path: '/jobs/:jobId', element: <JobDetailPage /> }], ['/jobs/missing']);
    expect(await screen.findByText('任务不存在')).toBeInTheDocument();

    mockedGetJob.mockRejectedValueOnce(new ApiError(403, 'forbidden'));

    renderWithRouter([{ path: '/jobs/:jobId', element: <JobDetailPage /> }], ['/jobs/forbidden']);
    expect(await screen.findByText('没有权限访问该任务')).toBeInTheDocument();
  });
});
