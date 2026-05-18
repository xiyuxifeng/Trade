import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { RegimeBacktestReportPage } from './RegimeBacktestReportPage';
import { renderWithRouter } from '@/test/test-utils';
import { downloadBacktestReport, getBacktestResult, listBacktestResults } from '@/lib/api/backtests';

vi.mock('@/lib/api/backtests', () => ({
  downloadBacktestReport: vi.fn(),
  getBacktestResult: vi.fn(),
  listBacktestResults: vi.fn(),
}));

const mockedDownloadBacktestReport = vi.mocked(downloadBacktestReport);
const mockedGetBacktestResult = vi.mocked(getBacktestResult);
const mockedListBacktestResults = vi.mocked(listBacktestResults);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('RegimeBacktestReportPage', () => {
  it('renders regime-aware backtest breakdowns and markdown report', async () => {
    mockedListBacktestResults.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 10,
      items: [
        {
          result_id: 'result-1',
          trader_id: 'trader_a',
          date_from: '2026-05-01',
          date_to: '2026-05-05',
          benchmark_symbol: '000300.SH',
          regime_version: 'market-regime-v3',
          source_feature_version: 'market-regime-features-v3',
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
        regime_version: 'market-regime-v3',
        source_feature_version: 'market-regime-features-v3',
        result_version: '1.0',
        summary: {
          total_days: 5,
          total_trades: 3,
          valid_trades: 2,
          skipped_trades: 1,
          win_rate: 0.67,
          avg_return_pct: 0.12,
        },
        records: [],
        regime_metrics: [
          {
            regime_label: 'trend_up',
            sample_count: 10,
            win_trades: 7,
            loss_trades: 3,
            win_rate: 0.7,
            avg_return: 0.03,
            avg_win_return: 0.05,
            avg_loss_return: -0.01,
            max_drawdown: 0.08,
            profit_factor: 1.8,
            confidence: 0.86,
            low_sample: false,
          },
        ],
        rule_regime_metrics: {
          rule_001: [
            {
              regime_label: 'trend_up',
              sample_count: 10,
              win_trades: 7,
              loss_trades: 3,
              win_rate: 0.7,
              avg_return: 0.03,
              avg_win_return: 0.05,
              avg_loss_return: -0.01,
              max_drawdown: 0.08,
              profit_factor: 1.8,
              confidence: 0.86,
              low_sample: false,
            },
          ],
        },
      },
    });
    mockedDownloadBacktestReport.mockResolvedValue('# Regime Backtest Report');

    renderWithRouter([{ path: '/backtest/regime', element: <RegimeBacktestReportPage /> }], ['/backtest/regime']);

    expect(await screen.findByRole('heading', { name: 'Regime Backtest Report' })).toBeInTheDocument();
    expect(await screen.findByText('market-regime-v3')).toBeInTheDocument();
    expect(screen.getByText('market-regime-features-v3')).toBeInTheDocument();
    expect((await screen.findAllByText('trend_up')).length).toBeGreaterThan(0);
    expect(screen.getByText('rule_001')).toBeInTheDocument();
    expect(mockedDownloadBacktestReport).toHaveBeenCalledWith('result-1');
  });
});
