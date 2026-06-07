import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { RegimeRuleSelectionPage } from './RegimeRuleSelectionPage';
import { renderWithRouter } from '@/test/test-utils';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import { listTraderOptions } from '@/lib/api/traders';

vi.mock('@/lib/api/strategyStudio', () => ({
  getStrategyVersion: vi.fn(),
  listStrategyVersions: vi.fn(),
}));

vi.mock('@/lib/api/traders', () => ({
  listTraderOptions: vi.fn(),
}));

const mockedGetStrategyVersion = vi.mocked(getStrategyVersion);
const mockedListStrategyVersions = vi.mocked(listStrategyVersions);
const mockedListTraderOptions = vi.mocked(listTraderOptions);

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('RegimeRuleSelectionPage', () => {
  it('renders selection trace, selected/skipped/blocked rules and override audit', async () => {
    mockedListStrategyVersions.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 20,
      items: [
        {
          version_id: 'trader_a_2026-05-19_draft',
          trader_id: 'trader_a',
          strategy_date: '2026-05-19',
          status: 'draft',
          version_type: 'manual',
          parent_version_id: null,
          recommendations_count: 2,
          source_article_ids_count: 1,
          released_at: null,
          has_rules_snapshot: true,
        },
      ],
    });
    mockedListTraderOptions.mockResolvedValue({
      status: 'success',
      count: 2,
      items: ['trader_a', 'trader_b'],
    } as never);
    mockedGetStrategyVersion.mockResolvedValue({
      status: 'success',
      item: {
        version_id: 'trader_a_2026-05-19_draft',
        trader_id: 'trader_a',
        strategy_date: '2026-05-19',
        status: 'draft',
        version_type: 'manual',
        parent_version_id: null,
        recommendations: [],
        source_article_ids: [],
        evidence_refs: [],
        notes: 'selection notes',
        released_at: null,
        rules_snapshot: [{ rule_id: 'rule-1', condition: 'trend', action: 'buy' }],
        regime_selection: {
          selection_id: 'sel-001',
          strategy_version_id: 'trader_a_2026-05-19_draft',
          snapshot_id: 'snap-1',
          market_regime_version: 'market-regime-v3',
          source_feature_version: 'market-regime-features-v3',
          applicability_profile_version: 'rule-applicability-v1',
          selected_by: 'web',
          confidence: 0.82,
          quality_status: 'ok',
          selection_reason: 'applicable 优先，neutral 低权重补充，blocked 默认排除',
          evidence: ['market_regime=strong_bull', 'selected_rules=1', 'blocked_rules=1'],
          warnings: [],
          selected_rules: [
            {
              rule_id: 'rule-1',
              decision: 'selected',
              score: 0.91,
              reason: 'strong_bull 下适用',
              evidence: ['decision=applicable'],
              regime_version: 'market-regime-v3',
              applicability_profile_version: 'rule-applicability-v1',
              sample_count: 20,
              profile_confidence: 0.8,
            },
          ],
          skipped_rules: [
            {
              rule_id: 'rule-2',
              decision: 'skipped',
              score: 0.12,
              reason: '未匹配当前 Market Regime',
              evidence: ['missing_applicability_profile'],
              regime_version: 'market-regime-v3',
              applicability_profile_version: 'rule-applicability-v1',
              sample_count: 0,
              profile_confidence: 0.1,
            },
          ],
          blocked_rules: [
            {
              rule_id: 'rule-3',
              decision: 'blocked',
              score: 0,
              reason: 'weak_bear 下默认阻断',
              evidence: ['decision=blocked'],
              regime_version: 'market-regime-v3',
              applicability_profile_version: 'rule-applicability-v1',
              sample_count: 12,
              profile_confidence: 0.9,
              override_applied: true,
            },
          ],
          override: {
            operator: 'web',
            reason: '人工放行',
            timestamp: '2026-05-19T08:30:00Z',
            risk_level: 'medium',
          },
          created_at: '2026-05-19T08:31:00Z',
        },
      },
    });

    renderWithRouter([{ path: '/strategies/regime-selection', element: <RegimeRuleSelectionPage /> }], ['/strategies/regime-selection']);

    await waitFor(() => {
      expect(mockedListStrategyVersions).toHaveBeenCalled();
      expect(mockedGetStrategyVersion).toHaveBeenCalled();
      expect(mockedListTraderOptions).toHaveBeenCalledWith({ source: 'strategy' });
    });

    expect(await screen.findByRole('heading', { level: 1, name: '规则选择' })).toBeInTheDocument();
    expect((await screen.findAllByText('sel-001')).length).toBeGreaterThan(1);
    expect(screen.getByText('snap-1')).toBeInTheDocument();
    expect(screen.getByText('market-regime-v3')).toBeInTheDocument();
    expect(screen.getByText('rule-applicability-v1')).toBeInTheDocument();
    expect(screen.getByText('rule-1')).toBeInTheDocument();
    expect(screen.getByText('rule-2')).toBeInTheDocument();
    expect(screen.getByText('rule-3')).toBeInTheDocument();
    expect(screen.getByText('人工放行')).toBeInTheDocument();
    expect(screen.getByText('weak_bear 下默认阻断')).toBeInTheDocument();
    expect(screen.getByText('strong_bull 下适用')).toBeInTheDocument();
  });
});
