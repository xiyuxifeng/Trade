import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { ApiError } from '@/lib/api/http';
import { StrategiesPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { getProfile, listProfiles } from '@/lib/api/profiles';
import { listJobs, createJob } from '@/lib/api/jobs';
import { listArtifacts } from '@/lib/api/artifacts';
import { getStrategyVersion, listStrategyVersions } from '@/lib/api/strategyStudio';
import { getOptimizeVersion, listOptimizeVersions, createOptimizeCandidateVersion } from '@/lib/api/optimize';

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

vi.mock('@/lib/api/strategyStudio', () => ({
  listStrategyVersions: vi.fn(),
  getStrategyVersion: vi.fn(),
}));

vi.mock('@/lib/api/optimize', () => ({
  listOptimizeVersions: vi.fn(),
  getOptimizeVersion: vi.fn(),
  createOptimizeCandidateVersion: vi.fn(),
}));

const mockedListProfiles = vi.mocked(listProfiles);
const mockedGetProfile = vi.mocked(getProfile);
const mockedListJobs = vi.mocked(listJobs);
const mockedCreateJob = vi.mocked(createJob);
const mockedListArtifacts = vi.mocked(listArtifacts);
const mockedListStrategyVersions = vi.mocked(listStrategyVersions);
const mockedGetStrategyVersion = vi.mocked(getStrategyVersion);
const mockedListOptimizeVersions = vi.mocked(listOptimizeVersions);
const mockedGetOptimizeVersion = vi.mocked(getOptimizeVersion);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('StrategiesPage', () => {
  it('renders the formal strategy workspace entry', async () => {
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
    mockedListStrategyVersions.mockResolvedValue({ status: 'ok', count: 0, total: 0, skip: 0, limit: 12, items: [] } as never);
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
        source_article_ids: [],
        evidence_refs: [],
        notes: null,
        released_at: null,
        rules_snapshot: [],
      },
    } as never);
    mockedListOptimizeVersions.mockResolvedValue({ status: 'success', count: 0, total: 0, skip: 0, limit: 8, items: [] } as never);
    mockedGetOptimizeVersion.mockResolvedValue({ status: 'success', item: null } as never);

    renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);

    expect(await screen.findByRole('heading', { name: '策略工作台' })).toBeInTheDocument();
    expect(screen.getByText('正式入口')).toBeInTheDocument();
    expect((await screen.findAllByText('config/strategy-v3.yaml')).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: /构建策略版本/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '候选版本' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '生成候选版本' })).toBeInTheDocument();
  });

  it('shows a shared recovery error when profile lookup fails', async () => {
    mockedListProfiles.mockRejectedValueOnce(new ApiError(403, 'forbidden'));
    mockedGetProfile.mockResolvedValue({
      profile: null,
      linked_jobs: [],
      snapshots: [],
    } as never);

    renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);

    expect(await screen.findAllByText('没有权限访问策略工作台')).toHaveLength(2);
    expect(screen.getAllByText('请切换到有权限的账号，或联系管理员调整权限。')).toHaveLength(2);
  });
});
