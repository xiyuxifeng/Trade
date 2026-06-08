import type { ReactNode } from 'react';
import { SectionCard, StatusBadge } from '@/components/kit';
import { EmptyState, LoadingState } from '@/components/kit';
import type { MarketSnapshotListItem } from '@/types/market';

type MarketSnapshotBrowserListProps = {
  snapshots: MarketSnapshotListItem[];
  selectedSnapshotId: string | null;
  isLoading: boolean;
  errorState: ReactNode | null;
  onSelectSnapshot: (snapshotId: string) => void;
};

function formatTimestamp(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function SnapshotMetaRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 break-all text-sm text-slate-800">{value}</p>
    </div>
  );
}

export function MarketSnapshotBrowserList({
  snapshots,
  selectedSnapshotId,
  isLoading,
  errorState,
  onSelectSnapshot,
}: MarketSnapshotBrowserListProps) {
  return (
    <SectionCard
      title="快照列表"
      description="选择一个快照继续查看质量、sections 和派生特征。"
      className="border-slate-200 bg-white"
    >
      {isLoading ? (
        <LoadingState label="正在加载快照列表" description="请稍候，列表数据正在从数据库查询。" />
      ) : errorState ? (
        errorState
      ) : snapshots.length ? (
        <div className="max-h-[55vh] space-y-3 overflow-y-auto pr-1">
          {snapshots.map((snapshot) => {
            const selected = snapshot.snapshot_id === selectedSnapshotId;
            return (
              <button
                key={snapshot.snapshot_id}
                type="button"
                aria-pressed={selected}
                onClick={() => onSelectSnapshot(snapshot.snapshot_id)}
                className={[
                  'w-full rounded-2xl border p-4 text-left transition-colors',
                  selected
                    ? 'border-sky-300 bg-sky-50 shadow-sm'
                    : 'border-slate-200 bg-slate-50 hover:border-slate-300 hover:bg-white',
                ].join(' ')}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-base font-semibold text-slate-950">{snapshot.snapshot_id}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      {snapshot.trade_date ?? '未记录'} · {snapshot.market} · {snapshot.data_version}
                    </p>
                  </div>
                  <StatusBadge value={snapshot.quality_status} />
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  <SnapshotMetaRow label="创建时间" value={formatTimestamp(snapshot.created_at)} />
                  <SnapshotMetaRow label="sections" value={`${snapshot.available_section_count}/${snapshot.section_count}`} />
                  <SnapshotMetaRow label="部分/缺失" value={`${snapshot.partial_section_count} / ${snapshot.missing_section_count}`} />
                </div>
              </button>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title="没有可展示的快照"
          description="当前筛选条件下没有找到 snapshot。请调整 trade_date、market 或 quality_status。"
        />
      )}
    </SectionCard>
  );
}
