import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/page-header';
import { ConfirmDialog, EmptyState, ErrorState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { getRulePoolRule, listRulePool, reviewRulePoolRule } from '@/lib/api/rule-pool';
import type { RuleDetailItem, RulePoolQuery, RulePoolReviewRequest, RuleSummaryItem } from '@/types/rule-pool';

const DEFAULT_FILTERS: RulePoolQuery = {
  status: 'pending',
  skip_no_mapped: false,
  skip: 0,
  limit: 18,
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

function formatConfidence(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${(value * 100).toFixed(1)}%`;
}

function RuleSummaryCard({
  rule,
  active,
  onClick,
}: {
  rule: RuleSummaryItem;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
        active ? 'border-sky-200 bg-sky-50' : 'border-slate-200 bg-white hover:border-sky-200 hover:bg-slate-50'
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-slate-950">{rule.rule_id}</p>
          <p className="mt-1 text-xs text-slate-500">
            {rule.rule_type} · {rule.instrument_focus} · {rule.source_type}
          </p>
        </div>
        <StatusBadge value={rule.review_status} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full border border-slate-200 px-2 py-1">映射 {rule.mapping_status}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">置信度 {formatConfidence(rule.validated_confidence ?? rule.initial_confidence)}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">回测样本 {rule.backtest_samples}</span>
      </div>
    </button>
  );
}

function SummaryStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-lg font-semibold text-slate-950">{value}</p>
    </div>
  );
}

type ReviewDecision = 'approve' | 'reject' | 'pending';

const REVIEW_ACTIONS: Array<{ decision: ReviewDecision; label: string; intent: 'default' | 'secondary' | 'destructive' }> = [
  { decision: 'approve', label: '批准', intent: 'default' },
  { decision: 'reject', label: '拒绝', intent: 'destructive' },
  { decision: 'pending', label: '标记待定', intent: 'secondary' },
];

export function RulePoolReviewWorkspace() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<RulePoolQuery>(DEFAULT_FILTERS);
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<ReviewDecision | null>(null);
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const rulesQuery = useQuery({
    queryKey: ['rule-pool', filters],
    queryFn: () =>
      listRulePool({
        status: filters.status || undefined,
        rule_type: filters.rule_type || undefined,
        mapping_status: filters.mapping_status || undefined,
        source_type: filters.source_type || undefined,
        instrument_focus: filters.instrument_focus || undefined,
        skip_no_mapped: filters.skip_no_mapped,
        skip: filters.skip,
        limit: filters.limit,
      }),
    staleTime: 30_000,
  });

  const ruleItems = rulesQuery.data?.items ?? [];
  const currentTotals = useMemo(
    () => ({
      total: rulesQuery.data?.total ?? 0,
      pending: ruleItems.filter((item) => item.review_status === 'pending').length,
      approved: ruleItems.filter((item) => item.review_status === 'approved').length,
      mapped: ruleItems.filter((item) => item.mapped).length,
    }),
    [ruleItems, rulesQuery.data?.total],
  );

  useEffect(() => {
    if (!ruleItems.length) {
      setSelectedRuleId(null);
      return;
    }
    if (!selectedRuleId || !ruleItems.some((item) => item.rule_id === selectedRuleId)) {
      setSelectedRuleId(ruleItems[0].rule_id);
    }
  }, [ruleItems, selectedRuleId]);

  const selectedRuleSummary = useMemo(
    () => ruleItems.find((item) => item.rule_id === selectedRuleId) ?? null,
    [ruleItems, selectedRuleId],
  );

  const selectedRuleIdResolved = selectedRuleId ?? ruleItems[0]?.rule_id ?? null;

  const detailQuery = useQuery({
    queryKey: ['rule-pool', 'detail', selectedRuleIdResolved],
    queryFn: () => getRulePoolRule(selectedRuleIdResolved as string),
    enabled: Boolean(selectedRuleIdResolved),
    staleTime: 30_000,
  });

  const selectedRule = detailQuery.data?.item ?? null;

  const reviewMutation = useMutation({
    mutationFn: async (decision: ReviewDecision) => {
      if (!selectedRuleIdResolved) {
        throw new Error('未选择规则');
      }
      const request: RulePoolReviewRequest = {
        decision,
        force: true,
        reviewed_by: 'web',
      };
      return reviewRulePoolRule(selectedRuleIdResolved, request);
    },
    onSuccess: async (_, decision) => {
      setSubmissionError(null);
      setSubmissionMessage(`规则 ${selectedRuleIdResolved} 已提交为 ${decision}。`);
      setPendingAction(null);
      await queryClient.invalidateQueries({ queryKey: ['rule-pool'] });
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'detail', selectedRuleIdResolved] });
    },
    onError: (error) => {
      setSubmissionError(error instanceof Error ? error.message : '规则审核失败');
    },
  });

  const queryError = rulesQuery.error ?? detailQuery.error;
  const permissionDenied = queryError instanceof ApiError && (queryError.status === 401 || queryError.status === 403);
  const selectedDetail = selectedRule ?? selectedRuleSummary;

  if (queryError) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="正式入口"
          title="规则池审核中心"
          description="在 Web 中查看规则证据、回测结果和审核动作。"
        />
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'strategy')}
          onRetry={
            permissionDenied
              ? undefined
              : () => {
                  void rulesQuery.refetch();
                  void detailQuery.refetch();
                }
          }
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="正式入口"
        title="规则池审核中心"
        description="查看规则列表、回测证据与审计轨迹，并在 Web 中完成批准或拒绝。"
        actionLabel="刷新"
        onAction={() => void rulesQuery.refetch()}
      />

      {submissionMessage ? (
        <section className="rounded-[28px] border border-emerald-200 bg-emerald-50 px-6 py-4 text-emerald-900 shadow-sm">
          <p className="font-medium">{submissionMessage}</p>
          <p className="mt-1 text-sm text-emerald-700">操作已写入审计，后续可在任务和规则详情中复查。</p>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.04fr)_minmax(0,0.96fr)]">
        <div className="space-y-6">
          <SectionCard
            title="规则筛选"
            description="按审核状态、类型和来源筛选规则池。"
            action={
              <Button
                variant="outline"
                className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                onClick={() => void rulesQuery.refetch()}
              >
                刷新
              </Button>
            }
          >
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <label className="space-y-2 text-sm text-slate-700">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">审核状态</span>
                <Select
                  aria-label="审核状态"
                  className="border-slate-200 bg-white text-slate-900"
                  value={filters.status ?? ''}
                  onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value || undefined, skip: 0 }))}
                >
                  <option value="">全部</option>
                  <option value="pending">pending</option>
                  <option value="approved">approved</option>
                  <option value="rejected">rejected</option>
                </Select>
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">规则类型</span>
                <Input
                  aria-label="规则类型"
                  className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                  placeholder="例如 breakout"
                  value={filters.rule_type ?? ''}
                  onChange={(event) => setFilters((current) => ({ ...current, rule_type: event.target.value || undefined, skip: 0 }))}
                />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">映射状态</span>
                <Input
                  aria-label="映射状态"
                  className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                  placeholder="mapped / unmapped"
                  value={filters.mapping_status ?? ''}
                  onChange={(event) => setFilters((current) => ({ ...current, mapping_status: event.target.value || undefined, skip: 0 }))}
                />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">来源类型</span>
                <Input
                  aria-label="来源类型"
                  className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                  placeholder="例如 standalone"
                  value={filters.source_type ?? ''}
                  onChange={(event) => setFilters((current) => ({ ...current, source_type: event.target.value || undefined, skip: 0 }))}
                />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">标的范围</span>
                <Input
                  aria-label="标的范围"
                  className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                  placeholder="例如 stock"
                  value={filters.instrument_focus ?? ''}
                  onChange={(event) => setFilters((current) => ({ ...current, instrument_focus: event.target.value || undefined, skip: 0 }))}
                />
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <input
                  checked={Boolean(filters.skip_no_mapped)}
                  className="h-4 w-4 rounded border-slate-300"
                  onChange={(event) => setFilters((current) => ({ ...current, skip_no_mapped: event.target.checked, skip: 0 }))}
                  type="checkbox"
                />
                <span>仅显示已映射规则</span>
              </label>
            </div>
          </SectionCard>

          <SectionCard title="规则概览" description="当前筛选下的审核统计。">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <SummaryStat label="总数" value={currentTotals.total} />
              <SummaryStat label="待审核" value={currentTotals.pending} />
              <SummaryStat label="已通过" value={currentTotals.approved} />
              <SummaryStat label="已映射" value={currentTotals.mapped} />
            </div>
          </SectionCard>

          <SectionCard
            title="规则列表"
            description={ruleItems.length ? `已加载 ${ruleItems.length} 条规则` : '暂无匹配规则'}
            action={<Badge variant="info">{rulesQuery.data?.total ?? 0} 条可见</Badge>}
          >
            {rulesQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full bg-slate-100" />
                <Skeleton className="h-24 w-full bg-slate-100" />
                <Skeleton className="h-24 w-full bg-slate-100" />
              </div>
            ) : ruleItems.length ? (
              <div className="grid gap-3">
                {ruleItems.map((rule) => (
                  <RuleSummaryCard
                    key={rule.rule_id}
                    rule={rule}
                    active={rule.rule_id === selectedRuleIdResolved}
                    onClick={() => setSelectedRuleId(rule.rule_id)}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                title="没有符合条件的规则"
                description="当前筛选没有返回规则条目，可以放宽筛选后重试。"
                actionLabel="重置筛选"
                onAction={() => setFilters(DEFAULT_FILTERS)}
              />
            )}
          </SectionCard>
        </div>

        <div className="space-y-6">
          <SectionCard title="规则详情" description="查看当前规则的回测证据、映射内容和审核信息。">
            {detailQuery.isLoading ? (
              <LoadingState label="加载规则详情" description="正在读取规则池详情和回测证据。" />
            ) : selectedDetail ? (
              <div className="space-y-6">
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">规则 ID</p>
                    <p className="mt-2 break-all text-sm font-medium text-slate-950">{selectedDetail.rule_id}</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">审核状态</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <StatusBadge value={selectedDetail.review_status} />
                      <Badge variant="info">{selectedDetail.mapping_status}</Badge>
                    </div>
                  </div>
                  <SummaryStat label="初始置信度" value={formatConfidence(selectedDetail.initial_confidence)} />
                  <SummaryStat label="校验后置信度" value={formatConfidence(selectedDetail.validated_confidence)} />
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <SummaryStat label="回测命中" value={selectedDetail.backtest_hits} />
                  <SummaryStat label="回测样本" value={selectedDetail.backtest_samples} />
                  <SummaryStat label="预测使用次数" value={selectedDetail.prediction_count} />
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                  <JsonViewer value={selectedDetail.backtest_result ?? {}} title="回测证据" />
                  <JsonViewer value={selectedDetail.extraction_layer ?? {}} title="映射证据" />
                </div>
              </div>
            ) : (
              <EmptyState
                title="请选择一条规则"
                description="从左侧规则列表中选择一条记录后，会显示详细证据和审核动作。"
              />
            )}
          </SectionCard>

          <SectionCard title="审计历史" description="该区域只展示与规则相关的可追溯记录。">
            {selectedDetail ? (
              <div className="grid gap-3 md:grid-cols-2">
                <AuditItem label="创建时间" value={formatTimestamp(selectedDetail.created_at)} />
                <AuditItem label="映射时间" value={formatTimestamp(selectedDetail.mapped_at)} />
                <AuditItem label="审核时间" value={formatTimestamp(selectedDetail.reviewed_at)} />
                <AuditItem label="回测触发时间" value={formatTimestamp(selectedDetail.backtest_triggered_at)} />
                <AuditItem label="最近使用时间" value={formatTimestamp(selectedDetail.last_used_at)} />
                <AuditItem label="更新时间" value={formatTimestamp(selectedDetail.updated_at)} />
              </div>
            ) : (
              <LoadingState label="等待规则详情" description="选择规则后将显示审计历史。" />
            )}
          </SectionCard>

          <SectionCard
            title="审核动作"
            description="批准、拒绝和标记待定都会写入后端审计。"
            action={<Badge variant="warning">高风险确认</Badge>}
          >
            {submissionError ? (
              <div className="mb-4">
                <ErrorState
                  category="job failed"
                  title="规则审核失败"
                  description="提交审核动作时返回了错误。"
                  suggestion="请先查看错误详情，再决定是否重试。"
                  detail={submissionError}
                />
              </div>
            ) : null}

            <div className="grid gap-3 md:grid-cols-3">
              {REVIEW_ACTIONS.map((action) => (
                <Button
                  key={action.decision}
                  className={action.intent === 'secondary' ? 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50' : undefined}
                  disabled={!selectedRuleIdResolved || reviewMutation.isPending}
                  onClick={() => setPendingAction(action.decision)}
                  variant={action.intent === 'destructive' ? 'destructive' : action.intent === 'secondary' ? 'outline' : 'default'}
                >
                  {action.label}
                </Button>
              ))}
            </div>
          </SectionCard>
        </div>
      </section>

      <ConfirmDialog
        open={Boolean(pendingAction)}
        onOpenChange={(open) => !open && setPendingAction(null)}
        title={pendingAction ? `${pendingAction === 'approve' ? '批准' : pendingAction === 'reject' ? '拒绝' : '标记待定'}规则` : '确认规则审核'}
        description="这是正式写操作。确认后会写入后端审计，并允许覆盖既有审核状态。"
        confirmLabel={reviewMutation.isPending ? '提交中' : '确认提交'}
        confirmDisabled={reviewMutation.isPending || !pendingAction || !selectedRuleIdResolved}
        cancelLabel="取消"
        onConfirm={async () => {
          if (!pendingAction) {
            return;
          }
          await reviewMutation.mutateAsync(pendingAction);
        }}
      >
        <div className="space-y-3">
          <p>
            规则：<span className="font-medium text-slate-950">{selectedRuleIdResolved ?? '未选择'}</span>
          </p>
          <p>
            当前状态：<span className="font-medium text-slate-950">{selectedDetail?.review_status ?? 'unknown'}</span>
          </p>
          <p>
            当前映射：<span className="font-medium text-slate-950">{selectedDetail?.mapping_status ?? 'unknown'}</span>
          </p>
          <p className="text-sm leading-6 text-slate-600">
            该操作会以强制模式提交，确保 UI 中的确认与后端审计一致。
          </p>
        </div>
      </ConfirmDialog>
    </main>
  );
}

function AuditItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-slate-950">{value}</p>
    </div>
  );
}
