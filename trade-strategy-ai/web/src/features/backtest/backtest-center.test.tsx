import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { cleanup, screen, waitFor } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { createJob } from '@/lib/api/jobs';
import {
  downloadBacktestReport,
  downloadBacktestValidationReport,
  getBacktestResult,
  listBacktestResults,
} from '@/lib/api/backtests';
import { listBenchmarkOptions } from '@/lib/api/market';
import { listArticleMetadataSummary } from '@/lib/api/article-metadata';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import { BacktestPage } from '@/pages/backtest';

vi.mock('@/lib/api/jobs', () => ({
  cancelJob: vi.fn(),
  createJob: vi.fn(),
  getJob: vi.fn(),
  getJobDefinition: vi.fn(),
  getJobLogs: vi.fn(),
  listJobDefinitions: vi.fn(),
  listJobs: vi.fn(),
  pauseJob: vi.fn(),
  resumeJob: vi.fn(),
  retryJob: vi.fn(),
}));

vi.mock('@/lib/api/backtests', () => ({
  buildBacktestReproducibilityParams: vi.fn((submission) => ({ kind: 'repro', submission })),
  buildBacktestRunParams: vi.fn((submission) => ({ kind: 'run', submission })),
  buildBacktestValidateRulesParams: vi.fn((submission) => ({ kind: 'validate', submission })),
  downloadBacktestReport: vi.fn(),
  downloadBacktestValidationReport: vi.fn(),
  getBacktestResult: vi.fn(),
  listBacktestResults: vi.fn(),
}));

vi.mock('@/lib/api/market', () => ({
  listBenchmarkOptions: vi.fn(),
}));

vi.mock('@/lib/api/article-metadata', () => ({
  listArticleMetadataSummary: vi.fn(),
}));

vi.mock('@/lib/api/profiles', () => ({
  getProfile: vi.fn(),
  listProfiles: vi.fn(),
}));

vi.mock('@/lib/api/strategyStudio', () => ({
  getStrategyVersion: vi.fn(),
  listStrategyVersions: vi.fn(),
}));

const mockedCreateJob = vi.mocked(createJob);
const mockedListProfiles = vi.mocked(listProfiles);
const mockedGetProfile = vi.mocked(getProfile);
const mockedListStrategyVersions = vi.mocked(listStrategyVersions);
const mockedGetStrategyVersion = vi.mocked(getStrategyVersion);
const mockedListBenchmarkOptions = vi.mocked(listBenchmarkOptions);
const mockedListBacktestResults = vi.mocked(listBacktestResults);
const mockedDownloadBacktestReport = vi.mocked(downloadBacktestReport);
const mockedDownloadBacktestValidationReport = vi.mocked(downloadBacktestValidationReport);
const mockedGetBacktestResult = vi.mocked(getBacktestResult);
const mockedListArticleMetadataSummary = vi.mocked(listArticleMetadataSummary);

beforeEach(() => {
  vi.restoreAllMocks();
  cleanup();

  mockedListProfiles.mockResolvedValue({
    count: 1,
    total: 1,
    skip: 0,
    limit: 50,
    items: [
      {
        profile_id: 'default',
        name: 'Default Profile',
        environment: 'production',
        version: 1,
        sections: {},
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T08:00:00Z',
        updated_at: '2026-05-16T08:10:00Z',
        archived_at: null,
      },
    ],
  } as never);
  mockedGetProfile.mockResolvedValue({
    profile: {
      profile_id: 'default',
      name: 'Default Profile',
      environment: 'production',
      version: 1,
      sections: {},
      secret_refs: {},
      validation_status: 'validated',
      created_by: 'web',
      created_at: '2026-05-16T08:00:00Z',
      updated_at: '2026-05-16T08:10:00Z',
      archived_at: null,
    },
    linked_jobs: [],
    snapshots: [
      {
        snapshot_id: 'profile-snapshot-1',
        profile_id: 'default',
        job_id: 'job-profile-1',
        source: 'profile-import',
        config_path: 'config/app.yaml',
        config_hash: 'hash-1',
        masked_snapshot: {},
        masked_sections: [],
        validation_status: 'validated',
        captured_at: '2026-05-16T08:10:00Z',
        snapshot_path: '/tmp/profile-snapshot-1.json',
      },
    ],
  } as never);
  mockedListStrategyVersions.mockResolvedValue({
    count: 1,
    total: 1,
    skip: 0,
    limit: 100,
    items: [
      {
        version_id: 'strategy-version-1',
        trader_id: 'trader-1',
        strategy_date: '2026-05-16',
        status: 'active',
      },
    ],
  } as never);
  mockedGetStrategyVersion.mockResolvedValue({
    version_id: 'strategy-version-1',
    trader_id: 'trader-1',
    strategy_date: '2026-05-16',
    status: 'active',
    source_article_ids: [],
  } as never);
  mockedListBenchmarkOptions.mockResolvedValue({
    count: 1,
    items: [{ symbol: '000300.SH', code: '000300', market: 'CN', name: '沪深300', security_type: 'index' }],
  } as never);
  mockedListBacktestResults.mockResolvedValue({
    count: 0,
    total: 0,
    skip: 0,
    limit: 8,
    items: [],
  } as never);
  mockedDownloadBacktestReport.mockResolvedValue(null as never);
  mockedDownloadBacktestValidationReport.mockResolvedValue(null as never);
  mockedGetBacktestResult.mockResolvedValue(null as never);
  mockedListArticleMetadataSummary.mockResolvedValue({
    count: 0,
    total: 0,
    skip: 0,
    limit: 20,
    items: [],
  } as never);
});

describe('BacktestCenter', () => {
  it('shows loading and success feedback when submitting a backtest job', async () => {
    const user = userEvent.setup();
    let resolveCreateJob:
      | ((value: {
          created: boolean;
          job: { id: string };
          job_dir: string;
          log_path: string;
          params_path: string;
          result_path: string;
          artifacts_path: string;
        }) => void)
      | undefined;

    mockedCreateJob.mockReturnValue(
      new Promise((resolve) => {
        resolveCreateJob = resolve;
      }) as never,
    );

    renderWithRouter([{ path: '/backtest', element: <BacktestPage /> }], ['/backtest']);

    expect(await screen.findByRole('heading', { name: '回测参数' })).toBeInTheDocument();
    const runButton = screen.getByRole('button', { name: '运行回测' });
    await user.click(runButton);

    expect(runButton).toHaveTextContent('提交中');
    expect(runButton).toBeDisabled();

    resolveCreateJob?.({
      created: true,
      job: { id: 'job-backtest-1' },
      job_dir: '/tmp/job-backtest-1',
      log_path: '/tmp/job-backtest-1/job.log',
      params_path: '/tmp/job-backtest-1/params.json',
      result_path: '/tmp/job-backtest-1/result.json',
      artifacts_path: '/tmp/job-backtest-1/artifacts.json',
    });

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'backtest-run',
          created_by: 'web',
        }),
      );
    });

    expect(await screen.findByText(/回测任务已提交/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '打开 Job 详情' })).toHaveAttribute('href', '/jobs/job-backtest-1');
  });

  it('shows a failure message when submitting a backtest job fails', async () => {
    const user = userEvent.setup();
    let rejectCreateJob:
      | ((reason?: unknown) => void)
      | undefined;
    mockedCreateJob.mockReturnValue(
      new Promise((_, reject) => {
        rejectCreateJob = reject;
      }) as never,
    );

    renderWithRouter([{ path: '/backtest', element: <BacktestPage /> }], ['/backtest']);

    expect(await screen.findByRole('heading', { name: '回测参数' })).toBeInTheDocument();
    const validateButton = screen.getByRole('button', { name: '验证规则' });
    const clickPromise = user.click(validateButton);

    await waitFor(() => {
      expect(validateButton).toHaveTextContent('提交中');
      expect(validateButton).toBeDisabled();
    });

    rejectCreateJob?.(new Error('backtest failed'));
    await clickPromise;

    await waitFor(() => {
      expect(screen.getByText('回测任务提交失败：回测任务提交失败，请稍后重试。')).toBeInTheDocument();
    });
  });
});
