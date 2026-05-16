import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/state/ErrorState';
import { EmptyState, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { formatWorkspaceTimestamp } from './strategy-workspace-utils';
import type { ArtifactRecord } from '@/types/artifacts';
import type { StrategyVersionDetailItem, StrategyVersionSummaryItem } from '@/types/strategyStudio';

function matchesStrategyArtifact(artifact: ArtifactRecord) {
  const text = `${artifact.name} ${artifact.kind} ${artifact.source}`.toLowerCase();
  return text.includes('strategy') || text.includes('report') || text.includes('evidence') || text.includes('ranking');
}

type StrategyWorkspaceArtifactsProps = {
  versions: StrategyVersionSummaryItem[];
  selectedVersionId: string | null;
  selectedVersionDetail: StrategyVersionDetailItem | null;
  isVersionsLoading: boolean;
  versionsError: unknown;
  isVersionDetailLoading: boolean;
  versionDetailError: unknown;
  artifacts: ArtifactRecord[];
  isArtifactsLoading: boolean;
  artifactsError: unknown;
  onRetryVersions: () => void;
  onRetryVersionDetail: () => void;
  onRetryArtifacts: () => void;
  onSelectVersion: (versionId: string) => void;
};

export function StrategyWorkspaceArtifacts({
  versions,
  selectedVersionId,
  selectedVersionDetail,
  isVersionsLoading,
  versionsError,
  isVersionDetailLoading,
  versionDetailError,
  artifacts,
  isArtifactsLoading,
  artifactsError,
  onRetryVersions,
  onRetryVersionDetail,
  onRetryArtifacts,
  onSelectVersion,
}: StrategyWorkspaceArtifactsProps) {
  const navigate = useNavigate();
  const versionItems = useMemo(
    () =>
      [...versions].sort((left, right) => {
        const dateDiff = right.strategy_date.localeCompare(left.strategy_date);
        if (dateDiff !== 0) return dateDiff;
        return right.version_id.localeCompare(left.version_id);
      }),
    [versions],
  );
  const relevantArtifacts = useMemo(
    () =>
      [...artifacts]
        .filter(matchesStrategyArtifact)
        .sort((left, right) => {
          const rightTime = right.modified_at ?? '';
          const leftTime = left.modified_at ?? '';
          return rightTime.localeCompare(leftTime);
        }),
    [artifacts],
  );
  const selectedVersion = selectedVersionDetail;

  return (
    <section className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <SectionCard
        title="最近策略版本"
        description="查看版本链、发布日期和推荐数量，继续追踪正式输出。"
        action={
          <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={onRetryVersions} variant="outline">
            刷新
          </Button>
        }
      >
        {isVersionsLoading ? (
          <LoadingState label="正在加载策略版本" description="稍后会显示版本链、发布日期和推荐数量。" />
        ) : versionsError ? (
          <ErrorState {...buildErrorRecoveryState(versionsError, 'strategy')} onRetry={onRetryVersions} />
        ) : versionItems.length ? (
          <div className="space-y-3">
            {versionItems.map((item) => (
              <button
                key={item.version_id}
                className={`w-full rounded-2xl border p-4 text-left transition-colors ${
                  item.version_id === selectedVersionId
                    ? 'border-sky-300 bg-sky-50/80'
                    : 'border-slate-200 bg-white hover:border-sky-200 hover:bg-sky-50/60'
                }`}
                onClick={() => onSelectVersion(item.version_id)}
                type="button"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-base font-medium text-slate-950">{item.version_id}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      {item.trader_id} · {item.strategy_date} · {item.version_type}
                    </p>
                  </div>
                  <StatusBadge value={item.status} />
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                  <span className="rounded-full border border-slate-200 px-2 py-1">{item.recommendations_count} 条推荐</span>
                  <span className="rounded-full border border-slate-200 px-2 py-1">{item.source_article_ids_count} 篇来源文章</span>
                  <span className="rounded-full border border-slate-200 px-2 py-1">{item.has_rules_snapshot ? '含规则快照' : '无规则快照'}</span>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <EmptyState title="暂无策略版本。" description="选择 trader 并提交构建后，版本链会在这里显示。" />
        )}
      </SectionCard>

      <div className="space-y-4">
        <SectionCard
          title="版本详情与证据包"
          description="通过后端生成的推荐、证据引用和规则快照解释结果，不在前端重新计算。"
          action={
            <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={onRetryVersionDetail} variant="outline">
              刷新
            </Button>
          }
        >
          {isVersionDetailLoading ? (
            <LoadingState label="正在加载版本详情" description="稍后会显示推荐、证据引用和规则快照。" />
          ) : versionDetailError ? (
            <ErrorState {...buildErrorRecoveryState(versionDetailError, 'strategy')} onRetry={onRetryVersionDetail} />
          ) : selectedVersion ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <MetaCard label="版本 ID" value={selectedVersion.version_id} />
                <MetaCard label="交易员" value={selectedVersion.trader_id} />
                <MetaCard label="策略日期" value={selectedVersion.strategy_date} />
                <MetaCard label="版本类型" value={selectedVersion.version_type} />
                <MetaCard label="状态" value={selectedVersion.status} />
                <MetaCard label="发布时间" value={formatWorkspaceTimestamp(selectedVersion.released_at)} />
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <MetaCard label="推荐数" value={selectedVersion.recommendations?.length ?? 0} />
                <MetaCard label="来源文章" value={selectedVersion.source_article_ids.length} />
                <MetaCard label="证据引用" value={selectedVersion.evidence_refs.length} />
              </div>

              {selectedVersion.notes ? (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700">
                  {selectedVersion.notes}
                </div>
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                  当前版本没有附加说明。
                </div>
              )}

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-950">推荐明细</p>
                    <p className="mt-1 text-sm text-slate-600">展示后端输出的推荐结果，用于人工复核。</p>
                  </div>
                  <StatusBadge value="info" label={`${selectedVersion.recommendations.length} 条`} />
                </div>
                <div className="mt-4 space-y-3">
                  {selectedVersion.recommendations.length ? (
                    selectedVersion.recommendations.slice(0, 5).map((recommendation) => (
                      <div key={`${recommendation.symbol}-${recommendation.decision}`} className="rounded-xl border border-slate-200 bg-white p-3">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-medium text-slate-950">{recommendation.symbol}</p>
                            <p className="mt-1 text-sm text-slate-600">{recommendation.decision}</p>
                          </div>
                          <StatusBadge value="info" label={`${Math.round(recommendation.confidence * 100)}%`} />
                        </div>
                        {recommendation.rationale ? (
                          <p className="mt-2 text-sm leading-6 text-slate-600">{recommendation.rationale}</p>
                        ) : null}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-600">暂无推荐明细。</p>
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-medium text-slate-950">证据包引用</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {selectedVersion.evidence_refs.length ? (
                    selectedVersion.evidence_refs.map((ref) => (
                      <StatusBadge key={ref} value="info" label={ref} />
                    ))
                  ) : (
                    <span className="text-sm text-slate-600">暂无证据引用。</span>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <EmptyState title="请选择一个策略版本。" description="这里会展示结果解释、推荐、证据包和规则快照。" />
          )}
        </SectionCard>

        <SectionCard
          title="报告与证据包产物"
          description="这里展示和策略链路相关的报告、ranking 和 evidence 产物，最终查看以 Artifact Center 为准。"
          action={
            <div className="flex flex-wrap gap-2">
              <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={onRetryArtifacts} variant="outline">
                刷新
              </Button>
              <Button className="bg-sky-500 text-slate-950 hover:bg-sky-400" onClick={() => navigate('/artifacts')}>
                前往产物中心
              </Button>
            </div>
          }
        >
          {isArtifactsLoading ? (
            <LoadingState label="正在加载策略产物" description="稍后会展示和策略链路相关的报告、ranking 和 evidence 产物。" />
          ) : artifactsError ? (
            <ErrorState {...buildErrorRecoveryState(artifactsError, 'strategy')} onRetry={onRetryArtifacts} />
          ) : relevantArtifacts.length ? (
            <div className="space-y-3">
              {relevantArtifacts.slice(0, 6).map((artifact) => (
                <button
                  key={artifact.artifact_id}
                  className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left transition-colors hover:border-sky-200 hover:bg-sky-50/70"
                  onClick={() => navigate('/artifacts')}
                  type="button"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-base font-medium text-slate-950">{artifact.name}</p>
                      <p className="mt-1 text-sm text-slate-600">{artifact.kind} · {artifact.source}</p>
                  </div>
                  <StatusBadge value={artifact.exists ? 'success' : 'failed'} label={artifact.exists ? '可用' : '缺失'} />
                </div>
                  {artifact.preview ? <p className="mt-3 text-sm leading-6 text-slate-600">{artifact.preview}</p> : null}
                </button>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无可识别的策略报告或证据产物。" description="完成策略任务后，这里会展示最新产物入口。" />
          )}
        </SectionCard>
      </div>
    </section>
  );
}

function MetaCard({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-sm text-slate-900">{value ?? '未记录'}</p>
    </div>
  );
}
