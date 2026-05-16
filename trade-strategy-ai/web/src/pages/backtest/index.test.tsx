import { describe, expect, it } from 'vitest';
import { screen } from '@testing-library/react';
import { BacktestPage } from './index';
import { renderWithRouter } from '@/test/test-utils';

describe('BacktestPage', () => {
  it('renders the backtest placeholder page', async () => {
    renderWithRouter([{ path: '/backtest', element: <BacktestPage /> }], ['/backtest']);

    expect(await screen.findByRole('heading', { name: '回测' })).toBeInTheDocument();
    expect(screen.getByText(/V3 预留/)).toBeInTheDocument();
  });
});
