import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ConfirmDialog, EmptyState, ErrorState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { listArtifacts } from '@/lib/api/artifacts';
import { createJob } from '@/lib/api/jobs';
import {
  createOptimizeCandidateVersion,
  getOptimizeVersion,
  listOptimizeVersions,
} from '@/lib/api/optimize';
import type { ArtifactRecord } from '@/types/artifacts';
import type { StrategyVersionDetailItem } from '@/types/strategyStudio';
import type { OptimizeCandidateCreateRequest, OptimizeVersionSummaryItem } from '@/types/optimize';

type PendingAction = 'create' | 'submit' | 'approve' | 'reject';

type StrategyWorkspaceCandidateProps = {
  traderId: string;
  selectedVersion: StrategyVersionDetailItem | null;
  onCandidateCreated?: (candidateVersionId: string) => void;
  onReviewSubmitted?: (jobId: string) => void;
};

function formatTimestamp(value: string | null | undefined) {
  if (!value) {
    return '未记录';
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function deriveAdjustments(selectedVersion: StrategyVersionDetailItem | null): OptimizeCandidateCreateRequest['adjustments'] {
  if (!selectedVersion) {
    return [];
  }

  return selectedVersion.rules_snapshot.map((rule, index) => {
    const snapshot = rule as Record<string, unknown>;
    const ruleId = String(snapshot.rule_id ?? snapshot.ruleId ?? `snapshot-${index + 1}`);
    const currentStatus = String(snapshot.status ?? snapshot.condition ?? snapshot.action ?? 'snapshot_review');
    return {
      trader_id: selectedVersion.trader_id,
      rule_id: ruleId,
      current_status: currentStatus,
      suggestion: '保留当前规则并生成候选规则版本',
      confidence: 0.5,
      basis: JSON.stringify(snapshot),
    };
  });
}

function CandidateSummaryCard({
  candidate,
  active,
  onSelect,
}: {
  candidate: OptimizeVersionSummaryItem;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
        active ? 'border-sky-200 bg-sky-50' : 'border-slate-200 bg-white hover:border-sky-200 hover:bg-slate-50'
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">{candidate.version_id}</p>
          <p className="mt-1 text-xs text-slate-500">
            父版本 {candidate.parent_version_id ?? 'n/a'} · {candidate.strategy_date}
          </p>
        </div>
        <StatusBadge value={candidate.status} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full border border-slate-200 px-2 py-1">版本类型 {candidate.version_type}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">推荐 {candidate.recommendations_count}</span>
      </div>
    </button>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-sm font-semibold text-slate-950">{value}</p>
    </div>
  );
}

export function StrategyWorkspaceCandidate({
  traderId,
  selectedVersion,
  onCandidateCreated,
  onReviewSubmitted,
}: StrategyWorkspaceCandidateProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [candidateNotes, setCandidateNotes] = useState('');
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const adjustments = useMemo(() => deriveAdjustments(selectedVersion), [selectedVersion]);

  useEffect(() => {
    setCandidateNotes(selectedVersion?.notes ?? '');
  }, [selectedVersion?.version_id, selectedVersion?.notes]);

  const candidateVersionsQuery = useQuery({
    queryKey: ['strategy-workspace', 'candidate-versions', traderId],
    queryFn: () =>
      listOptimizeVersions({
        trader_id: traderId.trim() || undefined,
        version_type: 'candidate',
        limit: 8,
      }),
    enabled: Boolean(traderId.trim()),
    staleTime: 30_000,
  });

  const candidateVersionItems = candidateVersionsQuery.data?.items ?? [];

  useEffect(() => {
    if (!candidateVersionItems.length) {
      setSelectedCandidateId(null);
      return;
    }

    if (!selectedCandidateId || !candidateVersionItems.some((item) => item.version_id === selectedCandidateId)) {
      setSelectedCandidateId(candidateVersionItems[0].version_id);
    }
  }, [candidateVersionItems, selectedCandidateId]);

  const selectedCandidateIdResolved = selectedCandidateId ?? candidateVersionItems[0]?.version_id ?? null;

  const candidateDetailQuery = useQuery({
    queryKey: ['strategy-workspace', 'candidate-detail', selectedCandidateIdResolved],
    queryFn: () => getOptimizeVersion(selectedCandidateIdResolved as string),
    enabled: Boolean(selectedCandidateIdResolved),
    staleTime: 30_000,
  });

  const selectedCandidateDetail = candidateDetailQuery.data?.item ?? null;
  const artifactsQuery = useQuery({
    queryKey: ['strategy-workspace', 'candidate-artifacts', traderId, selectedCandidateIdResolved],
    queryFn: () => listArtifacts({ limit: 12, q: selectedCandidateIdResolved ?? traderId }),
    enabled: Boolean(traderId.trim()),
    staleTime: 30_000,
  });

  const candidateArtifacts = useMemo(() => {
    const items = (artifactsQuery.data?.items ?? []) as ArtifactRecord[];
    return items.filter((artifact) => {
      const text = `${artifact.name} ${artifact.title} ${artifact.kind} ${artifact.job_type ?? ''} ${artifact.source}`.toLowerCase();
      return text.includes('candidate') || text.includes('optimize') || text.includes('strategy') || text.includes('report') || text.includes('evidence');
    });
  }, [artifactsQuery.data?.items]);

  const queryError = candidateVersionsQuery.error ?? candidateDetailQuery.error;
  const permissionDenied = queryError instanceof ApiError && (queryError.status === 401 || queryError.status === 403);

  const createCandidateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedVersion) {
        throw new Error('请先选择规则版本');
      }
      const payload: OptimizeCandidateCreateRequest = {
        parent_version_id: selectedVersion.version_id,
        trader_id: selectedVersion.trader_id,
        strategy_date: selectedVersion.strategy_date,
        adjustments,
        recommendations: selectedVersion.recommendations,
        notes: candidateNotes.trim() || null,
      };
      return createOptimizeCandidateVersion(payload);
    },
    onSuccess: async (result) => {
      setErrorMessage(null);
      setStatusMessage(`候选规则版本已生成: ${result.item.version_id}`);
      setPendingAction(null);
      setSelectedCandidateId(result.item.version_id);
      onCandidateCreated?.(result.item.version_id);
      await queryClient.invalidateQueries({ queryKey: ['strategy-workspace', 'candidate-versions'] });
      await queryClient.invalidateQueries({ queryKey: ['strategy-workspace', 'versions'] });
    },
    onError: (error) => {
      setStatusMessage(null);
      setErrorMessage(error instanceof Error ? error.message : '候选规则版本生成失败');
    },
  });

  const reviewMutation = useMutation({
    mutationFn: async (action: Exclude<PendingAction, 'create'>) => {
      if (!selectedCandidateIdResolved) {
        throw new Error('请先选择一个候选规则版本');
      }
      const decision = action === 'submit' ? 'pending' : action;
      return createJob({
        job_type: 'candidate-review',
        created_by: 'web',
        confirmed: true,
        params: {
          candidate_version_id: selectedCandidateIdResolved,
          decision,
          reviewed_by: 'web',
          force: true,
        },
      });
    },
    onSuccess: async (result, action) => {
      setErrorMessage(null);
      setStatusMessage(
        action === 'submit'
          ? `候选审核已提交，Job ${result.job.id}`
          : action === 'approve'
            ? `候选已批准，Job ${result.job.id}`
            : `候选已拒绝，Job ${result.job.id}`,
      );
      setPendingAction(null);
      onReviewSubmitted?.(result.job.id);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      await queryClient.invalidateQueries({ queryKey: ['strategy-workspace', 'candidate-versions'] });
      await queryClient.invalidateQueries({ queryKey: ['strategy-workspace', 'candidate-detail', selectedCandidateIdResolved] });
      await queryClient.invalidateQueries({ queryKey: ['strategy-workspace', 'candidate-artifacts', traderId, selectedCandidateIdResolved] });
    },
    onError: (error) => {
      setStatusMessage(null);
      setErrorMessage(error instanceof Error ? '候选审核提交失败，请稍后重试。' : '候选审核提交失败，请稍后重试。');
    },
  });

  if (queryError) {
    return (
      <SectionCard title="候选规则版本" description="查看候选规则版本、提交审核并追踪父版本与审计记录。">
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'strategy')}
          onRetry={
            permissionDenied
              ? undefined
              : () => {
                  void candidateVersionsQuery.refetch();
                  void candidateDetailQuery.refetch();
                }
          }
        />
      </SectionCard>
    );
  }

  return (
    <SectionCard
      title="候选规则版本"
      description="生成候选规则版本、比较父版本并提交审核任务。"
      action={<Badge variant="info">{candidateVersionItems.length} 个候选</Badge>}
    >
      <div className="space-y-4">
        {statusMessage ? (
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
            {statusMessage}
          </div>
        ) : null}
        {errorMessage ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
            {errorMessage}
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-950">候选规则版本列表</p>
                  <p className="mt-1 text-sm text-slate-600">最近生成的候选规则版本会在这里显示。</p>
                </div>
                <Button
                  className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  onClick={() => void candidateVersionsQuery.refetch()}
                  variant="outline"
                >
                  刷新
                </Button>
              </div>

              {candidateVersionsQuery.isLoading ? (
                <LoadingState label="正在加载候选规则版本" description="会读取最近候选和父版本信息。" />
              ) : candidateVersionItems.length ? (
                <div className="mt-4 space-y-3">
                  {candidateVersionItems.map((candidate) => (
                    <CandidateSummaryCard
                      key={candidate.version_id}
                      active={candidate.version_id === selectedCandidateIdResolved}
                      candidate={candidate}
                      onSelect={() => setSelectedCandidateId(candidate.version_id)}
                    />
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="暂无候选规则版本"
                  description="先选择一个规则版本并生成候选，候选列表会在这里出现。"
                />
              )}
            </div>

            <SectionCard
              title="相关产物链接"
              description="候选生成和审核相关的产物入口都在这里，最终下载与预览以产物中心为准。"
              action={
                <Button
                  className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  onClick={() => void artifactsQuery.refetch()}
                  variant="outline"
                >
                  刷新
                </Button>
              }
            >
              {artifactsQuery.isLoading ? (
                <LoadingState label="正在加载相关产物" description="稍后会显示候选生成和审核对应的产物链接。" />
              ) : artifactsQuery.error ? (
                <ErrorState
                  {...buildErrorRecoveryState(artifactsQuery.error, 'strategy')}
                  onRetry={() => void artifactsQuery.refetch()}
                />
              ) : candidateArtifacts.length ? (
                <div className="space-y-3">
                  {candidateArtifacts.slice(0, 4).map((artifact) => (
                    <div key={artifact.artifact_id} className="rounded-2xl border border-slate-200 bg-white p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-slate-950">{artifact.title || artifact.name}</p>
                          <p className="mt-1 text-xs text-slate-500">
                            {artifact.kind} · {artifact.job_type ?? '无 Job'} · {artifact.modified_at ?? '未记录'}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {artifact.job_id ? (
                            <Button
                              className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                              onClick={() => navigate(`/jobs/${artifact.job_id}`)}
                              variant="outline"
                            >
                              查看来源 Job
                            </Button>
                          ) : null}
                          <Button onClick={() => navigate('/artifacts')}>前往产物中心</Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="暂无相关产物"
                  description="生成候选或审核后，这里会显示对应的产物链接；也可以直接前往产物中心查看。"
                  actionLabel="前往产物中心"
                  onAction={() => navigate('/artifacts')}
                />
              )}
            </SectionCard>
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-950">候选生成与对比</p>
                  <p className="mt-1 text-sm text-slate-600">先确认生成参数，再把规则版本和候选规则版本放在一起核对。</p>
                </div>
                <StatusBadge value={selectedVersion?.status ?? 'draft'} />
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                <MiniStat label="规则版本" value={selectedVersion?.version_id ?? '未选择'} />
                <MiniStat label="父版本" value={selectedVersion?.parent_version_id ?? '无'} />
                <MiniStat label="规则快照" value={selectedVersion?.rules_snapshot.length ?? 0} />
                <MiniStat label="证据引用" value={selectedVersion?.evidence_refs.length ?? 0} />
              </div>
              <div className="mt-4 grid gap-3 xl:grid-cols-2">
                <div className="rounded-2xl border border-slate-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">候选备注</p>
                  <Textarea
                    aria-label="候选备注"
                    className="mt-2 min-h-32 border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                    placeholder="补充候选规则版本说明"
                    value={candidateNotes}
                    onChange={(event) => setCandidateNotes(event.target.value)}
                  />
                </div>
                <div className="space-y-3">
                  <JsonViewer value={adjustments} title="调整预览" />
                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">证据引用</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {selectedVersion?.evidence_refs.length ? (
                        selectedVersion.evidence_refs.map((ref) => (
                          <Badge key={ref} variant="info">
                            {ref}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-sm text-slate-600">暂无证据引用</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <Button
                  disabled={!selectedVersion || createCandidateMutation.isPending}
                  onClick={() => setPendingAction('create')}
                >
                  生成候选规则版本
                </Button>
              </div>

              <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-950">规则版本对比</p>
                    <p className="mt-1 text-sm text-slate-600">将当前选中的规则版本作为父版本，候选变更可回溯。</p>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <MiniStat label="执行日期" value={selectedVersion?.strategy_date ?? '未选择'} />
                  <MiniStat label="推荐数量" value={selectedVersion?.recommendations.length ?? 0} />
                </div>
                <div className="mt-4">
                  {selectedVersion ? (
                    <JsonViewer value={selectedVersion.recommendations} title="推荐明细" />
                  ) : (
                    <EmptyState title="请选择规则版本" description="在版本列表中选一个规则版本后，这里会显示对比数据。" />
                  )}
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-950">候选详情与审核</p>
                  <p className="mt-1 text-sm text-slate-600">候选规则版本来源、父版本和审核动作都在这里确认。</p>
                </div>
                {selectedCandidateDetail ? <StatusBadge value={selectedCandidateDetail.status} /> : null}
              </div>

              {candidateDetailQuery.isLoading ? (
                <LoadingState label="正在加载候选详情" description="会读取候选规则版本和父版本追溯信息。" />
              ) : selectedCandidateDetail ? (
                <div className="mt-4 space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <MiniStat label="候选规则版本" value={selectedCandidateDetail.version_id} />
                    <MiniStat label="父版本" value={selectedCandidateDetail.parent_version_id ?? 'n/a'} />
                    <MiniStat label="版本类型" value={selectedCandidateDetail.version_type} />
                    <MiniStat label="发布时间" value={formatTimestamp(selectedCandidateDetail.released_at)} />
                  </div>

                  <div className="grid gap-3 md:grid-cols-2">
                    <MiniStat label="推荐数" value={selectedCandidateDetail.recommendations.length} />
                    <MiniStat label="证据引用" value={selectedCandidateDetail.evidence_refs.length} />
                  </div>

                  <JsonViewer value={selectedCandidateDetail.recommendations} title="候选推荐" />

                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">候选证据</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {selectedCandidateDetail.evidence_refs.length ? (
                        selectedCandidateDetail.evidence_refs.map((ref) => (
                          <Badge key={ref} variant="info">
                            {ref}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-sm text-slate-600">暂无证据引用</span>
                      )}
                    </div>
                  </div>

                  <div className="grid gap-3 md:grid-cols-3">
                    <Button
                      disabled={!selectedCandidateIdResolved || reviewMutation.isPending}
                      onClick={() => setPendingAction('submit')}
                    >
                      提交审核
                    </Button>
                    <Button
                      disabled={!selectedCandidateIdResolved || reviewMutation.isPending}
                      onClick={() => setPendingAction('approve')}
                    >
                      批准
                    </Button>
                    <Button
                      disabled={!selectedCandidateIdResolved || reviewMutation.isPending}
                      onClick={() => setPendingAction('reject')}
                      variant="destructive"
                    >
                      拒绝
                    </Button>
                  </div>
                </div>
              ) : (
                <EmptyState
                  title="选择一个候选规则版本"
                  description="生成候选后，这里会显示候选规则版本、父版本和审核动作。"
                />
              )}
            </div>
          </div>
        </div>

        <ConfirmDialog
          open={Boolean(pendingAction)}
          onOpenChange={(open) => !open && setPendingAction(null)}
          title={
            pendingAction === 'create'
              ? '确认生成候选规则版本'
              : pendingAction === 'submit'
                ? '确认提交审核'
                : pendingAction === 'approve'
                  ? '确认批准候选'
                  : pendingAction === 'reject'
                    ? '确认拒绝候选'
                    : '确认候选操作'
          }
          description="这是正式写操作，会记录到任务轨迹和审计记录。"
          confirmLabel={
            createCandidateMutation.isPending || reviewMutation.isPending
              ? '提交中'
              : pendingAction === 'create'
                ? '确认生成'
                : '确认提交'
          }
          confirmDisabled={createCandidateMutation.isPending || reviewMutation.isPending}
          cancelLabel="取消"
          onConfirm={async () => {
            if (!pendingAction) {
              return;
            }
            if (pendingAction === 'create') {
              await createCandidateMutation.mutateAsync();
              return;
            }
            if (pendingAction === 'submit' || pendingAction === 'approve' || pendingAction === 'reject') {
              await reviewMutation.mutateAsync(pendingAction);
              return;
            }
          }}
        >
          <div className="space-y-3">
            <p>
              规则版本：<span className="font-medium text-slate-950">{selectedVersion?.version_id ?? '未选择'}</span>
            </p>
            <p>
              候选规则版本：<span className="font-medium text-slate-950">{selectedCandidateIdResolved ?? '未生成'}</span>
            </p>
            <p className="text-sm leading-6 text-slate-600">
              这会通过正式任务记录审计；候选规则版本生成和候选审核都保留追溯链。
            </p>
          </div>
        </ConfirmDialog>
      </div>
    </SectionCard>
  );
}
