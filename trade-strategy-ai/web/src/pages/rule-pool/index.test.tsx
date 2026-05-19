import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { RulePoolPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import {
  generateRuleApplicabilityProfile,
  getRuleApplicabilityProfile,
  getRulePoolRule,
  listRuleApplicabilityProfiles,
  listRulePool,
  reviewRuleApplicabilityProfile,
  reviewRulePoolRule,
} from '@/lib/api/rule-pool';

vi.mock('@/lib/api/rule-pool', () => ({
  listRulePool: vi.fn(),
  getRulePoolRule: vi.fn(),
  reviewRulePoolRule: vi.fn(),
  listRuleApplicabilityProfiles: vi.fn(),
  getRuleApplicabilityProfile: vi.fn(),
  generateRuleApplicabilityProfile: vi.fn(),
  reviewRuleApplicabilityProfile: vi.fn(),
}));

const mockedListRulePool = vi.mocked(listRulePool);
const mockedGetRulePoolRule = vi.mocked(getRulePoolRule);
const mockedReviewRulePoolRule = vi.mocked(reviewRulePoolRule);
const mockedListRuleApplicabilityProfiles = vi.mocked(listRuleApplicabilityProfiles);
const mockedGetRuleApplicabilityProfile = vi.mocked(getRuleApplicabilityProfile);
const mockedGenerateRuleApplicabilityProfile = vi.mocked(generateRuleApplicabilityProfile);
const mockedReviewRuleApplicabilityProfile = vi.mocked(reviewRuleApplicabilityProfile);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('RulePoolPage', () => {
  it('renders the formal rule pool workspace and submits the canonical review flow', async () => {
    const user = userEvent.setup();

    mockedListRulePool.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 18,
      items: [
        {
          rule_id: 'rule-1',
          source_type: 'standalone',
          rule_type: 'breakout',
          instrument_focus: 'stock',
          mapping_status: 'mapped',
          review_status: 'pending',
          initial_confidence: 0.61,
          validated_confidence: 0.72,
          backtest_result: { run_id: 'run-1', hit_rate: 0.65 },
          backtest_hits: 13,
          backtest_misses: 7,
          backtest_samples: 20,
          mapped: true,
          created_at: '2026-05-16T08:00:00Z',
        },
      ],
    });
    mockedGetRulePoolRule.mockResolvedValue({
      status: 'success',
      item: {
        id: '1',
        rule_id: 'rule-1',
        source_type: 'standalone',
        rule_type: 'breakout',
        instrument_focus: 'stock',
        mapping_status: 'mapped',
        review_status: 'pending',
        initial_confidence: 0.61,
        validated_confidence: 0.72,
        backtest_result: { run_id: 'run-1', hit_rate: 0.65 },
        backtest_hits: 13,
        backtest_misses: 7,
        backtest_samples: 20,
        mapped: true,
        created_at: '2026-05-16T08:00:00Z',
        source_article_ids: ['article-1'],
        extraction_layer: { raw_text: 'price above moving average', mapped_condition: { price: 'above_ma20' } },
        mapped_by: 'analyst',
        mapped_at: '2026-05-16T08:15:00Z',
        reviewed_by: null,
        reviewed_at: null,
        backtest_triggered_at: '2026-05-16T08:30:00Z',
        used_in_prediction: true,
        prediction_count: 3,
        last_used_at: '2026-05-16T09:00:00Z',
        updated_at: '2026-05-16T09:30:00Z',
      },
    });
    mockedReviewRulePoolRule.mockResolvedValue({ status: 'ok', rule_id: 'rule-1', review_status: 'approved' } as never);
    mockedListRuleApplicabilityProfiles.mockResolvedValueOnce({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 20,
      items: [
        {
          profile_id: 'profile-1',
          rule_id: 'rule-1',
          profile_version: 'rule-applicability-v1',
          source_backtest_id: 'backtest-1',
          source_rule_version: null,
          market_regime_version: 'market-regime-v3',
          source_feature_version: 'market-regime-features-v3',
          review_status: 'draft',
          min_sample_count: 5,
          confidence: 0.82,
          applicable_regimes: [
            {
              regime_label: 'strong_bull',
              decision: 'applicable',
              score: 0.71,
              sample_count: 12,
              win_rate: 0.67,
              avg_return: 0.05,
              avg_win_return: 0.08,
              avg_loss_return: -0.02,
              max_drawdown: -0.03,
              profit_factor: 1.4,
              confidence: 0.84,
              low_sample: false,
              reason: '胜率、收益和回撤综合表现较优',
              evidence: ['sample_count=12', 'win_rate=67.00%'],
            },
          ],
          blocked_regimes: [
            {
              regime_label: 'weak_bear',
              decision: 'blocked',
              score: -0.42,
              sample_count: 10,
              win_rate: 0.35,
              avg_return: -0.04,
              avg_win_return: 0.01,
              avg_loss_return: -0.06,
              max_drawdown: -0.1,
              profit_factor: 0.82,
              confidence: 0.75,
              low_sample: false,
              reason: '收益、胜率或回撤表现较差',
              evidence: ['sample_count=10'],
            },
          ],
          neutral_regimes: [],
          best_market_conditions: { summary: '胜率、收益和回撤综合表现较优', regimes: [] },
          worst_market_conditions: { summary: '收益、胜率或回撤表现较差', regimes: [] },
          summary: { total_regimes: 2, decision_counts: { applicable: 1, blocked: 1, neutral: 0 } },
          storage_ref: { source_backtest_id: 'backtest-1' },
          reviewed_by: null,
          reviewed_at: null,
          created_at: '2026-05-19T08:00:00Z',
          updated_at: '2026-05-19T08:00:00Z',
        },
      ],
    });
    mockedListRuleApplicabilityProfiles.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 20,
      items: [
        {
          profile_id: 'profile-2',
          rule_id: 'rule-1',
          profile_version: 'rule-applicability-v1',
          source_backtest_id: 'backtest-1',
          source_rule_version: null,
          market_regime_version: 'market-regime-v3',
          source_feature_version: 'market-regime-features-v3',
          review_status: 'draft',
          min_sample_count: 5,
          confidence: 0.82,
          applicable_regimes: [],
          blocked_regimes: [],
          neutral_regimes: [],
          best_market_conditions: { summary: 'n/a', regimes: [] },
          worst_market_conditions: { summary: 'n/a', regimes: [] },
          summary: { total_regimes: 0, decision_counts: { applicable: 0, blocked: 0, neutral: 0 } },
          storage_ref: { source_backtest_id: 'backtest-1' },
          reviewed_by: null,
          reviewed_at: null,
          created_at: '2026-05-19T08:30:00Z',
          updated_at: '2026-05-19T08:30:00Z',
        },
      ],
    });
    mockedGetRuleApplicabilityProfile.mockResolvedValue({
      status: 'success',
      item: {
        profile_id: 'profile-1',
        rule_id: 'rule-1',
        profile_version: 'rule-applicability-v1',
        source_backtest_id: 'backtest-1',
        source_rule_version: null,
        market_regime_version: 'market-regime-v3',
        source_feature_version: 'market-regime-features-v3',
        review_status: 'draft',
        min_sample_count: 5,
        confidence: 0.82,
        applicable_regimes: [
          {
            regime_label: 'strong_bull',
            decision: 'applicable',
            score: 0.71,
            sample_count: 12,
            win_rate: 0.67,
            avg_return: 0.05,
            avg_win_return: 0.08,
            avg_loss_return: -0.02,
            max_drawdown: -0.03,
            profit_factor: 1.4,
            confidence: 0.84,
            low_sample: false,
            reason: '胜率、收益和回撤综合表现较优',
            evidence: ['sample_count=12', 'win_rate=67.00%'],
          },
        ],
        blocked_regimes: [],
        neutral_regimes: [],
        best_market_conditions: { summary: '胜率、收益和回撤综合表现较优', regimes: [] },
        worst_market_conditions: { summary: '收益、胜率或回撤表现较差', regimes: [] },
        summary: { total_regimes: 1, decision_counts: { applicable: 1, blocked: 0, neutral: 0 } },
        storage_ref: { source_backtest_id: 'backtest-1' },
        reviewed_by: null,
        reviewed_at: null,
        created_at: '2026-05-19T08:00:00Z',
        updated_at: '2026-05-19T08:00:00Z',
      },
    });
    mockedGenerateRuleApplicabilityProfile.mockResolvedValue({
      status: 'success',
      item: {
        profile_id: 'profile-2',
        rule_id: 'rule-1',
        profile_version: 'rule-applicability-v1',
        source_backtest_id: 'backtest-1',
        source_rule_version: null,
        market_regime_version: 'market-regime-v3',
        source_feature_version: 'market-regime-features-v3',
        review_status: 'draft',
        min_sample_count: 5,
        confidence: 0.82,
        applicable_regimes: [],
        blocked_regimes: [],
        neutral_regimes: [],
        best_market_conditions: { summary: 'n/a', regimes: [] },
        worst_market_conditions: { summary: 'n/a', regimes: [] },
        summary: { total_regimes: 0, decision_counts: { applicable: 0, blocked: 0, neutral: 0 } },
        storage_ref: { source_backtest_id: 'backtest-1' },
        reviewed_by: null,
        reviewed_at: null,
        created_at: '2026-05-19T08:00:00Z',
        updated_at: '2026-05-19T08:00:00Z',
      },
    });
    mockedReviewRuleApplicabilityProfile.mockResolvedValue({
      status: 'success',
      item: {
        profile_id: 'profile-1',
        rule_id: 'rule-1',
        profile_version: 'rule-applicability-v1',
        source_backtest_id: 'backtest-1',
        source_rule_version: null,
        market_regime_version: 'market-regime-v3',
        source_feature_version: 'market-regime-features-v3',
        review_status: 'active',
        min_sample_count: 5,
        confidence: 0.82,
        applicable_regimes: [],
        blocked_regimes: [],
        neutral_regimes: [],
        best_market_conditions: { summary: 'n/a', regimes: [] },
        worst_market_conditions: { summary: 'n/a', regimes: [] },
        summary: { total_regimes: 0, decision_counts: { applicable: 0, blocked: 0, neutral: 0 } },
        storage_ref: { source_backtest_id: 'backtest-1' },
        reviewed_by: 'web',
        reviewed_at: '2026-05-19T08:30:00Z',
        created_at: '2026-05-19T08:00:00Z',
        updated_at: '2026-05-19T08:30:00Z',
      },
    });

    renderWithRouter([{ path: '/rule-pool', element: <RulePoolPage /> }], ['/rule-pool']);

    expect(await screen.findByRole('heading', { name: '规则池审核中心' })).toBeInTheDocument();
    expect(screen.getByText('规则筛选')).toBeInTheDocument();
    expect(screen.getByText('规则列表')).toBeInTheDocument();
    expect(screen.getByText('规则详情')).toBeInTheDocument();
    expect(screen.getByText('适用性画像')).toBeInTheDocument();
    expect(screen.getByText('审计历史')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '批准' })).toBeInTheDocument();

    expect(await screen.findByText('rule-1')).toBeInTheDocument();
    expect(await screen.findByText('rule-applicability-v1')).toBeInTheDocument();

    await user.type(screen.getByLabelText('回测结果 ID'), 'backtest-1');
    await user.click(screen.getByRole('button', { name: '生成画像' }));
    await waitFor(() => {
      expect(mockedGenerateRuleApplicabilityProfile).toHaveBeenCalledWith('rule-1', {
        source_backtest_id: 'backtest-1',
        profile_version: 'rule-applicability-v1',
        min_sample_count: 5,
        review_status: 'draft',
        reviewed_by: 'web',
      });
    });

    await user.click(screen.getByRole('button', { name: '激活' }));
    await waitFor(() => {
      expect(mockedReviewRuleApplicabilityProfile).toHaveBeenCalledWith('rule-1', 'profile-2', {
        review_status: 'active',
        reviewed_by: 'web',
      });
    });

    await user.click(screen.getByRole('button', { name: '批准' }));
    expect(await screen.findByRole('dialog', { name: '批准规则' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '确认提交' }));

    await waitFor(() => {
      expect(mockedReviewRulePoolRule).toHaveBeenCalledWith('rule-1', {
        decision: 'approve',
        force: true,
        reviewed_by: 'web',
      });
    });

    expect(await screen.findByText(/已提交为 approve/)).toBeInTheDocument();
  });

  it('shows an empty state when no rules match the filters', async () => {
    mockedListRulePool.mockResolvedValue({
      status: 'success',
      count: 0,
      total: 0,
      skip: 0,
      limit: 18,
      items: [],
    });
    mockedGetRulePoolRule.mockResolvedValue({ status: 'success', item: null } as never);

    renderWithRouter([{ path: '/rule-pool', element: <RulePoolPage /> }], ['/rule-pool']);

    expect(await screen.findByText('没有符合条件的规则')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重置筛选' })).toBeInTheDocument();
  });

  it('shows permission denied recovery when the canonical API rejects access', async () => {
    mockedListRulePool.mockRejectedValueOnce(new ApiError(403, 'forbidden'));
    mockedGetRulePoolRule.mockResolvedValue({ status: 'success', item: null } as never);

    renderWithRouter([{ path: '/rule-pool', element: <RulePoolPage /> }], ['/rule-pool']);

    expect(await screen.findByText('没有权限访问策略工作台')).toBeInTheDocument();
    expect(screen.getByText('请切换到有权限的账号，或联系管理员调整权限。')).toBeInTheDocument();
  });
});
