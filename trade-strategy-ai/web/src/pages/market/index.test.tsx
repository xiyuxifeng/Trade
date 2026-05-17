import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';

vi.mock('@/lib/api/market', () => ({
  getMarketRegimeFeature: vi.fn(),
  getMarketSnapshot: vi.fn(),
  getMarketSnapshotQuality: vi.fn(),
  listMarketRegimeFeatures: vi.fn(),
  listMarketSnapshotSections: vi.fn(),
  listMarketSnapshots: vi.fn(),
}));

import { ApiError } from '@/lib/api/http';
import { renderWithRouter } from '@/test/test-utils';
import { MarketPage } from './index';
import {
  getMarketRegimeFeature,
  getMarketSnapshot,
  getMarketSnapshotQuality,
  listMarketRegimeFeatures,
  listMarketSnapshotSections,
  listMarketSnapshots,
} from '@/lib/api/market';

const mockedListMarketSnapshots = vi.mocked(listMarketSnapshots);
const mockedGetMarketSnapshot = vi.mocked(getMarketSnapshot);
const mockedListMarketSnapshotSections = vi.mocked(listMarketSnapshotSections);
const mockedGetMarketSnapshotQuality = vi.mocked(getMarketSnapshotQuality);
const mockedListMarketRegimeFeatures = vi.mocked(listMarketRegimeFeatures);
const mockedGetMarketRegimeFeature = vi.mocked(getMarketRegimeFeature);

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

describe('MarketPage', () => {
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

    renderWithRouter([{ path: '/market', element: <MarketPage /> }], ['/market?snapshot_id=snap-001&trade_date=2026-05-16&market=CN']);

    expect(await screen.findByRole('heading', { name: 'Market Snapshot Browser' })).toBeInTheDocument();
    await waitFor(() => {
      expect(mockedListMarketSnapshots).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.queryByText('正在加载快照列表')).not.toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.queryByText('正在加载快照详情')).not.toBeInTheDocument();
    });
    expect(screen.getAllByText('snap-001').length).toBeGreaterThan(1);
    expect(screen.getByRole('link', { name: '查看数据集' })).toHaveAttribute(
      'href',
      '/market/datasets?trade_date=2026-05-16&market=CN',
    );
    expect(await screen.findByText('质量报告')).toBeInTheDocument();
    expect(screen.getByText('趋势特征')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '前往 Job 详情' })).toHaveAttribute('href', '/jobs/job-001');
    expect(screen.getAllByRole('link', { name: '前往产物中心' })[0]).toHaveAttribute(
      'href',
      '/artifacts?jobId=job-001',
    );
  });

  it('shows a shared recovery error when the selected snapshot is missing', async () => {
    mockedListMarketSnapshots.mockResolvedValue({
      filters: { trade_date: '2026-05-16', market: 'CN', quality_status: '' },
      page: { total: 1, limit: 50, offset: 0, count: 1 },
      items: [buildSnapshot('snap-001')],
    } as never);
    mockedGetMarketSnapshot.mockRejectedValueOnce(new ApiError(404, 'snapshot not found'));
    mockedListMarketSnapshotSections.mockResolvedValue({
      snapshot_id: 'snap-001',
      page: { total: 1, limit: 50, offset: 0, count: 1 },
      items: [buildSection('snap-001')],
    } as never);
    mockedGetMarketSnapshotQuality.mockRejectedValueOnce(new ApiError(404, 'quality missing'));
    mockedListMarketRegimeFeatures.mockResolvedValue({
      filters: { snapshot_id: 'snap-001' },
      page: { total: 0, limit: 50, offset: 0, count: 0 },
      items: [],
    } as never);

    renderWithRouter([{ path: '/market', element: <MarketPage /> }], ['/market?snapshot_id=snap-001&trade_date=2026-05-16&market=CN']);

    expect(await screen.findByText('快照不存在')).toBeInTheDocument();
    expect(screen.getAllByText('snap-001').length).toBeGreaterThan(0);
  });
});
