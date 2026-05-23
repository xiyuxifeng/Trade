import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { SectionCard } from '@/components/kit';

type MarketSnapshotBrowserFiltersProps = {
  tradeDate: string;
  market: string;
  qualityStatus: string;
  onChange: (patch: Partial<{ tradeDate: string; market: string; qualityStatus: string }>) => void;
  onSearch: () => void;
  onReset: () => void;
};

export function MarketSnapshotBrowserFilters({
  tradeDate,
  market,
  qualityStatus,
  onChange,
  onSearch,
  onReset,
}: MarketSnapshotBrowserFiltersProps) {
  return (
    <SectionCard
      title="筛选条件"
      description="按交易日、市场和质量状态筛选 Market Snapshot，点击搜索后才会生效。"
      className="border-slate-200 bg-white"
    >
      <div className="grid gap-3 lg:grid-cols-3">
        <label className="space-y-2">
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">trade_date</span>
          <Input
            type="date"
            value={tradeDate}
            onChange={(event) => onChange({ tradeDate: event.target.value })}
          />
        </label>
        <label className="space-y-2">
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">market</span>
          <Input value={market} onChange={(event) => onChange({ market: event.target.value })} placeholder="CN" />
        </label>
        <label className="space-y-2">
          <span className="text-xs font-medium uppercase tracking-[0.16em] text-slate-500">quality_status</span>
          <Select value={qualityStatus} onChange={(event) => onChange({ qualityStatus: event.target.value })}>
            <option value="">全部</option>
            <option value="success">成功</option>
            <option value="partial">部分可用</option>
            <option value="failed">失败</option>
            <option value="pending">等待中</option>
          </Select>
        </label>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button className="min-w-24" onClick={onSearch}>
          搜索
        </Button>
        <Button variant="outline" className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={onReset}>
          重置
        </Button>
      </div>
    </SectionCard>
  );
}
