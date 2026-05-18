import { fetchJson } from './http';
import type {
  MarketDatasetDetailResponse,
  MarketDatasetListResponse,
  MarketRegimeFeatureDetailResponse,
  MarketRegimeFeatureListResponse,
  MarketRegimeDetailResponse,
  MarketRegimeListResponse,
  MarketSnapshotDetailResponse,
  MarketSnapshotListResponse,
  MarketSnapshotQualityResponse,
  MarketSnapshotSectionListResponse,
  MarketSnapshotSectionResponse,
  OhlcvResponse,
  SymbolListResponse,
} from '@/types/market';

function buildQueryString(params: Record<string, string | number | null | undefined>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    query.set(key, String(value));
  });
  return query.toString();
}

export function listSymbols(q?: string, limit = 200) {
  const params = new URLSearchParams();
  if (q) {
    params.set('q', q);
  }
  params.set('limit', String(limit));
  const suffix = params.toString() ? `?${params.toString()}` : '';
  return fetchJson<SymbolListResponse>(`/market/symbols${suffix}`);
}

export function getOhlcv(symbol: string, startDate: string, endDate: string) {
  const params = new URLSearchParams({
    symbol,
    start_date: startDate,
    end_date: endDate,
  });
  return fetchJson<OhlcvResponse>(`/market/ohlcv?${params.toString()}`);
}

export function listMarketSnapshots(params: {
  tradeDate?: string;
  market?: string;
  section?: string;
  symbol?: string;
  topic?: string;
  qualityStatus?: string;
  limit?: number;
  offset?: number;
} = {}) {
  const query = buildQueryString({
    trade_date: params.tradeDate,
    market: params.market,
    section: params.section,
    symbol: params.symbol,
    topic: params.topic,
    quality_status: params.qualityStatus,
    limit: params.limit,
    offset: params.offset,
  });
  return fetchJson<MarketSnapshotListResponse>(`/market/snapshots${query ? `?${query}` : ''}`);
}

export function getMarketSnapshot(snapshotId: string) {
  return fetchJson<MarketSnapshotDetailResponse>(`/market/snapshots/${snapshotId}`);
}

export function listMarketSnapshotSections(snapshotId: string, limit = 200, offset = 0) {
  const query = buildQueryString({ limit, offset });
  return fetchJson<MarketSnapshotSectionListResponse>(`/market/snapshots/${snapshotId}/sections${query ? `?${query}` : ''}`);
}

export function getMarketSnapshotSection(
  snapshotId: string,
  section: string,
  params: {
    symbol?: string;
    topic?: string;
    limit?: number;
    offset?: number;
  } = {},
) {
  const query = buildQueryString({
    symbol: params.symbol,
    topic: params.topic,
    limit: params.limit,
    offset: params.offset,
  });
  return fetchJson<MarketSnapshotSectionResponse>(`/market/snapshots/${snapshotId}/sections/${section}${query ? `?${query}` : ''}`);
}

export function listMarketDatasets(params: {
  tradeDate?: string;
  market?: string;
  datasetType?: string;
  qualityStatus?: string;
  limit?: number;
  offset?: number;
} = {}) {
  const query = buildQueryString({
    trade_date: params.tradeDate,
    market: params.market,
    dataset_type: params.datasetType,
    quality_status: params.qualityStatus,
    limit: params.limit,
    offset: params.offset,
  });
  return fetchJson<MarketDatasetListResponse>(`/market/datasets${query ? `?${query}` : ''}`);
}

export function getMarketDataset(datasetId: string, limit = 100, offset = 0) {
  const query = buildQueryString({ limit, offset });
  return fetchJson<MarketDatasetDetailResponse>(`/market/datasets/${datasetId}${query ? `?${query}` : ''}`);
}

export function getMarketSnapshotQuality(snapshotId: string) {
  return fetchJson<MarketSnapshotQualityResponse>(`/market/snapshots/${snapshotId}/quality`);
}

export function listMarketRegimeFeatures(params: {
  tradeDate?: string;
  snapshotId?: string;
  market?: string;
  featureVersion?: string;
  limit?: number;
  offset?: number;
} = {}) {
  const query = buildQueryString({
    trade_date: params.tradeDate,
    snapshot_id: params.snapshotId,
    market: params.market,
    feature_version: params.featureVersion,
    limit: params.limit,
    offset: params.offset,
  });
  return fetchJson<MarketRegimeFeatureListResponse>(`/market/regime-features${query ? `?${query}` : ''}`);
}

export function getMarketRegimeFeature(snapshotId: string, featureVersion?: string) {
  const query = buildQueryString({ feature_version: featureVersion });
  return fetchJson<MarketRegimeFeatureDetailResponse>(
    `/market/snapshots/${snapshotId}/regime-features${query ? `?${query}` : ''}`,
  );
}

export function listMarketRegimes(params: {
  tradeDate?: string;
  snapshotId?: string;
  market?: string;
  regimeVersion?: string;
  limit?: number;
  offset?: number;
} = {}) {
  const query = buildQueryString({
    trade_date: params.tradeDate,
    snapshot_id: params.snapshotId,
    market: params.market,
    regime_version: params.regimeVersion,
    limit: params.limit,
    offset: params.offset,
  });
  return fetchJson<MarketRegimeListResponse>(`/market/regimes${query ? `?${query}` : ''}`);
}

export function getMarketRegime(snapshotId: string, regimeVersion?: string) {
  const query = buildQueryString({ regime_version: regimeVersion });
  return fetchJson<MarketRegimeDetailResponse>(`/market/snapshots/${snapshotId}/regime${query ? `?${query}` : ''}`);
}
