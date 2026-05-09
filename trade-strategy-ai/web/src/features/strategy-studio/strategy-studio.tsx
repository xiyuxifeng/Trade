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
  return <Badge variant={variant}>{value}</Badge>;
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
          <Badge variant={item.version_type === 'candidate' ? 'info' : 'default'}>{item.version_type}</Badge>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded-full border border-slate-800/80 px-2 py-1">recommendations {item.recommendations_count}</span>
        <span className="rounded-full border border-slate-800/80 px-2 py-1">rules snapshot {item.has_rules_snapshot ? 'yes' : 'no'}</span>
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
            {item.review_status}
          </Badge>
          <Badge variant={item.mapping_status === 'mapped' ? 'info' : 'default'}>{item.mapping_status}</Badge>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded-full border border-slate-800/80 px-2 py-1">confidence {formatNumber(item.validated_confidence ?? item.initial_confidence, 3)}</span>
        <span className="rounded-full border border-slate-800/80 px-2 py-1">hits {item.backtest_hits}</span>
        <span className="rounded-full border border-slate-800/80 px-2 py-1">samples {item.backtest_samples}</span>
      </div>
    </button>
  );
}

function VersionJsonPanel({ detail }: { detail: StrategyVersionDetailItem }) {
  return (
    <pre className="max-h-[30rem] overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200">
      {JSON.stringify(detail, null, 2)}
    </pre>
  );
}

function RuleJsonPanel({ detail }: { detail: RuleDetailItem }) {
  return (
    <pre className="max-h-[26rem] overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200">
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
        kicker="Strategy Studio"
        title="Strategy Studio"
        description="Browse strategy versions, generate candidate versions, and review the rule pool in one dense workspace."
        actionLabel="Refresh all"
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
        <MetricCard title="Versions" value={summary.totalVersions} accent="text-sky-300" />
        <MetricCard title="Candidate" value={summary.candidateVersions} />
        <MetricCard title="Rules" value={summary.totalRules} />
        <MetricCard title="Approved / Pending" value={`${summary.approvedRules} / ${summary.pendingRules}`} accent="text-emerald-300" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)_400px]">
        <Card>
          <CardHeader>
            <CardTitle>Strategy Versions</CardTitle>
            <CardDescription>Filter by trader, date, version status, and version type.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              <label className="space-y-2 text-sm text-slate-300">
                <span>Trader ID</span>
                <Input aria-label="Trader ID" value={traderId} onChange={(event) => setTraderId(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>Strategy date</span>
                <Input aria-label="Strategy date" type="date" value={strategyDate} onChange={(event) => setStrategyDate(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>Status</span>
                <Select aria-label="Version status" value={versionStatus} onChange={(event) => setVersionStatus(event.target.value)}>
                  <option value="">All</option>
                  <option value="draft">draft</option>
                  <option value="released">released</option>
                  <option value="archived">archived</option>
                </Select>
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>Version type</span>
                <Select aria-label="Version type" value={versionType} onChange={(event) => setVersionType(event.target.value)}>
                  <option value="">All</option>
                  <option value="manual">manual</option>
                  <option value="candidate">candidate</option>
                </Select>
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="space-y-2 text-sm text-slate-300">
                  <span>Skip</span>
                  <Input aria-label="Version skip" type="number" min={0} value={versionSkip} onChange={(event) => setVersionSkip(Number(event.target.value || 0))} />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span>Limit</span>
                  <Input aria-label="Version limit" type="number" min={1} max={100} value={versionLimit} onChange={(event) => setVersionLimit(Number(event.target.value || 0))} />
                </label>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setVersionSkip(0)}>
                  Reset page
                </Button>
                <Button variant="outline" size="sm" onClick={() => void versionsQuery.refetch()}>
                  Reload
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
            <CardTitle>Selected Version and Optimization</CardTitle>
            <CardDescription>Inspect the selected version, preview the candidate payload, and generate a candidate version.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedVersion ? (
              <EmptyPanel title="请选择一个策略版本。" description="左侧选中版本后，这里会显示详情、规则快照和候选版本生成入口。" />
            ) : (
              <>
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard title="Version" value={selectedVersion.version_id} accent="text-sky-300" />
                  <MetricCard title="Status" value={selectedVersion.status} />
                  <MetricCard title="Recommendations" value={selectedVersion.recommendations.length} />
                  <MetricCard title="Rules snapshot" value={selectedVersion.rules_snapshot.length} />
                </div>

                <Tabs defaultValue="summary">
                  <TabsList>
                    <TabsTrigger value="summary">Summary</TabsTrigger>
                    <TabsTrigger value="rules">Rules</TabsTrigger>
                    <TabsTrigger value="json">JSON</TabsTrigger>
                  </TabsList>
                  <TabsContent value="summary" className="space-y-4">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                        <h4 className="text-sm font-semibold text-slate-100">Version metadata</h4>
                        <dl className="mt-3 space-y-2 text-sm text-slate-300">
                          <div className="flex items-center justify-between gap-3"><dt>Trader</dt><dd>{selectedVersion.trader_id}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>Date</dt><dd>{selectedVersion.strategy_date}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>Status</dt><dd>{selectedVersion.status}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>Type</dt><dd>{selectedVersion.version_type}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>Parent</dt><dd>{selectedVersion.parent_version_id ?? 'n/a'}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>Released at</dt><dd>{formatDate(selectedVersion.released_at)}</dd></div>
                        </dl>
                      </div>
                      <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                        <h4 className="text-sm font-semibold text-slate-100">Source and evidence</h4>
                        <dl className="mt-3 space-y-2 text-sm text-slate-300">
                          <div className="flex items-center justify-between gap-3"><dt>Source articles</dt><dd>{selectedVersion.source_article_ids.length}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>Evidence refs</dt><dd>{selectedVersion.evidence_refs.length}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>Rules snapshot</dt><dd>{selectedVersion.rules_snapshot.length}</dd></div>
                          <div className="flex items-center justify-between gap-3"><dt>Has snapshot</dt><dd>{selectedVersion.rules_snapshot.length > 0 ? 'yes' : 'no'}</dd></div>
                        </dl>
                      </div>
                    </div>
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <h4 className="text-sm font-semibold text-slate-100">Notes</h4>
                      <p className="mt-2 text-sm leading-6 text-slate-300">{selectedVersion.notes ?? 'n/a'}</p>
                    </div>
                  </TabsContent>
                  <TabsContent value="rules" className="space-y-4">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <h4 className="text-sm font-semibold text-slate-100">Recommendations</h4>
                      {selectedVersion.recommendations.length ? (
                        <div className="mt-3 space-y-2">
                          {selectedVersion.recommendations.map((item) => (
                            <div key={`${item.symbol}-${item.decision}`} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2 text-sm text-slate-300">
                              <div className="flex items-center justify-between gap-3">
                                <span>{item.symbol}</span>
                                <Badge variant={item.decision === 'buy' ? 'success' : item.decision === 'sell' ? 'destructive' : 'default'}>{item.decision}</Badge>
                              </div>
                              <p className="mt-1 text-xs text-slate-500">
                                confidence {formatPercent(item.confidence)} · entry {formatNumber(item.entry_price)} · target {formatNumber(item.target_price)} · stop {formatNumber(item.stop_loss_price)}
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
                      <h4 className="text-sm font-semibold text-slate-100">Rules snapshot</h4>
                      {selectedVersion.rules_snapshot.length ? (
                        <div className="mt-3 space-y-2">
                          {selectedVersion.rules_snapshot.map((item, index) => (
                            <div key={`${String(item.rule_id ?? index)}`} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2 text-sm text-slate-300">
                              <div className="flex items-center justify-between gap-3">
                                <span>{String(item.rule_id ?? `rule-${index + 1}`)}</span>
                                <span className="text-xs text-slate-500">{String(item.condition ?? item.rule_text ?? 'n/a')}</span>
                              </div>
                              <p className="mt-1 text-xs text-slate-500">{String(item.action ?? 'n/a')}</p>
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
                      <h4 className="text-sm font-semibold text-slate-100">Candidate generation</h4>
                      <p className="text-sm text-slate-500">Use the selected version snapshot as the candidate baseline.</p>
                    </div>
                    <Button
                      onClick={() => {
                        void candidateMutation.mutateAsync();
                      }}
                      disabled={candidateMutation.isPending}
                    >
                      {candidateMutation.isPending ? 'Generating...' : 'Generate candidate'}
                    </Button>
                  </div>
                  <label className="space-y-2 text-sm text-slate-300">
                    <span>Candidate notes</span>
                    <Textarea
                      aria-label="Candidate notes"
                      value={candidateNotes}
                      onChange={(event) => setCandidateNotes(event.target.value)}
                      placeholder="Enter candidate notes or leave blank to use the service default."
                    />
                  </label>
                  <div className="rounded-xl border border-slate-800/70 bg-slate-950/50 p-3 text-xs text-slate-400">
                    <p>Adjustments preview: {candidateAdjustments.length}</p>
                    <p className="mt-1">Recommendations preview: {selectedVersion.recommendations.length}</p>
                    <p className="mt-1">Parent version: {selectedVersion.version_id}</p>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-100">Validation advice</h4>
                      <p className="text-sm text-slate-500">Generate optimization advice from the selected rule detail.</p>
                    </div>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        void adviseMutation.mutateAsync();
                      }}
                      disabled={adviseMutation.isPending}
                    >
                      {adviseMutation.isPending ? 'Analyzing...' : 'Run advice'}
                    </Button>
                  </div>
                  {selectedRule ? (
                    <p className="text-sm text-slate-300">
                      Using rule <span className="font-medium text-slate-100">{selectedRule.rule_id}</span> with
                      {` `}hit rate {formatPercent(selectedRule.backtest_samples > 0 ? selectedRule.backtest_hits / selectedRule.backtest_samples : null)}.
                    </p>
                  ) : (
                    <p className="text-sm text-slate-400">Select a rule on the right to build advice.</p>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Rule Pool</CardTitle>
            <CardDescription>Filter, inspect, and review rules from the same workspace.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3">
              <label className="space-y-2 text-sm text-slate-300">
                <span>Review status</span>
                <Select aria-label="Rule status" value={ruleStatus} onChange={(event) => setRuleStatus(event.target.value)}>
                  <option value="">All</option>
                  <option value="pending">pending</option>
                  <option value="approved">approved</option>
                  <option value="rejected">rejected</option>
                </Select>
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>Rule type</span>
                <Input aria-label="Rule type" value={ruleType} onChange={(event) => setRuleType(event.target.value)} placeholder="breakout" />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>Mapping status</span>
                <Select aria-label="Mapping status" value={mappingStatus} onChange={(event) => setMappingStatus(event.target.value)}>
                  <option value="">All</option>
                  <option value="unmapped">unmapped</option>
                  <option value="pending">pending</option>
                  <option value="mapped">mapped</option>
                  <option value="unmappable">unmappable</option>
                </Select>
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>Source type</span>
                <Input aria-label="Source type" value={sourceType} onChange={(event) => setSourceType(event.target.value)} placeholder="standalone" />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span>Instrument focus</span>
                <Input aria-label="Instrument focus" value={instrumentFocus} onChange={(event) => setInstrumentFocus(event.target.value)} placeholder="stock" />
              </label>
              <div className="flex items-center gap-2 text-sm text-slate-300">
                <input
                  id="skipNoMapped"
                  type="checkbox"
                  checked={skipNoMapped}
                  onChange={(event) => setSkipNoMapped(event.target.checked)}
                />
                <label htmlFor="skipNoMapped">Skip rules without mapped condition</label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="space-y-2 text-sm text-slate-300">
                  <span>Skip</span>
                  <Input aria-label="Rule skip" type="number" min={0} value={ruleSkip} onChange={(event) => setRuleSkip(Number(event.target.value || 0))} />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span>Limit</span>
                  <Input aria-label="Rule limit" type="number" min={1} max={100} value={ruleLimit} onChange={(event) => setRuleLimit(Number(event.target.value || 0))} />
                </label>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" size="sm" onClick={() => setRuleSkip(0)}>
                  Reset page
                </Button>
                <Button variant="outline" size="sm" onClick={() => void rulesQuery.refetch()}>
                  Reload
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
                    <h4 className="text-sm font-semibold text-slate-100">Selected rule</h4>
                    <p className="text-sm text-slate-500">{selectedRule.rule_id}</p>
                  </div>
                  <div className="flex gap-2">
                    <StatusBadge value={selectedRule.review_status} />
                    <Badge variant={selectedRule.mapping_status === 'mapped' ? 'info' : 'default'}>{selectedRule.mapping_status}</Badge>
                  </div>
                </div>

                <dl className="grid gap-2 text-sm text-slate-300">
                  <div className="flex items-center justify-between gap-3"><dt>Source</dt><dd>{selectedRule.source_type}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>Type</dt><dd>{selectedRule.rule_type}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>Focus</dt><dd>{selectedRule.instrument_focus}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>Confidence</dt><dd>{formatNumber(selectedRule.validated_confidence ?? selectedRule.initial_confidence, 3)}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>Backtest hits</dt><dd>{selectedRule.backtest_hits} / {selectedRule.backtest_samples}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>Created</dt><dd>{formatDate(selectedRule.created_at)}</dd></div>
                </dl>

                <Tabs defaultValue="detail">
                  <TabsList>
                    <TabsTrigger value="detail">Detail</TabsTrigger>
                    <TabsTrigger value="json">JSON</TabsTrigger>
                  </TabsList>
                  <TabsContent value="detail" className="space-y-4">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                      <h5 className="text-sm font-semibold text-slate-100">Mapped condition</h5>
                      <p className="mt-2 text-sm text-slate-300">
                        {(selectedRule.extraction_layer['mapped_condition'] as Record<string, unknown> | null | undefined)
                          ? JSON.stringify(selectedRule.extraction_layer['mapped_condition'])
                          : 'No mapped condition'}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                      <h5 className="text-sm font-semibold text-slate-100">Backtest result</h5>
                      <p className="mt-2 text-sm text-slate-300">
                        Hits {selectedRule.backtest_hits}, misses {selectedRule.backtest_misses}, samples {selectedRule.backtest_samples}.
                      </p>
                    </div>
                  </TabsContent>
                  <TabsContent value="json">
                    <RuleJsonPanel detail={selectedRule} />
                  </TabsContent>
                </Tabs>

                <div className="space-y-3 rounded-2xl border border-slate-800/80 bg-slate-950/50 p-4">
                  <h5 className="text-sm font-semibold text-slate-100">Single review</h5>
                  <div className="grid gap-3">
                    <Select aria-label="Review decision" value={reviewDecision} onChange={(event) => setReviewDecision(event.target.value as 'approve' | 'reject' | 'pending')}>
                      <option value="approve">approve</option>
                      <option value="reject">reject</option>
                      <option value="pending">pending</option>
                    </Select>
                    <Input aria-label="Reviewed by" value={reviewedBy} onChange={(event) => setReviewedBy(event.target.value)} />
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input type="checkbox" checked={reviewForce} onChange={(event) => setReviewForce(event.target.checked)} />
                      Force overwrite
                    </label>
                    <Button
                      onClick={() => {
                        void reviewRuleMutation.mutateAsync();
                      }}
                      disabled={reviewRuleMutation.isPending}
                    >
                      {reviewRuleMutation.isPending ? 'Submitting...' : 'Submit review'}
                    </Button>
                  </div>
                </div>

                <div className="space-y-3 rounded-2xl border border-slate-800/80 bg-slate-950/50 p-4">
                  <h5 className="text-sm font-semibold text-slate-100">Batch review</h5>
                  <div className="grid gap-3">
                    <Select aria-label="Batch decision" value={batchDecision} onChange={(event) => setBatchDecision(event.target.value as 'approve' | 'reject' | 'pending')}>
                      <option value="approve">approve</option>
                      <option value="reject">reject</option>
                      <option value="pending">pending</option>
                    </Select>
                    <Select aria-label="Batch status" value={batchStatus} onChange={(event) => setBatchStatus(event.target.value as 'pending' | 'approved' | 'rejected')}>
                      <option value="pending">pending</option>
                      <option value="approved">approved</option>
                      <option value="rejected">rejected</option>
                    </Select>
                    <Input aria-label="Batch limit" type="number" min={1} max={100} value={batchLimit} onChange={(event) => setBatchLimit(Number(event.target.value || 0))} />
                    <Input aria-label="Batch reviewed by" value={batchReviewedBy} onChange={(event) => setBatchReviewedBy(event.target.value)} />
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input type="checkbox" checked={batchForce} onChange={(event) => setBatchForce(event.target.checked)} />
                      Force overwrite
                    </label>
                    <Button
                      variant="secondary"
                      onClick={() => {
                        void reviewBatchMutation.mutateAsync();
                      }}
                      disabled={reviewBatchMutation.isPending}
                    >
                      {reviewBatchMutation.isPending ? 'Submitting...' : 'Batch review'}
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
