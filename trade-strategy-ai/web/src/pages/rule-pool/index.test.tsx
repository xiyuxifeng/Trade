import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { RulePoolPage } from './index';
import { RulePoolDetailPage } from './RulePoolDetailPage';
import { renderWithRouter } from '@/test/test-utils';
import { listRulePool, listRulePoolFilterOptions } from '@/lib/api/rule-pool';

vi.mock('@/lib/api/rule-pool', () => ({
  listRulePool: vi.fn(),
  listRulePoolFilterOptions: vi.fn(),
}));

const mockedListRulePool = vi.mocked(listRulePool);
const mockedListRulePoolFilterOptions = vi.mocked(listRulePoolFilterOptions);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('RulePoolPage', () => {
  it('renders filter dropdowns, searches the full rule data source and navigates to detail', async () => {
    const user = userEvent.setup();

    mockedListRulePoolFilterOptions.mockResolvedValue({
      status: 'success',
      review_statuses: ['pending', 'approved', 'rejected'],
      mapping_statuses: ['mapped', 'unmapped'],
      source_types: ['standalone', 'derived', 'experience'],
      rule_types: ['breakout', 'pullback'],
      instrument_focuses: ['mixed', 'stock'],
    });
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

    renderWithRouter(
      [
        { path: '/rule-pool', element: <RulePoolPage /> },
        { path: '/rule-pool/:ruleId', element: <RulePoolDetailPage /> },
      ],
      ['/rule-pool'],
    );

    expect(await screen.findByRole('heading', { name: '规则池审核中心' })).toBeInTheDocument();
    expect(screen.getByText('规则筛选')).toBeInTheDocument();
    expect(screen.getByText('规则概览与列表')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '搜索' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '刷新' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('仅显示已映射规则')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(mockedListRulePoolFilterOptions).toHaveBeenCalled();
      expect(mockedListRulePool).toHaveBeenCalledWith({
        status: 'pending',
        rule_type: undefined,
        mapping_status: undefined,
        source_type: undefined,
        instrument_focus: undefined,
        skip: 0,
        limit: 18,
      });
    });

    await user.selectOptions(screen.getByLabelText('规则类型'), 'pullback');
    await user.selectOptions(screen.getByLabelText('映射状态'), 'mapped');
    await user.click(screen.getByRole('button', { name: '搜索' }));

    await waitFor(() => {
      expect(mockedListRulePool).toHaveBeenLastCalledWith({
        status: 'pending',
        rule_type: 'pullback',
        mapping_status: 'mapped',
        source_type: undefined,
        instrument_focus: undefined,
        skip: 0,
        limit: 18,
      });
    });

    expect(await screen.findByText('rule-1')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '查看详情 rule-1' }));
    expect(await screen.findByRole('heading', { level: 1, name: '规则详情' })).toBeInTheDocument();
  });

  it('shows an empty state when no rules match the filters', async () => {
    mockedListRulePoolFilterOptions.mockResolvedValue({
      status: 'success',
      review_statuses: ['pending'],
      mapping_statuses: ['mapped', 'unmapped'],
      source_types: ['standalone'],
      rule_types: [],
      instrument_focuses: [],
    });
    mockedListRulePool.mockResolvedValue({
      status: 'success',
      count: 0,
      total: 0,
      skip: 0,
      limit: 18,
      items: [],
    });

    renderWithRouter([{ path: '/rule-pool', element: <RulePoolPage /> }], ['/rule-pool']);

    expect(await screen.findByText('没有符合条件的规则')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重置' })).toBeInTheDocument();
  });
});
