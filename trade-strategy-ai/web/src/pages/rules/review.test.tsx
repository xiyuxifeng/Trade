import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ApiError } from '@/lib/api/http';
import { renderWithRouter } from '@/test/test-utils';
import { RulesReviewPage } from './index';
import {
  getRuleReviewCandidate,
  listRuleReviewCandidates,
  submitRuleReviewAction,
} from '@/lib/api/rule-review';

vi.mock('@/lib/api/rule-review', () => ({
  listRuleReviewCandidates: vi.fn(),
  getRuleReviewCandidate: vi.fn(),
  submitRuleReviewAction: vi.fn(),
}));

const mockedListRuleReviewCandidates = vi.mocked(listRuleReviewCandidates);
const mockedGetRuleReviewCandidate = vi.mocked(getRuleReviewCandidate);
const mockedSubmitRuleReviewAction = vi.mocked(submitRuleReviewAction);

beforeEach(() => {
  mockedListRuleReviewCandidates.mockReset();
  mockedGetRuleReviewCandidate.mockReset();
  mockedSubmitRuleReviewAction.mockReset();
});

describe('RulesReviewPage', () => {
  it('renders loading and then candidate detail with business actions', async () => {
    const user = userEvent.setup();
    mockedListRuleReviewCandidates.mockResolvedValueOnce({
      count: 1,
      total: 1,
      items: [
        {
          candidate_id: 'candidate-1',
          title: '低风险规则',
          source_article_title: '示例文章',
          automatic_review: {
            status: 'recommend_pass',
            label: '建议通过',
            risk_level: 'low',
            reasons: ['证据完整'],
            requires_human_review: false,
          },
          current_review_state: '待审核',
          lifecycle_state: '候选',
          allowed_actions: [{ key: 'approve', label: '批准' }],
        },
      ],
    });
    mockedGetRuleReviewCandidate.mockResolvedValueOnce({
      candidate_id: 'candidate-1',
      title: '低风险规则',
      source_article: {
        title: '示例文章',
        summary: '冻结摘要',
        published_at: '2026-06-16T10:00:00Z',
      },
      automatic_review: {
        status: 'recommend_pass',
        label: '建议通过',
        risk_level: 'low',
        reasons: ['证据完整'],
        requires_human_review: false,
      },
      current_review_state: '待审核',
      current_lifecycle_state: '候选',
      missing_fields: [],
      data_dependencies: ['ohlcv_1d'],
      governance: { related_rules: [] },
      lifecycle: { allowed_next_actions: [] },
      history: [],
      allowed_actions: [{ key: 'approve', label: '批准' }],
      rule_version_id: null,
    });
    mockedSubmitRuleReviewAction.mockResolvedValueOnce({
      candidate_id: 'candidate-1',
      current_review_state: '已批准',
      current_lifecycle_state: '已批准',
      rule_version_id: 'rule-version-1',
      last_action: 'approve',
      allowed_actions: [],
    });

    renderWithRouter([{ path: '/rules/review', element: <RulesReviewPage /> }], ['/rules/review']);

    expect(screen.getByText('正在加载页面')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: '规则审核工作台' })).toBeInTheDocument();
    expect(await screen.findByText('低风险规则')).toBeInTheDocument();
    expect(await screen.findByText('建议通过')).toBeInTheDocument();
    expect(await screen.findByText('冻结摘要')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '批准' }));
    await waitFor(() => {
      expect(mockedSubmitRuleReviewAction).toHaveBeenCalledWith(
        'candidate-1',
        expect.objectContaining({ action: 'approve' }),
      );
    });
  });

  it('shows empty state', async () => {
    mockedListRuleReviewCandidates.mockResolvedValueOnce({
      count: 0,
      total: 0,
      items: [],
    });

    renderWithRouter([{ path: '/rules/review', element: <RulesReviewPage /> }], ['/rules/review']);

    expect(await screen.findByText('当前没有需要处理的候选规则')).toBeInTheDocument();
  });

  it('shows permission denied, partial and error states truthfully', async () => {
    mockedListRuleReviewCandidates.mockRejectedValueOnce(new ApiError(403, 'permission denied'));
    const denied = renderWithRouter([{ path: '/rules/review', element: <RulesReviewPage /> }], ['/rules/review']);
    expect(await screen.findByText('没有权限')).toBeInTheDocument();
    denied.unmount();

    mockedListRuleReviewCandidates.mockResolvedValueOnce({
      count: 1,
      total: 1,
      items: [
        {
          candidate_id: 'candidate-2',
          title: '资料不完整规则',
          source_article_title: '示例文章',
          automatic_review: {
            status: 'manual_review',
            label: '人工审核',
            risk_level: 'high',
            reasons: ['摘要暂不可用'],
            requires_human_review: true,
            blocked_reason: 'summary_unavailable',
          },
          current_review_state: '待审核',
          lifecycle_state: '候选',
          allowed_actions: [],
        },
      ],
    });
    mockedGetRuleReviewCandidate.mockResolvedValueOnce({
      candidate_id: 'candidate-2',
      title: '资料不完整规则',
      source_article: {
        title: '示例文章',
        summary: null,
        summary_status: 'unavailable',
      },
      automatic_review: {
        status: 'manual_review',
        label: '人工审核',
        risk_level: 'high',
        reasons: ['摘要暂不可用'],
        requires_human_review: true,
        blocked_reason: 'summary_unavailable',
      },
      current_review_state: '待审核',
      current_lifecycle_state: '候选',
      missing_fields: ['summary'],
      data_dependencies: [],
      governance: { related_rules: [] },
      lifecycle: { allowed_next_actions: [] },
      history: [],
      allowed_actions: [],
      rule_version_id: null,
    });
    const partial = renderWithRouter([{ path: '/rules/review', element: <RulesReviewPage /> }], ['/rules/review']);
    expect(await screen.findByText('部分信息暂不可用')).toBeInTheDocument();
    partial.unmount();

    mockedListRuleReviewCandidates.mockRejectedValueOnce(new ApiError(500, 'server error'));
    renderWithRouter([{ path: '/rules/review', element: <RulesReviewPage /> }], ['/rules/review']);
    expect(await screen.findByText('加载失败')).toBeInTheDocument();
  });
});
