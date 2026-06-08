import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';

vi.mock('@/lib/api/market', () => ({
  getMarketDataset: vi.fn(),
  listMarketDatasets: vi.fn(),
}));

import { ApiError } from '@/lib/api/http';
import { renderWithRouter } from '@/test/test-utils';
import { MarketDatasetPage } from './index';
import { getMarketDataset, listMarketDatasets } from '@/lib/api/market';

const mockedListMarketDatasets = vi.mocked(listMarketDatasets);
const mockedGetMarketDataset = vi.mocked(getMarketDataset);

function buildDatasetSummary(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 'dataset-row-1',
    dataset_id: 'snap-001:dataset',
    dataset_type: 'market_snapshot',
    trade_date: '2026-05-16',
    market: 'CN',
    source: 'snapshot-build',
    storage_ref: { source: 'db', logical_id: 'dataset-1', relative_path: null, uri: null, metadata: { job_id: 'job-001' } },
    snapshot_id: 'snap-001',
    profile_id: 'default',
    quality_status: 'ok',
    created_at: '2026-05-16T09:30:00+00:00',
    updated_at: '2026-05-16T09:40:00+00:00',
    ...overrides,
  };
}

function buildDatasetDetail() {
  return {
    dataset: buildDatasetSummary(),
    snapshot: {
      snapshot_id: 'snap-001',
      trade_date: '2026-05-16',
      market: 'CN',
      data_version: 'v1',
      quality_status: 'ok',
      created_at: '2026-05-16T09:30:00+00:00',
      section_count: 2,
      available_section_count: 2,
      partial_section_count: 0,
      missing_section_count: 0,
      profile_id: 'default',
    },
    page: { total: 2, limit: 20, offset: 0, count: 2 },
    items: [
      {
        id: 'item-1',
        snapshot_id: 'snap-001',
        section_id: 'overview',
        dataset_id: 'snap-001:dataset',
        symbol: '000001.SZ',
        item_key: 'overview:summary',
        item_type: 'overview',
        source_time: '2026-05-16T09:30:00+00:00',
        quality_status: 'ok',
        payload_json: { symbol: '000001.SZ', label: '概览' },
      },
      {
        id: 'item-2',
        snapshot_id: 'snap-001',
        section_id: 'overview',
        dataset_id: 'snap-001:dataset',
        symbol: '600000.SH',
        item_key: 'overview:summary:2',
        item_type: 'overview',
        source_time: '2026-05-16T09:31:00+00:00',
        quality_status: 'ok',
        payload_json: { symbol: '600000.SH', label: '概览二' },
      },
    ],
    warnings: ['dataset row missing optional field'],
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('MarketDatasetPage', () => {
  it('renders the dataset viewer shell and a populated detail pane', async () => {
    mockedListMarketDatasets.mockResolvedValue({
      filters: { trade_date: '2026-05-16', market: 'CN' },
      page: { total: 1, limit: 20, offset: 0, count: 1 },
      items: [buildDatasetSummary()],
    } as never);
    mockedGetMarketDataset.mockResolvedValue(buildDatasetDetail() as never);

    renderWithRouter(
      [{ path: '/market/datasets', element: <MarketDatasetPage /> }],
      ['/market/datasets?trade_date=2026-05-16&market=CN&dataset_id=snap-001:dataset&limit=20&offset=0'],
    );

    expect(await screen.findByText('第 3 步：浏览数据集。查看快照派生的样本、详情和关联回链。')).toBeInTheDocument();
    expect(screen.getByText('数据集列表')).toBeInTheDocument();
    expect(screen.getByText('数据集详情')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '返回市场上下文' })).toHaveAttribute('href', '/market');

    await waitFor(() => {
      expect(mockedGetMarketDataset).toHaveBeenCalledWith('snap-001:dataset', 20, 0);
    });

    expect(screen.getByText('分页样本')).toBeInTheDocument();
    expect(screen.getByText('000001.SZ')).toBeInTheDocument();
    expect(screen.getByText('600000.SH')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '前往 Snapshot' })).toHaveAttribute('href', '/market?snapshot_id=snap-001');
    expect(screen.getByRole('link', { name: '前往 Job 详情' })).toHaveAttribute('href', '/jobs/job-001');
    expect(screen.getByRole('link', { name: '前往产物中心' })).toHaveAttribute('href', '/artifacts?jobId=job-001');
  });

  it('shows an empty list state when no datasets match', async () => {
    mockedListMarketDatasets.mockResolvedValue({
      filters: { trade_date: '2026-05-16', market: 'CN' },
      page: { total: 0, limit: 20, offset: 0, count: 0 },
      items: [],
    } as never);

    renderWithRouter(
      [{ path: '/market/datasets', element: <MarketDatasetPage /> }],
      ['/market/datasets?trade_date=2026-05-16&market=CN'],
    );

    expect(await screen.findByText('没有匹配的数据集')).toBeInTheDocument();
  });

  it('shows dataset missing recovery when detail lookup returns 404', async () => {
    mockedListMarketDatasets.mockResolvedValue({
      filters: { trade_date: '2026-05-16', market: 'CN' },
      page: { total: 1, limit: 20, offset: 0, count: 1 },
      items: [buildDatasetSummary()],
    } as never);
    mockedGetMarketDataset.mockRejectedValueOnce(new ApiError(404, 'dataset not found'));

    renderWithRouter(
      [{ path: '/market/datasets', element: <MarketDatasetPage /> }],
      ['/market/datasets?trade_date=2026-05-16&market=CN&dataset_id=snap-001:dataset'],
    );

    expect(await screen.findByText('数据集不存在')).toBeInTheDocument();
  });

  it('shows permission denied recovery when detail lookup returns 403', async () => {
    mockedListMarketDatasets.mockResolvedValue({
      filters: { trade_date: '2026-05-16', market: 'CN' },
      page: { total: 1, limit: 20, offset: 0, count: 1 },
      items: [buildDatasetSummary()],
    } as never);
    mockedGetMarketDataset.mockRejectedValueOnce(new ApiError(403, 'permission denied'));

    renderWithRouter(
      [{ path: '/market/datasets', element: <MarketDatasetPage /> }],
      ['/market/datasets?trade_date=2026-05-16&market=CN&dataset_id=snap-001:dataset'],
    );

    expect(await screen.findByText('没有权限访问数据集')).toBeInTheDocument();
  });

  it('shows provider unavailable when the catalog query fails', async () => {
    mockedListMarketDatasets.mockRejectedValueOnce(new ApiError(503, 'service unavailable'));

    renderWithRouter(
      [{ path: '/market/datasets', element: <MarketDatasetPage /> }],
      ['/market/datasets?trade_date=2026-05-16&market=CN'],
    );

    expect(await screen.findByText('上游服务不可用')).toBeInTheDocument();
  });

  it('shows invalid query recovery when limit or offset is malformed', async () => {
    renderWithRouter(
      [{ path: '/market/datasets', element: <MarketDatasetPage /> }],
      ['/market/datasets?trade_date=2026-05-16&market=CN&limit=0&offset=abc'],
    );

    expect(await screen.findByText('无效查询参数')).toBeInTheDocument();
  });
});
