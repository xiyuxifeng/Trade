import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  adviseRuleValidations,
  createCandidateVersion,
  getStrategyRule,
  getStrategyVersion,
  listStrategyRules,
  listStrategyVersions,
  reviewStrategyRule,
  reviewStrategyRuleBatch,
} from './strategyStudio';

describe('strategy studio api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it('calls the strategy studio endpoints and forwards the stored API key', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'success',
          count: 1,
          total: 1,
          skip: 0,
          limit: 10,
          items: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
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
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ count: 1, rule_ids: ['rule-1'] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ results: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          status: 'success',
          item: {
            version_id: 'candidate-1',
            trader_id: 'trader_a',
            strategy_date: '2026-05-09',
            status: 'draft',
            version_type: 'candidate',
            parent_version_id: 'sv-1',
            recommendations: [],
            source_article_ids: [],
            evidence_refs: [],
            notes: 'custom notes',
            released_at: null,
            rules_snapshot: [],
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'success', count: 1, total: 1, skip: 0, limit: 10, items: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
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
            backtest_result: null,
            backtest_hits: 0,
            backtest_misses: 0,
            backtest_samples: 0,
            mapped: false,
            created_at: null,
            id: null,
            source_article_ids: [],
            extraction_layer: {},
            mapped_by: null,
            mapped_at: null,
            reviewed_by: null,
            reviewed_at: null,
            backtest_triggered_at: null,
            used_in_prediction: false,
            prediction_count: 0,
            last_used_at: null,
            updated_at: null,
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'ok', rule_id: 'rule-1' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'ok', updated_count: 1 }),
      });

    vi.stubGlobal('fetch', fetchMock);
    window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');

    await listStrategyVersions({ trader_id: 'trader_a', skip: 0, limit: 10 });
    await getStrategyVersion('sv-1');
    await adviseRuleValidations([
      {
        trader_id: 'trader_a',
        strategy_version_id: 'sv-1',
        rule_id: 'rule-1',
        rule_text: 'price above moving average',
        programmable: true,
        validation_status: 'validated',
        hit_count: 3,
        sample_count: 5,
        hit_rate: 0.6,
        posterior_return_mean: 0.12,
        posterior_return_median: 0.1,
        notes: ['ok'],
        result_version: '1.0',
      },
    ]);
    await createCandidateVersion({
      parent_version_id: 'sv-1',
      trader_id: 'trader_a',
      strategy_date: '2026-05-09',
      adjustments: [],
      recommendations: [],
      notes: 'custom notes',
    });
    await listStrategyRules({ status: 'pending', skip: 0, limit: 10 });
    await getStrategyRule('rule-1');
    await reviewStrategyRule('rule-1', { decision: 'approve', force: false, reviewed_by: 'web' });
    await reviewStrategyRuleBatch({ decision: 'reject', status: 'pending', limit: 25, force: true, reviewed_by: 'web' });

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/ui/v1/strategy-studio/versions?trader_id=trader_a&skip=0&limit=10', expect.any(Object));
    const firstInit = fetchMock.mock.calls[0][1] as RequestInit;
    expect((firstInit.headers as Headers).get('Accept')).toBe('application/json');
    expect((firstInit.headers as Headers).get('X-API-Key')).toBe('demo-key');

    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/ui/v1/strategy-studio/versions/sv-1', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/ui/v1/strategy-studio/optimize/advise-rule-validations', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/ui/v1/strategy-studio/optimize/create-candidate', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(5, '/api/ui/v1/strategy-studio/rule-pool?status=pending&skip=0&limit=10', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(6, '/api/ui/v1/strategy-studio/rule-pool/rule-1', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(7, '/api/ui/v1/strategy-studio/rule-pool/rule-1/review', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(8, '/api/ui/v1/strategy-studio/rule-pool/review-batch', expect.any(Object));
  });
});
