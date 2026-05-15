import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { JobsPage } from './index';
import { ArtifactsPage } from '@/pages/artifacts';
import { renderWithRouter } from '@/test/test-utils';
import { createJob, getJob, getJobLogs, listJobs } from '@/lib/api/jobs';
import { listArtifacts } from '@/lib/api/artifacts';

vi.mock('@/lib/api/jobs', () => ({
  cancelJob: vi.fn(),
  createJob: vi.fn(),
  getJob: vi.fn(),
  getJobLogs: vi.fn(),
  listJobs: vi.fn(),
}));

vi.mock('@/lib/api/artifacts', () => ({
  downloadArtifact: vi.fn(),
  getArtifact: vi.fn(),
  listArtifacts: vi.fn(),
}));

const mockedListJobs = vi.mocked(listJobs);
const mockedGetJob = vi.mocked(getJob);
const mockedGetJobLogs = vi.mocked(getJobLogs);
const mockedCreateJob = vi.mocked(createJob);
const mockedListArtifacts = vi.mocked(listArtifacts);

describe('JobsPage', () => {
  it('navigates to artifacts from an artifact reference', async () => {
    const user = userEvent.setup();
    const job1 = {
      id: 'job-1',
      job_type: 'run-pre-market',
      status: 'success',
      params: { date: '2026-05-09' },
      result: null,
      error: null,
      artifacts: [
        {
          artifact_id: 'artifact-1',
          job_id: 'job-1',
          workflow_id: null,
          step_id: null,
          kind: 'report',
          title: '抓取报告',
          summary: '任务执行结果摘要',
          safe_download_url: '/api/ui/v1/artifacts/artifact-1/download',
          download_token: null,
          size_bytes: 128,
          created_at: '2026-05-09T08:05:00Z',
          visibility: 'internal',
          metadata: { source: 'job' },
          storage_ref: null,
        },
      ],
      config_snapshot: {
        config_snapshot_id: 'snapshot-1',
        job_id: 'job-1',
        config_path: 'config/app.yaml',
        config_source: '/Users/example/project/config/app.yaml',
        config_hash: 'hash-1',
        masked_snapshot: { app: { api_key: '***' } },
        captured_at: '2026-05-09T07:55:00Z',
        snapshot_path: '/tmp/job-1/config_snapshot.json',
      },
      config_snapshot_path: '/tmp/job-1/config_snapshot.json',
      audit_events: [
        {
          id: 'audit-1',
          job_id: 'job-1',
          operation: 'create',
          actor: 'web',
          source: 'ui',
          params_summary: { date: '2026-05-09' },
          payload: { request_context: { channel: 'ui' } },
          event_at: '2026-05-09T08:00:00Z',
          created_at: '2026-05-09T08:00:00Z',
          updated_at: '2026-05-09T08:00:00Z',
        },
      ],
      created_by: 'web',
      idempotency_key: null,
      retry_count: 0,
      max_retries: 3,
      retry_backoff_seconds: 0,
      timeout_seconds: null,
      cancel_requested: false,
      cancel_requested_at: null,
      worker_id: null,
      lock_token: null,
      lock_acquired_at: null,
      heartbeat_at: null,
      scheduled_at: null,
      started_at: '2026-05-09T08:00:00Z',
      finished_at: '2026-05-09T08:05:00Z',
      created_at: '2026-05-09T08:00:00Z',
      updated_at: '2026-05-09T08:05:00Z',
    };

    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [job1],
    });
    mockedGetJob.mockResolvedValue({
      job: job1,
      job_dir: '/tmp/job-1',
      log_path: '/tmp/job-1/job.log',
      params_path: '/tmp/job-1/params.json',
      result_path: '/tmp/job-1/result.json',
      artifacts_path: '/tmp/job-1/artifacts.json',
    });
    mockedGetJobLogs.mockResolvedValue({
      job_id: 'job-1',
      log_path: '/tmp/job-1/job.log',
      count: 1,
      items: ['job started'],
    });
    mockedListArtifacts.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 50,
      items: [],
    });

    renderWithRouter(
      [
        { path: '/jobs', element: <JobsPage /> },
        { path: '/artifacts', element: <ArtifactsPage /> },
      ],
      ['/jobs?jobId=job-1'],
    );

    expect(await screen.findByText('任务详情')).toBeInTheDocument();
    expect(await screen.findByText('抓取报告')).toBeInTheDocument();
    expect(await screen.findByText('步骤时间线')).toBeInTheDocument();
    expect(await screen.findByText('web · create')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '在产物中心查看' }));
    expect(await screen.findByText('产物中心')).toBeInTheDocument();
  });

  it('reruns the selected job with the current parameter snapshot', async () => {
    const user = userEvent.setup();
    const job1 = {
      id: 'job-1',
      job_type: 'run-pre-market',
      status: 'success',
      params: { date: '2026-05-09' },
      result: null,
      error: null,
      artifacts: [],
      config_snapshot: null,
      config_snapshot_path: null,
      audit_events: [],
      created_by: 'web',
      idempotency_key: null,
      retry_count: 0,
      max_retries: 3,
      retry_backoff_seconds: 0,
      timeout_seconds: null,
      cancel_requested: false,
      cancel_requested_at: null,
      worker_id: null,
      lock_token: null,
      lock_acquired_at: null,
      heartbeat_at: null,
      scheduled_at: null,
      started_at: '2026-05-09T08:00:00Z',
      finished_at: '2026-05-09T08:05:00Z',
      created_at: '2026-05-09T08:00:00Z',
      updated_at: '2026-05-09T08:05:00Z',
    };
    const job2 = {
      id: 'job-2',
      job_type: 'run-pre-market',
      status: 'pending',
      params: { date: '2026-05-09' },
      result: null,
      error: null,
      artifacts: [],
      config_snapshot: null,
      config_snapshot_path: null,
      audit_events: [],
      created_by: 'web',
      idempotency_key: null,
      retry_count: 0,
      max_retries: 3,
      retry_backoff_seconds: 0,
      timeout_seconds: null,
      cancel_requested: false,
      cancel_requested_at: null,
      worker_id: null,
      lock_token: null,
      lock_acquired_at: null,
      heartbeat_at: null,
      scheduled_at: null,
      started_at: null,
      finished_at: null,
      created_at: '2026-05-09T09:00:00Z',
      updated_at: '2026-05-09T09:00:00Z',
    };

    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [job1],
    });
    mockedGetJob.mockImplementation(async (jobId: string) => ({
      job: jobId === 'job-2' ? job2 : job1,
      job_dir: jobId === 'job-2' ? '/tmp/job-2' : '/tmp/job-1',
      log_path: jobId === 'job-2' ? '/tmp/job-2/job.log' : '/tmp/job-1/job.log',
      params_path: jobId === 'job-2' ? '/tmp/job-2/params.json' : '/tmp/job-1/params.json',
      result_path: jobId === 'job-2' ? '/tmp/job-2/result.json' : '/tmp/job-1/result.json',
      artifacts_path: jobId === 'job-2' ? '/tmp/job-2/artifacts.json' : '/tmp/job-1/artifacts.json',
    }));
    mockedGetJobLogs.mockResolvedValue({
      job_id: 'job-1',
      log_path: '/tmp/job-1/job.log',
      count: 1,
      items: ['job started'],
    });
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: job2,
      job_dir: '/tmp/job-2',
      log_path: '/tmp/job-2/job.log',
      params_path: '/tmp/job-2/params.json',
      result_path: '/tmp/job-2/result.json',
      artifacts_path: '/tmp/job-2/artifacts.json',
    });

    renderWithRouter(
      [
        { path: '/jobs', element: <JobsPage /> },
        { path: '/jobs/:jobId', element: <div>job detail page</div> },
      ],
      ['/jobs?jobId=job-1'],
    );

    expect(await screen.findByText('任务详情')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '重新运行任务' }));
    await user.click(screen.getByRole('button', { name: '确认重新运行' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith({
        job_type: 'run-pre-market',
        params: { date: '2026-05-09' },
        created_by: 'web',
        max_retries: 3,
        retry_backoff_seconds: 0,
        timeout_seconds: null,
      });
    });
  });

  it('disables rerun and cancel actions for viewer principals', async () => {
    const job1 = {
      id: 'job-1',
      job_type: 'run-pre-market',
      status: 'success',
      params: { date: '2026-05-09' },
      result: null,
      error: null,
      artifacts: [],
      config_snapshot: null,
      config_snapshot_path: null,
      audit_events: [],
      created_by: 'web',
      idempotency_key: null,
      retry_count: 0,
      max_retries: 3,
      retry_backoff_seconds: 0,
      timeout_seconds: null,
      cancel_requested: false,
      cancel_requested_at: null,
      worker_id: null,
      lock_token: null,
      lock_acquired_at: null,
      heartbeat_at: null,
      scheduled_at: null,
      started_at: '2026-05-09T08:00:00Z',
      finished_at: '2026-05-09T08:05:00Z',
      created_at: '2026-05-09T08:00:00Z',
      updated_at: '2026-05-09T08:05:00Z',
    };

    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [job1],
    });
    mockedGetJob.mockResolvedValue({
      job: job1,
      job_dir: '/tmp/job-1',
      log_path: '/tmp/job-1/job.log',
      params_path: '/tmp/job-1/params.json',
      result_path: '/tmp/job-1/result.json',
      artifacts_path: '/tmp/job-1/artifacts.json',
    });
    mockedGetJobLogs.mockResolvedValue({
      job_id: 'job-1',
      log_path: '/tmp/job-1/job.log',
      count: 1,
      items: ['job started'],
    });

    renderWithRouter(
      [{ path: '/jobs', element: <JobsPage /> }],
      ['/jobs?jobId=job-1'],
      {
        initialPrincipal: {
          role: 'viewer',
          api_key_label: 'Local Viewer',
          authenticated: true,
          source: 'api_key',
        },
      },
    );

    expect(await screen.findByText('任务详情')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重新运行任务' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '取消任务' })).toBeDisabled();
    expect(screen.getByText(/需要 operator 权限/)).toBeInTheDocument();
  });
});
