import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  createStrategyDraft,
  compareStrategyVersion,
  diffStrategyVersion,
  getStrategyDraftOptions,
  listStrategies,
  publishStrategy,
  rollbackStrategyVersion,
  submitStrategyReview,
  validateStrategyVersion,
} from './strategies';

describe('strategies api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.clear();
  });

  it('calls the formal strategy center endpoints with stored api key', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          state: 'ready',
          current_strategy: { business_key: 'cn-swing-core', current_version_id: 'version-2' },
          items: [],
          count: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          rule_options: [],
          author_profile_options: { method: [], rule: [], validated: [] },
          dataset_options: [],
          market_snapshot_options: [],
          rule_applicability_options: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => ({
          strategy_version_id: 'version-1',
          strategy_id: 'strategy-1',
          business_key: 'cn-swing-core',
          title: 'A股趋势轮动策略',
          version_no: 1,
          lifecycle_state: 'draft',
          lifecycle_label: '草稿',
          review_status: 'draft',
          status_state: 'draft',
          schema_version: 'strategy-schema-v1',
          quality_status: 'verified',
          rule_pool: [],
          profiles: {},
          policies: {},
          evidence: { market_snapshot_ids: [], rule_applicability_profile_ids: [], backtest_run_ids: [], backtest_result_ids: [] },
          current_status: { is_current: false, current_version_id: null, previous_current_version_id: null },
          partial_reasons: [],
          limitations: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ strategy_version_id: 'version-1', lifecycle_state: 'pending_review' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ strategy_version_id: 'version-1', lifecycle_state: 'published' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          strategy_version_id: 'version-1',
          strategy_id: 'strategy-1',
          business_key: 'cn-swing-core',
          title: 'A股趋势轮动策略',
          version_no: 1,
          lifecycle_state: 'draft',
          lifecycle_label: '草稿',
          review_status: 'draft',
          status_state: 'draft',
          schema_version: 'strategy-schema-v1',
          quality_status: 'verified',
          rule_pool: [],
          profiles: {},
          policies: {},
          evidence: { market_snapshot_ids: [], rule_applicability_profile_ids: [], backtest_run_ids: [], backtest_result_ids: [] },
          current_status: { is_current: false, current_version_id: null, previous_current_version_id: null },
          validation: { state: 'passed', label: '验证通过', reviewer_decision: 'approved', reviewer_decision_label: '已批准' },
          partial_reasons: [],
          limitations: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          state: 'ready',
          current_version: { strategy_version_id: 'version-0' },
          candidate_version: { strategy_version_id: 'version-1' },
          delta: { rule_weight_changes: 1 },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          state: 'ready',
          base_version: { strategy_version_id: 'version-0' },
          target_version: { strategy_version_id: 'version-1' },
          changes: [{ field: 'title', label: '策略名称', before: '旧策略', after: '新策略' }],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          strategy_version_id: 'version-0',
          strategy_id: 'strategy-1',
          business_key: 'cn-swing-core',
          title: 'A股趋势轮动策略',
          version_no: 1,
          lifecycle_state: 'published',
          lifecycle_label: '已发布',
          review_status: 'published',
          status_state: 'published',
          schema_version: 'strategy-schema-v1',
          quality_status: 'verified',
          rule_pool: [],
          profiles: {},
          policies: {},
          evidence: { market_snapshot_ids: [], rule_applicability_profile_ids: [], backtest_run_ids: [], backtest_result_ids: [] },
          current_status: { is_current: true, current_version_id: 'version-0', previous_current_version_id: 'version-1' },
          partial_reasons: [],
          limitations: [],
        }),
      });

    vi.stubGlobal('fetch', fetchMock);
    window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');

    await listStrategies();
    await getStrategyDraftOptions();
    await createStrategyDraft({
      business_key: 'cn-swing-core',
      schema_version: 'strategy-schema-v1',
      title: 'A股趋势轮动策略',
      summary: '正式策略草稿',
      rule_memberships: [],
      author_method_profile_version_id: '22222222-2222-2222-2222-222222222222',
      author_rule_profile_version_id: '33333333-3333-3333-3333-333333333333',
      author_validated_profile_version_id: '44444444-4444-4444-4444-444444444444',
      risk_policy_json: {},
      selection_policy_json: {},
      universe_json: {},
      evidence_json: {},
    });
    await submitStrategyReview('version-1', { reason: '提交审核' });
    await publishStrategy('version-1', { reason: '审核通过' });
    await validateStrategyVersion('version-1', { reason: '校验正式策略' });
    await compareStrategyVersion('version-1');
    await diffStrategyVersion('version-1');
    await rollbackStrategyVersion('version-0', { reason: '回退到上一正式版本' });

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/ui/v1/strategies', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/ui/v1/strategies/draft-options', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/ui/v1/strategies', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/ui/v1/strategies/version-1/submit-review', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(5, '/api/ui/v1/strategies/version-1/publish', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(6, '/api/ui/v1/strategies/version-1/validate', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(7, '/api/ui/v1/strategies/version-1/comparison', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(8, '/api/ui/v1/strategies/version-1/diff', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(9, '/api/ui/v1/strategies/version-0/rollback', expect.any(Object));

    const firstInit = fetchMock.mock.calls[0][1] as RequestInit;
    expect((firstInit.headers as Headers).get('Accept')).toBe('application/json');
    expect((firstInit.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});
