import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { StrategyWorkspaceArtifacts } from './strategy-workspace-artifacts';
import { renderWithRouter } from '@/test/test-utils';
import type { ArtifactRecord } from '@/types/artifacts';

const versions = [
  {
    version_id: 'sv-2',
    trader_id: 'trader_a',
    strategy_date: '2026-05-16',
    status: 'released',
    version_type: 'daily',
    parent_version_id: null,
    recommendations_count: 2,
    source_article_ids_count: 1,
    released_at: '2026-05-16T09:00:00Z',
    has_rules_snapshot: true,
  },
  {
    version_id: 'sv-1',
    trader_id: 'trader_a',
    strategy_date: '2026-05-15',
    status: 'draft',
    version_type: 'daily',
    parent_version_id: null,
    recommendations_count: 1,
    source_article_ids_count: 1,
    released_at: null,
    has_rules_snapshot: false,
  },
] as const;

const detail = {
  version_id: 'sv-2',
  trader_id: 'trader_a',
  strategy_date: '2026-05-16',
  status: 'released',
  version_type: 'daily',
  parent_version_id: null,
  recommendations: [
    {
      symbol: '000001.SZ',
      decision: 'buy',
      confidence: 0.92,
      entry_price: 12.3,
      target_price: 13.8,
      stop_loss_price: 11.7,
      volume: 1000,
      rationale: '动量和成交量同步改善',
      evidence_refs: ['evidence-1'],
    },
  ],
  source_article_ids: ['article-1'],
  evidence_refs: ['pack-1', 'pack-2'],
  notes: '正式版本说明',
  released_at: '2026-05-16T09:00:00Z',
  rules_snapshot: [],
};

const artifacts: ArtifactRecord[] = [
  {
    artifact_id: 'artifact-1',
    name: 'strategy_report.html',
    path: 'artifacts/strategy_report.html',
    kind: 'report',
    source: 'job',
    exists: true,
    size_bytes: 1024,
    modified_at: '2026-05-16T09:10:00Z',
    previewable: true,
    job_id: 'job-strategy-2',
    metadata: {},
    preview: 'Strategy report preview',
    download_name: 'strategy_report.html',
  },
];

describe('StrategyWorkspaceArtifacts', () => {
  it('renders version detail and allows switching versions', async () => {
    const user = userEvent.setup();
    const onSelectVersion = vi.fn();

    renderWithRouter(
      [
        {
          path: '/strategies',
          element: (
            <StrategyWorkspaceArtifacts
              artifacts={artifacts}
              artifactsError={null}
              isArtifactsLoading={false}
              isVersionDetailLoading={false}
              isVersionsLoading={false}
              onRetryArtifacts={() => undefined}
              onRetryVersionDetail={() => undefined}
              onRetryVersions={() => undefined}
              onSelectVersion={onSelectVersion}
              selectedVersionDetail={detail as never}
              selectedVersionId="sv-2"
              versionDetailError={null}
              versions={versions as never}
              versionsError={null}
            />
          ),
        },
      ],
      ['/strategies'],
    );

    expect(screen.getByText('版本详情与证据包')).toBeInTheDocument();
    expect(screen.getByText('strategy_report.html')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /sv-1/ }));
    expect(onSelectVersion).toHaveBeenCalledWith('sv-1');
  });

  it('navigates to artifact center from the artifact panel', async () => {
    const user = userEvent.setup();

    const { router } = renderWithRouter(
      [
        {
          path: '/strategies',
          element: (
            <StrategyWorkspaceArtifacts
              artifacts={artifacts}
              artifactsError={null}
              isArtifactsLoading={false}
              isVersionDetailLoading={false}
              isVersionsLoading={false}
              onRetryArtifacts={() => undefined}
              onRetryVersionDetail={() => undefined}
              onRetryVersions={() => undefined}
              onSelectVersion={() => undefined}
              selectedVersionDetail={detail as never}
              selectedVersionId="sv-2"
              versionDetailError={null}
              versions={versions as never}
              versionsError={null}
            />
          ),
        },
        {
          path: '/artifacts',
          element: <div>artifacts</div>,
        },
      ],
      ['/strategies'],
    );

    await user.click(screen.getByRole('button', { name: '前往产物中心' }));
    expect(router.state.location.pathname).toBe('/artifacts');
  });
});
