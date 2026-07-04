import { useEffect, useMemo, useState, type ReactNode } from 'react';
import dayjs from 'dayjs';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { ConfirmDialog, EmptyState, ErrorState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { createJob } from '@/lib/api/jobs';
import {
  generateRuleApplicabilityProfile,
  getRuleApplicabilityProfile,
  getRulePoolRule,
  listRuleApplicabilityProfiles,
  reviewRuleApplicabilityProfile,
  reviewRulePoolRule,
} from '@/lib/api/rule-pool';
import type {
  RuleApplicabilityProfileItem,
  RuleApplicabilityGenerateRequest,
  RuleApplicabilityReviewRequest,
  RulePoolReviewRequest,
} from '@/types/rule-pool';

const PROFILE_STATUS_OPTIONS: Array<RuleApplicabilityGenerateRequest['review_status']> = ['draft', 'reviewed', 'active', 'archived'];

const REVIEW_ACTIONS: Array<{ decision: 'approve' | 'reject' | 'pending'; label: string; intent: 'default' | 'secondary' | 'destructive' }> = [
  { decision: 'approve', label: '批准', intent: 'default' },
  { decision: 'reject', label: '拒绝', intent: 'destructive' },
  { decision: 'pending', label: '标记待定', intent: 'secondary' },
];

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

function formatDecisionLabel(value: string) {
  if (value === 'applicable') {
    return '适用';
  }
  if (value === 'blocked') {
    return '禁用';
  }
  return '中性';
}

function SummaryStat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <div className="mt-2 break-all text-lg font-semibold text-slate-950">{value}</div>
    </div>
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

export function RulePoolDetailPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const params = useParams<{ ruleId?: string }>();
  const ruleId = params.ruleId?.trim() || '';
  const today = useMemo(() => dayjs().format('YYYY-MM-DD'), []);
  const defaultStart = useMemo(() => dayjs(today).subtract(30, 'day').format('YYYY-MM-DD'), [today]);

  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [submissionMessage, setSubmissionMessage] = useState<string | null>(null);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<'approve' | 'reject' | 'pending' | null>(null);
  const [backtestJobId, setBacktestJobId] = useState<string | null>(null);
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
  const [backtestForm, setBacktestForm] = useState({
    startDate: defaultStart,
    endDate: today,
    minConfidence: 0.5,
    marketRegimeVersion: 'market-regime-v3',
  });

  const detailQuery = useQuery({
    queryKey: ['rule-pool', 'detail', ruleId],
    queryFn: () => getRulePoolRule(ruleId),
    enabled: Boolean(ruleId),
    staleTime: 30_000,
  });

  const selectedRule = detailQuery.data?.item ?? null;

  const profilesQuery = useQuery({
    queryKey: ['rule-pool', 'applicability', ruleId],
    queryFn: () => listRuleApplicabilityProfiles(ruleId, { skip: 0, limit: 20 }),
    enabled: Boolean(ruleId),
    staleTime: 30_000,
  });

  const profileItems = profilesQuery.data?.items ?? [];

  useEffect(() => {
    if (!profileItems.length) {
      setSelectedProfileId(null);
      return;
    }
    if (!selectedProfileId) {
      setSelectedProfileId(profileItems[0].profile_id);
    }
  }, [profileItems, selectedProfileId]);

  const selectedProfile = useMemo(
    () => profileItems.find((item) => item.profile_id === selectedProfileId) ?? null,
    [profileItems, selectedProfileId],
  );

  const selectedProfileIdResolved = selectedProfileId ?? profileItems[0]?.profile_id ?? null;

  const profileDetailQuery = useQuery({
    queryKey: ['rule-pool', 'applicability', ruleId, selectedProfileIdResolved],
    queryFn: () => getRuleApplicabilityProfile(ruleId, selectedProfileIdResolved as string),
    enabled: Boolean(ruleId && selectedProfileIdResolved),
    staleTime: 30_000,
  });

  const selectedProfileDetail = profileDetailQuery.data?.item ?? selectedProfile ?? null;

  const reviewMutation = useMutation({
    mutationFn: async (decision: 'approve' | 'reject' | 'pending') => {
      if (!ruleId) {
        throw new Error('未选择规则');
      }
      const request: RulePoolReviewRequest = {
        decision,
        force: true,
        reviewed_by: 'web',
      };
      return reviewRulePoolRule(ruleId, request);
    },
    onSuccess: async (_, decision) => {
      setSubmissionError(null);
      setSubmissionMessage(`规则 ${ruleId} 已提交为 ${decision}。`);
      setPendingAction(null);
      await queryClient.invalidateQueries({ queryKey: ['rule-pool'] });
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'detail', ruleId] });
    },
    onError: (error) => {
      setSubmissionError(error instanceof Error ? error.message : '规则审核失败');
    },
  });

  const generateProfileMutation = useMutation({
    mutationFn: async () => {
      if (!ruleId) {
        throw new Error('未选择规则');
      }
      if (!profileDraft.sourceBacktestId.trim()) {
        throw new Error('请先填写 source_backtest_id');
      }
      return generateRuleApplicabilityProfile(ruleId, {
        source_backtest_id: profileDraft.sourceBacktestId.trim(),
        profile_version: profileDraft.profileVersion.trim() || 'rule-applicability-v1',
        min_sample_count: profileDraft.minSampleCount,
        review_status: profileDraft.reviewStatus,
        reviewed_by: 'web',
      });
    },
    onSuccess: async (response) => {
      setSubmissionError(null);
      setSubmissionMessage(`规则 ${ruleId} 已生成适用性画像。`);
      setSelectedProfileId(response.item.profile_id);
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'applicability', ruleId] });
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'applicability', ruleId, response.item.profile_id] });
    },
    onError: (error) => {
      setSubmissionError(error instanceof Error ? error.message : '适用性画像生成失败');
    },
  });

  const reviewProfileMutation = useMutation({
    mutationFn: async (review_status: RuleApplicabilityReviewRequest['review_status']) => {
      if (!ruleId || !selectedProfileIdResolved) {
        throw new Error('未选择适用性画像');
      }
      return reviewRuleApplicabilityProfile(ruleId, selectedProfileIdResolved, {
        review_status,
        reviewed_by: 'web',
      });
    },
    onSuccess: async (response) => {
      setSubmissionError(null);
      setSubmissionMessage(`画像 ${response.item.profile_id} 已更新为 ${response.item.review_status}。`);
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'applicability', ruleId] });
      await queryClient.invalidateQueries({ queryKey: ['rule-pool', 'applicability', ruleId, selectedProfileIdResolved] });
    },
    onError: (error) => {
      setSubmissionError(error instanceof Error ? error.message : '适用性画像审核失败');
    },
  });

  const ruleBacktestMutation = useMutation({
    mutationFn: async () => {
      if (!ruleId) {
        throw new Error('未选择规则');
      }
      const result = await createJob({
        job_type: 'rule-pool-backtest',
        params: {
          rule_id: ruleId,
          start_date: backtestForm.startDate,
          end_date: backtestForm.endDate,
          min_confidence: backtestForm.minConfidence,
          market_regime_version: backtestForm.marketRegimeVersion,
        },
        created_by: 'web',
        max_retries: 3,
        retry_backoff_seconds: 0,
        timeout_seconds: null,
      });
      return result;
    },
    onSuccess: async (response) => {
      setBacktestJobId(response.job.id);
      setSubmissionError(null);
      setSubmissionMessage(`规则回测 Job ${response.job.id} 已提交。`);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
    onError: (error) => {
      setSubmissionError(error instanceof Error ? error.message : '规则回测任务提交失败');
    },
  });

  const queryError = detailQuery.error ?? profilesQuery.error ?? profileDetailQuery.error;
  const permissionDenied = queryError instanceof ApiError && (queryError.status === 401 || queryError.status === 403);
  const selectedDetail = selectedRule;

  if (!ruleId) {
    return (
      <main className="page-stack">
        <ErrorState
          category="validation error"
          title="规则详情参数缺失"
          description="缺少规则 ID，无法打开详情页。"
          suggestion="请从规则列表进入详情页。"
          actions={[{ label: '返回规则池', to: '/rule-pool' }]}
        />
      </main>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader kicker="规则池" title="规则详情" description="正在加载规则、画像、审计与回测入口。" />
        <LoadingState label="加载规则详情" description="正在读取规则池详情和回测证据。" />
      </main>
    );
  }

  if (queryError) {
    return (
      <main className="page-stack">
        <PageHeader kicker="规则池" title="规则详情" description="正在加载规则、画像、审计与回测入口。" />
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'strategy')}
          onRetry={
            permissionDenied
              ? undefined
              : () => {
                  void detailQuery.refetch();
                  void profilesQuery.refetch();
                  void profileDetailQuery.refetch();
                }
          }
        />
      </main>
    );
  }

  if (!selectedDetail) {
    return (
      <main className="page-stack">
        <ErrorState
          category="data empty"
          title="规则不存在"
          description="无法读取规则详情。"
          suggestion="请返回规则列表重新选择一条规则。"
          actions={[{ label: '返回规则池', to: '/rule-pool' }]}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader kicker="规则池" title="规则详情" description="查看规则详情、适用性画像、审计轨迹，并提交规则回测 Job。" />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="outline" onClick={() => navigate('/rule-pool')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回规则池
        </Button>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => void detailQuery.refetch()}>
            刷新详情
          </Button>
          {backtestJobId ? (
            <Button variant="secondary" onClick={() => navigate(`/system/jobs/${encodeURIComponent(backtestJobId)}`)}>
              前往 Job 详情
            </Button>
          ) : null}
        </div>
      </div>

      {submissionMessage ? (
        <section className="rounded-[28px] border border-emerald-200 bg-emerald-50 px-6 py-4 text-emerald-900 shadow-sm">
          <p className="font-medium">{submissionMessage}</p>
          <p className="mt-1 text-sm text-emerald-700">操作已写入审计，可在规则详情与 Job 详情中复查。</p>
        </section>
      ) : null}

      {submissionError ? (
        <ErrorState
          category="job failed"
          title="规则池操作失败"
          description="提交审核、画像生成或回测任务时发生错误。"
          suggestion="请检查输入参数或重试。"
          detail={submissionError}
        />
      ) : null}

      <section className="space-y-6">
        <SectionCard title="规则详情" description="查看当前规则的回测证据、映射内容和审核信息。">
          <div className="space-y-6">
            <div className="grid gap-3 md:grid-cols-2">
              <SummaryStat label="规则 ID" value={selectedDetail.rule_id} />
              <SummaryStat
                label="审核状态"
                value={
                  <div className="flex flex-wrap gap-2">
                    <StatusBadge value={selectedDetail.review_status} />
                    <Badge variant="info">{selectedDetail.mapping_status}</Badge>
                  </div>
                }
              />
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
        </SectionCard>

        <SectionCard title="规则回测" description="运行当前规则的回测 Job，并跳转到 Job 详情进行查看。">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="space-y-2 text-sm text-slate-700">
              <span className="text-xs uppercase tracking-[0.16em] text-slate-500">开始日期</span>
              <Input type="date" value={backtestForm.startDate} onChange={(event) => setBacktestForm((current) => ({ ...current, startDate: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span className="text-xs uppercase tracking-[0.16em] text-slate-500">结束日期</span>
              <Input type="date" value={backtestForm.endDate} onChange={(event) => setBacktestForm((current) => ({ ...current, endDate: event.target.value }))} />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span className="text-xs uppercase tracking-[0.16em] text-slate-500">最小置信度</span>
              <Input
                type="number"
                min={0}
                max={1}
                step="0.05"
                value={backtestForm.minConfidence}
                onChange={(event) =>
                  setBacktestForm((current) => ({
                    ...current,
                    minConfidence: Number.parseFloat(event.target.value) || 0.5,
                  }))
                }
              />
            </label>
            <label className="space-y-2 text-sm text-slate-700">
              <span className="text-xs uppercase tracking-[0.16em] text-slate-500">市场状态版本</span>
              <Select
                value={backtestForm.marketRegimeVersion}
                onChange={(event) => setBacktestForm((current) => ({ ...current, marketRegimeVersion: event.target.value }))}
              >
                <option value="market-regime-v3">market-regime-v3</option>
                <option value="market-regime-v2">market-regime-v2</option>
                <option value="market-regime-v1">market-regime-v1</option>
              </Select>
            </label>
          </div>

          <div className="mt-4 flex flex-wrap gap-3">
            <Button disabled={ruleBacktestMutation.isPending} onClick={() => void ruleBacktestMutation.mutateAsync()}>
              {ruleBacktestMutation.isPending ? '提交中' : '运行当前规则回测'}
            </Button>
            {backtestJobId ? (
              <Button variant="outline" onClick={() => navigate(`/system/jobs/${encodeURIComponent(backtestJobId)}`)}>
                打开 Job 详情
              </Button>
            ) : null}
          </div>
        </SectionCard>

        <SectionCard title="审核动作" description="批准、拒绝和标记待定都会写入后端审计。" action={<Badge variant="warning">高风险确认</Badge>}>
          <div className="grid gap-3 md:grid-cols-3">
            {REVIEW_ACTIONS.map((action) => (
              <Button
                key={action.decision}
                className={action.intent === 'secondary' ? 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50' : undefined}
                disabled={reviewMutation.isPending}
                onClick={() => setPendingAction(action.decision)}
                variant={action.intent === 'destructive' ? 'destructive' : action.intent === 'secondary' ? 'outline' : 'default'}
              >
                {action.label}
              </Button>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="审计历史" description="该区域只展示与规则相关的可追溯记录。">
          <div className="grid gap-3 md:grid-cols-2">
            <AuditItem label="创建时间" value={formatTimestamp(selectedDetail.created_at)} />
            <AuditItem label="映射时间" value={formatTimestamp(selectedDetail.mapped_at)} />
            <AuditItem label="审核时间" value={formatTimestamp(selectedDetail.reviewed_at)} />
            <AuditItem label="回测触发时间" value={formatTimestamp(selectedDetail.backtest_triggered_at)} />
            <AuditItem label="最近使用时间" value={formatTimestamp(selectedDetail.last_used_at)} />
            <AuditItem label="更新时间" value={formatTimestamp(selectedDetail.updated_at)} />
          </div>
        </SectionCard>

        <SectionCard title="适用性画像" description="按市场状态回测结果生成规则适用/禁用画像，并支持 Web 审核。">
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
              <Button disabled={!ruleId || generateProfileMutation.isPending} onClick={() => void generateProfileMutation.mutateAsync()}>
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
                  <EmptyState title="暂无适用性画像" description="当前规则还没有生成 Rule Applicability Profile。" />
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
                  <EmptyState title="请选择一个画像" description="从左侧列表中选择规则画像，或先生成新的 profile。" />
                )}
              </div>
            </div>
          </div>
        </SectionCard>
      </section>

      <ConfirmDialog
        open={Boolean(pendingAction)}
        onOpenChange={(open) => !open && setPendingAction(null)}
        title={pendingAction ? `${pendingAction === 'approve' ? '批准' : pendingAction === 'reject' ? '拒绝' : '标记待定'}规则` : '确认规则审核'}
        description="这是正式写操作。确认后会写入后端审计，并允许覆盖既有审核状态。"
        confirmLabel={reviewMutation.isPending ? '提交中' : '确认提交'}
        confirmDisabled={reviewMutation.isPending || !pendingAction}
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
            规则：<span className="font-medium text-slate-950">{ruleId}</span>
          </p>
          <p>
            当前状态：<span className="font-medium text-slate-950">{selectedDetail.review_status}</span>
          </p>
          <p>
            当前映射：<span className="font-medium text-slate-950">{selectedDetail.mapping_status}</span>
          </p>
          <p className="text-sm leading-6 text-slate-600">
            该操作会以强制模式提交，确保 UI 中的确认与后端审计一致。
          </p>
        </div>
      </ConfirmDialog>
    </main>
  );
}
