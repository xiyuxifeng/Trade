import { EmptyState, LoadingState, SectionCard, StatusBadge, ErrorState } from '@/components/kit';
import type { ErrorRecoveryState } from '@/lib/error-recovery';
import type { MarketDatasetSummary } from '@/types/market';

type MarketDatasetViewerListProps = {
  datasets: MarketDatasetSummary[];
  selectedDatasetId: string | null;
  isLoading: boolean;
  errorState: ErrorRecoveryState | null;
  onSelectDataset: (datasetId: string) => void;
  onRetry: () => void;
};

function DatasetCard({
  dataset,
  selected,
  onSelect,
}: {
  dataset: MarketDatasetSummary;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={[
        'w-full rounded-2xl border p-4 text-left transition-colors',
        selected
          ? 'border-sky-300 bg-sky-50 shadow-sm'
          : 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white',
      ].join(' ')}
      type="button"
      onClick={onSelect}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">{dataset.dataset_id}</p>
          <p className="mt-1 text-xs text-slate-500">
            {dataset.trade_date} · {dataset.market} · {dataset.dataset_type}
          </p>
        </div>
        <StatusBadge value={dataset.quality_status} />
      </div>

      <div className="mt-4 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <p>
          来源：<span className="font-medium text-slate-800">{dataset.source ?? '未知'}</span>
        </p>
        <p>
          snapshot：<span className="font-medium text-slate-800">{dataset.snapshot_id ?? '未关联'}</span>
        </p>
      </div>
    </button>
  );
}

export function MarketDatasetViewerList({
  datasets,
  selectedDatasetId,
  isLoading,
  errorState,
  onSelectDataset,
  onRetry,
}: MarketDatasetViewerListProps) {
  return (
    <SectionCard title="数据集列表" description="按 trade_date 和质量状态浏览可用的数据集。">
      {isLoading ? (
        <LoadingState label="正在加载数据集列表" description="包括 dataset metadata 和质量摘要。" />
      ) : errorState ? (
        <ErrorState {...errorState} onRetry={errorState.retryable ? onRetry : undefined} />
      ) : datasets.length ? (
        <div className="space-y-3">
          {datasets.map((dataset) => (
            <DatasetCard
              key={dataset.dataset_id}
              dataset={dataset}
              selected={dataset.dataset_id === selectedDatasetId}
              onSelect={() => onSelectDataset(dataset.dataset_id)}
            />
          ))}
        </div>
      ) : (
        <EmptyState title="没有匹配的数据集" description="请调整筛选条件，或切换 trade_date / market 后重新查看。" />
      )}
    </SectionCard>
  );
}
