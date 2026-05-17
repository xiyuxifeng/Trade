import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { StrategyWorkspaceCandidate } from './strategy-workspace-candidate';
import { renderWithRouter } from '@/test/test-utils';
import { listArtifacts } from '@/lib/api/artifacts';
import { createOptimizeCandidateVersion, getOptimizeVersion, listOptimizeVersions } from '@/lib/api/optimize';
import { createJob } from '@/lib/api/jobs';

vi.mock('@/lib/api/optimize', () => ({
  listOptimizeVersions: vi.fn(),
  getOptimizeVersion: vi.fn(),
  createOptimizeCandidateVersion: vi.fn(),
}));

vi.mock('@/lib/api/artifacts', () => ({
  listArtifacts: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
}));

const mockedListOptimizeVersions = vi.mocked(listOptimizeVersions);
const mockedGetOptimizeVersion = vi.mocked(getOptimizeVersion);
const mockedCreateOptimizeCandidateVersion = vi.mocked(createOptimizeCandidateVersion);
const mockedListArtifacts = vi.mocked(listArtifacts);
const mockedCreateJob = vi.mocked(createJob);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('StrategyWorkspaceCandidate', () => {
  it('creates a candidate and switches the detail panel to the new version', async () => {
    const user = userEvent.setup();

    mockedListOptimizeVersions
      .mockResolvedValueOnce({
        status: 'success',
        count: 1,
        total: 1,
        skip: 0,
        limit: 8,
        items: [
          {
            version_id: 'candidate-1',
            parent_version_id: 'sv-1',
            trader_id: 'trader_a',
            strategy_date: '2026-05-17',
            status: 'candidate',
            version_type: 'candidate',
            recommendations_count: 1,
          },
        ],
      } as never)
      .mockResolvedValueOnce({
        status: 'success',
        count: 2,
        total: 2,
        skip: 0,
        limit: 8,
        items: [
          {
            version_id: 'candidate-2',
            parent_version_id: 'sv-1',
            trader_id: 'trader_a',
            strategy_date: '2026-05-17',
            status: 'candidate',
            version_type: 'candidate',
            recommendations_count: 1,
          },
          {
            version_id: 'candidate-1',
            parent_version_id: 'sv-1',
            trader_id: 'trader_a',
            strategy_date: '2026-05-17',
            status: 'candidate',
            version_type: 'candidate',
            recommendations_count: 1,
          },
        ],
      } as never);

    mockedGetOptimizeVersion.mockImplementation(async (versionId) => {
      return {
        status: 'success',
        item: {
          version_id: versionId,
          parent_version_id: 'sv-1',
          trader_id: 'trader_a',
          strategy_date: '2026-05-17',
          status: 'candidate',
          version_type: 'candidate',
          recommendations: [],
          evidence_refs: [],
          notes: null,
          released_at: null,
          rules_snapshot: [],
        },
      } as never;
    });

    mockedCreateOptimizeCandidateVersion.mockResolvedValue({
      status: 'success',
      item: {
        version_id: 'candidate-2',
        parent_version_id: 'sv-1',
        trader_id: 'trader_a',
        strategy_date: '2026-05-17',
        status: 'candidate',
        version_type: 'candidate',
        recommendations: [],
        evidence_refs: [],
        notes: 'generated from test',
        released_at: null,
        rules_snapshot: [],
      },
    } as never);

    mockedCreateJob.mockResolvedValue({
      status: 'ok',
      job: { id: 'job-candidate-review' },
    } as never);
    mockedListArtifacts.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [
        {
          artifact_id: 'artifact-1',
          name: 'candidate report',
          title: 'candidate report',
          path: 'data/processed/candidate/report.md',
          kind: 'report-markdown',
          source: 'job',
          exists: true,
          size_bytes: 128,
          modified_at: '2026-05-17T10:00:00Z',
          previewable: true,
          job_id: 'job-1',
          job_type: 'optimize-create-candidate',
          storage_ref: {
            source: 'file',
            logical_id: 'artifact-1',
            relative_path: 'report.md',
            uri: null,
            metadata: {},
          },
          metadata: {},
        },
      ],
    } as never);

    renderWithRouter(
      [
        {
          path: '/',
          element: (
            <StrategyWorkspaceCandidate
              traderId="trader_a"
              selectedVersion={{
                version_id: 'sv-1',
                trader_id: 'trader_a',
                strategy_date: '2026-05-17',
                status: 'draft',
                version_type: 'daily',
                parent_version_id: null,
                recommendations: [
                  {
                    rule_id: 'rule-1',
                    action: 'buy',
                    confidence: 0.7,
                    reason: 'test',
                  },
                ],
                source_article_ids: [],
                evidence_refs: ['evidence-1'],
                notes: 'seed version',
                released_at: null,
                rules_snapshot: [
                  {
                    rule_id: 'rule-1',
                    status: 'pending',
                    action: 'buy',
                  },
                ],
              } as never}
            />
          ),
        },
      ],
      ['/'],
    );

    expect(await screen.findByRole('heading', { name: '候选版本' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '生成候选版本' }));
    expect(await screen.findByRole('heading', { name: '确认生成候选版本' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '确认生成' }));

    expect(await screen.findByText('候选版本已生成: candidate-2')).toBeInTheDocument();
    expect(await screen.findByText('candidate-2')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '相关产物链接' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '确认生成候选版本' })).not.toBeInTheDocument();
    expect(mockedCreateOptimizeCandidateVersion).toHaveBeenCalledTimes(1);
  });
});
