import type { ReactNode } from 'react';
import { EmptyState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import type { MarketRegimeDetailResponse } from '@/types/market';

type MarketRegimePanelProps = {
  regime: MarketRegimeDetailResponse | null;
  isLoading: boolean;
  errorState: ReactNode | null;
};

function SummaryItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 break-all text-sm text-slate-800">{value}</p>
    </div>
  );
}

export function MarketRegimePanel({ regime, isLoading, errorState }: MarketRegimePanelProps) {
  const regimeBody = regime?.regime ?? null;
  const features = regime?.features ?? [];
  const warnings = regime?.warnings ?? [];

  return (
    <SectionCard
      title="市场状态画像"
      description="展示由市场上下文快照计算出的最终市场状态判断。"
      className="border-slate-200 bg-white"
    >
      {isLoading ? (
        <LoadingState label="正在加载市场状态画像" description="正在拉取市场状态列表和详情。" />
      ) : errorState ? (
        errorState
      ) : !regimeBody ? (
        <EmptyState title="暂无市场状态画像" description="当前快照尚未生成最终市场状态，或后端暂时没有可用结果。" />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <SummaryItem label="快照ID" value={regimeBody.snapshot_id} />
            <SummaryItem label="交易日" value={regimeBody.trade_date} />
            <SummaryItem label="市场" value={regimeBody.market} />
            <SummaryItem label="状态版本" value={regimeBody.regime_version} />
            <SummaryItem label="特征版本" value={regimeBody.source_feature_version} />
            <SummaryItem label="主标签" value={regimeBody.primary_label} />
            <SummaryItem label="置信度" value={Number(regimeBody.confidence).toFixed(2)} />
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">质量状态</p>
                <p className="mt-1 break-all text-sm text-slate-800">{regimeBody.quality_status}</p>
              </div>
              <StatusBadge value={regimeBody.quality_status} />
            </div>
          </div>

          {regimeBody.missing_reason ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
              {regimeBody.missing_reason}
            </div>
          ) : null}

          {warnings.length ? (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">提示</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-950">标签与证据</p>
                <p className="text-xs text-slate-500">主状态与结构标签的证据。</p>
              </div>
            </div>
            <div className="space-y-3">
              {regimeBody.labels.map((label) => (
                <section key={`${label.label}-${label.label_type}`} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-slate-950">{label.label}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        {label.label_type} · score {label.score.toFixed(2)} · confidence {label.confidence.toFixed(2)}
                      </p>
                    </div>
                    <StatusBadge value={label.status} />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-700">{label.reason}</p>
                  <div className="mt-4 space-y-2">
                    {label.evidence.map((item) => (
                      <div key={`${label.label}-${item.feature_key}-${item.source_section}`} className="rounded-xl border border-slate-200 bg-white p-3 text-sm text-slate-700">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <strong className="text-slate-950">{item.feature_key}</strong>
                          <span className="text-xs uppercase tracking-[0.16em] text-slate-500">{item.source_section}</span>
                        </div>
                        <p className="mt-1 break-all">{JSON.stringify(item.feature_value)}</p>
                        <p className="mt-1 text-xs text-slate-500">
                          contribution {item.contribution.toFixed(2)}
                          {item.note ? ` · ${item.note}` : ''}
                        </p>
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          </div>

          <JsonViewer value={features} title="市场状态特征" />
        </div>
      )}
    </SectionCard>
  );
}
