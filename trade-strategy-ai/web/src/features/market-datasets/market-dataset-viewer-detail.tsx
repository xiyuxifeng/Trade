import { Link } from 'react-router-dom';
import { EmptyState, ErrorState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import type { ErrorRecoveryState } from '@/lib/error-recovery';
import type { MarketDatasetDetailResponse, MarketDatasetSummary } from '@/types/market';
import { MarketDatasetViewerSampleRows } from './market-dataset-viewer-sample-rows';

type MarketDatasetViewerDetailProps = {
  selectedDataset: MarketDatasetSummary | null;
  detail: MarketDatasetDetailResponse | null;
  errorState: ErrorRecoveryState | null;
  isLoading: boolean;
  onRetry: () => void;
  symbol: string;
  section: string;
  offset: number;
  limit: number;
  canPrev: boolean;
  canNext: boolean;
  onChangeSymbol: (symbol: string) => void;
  onChangeSection: (section: string) => void;
  onPrevPage: () => void;
  onNextPage: () => void;
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

function SummaryItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-sm font-medium text-slate-950">{value}</p>
    </div>
  );
}

export function MarketDatasetViewerDetail({
  selectedDataset,
  detail,
  errorState,
  isLoading,
  onRetry,
  symbol,
  section,
  offset,
  limit,
  canPrev,
  canNext,
  onChangeSymbol,
  onChangeSection,
  onPrevPage,
  onNextPage,
}: MarketDatasetViewerDetailProps) {
  const sourceJobId = readNestedString(
    selectedDataset?.storage_ref ?? detail?.dataset?.storage_ref,
    ['metadata', 'job_id'],
  );
  const snapshotId = detail?.snapshot?.snapshot_id ?? selectedDataset?.snapshot_id ?? null;
  const datasetLink = snapshotId ? `/market?snapshot_id=${encodeURIComponent(snapshotId)}` : null;
  const jobLink = sourceJobId ? `/jobs/${encodeURIComponent(sourceJobId)}` : null;
  const artifactLink = sourceJobId ? `/artifacts?jobId=${encodeURIComponent(sourceJobId)}` : null;
  const warnings = detail?.warnings ?? [];
  const pageTotal = detail?.page.total ?? detail?.items.length ?? 0;
  const storageSource = readNestedString(selectedDataset?.storage_ref, ['source']) ?? 'db';

  return (
    <SectionCard
      title="数据集详情"
      description={selectedDataset ? '展示选中 dataset 的 metadata、sample rows、snapshot 回链和质量信息。' : '请选择一个数据集查看详情。'}
      className="border-slate-200 bg-white"
    >
      {isLoading ? (
        <LoadingState label="正在加载数据集详情" description="包括 metadata、样本行和 snapshot 回链。" />
      ) : errorState ? (
        <ErrorState {...errorState} onRetry={errorState.retryable ? onRetry : undefined} />
      ) : detail && selectedDataset ? (
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <SummaryItem label="Dataset" value={selectedDataset.dataset_id} />
            <SummaryItem label="Trade Date" value={selectedDataset.trade_date} />
            <SummaryItem label="Market" value={selectedDataset.market} />
            <SummaryItem label="Type" value={selectedDataset.dataset_type} />
          </div>

          <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">质量状态</p>
                  <p className="mt-1 text-base font-semibold text-slate-950">{selectedDataset.quality_status}</p>
                </div>
                <StatusBadge value={selectedDataset.quality_status} />
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <SummaryItem label="Profile" value={selectedDataset.profile_id ?? '未记录'} />
                <SummaryItem label="Source" value={selectedDataset.source ?? '未知'} />
                <SummaryItem label="Snapshot" value={snapshotId ?? '未关联'} />
                <SummaryItem label="Storage Ref" value={storageSource} />
              </div>
              <div className="mt-4 flex flex-wrap gap-2 text-sm">
                {datasetLink ? (
                  <Link className="text-sky-700 hover:underline" to={datasetLink}>
                    前往 Snapshot
                  </Link>
                ) : (
                  <span className="text-slate-500">暂无 Snapshot 回链</span>
                )}
                {jobLink ? (
                  <>
                    <span className="text-slate-400">·</span>
                    <Link className="text-sky-700 hover:underline" to={jobLink}>
                      前往 Job 详情
                    </Link>
                  </>
                ) : null}
                {artifactLink ? (
                  <>
                    <span className="text-slate-400">·</span>
                    <Link className="text-sky-700 hover:underline" to={artifactLink}>
                      前往产物中心
                    </Link>
                  </>
                ) : null}
              </div>
            </div>

            <JsonViewer value={selectedDataset.storage_ref ?? {}} title="存储引用" />
          </div>

          <SectionCard title="质量与提示" description="展示 dataset detail 返回的质量摘要和警告。">
            <div className="space-y-3">
              <p className="text-sm leading-6 text-slate-700">
                {detail.snapshot ? '当前 dataset 已关联 snapshot。' : '当前 dataset 尚未关联 snapshot。'}
              </p>
              {warnings.length ? (
                <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-slate-700">
                  {warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm leading-6 text-slate-700">没有额外警告。</p>
              )}
            </div>
          </SectionCard>

          <MarketDatasetViewerSampleRows
            rows={detail.items}
            totalCount={pageTotal}
            symbol={symbol}
            section={section}
            offset={offset}
            limit={limit}
            isLoading={false}
            onChangeSymbol={onChangeSymbol}
            onChangeSection={onChangeSection}
            onPrevPage={onPrevPage}
            onNextPage={onNextPage}
            canPrev={canPrev}
            canNext={canNext}
          />
        </div>
      ) : (
        <div className="space-y-4">
          <EmptyState title="请选择一个数据集" description="点击左侧列表中的 dataset 进入详情查看。" />
          <div className="flex flex-wrap gap-2 text-sm">
            <Link className="text-sky-700 hover:underline" to="/market">
              返回市场数据
            </Link>
            <span className="text-slate-400">·</span>
            <Link className="text-sky-700 hover:underline" to="/artifacts">
              前往产物中心
            </Link>
          </div>
        </div>
      )}
    </SectionCard>
  );
}
