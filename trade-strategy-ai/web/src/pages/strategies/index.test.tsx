import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';

import { renderWithRouter } from '@/test/test-utils';
import { StrategyOverviewPage } from './StrategyOverviewPage';

vi.mock('@/lib/api/strategies', () => ({
  listStrategies: vi.fn(),
  getStrategyDraftOptions: vi.fn(),
  createStrategyDraft: vi.fn(),
  submitStrategyReview: vi.fn(),
  publishStrategy: vi.fn(),
}));

import {
  createStrategyDraft,
  getStrategyDraftOptions,
  listStrategies,
  publishStrategy,
  submitStrategyReview,
} from '@/lib/api/strategies';

const ruleVersionId = '11111111-1111-1111-1111-111111111111';
const methodProfileId = '22222222-2222-2222-2222-222222222222';
const ruleProfileId = '33333333-3333-3333-3333-333333333333';
const validatedProfileId = '44444444-4444-4444-4444-444444444444';
const datasetSnapshotId = '55555555-5555-5555-5555-555555555555';
const marketSnapshotId = '66666666-6666-6666-6666-666666666666';
const applicabilityProfileId = '77777777-7777-7777-7777-777777777777';

describe('strategies page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows current formal strategy status instead of compatibility candidate copy', async () => {
    vi.mocked(listStrategies).mockResolvedValueOnce({
      state: 'ready',
      current_strategy: { business_key: 'cn-swing-core', current_version_id: 'version-2' },
      count: 1,
      items: [
        {
          strategy_version_id: 'version-2',
          strategy_id: 'strategy-1',
          business_key: 'cn-swing-core',
          title: 'A股趋势轮动策略',
          summary: '正式策略版本',
          version_no: 2,
          lifecycle_state: 'published',
          lifecycle_label: '已发布',
          review_status: 'published',
          status_state: 'published',
          schema_version: 'strategy-schema-v1',
          quality_status: 'verified',
          rule_pool: [{ rule_version_id: ruleVersionId, title: '放量突破', base_weight: 0.65, status: 'active', configuration_json: {} }],
          profiles: {
            author_method_profile_version_id: methodProfileId,
            author_rule_profile_version_id: ruleProfileId,
            author_validated_profile_version_id: validatedProfileId,
          },
          policies: {
            risk_policy_json: { position_constraints: { single_position_pct: 0.2, total_position_pct: 0.8 } },
            selection_policy_json: { degradation_policy: { missing_canonical_data: 'unavailable' } },
            universe_json: { market: 'CN', boards: ['主板'] },
          },
          evidence: {
            dataset_snapshot_id: datasetSnapshotId,
            market_snapshot_ids: [marketSnapshotId],
            rule_applicability_profile_ids: [applicabilityProfileId],
            backtest_run_ids: ['backtest-run-1'],
            backtest_result_ids: ['backtest-result-1'],
            evidence_fingerprint: 'fp-1',
          },
          current_status: { is_current: true, current_version_id: 'version-2', previous_current_version_id: 'version-1' },
          published_at: '2026-06-20T12:00:00+00:00',
          partial_reasons: [],
          limitations: [],
        },
      ],
    });
    vi.mocked(getStrategyDraftOptions).mockResolvedValueOnce({
      rule_options: [],
      author_profile_options: { method: [], rule: [], validated: [] },
      dataset_options: [],
      market_snapshot_options: [],
      rule_applicability_options: [],
    });

    renderWithRouter([{ path: '/strategies', element: <StrategyOverviewPage /> }], ['/strategies']);

    expect(await screen.findByText('A股趋势轮动策略')).toBeInTheDocument();
    expect(screen.getAllByText('当前正式策略').length).toBeGreaterThan(0);
    expect(screen.getByText(/已发布/)).toBeInTheDocument();
    expect(screen.getByText('规则池')).toBeInTheDocument();
    expect(screen.getByText('放量突破')).toBeInTheDocument();
    expect(screen.queryByText(/正式策略版本尚未建立/)).not.toBeInTheDocument();
  });

  it('creates a canonical strategy draft and submits and publishes it', async () => {
    vi.mocked(listStrategies).mockResolvedValue({
      state: 'empty',
      current_strategy: null,
      count: 0,
      items: [],
    });
    vi.mocked(getStrategyDraftOptions).mockResolvedValue({
      rule_options: [{ rule_version_id: ruleVersionId, title: '放量突破', rule_type: 'entry', canonical_fingerprint: 'fp-rule-1' }],
      author_profile_options: {
        method: [{ author_profile_version_id: methodProfileId, label: '作者方法画像 v1', author_id: 'author-1' }],
        rule: [{ author_profile_version_id: ruleProfileId, label: '作者规则画像 v1', author_id: 'author-1' }],
        validated: [{ author_profile_version_id: validatedProfileId, label: '作者验证画像 v1', author_id: 'author-1' }],
      },
      dataset_options: [{ dataset_snapshot_id: datasetSnapshotId, label: 'OHLCV 2026-06-19', content_fingerprint: 'fp-dataset-1' }],
      market_snapshot_options: [{ market_snapshot_id: marketSnapshotId, label: '2026-06-19 17-30 市场快照', content_fingerprint: 'fp-market-1' }],
      rule_applicability_options: [{ applicability_profile_id: applicabilityProfileId, label: '放量突破 适用性画像', dataset_snapshot_id: datasetSnapshotId }],
    });
    vi.mocked(createStrategyDraft).mockResolvedValueOnce({
      strategy_version_id: 'version-1',
      strategy_id: 'strategy-1',
      business_key: 'cn-swing-core',
      title: 'A股趋势轮动策略',
      summary: '正式策略草稿',
      version_no: 1,
      lifecycle_state: 'draft',
      lifecycle_label: '草稿',
      review_status: 'draft',
      status_state: 'draft',
      schema_version: 'strategy-schema-v1',
      quality_status: 'verified',
      rule_pool: [{ rule_version_id: ruleVersionId, title: '放量突破', base_weight: 0.65, status: 'active', configuration_json: {} }],
      profiles: {
        author_method_profile_version_id: methodProfileId,
        author_rule_profile_version_id: ruleProfileId,
        author_validated_profile_version_id: validatedProfileId,
      },
      policies: {
        risk_policy_json: { position_constraints: { single_position_pct: 0.2 } },
        selection_policy_json: { degradation_policy: { missing_canonical_data: 'unavailable' } },
        universe_json: { market: 'CN' },
      },
      evidence: {
        dataset_snapshot_id: datasetSnapshotId,
        market_snapshot_ids: [marketSnapshotId],
        rule_applicability_profile_ids: [applicabilityProfileId],
        backtest_run_ids: [],
        backtest_result_ids: [],
        evidence_fingerprint: 'fp-evidence-1',
      },
      current_status: { is_current: false, current_version_id: null, previous_current_version_id: null },
      partial_reasons: [],
      limitations: [],
    });
    vi.mocked(submitStrategyReview).mockResolvedValueOnce({
      strategy_version_id: 'version-1',
      lifecycle_state: 'pending_review',
    });
    vi.mocked(publishStrategy).mockResolvedValueOnce({
      strategy_version_id: 'version-1',
      lifecycle_state: 'published',
    });

    renderWithRouter([{ path: '/strategies', element: <StrategyOverviewPage /> }], ['/strategies']);

    fireEvent.change(await screen.findByLabelText('策略标识'), { target: { value: 'cn-swing-core' } });
    fireEvent.change(screen.getByLabelText('策略名称'), { target: { value: 'A股趋势轮动策略' } });
    fireEvent.change(screen.getByLabelText('策略摘要'), { target: { value: '正式策略草稿' } });
    fireEvent.change(screen.getByLabelText('正式规则'), { target: { value: ruleVersionId } });
    fireEvent.change(screen.getByLabelText('作者方法画像'), { target: { value: methodProfileId } });
    fireEvent.change(screen.getByLabelText('作者规则画像'), { target: { value: ruleProfileId } });
    fireEvent.change(screen.getByLabelText('作者验证画像'), { target: { value: validatedProfileId } });
    fireEvent.change(screen.getByLabelText('数据集快照'), { target: { value: datasetSnapshotId } });
    fireEvent.change(screen.getByLabelText('市场快照'), { target: { value: marketSnapshotId } });
    fireEvent.change(screen.getByLabelText('规则适用性画像'), { target: { value: applicabilityProfileId } });

    fireEvent.click(screen.getByRole('button', { name: '保存策略草稿' }));

    await waitFor(() => {
      expect(createStrategyDraft).toHaveBeenCalledWith(
        expect.objectContaining({
          business_key: 'cn-swing-core',
          title: 'A股趋势轮动策略',
          author_method_profile_version_id: methodProfileId,
          evidence_json: expect.objectContaining({ dataset_snapshot_id: datasetSnapshotId }),
        }),
      );
    });

    expect(await screen.findByText('已保存策略草稿')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '提交审核' }));
    await waitFor(() => expect(submitStrategyReview).toHaveBeenCalledWith('version-1', { reason: '提交策略审核' }));

    fireEvent.click(screen.getByRole('button', { name: '发布为当前策略' }));
    await waitFor(() => expect(publishStrategy).toHaveBeenCalledWith('version-1', { reason: '发布正式策略' }));
  });
});
