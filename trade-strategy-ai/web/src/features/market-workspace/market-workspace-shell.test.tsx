import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { MarketKaipanWorkspaceShell, MarketOhlcvWorkspaceShell, MarketWorkspaceShell } from './market-workspace-shell';
import { renderWithRouter } from '@/test/test-utils';
import { createJob, listJobs } from '@/lib/api/jobs';
import { listArtifacts } from '@/lib/api/artifacts';
import { getOhlcvSchedulerStatus, listBenchmarkOptions, runOhlcvScheduler, stopOhlcvScheduler } from '@/lib/api/market';
import { buildDashboardReport } from '@/lib/api/dataHealth';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { kaipanRun, kaipanStatus, kaipanStop } from '@/lib/api/kaipan';

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
  listJobs: vi.fn(),
}));

vi.mock('@/lib/api/artifacts', () => ({
  listArtifacts: vi.fn(),
  getArtifact: vi.fn(),
  downloadArtifact: vi.fn(),
}));

vi.mock('@/lib/api/market', () => ({
  getOhlcvSchedulerStatus: vi.fn(),
  listBenchmarkOptions: vi.fn(),
  runOhlcvScheduler: vi.fn(),
  stopOhlcvScheduler: vi.fn(),
}));

vi.mock('@/lib/api/dataHealth', () => ({
  buildDashboardReport: vi.fn(),
}));

vi.mock('@/lib/api/kaipan', () => ({
  kaipanRun: vi.fn(),
  kaipanStatus: vi.fn(),
  kaipanStop: vi.fn(),
}));

vi.mock('@/lib/api/profiles', () => ({
  getProfile: vi.fn(),
  listProfiles: vi.fn(),
}));

const mockedCreateJob = vi.mocked(createJob);
const mockedListJobs = vi.mocked(listJobs);
const mockedListArtifacts = vi.mocked(listArtifacts);
const mockedListBenchmarkOptions = vi.mocked(listBenchmarkOptions);
const mockedGetOhlcvSchedulerStatus = vi.mocked(getOhlcvSchedulerStatus);
const mockedRunOhlcvScheduler = vi.mocked(runOhlcvScheduler);
const mockedStopOhlcvScheduler = vi.mocked(stopOhlcvScheduler);
const mockedBuildDashboardReport = vi.mocked(buildDashboardReport);
const mockedKaipanRun = vi.mocked(kaipanRun);
const mockedKaipanStatus = vi.mocked(kaipanStatus);
const mockedKaipanStop = vi.mocked(kaipanStop);
const mockedListProfiles = vi.mocked(listProfiles);
const mockedGetProfile = vi.mocked(getProfile);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('MarketWorkspaceShell', () => {
  it('renders the market workspace and can submit a market job', async () => {
    const user = userEvent.setup();

    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [],
    } as never);
    mockedListArtifacts.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 8,
      items: [],
    } as never);
    mockedListBenchmarkOptions.mockResolvedValue({
      count: 2,
      items: [
        { symbol: '000300.SH', code: '000300', market: 'CN', name: '沪深300', security_type: 'index' },
        { symbol: '510300.SH', code: '510300', market: 'CN', name: '沪深300ETF', security_type: 'etf' },
      ],
    } as never);
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-market-1' },
      job_dir: '/tmp/job-market-1',
      log_path: '/tmp/job-market-1/log.txt',
      params_path: '/tmp/job-market-1/params.json',
      result_path: '/tmp/job-market-1/result.json',
      artifacts_path: '/tmp/job-market-1/artifacts',
    } as never);
    mockedBuildDashboardReport.mockResolvedValue({
      critical_alerts: 0,
      exit_code: 0,
      html_path: '/tmp/dashboard.html',
      report: { summary: true },
    } as never);

    renderWithRouter([{ path: '/market', element: <MarketWorkspaceShell /> }], ['/market']);

    expect(await screen.findByRole('heading', { name: '市场数据工作台' })).toBeInTheDocument();
    expect(screen.getByText('运行指定任务')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '运行快照构建' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '运行快照构建' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'snapshot-build',
          params: expect.objectContaining({
            config_path: 'config/app.yaml',
            benchmark_symbol: '000300.SH',
          }),
        }),
      );
    });
  });

  it('renders the kaipan workspace footer blocks and success message', async () => {
    const user = userEvent.setup();

    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [],
    } as never);
    mockedListArtifacts.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 8,
      items: [],
    } as never);
    mockedListBenchmarkOptions.mockResolvedValue({
      count: 2,
      items: [
        { symbol: '000300.SH', code: '000300', market: 'CN', name: '沪深300', security_type: 'index' },
        { symbol: '510300.SH', code: '510300', market: 'CN', name: '沪深300ETF', security_type: 'etf' },
      ],
    } as never);
    mockedBuildDashboardReport.mockResolvedValue({
      critical_alerts: 1,
      exit_code: 0,
      html_path: '/tmp/dashboard.html',
      report: { summary: true, detail: {} },
    } as never);
    mockedKaipanStatus.mockResolvedValue({
      config_path: 'config/kaipan.yaml',
      base_dir: '/tmp/trade-strategy-ai',
      raw_base: '/tmp/trade-strategy-ai/data/raw',
      latest_slot: null,
      scheduler_started: false,
      scheduler_pre_market: '9:25',
      scheduler_post_close: '17:30',
    } as never);
    mockedKaipanRun.mockResolvedValue({
      config_path: 'config/kaipan.yaml',
      base_dir: '/tmp/trade-strategy-ai',
      pre_market: '9:25',
      post_close: '17:30',
      started: true,
      scheduler_started: true,
    } as never);
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
          config_path: 'config/kaipan.yaml',
          config_hash: 'hash-1',
          masked_snapshot: {},
          masked_sections: [],
          validation_status: 'validated',
          captured_at: '2026-05-16T08:10:00Z',
          snapshot_path: '/tmp/profile-snapshot-1.json',
        },
      ],
    } as never);
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-kaipan-1' },
      job_dir: '/tmp/job-kaipan-1',
      log_path: '/tmp/job-kaipan-1/log.txt',
      params_path: '/tmp/job-kaipan-1/params.json',
      result_path: '/tmp/job-kaipan-1/result.json',
      artifacts_path: '/tmp/job-kaipan-1/artifacts',
    } as never);

    renderWithRouter([{ path: '/market/kaipan', element: <MarketKaipanWorkspaceShell /> }], ['/market/kaipan']);

    expect(await screen.findByRole('heading', { name: 'Kaipan 数据' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Dashboard report' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '最近产物' })).toBeInTheDocument();
    expect(await screen.findByRole('combobox', { name: /Profile/ })).toHaveValue('default');
    expect(screen.getByRole('button', { name: '启动调度器' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '启动调度器' }));

    await waitFor(() => {
      expect(screen.getByText(/Kaipan 调度器已启动/)).toBeInTheDocument();
      expect(mockedKaipanRun).toHaveBeenCalledWith(
        expect.objectContaining({
          start_scheduler: true,
          block: false,
        }),
      );
      expect(screen.getByRole('button', { name: '停止调度器' })).toBeInTheDocument();
    });
  });

  it('renders the kaipan scheduler stop state and can stop scheduler', async () => {
    const user = userEvent.setup();

    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [],
    } as never);
    mockedListArtifacts.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 8,
      items: [],
    } as never);
    mockedListBenchmarkOptions.mockResolvedValue({
      count: 2,
      items: [
        { symbol: '000300.SH', code: '000300', market: 'CN', name: '沪深300', security_type: 'index' },
        { symbol: '510300.SH', code: '510300', market: 'CN', name: '沪深300ETF', security_type: 'etf' },
      ],
    } as never);
    mockedBuildDashboardReport.mockResolvedValue({
      critical_alerts: 1,
      exit_code: 0,
      html_path: '/tmp/dashboard.html',
      report: { summary: true, detail: {} },
    } as never);
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
          config_path: 'config/kaipan.yaml',
          config_hash: 'hash-1',
          masked_snapshot: {},
          masked_sections: [],
          validation_status: 'validated',
          captured_at: '2026-05-16T08:10:00Z',
          snapshot_path: '/tmp/profile-snapshot-1.json',
        },
      ],
    } as never);
    mockedKaipanStatus
      .mockResolvedValueOnce({
        config_path: 'config/kaipan.yaml',
        base_dir: '/tmp/trade-strategy-ai',
        raw_base: '/tmp/trade-strategy-ai/data/raw',
        latest_slot: '2026-05-23_17-30',
        scheduler_started: true,
        scheduler_pre_market: '9:25',
        scheduler_post_close: '17:30',
      } as never)
      .mockResolvedValueOnce({
        config_path: 'config/kaipan.yaml',
        base_dir: '/tmp/trade-strategy-ai',
        raw_base: '/tmp/trade-strategy-ai/data/raw',
        latest_slot: '2026-05-23_17-30',
        scheduler_started: false,
        scheduler_pre_market: '9:25',
        scheduler_post_close: '17:30',
      } as never);
    mockedKaipanStop.mockResolvedValue({
      config_path: 'config/kaipan.yaml',
      base_dir: '/tmp/trade-strategy-ai',
      started: false,
      pre_market: '9:25',
      post_close: '17:30',
    } as never);

    renderWithRouter([{ path: '/market/kaipan', element: <MarketKaipanWorkspaceShell /> }], ['/market/kaipan']);

    expect(await screen.findByRole('button', { name: '停止调度器' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '停止调度器' }));

    await waitFor(() => {
      expect(screen.getByText(/Kaipan 调度器已停止/)).toBeInTheDocument();
      expect(mockedKaipanStop).toHaveBeenCalledTimes(1);
      expect(screen.getByRole('button', { name: '启动调度器' })).toBeInTheDocument();
    });
  });

  it('renders the ohlcv scheduler state and can toggle scheduler', async () => {
    const user = userEvent.setup();

    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [],
    } as never);
    mockedListArtifacts.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 8,
      items: [],
    } as never);
    mockedListBenchmarkOptions.mockResolvedValue({
      count: 2,
      items: [
        { symbol: '000300.SH', code: '000300', market: 'CN', name: '沪深300', security_type: 'index' },
        { symbol: '510300.SH', code: '510300', market: 'CN', name: '沪深300ETF', security_type: 'etf' },
      ],
    } as never);
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
          config_path: 'config/ohlcv.yaml',
          config_hash: 'hash-1',
          masked_snapshot: {},
          masked_sections: [],
          validation_status: 'validated',
          captured_at: '2026-05-16T08:10:00Z',
          snapshot_path: '/tmp/profile-snapshot-1.json',
        },
      ],
    } as never);
    mockedGetOhlcvSchedulerStatus.mockResolvedValue({
      config_path: 'config/ohlcv.yaml',
      base_dir: '/tmp/trade-strategy-ai',
      latest_trade_date: '2026-05-23',
      latest_record_count: 120,
      scheduler_started: false,
      scheduler_pre_market: '9:25',
      scheduler_post_close: '17:30',
    } as never);
    mockedRunOhlcvScheduler.mockResolvedValue({
      config_path: 'config/ohlcv.yaml',
      base_dir: '/tmp/trade-strategy-ai',
      pre_market: '9:25',
      post_close: '17:30',
      started: true,
      scheduler_started: true,
    } as never);
    mockedStopOhlcvScheduler.mockResolvedValue({
      config_path: 'config/ohlcv.yaml',
      base_dir: '/tmp/trade-strategy-ai',
      started: false,
      pre_market: '9:25',
      post_close: '17:30',
    } as never);

    renderWithRouter([{ path: '/market/ohlcv', element: <MarketOhlcvWorkspaceShell /> }], ['/market/ohlcv']);

    expect(await screen.findByRole('heading', { name: 'OHLCV 行情' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'OHLCV 调度器' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '启动调度器' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '启动调度器' }));

    await waitFor(() => {
      expect(screen.getByText(/OHLCV 调度器已启动/)).toBeInTheDocument();
      expect(mockedRunOhlcvScheduler).toHaveBeenCalledWith('default', 'config/ohlcv.yaml');
      expect(screen.getByRole('button', { name: '停止调度器' })).toBeInTheDocument();
    });

    mockedGetOhlcvSchedulerStatus.mockResolvedValueOnce({
      config_path: 'config/app.yaml',
      base_dir: '/tmp/trade-strategy-ai',
      latest_trade_date: '2026-05-23',
      latest_record_count: 120,
      scheduler_started: true,
      scheduler_pre_market: '9:25',
      scheduler_post_close: '17:30',
    } as never);

    await user.click(screen.getByRole('button', { name: '停止调度器' }));

    await waitFor(() => {
      expect(screen.getByText(/OHLCV 调度器已停止/)).toBeInTheDocument();
      expect(mockedStopOhlcvScheduler).toHaveBeenCalledWith('default', 'config/ohlcv.yaml');
      expect(screen.getByRole('button', { name: '启动调度器' })).toBeInTheDocument();
    });
  });

  it('submits ohlcv crawl with profile and allows empty limit for full crawl', async () => {
    const user = userEvent.setup();

    mockedListJobs.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [],
    } as never);
    mockedListArtifacts.mockResolvedValue({
      count: 0,
      total: 0,
      skip: 0,
      limit: 8,
      items: [],
    } as never);
    mockedListBenchmarkOptions.mockResolvedValue({
      count: 2,
      items: [
        { symbol: '000300.SH', code: '000300', market: 'CN', name: '沪深300', security_type: 'index' },
        { symbol: '510300.SH', code: '510300', market: 'CN', name: '沪深300ETF', security_type: 'etf' },
      ],
    } as never);
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
          config_path: 'config/ohlcv.yaml',
          config_hash: 'hash-1',
          masked_snapshot: {},
          masked_sections: [],
          validation_status: 'validated',
          captured_at: '2026-05-16T08:10:00Z',
          snapshot_path: '/tmp/profile-snapshot-1.json',
        },
      ],
    } as never);
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-ohlcv-1' },
      job_dir: '/tmp/job-ohlcv-1',
      log_path: '/tmp/job-ohlcv-1/log.txt',
      params_path: '/tmp/job-ohlcv-1/params.json',
      result_path: '/tmp/job-ohlcv-1/result.json',
      artifacts_path: '/tmp/job-ohlcv-1/artifacts',
    } as never);

    renderWithRouter([{ path: '/market/ohlcv', element: <MarketOhlcvWorkspaceShell /> }], ['/market/ohlcv']);

    await user.type(screen.getByLabelText('标的列表（逗号或换行分隔）'), '000001.SZ, 600000.SH');
    await user.click(screen.getByRole('button', { name: '运行 OHLCV 抓取' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'ohlcv-crawl',
          params: expect.objectContaining({
            profile_id: 'default',
            mode: 'incremental',
            symbols: ['000001.SZ', '600000.SH'],
            start_date: expect.any(String),
            end_date: expect.any(String),
          }),
        }),
      );
    });

    const call = mockedCreateJob.mock.calls.find(([arg]) => arg.job_type === 'ohlcv-crawl');
    expect(call?.[0].params).not.toHaveProperty('limit');
  });
});
