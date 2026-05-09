import { describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { SignalsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listSignals } from '@/lib/api/signals';

vi.mock('@/lib/api/signals', () => ({
  listSignals: vi.fn(),
}));

const mockedListSignals = vi.mocked(listSignals);

describe('SignalsPage', () => {
  it('renders the signals page and the summary table', async () => {
    mockedListSignals.mockResolvedValue({
      config_path: 'config/app.yaml',
      base_dir: '/tmp/project',
      count: 1,
      signals: [
        {
          signal_id: 'signal-1',
          symbol: '000001.SZ',
          side: 'buy',
          confidence: 0.93,
          timestamp: '2026-05-09T09:25:00Z',
          trader_id: 'trader_a',
          strategy_version_id: 'version-1',
          context: { trend: 'up' },
          context_summary: 'trend=up',
        },
      ],
    });

    renderWithRouter([{ path: '/signals', element: <SignalsPage /> }], ['/signals']);

    expect(await screen.findByText('Signals')).toBeInTheDocument();
    await waitFor(() => {
      expect(mockedListSignals).toHaveBeenCalledWith({
        symbol: undefined,
        since: expect.any(String),
        limit: 20,
      });
    });
    expect(await screen.findByText('signal-1', { selector: 'td' })).toBeInTheDocument();
    expect(await screen.findByText('trend=up', { selector: 'td' })).toBeInTheDocument();
    expect(await screen.findByText('trend=up', { selector: 'p' })).toBeInTheDocument();
  });
});
