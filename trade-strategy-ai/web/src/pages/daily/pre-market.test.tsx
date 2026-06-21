import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';

import { renderWithRouter } from '@/test/test-utils';
import { ApiError } from '@/lib/api/http';
import { getDailyRuleSelection, getPreMarketReadiness, getTradingDayPlan, reviewTradingDayPlan } from '@/lib/api/daily';
import { TodayPreMarketPage } from './index';

vi.mock('@/lib/api/daily', () => ({
  getPreMarketReadiness: vi.fn(),
  getDailyRuleSelection: vi.fn(),
  getTradingDayPlan: vi.fn(),
  reviewTradingDayPlan: vi.fn(),
}));

const mockedGetPreMarketReadiness = vi.mocked(getPreMarketReadiness);
const mockedGetDailyRuleSelection = vi.mocked(getDailyRuleSelection);
const mockedGetTradingDayPlan = vi.mocked(getTradingDayPlan);
const mockedReviewTradingDayPlan = vi.mocked(reviewTradingDayPlan);

beforeEach(() => {
  vi.clearAllMocks();
  mockedGetTradingDayPlan.mockResolvedValue({
    state: 'partial',
    plan_status: 'degraded',
    generated: true,
    trade_date: '2026-06-21',
    happened: '已根据已接受的每日规则选择生成每日运行计划。',
    affected: '今日盘前执行对象、信号和风险提示已经固定，可在批准后执行。',
    repair_guidance: '若需降低风险，请先补齐降级输入后重新生成计划。',
    daily_strategy_instance_id: 'daily-instance-1',
    trading_day_plan_id: 'daily-plan-1',
    daily_rule_selection_id: 'selection-1',
    revision_no: 1,
    strategy_version_id: 'strategy-version-1',
    instance_lifecycle_state: 'generated',
    plan_lifecycle_state: 'in_review',
    approval_state: 'pending',
    market_judgment: { state: 'degraded', summary: '强势上行（置信度 74%（中等））', details: ['市场状态 ID：market-state-1'] },
    enabled_rules: [],
    reduced_rules: [],
    suspended_rules: [],
    candidate_symbols: [{ symbol: '000001.SZ', name: '平安银行', rank: 1, score: 0.91, state: 'ready' }],
    candidate_symbols_state: { state: 'ready', summary: '候选标的来自正式盘前市场快照 strong_symbols section。', details: [] },
    signals: [
      {
        signal_id: 'signal-1',
        symbol: '000001.SZ',
        name: '平安银行',
        side: 'BUY',
        confidence: 0.74,
        confidence_label: '74%（中等）',
        state: 'degraded',
        entry_condition: '候选标的 000001.SZ 需满足已启用规则的盘前条件后再执行。',
        invalidation_condition: '若竞价/盘前状态偏离当前市场判断或关键规则失效，则该信号失效。',
        stop_loss_take_profit: '已绑定正式策略风险控制参数。',
        suggested_position: '建议单日总仓位不超过 35.0%。',
        triggered_rule_version_ids: ['rule-version-1'],
        degraded_inputs: ['insufficient_sample'],
        unresolved_inputs: [],
      },
    ],
    entry_conditions: { state: 'ready', summary: '已整理入场条件。', details: ['竞价强势跟随：关注 竞价强度 条件成立。'] },
    invalidation_conditions: { state: 'ready', summary: '若市场状态、规则适用性或关键数据质量发生变化，本计划即时失效。', details: [] },
    stop_loss_take_profit: { state: 'ready', summary: '已绑定正式策略风险控制参数。', details: ['止损：5%', '止盈：12%'] },
    suggested_position: { state: 'degraded', summary: '建议单日总仓位不超过 35.0%。', details: [] },
    risk_warnings: { state: 'degraded', summary: '执行前请先确认今日盘前依赖状态。', details: ['降级输入：insufficient_sample'] },
    confidence: { state: 'degraded', summary: '74%（中等）', details: [] },
    traceability: {
      trade_date: '2026-06-21',
      strategy_version_id: 'strategy-version-1',
      daily_rule_selection_id: 'selection-1',
      dataset_snapshot_id: 'dataset-snapshot-1',
      market_snapshot_id: 'market-snapshot-1',
      market_state_id: 'market-state-1',
      current_market_state_label: '强势上行',
      rule_applicability_profile_ids: ['applicability-1', 'applicability-2'],
      author_method_profile_version_id: 'author-method-1',
      author_rule_profile_version_id: 'author-rule-1',
      author_validated_profile_version_id: 'author-validated-1',
      data_quality_state: 'degraded',
      readiness_status: 'degraded',
      selected_rules: [],
      reduced_rules: [],
      suspended_rules: [],
      degraded_inputs: ['insufficient_sample'],
      unresolved_inputs: [],
    },
  } as never);
  mockedReviewTradingDayPlan.mockResolvedValue({
    approval_state: 'approved',
    approved_by: 'tester',
    plan_lifecycle_state: 'approved',
  } as never);
  mockedGetDailyRuleSelection.mockResolvedValue({
    state: 'partial',
    selection_status: 'degraded',
    generated: true,
    trade_date: '2026-06-21',
    happened: '部分规则因为样本不足被降权。',
    affected: '今日规则选择可继续，但需要关注降级输入。',
    repair_guidance: '先补齐适用性证据，或按降级结果继续。',
    daily_rule_selection_id: 'selection-1',
    revision_no: 1,
    strategy_version_id: 'strategy-version-1',
    quality_status: 'partial',
    readiness_status: 'degraded',
    enabled_rules: [
      {
        rule_version_id: 'rule-version-1',
        strategy_rule_membership_id: 'membership-1',
        decision: 'selected',
        controlling_priority_tier: 'current_market_state',
        controlling_priority_label: '当前市场状态',
        evidence_ids: ['applicability-1', 'market-state-1'],
        quality_states: ['verified', 'ready'],
        reason_tiers: ['formal_rule_applicability', 'current_market_state'],
        reason_list: ['规则适用性已发布。', '当前市场状态与规则适配。'],
        degraded_inputs: [],
        unresolved_inputs: [],
      },
    ],
    reduced_rules: [
      {
        rule_version_id: 'rule-version-2',
        strategy_rule_membership_id: 'membership-2',
        decision: 'reduced',
        controlling_priority_tier: 'formal_rule_applicability',
        controlling_priority_label: '正式规则适用性',
        evidence_ids: ['applicability-2'],
        quality_states: ['partial', 'insufficient_sample'],
        reason_tiers: ['formal_rule_applicability'],
        reason_list: ['样本不足，今日降权处理。'],
        degraded_inputs: ['insufficient_sample'],
        unresolved_inputs: [],
      },
    ],
    suspended_rules: [
      {
        rule_version_id: 'rule-version-3',
        strategy_rule_membership_id: 'membership-3',
        decision: 'suspended',
        controlling_priority_tier: 'formal_rule_applicability',
        controlling_priority_label: '正式规则适用性',
        evidence_ids: [],
        quality_states: ['unavailable'],
        reason_tiers: ['formal_rule_applicability'],
        reason_list: ['缺少正式规则适用性，今日暂停。'],
        degraded_inputs: [],
        unresolved_inputs: ['missing_rule_applicability'],
      },
    ],
    traceability: {
      trade_date: '2026-06-21',
      strategy_version_id: 'strategy-version-1',
      dataset_snapshot_id: 'dataset-snapshot-1',
      market_snapshot_id: 'market-snapshot-1',
      market_state_id: 'market-state-1',
      rule_applicability_profile_ids: ['applicability-1', 'applicability-2'],
      author_method_profile_version_id: 'author-method-1',
      author_rule_profile_version_id: 'author-rule-1',
      author_validated_profile_version_id: 'author-validated-1',
      data_quality_state: 'degraded',
      readiness_status: 'degraded',
    },
    degraded_inputs: ['insufficient_sample'],
    unresolved_inputs: [],
  } as never);
});

describe('TodayPreMarketPage', () => {
  it('shows degraded readiness in business Chinese without legacy job language', async () => {
    mockedGetPreMarketReadiness.mockResolvedValue({
      state: 'partial',
      readiness_status: 'degraded',
      trade_date: '2026-06-21',
      slot: '09-25',
      summary_title: '可降级继续',
      happened: '正式规则适用性覆盖不完整。',
      affected: '今日规则选择会缺少一部分正式适用性证据。',
      repair_guidance: '先补齐规则适用性画像，或在降级模式下继续。',
      can_proceed: true,
      can_proceed_in_degraded_mode: true,
      checks: [
        {
          code: 'rule_applicability',
          label: '规则适用性',
          status: 'degraded',
          happened: '正式规则适用性覆盖不完整。',
          affected: '今日规则选择会缺少一部分正式适用性证据。',
          repair_guidance: '先补齐规则适用性画像，或在降级模式下继续。',
          can_proceed_in_degraded_mode: true,
          traceability: {
            applicability_profile_ids: [],
            missing_rule_version_ids: ['rule-version-1'],
          },
        },
      ],
      traceability: {
        trade_date: '2026-06-21',
        strategy_version_id: 'strategy-version-1',
        dataset_snapshot_id: 'dataset-snapshot-1',
        market_snapshot_id: 'market-snapshot-1',
        market_state_id: 'market-state-1',
        rule_applicability_profile_ids: [],
        author_validated_profile_version_id: 'author-validated-1',
        data_quality_state: 'degraded',
      },
      repair_actions: [{ label: '补齐缺失数据', to: '/system/data' }],
      warnings: [],
    } as never);

    renderWithRouter([{ path: '/daily/pre-market', element: <TodayPreMarketPage /> }], ['/daily/pre-market']);

    expect(await screen.findByRole('heading', { name: '今日盘前' })).toBeInTheDocument();
    expect(await screen.findAllByText('可降级继续')).not.toHaveLength(0);
    expect(await screen.findAllByText('正式规则适用性覆盖不完整。')).not.toHaveLength(0);
    expect(await screen.findAllByText('今日规则选择会缺少一部分正式适用性证据。')).not.toHaveLength(0);
    expect(await screen.findByRole('link', { name: '补齐缺失数据' })).toHaveAttribute('href', '/system/data');
    expect(screen.queryByText('run-pre-market')).not.toBeInTheDocument();
    expect(screen.queryByText('snapshot-build')).not.toBeInTheDocument();
    expect(screen.queryByText('config_path')).not.toBeInTheDocument();
    expect(screen.queryByText('Job')).not.toBeInTheDocument();
    expect(screen.queryByText('Workflow')).not.toBeInTheDocument();
    expect(screen.queryByText('Pipeline')).not.toBeInTheDocument();
    expect(screen.queryByText('Artifact')).not.toBeInTheDocument();
    expect(screen.queryByText('DatasetSnapshot')).not.toBeInTheDocument();
    expect(screen.queryByText('MarketSnapshot')).not.toBeInTheDocument();
    expect(screen.queryByText('dataset_snapshot_id')).not.toBeInTheDocument();
    expect(screen.queryByText('market_snapshot_id')).not.toBeInTheDocument();
    expect(await screen.findAllByText('历史行情快照')).not.toHaveLength(0);
    expect(await screen.findAllByText('盘前市场快照')).not.toHaveLength(0);
  });

  it('shows enabled reduced and suspended rules with Chinese reason tiers', async () => {
    mockedGetPreMarketReadiness.mockResolvedValue({
      state: 'partial',
      readiness_status: 'degraded',
      trade_date: '2026-06-21',
      slot: '09-25',
      summary_title: '可降级继续',
      happened: '正式规则适用性覆盖不完整。',
      affected: '今日规则选择会缺少一部分正式适用性证据。',
      repair_guidance: '先补齐规则适用性画像，或在降级模式下继续。',
      can_proceed: true,
      can_proceed_in_degraded_mode: true,
      checks: [],
      traceability: {
        trade_date: '2026-06-21',
        strategy_version_id: 'strategy-version-1',
        dataset_snapshot_id: 'dataset-snapshot-1',
        market_snapshot_id: 'market-snapshot-1',
        market_state_id: 'market-state-1',
        rule_applicability_profile_ids: ['applicability-1', 'applicability-2'],
        author_method_profile_version_id: 'author-method-1',
        author_rule_profile_version_id: 'author-rule-1',
        author_validated_profile_version_id: 'author-validated-1',
        data_quality_state: 'degraded',
      },
      repair_actions: [],
      warnings: [],
    } as never);

    renderWithRouter([{ path: '/daily/pre-market', element: <TodayPreMarketPage /> }], ['/daily/pre-market']);

    expect(await screen.findByText('今日规则选择')).toBeInTheDocument();
    expect(await screen.findByText('每日运行计划')).toBeInTheDocument();
    expect(await screen.findAllByText('不是正式策略')).not.toHaveLength(0);
    expect(await screen.findByText('候选标的')).toBeInTheDocument();
    expect(await screen.findByText('信号')).toBeInTheDocument();
    expect(await screen.findByText('入场条件')).toBeInTheDocument();
    expect(await screen.findByText('失效条件')).toBeInTheDocument();
    expect(await screen.findByText('止盈止损')).toBeInTheDocument();
    expect(await screen.findByText('建议仓位')).toBeInTheDocument();
    expect(await screen.findByText('风险提示')).toBeInTheDocument();
    expect(await screen.findAllByText('74%（中等）')).not.toHaveLength(0);
    expect(await screen.findAllByText('启用规则')).not.toHaveLength(0);
    expect(await screen.findAllByText('降权规则')).not.toHaveLength(0);
    expect(await screen.findAllByText('暂停规则')).not.toHaveLength(0);
    expect(await screen.findByText('当前市场状态')).toBeInTheDocument();
    expect(await screen.findAllByText('正式规则适用性')).not.toHaveLength(0);
    expect(await screen.findByText('样本不足，今日降权处理。')).toBeInTheDocument();
    expect(await screen.findByText('缺少正式规则适用性，今日暂停。')).toBeInTheDocument();
    expect(screen.queryByText('Regime')).not.toBeInTheDocument();
    expect(screen.queryByText('selected')).not.toBeInTheDocument();
    expect(screen.queryByText('reduced')).not.toBeInTheDocument();
    expect(screen.queryByText('suspended')).not.toBeInTheDocument();
    expect(screen.queryByText('BUY')).not.toBeInTheDocument();
    expect(await screen.findAllByText('已启用')).not.toHaveLength(0);
    expect(await screen.findAllByText('已降权')).not.toHaveLength(0);
    expect(await screen.findAllByText('已暂停')).not.toHaveLength(0);
    expect(await screen.findByText('买入')).toBeInTheDocument();
  });

  it('submits approval action for the daily plan', async () => {
    mockedGetPreMarketReadiness.mockResolvedValue({
      state: 'ready',
      readiness_status: 'ready',
      trade_date: '2026-06-21',
      slot: '09-25',
      summary_title: '已就绪',
      happened: '正式盘前输入已齐备。',
      affected: '可以继续正式盘前流程。',
      repair_guidance: '当前无需修复。',
      can_proceed: true,
      can_proceed_in_degraded_mode: false,
      checks: [],
      traceability: {
        trade_date: '2026-06-21',
        strategy_version_id: 'strategy-version-1',
        dataset_snapshot_id: 'dataset-snapshot-1',
        market_snapshot_id: 'market-snapshot-1',
        market_state_id: 'market-state-1',
        rule_applicability_profile_ids: [],
        author_validated_profile_version_id: 'author-validated-1',
        data_quality_state: 'ready',
      },
      repair_actions: [],
      warnings: [],
    } as never);

    renderWithRouter([{ path: '/daily/pre-market', element: <TodayPreMarketPage /> }], ['/daily/pre-market']);

    const approveButton = await screen.findByRole('button', { name: '批准今日计划' });
    approveButton.click();

    await waitFor(() => {
      expect(mockedReviewTradingDayPlan).toHaveBeenCalledWith('2026-06-21', { action: 'approve' });
    });
  });

  it('shows permission denied truthfully', async () => {
    mockedGetPreMarketReadiness.mockRejectedValue(
      new ApiError(403, 'forbidden'),
    );

    renderWithRouter([{ path: '/daily/pre-market', element: <TodayPreMarketPage /> }], ['/daily/pre-market']);

    expect(await screen.findByRole('heading', { name: '今日盘前' })).toBeInTheDocument();
    expect(await screen.findAllByText('无权限')).not.toHaveLength(0);
  });

  it('shows blocked readiness when canonical market coverage is missing', async () => {
    mockedGetPreMarketReadiness.mockResolvedValue({
      state: 'unavailable',
      readiness_status: 'blocked',
      trade_date: '2026-06-21',
      slot: '09-25',
      summary_title: '已阻塞',
      happened: '今日盘前市场快照缺失。',
      affected: '系统无法确认当前市场状态，也不能继续正式盘前流程。',
      repair_guidance: '先到数据管理补齐今日盘前市场数据。',
      can_proceed: false,
      can_proceed_in_degraded_mode: false,
      checks: [
        {
          code: 'kaipan_pre_market',
          label: 'Kaipan 盘前数据',
          status: 'blocked',
          happened: '今日盘前市场快照缺失。',
          affected: '无法确认当前市场状态。',
          repair_guidance: '先补齐今日盘前市场数据。',
          can_proceed_in_degraded_mode: false,
          traceability: {
            market_snapshot_id: null,
          },
        },
      ],
      traceability: {
        trade_date: '2026-06-21',
        strategy_version_id: 'strategy-version-1',
        dataset_snapshot_id: 'dataset-snapshot-1',
        market_snapshot_id: null,
        market_state_id: null,
        rule_applicability_profile_ids: [],
        author_validated_profile_version_id: 'author-validated-1',
        data_quality_state: 'blocked',
      },
      repair_actions: [{ label: '前往数据管理', to: '/system/data' }],
      warnings: [],
    } as never);

    renderWithRouter([{ path: '/daily/pre-market', element: <TodayPreMarketPage /> }], ['/daily/pre-market']);

    expect(await screen.findAllByText('已阻塞')).not.toHaveLength(0);
    expect(await screen.findAllByText('系统无法确认当前市场状态，也不能继续正式盘前流程。')).not.toHaveLength(0);
    expect(await screen.findByRole('link', { name: '前往数据管理' })).toHaveAttribute('href', '/system/data');
    expect(await screen.findAllByText('当前不能继续后续流程。')).not.toHaveLength(0);
  });
});
