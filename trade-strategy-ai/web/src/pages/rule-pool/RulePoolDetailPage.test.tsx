import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { RulePoolDetailPage } from './RulePoolDetailPage';
import { renderWithRouter } from '@/test/test-utils';
import { createJob } from '@/lib/api/jobs';
import {
  generateRuleApplicabilityProfile,
  getRuleApplicabilityProfile,
  getRulePoolRule,
  listRuleApplicabilityProfiles,
  reviewRuleApplicabilityProfile,
  reviewRulePoolRule,
} from '@/lib/api/rule-pool';

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
}));
vi.mock('@/lib/api/rule-pool', () => ({
  generateRuleApplicabilityProfile: vi.fn(),
  getRuleApplicabilityProfile: vi.fn(),
  getRulePoolRule: vi.fn(),
  listRuleApplicabilityProfiles: vi.fn(),
  reviewRuleApplicabilityProfile: vi.fn(),
  reviewRulePoolRule: vi.fn(),
}));

const mockedCreateJob = vi.mocked(createJob);
const mockedGenerateRuleApplicabilityProfile = vi.mocked(generateRuleApplicabilityProfile);
const mockedGetRuleApplicabilityProfile = vi.mocked(getRuleApplicabilityProfile);
const mockedGetRulePoolRule = vi.mocked(getRulePoolRule);
const mockedListRuleApplicabilityProfiles = vi.mocked(listRuleApplicabilityProfiles);
const mockedReviewRuleApplicabilityProfile = vi.mocked(reviewRuleApplicabilityProfile);
const mockedReviewRulePoolRule = vi.mocked(reviewRulePoolRule);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('RulePoolDetailPage', () => {
  it('renders rule detail sections, supports review actions and submits rule backtest job', async () => {
    const user = userEvent.setup();

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
    mockedListRuleApplicabilityProfiles.mockResolvedValue({
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
    mockedReviewRulePoolRule.mockResolvedValue({ status: 'ok', rule_id: 'rule-1', review_status: 'approved' } as never);
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: {
        id: 'job-rule-1',
        job_type: 'rule-pool-backtest',
        result: null,
      },
      job_dir: '/tmp/job-rule-1',
      log_path: '/tmp/job-rule-1/job.log',
      params_path: '/tmp/job-rule-1/params.json',
      result_path: '/tmp/job-rule-1/result.json',
      artifacts_path: '/tmp/job-rule-1/artifacts.json',
    } as never);

    renderWithRouter(
      [
        { path: '/rule-pool/:ruleId', element: <RulePoolDetailPage /> },
        { path: '/jobs/:jobId', element: <div>job detail page</div> },
      ],
      ['/rule-pool/rule-1'],
    );

    expect(await screen.findByRole('heading', { level: 1, name: '规则详情' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '返回规则池' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: '规则详情' })).toBeInTheDocument();
    expect(screen.getByText('适用性画像')).toBeInTheDocument();
    expect(screen.getByText('规则回测')).toBeInTheDocument();
    expect(screen.getByText('审计历史')).toBeInTheDocument();
    expect(screen.getByText('审核动作')).toBeInTheDocument();

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

    await user.click(screen.getByRole('button', { name: '运行当前规则回测' }));
    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'rule-pool-backtest',
          params: expect.objectContaining({
            rule_id: 'rule-1',
            start_date: expect.any(String),
            end_date: expect.any(String),
            min_confidence: 0.5,
            market_regime_version: 'market-regime-v3',
          }),
        }),
      );
    });
    expect(screen.getByRole('button', { name: '前往 Job 详情' })).toBeInTheDocument();

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
});
