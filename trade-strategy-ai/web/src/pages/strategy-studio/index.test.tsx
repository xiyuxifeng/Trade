import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { StrategyStudioPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import {
  adviseRuleValidations,
  createCandidateVersion,
  getStrategyRule,
  getStrategyVersion,
  listStrategyRules,
  listStrategyVersions,
  reviewStrategyRule,
  reviewStrategyRuleBatch,
} from '@/lib/api/strategyStudio';

vi.mock('@/lib/api/strategyStudio', () => ({
  adviseRuleValidations: vi.fn(),
  createCandidateVersion: vi.fn(),
  getStrategyRule: vi.fn(),
  getStrategyVersion: vi.fn(),
  listStrategyRules: vi.fn(),
  listStrategyVersions: vi.fn(),
  reviewStrategyRule: vi.fn(),
  reviewStrategyRuleBatch: vi.fn(),
}));

const mockedAdviseRuleValidations = vi.mocked(adviseRuleValidations);
const mockedCreateCandidateVersion = vi.mocked(createCandidateVersion);
const mockedGetStrategyRule = vi.mocked(getStrategyRule);
const mockedGetStrategyVersion = vi.mocked(getStrategyVersion);
const mockedListStrategyRules = vi.mocked(listStrategyRules);
const mockedListStrategyVersions = vi.mocked(listStrategyVersions);
const mockedReviewStrategyRule = vi.mocked(reviewStrategyRule);
const mockedReviewStrategyRuleBatch = vi.mocked(reviewStrategyRuleBatch);

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('StrategyStudioPage', () => {
  it('renders a three-panel workspace and submits candidate and review actions', async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);

    mockedListStrategyVersions.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 20,
      items: [
        {
          version_id: 'trader_a_2026-05-09_released',
          trader_id: 'trader_a',
          strategy_date: '2026-05-09',
          status: 'released',
          version_type: 'manual',
          parent_version_id: null,
          recommendations_count: 1,
          source_article_ids_count: 2,
          released_at: '2026-05-09T10:30:00Z',
          has_rules_snapshot: true,
        },
      ],
    });
    mockedGetStrategyVersion.mockResolvedValue({
      status: 'success',
      item: {
        version_id: 'trader_a_2026-05-09_released',
        trader_id: 'trader_a',
        strategy_date: '2026-05-09',
        status: 'released',
        version_type: 'manual',
        parent_version_id: null,
        recommendations: [
          {
            symbol: '000001.SZ',
            decision: 'buy',
            confidence: 0.91,
            entry_price: 10,
            target_price: 11.5,
            stop_loss_price: 9.2,
            volume: 100,
            rationale: 'trend confirmed',
            evidence_refs: ['evidence-1'],
          },
        ],
        source_article_ids: ['article-1', 'article-2'],
        evidence_refs: ['evidence-1'],
        notes: 'version notes',
        released_at: '2026-05-09T10:30:00Z',
        rules_snapshot: [
          { rule_id: 'rule-1', condition: 'price above moving average', action: 'buy' },
        ],
      },
    });
    mockedListStrategyRules.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 20,
      items: [
        {
          rule_id: 'rule-1',
          source_type: 'standalone',
          rule_type: 'breakout',
          instrument_focus: 'stock',
          mapping_status: 'unmapped',
          review_status: 'pending',
          initial_confidence: 0.61,
          validated_confidence: null,
          backtest_result: { run_id: 'run-1' },
          backtest_hits: 13,
          backtest_misses: 7,
          backtest_samples: 20,
          mapped: false,
          created_at: '2026-05-08T12:00:00Z',
        },
      ],
    });
    mockedGetStrategyRule.mockResolvedValue({
      status: 'success',
      item: {
        rule_id: 'rule-1',
        source_type: 'standalone',
        rule_type: 'breakout',
        instrument_focus: 'stock',
        mapping_status: 'unmapped',
        review_status: 'pending',
        initial_confidence: 0.61,
        validated_confidence: null,
        backtest_result: { run_id: 'run-1' },
        backtest_hits: 13,
        backtest_misses: 7,
        backtest_samples: 20,
        mapped: false,
        created_at: '2026-05-08T12:00:00Z',
        id: '11111111-1111-1111-1111-111111111111',
        source_article_ids: ['article-1'],
        extraction_layer: {
          raw_text: 'price above moving average',
          mapped_condition: null,
        },
        mapped_by: null,
        mapped_at: null,
        reviewed_by: null,
        reviewed_at: null,
        backtest_triggered_at: '2026-05-09T11:30:00Z',
        used_in_prediction: true,
        prediction_count: 3,
        last_used_at: '2026-05-09T12:00:00Z',
        updated_at: '2026-05-09T12:30:00Z',
      },
    });
    mockedAdviseRuleValidations.mockResolvedValue({
      count: 1,
      rule_ids: ['rule-1'],
    } as Awaited<ReturnType<typeof adviseRuleValidations>>);
    mockedCreateCandidateVersion.mockResolvedValue({
      status: 'success',
      item: {
        version_id: 'trader_a_2026-05-09_candidate_parent123',
        trader_id: 'trader_a',
        strategy_date: '2026-05-09',
        status: 'draft',
        version_type: 'candidate',
        parent_version_id: 'trader_a_2026-05-09_released',
        recommendations: [],
        source_article_ids: [],
        evidence_refs: [],
        notes: 'version notes',
        released_at: null,
        rules_snapshot: [],
      },
    } as Awaited<ReturnType<typeof createCandidateVersion>>);
    mockedReviewStrategyRule.mockResolvedValue({ ok: true } as Awaited<ReturnType<typeof reviewStrategyRule>>);
    mockedReviewStrategyRuleBatch.mockResolvedValue({ ok: true } as Awaited<ReturnType<typeof reviewStrategyRuleBatch>>);

    renderWithRouter([{ path: '/strategy-studio', element: <StrategyStudioPage /> }], ['/strategy-studio']);

    await waitFor(() => {
      expect(mockedListStrategyVersions).toHaveBeenCalled();
      expect(mockedListStrategyRules).toHaveBeenCalled();
    });

    expect(await screen.findByRole('heading', { level: 1, name: 'Strategy Studio' })).toBeInTheDocument();
    expect(await screen.findByText('trader_a_2026-05-09_released')).toBeInTheDocument();
    expect(await screen.findByText('rule-1')).toBeInTheDocument();
    expect(screen.getByText('Candidate generation')).toBeInTheDocument();
    expect(screen.getByText('Validation advice')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Generate candidate' }));
    await waitFor(() => {
      expect(mockedCreateCandidateVersion).toHaveBeenCalledWith(
        expect.objectContaining({
          parent_version_id: 'trader_a_2026-05-09_released',
          trader_id: 'trader_a',
          strategy_date: '2026-05-09',
          notes: 'version notes',
        }),
      );
    });

    await user.click(screen.getByRole('button', { name: 'Run advice' }));
    await waitFor(() => {
      expect(mockedAdviseRuleValidations).toHaveBeenCalled();
    });

    await user.click(screen.getByRole('button', { name: 'Submit review' }));
    await waitFor(() => {
      expect(mockedReviewStrategyRule).toHaveBeenCalledWith(
        'rule-1',
        expect.objectContaining({
          decision: 'approve',
          force: false,
          reviewed_by: 'web',
        }),
      );
    });

    await user.click(screen.getByRole('button', { name: 'Batch review' }));
    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalled();
      expect(mockedReviewStrategyRuleBatch).toHaveBeenCalledWith(
        expect.objectContaining({
          decision: 'approve',
          status: 'pending',
          limit: 25,
          force: false,
          reviewed_by: 'web',
        }),
      );
    });
  });

  it('shows empty states when there are no versions or rules', async () => {
    mockedListStrategyVersions.mockResolvedValue({
      status: 'success',
      count: 0,
      total: 0,
      skip: 0,
      limit: 20,
      items: [],
    });
    mockedListStrategyRules.mockResolvedValue({
      status: 'success',
      count: 0,
      total: 0,
      skip: 0,
      limit: 20,
      items: [],
    });

    renderWithRouter([{ path: '/strategy-studio', element: <StrategyStudioPage /> }], ['/strategy-studio']);

    await waitFor(() => {
      expect(mockedListStrategyVersions).toHaveBeenCalled();
    });

    expect(await screen.findByText('当前筛选范围内暂无策略版本。')).toBeInTheDocument();
    expect(await screen.findByText('当前筛选范围内暂无规则。')).toBeInTheDocument();
    expect(screen.getByText('请选择一个策略版本。')).toBeInTheDocument();
    expect(screen.getByText('请选择一条规则。')).toBeInTheDocument();
  });
});
