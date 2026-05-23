import { beforeEach, describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen, waitFor } from '@testing-library/react';
import { CandidatesPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listProfiles, getProfile } from '@/lib/api/profiles';
import { listStrategyVersions, getStrategyVersion } from '@/lib/api/strategyStudio';
import { listOptimizeVersions, getOptimizeVersion, createOptimizeCandidateVersion } from '@/lib/api/optimize';
import { listArtifacts } from '@/lib/api/artifacts';
import { listTraderOptions } from '@/lib/api/traders';

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
  getProfile: vi.fn(),
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

vi.mock('@/lib/api/artifacts', () => ({
  listArtifacts: vi.fn(),
}));

vi.mock('@/lib/api/traders', () => ({
  listTraderOptions: vi.fn(),
}));

const mockedListProfiles = vi.mocked(listProfiles);
const mockedGetProfile = vi.mocked(getProfile);
const mockedListStrategyVersions = vi.mocked(listStrategyVersions);
const mockedGetStrategyVersion = vi.mocked(getStrategyVersion);
const mockedListOptimizeVersions = vi.mocked(listOptimizeVersions);
const mockedGetOptimizeVersion = vi.mocked(getOptimizeVersion);
const mockedCreateOptimizeCandidateVersion = vi.mocked(createOptimizeCandidateVersion);
const mockedListArtifacts = vi.mocked(listArtifacts);
const mockedListTraderOptions = vi.mocked(listTraderOptions);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('CandidatesPage', () => {
  it('renders candidate creation and submits without config_path', async () => {
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
        rules_snapshot: [{ rule_id: 'rule-1', condition: 'trend', action: 'buy' }],
        regime_selection: {
          selection_id: 'sel-1',
          snapshot_id: 'snap-2',
        },
      },
    } as never);
    mockedListOptimizeVersions.mockResolvedValue({
      status: 'success',
      count: 1,
      total: 1,
      skip: 0,
      limit: 8,
      items: [
        {
          version_id: 'cv-1',
          trader_id: 'trader_a',
          strategy_date: '2026-05-16',
          status: 'draft',
          version_type: 'candidate',
          parent_version_id: 'trader_a_2026-05-16_released',
          recommendations_count: 1,
          source_article_ids_count: 1,
          released_at: null,
          has_rules_snapshot: true,
        },
      ],
    } as never);
    mockedGetOptimizeVersion.mockResolvedValue({ status: 'success', item: null } as never);
    mockedListArtifacts.mockResolvedValue({ count: 0, total: 0, skip: 0, limit: 12, items: [] } as never);
    mockedListTraderOptions.mockResolvedValue({
      status: 'success',
      count: 2,
      items: ['trader_a', 'trader_b'],
    } as never);
    mockedCreateOptimizeCandidateVersion.mockResolvedValue({
      status: 'success',
      item: {
        version_id: 'cv-new',
        trader_id: 'trader_a',
        strategy_date: '2026-05-16',
        status: 'draft',
        version_type: 'candidate',
        parent_version_id: 'trader_a_2026-05-16_released',
        recommendations: [],
        source_article_ids: [],
        evidence_refs: [],
        notes: null,
        released_at: null,
        rules_snapshot: [],
      },
    } as never);

    renderWithRouter([{ path: '/strategies/candidates', element: <CandidatesPage /> }], ['/strategies/candidates']);

    expect(await screen.findByRole('heading', { name: '候选版本' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '返回策略首页' })).toBeInTheDocument();
    expect(await screen.findByText('trader_a_2026-05-16_released')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '生成候选版本' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: '搜索' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重置' })).toBeInTheDocument();
    expect(mockedListTraderOptions).toHaveBeenCalledWith({ source: 'strategy' });

    await user.click(screen.getByRole('button', { name: '搜索' }));
    await user.click(screen.getByRole('button', { name: '生成候选版本' }));
    await user.click(screen.getByRole('button', { name: '确认生成' }));

    await waitFor(() => {
      expect(mockedCreateOptimizeCandidateVersion).toHaveBeenCalledWith(
        expect.objectContaining({
          parent_version_id: 'trader_a_2026-05-16_released',
          trader_id: 'trader_a',
          strategy_date: '2026-05-16',
        }),
      );
      expect(mockedCreateOptimizeCandidateVersion.mock.calls[0][0]).not.toHaveProperty('config_path');
    });
  });
});
