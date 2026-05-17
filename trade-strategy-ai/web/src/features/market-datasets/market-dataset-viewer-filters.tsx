import { SectionCard } from '@/components/kit';

type MarketDatasetViewerFilterPatch = {
  tradeDate?: string;
  market?: string;
  datasetType?: string;
  qualityStatus?: string;
};

type MarketDatasetViewerFiltersProps = {
  tradeDate: string;
  market: string;
  datasetType: string;
  qualityStatus: string;
  onChange: (patch: MarketDatasetViewerFilterPatch) => void;
  onReset: () => void;
};

const datasetTypeOptions = [
  '',
  'market_snapshot',
  'market_dataset',
  'regime_feature',
];

const qualityStatusOptions = ['', 'ok', 'partial', 'missing', 'failed'];

function FieldLabel({ children }: { children: string }) {
  return <label className="text-xs uppercase tracking-[0.16em] text-slate-500">{children}</label>;
}

export function MarketDatasetViewerFilters({
  tradeDate,
  market,
  datasetType,
  qualityStatus,
  onChange,
  onReset,
}: MarketDatasetViewerFiltersProps) {
  return (
    <SectionCard
      title="数据集筛选"
      description="按 trade_date、market、dataset_type 和质量状态筛选数据集目录。"
      className="border-slate-200 bg-white"
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="space-y-2">
          <FieldLabel>trade_date</FieldLabel>
          <input
            className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none transition-colors placeholder:text-slate-400 focus:border-sky-400"
            type="date"
            value={tradeDate}
            onChange={(event) => onChange({ tradeDate: event.target.value })}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel>market</FieldLabel>
          <input
            className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none transition-colors placeholder:text-slate-400 focus:border-sky-400"
            placeholder="CN"
            value={market}
            onChange={(event) => onChange({ market: event.target.value })}
          />
        </div>

        <div className="space-y-2">
          <FieldLabel>dataset_type</FieldLabel>
          <select
            className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none transition-colors focus:border-sky-400"
            value={datasetType}
            onChange={(event) => onChange({ datasetType: event.target.value })}
          >
            {datasetTypeOptions.map((option) => (
              <option key={option || '__all__'} value={option}>
                {option || '全部类型'}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <FieldLabel>quality_status</FieldLabel>
          <select
            className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none transition-colors focus:border-sky-400"
            value={qualityStatus}
            onChange={(event) => onChange({ qualityStatus: event.target.value })}
          >
            {qualityStatusOptions.map((option) => (
              <option key={option || '__all__'} value={option}>
                {option || '全部状态'}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          type="button"
          onClick={onReset}
        >
          重置筛选
        </button>
      </div>
    </SectionCard>
  );
}
