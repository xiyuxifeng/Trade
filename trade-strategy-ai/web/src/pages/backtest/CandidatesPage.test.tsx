import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import { listTraderOptions } from '@/lib/api/traders';
import { CandidatesPage as BacktestCandidatesPage } from './CandidatesPage';

vi.mock('@/features/strategy-workspace', () => ({
  StrategyWorkspaceCandidate: ({ traderId, selectedVersion }: { traderId: string; selectedVersion: { version_id: string } | null }) => (
    <div data-testid="candidate-workspace">
      {traderId}:{selectedVersion?.version_id ?? 'none'}
    </div>
  ),
}));

vi.mock('@/lib/api/traders', () => ({
  listTraderOptions: vi.fn(),
}));

vi.mock('@/lib/api/strategyStudio', () => ({
  listStrategyVersions: vi.fn(),
  getStrategyVersion: vi.fn(),
}));

const mockedListTraderOptions = vi.mocked(listTraderOptions);
const mockedListStrategyVersions = vi.mocked(listStrategyVersions);
const mockedGetStrategyVersion = vi.mocked(getStrategyVersion);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('BacktestCandidatesPage', () => {
  it('renders the standalone candidate page and keeps the backtest page light', async () => {
    mockedListTraderOptions.mockResolvedValue({
      status: 'success',
      count: 2,
      items: ['trader_a', 'trader_b'],
    });
    mockedListStrategyVersions.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 100,
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
      ],
    });
    mockedGetStrategyVersion.mockResolvedValue({
      status: 'success',
      item: {
        version_id: 'sv-1',
        trader_id: 'trader_a',
        strategy_date: '2026-05-09',
        status: 'released',
        version_type: 'manual',
        parent_version_id: null,
        recommendations: [],
        source_article_ids: [],
        evidence_refs: [],
        notes: null,
        released_at: null,
        rules_snapshot: [],
        regime_selection: null,
      },
    } as never);

    renderWithRouter([{ path: '/backtest/candidates', element: <BacktestCandidatesPage /> }], ['/backtest/candidates']);

    expect(await screen.findByRole('heading', { name: '候选版本' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回回测与画像' })).toHaveAttribute('href', '/backtest');
    expect(screen.getByText('候选版本生成与审核放在独立页面中，回测页只保留轻入口。')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockedListTraderOptions).toHaveBeenCalledWith({ source: 'strategy' });
      expect(mockedListStrategyVersions).toHaveBeenCalledWith({ skip: 0, limit: 100 });
      expect(mockedGetStrategyVersion).toHaveBeenCalledWith('sv-1');
    });

    expect(screen.getByLabelText('交易员 ID')).toHaveValue('trader_a');
    expect(screen.getByLabelText('规则版本 ID')).toHaveValue('sv-1');
    await waitFor(() => {
      expect(screen.getByTestId('candidate-workspace')).toHaveTextContent('trader_a:sv-1');
    });
  });
});
