import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { PageHeader } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { formatLocalDateInputOffset } from '@/lib/date';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import {
  getMarketRegimeFeature,
  getMarketSnapshot,
  getMarketSnapshotQuality,
  listMarketRegimeFeatures,
  listMarketSnapshotSections,
  listMarketSnapshots,
} from '@/lib/api/market';
import type { MarketSnapshotDetailResponse, MarketSnapshotListItem } from '@/types/market';
import { MarketSnapshotBrowserDetail } from './market-snapshot-browser-detail';
import { MarketSnapshotBrowserFilters } from './market-snapshot-browser-filters';
import { MarketSnapshotBrowserList } from './market-snapshot-browser-list';

function buildSearchParams(base: URLSearchParams, patch: Record<string, string | null | undefined>) {
  const next = new URLSearchParams(base);
  Object.entries(patch).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      next.delete(key);
      return;
    }
    next.set(key, value);
  });
  return next;
}

function extractSnapshotId(items: MarketSnapshotListItem[], snapshotId: string | null) {
  if (snapshotId && items.some((item) => item.snapshot_id === snapshotId)) {
    return snapshotId;
  }
  return items[0]?.snapshot_id ?? null;
}

export function MarketSnapshotBrowserShell() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tradeDate = searchParams.get('trade_date') ?? formatLocalDateInputOffset(0);
  const market = searchParams.get('market') ?? 'CN';
  const qualityStatus = searchParams.get('quality_status') ?? '';
  const selectedSnapshotIdParam = searchParams.get('snapshot_id');

  const snapshotsQuery = useQuery({
    queryKey: ['market-snapshots-browser', tradeDate, market, qualityStatus],
    queryFn: () =>
      listMarketSnapshots({
        tradeDate,
        market,
        qualityStatus: qualityStatus || undefined,
        limit: 50,
        offset: 0,
      }),
    staleTime: 30_000,
  });

  const snapshots = snapshotsQuery.data?.items ?? [];
  const selectedSnapshotId = extractSnapshotId(snapshots, selectedSnapshotIdParam);

  useEffect(() => {
    if (!snapshots.length) return;
    if (selectedSnapshotId === selectedSnapshotIdParam) return;
    setSearchParams(
      buildSearchParams(searchParams, {
        snapshot_id: selectedSnapshotId ?? undefined,
      }),
      { replace: true },
    );
  }, [searchParams, selectedSnapshotId, selectedSnapshotIdParam, setSearchParams, snapshots.length]);

  const selectedSnapshot = useMemo(
    () => snapshots.find((item) => item.snapshot_id === selectedSnapshotId) ?? null,
    [selectedSnapshotId, snapshots],
  );

  const detailQuery = useQuery({
    queryKey: ['market-snapshot-detail-browser', selectedSnapshotId],
    queryFn: () => getMarketSnapshot(selectedSnapshotId ?? ''),
    enabled: Boolean(selectedSnapshotId),
    staleTime: 30_000,
  });

  const detail = detailQuery.data ?? null;
  const sectionsQuery = useQuery({
    queryKey: ['market-snapshot-sections-browser', selectedSnapshotId],
    queryFn: () => listMarketSnapshotSections(selectedSnapshotId ?? '', 200, 0),
    enabled: Boolean(selectedSnapshotId),
    staleTime: 30_000,
  });

  const qualityQuery = useQuery({
    queryKey: ['market-snapshot-quality-browser', selectedSnapshotId],
    queryFn: () => getMarketSnapshotQuality(selectedSnapshotId ?? ''),
    enabled: Boolean(selectedSnapshotId),
    staleTime: 30_000,
  });

  const regimeFeaturesQuery = useQuery({
    queryKey: ['market-regime-features-browser', selectedSnapshotId, tradeDate, market],
    queryFn: () =>
      listMarketRegimeFeatures({
        snapshotId: selectedSnapshotId ?? undefined,
        tradeDate,
        market,
        limit: 20,
        offset: 0,
      }),
    enabled: Boolean(selectedSnapshotId),
    staleTime: 30_000,
  });

  const selectedRegimeFeatureVersion = regimeFeaturesQuery.data?.items[0]?.feature_version ?? null;
  const regimeFeatureDetailQuery = useQuery({
    queryKey: ['market-regime-feature-detail-browser', selectedSnapshotId, selectedRegimeFeatureVersion],
    queryFn: () => getMarketRegimeFeature(selectedSnapshotId ?? '', selectedRegimeFeatureVersion ?? undefined),
    enabled: Boolean(selectedSnapshotId && selectedRegimeFeatureVersion),
    staleTime: 30_000,
  });

  const listErrorState = snapshotsQuery.error ? buildErrorRecoveryState(snapshotsQuery.error, 'market') : null;

  const selectedDetail: MarketSnapshotDetailResponse | null = detail;
  const detailError = detailQuery.error;

  return (
    <main className="page-stack">
      <PageHeader
        kicker="市场数据"
        title="Market Snapshot Browser"
        description="在 Web 中浏览 Market Snapshot，查看 sections、质量报告和派生特征，而不是切换到调试式任务页。"
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
        <div className="space-y-4">
          <MarketSnapshotBrowserFilters
            tradeDate={tradeDate}
            market={market}
            qualityStatus={qualityStatus}
            onChange={(patch) => {
              setSearchParams(
                buildSearchParams(searchParams, {
                  trade_date: patch.tradeDate ?? tradeDate,
                  market: patch.market ?? market,
                  quality_status: patch.qualityStatus ?? qualityStatus,
                }),
                { replace: true },
              );
            }}
            onReset={() => {
              setSearchParams(
                buildSearchParams(new URLSearchParams(), {
                  trade_date: formatLocalDateInputOffset(0),
                  market: 'CN',
                }),
                { replace: true },
              );
            }}
          />

          <MarketSnapshotBrowserList
            snapshots={snapshots}
            selectedSnapshotId={selectedSnapshotId}
            isLoading={snapshotsQuery.isLoading}
            errorState={listErrorState ? <ErrorState {...listErrorState} onRetry={() => void snapshotsQuery.refetch()} /> : null}
            onSelectSnapshot={(snapshotId) => {
              setSearchParams(
                buildSearchParams(searchParams, {
                  snapshot_id: snapshotId,
                }),
                { replace: true },
              );
            }}
            onRetry={() => {
              void snapshotsQuery.refetch();
            }}
          />
        </div>

        <MarketSnapshotBrowserDetail
          snapshotId={selectedSnapshotId}
          selectedSnapshot={selectedSnapshot}
          detail={selectedDetail}
          sections={sectionsQuery.data?.items ?? []}
          quality={qualityQuery.data ?? null}
          regimeFeatures={regimeFeaturesQuery.data?.items ?? []}
          regimeFeatureDetail={regimeFeatureDetailQuery.data ?? null}
          isLoading={
            detailQuery.isLoading ||
            sectionsQuery.isLoading ||
            qualityQuery.isLoading ||
            regimeFeaturesQuery.isLoading ||
            regimeFeatureDetailQuery.isLoading
          }
          error={detailError}
          onRetry={() => {
            void detailQuery.refetch();
            void sectionsQuery.refetch();
            void qualityQuery.refetch();
            void regimeFeaturesQuery.refetch();
            void regimeFeatureDetailQuery.refetch();
          }}
          tradeDate={tradeDate}
        />
      </div>
    </main>
  );
}
