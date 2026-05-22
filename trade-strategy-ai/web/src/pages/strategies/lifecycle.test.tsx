import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Navigate } from 'react-router-dom';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { AfterClosePage, PreMarketPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listJobs } from '@/lib/api/jobs';
import { createJob } from '@/lib/api/jobs';
import { listBenchmarkOptions } from '@/lib/api/market';
import { listProfiles } from '@/lib/api/profiles';

vi.mock('@/lib/api/jobs', () => ({
  listJobs: vi.fn(),
  createJob: vi.fn(),
}));
vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
}));
vi.mock('@/lib/api/market', () => ({
  listBenchmarkOptions: vi.fn(),
}));

const mockedListJobs = vi.mocked(listJobs);
const mockedCreateJob = vi.mocked(createJob);
const mockedListBenchmarkOptions = vi.mocked(listBenchmarkOptions);
const mockedListProfiles = vi.mocked(listProfiles);

beforeEach(() => {
  vi.clearAllMocks();
  mockedListProfiles.mockResolvedValue({
    count: 1,
    total: 1,
    skip: 0,
    limit: 50,
    items: [
      {
        profile_id: 'default',
        name: '默认配置',
        environment: 'production',
        version: 3,
        sections: {},
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'tester',
        created_at: '2026-05-16T00:00:00Z',
        updated_at: '2026-05-16T00:00:00Z',
        archived_at: null,
      },
    ],
  } as never);
  mockedListJobs.mockResolvedValue({
    count: 0,
    total: 0,
    skip: 0,
    limit: 20,
    items: [],
  } as never);
  mockedListBenchmarkOptions.mockResolvedValue({
    count: 2,
    items: [
      { symbol: '000300.SH', code: '000300', market: 'SH', name: '沪深300', security_type: 'index' },
      { symbol: '000905.SH', code: '000905', market: 'SH', name: '中证500', security_type: 'index' },
    ],
  } as never);
});

describe('Strategy lifecycle pages', () => {
  it('submits snapshot-build and run-pre-market from the profile-only pre-market page', async () => {
    mockedListJobs
      .mockResolvedValueOnce({
        count: 1,
        total: 1,
        skip: 0,
        limit: 10,
        items: [
          {
            id: 'snapshot-build-1',
            job_type: 'snapshot-build',
            status: 'success',
            params: {},
            result: null,
            error: null,
            artifacts: [],
            created_by: 'web',
            idempotency_key: null,
            retry_count: 0,
            max_retries: 0,
            retry_backoff_seconds: 0,
            timeout_seconds: null,
            cancel_requested: false,
            cancel_requested_at: null,
            worker_id: null,
            lock_token: null,
            lock_acquired_at: null,
            heartbeat_at: null,
            scheduled_at: null,
            started_at: '2026-05-22T07:00:00Z',
            finished_at: '2026-05-22T07:05:00Z',
            audit_events: [],
            created_at: '2026-05-22T07:00:00Z',
            updated_at: '2026-05-22T07:05:00Z',
          },
        ],
      } as never)
      .mockResolvedValueOnce({
        count: 1,
        total: 1,
        skip: 0,
        limit: 10,
        items: [
          {
            id: 'run-pre-market-1',
            job_type: 'run-pre-market',
            status: 'success',
            params: {},
            result: null,
            error: null,
            artifacts: [],
            created_by: 'web',
            idempotency_key: null,
            retry_count: 0,
            max_retries: 0,
            retry_backoff_seconds: 0,
            timeout_seconds: null,
            cancel_requested: false,
            cancel_requested_at: null,
            worker_id: null,
            lock_token: null,
            lock_acquired_at: null,
            heartbeat_at: null,
            scheduled_at: null,
            started_at: '2026-05-22T08:00:00Z',
            finished_at: '2026-05-22T08:05:00Z',
            audit_events: [],
            created_at: '2026-05-22T08:00:00Z',
            updated_at: '2026-05-22T08:05:00Z',
          },
        ],
      } as never);
    mockedCreateJob.mockResolvedValueOnce({
      created: true,
      job: {
        id: 'job-snapshot-1',
        job_type: 'snapshot-build',
        status: 'pending',
      },
      job_dir: '/tmp/job-snapshot-1',
      log_path: '/tmp/job-snapshot-1/job.log',
      params_path: '/tmp/job-snapshot-1/params.json',
      result_path: '/tmp/job-snapshot-1/result.json',
      artifacts_path: '/tmp/job-snapshot-1/artifacts',
    } as never);
    mockedCreateJob.mockResolvedValueOnce({
      created: true,
      job: {
        id: 'job-run-1',
        job_type: 'run-pre-market',
        status: 'pending',
      },
      job_dir: '/tmp/job-run-1',
      log_path: '/tmp/job-run-1/job.log',
      params_path: '/tmp/job-run-1/params.json',
      result_path: '/tmp/job-run-1/result.json',
      artifacts_path: '/tmp/job-run-1/artifacts',
    } as never);

    renderWithRouter([{ path: '/strategies/pre-market', element: <PreMarketPage /> }], ['/strategies/pre-market']);

    expect(await screen.findByLabelText('Profile')).toHaveValue('default');
    expect(screen.getByLabelText('Profile')).toHaveValue('default');
    expect(screen.getByLabelText('Benchmark 选择')).toHaveValue('');
    expect(screen.getByLabelText('Strategy date')).toBeInTheDocument();
    expect(screen.getByLabelText('Snapshot start date')).toBeInTheDocument();
    expect(screen.getByLabelText('Snapshot end date')).toBeInTheDocument();
    expect(screen.getByLabelText('Snapshot slot')).toHaveValue('17-30');
    expect(screen.getByLabelText('Snapshot type')).toHaveValue('all');
    expect(screen.getByLabelText('Snapshot force')).not.toBeChecked();
    expect(screen.getByLabelText('Snapshot offline')).not.toBeChecked();
    expect(screen.getByLabelText('Run force')).not.toBeChecked();
    expect(screen.getByLabelText('Export HTML')).not.toBeChecked();
    expect(screen.getByRole('button', { name: '提交快照构建' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '提交盘前运行' })).toBeInTheDocument();
    expect(screen.getByText('可手动选择指数基准；留空时由后端按 Profile 默认值补齐。')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Strategy date'), { target: { value: '2026-05-22' } });
    fireEvent.change(screen.getByLabelText('Snapshot start date'), { target: { value: '2026-05-20' } });
    fireEvent.change(screen.getByLabelText('Snapshot end date'), { target: { value: '2026-05-22' } });
    fireEvent.change(screen.getByLabelText('Snapshot slot'), { target: { value: '17-30' } });
    fireEvent.change(screen.getByLabelText('Snapshot type'), { target: { value: 'all' } });
    fireEvent.click(screen.getByLabelText('Snapshot force'));
    fireEvent.click(screen.getByLabelText('Snapshot offline'));
    fireEvent.click(screen.getByRole('button', { name: '提交快照构建' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'snapshot-build',
            params: expect.objectContaining({
              profile_id: 'default',
              start_date: '2026-05-20',
              end_date: '2026-05-22',
              slot: '17-30',
              snapshot_type: 'all',
              force: true,
              offline: true,
            }),
          }),
        );
      expect(mockedCreateJob.mock.calls[0][0].params).not.toHaveProperty('date');
      expect(mockedCreateJob.mock.calls[0][0].params).not.toHaveProperty('benchmark_symbol');
    });

    fireEvent.change(screen.getByLabelText('Benchmark 选择'), { target: { value: '000905.SH' } });
    fireEvent.click(screen.getByLabelText('Run force'));
    fireEvent.click(screen.getByLabelText('Export HTML'));
    fireEvent.click(screen.getByRole('button', { name: '提交盘前运行' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'run-pre-market',
          params: expect.objectContaining({
            profile_id: 'default',
            benchmark_symbol: '000905.SH',
            as_of_date: '2026-05-22',
            force: true,
            export_html: true,
          }),
        }),
      );
    });
  });

  it.each([
    {
      initialPath: '/strategies/pre-market',
      heading: '盘前准备',
    },
    {
      initialPath: '/strategies/after-close',
      heading: '盘后复盘',
    },
  ])('renders lifecycle entry page for $heading', async ({ initialPath, heading }) => {
    if (initialPath === '/strategies/pre-market') {
      mockedListJobs
        .mockResolvedValueOnce({
          count: 1,
          total: 1,
          skip: 0,
          limit: 20,
          items: [
            {
              id: 'snapshot-build-1',
              job_type: 'snapshot-build',
              status: 'success',
              params: {},
              result: null,
              error: null,
              artifacts: [],
              created_by: 'web',
              idempotency_key: null,
              retry_count: 0,
              max_retries: 0,
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
              audit_events: [],
              created_at: '2026-05-22T07:00:00Z',
              updated_at: '2026-05-22T07:00:00Z',
            },
          ],
        } as never)
        .mockResolvedValueOnce({
          count: 1,
          total: 1,
          skip: 0,
          limit: 20,
          items: [
            {
              id: 'run-pre-market-1',
              job_type: 'run-pre-market',
              status: 'success',
              params: {},
              result: null,
              error: null,
              artifacts: [],
              created_by: 'web',
              idempotency_key: null,
              retry_count: 0,
              max_retries: 0,
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
              audit_events: [],
              created_at: '2026-05-22T08:00:00Z',
              updated_at: '2026-05-22T08:00:00Z',
            },
          ],
        } as never);
    } else {
      mockedListJobs.mockResolvedValue({
        count: 1,
        total: 1,
        skip: 0,
        limit: 20,
        items: [
          {
            id: 'run-after-close-1',
            job_type: 'run-after-close',
            status: 'success',
            params: {
              profile_id: 'default',
              as_of_date: '2026-05-21',
              force: false,
              export_html: true,
            },
            result: {
              as_of_date: '2026-05-21',
              evaluations_count: 2,
              result: {
                result_id: 'evaluation-1',
                as_of_date: '2026-05-21',
                generated_at: '2026-05-21T08:30:00Z',
                evaluations: [
                  {
                    idea_id: 'idea-1',
                    symbol: '000001.SZ',
                    entry_price: 10,
                    current_price: 11.2,
                    return_pct: 0.12,
                    status: 'ok',
                    partial_data: false,
                    fallback_reason: null,
                    notes: ['首个信号表现良好'],
                  },
                  {
                    idea_id: 'idea-2',
                    symbol: '000002.SZ',
                    entry_price: 9.8,
                    current_price: 9.4,
                    return_pct: -0.04,
                    status: 'partial',
                    partial_data: true,
                    fallback_reason: 'missing_last_price',
                    notes: ['第二个信号存在数据不足'],
                  },
                ],
                evidence_pack_refs: ['pack-1'],
                failure_categories: ['entry_timing_poor'],
                ranking_features: {
                  return_pct: 0.12,
                  mfe: 0.18,
                  mae: 0.03,
                },
                postmortem_notes: ['首个信号表现良好', '第二个信号存在数据不足'],
                summary: ['2 条评估', '1 条归因'],
              },
              html_path: 'evaluation_2026-05-21.html',
            },
            error: null,
            artifacts: [
              {
                artifact_id: 'artifact-1',
                job_id: 'run-after-close-1',
                workflow_id: null,
                step_id: null,
                kind: 'html',
                title: 'evaluation_2026-05-21.html',
                summary: '盘后 HTML',
                safe_download_url: '/api/ui/v1/artifacts/artifact-1/download',
                download_token: 'token',
                size_bytes: 1024,
                created_at: '2026-05-21T08:35:00Z',
                visibility: 'public',
                metadata: {},
                storage_ref: {
                  source: 'file',
                  logical_id: 'jobs/run-after-close-1/evaluation.html',
                  relative_path: 'jobs/run-after-close-1/evaluation.html',
                  uri: null,
                  metadata: {},
                },
              },
            ],
            created_by: 'web',
            idempotency_key: null,
            retry_count: 0,
            max_retries: 0,
            retry_backoff_seconds: 0,
            timeout_seconds: null,
            cancel_requested: false,
            cancel_requested_at: null,
            worker_id: null,
            lock_token: null,
            lock_acquired_at: null,
            heartbeat_at: null,
            scheduled_at: null,
            started_at: '2026-05-21T08:00:00Z',
            finished_at: '2026-05-21T08:40:00Z',
            audit_events: [],
            created_at: '2026-05-21T08:00:00Z',
            updated_at: '2026-05-21T08:40:00Z',
          },
        ],
      } as never);
      mockedCreateJob.mockResolvedValueOnce({
        created: true,
        job: {
          id: 'run-after-close-submit-1',
          job_type: 'run-after-close',
          status: 'pending',
        },
        job_dir: '/tmp/job-run-after-close-submit-1',
        log_path: '/tmp/job-run-after-close-submit-1/log.txt',
        params_path: '/tmp/job-run-after-close-submit-1/params.json',
        result_path: '/tmp/job-run-after-close-submit-1/result.json',
        artifacts_path: '/tmp/job-run-after-close-submit-1/artifacts',
      } as never);
    }

    renderWithRouter(
      [
        { path: '/strategies/pre-market', element: <PreMarketPage /> },
        { path: '/strategies/after-close', element: <AfterClosePage /> },
      ],
      [initialPath],
    );

    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /返回策略工作台/ })).toBeInTheDocument();

    if (initialPath === '/strategies/pre-market') {
      expect(await screen.findByRole('link', { name: /进入任务中心/ })).toHaveAttribute('href', '/jobs');
      expect(screen.getByRole('link', { name: /查看 snapshot-build/ })).toHaveAttribute('href', '/jobs?job_type=snapshot-build');
      expect(screen.getByRole('link', { name: /查看 run-pre-market/ })).toHaveAttribute('href', '/jobs?job_type=run-pre-market');
      expect(
        await screen.findByRole('heading', {
          name: '最近任务',
        }),
      ).toBeInTheDocument();
    } else {
      expect(await screen.findByLabelText('Profile')).toHaveValue('default');
      expect(screen.getByLabelText('执行日期')).toBeInTheDocument();
      expect(await screen.findByText('盘后结果')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '提交盘后复盘' })).toBeInTheDocument();
      expect(screen.getByText('盘后结果')).toBeInTheDocument();
      expect(screen.getByText('信号归因')).toBeInTheDocument();
      expect(screen.getByText('今日策略表现')).toBeInTheDocument();
      expect(screen.getByText('产物与来源')).toBeInTheDocument();
      expect(screen.getByText('entry_timing_poor')).toBeInTheDocument();
      expect(screen.getAllByText('evaluation_2026-05-21.html').length).toBeGreaterThan(0);
      expect(screen.getByRole('link', { name: '查看 Job Detail' })).toHaveAttribute('href', '/jobs/run-after-close-1');

      fireEvent.change(screen.getByLabelText('执行日期'), { target: { value: '2026-05-22' } });
      fireEvent.click(screen.getByLabelText('force'));
      fireEvent.click(screen.getByLabelText('export_html'));
      fireEvent.click(screen.getByRole('button', { name: '提交盘后复盘' }));

      await waitFor(() => {
        expect(mockedCreateJob).toHaveBeenCalledWith(
          expect.objectContaining({
            job_type: 'run-after-close',
            params: expect.objectContaining({
              profile_id: 'default',
              as_of_date: '2026-05-22',
              force: true,
              export_html: true,
            }),
          }),
        );
      });
      expect(mockedCreateJob.mock.calls[0][0].params).not.toHaveProperty('config_path');
    }
  });

  it.each([
    ['/workflows/pre-market/run', '/strategies/pre-market'],
    ['/workflows/after-close/run', '/strategies/after-close'],
  ])('redirects old workflow deep links %s to %s', async (initialPath, expectedPath) => {
    mockedListJobs.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 20,
      items: [],
    } as never);

    const { router } = renderWithRouter(
      [
        { path: '/strategies/pre-market', element: <PreMarketPage /> },
        { path: '/strategies/after-close', element: <AfterClosePage /> },
        { path: '/workflows/pre-market/run', element: <Navigate to="/strategies/pre-market" replace /> },
        { path: '/workflows/after-close/run', element: <Navigate to="/strategies/after-close" replace /> },
      ],
      [initialPath],
    );

    await waitFor(() => {
      expect(router.state.location.pathname).toBe(expectedPath);
    });
  });
});
