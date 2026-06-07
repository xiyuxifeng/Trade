import { Link } from 'react-router-dom';
import { EmptyState, ErrorState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import type {
  MarketRegimeFeatureDetailResponse,
  MarketRegimeFeatureSummary,
  MarketRegimeDetailResponse,
  MarketSnapshotDetailResponse,
  MarketSnapshotListItem,
  MarketSnapshotQualityResponse,
  MarketSnapshotSectionSummary,
} from '@/types/market';
import { MarketRegimePanel } from './market-regime-panel';
import { MarketSnapshotBrowserRegimeFeatures } from './market-snapshot-browser-regime-features';

type MarketSnapshotBrowserDetailProps = {
  snapshotId: string | null;
  selectedSnapshot: MarketSnapshotListItem | null;
  detail: MarketSnapshotDetailResponse | null;
  sections: MarketSnapshotSectionSummary[];
  quality: MarketSnapshotQualityResponse | null;
  regime: MarketRegimeDetailResponse | null;
  regimeFeatures: MarketRegimeFeatureSummary[];
  regimeFeatureDetail: MarketRegimeFeatureDetailResponse | null;
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
  tradeDate: string;
};

function readNestedString(value: unknown, path: string[]): string | null {
  let current: unknown = value;
  for (const key of path) {
    if (!current || typeof current !== 'object') {
      return null;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return typeof current === 'string' && current.trim() ? current : null;
}

function readAnyString(values: unknown[], path: string[]): string | null {
  for (const value of values) {
    const found = readNestedString(value, path);
    if (found) return found;
  }
  return null;
}

function SummaryItem({ label, value }: { label: string; value: string | number | null | undefined | Record<string, unknown> }) {
  const renderedValue = value === null || value === undefined ? 'n/a' : typeof value === 'string' || typeof value === 'number' ? value : JSON.stringify(value);
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-sm font-medium text-slate-950">{renderedValue}</p>
    </div>
  );
}

export function MarketSnapshotBrowserDetail({
  snapshotId,
  selectedSnapshot,
  detail,
  sections,
  quality,
  regime,
  regimeFeatures,
  regimeFeatureDetail,
  isLoading,
  error,
  onRetry,
  tradeDate,
}: MarketSnapshotBrowserDetailProps) {
  const datasetId = readAnyString([detail?.dataset], ['dataset_id']);
  const sourceJobId = readAnyString(
    [detail?.dataset, detail?.quality_report, regimeFeatureDetail?.feature_payload_json, regimeFeatureDetail?.summary_json],
    ['storage_ref', 'metadata', 'job_id'],
  );
  const relatedDataLink = datasetId
    ? `/market/datasets?trade_date=${encodeURIComponent(selectedSnapshot?.trade_date ?? tradeDate)}&market=${encodeURIComponent(
        selectedSnapshot?.market ?? 'CN',
      )}&dataset_id=${encodeURIComponent(datasetId)}`
    : `/market/datasets?trade_date=${encodeURIComponent(selectedSnapshot?.trade_date ?? tradeDate)}&market=${encodeURIComponent(
        selectedSnapshot?.market ?? 'CN',
      )}`;
  const fallbackArtifactLink = `/artifacts?jobType=snapshot-build&date=${tradeDate}&source=market-snapshot-browser`;
  const artifactLink = sourceJobId ? `/artifacts?jobId=${encodeURIComponent(sourceJobId)}` : fallbackArtifactLink;
  const jobLink = sourceJobId ? `/jobs/${encodeURIComponent(sourceJobId)}` : '/jobs';
  const errorState = error ? buildErrorRecoveryState(error, 'market') : null;
  const qualityReport = quality?.quality_report as Record<string, unknown> | null | undefined;
  const qualityStatus = typeof qualityReport?.overall_status === 'string' ? qualityReport.overall_status : selectedSnapshot?.quality_status ?? 'unknown';
  const warnings = detail?.warnings ?? [];
  const qualitySummary =
    typeof qualityReport?.summary === 'string'
      ? qualityReport.summary
      : warnings.length
        ? warnings.join('；')
        : '质量报告已加载。';

  return (
    <SectionCard
      title="市场上下文快照详情"
      description={snapshotId ? '右侧保持当前市场上下文快照详情，切换列表筛选后如果快照仍然存在会继续保留。' : '请选择一个市场上下文快照查看详情。'}
      className="border-slate-200 bg-white"
    >
      {isLoading ? (
        <LoadingState label="正在加载快照详情" description="包括快照、sections、质量报告和市场状态特征。" />
      ) : errorState ? (
        <ErrorState
          {...errorState}
          onRetry={errorState.retryable ? onRetry : undefined}
        />
      ) : detail && selectedSnapshot ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <SummaryItem label="快照ID" value={selectedSnapshot.snapshot_id} />
            <SummaryItem label="交易日" value={selectedSnapshot.trade_date ?? '未记录'} />
            <SummaryItem label="市场" value={selectedSnapshot.market} />
            <SummaryItem label="数据版本" value={selectedSnapshot.data_version} />
          </div>

          <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">质量状态</p>
                  <p className="mt-1 text-base font-semibold text-slate-950">{qualityStatus}</p>
                </div>
                <StatusBadge value={selectedSnapshot.quality_status} />
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-700">{qualitySummary}</p>
              <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
                <Link className="text-sky-700 hover:underline" to={jobLink}>
                  前往 Job 详情
                </Link>
                <span className="text-slate-400">·</span>
                <Link className="text-sky-700 hover:underline" to={relatedDataLink}>
                  查看相关数据
                </Link>
                <span className="text-slate-400">·</span>
                <Link className="text-sky-700 hover:underline" to={artifactLink}>
                  前往产物中心
                </Link>
              </div>
            </div>

            <JsonViewer value={quality?.quality_report ?? detail.quality_report ?? {}} title="质量报告" />
          </div>

          <SectionCard title="分段内容" description="展示当前市场上下文快照的 section 摘要与缺失信息。">
            {sections.length ? (
              <div className="space-y-3">
                {sections.map((section) => (
                  <div key={section.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-base font-semibold text-slate-950">{section.section_id}</p>
                        <p className="mt-1 text-sm text-slate-600">
                          {section.provider ?? '未知 provider'} · {section.source_time ?? '未记录'} · {section.section_version ?? '未知版本'}
                        </p>
                      </div>
                      <StatusBadge value={section.quality_status} />
                    </div>
                    <div className="mt-4 grid gap-3 md:grid-cols-3">
                      <SummaryItem label="记录数" value={section.record_count} />
                      <SummaryItem label="缺失原因" value={section.missing_reason ?? '无'} />
                      <SummaryItem
                        label="存储引用"
                        value={typeof section.storage_ref?.source === 'string' ? section.storage_ref.source : 'db'}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无分段内容" description="这个市场上下文快照还没有可展示的 section 摘要。" />
            )}
          </SectionCard>

          <MarketRegimePanel regime={regime} isLoading={false} errorState={null} />

          <MarketSnapshotBrowserRegimeFeatures
            items={regimeFeatures}
            detail={regimeFeatureDetail}
            isLoading={false}
            errorState={null}
          />
        </div>
      ) : (
        <EmptyState title="请选择一个市场上下文快照" description="点击左侧列表中的任意一项查看详情。" />
      )}
    </SectionCard>
  );
}
