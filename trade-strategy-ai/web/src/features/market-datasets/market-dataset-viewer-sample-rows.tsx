import { EmptyState, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import type { MarketSnapshotItemSummary } from '@/types/market';

type MarketDatasetViewerSampleRowsProps = {
  rows: MarketSnapshotItemSummary[];
  totalCount: number;
  symbol: string;
  section: string;
  offset: number;
  limit: number;
  isLoading: boolean;
  onChangeSymbol: (symbol: string) => void;
  onChangeSection: (section: string) => void;
  onPrevPage: () => void;
  onNextPage: () => void;
  canPrev: boolean;
  canNext: boolean;
};

function readPreview(payload: Record<string, unknown>) {
  const entries = Object.entries(payload).slice(0, 3);
  if (!entries.length) return '空 payload';
  return entries.map(([key, value]) => `${key}: ${typeof value === 'string' ? value : JSON.stringify(value)}`).join(' · ');
}

export function MarketDatasetViewerSampleRows({
  rows,
  totalCount,
  symbol,
  section,
  offset,
  limit,
  isLoading,
  onChangeSymbol,
  onChangeSection,
  onPrevPage,
  onNextPage,
  canPrev,
  canNext,
}: MarketDatasetViewerSampleRowsProps) {
  const filteredRows = rows.filter((row) => {
    const symbolMatch = symbol.trim() ? row.symbol?.toLowerCase().includes(symbol.trim().toLowerCase()) : true;
    const sectionMatch = section.trim() ? row.section_id.toLowerCase().includes(section.trim().toLowerCase()) : true;
    return symbolMatch && sectionMatch;
  });
  const rangeStart = totalCount > 0 ? offset + 1 : 0;
  const rangeEnd = totalCount > 0 ? Math.min(offset + limit, totalCount) : 0;

  return (
    <SectionCard title="分页样本" description="样本分页只在当前 dataset 详情响应内做过滤，不额外扩展后端查询契约。">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <label className="text-xs uppercase tracking-[0.16em] text-slate-500">symbol</label>
          <input
            className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none transition-colors placeholder:text-slate-400 focus:border-sky-400"
            placeholder="000001.SZ"
            value={symbol}
            onChange={(event) => onChangeSymbol(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs uppercase tracking-[0.16em] text-slate-500">section</label>
          <input
            className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-950 outline-none transition-colors placeholder:text-slate-400 focus:border-sky-400"
            placeholder="overview"
            value={section}
            onChange={(event) => onChangeSection(event.target.value)}
          />
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
        <p>
          当前页 {rangeStart}-{rangeEnd} 条，共 {totalCount} 条
        </p>
        <div className="flex gap-2">
          <button
            className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50"
            type="button"
            onClick={onPrevPage}
            disabled={!canPrev || isLoading}
          >
            上一页
          </button>
          <button
            className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:pointer-events-none disabled:opacity-50"
            type="button"
            onClick={onNextPage}
            disabled={!canNext || isLoading}
          >
            下一页
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="mt-4">
          <LoadingState label="正在加载分页样本" description="只拉取当前页样本，不一次性加载整个数据集。" />
        </div>
      ) : filteredRows.length ? (
        <div className="mt-4 overflow-hidden rounded-2xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-xs uppercase tracking-[0.14em] text-slate-500">
                <th className="px-4 py-3 font-medium">Section</th>
                <th className="px-4 py-3 font-medium">Symbol</th>
                <th className="px-4 py-3 font-medium">Item Key</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {filteredRows.map((row) => (
                <tr key={row.id} className="align-top">
                  <td className="px-4 py-4 text-slate-900">{row.section_id}</td>
                  <td className="px-4 py-4 text-slate-700">{row.symbol ?? '—'}</td>
                  <td className="px-4 py-4 text-slate-700">{row.item_key}</td>
                  <td className="px-4 py-4 text-slate-700">{row.item_type ?? '—'}</td>
                  <td className="px-4 py-4">
                    <StatusBadge value={row.quality_status} />
                  </td>
                  <td className="px-4 py-4 text-xs leading-6 text-slate-600">{readPreview(row.payload_json)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title={symbol.trim() || section.trim() ? '当前页没有匹配的样本' : '当前页没有样本'}
          description="可以换一页，或者放宽 symbol / section 过滤条件。"
        />
      )}
    </SectionCard>
  );
}
