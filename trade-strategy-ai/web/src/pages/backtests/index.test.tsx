import dayjs from 'dayjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { BacktestsPage } from './index';
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
  })),
  buildBacktestValidateRulesParams: vi.fn((submission) => ({
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    config_path: submission.configPath,
  })),
  buildBacktestReproducibilityParams: vi.fn((submission) => ({
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    benchmark_symbol: submission.benchmarkSymbol || undefined,
    mode: submission.mode,
    config_path: submission.configPath,
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

describe('BacktestsPage', () => {
  it('submits backtest jobs and renders the selected result details', async () => {
    const user = userEvent.setup();
    const today = dayjs().format('YYYY-MM-DD');
    const thirtyDaysAgo = dayjs().subtract(30, 'day').format('YYYY-MM-DD');

    mockedListBacktestResults.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
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
      count: 1,
      items: [
        { symbol: '000300.SH', code: '000300', market: 'SH', name: '沪深300', security_type: 'index' },
      ],
    });
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-1', job_type: 'backtest-run' },
      job_dir: '/tmp/job-1',
      log_path: '/tmp/job-1/job.log',
      params_path: '/tmp/job-1/params.json',
      result_path: '/tmp/job-1/result.json',
      artifacts_path: '/tmp/job-1/artifacts.json',
    } as Awaited<ReturnType<typeof createJob>>);

    renderWithRouter([{ path: '/backtests', element: <BacktestsPage /> }], ['/backtests']);

    await waitFor(() => {
      expect(mockedListBacktestResults).toHaveBeenCalled();
    });

    expect(await screen.findByText('回测中心')).toBeInTheDocument();
    expect(await screen.findByText('result-1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重置筛选' })).toBeInTheDocument();
    expect(screen.getByDisplayValue('沪深300 (000300.SH)')).toBeInTheDocument();
    expect(await screen.findByText('有效交易')).toBeInTheDocument();
    expect(await screen.findByText('跳过交易')).toBeInTheDocument();

    expect(screen.getByLabelText('开始日期')).toHaveValue(thirtyDaysAgo);
    expect(screen.getByLabelText('结束日期')).toHaveValue(today);
    expect(screen.getByDisplayValue('沪深300 (000300.SH)')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '7天' }));
    expect(screen.getByLabelText('开始日期')).toHaveValue(dayjs(today).subtract(7, 'day').format('YYYY-MM-DD'));
    expect(screen.getByLabelText('结束日期')).toHaveValue(today);

    await user.click(screen.getByRole('button', { name: '重置筛选' }));
    expect(screen.getByLabelText('开始日期')).toHaveValue(thirtyDaysAgo);
    expect(screen.getByLabelText('结束日期')).toHaveValue(today);

    await user.type(screen.getByLabelText('交易员 ID'), 'trader_a');

    await user.click(screen.getByRole('button', { name: '运行回测' }));
    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'backtest-run',
          params: expect.objectContaining({ benchmark_symbol: '000300.SH' }),
        }),
      );
    });

    await user.click(screen.getByRole('button', { name: '验证规则' }));
    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({ job_type: 'backtest-validate-rules' }),
      );
    });

    await user.click(screen.getByRole('button', { name: '复现性检查' }));
    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({ job_type: 'backtest-reproducibility-check' }),
      );
    });

    await waitFor(() => {
      expect(mockedDownloadBacktestReport).toHaveBeenCalled();
      expect(mockedDownloadBacktestValidationReport).toHaveBeenCalled();
    });

    await user.click(screen.getByRole('button', { name: '报告' }));
    expect(await screen.findByRole('heading', { name: 'Backtest Report' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '验真' }));
    expect(await screen.findByRole('heading', { name: 'Rule Validation Report' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '摘要' }));
    expect(await screen.findByTestId('backtest-detail-summary')).toHaveTextContent('总天数');
    await user.click(screen.getByRole('button', { name: 'JSON' }));
    expect(await screen.findByTestId('backtest-detail-json')).toHaveTextContent('"result_version"');

    expect(screen.getByText('摘要')).toBeInTheDocument();
    expect(screen.getByText('记录')).toBeInTheDocument();
    expect(screen.getByText('报告')).toBeInTheDocument();
    expect(screen.getByText('验真')).toBeInTheDocument();
    expect(screen.getByText('JSON')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '报告' }));
    expect(screen.getByRole('button', { name: '下载原文' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '预览' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '原文' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '验真' }));
    expect(screen.getByRole('button', { name: '下载原文' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '预览' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '原文' })).toBeInTheDocument();
  });

  it('shows an actionable empty state when the filter window has no results', async () => {
    const user = userEvent.setup();
    const today = dayjs().format('YYYY-MM-DD');
    const thirtyDaysAgo = dayjs().subtract(30, 'day').format('YYYY-MM-DD');

    mockedListBacktestResults.mockResolvedValue({
      status: 'success',
      count: 0,
      total: 0,
      skip: 0,
      limit: 50,
      items: [],
    });

    renderWithRouter([{ path: '/backtests', element: <BacktestsPage /> }], ['/backtests']);

    await waitFor(() => {
      expect(mockedListBacktestResults).toHaveBeenCalled();
    });

    expect(await screen.findByText('当前筛选范围内暂无回测结果。')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: '重置筛选' })).toHaveLength(2);
    expect(screen.getByRole('button', { name: '最近 30 天' })).toBeInTheDocument();

    await user.type(screen.getByLabelText('交易员 ID'), 'trader_b');
    await user.click(screen.getAllByRole('button', { name: '重置筛选' })[1]);

    expect(screen.getByLabelText('交易员 ID')).toHaveValue('');
    expect(screen.getByLabelText('开始日期')).toHaveValue(thirtyDaysAgo);
    expect(screen.getByLabelText('结束日期')).toHaveValue(today);
  });
});
