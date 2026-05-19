import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/page-header';
import { ConfirmDialog, EmptyState, ErrorState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import {
  generateRuleApplicabilityProfile,
  getRuleApplicabilityProfile,
  getRulePoolRule,
  listRuleApplicabilityProfiles,
  listRulePool,
  reviewRuleApplicabilityProfile,
  reviewRulePoolRule,
} from '@/lib/api/rule-pool';
import type {
  RuleApplicabilityProfileItem,
  RuleApplicabilityGenerateRequest,
  RuleApplicabilityReviewRequest,
  RulePoolQuery,
  RulePoolReviewRequest,
  RuleSummaryItem,
} from '@/types/rule-pool';

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

function formatPct(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${(value * 100).toFixed(2)}%`;
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

function SummaryStat({ label, value }: { label: string; value: string | number | null | undefined }) {
  const renderedValue = value === null || value === undefined ? 'n/a' : value;
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-lg font-semibold text-slate-950">{renderedValue}</p>
    </div>
  );
}

type ReviewDecision = 'approve' | 'reject' | 'pending';

const REVIEW_ACTIONS: Array<{ decision: ReviewDecision; label: string; intent: 'default' | 'secondary' | 'destructive' }> = [
  { decision: 'approve', label: '批准', intent: 'default' },
  { decision: 'reject', label: '拒绝', intent: 'destructive' },
  { decision: 'pending', label: '标记待定', intent: 'secondary' },
];

const PROFILE_STATUS_OPTIONS: Array<RuleApplicabilityGenerateRequest['review_status']> = ['draft', 'reviewed', 'active', 'archived'];

function formatDecisionLabel(value: string) {
  if (value === 'applicable') {
    return '适用';
  }
  if (value === 'blocked') {
    return '禁用';
  }
  return '中性';
}

function ApplicabilityRegimeList({
  title,
  items,
  tone,
}: {
  title: string;
  items: RuleApplicabilityProfileItem['applicable_regimes'];
  tone: 'success' | 'danger' | 'warning';
}) {
  const badgeVariant = tone === 'success' ? 'success' : tone === 'danger' ? 'destructive' : 'warning';
  return (
    <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-slate-950">{title}</h4>
        <Badge variant={badgeVariant}>{items.length} 条</Badge>
      </div>
      {items.length ? (
        <div className="mt-3 space-y-3">
          {items.map((item) => (
            <div key={`${title}-${item.regime_label}`} className="rounded-2xl border border-slate-200 bg-white p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-slate-950">{item.regime_label}</span>
                <Badge variant="info">{formatDecisionLabel(item.decision)}</Badge>
                {item.low_sample ? <Badge variant="warning">低样本</Badge> : <Badge variant="success">样本充足</Badge>}
              </div>
              <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
                <span>分数 {item.score.toFixed(3)}</span>
                <span>样本 {item.sample_count}</span>
                <span>胜率 {formatPct(item.win_rate)}</span>
                <span>平均收益 {formatPct(item.avg_return)}</span>
                <span>最大回撤 {formatPct(item.max_drawdown)}</span>
                <span>置信度 {formatPct(item.confidence)}</span>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">{item.reason}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {item.evidence.map((fact) => (
                  <span key={fact} className="rounded-full border border-slate-200 px-2 py-1 text-[11px] text-slate-500">
                    {fact}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-slate-500">暂无条目</p>
      )}
    </section>
  );
}

function ApplicabilityProfileCard({
  profile,
  active,
  onClick,
}: {
  profile: RuleApplicabilityProfileItem;
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
          <p className="text-sm font-semibold text-slate-950">{profile.profile_version}</p>
          <p className="mt-1 text-xs text-slate-500">来源 {profile.source_backtest_id}</p>
        </div>
        <Badge variant={profile.review_status === 'active' ? 'success' : profile.review_status === 'archived' ? 'warning' : 'info'}>
          {profile.review_status}
        </Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full border border-slate-200 px-2 py-1">置信度 {formatConfidence(profile.confidence)}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">适用 {profile.applicable_regimes.length}</span>
        <span className="rounded-full border border-slate-200 px-2 py-1">禁用 {profile.blocked_regimes.length}</span>
      </div>
    </button>
  );
}

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

  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [applicabilityMessage, setApplicabilityMessage] = useState<string | null>(null);
  const [applicabilityError, setApplicabilityError] = useState<string | null>(null);
  const [profileDraft, setProfileDraft] = useState<{
    sourceBacktestId: string;
    profileVersion: string;
    minSampleCount: number;
    reviewStatus: RuleApplicabilityGenerateRequest['review_status'];
  }>({
    sourceBacktestId: '',
    profileVersion: 'rule-applicability-v1',
    minSampleCount: 5,
    reviewStatus: 'draft',
  });

  const profilesQuery = useQuery({
    queryKey: ['rule-pool', 'applicability', selectedRuleIdResolved],
    queryFn: () => listRuleApplicabilityProfiles(selectedRuleIdResolved as string, { skip: 0, limit: 20 }),
    enabled: Boolean(selectedRuleIdResolved),
    staleTime: 30_000,
  });

  const profileItems = profilesQuery.data?.items ?? [];
  useEffect(() => {
    if (!profileItems.length) {
      setSelectedProfileId(null);
      return;
    }
    if (!selectedProfileId || !profileItems.some((item) => item.profile_id === selectedProfileId)) {
      setSelectedProfileId(profileItems[0].profile_id);
    }
  }, [profileItems, selectedProfileId]);

  const selectedProfile = useMemo(
    () => profileItems.find((item) => item.profile_id === selectedProfileId) ?? null,
    [profileItems, selectedProfileId],
  );

  const selectedProfileIdResolved = selectedProfileId ?? profileItems[0]?.profile_id ?? null;

  const profileDetailQuery = useQuery({
    queryKey: ['rule-pool', 'applicability', selectedRuleIdResolved, selectedProfileIdResolved],
    queryFn: () => getRuleApplicabilityProfile(selectedRuleIdResolved as string, selectedProfileIdResolved as string),
    enabled: Boolean(selectedRuleIdResolved && selectedProfileIdResolved),
    staleTime: 30_000,
  });

  const selectedProfileDetail = profileDetailQuery.data?.item ?? selectedProfile ?? null;

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

  const generateProfileMutation = useMutation({
    mutationFn: async () => {
      if (!selectedRuleIdResolved) {
        throw new Error('未选择规则');
      }
      if (!profileDraft.sourceBacktestId.trim()) {
        throw new Error('请先填写 source_backtest_id');
      }
      return generateRuleApplicabilityProfile(selectedRuleIdResolved, {
        source_backtest_id: profileDraft.sourceBacktestId.trim(),
        profile_version: profileDraft.profileVersion.trim() || 'rule-applicability-v1',
        min_sample_count: profileDraft.minSampleCount,
        review_status: profileDraft.reviewStatus,
        reviewed_by: 'web',
      });
    },
    onSuccess: async (response) => {
      setApplicabilityError(null);
      setApplicabilityMessage(`规则 ${selectedRuleIdResolved} 已生成适用性画像。`);
      setSelectedProfileId(response.item.profile_id);
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'applicability', selectedRuleIdResolved] });
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'applicability', selectedRuleIdResolved, response.item.profile_id] });
    },
    onError: (error) => {
      setApplicabilityError(error instanceof Error ? error.message : '适用性画像生成失败');
    },
  });

  const reviewProfileMutation = useMutation({
    mutationFn: async (review_status: RuleApplicabilityReviewRequest['review_status']) => {
      if (!selectedRuleIdResolved || !selectedProfileIdResolved) {
        throw new Error('未选择适用性画像');
      }
      return reviewRuleApplicabilityProfile(selectedRuleIdResolved, selectedProfileIdResolved, {
        review_status,
        reviewed_by: 'web',
      });
    },
    onSuccess: async (response) => {
      setApplicabilityError(null);
      setApplicabilityMessage(`画像 ${response.item.profile_id} 已更新为 ${response.item.review_status}。`);
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'applicability', selectedRuleIdResolved] });
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'applicability', selectedRuleIdResolved, selectedProfileIdResolved] });
    },
    onError: (error) => {
      setApplicabilityError(error instanceof Error ? error.message : '适用性画像审核失败');
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

          <SectionCard title="适用性画像" description="按 Regime-aware Backtest 结果生成规则适用/禁用画像，并支持 Web 审核。">
            {applicabilityMessage ? (
              <section className="rounded-[24px] border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-900">
                <p className="font-medium">{applicabilityMessage}</p>
                <p className="mt-1 text-sm text-emerald-700">画像已落库，后续可从规则池详情回查。</p>
              </section>
            ) : null}
            {applicabilityError ? (
              <div className="mb-4">
                <ErrorState
                  category="job failed"
                  title="适用性画像操作失败"
                  description="生成或审核 profile 时发生错误。"
                  suggestion="请检查回测结果 ID、样本阈值或后端接口返回。"
                  detail={applicabilityError}
                />
              </div>
            ) : null}

            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <label className="space-y-2 text-sm text-slate-700">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">回测结果 ID</span>
                  <Input
                    aria-label="回测结果 ID"
                    className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                    placeholder="例如 result-20260519-001"
                    value={profileDraft.sourceBacktestId}
                    onChange={(event) => setProfileDraft((current) => ({ ...current, sourceBacktestId: event.target.value }))}
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Profile Version</span>
                  <Input
                    aria-label="Profile Version"
                    className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                    value={profileDraft.profileVersion}
                    onChange={(event) => setProfileDraft((current) => ({ ...current, profileVersion: event.target.value }))}
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">最小样本数</span>
                  <Input
                    aria-label="最小样本数"
                    className="border-slate-200 bg-white text-slate-900 placeholder:text-slate-400"
                    inputMode="numeric"
                    type="number"
                    value={profileDraft.minSampleCount}
                    onChange={(event) =>
                      setProfileDraft((current) => ({
                        ...current,
                        minSampleCount: Number.parseInt(event.target.value, 10) || 1,
                      }))
                    }
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">初始状态</span>
                  <Select
                    aria-label="初始状态"
                    className="border-slate-200 bg-white text-slate-900"
                    value={profileDraft.reviewStatus}
                    onChange={(event) =>
                      setProfileDraft((current) => ({
                        ...current,
                        reviewStatus: event.target.value as RuleApplicabilityGenerateRequest['review_status'],
                      }))
                    }
                  >
                    {PROFILE_STATUS_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </Select>
                </label>
              </div>

              <div className="flex flex-wrap gap-3">
                <Button
                  disabled={!selectedRuleIdResolved || generateProfileMutation.isPending}
                  onClick={() => void generateProfileMutation.mutateAsync()}
                >
                  {generateProfileMutation.isPending ? '生成中' : '生成画像'}
                </Button>
                <Button
                  className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  disabled={!selectedProfileIdResolved || reviewProfileMutation.isPending}
                  onClick={() => void reviewProfileMutation.mutateAsync('reviewed')}
                  variant="outline"
                >
                  标记已评审
                </Button>
                <Button
                  className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  disabled={!selectedProfileIdResolved || reviewProfileMutation.isPending}
                  onClick={() => void reviewProfileMutation.mutateAsync('active')}
                  variant="outline"
                >
                  激活
                </Button>
                <Button
                  className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                  disabled={!selectedProfileIdResolved || reviewProfileMutation.isPending}
                  onClick={() => void reviewProfileMutation.mutateAsync('archived')}
                  variant="outline"
                >
                  归档
                </Button>
              </div>

              <div className="grid gap-4 xl:grid-cols-[0.92fr_1.08fr]">
                <div className="space-y-3">
                  {profilesQuery.isLoading ? (
                    <LoadingState label="加载画像列表" description="正在读取指定规则的适用性画像。" />
                  ) : profilesQuery.error ? (
                    <ErrorState
                      category="job failed"
                      title="适用性画像列表加载失败"
                      description="后端返回了错误。"
                      suggestion="请检查接口权限或重试。"
                      detail={profilesQuery.error instanceof Error ? profilesQuery.error.message : '加载失败'}
                      onRetry={() => void profilesQuery.refetch()}
                    />
                  ) : profileItems.length ? (
                    <div className="grid gap-3">
                      {profileItems.map((profile) => (
                        <ApplicabilityProfileCard
                          key={profile.profile_id}
                          profile={profile}
                          active={profile.profile_id === selectedProfileIdResolved}
                          onClick={() => setSelectedProfileId(profile.profile_id)}
                        />
                      ))}
                    </div>
                  ) : (
                    <EmptyState
                      title="暂无适用性画像"
                      description="当前规则还没有生成 Rule Applicability Profile。"
                    />
                  )}
                </div>

                <div className="space-y-4">
                  {profileDetailQuery.isLoading ? (
                    <LoadingState label="加载画像详情" description="正在读取适用/禁用市场环境。" />
                  ) : selectedProfileDetail ? (
                    <div className="space-y-4">
                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        <SummaryStat label="Profile ID" value={selectedProfileDetail.profile_id} />
                        <SummaryStat label="Profile Version" value={selectedProfileDetail.profile_version} />
                        <SummaryStat label="Source Backtest" value={selectedProfileDetail.source_backtest_id} />
                        <SummaryStat label="置信度" value={formatConfidence(selectedProfileDetail.confidence)} />
                        <SummaryStat label="最小样本数" value={selectedProfileDetail.min_sample_count} />
                        <SummaryStat label="审核状态" value={selectedProfileDetail.review_status} />
                      </div>

                      <div className="grid gap-3 md:grid-cols-3">
                        <SummaryStat label="适用 Regime" value={selectedProfileDetail.applicable_regimes.length} />
                        <SummaryStat label="禁用 Regime" value={selectedProfileDetail.blocked_regimes.length} />
                        <SummaryStat label="中性 Regime" value={selectedProfileDetail.neutral_regimes.length} />
                      </div>

                      {selectedProfileDetail.applicable_regimes.some((item) => item.low_sample) ||
                      selectedProfileDetail.blocked_regimes.some((item) => item.low_sample) ||
                      selectedProfileDetail.neutral_regimes.some((item) => item.low_sample) ? (
                        <section className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900">
                          <p className="font-medium">当前画像包含低样本 regime，适用于观察，不应直接作为唯一选择依据。</p>
                        </section>
                      ) : null}

                      <ApplicabilityRegimeList title="适用市场环境" items={selectedProfileDetail.applicable_regimes} tone="success" />
                      <ApplicabilityRegimeList title="禁用市场环境" items={selectedProfileDetail.blocked_regimes} tone="danger" />
                      <ApplicabilityRegimeList title="中性市场环境" items={selectedProfileDetail.neutral_regimes} tone="warning" />

                      <div className="grid gap-4 xl:grid-cols-2">
                        <JsonViewer value={selectedProfileDetail.best_market_conditions ?? {}} title="最佳市场条件" />
                        <JsonViewer value={selectedProfileDetail.worst_market_conditions ?? {}} title="最差市场条件" />
                      </div>

                      <JsonViewer value={selectedProfileDetail.summary ?? {}} title="画像摘要" />
                    </div>
                  ) : (
                    <EmptyState
                      title="请选择一个画像"
                      description="从左侧列表中选择规则画像，或先生成新的 profile。"
                    />
                  )}
                </div>
              </div>
            </div>
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
