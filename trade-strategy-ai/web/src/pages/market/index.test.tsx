import { beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';

vi.mock('@/lib/api/market', () => ({
  listMarketSnapshots: vi.fn(),
  listMarketDatasets: vi.fn(),
  getStockInfoStatus: vi.fn(),
}));

vi.mock('@/lib/api/jobs', () => ({
  listJobs: vi.fn(),
}));

vi.mock('@/lib/api/artifacts', () => ({
  listArtifacts: vi.fn(),
}));

import { renderWithRouter } from '@/test/test-utils';
import { MarketPage } from './index';
import { listArtifacts } from '@/lib/api/artifacts';
import { listJobs } from '@/lib/api/jobs';
import { getStockInfoStatus, listMarketDatasets, listMarketSnapshots } from '@/lib/api/market';

const mockedListMarketSnapshots = vi.mocked(listMarketSnapshots);
const mockedListMarketDatasets = vi.mocked(listMarketDatasets);
const mockedGetStockInfoStatus = vi.mocked(getStockInfoStatus);
const mockedListJobs = vi.mocked(listJobs);
const mockedListArtifacts = vi.mocked(listArtifacts);

beforeEach(() => {
  vi.clearAllMocks();
  mockedGetStockInfoStatus.mockResolvedValue({
    total: 5515,
    stock_count: 5505,
    index_count: 10,
    benchmark_count: 10,
    expected_benchmark_count: 10,
    missing_benchmark_symbols: [],
    latest_updated_at: '2026-05-29T10:00:00+00:00',
    is_fresh: true,
    needs_refresh: false,
    message: '基础信息已就绪，可直接用于 OHLCV 抓取',
    max_age_days: 7,
  } as never);
});

describe('MarketPage', () => {
  it('renders market overview and entry links', async () => {
    mockedListMarketSnapshots.mockResolvedValue({
      filters: {},
      page: { total: 12, limit: 1, offset: 0, count: 1 },
      items: [
        {
          snapshot_id: 'snap-001',
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
        },
      ],
    } as never);
    mockedListMarketDatasets.mockResolvedValue({
      filters: {},
      page: { total: 7, limit: 1, offset: 0, count: 1 },
      items: [
        {
          id: 'dataset-row-1',
          dataset_id: 'snap-001:dataset',
          dataset_type: 'market_snapshot',
          trade_date: '2026-05-16',
          market: 'CN',
          source: 'snapshot-build',
          storage_ref: { source: 'db', logical_id: 'dataset-1', relative_path: null, uri: null, metadata: {} },
          snapshot_id: 'snap-001',
          profile_id: 'default',
          quality_status: 'ok',
          created_at: '2026-05-16T09:30:00+00:00',
          updated_at: '2026-05-16T09:40:00+00:00',
        },
      ],
    } as never);
    mockedListJobs.mockResolvedValue({
      count: 2,
      total: 2,
      skip: 0,
      limit: 20,
      items: [
        { id: 'job-1', job_type: 'snapshot-build', status: 'failed', created_at: '2026-05-16T09:00:00Z', created_by: 'web' },
        { id: 'job-2', job_type: 'ohlcv-crawl', status: 'success', created_at: '2026-05-16T10:00:00Z', created_by: 'web' },
      ],
    } as never);
    mockedListArtifacts.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [
        {
          artifact_id: 'artifact-1',
          name: 'market snapshot report',
          kind: 'report',
          source: 'snapshot-build',
          modified_at: '2026-05-16T09:40:00Z',
          exists: true,
        },
      ],
    } as never);

    renderWithRouter([{ path: '/market', element: <MarketPage /> }], ['/market']);

    expect(await screen.findByRole('heading', { name: '市场上下文' })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByRole('link').some((link) => link.getAttribute('href') === '/market/snapshots')).toBe(true);
    });
    expect(screen.getByText('快照总数')).toBeInTheDocument();
    expect(screen.getByText('数据集总数')).toBeInTheDocument();
    expect(screen.getAllByText('最近失败任务').length).toBeGreaterThan(0);
    expect(screen.getByText('流程状态')).toBeInTheDocument();
    expect(screen.getAllByText('基础信息检查').length).toBeGreaterThan(0);
    expect(screen.getAllByText('先抓取').length).toBeGreaterThan(0);
    expect(screen.getAllByText('生成快照').length).toBeGreaterThan(0);
    expect(screen.getAllByRole('link').find((link) => link.getAttribute('href') === '/market/snapshots')).toHaveAttribute('href', '/market/snapshots');
    expect(screen.getByRole('link', { name: /数据集浏览/ })).toHaveAttribute('href', '/market/datasets');
    expect(screen.queryByRole('link', { name: /查看最新数据集/ })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /进入市场数据页/ })).toHaveAttribute('href', '/market/kaipan');
    expect(screen.getByRole('link', { name: /前往 OHLCV 页面/ })).toHaveAttribute('href', '/market/ohlcv');
    expect(screen.getByRole('link', { name: /查看 Job 详情/ })).toHaveAttribute('href', '/jobs/job-1');
    expect(screen.getAllByRole('link').find((link) => link.getAttribute('href') === '/artifacts')).toHaveAttribute('href', '/artifacts');

    await waitFor(() => {
      expect(mockedListMarketSnapshots).toHaveBeenCalledWith({ limit: 1, offset: 0 });
      expect(mockedGetStockInfoStatus).toHaveBeenCalledWith(7);
    });
  });

  it('keeps market overview usable when stock info refresh fails', async () => {
    mockedListMarketSnapshots.mockResolvedValue({
      filters: {},
      page: { total: 12, limit: 1, offset: 0, count: 1 },
      items: [
        {
          snapshot_id: 'snap-001',
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
        },
      ],
    } as never);
    mockedListMarketDatasets.mockResolvedValue({
      filters: {},
      page: { total: 7, limit: 1, offset: 0, count: 1 },
      items: [
        {
          id: 'dataset-row-1',
          dataset_id: 'snap-001:dataset',
          dataset_type: 'market_snapshot',
          trade_date: '2026-05-16',
          market: 'CN',
          source: 'snapshot-build',
          storage_ref: { source: 'db', logical_id: 'dataset-1', relative_path: null, uri: null, metadata: {} },
          snapshot_id: 'snap-001',
          profile_id: 'default',
          quality_status: 'ok',
          created_at: '2026-05-16T09:30:00+00:00',
          updated_at: '2026-05-16T09:40:00+00:00',
        },
      ],
    } as never);
    mockedListJobs.mockResolvedValue({
      count: 2,
      total: 2,
      skip: 0,
      limit: 20,
      items: [
        { id: 'job-1', job_type: 'snapshot-build', status: 'failed', created_at: '2026-05-16T09:00:00Z', created_by: 'web' },
        { id: 'job-2', job_type: 'ohlcv-crawl', status: 'success', created_at: '2026-05-16T10:00:00Z', created_by: 'web' },
      ],
    } as never);
    mockedListArtifacts.mockResolvedValue({
      count: 1,
      total: 1,
      skip: 0,
      limit: 12,
      items: [
        {
          artifact_id: 'artifact-1',
          name: 'market snapshot report',
          kind: 'report',
          source: 'snapshot-build',
          modified_at: '2026-05-16T09:40:00Z',
          exists: true,
        },
      ],
    } as never);
    renderWithRouter([{ path: '/market', element: <MarketPage /> }], ['/market']);

    expect(await screen.findByRole('heading', { name: '市场上下文' })).toBeInTheDocument();
    expect((await screen.findAllByText('基础信息检查')).length).toBeGreaterThan(0);
    expect(screen.getByRole('link', { name: /前往 OHLCV 页面/ })).toHaveAttribute('href', '/market/ohlcv');
  });
});
