import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  acceptStrategyRevisionProposalToDraft,
  createStrategyDraft,
  compareStrategyVersion,
  diffStrategyVersion,
  getStrategyDraftOptions,
  getStrategyRevisionProposal,
  listStrategies,
  listStrategyRevisionProposals,
  publishStrategy,
  rollbackStrategyVersion,
  reviewStrategyRevisionProposal,
  submitStrategyReview,
  validateStrategyVersion,
} from './strategies';

function proposalPayload(overrides: Record<string, unknown> = {}) {
  return {
    proposal_id: 'proposal-1',
    proposal_type: 'strategy_revision',
    lifecycle_state: 'in_review',
    lifecycle_label: '复核中',
    revision_no: 1,
    confidence: 0.82,
    rationale: '回测样本显示波动上升',
    trigger_type: 'market_state_shift',
    evidence_state: 'partial',
    evidence_label: '证据不完整',
    affected_strategy_version: {
      strategy_version_id: 'version-1',
      strategy_id: 'strategy-1',
      business_key: 'cn-swing-core',
      title: 'A股趋势轮动策略',
      version_no: 2,
      lifecycle_state: 'published',
      lifecycle_label: '已发布',
      validation_summary: {
        state: 'passed',
        label: '验证通过',
        reviewer_decision: 'approved',
        reviewer_decision_label: '已批准',
        dataset_binding: { state: 'ready', dataset_snapshot_id: 'dataset-1', market_state_definition_version: 'market-state-v2' },
        market_snapshot_binding: { state: 'ready', market_snapshot_ids: ['market-1'] },
        backtest: {
          state: 'ready',
          out_of_sample_state: 'available',
          backtest_run_ids: ['run-1'],
          backtest_result_ids: ['result-1'],
          requested_level: 'L2',
          effective_level: 'L2',
          annual_return: 0.18,
          max_drawdown: 0.09,
          win_rate: 0.56,
        },
        rule_applicability: { state: 'ready', covered_rule_count: 1, total_rule_count: 1, coverage_ratio: 1 },
        sample_coverage: { state: 'sufficient', sample_count: 48, insufficient_sample: false },
        data_quality: { state: 'verified', warnings: [], limitations: [] },
      },
      current_status: { is_current: true, current_version_id: 'version-1', previous_current_version_id: null },
    },
    base_version_id: 'version-0',
    accepted_draft_version_id: null,
    proposed_changes: { proposed_weight_changes: [{ rule_version_id: 'rule-1', base_weight: 0.5 }] },
    evidence: {
      dataset_snapshot_id: 'dataset-1',
      market_snapshot_ids: ['market-1'],
      rule_applicability_profile_ids: ['rule-1'],
      backtest_run_ids: ['run-1'],
      backtest_result_ids: ['result-1'],
      evidence_fingerprint: 'fp-1',
    },
    created_at: '2026-06-20T12:00:00+00:00',
    updated_at: '2026-06-20T14:00:00+00:00',
    available_actions: ['start_review', 'reject', 'generate_draft'],
    partial_reasons: [],
    limitations: [],
    ...overrides,
  };
}

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
          state: 'ready',
          count: 1,
          items: [proposalPayload()],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => proposalPayload(),
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
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => proposalPayload({ accepted_draft_version_id: 'version-2', lifecycle_state: 'accepted', lifecycle_label: '已生成草稿', available_actions: ['archive', 'supersede'] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => proposalPayload({ accepted_draft_version_id: 'version-2', lifecycle_state: 'accepted', lifecycle_label: '已生成草稿', available_actions: ['archive', 'supersede'] }),
      });

    vi.stubGlobal('fetch', fetchMock);
    window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');

    await listStrategies();
    await listStrategyRevisionProposals();
    await getStrategyRevisionProposal('proposal-1');
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
    await reviewStrategyRevisionProposal('proposal-1', { action: 'start_review', reason: '建议有效' });
    await acceptStrategyRevisionProposalToDraft('proposal-1', { reason: '生成草稿' });

    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/ui/v1/strategies', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(2, '/api/ui/v1/strategies/proposals', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(3, '/api/ui/v1/strategies/proposals/proposal-1', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(4, '/api/ui/v1/strategies/draft-options', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(5, '/api/ui/v1/strategies', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(6, '/api/ui/v1/strategies/version-1/submit-review', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(7, '/api/ui/v1/strategies/version-1/publish', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(8, '/api/ui/v1/strategies/version-1/validate', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(9, '/api/ui/v1/strategies/version-1/comparison', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(10, '/api/ui/v1/strategies/version-1/diff', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(11, '/api/ui/v1/strategies/version-0/rollback', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(12, '/api/ui/v1/strategies/proposals/proposal-1/review', expect.any(Object));
    expect(fetchMock).toHaveBeenNthCalledWith(13, '/api/ui/v1/strategies/proposals/proposal-1/accept-to-draft', expect.any(Object));

    const firstInit = fetchMock.mock.calls[0][1] as RequestInit;
    expect((firstInit.headers as Headers).get('Accept')).toBe('application/json');
    expect((firstInit.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});
