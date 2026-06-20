import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
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
});
