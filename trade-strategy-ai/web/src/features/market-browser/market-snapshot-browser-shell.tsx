import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { SectionCard } from '@/components/kit';
import { PageHeader } from '@/components/layout/page-header';
import { ErrorState } from '@/components/state/ErrorState';
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
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const appliedTradeDate = searchParams.get('trade_date') ?? '';
  const appliedMarket = searchParams.get('market') ?? 'CN';
  const appliedQualityStatus = searchParams.get('quality_status') ?? '';
  const [draftTradeDate, setDraftTradeDate] = useState(appliedTradeDate);
  const [draftMarket, setDraftMarket] = useState(appliedMarket);
  const [draftQualityStatus, setDraftQualityStatus] = useState(appliedQualityStatus);
  const selectedSnapshotIdParam = searchParams.get('snapshot_id');
  const selectedRegimeVersionParam = searchParams.get('regime_version');
  const selectedFeatureVersionParam = searchParams.get('feature_version');

  useEffect(() => {
    setDraftTradeDate(appliedTradeDate);
    setDraftMarket(appliedMarket);
    setDraftQualityStatus(appliedQualityStatus);
  }, [appliedTradeDate, appliedMarket, appliedQualityStatus]);

  const snapshotsQuery = useQuery({
    queryKey: ['market-snapshots-browser', appliedTradeDate, appliedMarket, appliedQualityStatus],
    queryFn: () =>
      listMarketSnapshots({
        tradeDate: appliedTradeDate || undefined,
        market: appliedMarket,
        qualityStatus: appliedQualityStatus || undefined,
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
    queryKey: ['market-regime-features-browser', selectedSnapshotId, appliedTradeDate, appliedMarket],
    queryFn: () =>
      listMarketRegimeFeatures({
        snapshotId: selectedSnapshotId ?? undefined,
        tradeDate: appliedTradeDate,
        market: appliedMarket,
        limit: 20,
        offset: 0,
      }),
    enabled: Boolean(selectedSnapshotId),
    staleTime: 30_000,
  });

  const regimeListQuery = useQuery({
    queryKey: ['market-regimes-browser', selectedSnapshotId, appliedTradeDate, appliedMarket],
    queryFn: () =>
      listMarketRegimes({
        snapshotId: selectedSnapshotId ?? undefined,
        tradeDate: appliedTradeDate,
        market: appliedMarket,
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
  const datasetViewerLink = appliedTradeDate
    ? `/market/datasets?trade_date=${encodeURIComponent(appliedTradeDate)}&market=${encodeURIComponent(appliedMarket)}`
    : `/market/datasets?market=${encodeURIComponent(appliedMarket)}`;
  const artifactCenterLink = appliedTradeDate
    ? `/artifacts?jobType=snapshot-build&date=${encodeURIComponent(appliedTradeDate)}&source=market-snapshot-browser`
    : '/artifacts?jobType=snapshot-build&source=market-snapshot-browser';
  const snapshotBuildLink = '/strategies/pre-market';
  const snapshotJobLink = '/system/jobs?job_type=snapshot-build';

  const selectedDetail: MarketSnapshotDetailResponse | null = detail;
  const regimeDetail: MarketRegimeDetailResponse | null = regimeDetailQuery.data ?? null;
  const detailError = detailQuery.error ?? regimeListQuery.error ?? regimeDetailQuery.error;

  return (
    <main className="page-stack">
      <PageHeader
        kicker="市场数据"
        title="市场上下文快照"
        description="第 2 步：生成快照。查看快照质量、派生特征，并跳转到数据集浏览。"
        actionLabel="返回市场上下文"
        onAction={() => navigate('/market')}
      />

      <SectionCard title="流程定位" description="当前阶段是生成快照，下一步是浏览快照派生的数据集，之后在总页做基础信息检查。">
        <div className="grid gap-3 md:grid-cols-4">
          {[
            { number: '01', label: '先抓取', active: false },
            { number: '02', label: '生成快照', active: true },
            { number: '03', label: '浏览数据集', active: false },
            { number: '04', label: '基础信息检查', active: false },
          ].map((step) => (
            <div
              key={step.number}
              className={[
                'rounded-2xl border p-4',
                step.active ? 'border-sky-300 bg-sky-50' : 'border-slate-200 bg-slate-50',
              ].join(' ')}
            >
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{step.number}</p>
              <p className="mt-2 text-sm font-semibold text-slate-950">{step.label}</p>
              <p className="mt-1 text-xs text-slate-600">
                {step.active ? '当前页' : step.number === '03' ? '下一步' : '前后流程'}
              </p>
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.75fr)]">
        <SectionCard
          title="快照入口"
          description="这里负责生成和检查市场上下文快照，完成后再进入数据集浏览。"
          className="border-slate-200 bg-white"
        >
          <div className="grid grid-cols-2 gap-2">
            <Link
              className="inline-flex min-h-16 items-center justify-start rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-white"
              to={snapshotBuildLink}
            >
              <span>构建市场上下文</span>
            </Link>
            <Link
              className="inline-flex min-h-16 items-center justify-start rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-white"
              to={snapshotJobLink}
            >
              <span>查看市场上下文构建任务</span>
              <span className="mt-1 text-xs font-normal text-slate-500">任务列表</span>
            </Link>
            <Link
              className="inline-flex min-h-16 items-center justify-start rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-white"
              to={artifactCenterLink}
            >
              <span>查看市场上下文产物</span>
            </Link>
            <Link
              className="inline-flex min-h-16 items-center justify-start rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-white"
              to={datasetViewerLink}
            >
              <span>浏览数据集</span>
            </Link>
          </div>
        </SectionCard>

        <SectionCard
          title="版本切换"
          description="在查看快照后切换特征版本和状态版本。"
          className="border-slate-200 bg-white"
        >
          <div className="grid gap-4">
            <label className="space-y-2">
              <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">特征版本</span>
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
              <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">状态版本</span>
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
      </div>

      <MarketSnapshotBrowserFilters
        tradeDate={draftTradeDate}
        market={draftMarket}
        qualityStatus={draftQualityStatus}
        onChange={(patch) => {
          if (patch.tradeDate !== undefined) {
            setDraftTradeDate(patch.tradeDate);
          }
          if (patch.market !== undefined) {
            setDraftMarket(patch.market);
          }
          if (patch.qualityStatus !== undefined) {
            setDraftQualityStatus(patch.qualityStatus);
          }
        }}
        onSearch={() => {
          setSearchParams(
            buildSearchParams(searchParams, {
              trade_date: draftTradeDate || undefined,
              market: draftMarket || undefined,
              quality_status: draftQualityStatus || undefined,
              snapshot_id: undefined,
              regime_version: undefined,
              feature_version: undefined,
            }),
            { replace: true },
          );
        }}
        onReset={() => {
          setDraftTradeDate('');
          setDraftMarket('CN');
          setDraftQualityStatus('');
          setSearchParams(
            buildSearchParams(new URLSearchParams(), {
              market: 'CN',
            }),
            { replace: true },
          );
        }}
      />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
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
        />

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
          tradeDate={appliedTradeDate}
        />
      </div>
    </main>
  );
}
