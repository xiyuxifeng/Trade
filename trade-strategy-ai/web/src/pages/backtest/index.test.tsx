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

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
}));

vi.mock('@/lib/api/backtests', () => ({
  downloadBacktestReport: vi.fn(),
  downloadBacktestValidationReport: vi.fn(),
  buildBacktestRunParams: vi.fn((submission) => ({
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    config_path: submission.configPath,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  })),
  buildBacktestValidateRulesParams: vi.fn((submission) => ({
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    config_path: submission.configPath,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  })),
  buildBacktestReproducibilityParams: vi.fn((submission) => ({
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    config_path: submission.configPath,
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

const mockedCreateJob = vi.mocked(createJob);
const mockedDownloadBacktestReport = vi.mocked(downloadBacktestReport);
const mockedDownloadBacktestValidationReport = vi.mocked(downloadBacktestValidationReport);
const mockedGetBacktestResult = vi.mocked(getBacktestResult);
const mockedListBacktestResults = vi.mocked(listBacktestResults);
const mockedListBenchmarkOptions = vi.mocked(listBenchmarkOptions);

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

    expect(await screen.findByRole('heading', { name: '回测参数' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '运行回测' })).toBeInTheDocument();
    expect(screen.getByText('最近结果')).toBeInTheDocument();
    expect(screen.getByText('最近任务')).toBeInTheDocument();
    expect(screen.getByLabelText('交易员 ID')).toHaveValue('');
    expect(screen.getByLabelText('回测模式')).toHaveValue('full');
    expect(screen.getByLabelText('仅使用快照数据')).toBeChecked();
    expect(screen.getByLabelText('评分配置')).toHaveValue('stage5');
    expect(screen.getByLabelText('标的列表')).toHaveValue('');
    expect(screen.getByLabelText('Benchmark 选择')).toHaveValue('000300.SH');

    await waitFor(() => {
      expect(mockedListBacktestResults).toHaveBeenCalled();
    });
    expect((await screen.findAllByText('result-1')).length).toBeGreaterThan(0);
    expect(screen.getByText('最近 fingerprint')).toBeInTheDocument();

    await user.type(screen.getByLabelText('交易员 ID'), 'trader_a');
    await user.type(screen.getByLabelText('策略版本 ID'), 'sv-1');
    await user.type(screen.getByLabelText('标的列表'), '000001.SZ, 000002.SZ');
    await user.type(screen.getByLabelText('配置路径'), 'config/app.yaml');
    await user.click(screen.getByRole('button', { name: '运行回测' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'backtest-run',
          params: expect.objectContaining({
            trader_id: 'trader_a',
            strategy_version_id: 'sv-1',
            benchmark_symbol: '000300.SH',
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
            symbols: ['000001.SZ', '000002.SZ'],
            benchmark_symbol: '000300.SH',
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
            symbols: ['000001.SZ', '000002.SZ'],
            benchmark_symbol: '000300.SH',
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
