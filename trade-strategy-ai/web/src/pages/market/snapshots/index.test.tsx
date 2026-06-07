import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';

vi.mock('@/lib/api/market', () => ({
  getMarketRegime: vi.fn(),
  getMarketRegimeFeature: vi.fn(),
  getMarketSnapshot: vi.fn(),
  getMarketSnapshotQuality: vi.fn(),
  listMarketRegimeFeatures: vi.fn(),
  listMarketRegimes: vi.fn(),
  listMarketSnapshotSections: vi.fn(),
  listMarketSnapshots: vi.fn(),
}));

import { ApiError } from '@/lib/api/http';
import { renderWithRouter } from '@/test/test-utils';
import { MarketSnapshotsPage } from './index';
import {
  getMarketRegime,
  getMarketRegimeFeature,
  getMarketSnapshot,
  getMarketSnapshotQuality,
  listMarketRegimeFeatures,
  listMarketRegimes,
  listMarketSnapshotSections,
  listMarketSnapshots,
} from '@/lib/api/market';

const mockedListMarketSnapshots = vi.mocked(listMarketSnapshots);
const mockedGetMarketSnapshot = vi.mocked(getMarketSnapshot);
const mockedListMarketSnapshotSections = vi.mocked(listMarketSnapshotSections);
const mockedGetMarketSnapshotQuality = vi.mocked(getMarketSnapshotQuality);
const mockedListMarketRegimeFeatures = vi.mocked(listMarketRegimeFeatures);
const mockedGetMarketRegimeFeature = vi.mocked(getMarketRegimeFeature);
const mockedListMarketRegimes = vi.mocked(listMarketRegimes);
const mockedGetMarketRegime = vi.mocked(getMarketRegime);

function buildSnapshot(snapshotId: string) {
  return {
    snapshot_id: snapshotId,
    trade_date: '2026-05-16',
    market: 'CN',
    data_version: 'market-snapshot-v1',
    quality_status: 'partial',
    created_at: '2026-05-16T08:00:00Z',
    section_count: 3,
    available_section_count: 2,
    partial_section_count: 1,
    missing_section_count: 0,
    profile_id: 'profile-a',
  };
}

function buildSection(snapshotId: string) {
  return {
    id: `${snapshotId}-section-1`,
    snapshot_id: snapshotId,
    section_id: 'market_summary',
    provider: 'akshare',
    source_time: '2026-05-16T08:00:00Z',
    record_count: 12,
    missing_reason: null,
    quality_status: 'partial',
    section_version: 'v1',
    storage_ref: { source: 'db', logical_id: `${snapshotId}-section-1`, relative_path: null, uri: null, metadata: {} },
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('MarketSnapshotsPage', () => {
  it('renders the market snapshot browser and detail pane', async () => {
    mockedListMarketSnapshots.mockResolvedValue({
      filters: { trade_date: '2026-05-16', market: 'CN', quality_status: '' },
      page: { total: 1, limit: 50, offset: 0, count: 1 },
      items: [buildSnapshot('snap-001')],
    } as never);
    mockedGetMarketSnapshot.mockResolvedValue({
      snapshot: buildSnapshot('snap-001'),
      sections: [buildSection('snap-001')],
      item_count: 1,
      quality_report: { status: 'partial', summary: '存在部分缺失' },
      dataset: {
        dataset_id: 'snap-001:dataset',
        storage_ref: {
          source: 'db',
          logical_id: 'dataset-001',
          relative_path: null,
          uri: null,
          metadata: { job_id: 'job-001' },
        },
      },
      warnings: ['profile snapshot is partial'],
    } as never);
    mockedListMarketSnapshotSections.mockResolvedValue({
      snapshot_id: 'snap-001',
      page: { total: 1, limit: 50, offset: 0, count: 1 },
      items: [buildSection('snap-001')],
    } as never);
    mockedGetMarketSnapshotQuality.mockResolvedValue({
      quality_report: { status: 'partial', summary: '存在部分缺失' },
    } as never);
    mockedListMarketRegimeFeatures.mockResolvedValue({
      filters: { snapshot_id: 'snap-001' },
      page: { total: 1, limit: 50, offset: 0, count: 1 },
      items: [
        {
          id: 'feature-1',
          snapshot_id: 'snap-001',
          trade_date: '2026-05-16',
          market: 'CN',
          feature_version: 'market-regime-features-v1',
          quality_status: 'partial',
          available_feature_count: 7,
          partial_feature_count: 2,
          missing_feature_count: 0,
          feature_payload_json: { trend: 'up' },
          summary_json: { label: '趋势特征' },
          storage_ref: { source: 'db', logical_id: 'feature-1', relative_path: null, uri: null, metadata: {} },
          created_at: '2026-05-16T08:10:00Z',
          updated_at: '2026-05-16T08:10:00Z',
        },
      ],
    } as never);
    mockedGetMarketRegimeFeature.mockResolvedValue({
      feature: {
        id: 'feature-1',
        snapshot_id: 'snap-001',
        trade_date: '2026-05-16',
        market: 'CN',
        feature_version: 'market-regime-features-v1',
        quality_status: 'partial',
        available_feature_count: 7,
        partial_feature_count: 2,
        missing_feature_count: 0,
        feature_payload_json: { trend: 'up' },
        summary_json: { label: '趋势特征' },
        storage_ref: { source: 'db', logical_id: 'feature-1', relative_path: null, uri: null, metadata: {} },
        created_at: '2026-05-16T08:10:00Z',
        updated_at: '2026-05-16T08:10:00Z',
      },
      feature_payload_json: { trend: 'up' },
      summary_json: { label: '趋势特征' },
      warnings: [],
    } as never);
    mockedListMarketRegimes.mockResolvedValue({
      filters: { snapshot_id: 'snap-001' },
      page: { total: 1, limit: 50, offset: 0, count: 1 },
      items: [
        {
          regime_id: 'snap-001:market-regime-v1',
          snapshot_id: 'snap-001',
          trade_date: '2026-05-16',
          market: 'CN',
          regime_version: 'market-regime-v1',
          source_feature_version: 'market-regime-features-v1',
          primary_label: 'strong_bull',
          labels: [
            {
              label: 'strong_bull',
              label_type: 'primary',
              score: 5.6,
              confidence: 0.86,
              status: 'active',
              evidence: [],
              reason: 'combined_score=5.60',
            },
          ],
          confidence: 0.86,
          quality_status: 'ok',
          missing_reason: null,
          storage_ref: { snapshot_id: 'snap-001', regime_version: 'market-regime-v1' },
          created_at: '2026-05-16T08:09:00Z',
          updated_at: '2026-05-16T08:09:00Z',
        },
      ],
    } as never);
    mockedGetMarketRegime.mockResolvedValue({
      regime: {
        regime_id: 'snap-001:market-regime-v1',
        snapshot_id: 'snap-001',
        trade_date: '2026-05-16',
        market: 'CN',
        regime_version: 'market-regime-v1',
        source_feature_version: 'market-regime-features-v1',
        primary_label: 'strong_bull',
        labels: [
          {
            label: 'strong_bull',
            label_type: 'primary',
            score: 5.6,
            confidence: 0.86,
            status: 'active',
            evidence: [],
            reason: 'combined_score=5.60',
          },
        ],
        confidence: 0.86,
        quality_status: 'ok',
        missing_reason: null,
        storage_ref: { snapshot_id: 'snap-001', regime_version: 'market-regime-v1' },
        created_at: '2026-05-16T08:09:00Z',
        updated_at: '2026-05-16T08:09:00Z',
      },
      features: [
        {
          feature_key: 'trend',
          raw_value: { ret_20d: 0.11 },
          normalized_value: 0.8,
          source_section: 'overview',
          source_field: 'trend',
          source_version: 'market-regime-features-v1',
          confidence: 0.9,
          weight: 0.3,
          missing_reason: null,
        },
      ],
      warnings: [],
    } as never);

    renderWithRouter([{ path: '/market/snapshots', element: <MarketSnapshotsPage /> }], ['/market/snapshots?snapshot_id=snap-001&trade_date=2026-05-16&market=CN']);

    expect(await screen.findByRole('heading', { name: '市场上下文快照' })).toBeInTheDocument();
    expect(await screen.findByText('市场上下文入口')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '构建市场上下文' })).toHaveAttribute('href', '/strategies/pre-market');
    expect(screen.getByRole('link', { name: /查看市场上下文构建任务/ })).toHaveAttribute(
      'href',
      '/jobs?job_type=snapshot-build',
    );
    expect(screen.getByRole('link', { name: '查看市场上下文产物' })).toHaveAttribute(
      'href',
      '/artifacts?jobType=snapshot-build&date=2026-05-16&source=market-snapshot-browser',
    );
    expect(screen.getByRole('link', { name: '查看数据集' })).toHaveAttribute(
      'href',
      '/market/datasets?trade_date=2026-05-16&market=CN',
    );
    await waitFor(() => {
      expect(screen.getByRole('link', { name: '查看相关数据' })).toHaveAttribute(
        'href',
        '/market/datasets?trade_date=2026-05-16&market=CN&dataset_id=snap-001%3Adataset',
      );
    });
    expect(screen.queryByRole('button', { name: '重试' })).not.toBeInTheDocument();
    expect(await screen.findByText('质量报告')).toBeInTheDocument();
    expect(screen.getByText('趋势特征')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '前往 Job 详情' })).toHaveAttribute('href', '/jobs/job-001');

    await waitFor(() => {
      expect(mockedListMarketSnapshots).toHaveBeenCalled();
    });
  });

  it('loads market snapshots without forcing today as the default trade date', async () => {
    mockedListMarketSnapshots.mockResolvedValue({
      filters: { trade_date: null, market: 'CN', quality_status: '' },
      page: { total: 1, limit: 50, offset: 0, count: 1 },
      items: [buildSnapshot('snap-002')],
    } as never);
    mockedGetMarketSnapshot.mockResolvedValue({
      snapshot: buildSnapshot('snap-002'),
      sections: [],
      item_count: 0,
      quality_report: { status: 'ok', summary: 'ok' },
      dataset: null,
      warnings: [],
    } as never);
    mockedListMarketSnapshotSections.mockResolvedValue({
      snapshot_id: 'snap-002',
      page: { total: 0, limit: 50, offset: 0, count: 0 },
      items: [],
    } as never);
    mockedGetMarketSnapshotQuality.mockResolvedValue({
      quality_report: { status: 'ok', summary: 'ok' },
    } as never);
    mockedListMarketRegimeFeatures.mockResolvedValue({ filters: { snapshot_id: 'snap-002' }, page: { total: 0, limit: 50, offset: 0, count: 0 }, items: [] } as never);
    mockedListMarketRegimes.mockResolvedValue({ filters: { snapshot_id: 'snap-002' }, page: { total: 0, limit: 50, offset: 0, count: 0 }, items: [] } as never);
    mockedGetMarketRegime.mockResolvedValue({ regime: null, features: [], warnings: [] } as never);

    renderWithRouter([{ path: '/market/snapshots', element: <MarketSnapshotsPage /> }], ['/market/snapshots']);

    expect(await screen.findByText('市场上下文入口')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看数据集' })).toHaveAttribute('href', '/market/datasets?market=CN');
  });

  it('shows permission denied recovery when the detail query returns 403', async () => {
    mockedListMarketSnapshots.mockResolvedValue({
      filters: { trade_date: '2026-05-16', market: 'CN', quality_status: '' },
      page: { total: 1, limit: 50, offset: 0, count: 1 },
      items: [buildSnapshot('snap-003')],
    } as never);
    mockedGetMarketSnapshot.mockRejectedValueOnce(new ApiError(403, 'permission denied'));

    renderWithRouter([{ path: '/market/snapshots', element: <MarketSnapshotsPage /> }], ['/market/snapshots?snapshot_id=snap-003&trade_date=2026-05-16&market=CN']);

    expect(await screen.findByText('没有权限访问市场上下文')).toBeInTheDocument();
  });
});
