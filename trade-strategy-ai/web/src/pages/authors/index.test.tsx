import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { ApiError } from '@/lib/api/http';
import { AuthorsPage } from './index';

vi.mock('@/lib/api/authors', () => ({
  listAuthorProfiles: vi.fn(),
}));

import { listAuthorProfiles } from '@/lib/api/authors';

describe('authors page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows empty formal profile state without legacy persona fallback', async () => {
    vi.mocked(listAuthorProfiles).mockResolvedValueOnce({ state: 'empty', items: [], count: 0 });

    renderWithRouter([{ path: '/authors', element: <AuthorsPage /> }], ['/authors']);

    expect(await screen.findAllByText('暂无正式画像版本')).toHaveLength(2);
    expect(screen.getByText('新证据会先生成草稿或修订建议，不会自动覆盖已发布画像。')).toBeInTheDocument();
    expect(screen.queryByText('交易风格画像')).not.toBeInTheDocument();
  });

  it('shows unavailable state when the formal author profile API is unavailable', async () => {
    vi.mocked(listAuthorProfiles).mockRejectedValueOnce(new ApiError(503, 'service unavailable'));

    renderWithRouter([{ path: '/authors', element: <AuthorsPage /> }], ['/authors']);

    expect(await screen.findAllByText('当前不可用')).toHaveLength(2);
    expect(screen.getByText('相关服务或数据暂时不可用。')).toBeInTheDocument();
    expect(screen.getByText('作者画像读取失败')).toBeInTheDocument();
  });

  it('shows draft, pending review, published, archived and partial evidence states truthfully', async () => {
    vi.mocked(listAuthorProfiles).mockResolvedValueOnce({
      state: 'partial',
      count: 4,
      items: [
        {
          author_profile_version_id: 'apv-1',
          author_profile_id: 'ap-1',
          author_id: 'author-1',
          profile_kind: 'method',
          profile_kind_label: '作者方法画像',
          version_no: 1,
          lifecycle_state: 'draft',
          lifecycle_label: '草稿',
          review_status: 'draft',
          status_state: 'partial',
          schema_version: 'author-profile-v1',
          prompt_version: 'author_method_profile_batch_v1',
          evidence_period: { from: null, to: null },
          effective_period: { from: null, to: null },
          source_versions: {},
          evidence_fingerprint: null,
          profile_fingerprint: null,
          quality_status: 'partial',
          partial_reasons: ['证据区间不完整，当前画像只能作为部分证据查看。'],
          limitations: [],
          payload: {},
          evidence: {},
          source_bindings: {},
          supersession: {},
        },
        {
          author_profile_version_id: 'apv-2',
          author_profile_id: 'ap-1',
          author_id: 'author-1',
          profile_kind: 'rule',
          profile_kind_label: '作者规则画像',
          version_no: 2,
          lifecycle_state: 'pending_review',
          lifecycle_label: '待审核',
          review_status: 'pending_review',
          status_state: 'pending_review',
          schema_version: 'author-profile-v1',
          evidence_period: { from: '2026-01-01', to: '2026-03-31' },
          effective_period: { from: '2026-04-01', to: null },
          source_versions: { rules: 'v1' },
          evidence_fingerprint: 'e2',
          profile_fingerprint: 'p2',
          quality_status: 'complete',
          partial_reasons: [],
          limitations: [],
          payload: {},
          evidence: {},
          source_bindings: {},
          supersession: {},
        },
        {
          author_profile_version_id: 'apv-3',
          author_profile_id: 'ap-1',
          author_id: 'author-1',
          profile_kind: 'validated',
          profile_kind_label: '作者验证画像',
          version_no: 3,
          lifecycle_state: 'published',
          lifecycle_label: '已发布',
          review_status: 'published',
          status_state: 'published',
          schema_version: 'author-profile-v1',
          evidence_period: { from: '2026-01-01', to: '2026-03-31' },
          effective_period: { from: '2026-04-01', to: null },
          source_versions: { backtests: 'v1' },
          evidence_fingerprint: 'e3',
          profile_fingerprint: 'p3',
          quality_status: 'verified',
          partial_reasons: [],
          limitations: [],
          payload: {},
          evidence: {},
          source_bindings: {},
          supersession: {},
        },
        {
          author_profile_version_id: 'apv-4',
          author_profile_id: 'ap-1',
          author_id: 'author-1',
          profile_kind: 'method',
          profile_kind_label: '作者方法画像',
          version_no: 4,
          lifecycle_state: 'archived',
          lifecycle_label: '已归档',
          review_status: 'archived',
          status_state: 'archived',
          schema_version: 'author-profile-v1',
          evidence_period: { from: '2025-01-01', to: '2025-12-31' },
          effective_period: { from: '2026-01-01', to: '2026-03-31' },
          source_versions: { articles: 'v1' },
          evidence_fingerprint: 'e4',
          profile_fingerprint: 'p4',
          quality_status: 'verified',
          partial_reasons: [],
          limitations: [],
          payload: {},
          evidence: {},
          source_bindings: {},
          supersession: {},
        },
      ],
    });

    renderWithRouter([{ path: '/authors', element: <AuthorsPage /> }], ['/authors']);

    expect(await screen.findByText('作者方法画像 v1')).toBeInTheDocument();
    expect(screen.getByText('作者规则画像 v2')).toBeInTheDocument();
    expect(screen.getByText('作者验证画像 v3')).toBeInTheDocument();
    expect(screen.getByText('作者方法画像 v4')).toBeInTheDocument();
    expect(screen.getByText('证据区间不完整，当前画像只能作为部分证据查看。')).toBeInTheDocument();
    expect(screen.getAllByText(/不是作者真实实盘收益描述/)).toHaveLength(4);
  });

  it('shows method-profile details from formal payload instead of legacy persona text', async () => {
    vi.mocked(listAuthorProfiles).mockResolvedValueOnce({
      state: 'partial',
      count: 1,
      items: [
        {
          author_profile_version_id: 'apv-1',
          author_profile_id: 'ap-1',
          author_id: 'author-1',
          profile_kind: 'method',
          profile_kind_label: '作者方法画像',
          version_no: 1,
          lifecycle_state: 'draft',
          lifecycle_label: '草稿',
          review_status: 'draft',
          status_state: 'partial',
          schema_version: 'author-profile-v1',
          prompt_version: 'author_method_profile_batch_v1',
          evidence_period: { from: '2026-01-01', to: '2026-01-10' },
          effective_period: { from: '2026-01-11', to: null },
          source_versions: {},
          evidence_fingerprint: null,
          profile_fingerprint: null,
          quality_status: 'partial',
          partial_reasons: ['证据区间不完整，当前画像只能作为部分证据查看。'],
          limitations: ['画像来自结构化文章表达，不代表真实实盘表现。'],
          payload: {
            method_profile: {
              trading_style: [{ name: '趋势突破' }],
              analysis_framework: [{ name: '量价共振' }],
              stock_selection_preference: [{ name: '强势股' }],
            },
            conclusions: [],
          },
          evidence: {},
          source_bindings: {},
          supersession: {},
        },
      ],
    });

    renderWithRouter([{ path: '/authors', element: <AuthorsPage /> }], ['/authors']);

    expect(await screen.findByText('交易风格')).toBeInTheDocument();
    expect(screen.getByText('趋势突破')).toBeInTheDocument();
    expect(screen.getByText('分析框架')).toBeInTheDocument();
    expect(screen.getByText('量价共振')).toBeInTheDocument();
    expect(screen.queryByText('交易风格画像')).not.toBeInTheDocument();
  });

  it('shows rule-profile details from formal rule evidence instead of legacy rule-pool terms', async () => {
    vi.mocked(listAuthorProfiles).mockResolvedValueOnce({
      state: 'ready',
      count: 1,
      items: [
        {
          author_profile_version_id: 'apv-rule-1',
          author_profile_id: 'ap-rule-1',
          author_id: 'author-1',
          profile_kind: 'rule',
          profile_kind_label: '作者规则画像',
          version_no: 1,
          lifecycle_state: 'pending_review',
          lifecycle_label: '待审核',
          review_status: 'pending_review',
          status_state: 'pending_review',
          schema_version: 'author-profile-v1',
          evidence_period: { from: '2026-01-01', to: '2026-03-31' },
          effective_period: { from: '2026-04-01', to: null },
          source_versions: {},
          evidence_fingerprint: 'rule-e1',
          profile_fingerprint: 'rule-p1',
          quality_status: 'complete',
          partial_reasons: [],
          limitations: ['画像来自已审核的规则与规则族证据，不代表作者真实实盘表现。'],
          payload: {
            rule_profile: {
              rule_type_distribution: [{ rule_type: 'entry', count: 2, share: 1 }],
              rule_families: [{ name: '放量突破族', member_count: 2 }],
              quantifiability: { label: '部分可量化' },
              data_dependencies: [{ name: 'ohlcv_1d', count: 2 }],
              repeat_conflict_summary: { conflict_pair_count: 1 },
              representative_rules: [{ title: '放量突破介入' }],
            },
            conclusions: [],
          },
          evidence: {},
          source_bindings: {},
          supersession: {},
        },
      ],
    });

    renderWithRouter([{ path: '/authors', element: <AuthorsPage /> }], ['/authors']);

    expect(await screen.findByText('规则类型分布')).toBeInTheDocument();
    expect(screen.getByText('entry：2 条')).toBeInTheDocument();
    expect(screen.getByText('规则族')).toBeInTheDocument();
    expect(screen.getByText('放量突破族（2 条）')).toBeInTheDocument();
    expect(screen.getByText('可量化程度')).toBeInTheDocument();
    expect(screen.getByText('部分可量化')).toBeInTheDocument();
    expect(screen.getByText('重复与冲突')).toBeInTheDocument();
    expect(screen.getByText('发现 1 组冲突规则')).toBeInTheDocument();
    expect(screen.queryByText('rule pool')).not.toBeInTheDocument();
  });

  it('shows validated-profile details from formal backtest and适用性证据', async () => {
    vi.mocked(listAuthorProfiles).mockResolvedValueOnce({
      state: 'partial',
      count: 1,
      items: [
        {
          author_profile_version_id: 'apv-validated-1',
          author_profile_id: 'ap-validated-1',
          author_id: 'author-1',
          profile_kind: 'validated',
          profile_kind_label: '作者验证画像',
          version_no: 1,
          lifecycle_state: 'draft',
          lifecycle_label: '草稿',
          review_status: 'draft',
          status_state: 'partial',
          schema_version: 'author-profile-v1',
          evidence_period: { from: '2026-01-01', to: '2026-03-31' },
          effective_period: { from: '2026-04-01', to: null },
          source_versions: {},
          evidence_fingerprint: 'validated-e1',
          profile_fingerprint: 'validated-p1',
          quality_status: 'partial',
          partial_reasons: ['样本不足时只能作为部分验证证据查看。'],
          limitations: ['缺失 Kaipan 数据只会记为覆盖限制，不会被当成规则失败。'],
          payload: {
            validated_profile: {
              strong_rule_types: [{ rule_type: 'entry', count: 2 }],
              weak_rule_types: [{ rule_type: 'exit', count: 1 }],
              strong_market_states: [{ market_state: '强势上行', count: 2 }],
              weak_market_states: [{ market_state: '情绪退潮', count: 1 }],
              common_failure_modes: [{ reason: '情绪退潮时回撤扩大', count: 1 }],
              data_coverage: { total_applicability_profiles: 2, kaipan_limitation_profiles: 1 },
              sample_count: { total: 21, insufficient_sample_profiles: 1 },
              confidence: { overall: 0.58 },
            },
            conclusions: [],
          },
          evidence: {},
          source_bindings: {},
          supersession: {},
        },
      ],
    });

    renderWithRouter([{ path: '/authors', element: <AuthorsPage /> }], ['/authors']);

    expect(await screen.findByText('优势规则类型')).toBeInTheDocument();
    expect(screen.getByText('entry：2 条')).toBeInTheDocument();
    expect(screen.getByText('弱势规则类型')).toBeInTheDocument();
    expect(screen.getByText('exit：1 条')).toBeInTheDocument();
    expect(screen.getByText('优势市场状态')).toBeInTheDocument();
    expect(screen.getByText('强势上行：2 次')).toBeInTheDocument();
    expect(screen.getByText('弱势市场状态')).toBeInTheDocument();
    expect(screen.getByText('情绪退潮：1 次')).toBeInTheDocument();
    expect(screen.getByText('常见失效模式')).toBeInTheDocument();
    expect(screen.getByText('情绪退潮时回撤扩大（1 次）')).toBeInTheDocument();
    expect(screen.getByText('样本量')).toBeInTheDocument();
    expect(screen.getByText(/21（样本不足画像 1 条）/)).toBeInTheDocument();
    expect(screen.getByText('缺失 Kaipan 数据只会记为覆盖限制，不会被当成规则失败。')).toBeInTheDocument();
    expect(screen.queryByText('Regime')).not.toBeInTheDocument();
  });
});
