import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { VersionsPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listProfiles, getProfile } from '@/lib/api/profiles';
import { listArtifacts } from '@/lib/api/artifacts';
import { listArticleMetadataSummary } from '@/lib/api/article-metadata';
import { listStrategyVersions, getStrategyVersion } from '@/lib/api/strategyStudio';
import { createJob } from '@/lib/api/jobs';
import { listTraderOptions } from '@/lib/api/traders';

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
  getProfile: vi.fn(),
}));

vi.mock('@/lib/api/artifacts', () => ({
  listArtifacts: vi.fn(),
}));

vi.mock('@/lib/api/article-metadata', () => ({
  listArticleMetadataSummary: vi.fn(),
}));

vi.mock('@/lib/api/strategyStudio', () => ({
  listStrategyVersions: vi.fn(),
  getStrategyVersion: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
}));

vi.mock('@/lib/api/traders', () => ({
  listTraderOptions: vi.fn(),
}));

const mockedListProfiles = vi.mocked(listProfiles);
const mockedGetProfile = vi.mocked(getProfile);
const mockedListArtifacts = vi.mocked(listArtifacts);
const mockedListArticleMetadataSummary = vi.mocked(listArticleMetadataSummary);
const mockedListStrategyVersions = vi.mocked(listStrategyVersions);
const mockedGetStrategyVersion = vi.mocked(getStrategyVersion);
const mockedCreateJob = vi.mocked(createJob);
const mockedListTraderOptions = vi.mocked(listTraderOptions);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('VersionsPage', () => {
  it('shows version details and submits strategy-build with profile_id only', async () => {
    const user = userEvent.setup();

    mockedListProfiles.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 50,
      items: [
        {
          profile_id: 'default',
          name: '默认配置',
          environment: 'production',
          version: 3,
          sections: {},
          secret_refs: {},
          validation_status: 'validated',
          created_by: 'web',
          created_at: '2026-05-16T00:00:00Z',
          updated_at: '2026-05-16T00:00:00Z',
          archived_at: null,
        },
      ],
    } as never);
    mockedGetProfile.mockResolvedValue({
      profile: {
        profile_id: 'default',
        name: '默认配置',
        environment: 'production',
        version: 3,
        sections: {},
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T00:00:00Z',
        updated_at: '2026-05-16T00:00:00Z',
        archived_at: null,
      },
      linked_jobs: [],
      snapshots: [
        {
          snapshot_id: 'snap-2',
          profile_id: 'default',
          job_id: 'job-2',
          source: 'import',
          config_path: 'config/strategy-v3.yaml',
          config_hash: 'hash-2',
          masked_snapshot: {},
          masked_sections: [],
          validation_status: 'validated',
          captured_at: '2026-05-16T08:00:00Z',
          snapshot_path: 'ignored',
        },
      ],
    } as never);
    mockedListStrategyVersions.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [
        {
          version_id: 'trader_a_2026-05-16_released',
          trader_id: 'trader_a',
          strategy_date: '2026-05-16',
          status: 'released',
          version_type: 'daily',
          parent_version_id: null,
          recommendations_count: 2,
          source_article_ids_count: 1,
          released_at: '2026-05-16T03:00:00Z',
          has_rules_snapshot: true,
        },
      ],
    } as never);
    mockedGetStrategyVersion.mockResolvedValue({
      status: 'success',
      item: {
        version_id: 'trader_a_2026-05-16_released',
        trader_id: 'trader_a',
        strategy_date: '2026-05-16',
        status: 'released',
        version_type: 'daily',
        parent_version_id: null,
        recommendations: [
          {
            symbol: '000001.SZ',
            decision: 'buy',
            confidence: 0.91,
            entry_price: 10,
            target_price: 11,
            stop_loss_price: 9,
            volume: 100,
            rationale: 'trend confirmed',
            evidence_refs: ['evidence-1'],
          },
        ],
        source_article_ids: ['article-1'],
        evidence_refs: ['evidence-1'],
        notes: 'latest released version',
        released_at: '2026-05-16T03:00:00Z',
        rules_snapshot: [{ rule_id: 'rule-1' }],
        regime_selection: {
          selection_id: 'sel-1',
          snapshot_id: 'snap-2',
          market_regime_version: 'market-regime-v3',
          source_feature_version: 'market-regime-features-v3',
          applicability_profile_version: 'rule-applicability-v1',
          selected_by: 'web',
          confidence: 0.91,
          quality_status: 'ok',
        },
      },
    } as never);
    mockedListArticleMetadataSummary.mockResolvedValue({
      items: [
        {
          article_id: 'article-1',
          selected_schema_version: 'v1',
          selected_by: 'web',
          selected_at: '2026-05-16T08:00:00Z',
          selection_mode: 'auto',
          selection_score: 4.7,
          selection_reason: '自动推荐',
          recommended_schema_version: 'v1',
          recommended_score: 4.7,
          recommended_reason: '自动推荐',
          effective_schema_version: 'v1',
          effective_score: 4.7,
          effective_reason: '自动推荐',
          warning: null,
          candidates: [],
        },
      ],
    } as never);
    mockedListArtifacts.mockResolvedValue({ count: 0, total: 0, skip: 0, limit: 24, items: [] } as never);
    mockedListTraderOptions.mockResolvedValue({
      status: 'success',
      count: 2,
      items: ['trader_a', 'trader_b'],
    } as never);
    mockedCreateJob.mockResolvedValue({
      created: true,
      job: { id: 'job-build-1' },
      job_dir: '/tmp/job-build-1',
      log_path: '/tmp/job-build-1/job.log',
      params_path: '/tmp/job-build-1/params.json',
      result_path: '/tmp/job-build-1/result.json',
      artifacts_path: '/tmp/job-build-1/artifacts',
    } as never);

    renderWithRouter([{ path: '/strategies/versions', element: <VersionsPage /> }], ['/strategies/versions']);

    expect(await screen.findByRole('heading', { name: '规则版本' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '返回概览' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '搜索' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重置' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /构建规则版本/ })).toBeInTheDocument();
    expect((await screen.findAllByText('trader_a_2026-05-16_released')).length).toBeGreaterThan(0);
    expect(screen.getByText('latest released version')).toBeInTheDocument();
    expect(await screen.findByText('来源文章版本信息')).toBeInTheDocument();
    expect(screen.getByText('article-1')).toBeInTheDocument();
    expect(mockedListTraderOptions).toHaveBeenCalledWith({ source: 'strategy' });
    expect(mockedListArticleMetadataSummary).toHaveBeenCalledWith(['article-1']);

    fireEvent.change(screen.getByLabelText('执行日期'), { target: { value: '2026-05-16' } });
    await user.click(screen.getByRole('button', { name: '搜索' }));
    await user.click(screen.getByRole('button', { name: /构建规则版本/ }));
    await user.click(screen.getByRole('button', { name: '确认提交' }));

    await waitFor(() => {
      expect(mockedCreateJob).toHaveBeenCalledWith(
        expect.objectContaining({
          job_type: 'strategy-build',
          params: expect.objectContaining({
            profile_id: 'default',
            trader_id: 'trader_a',
            strategy_date: '2026-05-16',
            snapshot_id: 'snap-2',
            selected_by: 'web',
          }),
        }),
      );
      expect(mockedCreateJob.mock.calls[0][0].params).not.toHaveProperty('config_path');
    });
  });
});
