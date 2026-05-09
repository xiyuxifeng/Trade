import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  downloadBacktestReport,
  downloadBacktestValidationReport,
  getBacktestResult,
  listBacktestResults,
} from './backtests';

describe('backtests api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it('calls the root backtest_results endpoint and sends the stored API key', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: 'success',
        count: 0,
        total: 0,
        skip: 0,
        limit: 10,
        items: [],
      }),
    });
    vi.stubGlobal('fetch', fetchMock);
    window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');

    await listBacktestResults({ skip: 0, limit: 10 });

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe('/backtest_results/?skip=0&limit=10');
    expect((init?.headers as Headers).get('Accept')).toBe('application/json');
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('loads a backtest result and markdown reports from the root API', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'success',
          item: {
            request_trader_id: 'trader_a',
            request_date_from: '2026-05-01',
            request_date_to: '2026-05-05',
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
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: async () => '# Backtest Report',
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: async () => '# Rule Validation Report',
      });
    vi.stubGlobal('fetch', fetchMock);

    await getBacktestResult('result-1');
    await downloadBacktestReport('result-1');
    await downloadBacktestValidationReport('result-1');

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/backtest_results/result-1', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/backtest_results/result-1/report', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/backtest_results/result-1/validate_rules', expect.any(Object));
  });
});
