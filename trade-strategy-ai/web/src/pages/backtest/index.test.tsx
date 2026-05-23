import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { BacktestPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { createJob } from '@/lib/api/jobs';
import {
  downloadBacktestReport,
  downloadBacktestValidationReport,
  getBacktestResult,
  listBacktestResults,
} from '@/lib/api/backtests';
import { listBenchmarkOptions } from '@/lib/api/market';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { listTraderOptions } from '@/lib/api/traders';
import { listStrategyVersions } from '@/lib/api/strategyStudio';

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
}));

vi.mock('@/lib/api/backtests', () => ({
  downloadBacktestReport: vi.fn(),
  downloadBacktestValidationReport: vi.fn(),
  buildBacktestRunParams: vi.fn((submission) => ({
    profile_id: submission.profileId,
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    config_path: submission.configPath || undefined,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  })),
  buildBacktestValidateRulesParams: vi.fn((submission) => ({
    profile_id: submission.profileId,
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    config_path: submission.configPath || undefined,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  })),
  buildBacktestReproducibilityParams: vi.fn((submission) => ({
    profile_id: submission.profileId,
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    config_path: submission.configPath || undefined,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  })),
  getBacktestResult: vi.fn(),
  listBacktestResults: vi.fn(),
}));
vi.mock('@/lib/api/market', () => ({
  listBenchmarkOptions: vi.fn(),
}));
vi.mock('@/lib/api/profiles', () => ({
  getProfile: vi.fn(),
  listProfiles: vi.fn(),
}));
vi.mock('@/lib/api/traders', () => ({
  listTraderOptions: vi.fn(),
}));
vi.mock('@/lib/api/strategyStudio', () => ({
  listStrategyVersions: vi.fn(),
}));

const mockedCreateJob = vi.mocked(createJob);
const mockedDownloadBacktestReport = vi.mocked(downloadBacktestReport);
const mockedDownloadBacktestValidationReport = vi.mocked(downloadBacktestValidationReport);
const mockedGetBacktestResult = vi.mocked(getBacktestResult);
const mockedListBacktestResults = vi.mocked(listBacktestResults);
const mockedListBenchmarkOptions = vi.mocked(listBenchmarkOptions);
const mockedGetProfile = vi.mocked(getProfile);
const mockedListProfiles = vi.mocked(listProfiles);
const mockedListTraderOptions = vi.mocked(listTraderOptions);
const mockedListStrategyVersions = vi.mocked(listStrategyVersions);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('BacktestPage', () => {
  it('renders the formal backtest workbench and submits the canonical contract', async () => {
    const user = userEvent.setup();

    mockedListBacktestResults.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 8,
      items: [
        {
          result_id: 'result-1',
          trader_id: 'trader_a',
          date_from: '2026-05-01',
          date_to: '2026-05-05',
          benchmark_symbol: '000300.SH',
          summary: {
            total_days: 5,
            total_trades: 3,
            valid_trades: 2,
            skipped_trades: 1,
            win_rate: 0.67,
            avg_return_pct: 0.12,
          },
        },
      ],
    });
    mockedGetBacktestResult.mockResolvedValue({
      status: 'success',
      item: {
        request_trader_id: 'trader_a',
        request_date_from: '2026-05-01',
        request_date_to: '2026-05-05',
        benchmark_symbol: '000300.SH',
        result_version: '1.0',
        summary: {
          total_days: 5,
          total_trades: 3,
          valid_trades: 2,
          skipped_trades: 1,
          win_rate: 0.67,
          avg_return_pct: 0.12,
        },
        records: [
          {
            trade_date: '2026-05-01',
            trader_id: 'trader_a',
            strategy_version_id: 'sv-1',
            symbol: '000001.SZ',
            status: 'closed',
            entry_price: 10,
            exit_price: 11,
            entry_date: '2026-05-01',
            exit_date: '2026-05-02',
            return_pct: 0.1,
            mfe: 0.12,
            mae: -0.02,
            volume: 100,
            is_valid_lot_size: true,
            skip_reason: null,
            evidence_refs: ['e-1'],
          },
        ],
      },
    });
    mockedDownloadBacktestReport.mockResolvedValue('# Backtest Report');
    mockedDownloadBacktestValidationReport.mockResolvedValue('# Rule Validation Report');
    mockedListBenchmarkOptions.mockResolvedValue({
      count: 2,
      items: [
        { symbol: '000300.SH', code: '000300', market: 'SH', name: '沪深300', security_type: 'index' },
        { symbol: '000905.SH', code: '000905', market: 'SH', name: '中证500', security_type: 'index' },
      ],
    });
    mockedListProfiles.mockResolvedValue({
      count: 2,
      total: 2,
      skip: 0,
      limit: 50,
      items: [
        {
          profile_id: 'default',
          name: 'Default Profile',
          environment: 'production',
          version: 3,
          sections: {},
          secret_refs: {},
          validation_status: 'validated',
          created_by: 'system',
          created_at: '2026-05-01T08:00:00Z',
          updated_at: '2026-05-20T08:00:00Z',
          archived_at: null,
        },
        {
          profile_id: 'alt',
          name: 'Alternative Profile',
          environment: 'production',
          version: 1,
          sections: {},
          secret_refs: {},
          validation_status: 'validated',
          created_by: 'system',
          created_at: '2026-05-01T08:00:00Z',
          updated_at: '2026-05-18T08:00:00Z',
          archived_at: null,
        },
      ],
    });
    mockedListTraderOptions.mockResolvedValue({
      status: 'success',
      count: 2,
      items: ['trader_a', 'trader_b'],
    });
    mockedGetProfile.mockImplementation(async (profileId) => {
      if (profileId === 'default') {
        return {
          profile: {
            profile_id: 'default',
            name: 'Default Profile',
            environment: 'production',
            version: 3,
            sections: {},
            secret_refs: {},
            validation_status: 'validated',
            created_by: 'system',
            created_at: '2026-05-01T08:00:00Z',
            updated_at: '2026-05-20T08:00:00Z',
            archived_at: null,
          },
          linked_jobs: [],
          snapshots: [
            {
              snapshot_id: 'snapshot-1',
              profile_id: 'default',
              job_id: 'job-1',
              source: 'job:job-1',
              config_path: 'config/profile-default.yaml',
              config_hash: 'hash-1',
              masked_snapshot: {},
              masked_sections: [],
              validation_status: 'validated',
              captured_at: '2026-05-20T08:00:00Z',
              snapshot_path: '/tmp/profile-default.json',
            },
          ],
        };
      }
      return {
        profile: {
          profile_id: 'alt',
          name: 'Alternative Profile',
          environment: 'production',
          version: 1,
          sections: {},
          secret_refs: {},
          validation_status: 'validated',
          created_by: 'system',
          created_at: '2026-05-01T08:00:00Z',
          updated_at: '2026-05-18T08:00:00Z',
          archived_at: null,
        },
        linked_jobs: [],
        snapshots: [],
      };
    });
    mockedListStrategyVersions.mockResolvedValue({
      status: 'success',
      count: 2,
      total: 2,
      skip: 0,
      limit: 200,
      items: [
        {
          version_id: 'sv-1',
          trader_id: 'trader_a',
          strategy_date: '2026-05-09',
          status: 'released',
          version_type: 'manual',
          parent_version_id: null,
          recommendations_count: 0,
          source_article_ids_count: 0,
          released_at: null,
          has_rules_snapshot: true,
        },
        {
          version_id: 'sv-2',
          trader_id: 'trader_b',
          strategy_date: '2026-05-10',
          status: 'released',
          version_type: 'manual',
          parent_version_id: null,
          recommendations_count: 0,
          source_article_ids_count: 0,
          released_at: null,
          has_rules_snapshot: true,
        },
      ],
    });
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: {
        id: 'job-1',
        job_type: 'backtest-run',
        result: {
          payload: {
            fingerprint: 'f'.repeat(64),
          },
        },
      },
      job_dir: '/tmp/job-1',
      log_path: '/tmp/job-1/job.log',
      params_path: '/tmp/job-1/params.json',
      result_path: '/tmp/job-1/result.json',
      artifacts_path: '/tmp/job-1/artifacts.json',
    } as unknown as Awaited<ReturnType<typeof createJob>>);

    renderWithRouter([{ path: '/backtest', element: <BacktestPage /> }], ['/backtest']);

    expect(screen.getByRole('link', { name: '进入 Regime 回测' })).toHaveAttribute('href', '/backtest/regime');
    expect(screen.getByRole('link', { name: '打开任务中心' })).toHaveAttribute('href', '/jobs');
    expect(await screen.findByRole('heading', { name: '回测参数' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '运行回测' })).toBeInTheDocument();
    expect(screen.getByText('最近结果')).toBeInTheDocument();
    expect(screen.getByText('最近任务')).toBeInTheDocument();
    const profileSelect = await screen.findByLabelText('Profile');
    await waitFor(() => {
      expect(profileSelect).toHaveValue('default');
      expect(screen.getByLabelText('交易员 ID')).toHaveValue('trader_a');
      expect(screen.getByLabelText('策略版本 ID')).toHaveValue('sv-1');
    });
    expect(screen.getByLabelText('回测模式')).toHaveValue('full');
    expect(screen.getByText('仅使用快照数据')).toBeInTheDocument();
    expect(screen.getByText('统一回测评分口径')).toBeInTheDocument();
    expect(
      screen.getByText('按 MFE / MAE / return_pct 计算，并包含 T+1 与涨跌停约束。当前为固定口径，不提供切换。'),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('标的列表')).toHaveValue('');
    expect(screen.getByLabelText('Benchmark 选择')).toHaveValue('000300.SH');
    expect(screen.queryByLabelText('配置路径')).not.toBeInTheDocument();
    expect(screen.queryByText('当前 Profile')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(mockedListBacktestResults).toHaveBeenCalled();
      expect(mockedListProfiles).toHaveBeenCalled();
      expect(mockedListTraderOptions).toHaveBeenCalledWith({ source: 'strategy' });
      expect(mockedListStrategyVersions).toHaveBeenCalledWith({ skip: 0, limit: 100 });
      expect(mockedGetProfile).toHaveBeenCalledWith('default');
    });
    expect((await screen.findAllByText('result-1')).length).toBeGreaterThan(0);
    expect(screen.getByText('最近 fingerprint')).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText('Profile'), 'alt');
    await waitFor(() => {
      expect(mockedGetProfile).toHaveBeenCalledWith('alt');
    });
    await user.selectOptions(screen.getByLabelText('Profile'), 'default');
    await user.selectOptions(screen.getByLabelText('交易员 ID'), 'trader_a');
    await user.selectOptions(screen.getByLabelText('策略版本 ID'), 'sv-1');
    await user.type(screen.getByLabelText('标的列表'), '000001.SZ, 000002.SZ');
    await user.click(screen.getByRole('button', { name: '运行回测' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'backtest-run',
          params: expect.objectContaining({
            profile_id: 'default',
            trader_id: 'trader_a',
            strategy_version_id: 'sv-1',
            benchmark_symbol: '000300.SH',
            config_path: 'config/profile-default.yaml',
            symbols: ['000001.SZ', '000002.SZ'],
            use_snapshot_only: true,
            scoring_profile: 'stage5',
          }),
        }),
      );
    });

    expect(await screen.findByText(/f{16}/)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '验证规则' }));
    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'backtest-validate-rules',
          params: expect.objectContaining({
            profile_id: 'default',
            symbols: ['000001.SZ', '000002.SZ'],
            benchmark_symbol: '000300.SH',
            config_path: 'config/profile-default.yaml',
            use_snapshot_only: true,
            scoring_profile: 'stage5',
          }),
        }),
      );
    });

    await user.click(screen.getByRole('button', { name: '可复现性检查' }));
    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'backtest-reproducibility-check',
          params: expect.objectContaining({
            profile_id: 'default',
            symbols: ['000001.SZ', '000002.SZ'],
            benchmark_symbol: '000300.SH',
            config_path: 'config/profile-default.yaml',
            use_snapshot_only: true,
            scoring_profile: 'stage5',
          }),
        }),
      );
    });
  });

  it('shows a usable empty state when no recent results exist', async () => {
    mockedListBacktestResults.mockResolvedValue({
      status: 'success',
      count: 0,
      total: 0,
      skip: 0,
      limit: 8,
      items: [],
    });

    renderWithRouter([{ path: '/backtest', element: <BacktestPage /> }], ['/backtest']);

    expect(await screen.findByText('当前筛选范围内暂无回测结果。')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '重置查询' }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole('button', { name: '最近 30 天' }).length).toBeGreaterThan(0);
  });
});
