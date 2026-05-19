import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { SectionCard } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { formatLocalDateInputOffset } from '@/lib/date';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
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
import type { MarketRegimeDetailResponse, MarketSnapshotDetailResponse, MarketSnapshotListItem } from '@/types/market';
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

function uniqueVersions(items: Array<{ [key: string]: unknown }>, key: string) {
  const versions: string[] = [];
  const seen = new Set<string>();
  for (const item of items) {
    const value = item[key];
    if (typeof value !== 'string' || !value.trim() || seen.has(value)) {
      continue;
    }
    seen.add(value);
    versions.push(value);
  }
  return versions;
}

export function MarketSnapshotBrowserShell() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tradeDate = searchParams.get('trade_date') ?? formatLocalDateInputOffset(0);
  const market = searchParams.get('market') ?? 'CN';
  const qualityStatus = searchParams.get('quality_status') ?? '';
  const selectedSnapshotIdParam = searchParams.get('snapshot_id');
  const selectedRegimeVersionParam = searchParams.get('regime_version');
  const selectedFeatureVersionParam = searchParams.get('feature_version');

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

  const regimeListQuery = useQuery({
    queryKey: ['market-regimes-browser', selectedSnapshotId, tradeDate, market],
    queryFn: () =>
      listMarketRegimes({
        snapshotId: selectedSnapshotId ?? undefined,
        tradeDate,
        market,
        limit: 20,
        offset: 0,
      }),
    enabled: Boolean(selectedSnapshotId),
    staleTime: 30_000,
  });

  const regimeVersions = useMemo(() => uniqueVersions(regimeListQuery.data?.items ?? [], 'regime_version'), [regimeListQuery.data?.items]);
  const featureVersions = useMemo(() => uniqueVersions(regimeFeaturesQuery.data?.items ?? [], 'feature_version'), [regimeFeaturesQuery.data?.items]);
  const selectedRegimeVersion = selectedRegimeVersionParam && regimeVersions.includes(selectedRegimeVersionParam) ? selectedRegimeVersionParam : regimeVersions[0] ?? null;
  const selectedFeatureVersion = selectedFeatureVersionParam && featureVersions.includes(selectedFeatureVersionParam) ? selectedFeatureVersionParam : featureVersions[0] ?? null;

  useEffect(() => {
    const nextPatch: Record<string, string | null | undefined> = {};
    if (regimeVersions.length && (!selectedRegimeVersionParam || !regimeVersions.includes(selectedRegimeVersionParam))) {
      nextPatch.regime_version = regimeVersions[0];
    }
    if (featureVersions.length && (!selectedFeatureVersionParam || !featureVersions.includes(selectedFeatureVersionParam))) {
      nextPatch.feature_version = featureVersions[0];
    }
    if (Object.keys(nextPatch).length === 0) {
      return;
    }
    setSearchParams(buildSearchParams(searchParams, nextPatch), { replace: true });
  }, [featureVersions, regimeVersions, selectedFeatureVersionParam, selectedRegimeVersionParam, searchParams, setSearchParams]);

  const regimeDetailQuery = useQuery({
    queryKey: ['market-regime-detail-browser', selectedSnapshotId, selectedRegimeVersion],
    queryFn: () => getMarketRegime(selectedSnapshotId ?? '', selectedRegimeVersion ?? undefined),
    enabled: Boolean(selectedSnapshotId && selectedRegimeVersion),
    staleTime: 30_000,
  });

  const regimeFeatureDetailQuery = useQuery({
    queryKey: ['market-regime-feature-detail-browser', selectedSnapshotId, selectedFeatureVersion],
    queryFn: () => getMarketRegimeFeature(selectedSnapshotId ?? '', selectedFeatureVersion ?? undefined),
    enabled: Boolean(selectedSnapshotId && selectedFeatureVersion),
    staleTime: 30_000,
  });

  const listErrorState = snapshotsQuery.error ? buildErrorRecoveryState(snapshotsQuery.error, 'market') : null;
  const datasetViewerLink = `/market/datasets?trade_date=${encodeURIComponent(tradeDate)}&market=${encodeURIComponent(market)}`;

  const selectedDetail: MarketSnapshotDetailResponse | null = detail;
  const regimeDetail: MarketRegimeDetailResponse | null = regimeDetailQuery.data ?? null;
  const detailError = detailQuery.error ?? regimeListQuery.error ?? regimeDetailQuery.error;

  return (
    <main className="page-stack">
      {/* <PageHeader
        kicker="市场数据"
        title="Market Snapshot Browser"
        description="在 Web 中浏览 Market Snapshot，查看 sections、质量报告和派生特征，而不是切换到调试式任务页。"
      /> */}

      <div className="flex justify-start">
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50"
          to={datasetViewerLink}
        >
          查看数据集
        </Link>
      </div>

      <SectionCard
        title="版本切换"
        description="通过 URL 和下拉框切换 Market Regime Features 与 Market Regime 版本，默认展示当前可用最新版本。"
        className="border-slate-200 bg-white"
      >
        <div className="grid gap-4 md:grid-cols-2">
          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">feature_version</span>
            <select
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none transition-colors focus:border-sky-400"
              value={selectedFeatureVersion ?? ''}
              onChange={(event) => {
                setSearchParams(
                  buildSearchParams(searchParams, {
                    feature_version: event.target.value,
                  }),
                  { replace: true },
                );
              }}
            >
              {featureVersions.length ? (
                featureVersions.map((version) => (
                  <option key={version} value={version}>
                    {version}
                  </option>
                ))
              ) : (
                <option value="">暂无可用版本</option>
              )}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">regime_version</span>
            <select
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none transition-colors focus:border-sky-400"
              value={selectedRegimeVersion ?? ''}
              onChange={(event) => {
                setSearchParams(
                  buildSearchParams(searchParams, {
                    regime_version: event.target.value,
                  }),
                  { replace: true },
                );
              }}
            >
              {regimeVersions.length ? (
                regimeVersions.map((version) => (
                  <option key={version} value={version}>
                    {version}
                  </option>
                ))
              ) : (
                <option value="">暂无可用版本</option>
              )}
            </select>
          </label>
        </div>
      </SectionCard>

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
          regime={regimeDetail}
          regimeFeatures={regimeFeaturesQuery.data?.items ?? []}
          regimeFeatureDetail={regimeFeatureDetailQuery.data ?? null}
          isLoading={
            detailQuery.isLoading ||
            sectionsQuery.isLoading ||
            qualityQuery.isLoading ||
            regimeListQuery.isLoading ||
            regimeDetailQuery.isLoading ||
            regimeFeaturesQuery.isLoading ||
            regimeFeatureDetailQuery.isLoading
          }
          error={detailError}
          onRetry={() => {
            void detailQuery.refetch();
            void sectionsQuery.refetch();
            void qualityQuery.refetch();
            void regimeListQuery.refetch();
            void regimeDetailQuery.refetch();
            void regimeFeaturesQuery.refetch();
            void regimeFeatureDetailQuery.refetch();
          }}
          tradeDate={tradeDate}
        />
      </div>
    </main>
  );
}
