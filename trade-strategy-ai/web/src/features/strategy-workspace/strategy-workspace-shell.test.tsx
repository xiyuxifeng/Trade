import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { StrategyWorkspaceShell } from './strategy-workspace-shell';
import { renderWithRouter } from '@/test/test-utils';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { listJobs, createJob } from '@/lib/api/jobs';
import { listArtifacts } from '@/lib/api/artifacts';
import { listArticleMetadataSummary } from '@/lib/api/article-metadata';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import { getOptimizeVersion, listOptimizeVersions } from '@/lib/api/optimize';
import { listTraderOptions } from '@/lib/api/traders';

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
  getProfile: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  listJobs: vi.fn(),
  createJob: vi.fn(),
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

vi.mock('@/lib/api/optimize', () => ({
  listOptimizeVersions: vi.fn(),
  getOptimizeVersion: vi.fn(),
  createOptimizeCandidateVersion: vi.fn(),
}));

vi.mock('@/lib/api/traders', () => ({
  listTraderOptions: vi.fn(),
}));

const mockedListProfiles = vi.mocked(listProfiles);
const mockedGetProfile = vi.mocked(getProfile);
const mockedListJobs = vi.mocked(listJobs);
const mockedCreateJob = vi.mocked(createJob);
const mockedListArtifacts = vi.mocked(listArtifacts);
const mockedListArticleMetadataSummary = vi.mocked(listArticleMetadataSummary);
const mockedListStrategyVersions = vi.mocked(listStrategyVersions);
const mockedGetStrategyVersion = vi.mocked(getStrategyVersion);
const mockedListOptimizeVersions = vi.mocked(listOptimizeVersions);
const mockedGetOptimizeVersion = vi.mocked(getOptimizeVersion);
const mockedListTraderOptions = vi.mocked(listTraderOptions);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('StrategyWorkspaceShell', () => {
  it('loads the latest profile snapshot and keeps the workspace usable', async () => {
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
    mockedListJobs.mockResolvedValue({ count: 0, total: 0, skip: 0, limit: 30, items: [] } as never);
    mockedListArtifacts.mockResolvedValue({ count: 0, total: 0, skip: 0, limit: 24, items: [] } as never);
    mockedListStrategyVersions.mockResolvedValue({
      status: 'ok',
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [
        {
          version_id: 'sv-1',
          trader_id: 'trader_a',
          strategy_date: '2026-05-16',
          status: 'draft',
          version_type: 'daily',
          parent_version_id: null,
          recommendations_count: 0,
          source_article_ids_count: 1,
          released_at: null,
          has_rules_snapshot: true,
        },
      ],
    } as never);
    mockedGetStrategyVersion.mockResolvedValue({
      status: 'ok',
      item: {
        version_id: 'sv-1',
        trader_id: 'trader_a',
        strategy_date: '2026-05-16',
        status: 'draft',
        version_type: 'daily',
        parent_version_id: null,
        recommendations: [],
        source_article_ids: ['article-1'],
        evidence_refs: [],
        notes: null,
        released_at: null,
        rules_snapshot: [],
        regime_selection: {
          selection_id: 'sel-001',
          snapshot_id: 'snap-1',
          market_regime_version: 'market-regime-v3',
          applicability_profile_version: 'rule-applicability-v1',
          selected_by: 'web',
          confidence: 0.92,
          quality_status: 'ok',
        },
      },
    } as never);
    mockedListArticleMetadataSummary.mockResolvedValue({
      items: [
        {
          article_id: 'article-1',
          selected_schema_version: 'v1',
          selected_by: 'system',
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
    mockedListOptimizeVersions.mockResolvedValue({ status: 'success', count: 0, total: 0, skip: 0, limit: 8, items: [] } as never);
    mockedGetOptimizeVersion.mockResolvedValue({ status: 'success', item: null } as never);
    mockedListTraderOptions.mockResolvedValue({
      status: 'success',
      count: 2,
      items: ['trader_a', 'trader_b'],
    } as never);

    renderWithRouter([{ path: '/strategies', element: <StrategyWorkspaceShell /> }], ['/strategies']);

    expect(screen.getByRole('link', { name: '进入规则选择' })).toHaveAttribute(
      'href',
      '/strategies/regime-selection',
    );
    expect(
      screen.getByText('在 Web 中构建策略版本、运行盘前和盘后任务，并通过任务详情、产物和报告追踪结果。'),
    ).toBeInTheDocument();
    expect((await screen.findAllByText('snap-2')).length).toBeGreaterThan(0);
    expect(await screen.findByText('来源文章 metadata 版本')).toBeInTheDocument();
    expect(screen.getByText('article-1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /盘前运行/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /盘后运行/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '候选版本' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成候选版本' })).toBeInTheDocument();
    expect(mockedListTraderOptions).toHaveBeenCalledWith({ source: 'strategy' });
    expect(mockedCreateJob).not.toHaveBeenCalled();
  });
});
