import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { RulePoolPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { getRulePoolRule, listRulePool, reviewRulePoolRule } from '@/lib/api/rule-pool';

vi.mock('@/lib/api/rule-pool', () => ({
  listRulePool: vi.fn(),
  getRulePoolRule: vi.fn(),
  reviewRulePoolRule: vi.fn(),
}));

const mockedListRulePool = vi.mocked(listRulePool);
const mockedGetRulePoolRule = vi.mocked(getRulePoolRule);
const mockedReviewRulePoolRule = vi.mocked(reviewRulePoolRule);

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

    renderWithRouter([{ path: '/rule-pool', element: <RulePoolPage /> }], ['/rule-pool']);

    expect(await screen.findByRole('heading', { name: '规则池审核中心' })).toBeInTheDocument();
    expect(screen.getByText('规则筛选')).toBeInTheDocument();
    expect(screen.getByText('规则列表')).toBeInTheDocument();
    expect(screen.getByText('规则详情')).toBeInTheDocument();
    expect(screen.getByText('审计历史')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '批准' })).toBeInTheDocument();

    expect(await screen.findByText('rule-1')).toBeInTheDocument();

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
