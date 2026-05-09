import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { MarketStatePage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { buildMarketState } from '@/lib/api/persona';

vi.mock('@/lib/api/persona', () => ({
  buildMarketState: vi.fn(),
  buildSampleClusters: vi.fn(),
}));

const mockedBuildMarketState = vi.mocked(buildMarketState);

describe('MarketStatePage', () => {
  it('builds a market state snapshot from the workbench', async () => {
    const user = userEvent.setup();
    mockedBuildMarketState.mockResolvedValue({
      config_path: 'config/app.yaml',
      base_dir: '/tmp/project',
      market_state_path: '/tmp/project/data/processed/persona/market_state.json',
      snapshot_path: '/tmp/project/data/processed/persona/market_state.json',
      source: 'cache',
      market_state: { state: 'bull' },
    });

    renderWithRouter([{ path: '/market-state', element: <MarketStatePage /> }], ['/market-state']);

    expect(await screen.findByText('Market State')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Build MarketState' }));

    await waitFor(() => {
      expect(mockedBuildMarketState).toHaveBeenCalledWith({
        as_of: expect.any(String),
        from_akshare: false,
        cache_csv: true,
      });
    });
    expect(
      await screen.findByText('/tmp/project/data/processed/persona/market_state.json', { selector: 'p' }),
    ).toBeInTheDocument();
  });
});
