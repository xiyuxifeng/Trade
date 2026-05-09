import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { MarketPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { getOhlcv, listSymbols } from '@/lib/api/market';

vi.mock('@/lib/api/market', () => ({
  getOhlcv: vi.fn(),
  listSymbols: vi.fn(),
}));

const mockedListSymbols = vi.mocked(listSymbols);
const mockedGetOhlcv = vi.mocked(getOhlcv);

describe('MarketPage', () => {
  it('renders a candlestick chart for the selected symbol and date range', async () => {
    const user = userEvent.setup();

    mockedListSymbols.mockResolvedValue({
      count: 2,
      items: ['AAA', 'BBB'],
    });
    mockedGetOhlcv.mockResolvedValue({
      symbol: 'AAA',
      start_date: '2026-04-01',
      end_date: '2026-04-03',
      count: 3,
      items: [
        {
          time: '2026-04-01T00:00:00Z',
          open: 10,
          high: 13,
          low: 9,
          close: 12,
          volume: 1200,
          turnover: 12000,
        },
        {
          time: '2026-04-02T00:00:00Z',
          open: 12,
          high: 14,
          low: 11,
          close: 11.5,
          volume: 1500,
          turnover: 16500,
        },
        {
          time: '2026-04-03T00:00:00Z',
          open: 11.5,
          high: 15,
          low: 11,
          close: 14,
          volume: 1800,
          turnover: 25200,
        },
      ],
    });

    renderWithRouter([{ path: '/market', element: <MarketPage /> }], ['/market']);

    await waitFor(() => {
      expect(mockedListSymbols).toHaveBeenCalled();
    });

    await user.click(await screen.findByRole('button', { name: 'AAA' }));
    await user.click(screen.getByRole('button', { name: '查询 OHLCV' }));

    expect(await screen.findByText('K线图')).toBeInTheDocument();
    expect(screen.getByLabelText('K线图')).toBeInTheDocument();
    expect(screen.getAllByText('AAA · 3 rows').length).toBeGreaterThan(0);
  });
});
