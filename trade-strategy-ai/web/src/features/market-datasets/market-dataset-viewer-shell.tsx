import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { ErrorState, PageHeader } from '@/components/kit';
import { formatLocalDateInputOffset } from '@/lib/date';
import { getMarketDataset, listMarketDatasets } from '@/lib/api/market';
import type { MarketDatasetSummary } from '@/types/market';
import { buildDatasetDetailErrorState, buildDatasetListErrorState, buildInvalidDatasetQueryState } from './market-dataset-viewer-state';
import { MarketDatasetViewerDetail } from './market-dataset-viewer-detail';
import { MarketDatasetViewerFilters } from './market-dataset-viewer-filters';
import { MarketDatasetViewerList } from './market-dataset-viewer-list';

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

function parsePositiveInteger(value: string | null, fallback: number, min: number) {
  if (value === null || value === '') {
    return { value: fallback, valid: true };
  }
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < min) {
    return { value: fallback, valid: false };
  }
  return { value: parsed, valid: true };
}

function resolveSelectedDatasetId(datasetId: string | null, datasets: MarketDatasetSummary[]) {
  if (datasetId) {
    return datasetId;
  }
  return datasets[0]?.dataset_id ?? null;
}

function buildCatalogPatch(
  patch: {
    tradeDate?: string;
    market?: string;
    datasetType?: string;
    qualityStatus?: string;
  },
  extra?: Record<string, string | null | undefined>,
) {
  return {
    trade_date: patch.tradeDate,
    market: patch.market,
    dataset_type: patch.datasetType,
    quality_status: patch.qualityStatus,
    ...extra,
  };
}

export function MarketDatasetViewerShell() {
  const [searchParams, setSearchParams] = useSearchParams();
  const searchParamsString = searchParams.toString();

  const tradeDate = searchParams.get('trade_date') ?? formatLocalDateInputOffset(0);
  const market = searchParams.get('market') ?? 'CN';
  const datasetType = searchParams.get('dataset_type') ?? '';
  const qualityStatus = searchParams.get('quality_status') ?? '';
  const symbol = searchParams.get('symbol') ?? '';
  const section = searchParams.get('section') ?? '';
  const datasetIdParam = searchParams.get('dataset_id');
  const rawLimit = searchParams.get('limit');
  const rawOffset = searchParams.get('offset');
  const limitState = parsePositiveInteger(rawLimit, 20, 1);
  const offsetState = parsePositiveInteger(rawOffset, 0, 0);
  const invalidQueryState = !limitState.valid || !offsetState.valid ? buildInvalidDatasetQueryState(`limit=${rawLimit ?? ''}, offset=${rawOffset ?? ''}`) : null;

  const listQuery = useQuery({
    queryKey: ['market-datasets-browser', tradeDate, market, datasetType, qualityStatus],
    queryFn: () =>
      listMarketDatasets({
        tradeDate: tradeDate || undefined,
        market: market || undefined,
        datasetType: datasetType || undefined,
        qualityStatus: qualityStatus || undefined,
        limit: 20,
        offset: 0,
      }),
    staleTime: 30_000,
    enabled: !invalidQueryState,
  });

  const datasets = listQuery.data?.items ?? [];
  const selectedDatasetId = resolveSelectedDatasetId(datasetIdParam, datasets);

  useEffect(() => {
    if (!datasets.length) return;
    if (datasetIdParam) return;
    const firstDatasetId = datasets[0]?.dataset_id;
    if (!firstDatasetId || firstDatasetId === datasetIdParam) return;
    setSearchParams(
      buildSearchParams(searchParams, {
        dataset_id: firstDatasetId,
        symbol: null,
        section: null,
        offset: '0',
        limit: String(limitState.value),
      }),
      { replace: true },
    );
  }, [datasetIdParam, datasets, limitState.value, searchParams, searchParamsString, setSearchParams]);

  const detailQuery = useQuery({
    queryKey: ['market-dataset-detail-browser', selectedDatasetId, limitState.value, offsetState.value],
    queryFn: () => getMarketDataset(selectedDatasetId ?? '', limitState.value, offsetState.value),
    staleTime: 30_000,
    enabled: Boolean(selectedDatasetId && !invalidQueryState),
  });

  const detail = detailQuery.data ?? null;
  const selectedDataset = useMemo(
    () => detail?.dataset ?? datasets.find((item) => item.dataset_id === selectedDatasetId) ?? null,
    [datasets, detail?.dataset, selectedDatasetId],
  );

  const listErrorState = listQuery.error ? buildDatasetListErrorState(listQuery.error) : null;
  const detailErrorState = detailQuery.error ? buildDatasetDetailErrorState(detailQuery.error) : null;

  const canPrev = offsetState.value > 0;
  const canNext = Boolean(detail?.page && detail.page.offset + detail.page.count < detail.page.total);

  const updateQueryState = (patch: Record<string, string | null | undefined>) => {
    setSearchParams(buildSearchParams(searchParams, patch), { replace: true });
  };

  return (
    <main className="page-stack">
      <PageHeader
        description="在 Web 中浏览 DB 里的市场数据集、分页样本与关联回链，不把 /market 再扩成一个复合控制台。"
      />

      <div className="flex flex-wrap items-center justify-start gap-3">
        <Link className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50" to="/market">
          返回市场数据
        </Link>
      </div>

      {invalidQueryState ? (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)]">
          <div className="space-y-4">
            <MarketDatasetViewerFilters
              tradeDate={tradeDate}
              market={market}
              datasetType={datasetType}
              qualityStatus={qualityStatus}
              onChange={(patch) => {
                updateQueryState({
                  ...buildCatalogPatch(patch),
                  offset: '0',
                });
              }}
              onReset={() => {
                updateQueryState({
                  trade_date: formatLocalDateInputOffset(0),
                  market: 'CN',
                  dataset_type: null,
                  quality_status: null,
                  dataset_id: null,
                  symbol: null,
                  section: null,
                  limit: '20',
                  offset: '0',
                });
              }}
            />
            <MarketDatasetViewerList
              datasets={[]}
              selectedDatasetId={null}
              isLoading={false}
              errorState={null}
              onSelectDataset={() => undefined}
              onRetry={() => undefined}
            />
          </div>
          <div className="space-y-4">
            <ErrorState {...invalidQueryState} />
            <div className="flex flex-wrap gap-2 text-sm">
              <Link className="text-sky-700 hover:underline" to="/market">
                返回市场数据
              </Link>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.02fr)_minmax(0,0.98fr)]">
          <div className="space-y-4">
            <MarketDatasetViewerFilters
              tradeDate={tradeDate}
              market={market}
              datasetType={datasetType}
              qualityStatus={qualityStatus}
              onChange={(patch) => {
                updateQueryState({
                  ...buildCatalogPatch(patch, {
                    dataset_id: null,
                    symbol: null,
                    section: null,
                    offset: '0',
                  }),
                });
              }}
              onReset={() => {
                updateQueryState({
                  trade_date: formatLocalDateInputOffset(0),
                  market: 'CN',
                  dataset_type: null,
                  quality_status: null,
                  dataset_id: null,
                  symbol: null,
                  section: null,
                  limit: '20',
                  offset: '0',
                });
              }}
            />

            <MarketDatasetViewerList
              datasets={datasets}
              selectedDatasetId={selectedDatasetId}
              isLoading={listQuery.isLoading}
              errorState={listErrorState}
              onSelectDataset={(datasetId) => {
                updateQueryState({
                  dataset_id: datasetId,
                  symbol: null,
                  section: null,
                  offset: '0',
                  limit: String(limitState.value),
                });
              }}
              onRetry={() => {
                void listQuery.refetch();
              }}
            />
          </div>

          <MarketDatasetViewerDetail
            selectedDataset={selectedDataset}
            detail={detail}
            errorState={detailErrorState}
            isLoading={detailQuery.isLoading}
            onRetry={() => {
              void detailQuery.refetch();
            }}
            symbol={symbol}
            section={section}
            offset={offsetState.value}
            limit={limitState.value}
            canPrev={canPrev}
            canNext={canNext}
            onChangeSymbol={(nextSymbol) => {
              updateQueryState({
                symbol: nextSymbol,
                offset: '0',
              });
            }}
            onChangeSection={(nextSection) => {
              updateQueryState({
                section: nextSection,
                offset: '0',
              });
            }}
            onPrevPage={() => {
              if (!canPrev) return;
              updateQueryState({
                offset: String(Math.max(0, offsetState.value - limitState.value)),
              });
            }}
            onNextPage={() => {
              if (!canNext) return;
              updateQueryState({
                offset: String(offsetState.value + limitState.value),
              });
            }}
          />
        </div>
      )}
    </main>
  );
}
