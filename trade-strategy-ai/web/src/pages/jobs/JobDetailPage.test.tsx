import { describe, expect, it, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { getJob, getJobDefinition, getJobLogs } from '@/lib/api/jobs';
import { renderWithRouter } from '@/test/test-utils';
import { JobDetailPage } from './JobDetailPage';

vi.mock('@/lib/api/jobs', () => ({
  cancelJob: vi.fn(),
  createJob: vi.fn(),
  getJob: vi.fn(),
  getJobDefinition: vi.fn(),
  getJobLogs: vi.fn(),
  pauseJob: vi.fn(),
  resumeJob: vi.fn(),
  retryJob: vi.fn(),
  listJobs: vi.fn(),
}));

const mockedGetJob = vi.mocked(getJob);
const mockedGetJobDefinition = vi.mocked(getJobDefinition);
const mockedGetJobLogs = vi.mocked(getJobLogs);

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('JobDetailPage', () => {
  it('renders successful job detail sections, artifacts and config snapshot', async () => {
    mockedGetJobDefinition.mockResolvedValue({
      job_type: 'pipeline-run',
      title: 'Pipeline Run',
      service_name: 'pipeline',
      handler_name: 'pipeline_run',
      permission: 'operator',
      risk: 'medium',
      can_retry: true,
      can_pause: true,
      can_resume: true,
      can_cancel: true,
      can_run_concurrently: false,
      concurrency_group: 'pipeline',
      requires_confirmation: false,
      runnable: true,
      description: 'desc',
      param_schema: {},
    });
    mockedGetJob.mockResolvedValue({
      job: {
        id: 'job-1',
        job_type: 'pipeline-run',
        status: 'success',
        params: { config_path: '/Users/example/project/config/app.yaml', force: true },
        result: { message: 'ok' },
        error: null,
        progress: {
          job_type: 'kaipan-fetch',
          stage: 'normalize',
          current: 2,
          total: 4,
          percent: 50,
          remaining: 2,
          current_trade_date: '2026-05-09',
          current_slot: '09-25',
          current_fetcher: null,
          current_dataset: 'hot_topics',
          current_step: 'normalize:hot_topics',
          status: 'success',
          error: null,
          updated_at: '2026-05-09T08:01:00Z',
        },
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
        runtime_state: null,
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
    expect(screen.getByText('成功')).toBeInTheDocument();
    expect(screen.getByText('执行进度')).toBeInTheDocument();
    expect(screen.getByText('normalize:hot_topics')).toBeInTheDocument();
    expect(screen.getByText('2 / 4 · 50%')).toBeInTheDocument();
    expect(screen.getByText('脱敏配置快照')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '预览' })).toBeInTheDocument();
  });

  it('renders failed job detail with empty artifact fallback', async () => {
    mockedGetJobDefinition.mockResolvedValue({
      job_type: 'pipeline-run',
      title: 'Pipeline Run',
      service_name: 'pipeline',
      handler_name: 'pipeline_run',
      permission: 'operator',
      risk: 'medium',
      can_retry: true,
      can_pause: true,
      can_resume: true,
      can_cancel: true,
      can_run_concurrently: false,
      concurrency_group: 'pipeline',
      requires_confirmation: false,
      runnable: true,
      description: 'desc',
      param_schema: {},
    });
    mockedGetJob.mockResolvedValue({
      job: {
        id: 'job-2',
        job_type: 'pipeline-run',
        status: 'failed',
        params: { config_path: '/Users/example/project/config/app.yaml' },
        result: null,
        error: { type: 'runner_error', message: 'handler failed' },
        artifacts: [],
        created_by: 'web',
        idempotency_key: null,
        retry_count: 0,
        max_retries: 3,
        retry_backoff_seconds: 0,
        timeout_seconds: null,
        cancel_requested: false,
        cancel_requested_at: null,
        worker_id: 'worker-1',
        lock_token: null,
        lock_acquired_at: '2026-05-09T08:00:00Z',
        heartbeat_at: '2026-05-09T08:01:00Z',
        scheduled_at: null,
        started_at: '2026-05-09T08:00:00Z',
        finished_at: '2026-05-09T08:05:00Z',
        audit_events: [
          {
            id: 'audit-1',
            job_id: 'job-2',
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
            job_id: 'job-2',
            operation: 'fail',
            actor: 'worker-1',
            source: 'runner',
            params_summary: { config_path: '/Users/example/project/config/app.yaml' },
            payload: { details: { error_type: 'runner_error' } },
            event_at: '2026-05-09T08:05:00Z',
            created_at: '2026-05-09T08:05:00Z',
            updated_at: '2026-05-09T08:05:00Z',
          },
        ],
        created_at: '2026-05-09T08:00:00Z',
        updated_at: '2026-05-09T08:05:00Z',
        runtime_state: null,
        config_snapshot_path: '/tmp/job-2/config_snapshot.json',
        config_snapshot: {
          config_snapshot_id: 'snapshot-2',
          job_id: 'job-2',
          config_path: '/Users/example/project/config/app.yaml',
          config_source: '/Users/example/project/config/app.yaml',
          config_hash: 'hash-2',
          masked_snapshot: {
            app: {
              api_key: '***',
            },
          },
          captured_at: '2026-05-09T07:55:00Z',
          snapshot_path: '/tmp/job-2/config_snapshot.json',
        },
      },
      job_dir: '/tmp/job-2',
      log_path: '/tmp/job-2/job.log',
      params_path: '/tmp/job-2/params.json',
      result_path: '/tmp/job-2/result.json',
      artifacts_path: '/tmp/job-2/artifacts.json',
    });
    mockedGetJobLogs.mockResolvedValue({
      job_id: 'job-2',
      log_path: '/tmp/job-2/job.log',
      count: 2,
      items: ['job started', 'handler failed'],
    });

    renderWithRouter([{ path: '/jobs/:jobId', element: <JobDetailPage /> }], ['/jobs/job-2']);

    expect(await screen.findByText('任务执行失败')).toBeInTheDocument();
    expect(screen.getByText('先打开 Job 详情确认错误，再决定是否重试。')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重新运行' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '重试' })).toBeInTheDocument();
    expect(screen.getByText('该任务未产生任何产物。')).toBeInTheDocument();
    expect(screen.getByText('脱敏配置快照')).toBeInTheDocument();
  });

  it('renders not found and permission denied states', async () => {
    mockedGetJob.mockRejectedValueOnce(new ApiError(404, 'job not found'));

    renderWithRouter([{ path: '/jobs/:jobId', element: <JobDetailPage /> }], ['/jobs/missing']);
    expect(await screen.findByText('任务不存在')).toBeInTheDocument();
    expect(screen.getByText('请检查任务 ID 是否正确，或返回任务列表查看最近任务。')).toBeInTheDocument();

    mockedGetJob.mockRejectedValueOnce(new ApiError(403, 'forbidden'));

    renderWithRouter([{ path: '/jobs/:jobId', element: <JobDetailPage /> }], ['/jobs/forbidden']);
    expect(await screen.findByText('没有权限访问任务详情')).toBeInTheDocument();
  });
});
