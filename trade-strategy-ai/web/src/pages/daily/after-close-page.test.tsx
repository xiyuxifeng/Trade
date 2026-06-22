import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';

import { renderWithRouter } from '@/test/test-utils';
import {
  acceptAfterCloseProposalToDraft,
  generateAfterCloseProposals,
  getAfterCloseReview,
  getTradingDayPlan,
  listAfterCloseProposals,
  reviewAfterCloseProposal,
} from '@/lib/api/daily';
import { TodayAfterClosePage } from './after-close-page';

vi.mock('@/lib/api/daily', () => ({
  getTradingDayPlan: vi.fn(),
  getAfterCloseReview: vi.fn(),
  listAfterCloseProposals: vi.fn(),
  generateAfterCloseProposals: vi.fn(),
  reviewAfterCloseProposal: vi.fn(),
  acceptAfterCloseProposalToDraft: vi.fn(),
}));

const mockedGetTradingDayPlan = vi.mocked(getTradingDayPlan);
const mockedGetAfterCloseReview = vi.mocked(getAfterCloseReview);
const mockedListAfterCloseProposals = vi.mocked(listAfterCloseProposals);
const mockedGenerateAfterCloseProposals = vi.mocked(generateAfterCloseProposals);
const mockedReviewAfterCloseProposal = vi.mocked(reviewAfterCloseProposal);
const mockedAcceptAfterCloseProposalToDraft = vi.mocked(acceptAfterCloseProposalToDraft);

function buildTradingDayPlan() {
  return {
    state: 'ready',
    plan_status: 'ready',
    generated: true,
    trade_date: '2026-06-21',
    happened: '已生成每日运行计划。',
    affected: '今天的盘前预测可用于盘后复核。',
    repair_guidance: '无需修复。',
    daily_strategy_instance_id: 'instance-1',
    trading_day_plan_id: 'plan-1',
    daily_rule_selection_id: 'selection-1',
    revision_no: 1,
    strategy_version_id: 'strategy-version-1',
    instance_lifecycle_state: 'generated',
    plan_lifecycle_state: 'approved',
    approval_state: 'approved',
    market_judgment: { state: 'ready', summary: '强势上行', details: [] },
    enabled_rules: [],
    reduced_rules: [],
    suspended_rules: [],
    candidate_symbols: [],
    candidate_symbols_state: { state: 'ready', summary: '已完成', details: [] },
    signals: [
      {
        signal_id: 'signal-1',
        symbol: '000001.SZ',
        name: '平安银行',
        side: 'BUY',
        confidence: 0.74,
        confidence_label: '74%（中等）',
        state: 'ready',
        entry_condition: '竞价强度继续走强后再执行。',
        invalidation_condition: '若盘前市场状态弱化则失效。',
        stop_loss_take_profit: '止损 5%，止盈 12%。',
        suggested_position: '建议单日仓位不超过 35%。',
        triggered_rule_version_ids: ['rule-1'],
        degraded_inputs: [],
        unresolved_inputs: [],
      },
    ],
    entry_conditions: { state: 'ready', summary: '已整理入场条件。', details: [] },
    invalidation_conditions: { state: 'ready', summary: '已整理失效条件。', details: [] },
    stop_loss_take_profit: { state: 'ready', summary: '已整理止盈止损。', details: [] },
    suggested_position: { state: 'ready', summary: '已整理仓位建议。', details: [] },
    risk_warnings: { state: 'ready', summary: '已整理风险提示。', details: [] },
    confidence: { state: 'ready', summary: '74%（中等）', details: [] },
  } as const;
}

function buildReview(state: 'ready' | 'partial' | 'unavailable' | 'conflict' = 'partial') {
  return {
    state,
    generated: true,
    post_market_review_id: 'review-1',
    trading_day_plan_id: 'plan-1',
    trade_date: '2026-06-21',
    revision_no: 2,
    lifecycle_state: 'draft',
    quality_status: state === 'ready' ? 'complete' : 'partial',
    signal_outcome_state: state,
    attribution_state: state === 'conflict' ? 'conflict' : 'ready',
    post_close_market_snapshot_id: 'snapshot-1',
    post_close_market_state_id: state === 'conflict' ? null : 'market-state-close-1',
    signal_results: [
      {
        signal_id: 'signal-1',
        symbol: '000001.SZ',
        side: 'BUY',
        state: state === 'conflict' ? 'conflict' : 'ready',
        triggered: { state: 'ready', value: true },
        executed: { state: 'unavailable', value: null, reason: 'approved_execution_supplement_missing' },
        matched_rule: {
          state: 'ready',
          rule_version_ids: ['rule-1'],
          signal_rule_version_ids: ['rule-1'],
          triggered_rules: ['rule-1'],
          selection_decisions: { 'rule-1': 'selected' },
        },
        market_state_change: state === 'conflict'
          ? { state: 'unavailable', value: null, reason: 'post_close_market_state_missing' }
          : { state: 'ready', value: 'unchanged' },
        actual_result: state === 'conflict'
          ? { state: 'conflict', value: null, reason: 'actual_row_not_available' }
          : { state: 'ready', value: 'up' },
        mfe: state === 'conflict' ? { state: 'conflict', value: null, reason: 'actual_row_not_available' } : { state: 'ready', value: 0.06 },
        mae: state === 'conflict' ? { state: 'conflict', value: null, reason: 'actual_row_not_available' } : { state: 'ready', value: -0.01 },
        return: state === 'conflict' ? { state: 'conflict', value: null, reason: 'actual_row_not_available' } : { state: 'ready', value: 0.03 },
        evidence: { row_fingerprint: 'row-1', reasons: [], metric_policy_version: 'stage10-signal-outcome-v1' },
      },
    ],
    attribution: {
      state: state === 'conflict' ? 'conflict' : 'ready',
      signals: [
        {
          signal_id: 'signal-1',
          symbol: '000001.SZ',
          state: state === 'conflict' ? 'conflict' : 'ready',
          category: state === 'conflict' ? 'data issue' : 'unattributable',
          user_explanation: state === 'conflict'
            ? '000001.SZ 的盘后证据存在缺失、冲突或降级，当前先归为数据问题。'
            : '000001.SZ 当前结果没有落入固定五类问题，按规则归为暂不可归因。',
        },
      ],
    },
    evidence: {
      actuals: {
        coverage_state: state,
        market_snapshot_content_fingerprint: 'market-fingerprint-1',
        dataset_content_fingerprint: 'dataset-fingerprint-1',
      },
      evidence_fingerprint: 'evidence-fingerprint-1',
    },
    happened: state === 'ready' ? '已读取正式盘后复盘。' : '正式盘后复盘存在未满足的数据状态。',
    affected: state === 'ready'
      ? '页面会按正式证据展示盘前预测、实际结果、差异和建议操作；缺失值不会被当作成功。'
      : '页面只会展示当前已确认的盘后结果，并明确标注缺失、冲突或降级部分。',
    repair_guidance: state === 'ready' ? '可继续查看今日建议操作。' : '请先补齐缺失证据、处理冲突，或在正式状态允许时继续查看可用部分。',
  } as const;
}

function buildProposals() {
  return {
    state: 'partial',
    count: 3,
    items: [
      {
        proposal_id: 'proposal-rule',
        proposal_type: 'rule_optimization',
        proposal_type_label: '规则优化建议',
        lifecycle_state: 'draft',
        lifecycle_label: '待处理',
        revision_no: 1,
        confidence: 0.43,
        evidence_state: 'ready',
        evidence_label: '证据完整',
        recommendation_state: 'continue_observing',
        recommendation_label: '继续观察',
        rationale: '规则层仅形成观察建议。',
        target: {
          asset_type: 'RuleVersion',
          asset_id: 'rule-1',
          label: '竞价强势跟随',
          strategy_membership_ids: ['membership-1'],
          rule_version_ids: ['rule-1'],
          author_profile_version_ids: [],
        },
        review_binding: {},
        proposed_changes: {},
        evidence: {},
        available_actions: ['start_review', 'reject'],
        partial_reasons: [],
        limitations: [],
      },
      {
        proposal_id: 'proposal-author',
        proposal_type: 'author_profile_revision',
        proposal_type_label: '作者画像修订建议',
        lifecycle_state: 'draft',
        lifecycle_label: '待处理',
        revision_no: 1,
        confidence: 0.4,
        evidence_state: 'partial',
        evidence_label: '证据不完整',
        recommendation_state: 'continue_observing',
        recommendation_label: '继续观察',
        rationale: '画像层仅形成观察建议。',
        target: {
          asset_type: 'AuthorProfileVersion',
          asset_id: 'profile-1',
          label: '作者验证画像 v1',
          strategy_membership_ids: [],
          rule_version_ids: ['rule-1'],
          author_profile_version_ids: ['profile-1'],
        },
        review_binding: {},
        proposed_changes: {},
        evidence: {},
        available_actions: ['start_review', 'reject'],
        partial_reasons: ['证据仍需继续观察'],
        limitations: [],
      },
      {
        proposal_id: 'proposal-strategy',
        proposal_type: 'strategy_revision',
        proposal_type_label: '策略修订建议',
        lifecycle_state: 'in_review',
        lifecycle_label: '复核中',
        revision_no: 1,
        confidence: 0.68,
        evidence_state: 'ready',
        evidence_label: '证据完整',
        recommendation_state: 'create_draft_review_suggestion',
        recommendation_label: '生成草稿复核建议',
        rationale: '策略层可安全进入草稿复核。',
        target: {
          asset_type: 'StrategyVersion',
          asset_id: 'strategy-version-1',
          label: '正式策略 v1',
          strategy_membership_ids: ['membership-1'],
          rule_version_ids: ['rule-1'],
          author_profile_version_ids: ['profile-1'],
        },
        review_binding: {},
        proposed_changes: {},
        evidence: {},
        available_actions: ['continue_observing', 'accept_to_draft', 'reject'],
        partial_reasons: [],
        limitations: [],
      },
    ],
    happened: '已读取正式盘后优化建议列表。',
    affected: '页面会按规则、画像、策略三条独立建议展示当前状态和可执行动作。',
    repair_guidance: '如建议为空，请先完成盘后结果评估、结构化归因，并生成本次优化建议。',
  } as const;
}

beforeEach(() => {
  vi.clearAllMocks();
  mockedGetTradingDayPlan.mockResolvedValue(buildTradingDayPlan() as never);
  mockedGetAfterCloseReview.mockResolvedValue(buildReview('partial') as never);
  mockedListAfterCloseProposals.mockResolvedValue(buildProposals() as never);
  mockedGenerateAfterCloseProposals.mockResolvedValue(buildProposals() as never);
  mockedReviewAfterCloseProposal.mockResolvedValue({} as never);
  mockedAcceptAfterCloseProposalToDraft.mockResolvedValue({} as never);
});

describe('TodayAfterClosePage', () => {
  it('renders the formal after-close page with required sections and no legacy terms', async () => {
    renderWithRouter([{ path: '/daily/after-close', element: <TodayAfterClosePage /> }], ['/daily/after-close']);

    expect(await screen.findByRole('heading', { name: '今日盘后' })).toBeInTheDocument();
    expect(screen.getByText('盘前预测')).toBeInTheDocument();
    expect(screen.getByText('实际结果')).toBeInTheDocument();
    expect(screen.getByText('差异')).toBeInTheDocument();
    expect(screen.getByText('成功原因')).toBeInTheDocument();
    expect(screen.getByText('失败原因')).toBeInTheDocument();
    expect(screen.getByText('建议操作')).toBeInTheDocument();
    expect((await screen.findAllByText('执行补充证据未提供，成交相关结果暂不可用。')).length).toBeGreaterThan(0);
    expect(screen.queryByText('Job')).not.toBeInTheDocument();
    expect(screen.queryByText('Workflow')).not.toBeInTheDocument();
    expect(screen.queryByText('Pipeline')).not.toBeInTheDocument();
    expect(screen.queryByText('Artifact')).not.toBeInTheDocument();
    expect(screen.queryByText('DatasetSnapshot')).not.toBeInTheDocument();
    expect(screen.queryByText('MarketSnapshot')).not.toBeInTheDocument();
    expect(screen.queryByText('run-after-close')).not.toBeInTheDocument();
    expect(screen.queryByText('config_path')).not.toBeInTheDocument();
  });

  it('keeps missing review unavailable instead of showing success defaults', async () => {
    mockedGetAfterCloseReview.mockResolvedValue({
      state: 'unavailable',
      generated: false,
      trading_day_plan_id: 'plan-1',
      trade_date: '2026-06-21',
      signal_outcome_state: 'unavailable',
      attribution_state: 'unavailable',
      signal_results: [],
      attribution: { state: 'unavailable', signals: [] },
      evidence: {},
      happened: '正式盘后复盘尚未生成。',
      affected: '当前只能查看盘前预测，实际结果、差异和建议操作暂不可用。',
      repair_guidance: '请先完成正式盘后结果评估；如果今天已经完成，请刷新页面后重试。',
    } as never);

    renderWithRouter([{ path: '/daily/after-close', element: <TodayAfterClosePage /> }], ['/daily/after-close']);

    expect((await screen.findAllByText('盘后结果暂不可用')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('正式盘后复盘尚未生成。').length).toBeGreaterThan(0);
    expect(screen.queryByText('与盘前方向一致')).not.toBeInTheDocument();
    expect(screen.queryByText('0.00%')).not.toBeInTheDocument();
  });

  it('renders conflict and missing market-state truthfully', async () => {
    mockedGetAfterCloseReview.mockResolvedValue(buildReview('conflict') as never);

    renderWithRouter([{ path: '/daily/after-close', element: <TodayAfterClosePage /> }], ['/daily/after-close']);

    expect((await screen.findAllByText('证据冲突')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('盘后市场状态暂不可用，当前不能判断是否发生变化。').length).toBeGreaterThan(0);
    expect(screen.queryByText('未变化')).not.toBeInTheDocument();
    expect(screen.queryByText('成功')).not.toBeInTheDocument();
  });

  it('keeps proposal actions inside RT-S10-003 boundaries', async () => {
    renderWithRouter([{ path: '/daily/after-close', element: <TodayAfterClosePage /> }], ['/daily/after-close']);

    expect(await screen.findByText('规则优化建议')).toBeInTheDocument();
    expect(screen.getByText('作者画像修订建议')).toBeInTheDocument();
    expect(screen.getByText('策略修订建议')).toBeInTheDocument();
    expect(screen.queryAllByRole('button', { name: '生成策略草稿' })).toHaveLength(1);

    fireEvent.click(screen.getAllByRole('button', { name: '拒绝' })[0]);
    await waitFor(() => {
      expect(mockedReviewAfterCloseProposal).toHaveBeenCalledWith('proposal-rule', { action: 'reject' });
    });

    fireEvent.click(screen.getByRole('button', { name: '生成策略草稿' }));
    await waitFor(() => {
      expect(mockedAcceptAfterCloseProposalToDraft).toHaveBeenCalledWith('proposal-strategy', { reason: '盘后页面发起草稿复核' });
    });
  });
});
