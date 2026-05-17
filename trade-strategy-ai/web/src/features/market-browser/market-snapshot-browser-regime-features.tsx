import type { ReactNode } from 'react';
import { EmptyState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import type { MarketRegimeFeatureDetailResponse, MarketRegimeFeatureSummary } from '@/types/market';

type MarketSnapshotBrowserRegimeFeaturesProps = {
  items: MarketRegimeFeatureSummary[];
  detail: MarketRegimeFeatureDetailResponse | null;
  isLoading: boolean;
  errorState: ReactNode | null;
};

function FeatureSummaryRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 break-all text-sm text-slate-800">{value}</p>
    </div>
  );
}

export function MarketSnapshotBrowserRegimeFeatures({
  items,
  detail,
  isLoading,
  errorState,
}: MarketSnapshotBrowserRegimeFeaturesProps) {
  const detailFeaturePayload = detail?.feature_payload_json ?? null;
  const detailSummary = detail?.summary_json ?? null;

  return (
    <SectionCard
      title="市场状态特征"
      description="展示从 Market Snapshot 派生的 regime features。"
      className="border-slate-200 bg-white"
    >
      {isLoading ? (
        <LoadingState label="正在加载 regime features" description="特征列表和详情正在并行加载。" />
      ) : errorState ? (
        errorState
      ) : !items.length ? (
        <EmptyState
          title="暂无 regime features"
          description="当前快照没有可用的派生特征，或者后端尚未生成相关数据。"
        />
      ) : (
        <div className="space-y-3">
          {items.map((item, index) => (
            <section key={item.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold text-slate-950">
                    {String((item.summary_json as Record<string, unknown> | undefined)?.label ?? item.feature_version)}
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    {item.trade_date} · {item.market} · {item.feature_version}
                  </p>
                </div>
                <StatusBadge value={item.quality_status} />
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                <FeatureSummaryRow label="available" value={item.available_feature_count} />
                <FeatureSummaryRow label="partial" value={item.partial_feature_count} />
                <FeatureSummaryRow label="missing" value={item.missing_feature_count} />
              </div>

              {index === 0 && detail ? (
                <div className="mt-4 grid gap-3 xl:grid-cols-2">
                  <JsonViewer value={detailFeaturePayload} title="特征 payload" />
                  <JsonViewer value={detailSummary} title="特征摘要" />
                </div>
              ) : null}
            </section>
          ))}
        </div>
      )}
    </SectionCard>
  );
}
