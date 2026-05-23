import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { PageHeader } from '@/components/layout/page-header';
import { TraderIdSelect } from '@/components/inputs/trader-id-select';
import { ApiError } from '@/lib/api/http';
import {
  adviseRuleValidations,
  createCandidateVersion,
  getStrategyRule,
  getStrategyVersion,
  listStrategyRules,
  listStrategyVersions,
  reviewStrategyRule,
  reviewStrategyRuleBatch,
} from '@/lib/api/strategyStudio';
import type {
  CandidateCreateRequest,
  RuleDetailItem,
  RuleSummaryItem,
  StrategyVersionDetailItem,
  StrategyVersionSummaryItem,
} from '@/types/strategyStudio';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return 'Strategy Studio 数据加载失败';
}

function formatNumber(value: number | null | undefined, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return value.toFixed(digits);
}

function formatPercent(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return 'n/a';
  return dayjs(value).format('YYYY-MM-DD HH:mm');
}

function StatusBadge({ value }: { value: string }) {
  const variant =
    value === 'released' || value === 'approved'
      ? 'success'
      : value === 'draft' || value === 'pending'
        ? 'warning'
        : value === 'candidate'
          ? 'info'
          : 'default';

  const labelMap: Record<string, string> = {
    released: '已发布',
    approved: '已批准',
    draft: '草稿',
    pending: '待定',
    candidate: '候选',
    rejected: '已拒绝',
  };

  return <Badge variant={variant}>{labelMap[value] || value}</Badge>;
}

function MetricCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function EmptyPanel({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 px-4 py-8 text-center">
      <p className="text-sm font-medium text-slate-200">{title}</p>
      <p className="mt-2 text-sm text-slate-500">{description}</p>
    </div>
  );
}

function VersionRow({
  item,
  active,
  onSelect,
}: {
  item: StrategyVersionSummaryItem;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
        active
          ? 'border-sky-500/40 bg-sky-500/10 text-sky-100'
          : 'border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-medium">{item.version_id}</p>
          <p className="break-all text-xs text-slate-500">{item.trader_id} · {item.strategy_date}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <StatusBadge value={item.status} />
          <Badge variant={item.version_type === 'candidate' ? 'info' : 'default'}>
            {item.version_type === 'candidate' ? '候选' : item.version_type}
          </Badge>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded-full border border-slate-800/80 px-2 py-1">推荐数 {item.recommendations_count}</span>
        <span className="rounded-full border border-slate-800/80 px-2 py-1">规则快照 {item.has_rules_snapshot ? '有' : '无'}</span>
      </div>
    </button>
  );
}

function RuleRow({
  item,
  active,
  onSelect,
}: {
  item: RuleSummaryItem;
  active: boolean;
  onSelect: () => void;
}) {
  const reviewStatusMap: Record<string, string> = {
    approved: '已批准',
    rejected: '已拒绝',
    pending: '待定',
  };
  const mappingStatusMap: Record<string, string> = {
    mapped: '已映射',
    unmapped: '未映射',
  };

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
        active
          ? 'border-sky-500/40 bg-sky-500/10 text-sky-100'
          : 'border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-medium">{item.rule_id}</p>
          <p className="break-all text-xs text-slate-500">{item.rule_type} · {item.instrument_focus}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge variant={item.review_status === 'approved' ? 'success' : item.review_status === 'rejected' ? 'destructive' : 'warning'}>
            {reviewStatusMap[item.review_status] || item.review_status}
          </Badge>
          <Badge variant={item.mapping_status === 'mapped' ? 'info' : 'default'}>
            {mappingStatusMap[item.mapping_status] || item.mapping_status}
          </Badge>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded-full border border-slate-800/80 px-2 py-1">置信度 {formatNumber(item.validated_confidence ?? item.initial_confidence, 3)}</span>
        <span className="rounded-full border border-slate-800/80 px-2 py-1">回测命中 {item.backtest_hits}</span>
        <span className="rounded-full border border-slate-800/80 px-2 py-1">样本数 {item.backtest_samples}</span>
      </div>
    </button>
  );
}

function VersionJsonPanel({ detail }: { detail: StrategyVersionDetailItem }) {
  return (
    <pre
      className="max-h-[30rem] overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200"
      data-testid="strategy-version-json"
    >
      {JSON.stringify(detail, null, 2)}
    </pre>
  );
}

function RuleJsonPanel({ detail }: { detail: RuleDetailItem }) {
  return (
    <pre
      className="max-h-[26rem] overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200"
      data-testid="strategy-rule-json"
    >
      {JSON.stringify(detail, null, 2)}
    </pre>
  );
}

export function StrategyStudio() {
  const queryClient = useQueryClient();
  const today = useMemo(() => dayjs().format('YYYY-MM-DD'), []);

  const [traderId, setTraderId] = useState('trader_a');
  const [strategyDate, setStrategyDate] = useState(today);
  const [versionStatus, setVersionStatus] = useState('');
  const [versionType, setVersionType] = useState('');
  const [versionSkip, setVersionSkip] = useState(0);
  const [versionLimit, setVersionLimit] = useState(20);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [candidateNotes, setCandidateNotes] = useState('');

  const [ruleStatus, setRuleStatus] = useState('');
  const [ruleType, setRuleType] = useState('');
  const [mappingStatus, setMappingStatus] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [instrumentFocus, setInstrumentFocus] = useState('');
  const [skipNoMapped, setSkipNoMapped] = useState(false);
  const [ruleSkip, setRuleSkip] = useState(0);
  const [ruleLimit, setRuleLimit] = useState(20);
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [reviewDecision, setReviewDecision] = useState<'approve' | 'reject' | 'pending'>('approve');
  const [reviewForce, setReviewForce] = useState(false);
  const [reviewedBy, setReviewedBy] = useState('web');
  const [batchDecision, setBatchDecision] = useState<'approve' | 'reject' | 'pending'>('approve');
  const [batchStatus, setBatchStatus] = useState<'pending' | 'approved' | 'rejected'>('pending');
  const [batchLimit, setBatchLimit] = useState(25);
  const [batchForce, setBatchForce] = useState(false);
  const [batchReviewedBy, setBatchReviewedBy] = useState('web');
  const [validationAdviceMessage, setValidationAdviceMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const versionsQuery = useQuery({
    queryKey: ['strategy-studio', 'versions', traderId, strategyDate, versionStatus, versionType, versionSkip, versionLimit],
    queryFn: () =>
      listStrategyVersions({
        trader_id: traderId || undefined,
        status: versionStatus || undefined,
        version_type: versionType || undefined,
        date_from: strategyDate || undefined,
        date_to: strategyDate || undefined,
        skip: versionSkip,
        limit: versionLimit,
      }),
    staleTime: 10_000,
  });

  const rulesQuery = useQuery({
    queryKey: ['strategy-studio', 'rules', ruleStatus, ruleType, mappingStatus, sourceType, instrumentFocus, skipNoMapped, ruleSkip, ruleLimit],
    queryFn: () =>
      listStrategyRules({
        status: ruleStatus || undefined,
        rule_type: ruleType || undefined,
        mapping_status: mappingStatus || undefined,
        source_type: sourceType || undefined,
        instrument_focus: instrumentFocus || undefined,
        skip_no_mapped: skipNoMapped,
        skip: ruleSkip,
        limit: ruleLimit,
      }),
    staleTime: 10_000,
  });

  const versionItems = versionsQuery.data?.items ?? [];
  const ruleItems = rulesQuery.data?.items ?? [];

  useEffect(() => {
    if (!versionItems.length) {
      setSelectedVersionId(null);
      return;
    }
    if (!selectedVersionId || !versionItems.some((item) => item.version_id === selectedVersionId)) {
      setSelectedVersionId(versionItems[0].version_id);
    }
  }, [selectedVersionId, versionItems]);

  useEffect(() => {
    if (!ruleItems.length) {
      setSelectedRuleId(null);
      return;
    }
    if (!selectedRuleId || !ruleItems.some((item) => item.rule_id === selectedRuleId)) {
      setSelectedRuleId(ruleItems[0].rule_id);
    }
  }, [ruleItems, selectedRuleId]);

  const versionDetailQuery = useQuery({
    queryKey: ['strategy-studio', 'version-detail', selectedVersionId],
    queryFn: () => getStrategyVersion(selectedVersionId as string),
    enabled: Boolean(selectedVersionId),
  });

  const ruleDetailQuery = useQuery({
    queryKey: ['strategy-studio', 'rule-detail', selectedRuleId],
    queryFn: () => getStrategyRule(selectedRuleId as string),
    enabled: Boolean(selectedRuleId),
  });

  const selectedVersion = versionDetailQuery.data?.item ?? null;
  const selectedRule = ruleDetailQuery.data?.item ?? null;

  useEffect(() => {
    setCandidateNotes(selectedVersion?.notes ?? '');
  }, [selectedVersion?.version_id, selectedVersion?.notes]);

  const candidateAdjustments = useMemo(() => {
    if (!selectedVersion) return [];
    return selectedVersion.rules_snapshot.map((rule, index) => {
      const snapshot = rule as Record<string, unknown>;
      const ruleId = String(snapshot.rule_id ?? snapshot.ruleId ?? `snapshot-${index + 1}`);
      return {
        trader_id: selectedVersion.trader_id,
        rule_id: ruleId,
        current_status: 'snapshot_review',
        suggestion: '保留当前规则并生成候选版本',
        confidence: 0.5,
        basis: JSON.stringify(snapshot),
      };
    });
  }, [selectedVersion]);

  const candidateMutation = useMutation({
    mutationFn: async () => {
      if (!selectedVersion) {
        throw new Error('请先选择一个策略版本');
      }
      const payload: CandidateCreateRequest = {
        parent_version_id: selectedVersion.version_id,
        trader_id: selectedVersion.trader_id,
        strategy_date: selectedVersion.strategy_date,
        adjustments: candidateAdjustments,
        recommendations: selectedVersion.recommendations,
        notes: candidateNotes,
      };
      return createCandidateVersion(payload);
    },
    onSuccess: async (result) => {
      setStatusMessage(`候选版本已生成: ${result.item.version_id}`);
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ['strategy-studio'] });
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error));
      setStatusMessage(null);
    },
  });

  const adviseMutation = useMutation({
    mutationFn: async () => {
      if (!selectedVersion || !selectedRule) {
        throw new Error('请选择一个版本和一条规则后再生成优化建议');
      }
      return adviseRuleValidations([
        {
          trader_id: selectedVersion.trader_id,
          strategy_version_id: selectedVersion.version_id,
          rule_id: selectedRule.rule_id,
          rule_text: String((selectedRule.extraction_layer['raw_text'] as string | undefined) ?? selectedRule.rule_type ?? selectedRule.rule_id),
          programmable: true,
          validation_status: 'validated',
          hit_count: selectedRule.backtest_hits,
          sample_count: selectedRule.backtest_samples,
          hit_rate: selectedRule.backtest_samples > 0 ? selectedRule.backtest_hits / selectedRule.backtest_samples : null,
          posterior_return_mean: null,
          posterior_return_median: null,
          notes: [],
          result_version: '1.0',
        },
      ]);
    },
    onSuccess: async (result) => {
      setValidationAdviceMessage(`已生成 ${result.count} 条优化建议`);
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ['strategy-studio'] });
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error));
      setValidationAdviceMessage(null);
    },
  });

  const reviewRuleMutation = useMutation({
    mutationFn: async () => {
      if (!selectedRule) {
        throw new Error('请选择一条规则');
      }
      return reviewStrategyRule(selectedRule.rule_id, {
        decision: reviewDecision,
        force: reviewForce,
        reviewed_by: reviewedBy,
      });
    },
    onSuccess: async () => {
      setStatusMessage('规则审核已提交');
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ['strategy-studio', 'rules'] });
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error));
      setStatusMessage(null);
    },
  });

  const reviewBatchMutation = useMutation({
    mutationFn: async () => {
      if (!window.confirm(`确认将规则池中 ${batchLimit} 条 ${batchStatus} 规则按 ${batchDecision} 处理？`)) {
        throw new Error('已取消批量审核');
      }
      return reviewStrategyRuleBatch({
        decision: batchDecision,
        status: batchStatus,
        limit: batchLimit,
        force: batchForce,
        reviewed_by: batchReviewedBy,
      });
    },
    onSuccess: async () => {
      setStatusMessage('批量规则审核已提交');
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ['strategy-studio', 'rules'] });
    },
    onError: (error) => {
      if (error instanceof Error && error.message === '已取消批量审核') {
        return;
      }
      setErrorMessage(getErrorMessage(error));
      setStatusMessage(null);
    },
  });

  const summary = useMemo(() => {
    const totalVersions = versionsQuery.data?.total ?? 0;
    const candidateVersions = versionItems.filter((item) => item.version_type === 'candidate').length;
    const totalRules = rulesQuery.data?.total ?? 0;
    const approvedRules = ruleItems.filter((item) => item.review_status === 'approved').length;
    const pendingRules = ruleItems.filter((item) => item.review_status === 'pending').length;
    return { totalVersions, candidateVersions, totalRules, approvedRules, pendingRules };
  }, [ruleItems, rulesQuery.data?.total, versionItems, versionsQuery.data?.total]);

  const refreshAll = async () => {
    await queryClient.invalidateQueries({ queryKey: ['strategy-studio'] });
    setStatusMessage('已刷新 Strategy Studio 数据');
    setErrorMessage(null);
  };

  return (
    <main className="page-stack">
      <PageHeader
        kicker="策略工作室"
        title="策略工作室"
        description="在一站式工作区中浏览策略版本、生成候选版本并审核规则池。"
        actionLabel="全部刷新"
        onAction={() => {
          void refreshAll();
        }}
      />

      {(statusMessage || errorMessage || validationAdviceMessage) && (
        <div className="space-y-2">
          {statusMessage ? <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{statusMessage}</div> : null}
          {validationAdviceMessage ? <div className="rounded-xl border border-sky-500/20 bg-sky-500/10 px-4 py-3 text-sm text-sky-200">{validationAdviceMessage}</div> : null}
          {errorMessage ? <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{errorMessage}</div> : null}
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="版本总数" value={summary.totalVersions} accent="text-sky-300" />
        <MetricCard title="候选版本" value={summary.candidateVersions} />
        <MetricCard title="规则总数" value={summary.totalRules} />
        <MetricCard title="已批准 / 待处理" value={`${summary.approvedRules} / ${summary.pendingRules}`} accent="text-emerald-300" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)_400px]">
        <Card>
          <CardHeader>
            <CardTitle>策略版本</CardTitle>
            <CardDescription>按交易员、日期、版本状态和版本类型过滤。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              <label className="space-y-2 text-sm text-slate-300">
                <span>交易员 ID</span>
                <TraderIdSelect
                  ariaLabel="Trader ID"
                  className="border-slate-700 bg-slate-950 text-slate-100"
                  onChange={setTraderId}
                  source="strategy"
                  value={traderId}
                />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>策略日期</span>
                <Input aria-label="Strategy date" type="date" value={strategyDate} onChange={(event) => setStrategyDate(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>状态</span>
                <Select aria-label="Version status" value={versionStatus} onChange={(event) => setVersionStatus(event.target.value)}>
                  <option value="">全部</option>
                  <option value="draft">草稿</option>
                  <option value="released">已发布</option>
                  <option value="archived">已存档</option>
                </Select>
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>版本类型</span>
                <Select aria-label="Version type" value={versionType} onChange={(event) => setVersionType(event.target.value)}>
                  <option value="">全部</option>
                  <option value="manual">手动</option>
                  <option value="candidate">候选</option>
                </Select>
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="space-y-2 text-sm text-slate-300">
                  <span>跳过 (Skip)</span>
                  <Input aria-label="Version skip" type="number" min={0} value={versionSkip} onChange={(event) => setVersionSkip(Number(event.target.value || 0))} />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span>限制 (Limit)</span>
                  <Input aria-label="Version limit" type="number" min={1} max={100} value={versionLimit} onChange={(event) => setVersionLimit(Number(event.target.value || 0))} />
                </label>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setVersionSkip(0)}>
                  重置页码
                </Button>
                <Button variant="outline" size="sm" onClick={() => void versionsQuery.refetch()}>
                  重新加载
                </Button>
              </div>
            </div>

            <div className="space-y-3">
              {versionsQuery.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-24 w-full" />
                  <Skeleton className="h-24 w-full" />
                </div>
              ) : versionItems.length ? (
                versionItems.map((item) => (
                  <VersionRow
                    key={item.version_id}
                    item={item}
                    active={item.version_id === selectedVersionId}
                    onSelect={() => setSelectedVersionId(item.version_id)}
                  />
                ))
              ) : (
                <EmptyPanel title="当前筛选范围内暂无策略版本。" description="调整 trader、日期、状态或版本类型后重试。" />
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>所选版本与优化</CardTitle>
            <CardDescription>检查所选版本，预览候选负载，并生成候选版本。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedVersion ? (
              <EmptyPanel title="请选择一个策略版本。" description="左侧选中版本后，这里会显示详情、规则快照和候选版本生成入口。" />
            ) : (
              <>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard title="版本" value={selectedVersion.version_id} accent="text-sky-300" />
                  <MetricCard title="状态" value={selectedVersion.status} />
                  <MetricCard title="优化建议" value={selectedVersion.recommendations.length} />
                  <MetricCard title="规则快照" value={selectedVersion.rules_snapshot.length} />
                </div>

                <Tabs defaultValue="summary">
                  <TabsList>
                    <TabsTrigger value="summary">摘要</TabsTrigger>
                    <TabsTrigger value="rules">规则</TabsTrigger>
                    <TabsTrigger value="json">JSON</TabsTrigger>
                  </TabsList>
                  <TabsContent value="summary" className="space-y-4">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                        <h4 className="text-sm font-semibold text-slate-100">版本元数据</h4>
                        <dl className="mt-3 space-y-2 text-sm text-slate-300">
                          <div className="flex items-center justify-between gap-3"><dt>交易员</dt><dd>{selectedVersion.trader_id}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>日期</dt><dd>{selectedVersion.strategy_date}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>状态</dt><dd>{selectedVersion.status}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>类型</dt><dd>{selectedVersion.version_type}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>父版本</dt><dd>{selectedVersion.parent_version_id ?? '无'}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>发布于</dt><dd>{formatDate(selectedVersion.released_at)}</dd></div>
                        </dl>
                      </div>
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                        <h4 className="text-sm font-semibold text-slate-100">来源与证据</h4>
                        <dl className="mt-3 space-y-2 text-sm text-slate-300">
                          <div className="flex items-center justify-between gap-3"><dt>来源文章</dt><dd>{selectedVersion.source_article_ids.length}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>证据引用</dt><dd>{selectedVersion.evidence_refs.length}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>规则快照</dt><dd>{selectedVersion.rules_snapshot.length}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>是否有快照</dt><dd>{selectedVersion.rules_snapshot.length > 0 ? '是' : '否'}</dd></div>
                        </dl>
                      </div>
                    </div>
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <h4 className="text-sm font-semibold text-slate-100">备注</h4>
                      <p className="mt-2 text-sm leading-6 text-slate-300">{selectedVersion.notes ?? '无'}</p>
                    </div>
                  </TabsContent>
                  <TabsContent value="rules" className="space-y-4">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <h4 className="text-sm font-semibold text-slate-100">推荐建议</h4>
                      {selectedVersion.recommendations.length ? (
                        <div className="mt-3 space-y-2">
                          {selectedVersion.recommendations.map((item) => (
                            <div key={`${item.symbol}-${item.decision}`} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2 text-sm text-slate-300">
                              <div className="flex items-center justify-between gap-3">
                                <span>{item.symbol}</span>
                                <Badge variant={item.decision === 'buy' ? 'success' : item.decision === 'sell' ? 'destructive' : 'default'}>
                                  {item.decision === 'buy' ? '买入' : item.decision === 'sell' ? '卖出' : item.decision}
                                </Badge>
                              </div>
                              <p className="mt-1 text-xs text-slate-500">
                                置信度 {formatPercent(item.confidence)} · 买入价 {formatNumber(item.entry_price)} · 目标价 {formatNumber(item.target_price)} · 止损价 {formatNumber(item.stop_loss_price)}
                              </p>
                              {item.rationale ? <p className="mt-2 text-xs text-slate-400">{item.rationale}</p> : null}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-sm text-slate-400">暂无推荐。</p>
                      )}
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <h4 className="text-sm font-semibold text-slate-100">规则快照</h4>
                      {selectedVersion.rules_snapshot.length ? (
                        <div className="mt-3 space-y-2">
                          {selectedVersion.rules_snapshot.map((item, index) => (
                            <div key={`${String(item.rule_id ?? index)}`} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2 text-sm text-slate-300">
                              <div className="flex items-center justify-between gap-3">
                                <span>{String(item.rule_id ?? `rule-${index + 1}`)}</span>
                                <span className="text-xs text-slate-500">{String(item.condition ?? item.rule_text ?? '无')}</span>
                              </div>
                              <p className="mt-1 text-xs text-slate-500">{String(item.action ?? '无')}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-sm text-slate-400">当前版本没有规则快照。</p>
                      )}
                    </div>
                  </TabsContent>
                  <TabsContent value="json">
                    <VersionJsonPanel detail={selectedVersion} />
                  </TabsContent>
                </Tabs>

                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-100">候选版本生成</h4>
                      <p className="text-sm text-slate-500">使用所选版本快照作为候选基准。</p>
                    </div>
                    <Button
                      onClick={() => {
                        void candidateMutation.mutateAsync();
                      }}
                      disabled={candidateMutation.isPending}
                    >
                      {candidateMutation.isPending ? '正在生成...' : '生成候选版本'}
                    </Button>
                  </div>
                  <label className="space-y-2 text-sm text-slate-300">
                    <span>候选备注</span>
                    <Textarea
                      aria-label="Candidate notes"
                      value={candidateNotes}
                      onChange={(event) => setCandidateNotes(event.target.value)}
                      placeholder="输入候选版本备注，或留空以使用服务默认值。"
                    />
                  </label>
                  <div className="rounded-xl border border-slate-800/70 bg-slate-950/50 p-3 text-xs text-slate-400" data-testid="strategy-candidate-preview">
                    <p>调整预览: {candidateAdjustments.length}</p>
                    <p className="mt-1">推荐预览: {selectedVersion.recommendations.length}</p>
                    <p className="mt-1">父版本: {selectedVersion.version_id}</p>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-100">优化建议</h4>
                      <p className="text-sm text-slate-500">从所选规则详情中生成优化建议。</p>
                    </div>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        void adviseMutation.mutateAsync();
                      }}
                      disabled={adviseMutation.isPending}
                    >
                      {adviseMutation.isPending ? '正在分析...' : '运行优化建议'}
                    </Button>
                  </div>
                  {selectedRule ? (
                    <p className="text-sm text-slate-300" data-testid="strategy-rule-advice">
                      正在针对规则 <span className="font-medium text-slate-100">{selectedRule.rule_id}</span> 生成建议，
                      命中率 {formatPercent(selectedRule.backtest_samples > 0 ? selectedRule.backtest_hits / selectedRule.backtest_samples : null)}。
                    </p>
                  ) : (
                    <p className="text-sm text-slate-400">在右侧选择一条规则以生成优化建议。</p>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>规则池</CardTitle>
            <CardDescription>在同一工作区中过滤、检查并审核规则。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              <label className="space-y-2 text-sm text-slate-300">
                <span>审核状态</span>
                <Select aria-label="Rule status" value={ruleStatus} onChange={(event) => setRuleStatus(event.target.value)}>
                  <option value="">全部</option>
                  <option value="pending">待定 (pending)</option>
                  <option value="approved">已批准 (approved)</option>
                  <option value="rejected">已拒绝 (rejected)</option>
                </Select>
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>规则类型</span>
                <Input aria-label="Rule type" value={ruleType} onChange={(event) => setRuleType(event.target.value)} placeholder="如 breakout" />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>映射状态</span>
                <Select aria-label="Mapping status" value={mappingStatus} onChange={(event) => setMappingStatus(event.target.value)}>
                  <option value="">全部</option>
                  <option value="unmapped">未映射</option>
                  <option value="pending">待定</option>
                  <option value="mapped">已映射</option>
                  <option value="unmappable">无法映射</option>
                </Select>
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>来源类型</span>
                <Input aria-label="Source type" value={sourceType} onChange={(event) => setSourceType(event.target.value)} placeholder="如 standalone" />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>关注标的</span>
                <Input aria-label="Instrument focus" value={instrumentFocus} onChange={(event) => setInstrumentFocus(event.target.value)} placeholder="如 stock" />
              </label>
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <input
                  id="skipNoMapped"
                  type="checkbox"
                  checked={skipNoMapped}
                  onChange={(event) => setSkipNoMapped(event.target.checked)}
                />
                <label htmlFor="skipNoMapped">跳过未映射条件的规则</label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="space-y-2 text-sm text-slate-300">
                  <span>跳过 (Skip)</span>
                  <Input aria-label="Rule skip" type="number" min={0} value={ruleSkip} onChange={(event) => setRuleSkip(Number(event.target.value || 0))} />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span>限制 (Limit)</span>
                  <Input aria-label="Rule limit" type="number" min={1} max={100} value={ruleLimit} onChange={(event) => setRuleLimit(Number(event.target.value || 0))} />
                </label>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setRuleSkip(0)}>
                  重置页码
                </Button>
                <Button variant="outline" size="sm" onClick={() => void rulesQuery.refetch()}>
                  重新加载
                </Button>
              </div>
            </div>

            <div className="space-y-3">
              {rulesQuery.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-24 w-full" />
                  <Skeleton className="h-24 w-full" />
                </div>
              ) : ruleItems.length ? (
                ruleItems.map((item) => (
                  <RuleRow
                    key={item.rule_id}
                    item={item}
                    active={item.rule_id === selectedRuleId}
                    onSelect={() => setSelectedRuleId(item.rule_id)}
                  />
                ))
              ) : (
                <EmptyPanel title="当前筛选范围内暂无规则。" description="调整 review status、mapping status 或 rule type 后重试。" />
              )}
            </div>

            {!selectedRule ? (
              <EmptyPanel title="请选择一条规则。" description="选中规则后可以查看详情、发起审核和生成优化建议。" />
            ) : (
              <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-100">所选规则</h4>
                    <p className="text-sm text-slate-500">{selectedRule.rule_id}</p>
                  </div>
                  <div className="flex gap-2">
                    <StatusBadge value={selectedRule.review_status} />
                    <Badge variant={selectedRule.mapping_status === 'mapped' ? 'info' : 'default'}>
                      {selectedRule.mapping_status === 'mapped' ? '已映射' : selectedRule.mapping_status}
                    </Badge>
                  </div>
                </div>

                <dl className="grid gap-2 text-sm text-slate-300">
                  <div className="flex items-center justify-between gap-3"><dt>来源</dt><dd>{selectedRule.source_type}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>类型</dt><dd>{selectedRule.rule_type}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>关注标的</dt><dd>{selectedRule.instrument_focus}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>置信度</dt><dd>{formatNumber(selectedRule.validated_confidence ?? selectedRule.initial_confidence, 3)}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>回测命中</dt><dd>{selectedRule.backtest_hits} / {selectedRule.backtest_samples}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>创建时间</dt><dd>{formatDate(selectedRule.created_at)}</dd></div>
                </dl>

                <Tabs defaultValue="detail">
                  <TabsList>
                    <TabsTrigger value="detail">详情</TabsTrigger>
                    <TabsTrigger value="json">JSON</TabsTrigger>
                  </TabsList>
                  <TabsContent value="detail" className="space-y-4">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                      <h5 className="text-sm font-semibold text-slate-100">映射条件</h5>
                      <p className="mt-2 text-sm text-slate-300" data-testid="strategy-rule-mapped-condition">
                        {(selectedRule.extraction_layer['mapped_condition'] as Record<string, unknown> | null | undefined)
                          ? JSON.stringify(selectedRule.extraction_layer['mapped_condition'])
                          : '无映射条件'}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                      <h5 className="text-sm font-semibold text-slate-100">回测结果</h5>
                      <p className="mt-2 text-sm text-slate-300">
                        命中 {selectedRule.backtest_hits}, 未命中 {selectedRule.backtest_misses}, 总样本 {selectedRule.backtest_samples}。
                      </p>
                    </div>
                  </TabsContent>
                  <TabsContent value="json">
                    <RuleJsonPanel detail={selectedRule} />
                  </TabsContent>
                </Tabs>

                <div className="space-y-3 rounded-2xl border border-slate-800/80 bg-slate-950/50 p-4">
                  <h5 className="text-sm font-semibold text-slate-100">单条审核</h5>
                  <div className="grid gap-3">
                    <Select aria-label="Review decision" value={reviewDecision} onChange={(event) => setReviewDecision(event.target.value as 'approve' | 'reject' | 'pending')}>
                      <option value="approve">批准 (approve)</option>
                      <option value="reject">拒绝 (reject)</option>
                      <option value="pending">待定 (pending)</option>
                    </Select>
                    <Input aria-label="Reviewed by" value={reviewedBy} onChange={(event) => setReviewedBy(event.target.value)} />
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input type="checkbox" checked={reviewForce} onChange={(event) => setReviewForce(event.target.checked)} />
                      强制重写
                    </label>
                    <Button
                      onClick={() => {
                        void reviewRuleMutation.mutateAsync();
                      }}
                      disabled={reviewRuleMutation.isPending}
                    >
                      {reviewRuleMutation.isPending ? '正在提交...' : '提交审核'}
                    </Button>
                  </div>
                </div>

                <div className="space-y-3 rounded-2xl border border-slate-800/80 bg-slate-950/50 p-4">
                  <h5 className="text-sm font-semibold text-slate-100">批量审核</h5>
                  <div className="grid gap-3">
                    <Select aria-label="Batch decision" value={batchDecision} onChange={(event) => setBatchDecision(event.target.value as 'approve' | 'reject' | 'pending')}>
                      <option value="approve">全部批准 (approve)</option>
                      <option value="reject">全部拒绝 (reject)</option>
                      <option value="pending">全部设为待定 (pending)</option>
                    </Select>
                    <Select aria-label="Batch status" value={batchStatus} onChange={(event) => setBatchStatus(event.target.value as 'pending' | 'approved' | 'rejected')}>
                      <option value="pending">针对：待定 (pending)</option>
                      <option value="approved">针对：已批准 (approved)</option>
                      <option value="rejected">针对：已拒绝 (rejected)</option>
                    </Select>
                    <Input aria-label="Batch limit" type="number" min={1} max={100} value={batchLimit} onChange={(event) => setBatchLimit(Number(event.target.value || 0))} />
                    <Input aria-label="Batch reviewed by" value={batchReviewedBy} onChange={(event) => setBatchReviewedBy(event.target.value)} />
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input type="checkbox" checked={batchForce} onChange={(event) => setBatchForce(event.target.checked)} />
                      强制重写
                    </label>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        void reviewBatchMutation.mutateAsync();
                      }}
                      disabled={reviewBatchMutation.isPending}
                    >
                      {reviewBatchMutation.isPending ? '正在批量处理...' : '运行批量审核'}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
