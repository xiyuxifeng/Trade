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
      artifacts: [{ kind: 'report', path: 'data/jobs/job-1/result.json', metadata: { source: 'job' } }],
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

    expect(await screen.findByText('Job details')).toBeInTheDocument();
    expect(await screen.findByText('report')).toBeInTheDocument();
    expect(await screen.findByText('Audit trail')).toBeInTheDocument();
    expect(await screen.findByText('web · create')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Open in Artifacts' }));
    expect(await screen.findByText('Artifact center')).toBeInTheDocument();
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

    renderWithRouter([{ path: '/jobs', element: <JobsPage /> }], ['/jobs?jobId=job-1']);

    expect(await screen.findByText('Job details')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Rerun job' }));
    await user.click(screen.getByRole('button', { name: 'Confirm rerun' }));

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

    expect(await screen.findByText('Job details')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Rerun job' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel job' })).toBeDisabled();
    expect(screen.getByText(/需要 operator 权限/)).toBeInTheDocument();
  });
});
