import { useMemo, useState } from 'react';

import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { ApiError } from '@/lib/api/http';
import {
  acceptStrategyRevisionProposalToDraft,
  compareStrategyVersion,
  createStrategyDraft,
  diffStrategyVersion,
  getStrategyRevisionProposal,
  getStrategyDraftOptions,
  listStrategies,
  listStrategyRevisionProposals,
  publishStrategy,
  rollbackStrategyVersion,
  reviewStrategyRevisionProposal,
  submitStrategyReview,
  validateStrategyVersion,
} from '@/lib/api/strategies';
import type {
  StrategyComparisonResponse,
  StrategyDiffResponse,
  StrategyRevisionProposal,
  StrategyVersion,
} from '@/types/strategies';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

type FormalPageProps = {
  availability?: PageAvailability;
};

export function StrategyOverviewPage({ availability }: FormalPageProps = {}) {
  const [businessKey, setBusinessKey] = useState('');
  const [title, setTitle] = useState('');
  const [summary, setSummary] = useState('');
  const [selectedRuleVersionId, setSelectedRuleVersionId] = useState('');
  const [selectedMethodProfileId, setSelectedMethodProfileId] = useState('');
  const [selectedRuleProfileId, setSelectedRuleProfileId] = useState('');
  const [selectedValidatedProfileId, setSelectedValidatedProfileId] = useState('');
  const [selectedDatasetSnapshotId, setSelectedDatasetSnapshotId] = useState('');
  const [selectedMarketSnapshotId, setSelectedMarketSnapshotId] = useState('');
  const [selectedApplicabilityProfileId, setSelectedApplicabilityProfileId] = useState('');
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [selectedProposalId, setSelectedProposalId] = useState<string | null>(null);
  const [localVersion, setLocalVersion] = useState<StrategyVersion | null>(null);
  const [comparison, setComparison] = useState<StrategyComparisonResponse | null>(null);
  const [diff, setDiff] = useState<StrategyDiffResponse | null>(null);
  const [rollbackReason, setRollbackReason] = useState('');
  const [proposalReviewReason, setProposalReviewReason] = useState('');
  const [proposalDraftReason, setProposalDraftReason] = useState('');
  const [riskPolicyText, setRiskPolicyText] = useState(
    JSON.stringify({ position_constraints: { single_position_pct: 0.2, total_position_pct: 0.8 } }, null, 2),
  );
  const [selectionPolicyText, setSelectionPolicyText] = useState(
    JSON.stringify(
      {
        market_state_selection_policy: { preferred_states: ['强势上行'] },
        degradation_policy: { missing_canonical_data: 'unavailable' },
      },
      null,
      2,
    ),
  );
  const [universeText, setUniverseText] = useState(JSON.stringify({ market: 'CN', boards: ['主板'] }, null, 2));
  const queryClient = useQueryClient();

  const strategiesQuery = useQuery({
    queryKey: ['formal-strategies'],
    queryFn: () => listStrategies(),
    enabled: availability === undefined,
  });
  const optionsQuery = useQuery({
    queryKey: ['formal-strategy-draft-options'],
    queryFn: () => getStrategyDraftOptions(),
    enabled: availability === undefined,
  });
  const proposalsQuery = useQuery({
    queryKey: ['formal-strategy-proposals'],
    queryFn: () => listStrategyRevisionProposals(),
    enabled: availability === undefined,
  });

  const proposalItems = proposalsQuery.data?.items ?? [];
  const activeProposalId = selectedProposalId ?? proposalItems[0]?.proposal_id ?? null;
  const activeProposalFromList = proposalItems.find((item) => item.proposal_id === activeProposalId) ?? null;
  const proposalDetailQuery = useQuery({
    queryKey: ['formal-strategy-proposal', activeProposalId],
    queryFn: () => getStrategyRevisionProposal(activeProposalId ?? ''),
    enabled: availability === undefined && activeProposalId !== null,
  });
  const activeProposal: StrategyRevisionProposal | null = proposalDetailQuery.data ?? activeProposalFromList;

  const saveDraft = useMutation({
    mutationFn: (draft: Parameters<typeof createStrategyDraft>[0]) => createStrategyDraft(draft),
    onSuccess: (data) => {
      setLocalVersion(data);
      setSelectedVersionId(data.strategy_version_id);
      setStatusMessage('已保存策略草稿');
    },
    onError: (error) => {
      setStatusMessage(resolveErrorMessage(error));
    },
  });
  const submitReview = useMutation({
    mutationFn: (versionId: string) => submitStrategyReview(versionId, { reason: '提交策略审核' }),
    onSuccess: (data) => {
      setLocalVersion((current) => (current ? { ...current, lifecycle_state: data.lifecycle_state, lifecycle_label: '待审核', review_status: 'pending_review', status_state: 'pending_review' } : current));
      setStatusMessage('已提交审核');
    },
    onError: (error) => setStatusMessage(resolveErrorMessage(error)),
  });
  const publish = useMutation({
    mutationFn: (versionId: string) => publishStrategy(versionId, { reason: '发布正式策略' }),
    onSuccess: (data) => {
      setLocalVersion((current) =>
        current
          ? {
              ...current,
              lifecycle_state: data.lifecycle_state,
              lifecycle_label: '已发布',
              review_status: 'published',
              status_state: 'published',
              current_status: { is_current: true, current_version_id: current.strategy_version_id, previous_current_version_id: current.current_status.current_version_id ?? null },
            }
          : current,
      );
      setStatusMessage('已发布为当前策略');
    },
    onError: (error) => setStatusMessage(resolveErrorMessage(error)),
  });
  const validate = useMutation({
    mutationFn: (versionId: string) => validateStrategyVersion(versionId, { reason: '校验正式策略' }),
    onSuccess: async (data) => {
      setLocalVersion(data);
      setStatusMessage(data.validation.label);
      const [comparisonData, diffData] = await Promise.all([
        compareStrategyVersion(data.strategy_version_id),
        diffStrategyVersion(data.strategy_version_id),
      ]);
      setComparison(comparisonData);
      setDiff(diffData);
    },
    onError: (error) => setStatusMessage(resolveErrorMessage(error)),
  });
  const rollback = useMutation({
    mutationFn: (params: { versionId: string; reason: string }) => rollbackStrategyVersion(params.versionId, { reason: params.reason }),
    onSuccess: (data) => {
      setLocalVersion(data);
      setSelectedVersionId(data.strategy_version_id);
      setStatusMessage('已回退到所选正式版本');
    },
    onError: (error) => setStatusMessage(resolveErrorMessage(error)),
  });
  const reviewProposal = useMutation({
    mutationFn: (params: {
      proposalId: string;
      action: 'start_review' | 'return_to_draft' | 'reject' | 'archive' | 'supersede';
      reason?: string | null;
    }) => reviewStrategyRevisionProposal(params.proposalId, { action: params.action, reason: params.reason }),
    onSuccess: async (data) => {
      setStatusMessage('已更新策略优化建议复核状态');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['formal-strategy-proposals'] }),
        queryClient.invalidateQueries({ queryKey: ['formal-strategy-proposal', data.proposal_id] }),
      ]);
    },
    onError: (error) => setStatusMessage(resolveErrorMessage(error)),
  });
  const acceptProposal = useMutation({
    mutationFn: (params: { proposalId: string; reason?: string | null }) =>
      acceptStrategyRevisionProposalToDraft(params.proposalId, { reason: params.reason }),
    onSuccess: async (data) => {
      setStatusMessage('已生成策略草稿');
      setSelectedProposalId(data.proposal_id);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['formal-strategies'] }),
        queryClient.invalidateQueries({ queryKey: ['formal-strategy-proposals'] }),
        queryClient.invalidateQueries({ queryKey: ['formal-strategy-proposal', data.proposal_id] }),
      ]);
      if (data.accepted_draft_version_id) {
        const refreshed = await queryClient.fetchQuery({
          queryKey: ['formal-strategies'],
          queryFn: () => listStrategies(),
        });
        const acceptedDraft = refreshed.items.find((item) => item.strategy_version_id === data.accepted_draft_version_id);
        if (acceptedDraft) {
          setLocalVersion(acceptedDraft);
          setSelectedVersionId(acceptedDraft.strategy_version_id);
        }
      }
    },
    onError: (error) => setStatusMessage(resolveErrorMessage(error)),
  });

  const permissionDenied =
    (strategiesQuery.error instanceof ApiError && [401, 403].includes(strategiesQuery.error.status)) ||
    (optionsQuery.error instanceof ApiError && [401, 403].includes(optionsQuery.error.status)) ||
    (proposalsQuery.error instanceof ApiError && [401, 403].includes(proposalsQuery.error.status)) ||
    (proposalDetailQuery.error instanceof ApiError && [401, 403].includes(proposalDetailQuery.error.status));
  const unavailable =
    (strategiesQuery.error instanceof ApiError && strategiesQuery.error.status >= 500) ||
    (optionsQuery.error instanceof ApiError && optionsQuery.error.status >= 500) ||
    (proposalsQuery.error instanceof ApiError && proposalsQuery.error.status >= 500) ||
    (proposalDetailQuery.error instanceof ApiError && proposalDetailQuery.error.status >= 500);
  const state: PageAvailability =
    availability ??
    (strategiesQuery.isLoading || optionsQuery.isLoading || proposalsQuery.isLoading
      ? 'loading'
      : permissionDenied
        ? 'permission_denied'
        : unavailable
          ? 'unavailable'
          : strategiesQuery.error || optionsQuery.error || proposalsQuery.error || proposalDetailQuery.error
            ? 'error'
            : strategiesQuery.data?.state === 'empty' && proposalsQuery.data?.state === 'empty'
              ? 'empty'
              : strategiesQuery.data?.state === 'partial' || proposalsQuery.data?.state === 'partial'
                ? 'partial'
                : 'ready');

  const versions = useMemo(() => {
    const items = [...(strategiesQuery.data?.items ?? [])];
    if (localVersion) {
      const index = items.findIndex((item) => item.strategy_version_id === localVersion.strategy_version_id);
      if (index >= 0) {
        items[index] = localVersion;
      } else {
        items.unshift(localVersion);
      }
    }
    return items;
  }, [localVersion, strategiesQuery.data?.items]);

  const activeVersion =
    versions.find((item) => item.strategy_version_id === selectedVersionId) ??
    localVersion ??
    versions.find((item) => item.current_status.is_current) ??
    versions[0] ??
    null;
  const selectedProposal = activeProposal;
  const rollbackTargetVersionId =
    comparison?.current_version?.strategy_version_id && comparison.current_version.strategy_version_id !== activeVersion?.strategy_version_id
      ? comparison.current_version.strategy_version_id
      : null;

  const handleSaveDraft = () => {
    try {
      setStatusMessage(null);
      const riskPolicyJson = JSON.parse(riskPolicyText);
      const selectionPolicyJson = JSON.parse(selectionPolicyText);
      const universeJson = JSON.parse(universeText);
      saveDraft.mutate({
        business_key: businessKey,
        schema_version: 'strategy-schema-v1',
        title,
        summary,
        rule_memberships: [
          {
            rule_version_id: selectedRuleVersionId,
            base_weight: 0.65,
            status: 'active',
            configuration_json: { position_role: 'core' },
          },
        ],
        author_method_profile_version_id: selectedMethodProfileId,
        author_rule_profile_version_id: selectedRuleProfileId,
        author_validated_profile_version_id: selectedValidatedProfileId,
        risk_policy_json: riskPolicyJson,
        selection_policy_json: selectionPolicyJson,
        universe_json: universeJson,
        evidence_json: {
          dataset_snapshot_id: selectedDatasetSnapshotId,
          market_snapshot_ids: selectedMarketSnapshotId ? [selectedMarketSnapshotId] : [],
          rule_applicability_profile_ids: selectedApplicabilityProfileId ? [selectedApplicabilityProfileId] : [],
          backtest_run_ids: [],
          backtest_result_ids: [],
        },
      });
    } catch {
      setStatusMessage('策略参数 JSON 解析失败，请修正后再保存。');
    }
  };

  return (
    <ProductPageAdapter
      title="策略中心"
      queryState={state}
      purpose="组合正式规则、作者画像和风险约束，形成可追溯的正式策略版本。"
      inputDescription="输入包括正式规则、作者画像、数据集快照、市场快照和规则适用性画像。"
      processingDescription="系统保存正式策略草稿，记录版本、证据指纹、审核状态和当前策略指针。"
      outputDescription="输出是可审核、可发布、可追溯的正式策略版本，不会把每日结果直接覆盖成正式策略。"
      businessAction={{ label: '查看每日盘前', to: '/daily/pre-market' }}
      stateTitle={state === 'empty' ? '暂无正式策略版本' : undefined}
      stateDescription={state === 'empty' ? '当前还没有正式策略版本；请先保存策略草稿，再提交审核和发布。' : undefined}
      impact={state === 'empty' ? '盘前和盘后只能显示策略入口，不能引用不存在的正式策略版本。' : undefined}
      result={
        availability ? undefined : (
          <div className="grid gap-4">
            <section className="grid gap-3 rounded-lg border border-slate-200 bg-white px-4 py-4">
              <h2 className="m-0 text-base font-semibold text-slate-950">当前正式策略</h2>
              {activeVersion ? (
                <article className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="m-0 text-sm font-medium text-slate-950">{activeVersion.title}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        {activeVersion.business_key} · v{activeVersion.version_no} · {activeVersion.lifecycle_label}
                      </p>
                    </div>
                    <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                      {activeVersion.current_status.is_current ? '当前正式策略' : '历史版本'}
                    </span>
                  </div>
                  <div className="grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                    <InfoRow label="规则池" value={activeVersion.rule_pool.map((item) => item.title ?? item.rule_version_id).join('、') || '未绑定'} />
                    <InfoRow label="作者方法画像" value={activeVersion.profiles.author_method_profile_version_id ?? '未绑定'} />
                    <InfoRow label="作者规则画像" value={activeVersion.profiles.author_rule_profile_version_id ?? '未绑定'} />
                    <InfoRow label="作者验证画像" value={activeVersion.profiles.author_validated_profile_version_id ?? '未绑定'} />
                    <InfoRow label="数据集快照" value={activeVersion.evidence.dataset_snapshot_id ?? '未绑定'} />
                    <InfoRow label="市场快照" value={activeVersion.evidence.market_snapshot_ids.join('、') || '未绑定'} />
                  </div>
                  {versions.length > 1 ? (
                    <div className="grid gap-2">
                      <p className="m-0 text-xs font-medium text-slate-500">选择要查看的版本</p>
                      <div className="flex flex-wrap gap-2">
                        {versions.map((version) => (
                          <button
                            key={version.strategy_version_id}
                            type="button"
                            className={`rounded-full px-3 py-1 text-xs font-medium ${
                              version.strategy_version_id === activeVersion.strategy_version_id
                                ? 'bg-slate-900 text-white'
                                : 'border border-slate-200 bg-white text-slate-700'
                            }`}
                            onClick={() => setSelectedVersionId(version.strategy_version_id)}
                          >
                            v{version.version_no} {version.lifecycle_label}
                          </button>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </article>
              ) : (
                <p className="m-0 text-sm text-slate-600">当前还没有正式策略版本。</p>
              )}
            </section>

            <section className="grid gap-3 rounded-lg border border-slate-200 bg-white px-4 py-4">
              <h2 className="m-0 text-base font-semibold text-slate-950">保存策略草稿</h2>
              <div className="grid gap-3 md:grid-cols-2">
                <LabeledInput label="策略标识" value={businessKey} onChange={setBusinessKey} />
                <LabeledInput label="策略名称" value={title} onChange={setTitle} />
                <LabeledTextarea label="策略摘要" value={summary} onChange={setSummary} className="md:col-span-2" />
                <LabeledSelect label="正式规则" value={selectedRuleVersionId} onChange={setSelectedRuleVersionId} options={optionsQuery.data?.rule_options.map((item) => ({ value: item.rule_version_id, label: item.title })) ?? []} />
                <LabeledSelect label="作者方法画像" value={selectedMethodProfileId} onChange={setSelectedMethodProfileId} options={optionsQuery.data?.author_profile_options.method.map((item) => ({ value: item.author_profile_version_id, label: item.label })) ?? []} />
                <LabeledSelect label="作者规则画像" value={selectedRuleProfileId} onChange={setSelectedRuleProfileId} options={optionsQuery.data?.author_profile_options.rule.map((item) => ({ value: item.author_profile_version_id, label: item.label })) ?? []} />
                <LabeledSelect label="作者验证画像" value={selectedValidatedProfileId} onChange={setSelectedValidatedProfileId} options={optionsQuery.data?.author_profile_options.validated.map((item) => ({ value: item.author_profile_version_id, label: item.label })) ?? []} />
                <LabeledSelect label="数据集快照" value={selectedDatasetSnapshotId} onChange={setSelectedDatasetSnapshotId} options={optionsQuery.data?.dataset_options.map((item) => ({ value: item.dataset_snapshot_id, label: item.label })) ?? []} />
                <LabeledSelect label="市场快照" value={selectedMarketSnapshotId} onChange={setSelectedMarketSnapshotId} options={optionsQuery.data?.market_snapshot_options.map((item) => ({ value: item.market_snapshot_id, label: item.label })) ?? []} />
                <LabeledSelect label="规则适用性画像" value={selectedApplicabilityProfileId} onChange={setSelectedApplicabilityProfileId} options={optionsQuery.data?.rule_applicability_options.map((item) => ({ value: item.applicability_profile_id, label: item.label })) ?? []} />
                <LabeledTextarea label="风险政策" value={riskPolicyText} onChange={setRiskPolicyText} className="md:col-span-2" />
                <LabeledTextarea label="市场状态与降级政策" value={selectionPolicyText} onChange={setSelectionPolicyText} className="md:col-span-2" />
                <LabeledTextarea label="目标股票范围" value={universeText} onChange={setUniverseText} className="md:col-span-2" />
              </div>
              <div className="flex flex-wrap gap-3">
                <button type="button" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white" onClick={handleSaveDraft}>
                  保存策略草稿
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700"
                  onClick={() => activeVersion && submitReview.mutate(activeVersion.strategy_version_id)}
                  disabled={!activeVersion}
                >
                  提交审核
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700"
                  onClick={() => activeVersion && validate.mutate(activeVersion.strategy_version_id)}
                  disabled={!activeVersion}
                >
                  验证当前版本
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700"
                  onClick={() => activeVersion && publish.mutate(activeVersion.strategy_version_id)}
                  disabled={!activeVersion}
                >
                  发布为当前策略
                </button>
              </div>
              {activeVersion ? (
                <div className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                  <h3 className="m-0 text-sm font-semibold text-slate-950">验证结果</h3>
                  <div className="grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                    <InfoRow label="验证状态" value={activeVersion.validation.label} />
                    <InfoRow label="复核结论" value={activeVersion.validation.reviewer_decision_label} />
                    <InfoRow label="数据集快照" value={activeVersion.validation.dataset_binding.dataset_snapshot_id ?? '未绑定'} />
                    <InfoRow label="样本覆盖" value={activeVersion.validation.sample_coverage.state} />
                    <InfoRow label="样本数量" value={activeVersion.validation.sample_coverage.sample_count?.toString() ?? '未知'} />
                    <InfoRow label="样本外验证" value={activeVersion.validation.backtest.out_of_sample_state} />
                    <InfoRow label="规则覆盖率" value={`${Math.round(activeVersion.validation.rule_applicability.coverage_ratio * 100)}%`} />
                    <InfoRow label="数据质量" value={activeVersion.validation.data_quality.state} />
                  </div>
                </div>
              ) : null}
              {comparison ? (
                <div className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                  <h3 className="m-0 text-sm font-semibold text-slate-950">当前策略对比</h3>
                  <div className="grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                    <InfoRow label="当前正式版本" value={comparison.current_version?.title?.toString() ?? '暂无'} />
                    <InfoRow label="候选版本" value={comparison.candidate_version?.title?.toString() ?? '暂无'} />
                    <InfoRow label="规则权重变化" value={comparison.delta.rule_weight_changes.toString()} />
                    <InfoRow label="年化收益变化" value={formatPercentDelta(comparison.delta.annual_return_change)} />
                    <InfoRow label="最大回撤变化" value={formatPercentDelta(comparison.delta.max_drawdown_change)} />
                  </div>
                </div>
              ) : null}
              {diff ? (
                <div className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
                  <h3 className="m-0 text-sm font-semibold text-slate-950">版本差异</h3>
                  {diff.changes.length ? (
                    <ul className="m-0 grid gap-2 pl-5 text-sm text-slate-700">
                      {diff.changes.map((item) => (
                        <li key={item.field}>
                          {item.label}：{summarizeDiffValue(item.before)} {'->'} {summarizeDiffValue(item.after)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="m-0 text-sm text-slate-600">当前版本与对比基线没有发现结构差异。</p>
                  )}
                </div>
              ) : null}
              {rollbackTargetVersionId ? (
                <div className="grid gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
                  <h3 className="m-0 text-sm font-semibold text-amber-950">回退当前策略</h3>
                  <LabeledInput label="回退原因" value={rollbackReason} onChange={setRollbackReason} />
                  <div className="flex flex-wrap gap-3">
                    <button
                      type="button"
                      className="rounded-lg border border-amber-300 px-4 py-2 text-sm font-medium text-amber-900"
                      onClick={() => rollback.mutate({ versionId: rollbackTargetVersionId, reason: rollbackReason })}
                      disabled={!rollbackReason.trim()}
                    >
                      确认回退到该版本
                    </button>
                  </div>
                </div>
              ) : null}
              <section className="grid gap-4 rounded-lg border border-slate-200 bg-white px-4 py-4">
                <div className="grid gap-2">
                  <h3 className="m-0 text-base font-semibold text-slate-950">策略优化建议</h3>
                  <p className="m-0 text-sm text-slate-600">
                    这里展示正式优化建议。接受建议只会生成草稿，不会直接改写当前使用中的正式策略。
                  </p>
                </div>
                {proposalsQuery.data?.state === 'empty' ? (
                  <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    当前还没有正式的策略优化建议。
                  </div>
                ) : selectedProposal ? (
                  <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
                    <div className="grid gap-2">
                      {proposalItems.map((proposal) => {
                        const isSelected = proposal.proposal_id === selectedProposal.proposal_id;
                        return (
                          <button
                            key={proposal.proposal_id}
                            type="button"
                            className={`grid gap-2 rounded-lg border px-4 py-3 text-left transition-colors ${
                              isSelected ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-slate-50 text-slate-800'
                            }`}
                            onClick={() => setSelectedProposalId(proposal.proposal_id)}
                          >
                            <div className="flex flex-wrap items-start justify-between gap-2">
                              <div>
                                <p className="m-0 text-sm font-medium">{proposal.affected_strategy_version.title}</p>
                                <p className={`mt-1 text-xs ${isSelected ? 'text-slate-200' : 'text-slate-500'}`}>{proposal.lifecycle_label}</p>
                              </div>
                              <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${isSelected ? 'bg-white/10 text-white' : 'bg-white text-slate-600'}`}>
                                置信度 {formatConfidence(proposal.confidence)}
                              </span>
                            </div>
                            <p className={`m-0 text-xs ${isSelected ? 'text-slate-200' : 'text-slate-500'}`}>
                              影响版本：{proposal.affected_strategy_version.title}
                            </p>
                          </button>
                        );
                      })}
                    </div>

                    <article className="grid gap-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <h4 className="m-0 text-base font-semibold text-slate-950">{selectedProposal.affected_strategy_version.title}</h4>
                          <p className="mt-1 text-sm text-slate-600">
                            策略修订建议 · {selectedProposal.lifecycle_label} · {selectedProposal.evidence_label}
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                            置信度 {formatConfidence(selectedProposal.confidence)}
                          </span>
                          <span className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700">
                            {selectedProposal.lifecycle_label}
                          </span>
                        </div>
                      </div>

                      <div className="grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                        <InfoRow label="影响版本" value={renderVersionSnapshot(selectedProposal.affected_strategy_version)} />
                        <InfoRow label="基础版本" value={selectedProposal.base_version_id ?? '未记录'} />
                        <InfoRow label="建议触发" value={selectedProposal.trigger_type || '未说明'} />
                        <InfoRow label="证据状态" value={selectedProposal.evidence_label} />
                        <InfoRow label="当前使用中" value={selectedProposal.affected_strategy_version.current_status.is_current ? '是' : '否'} />
                        <InfoRow label="当前正式版本" value={selectedProposal.affected_strategy_version.current_status.current_version_id ?? '未记录'} />
                        <InfoRow label="已生成草稿" value={selectedProposal.accepted_draft_version_id ?? '尚未生成'} />
                        <InfoRow label="最近更新时间" value={selectedProposal.updated_at ?? '未记录'} />
                      </div>

                      <div className="grid gap-2 rounded-lg border border-slate-200 bg-white px-4 py-3">
                        <p className="m-0 text-sm font-medium text-slate-900">建议理由</p>
                        <p className="m-0 text-sm text-slate-700">{selectedProposal.rationale}</p>
                      </div>

                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="grid gap-2 rounded-lg border border-slate-200 bg-white px-4 py-3">
                          <p className="m-0 text-sm font-medium text-slate-900">证据</p>
                          <div className="grid gap-2 text-sm text-slate-700">
                            <InfoRow label="数据集快照" value={selectedProposal.evidence.dataset_snapshot_id ?? '未绑定'} />
                            <InfoRow label="市场快照" value={(selectedProposal.evidence.market_snapshot_ids ?? []).join('、') || '未绑定'} />
                            <InfoRow label="规则适用性画像" value={(selectedProposal.evidence.rule_applicability_profile_ids ?? []).join('、') || '未绑定'} />
                            <InfoRow label="回测记录" value={(selectedProposal.evidence.backtest_run_ids ?? []).join('、') || '未绑定'} />
                            <InfoRow label="回测结果" value={(selectedProposal.evidence.backtest_result_ids ?? []).join('、') || '未绑定'} />
                          </div>
                        </div>

                        <div className="grid gap-2 rounded-lg border border-slate-200 bg-white px-4 py-3">
                          <p className="m-0 text-sm font-medium text-slate-900">复核可用动作</p>
                          <div className="flex flex-wrap gap-2">
                            {selectedProposal.available_actions.map((action) => (
                              <span key={action} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
                                {proposalActionLabel(action)}
                              </span>
                            ))}
                          </div>
                          {selectedProposal.partial_reasons.length ? (
                            <p className="m-0 text-sm text-amber-800">部分说明：{selectedProposal.partial_reasons.join('；')}</p>
                          ) : null}
                          {selectedProposal.limitations.length ? (
                            <p className="m-0 text-sm text-slate-600">限制：{selectedProposal.limitations.join('；')}</p>
                          ) : null}
                        </div>
                      </div>

                      <div className="grid gap-2 rounded-lg border border-slate-200 bg-white px-4 py-3">
                        <p className="m-0 text-sm font-medium text-slate-900">建议变更</p>
                        {Object.keys(selectedProposal.proposed_changes).length ? (
                          <div className="grid gap-2 text-sm text-slate-700">
                            {Object.entries(selectedProposal.proposed_changes).map(([field, value]) => (
                              <InfoRow key={field} label={proposalChangeLabel(field)} value={summarizeDiffValue(value)} />
                            ))}
                          </div>
                        ) : (
                          <p className="m-0 text-sm text-slate-600">当前建议没有新增字段差异。</p>
                        )}
                      </div>

                      <div className="grid gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
                        <p className="m-0 text-sm font-medium text-slate-900">复核与生成草稿</p>
                        <div className="grid gap-3 md:grid-cols-2">
                          <LabeledTextarea
                            label="复核说明"
                            value={proposalReviewReason}
                            onChange={setProposalReviewReason}
                            className="md:col-span-1"
                          />
                          <LabeledTextarea
                            label="生成草稿说明"
                            value={proposalDraftReason}
                            onChange={setProposalDraftReason}
                            className="md:col-span-1"
                          />
                        </div>
                        <div className="flex flex-wrap gap-3">
                          <button
                            type="button"
                            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700"
                            onClick={() =>
                              reviewProposal.mutate({
                                proposalId: selectedProposal.proposal_id,
                                action: 'start_review',
                                reason: proposalReviewReason.trim() || undefined,
                              })
                            }
                            disabled={reviewProposal.isPending || acceptProposal.isPending}
                          >
                            开始复核
                          </button>
                          <button
                            type="button"
                            className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700"
                            onClick={() =>
                              reviewProposal.mutate({
                                proposalId: selectedProposal.proposal_id,
                                action: 'reject',
                                reason: proposalReviewReason.trim() || undefined,
                              })
                            }
                            disabled={reviewProposal.isPending || acceptProposal.isPending}
                          >
                            驳回建议
                          </button>
                          <button
                            type="button"
                            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white"
                            onClick={() =>
                              acceptProposal.mutate({
                                proposalId: selectedProposal.proposal_id,
                                reason: proposalDraftReason.trim() || undefined,
                              })
                            }
                            disabled={acceptProposal.isPending || reviewProposal.isPending}
                          >
                            生成草稿
                          </button>
                        </div>
                        {selectedProposal.accepted_draft_version_id ? (
                          <p className="m-0 text-sm text-emerald-700">
                            已生成草稿版本：{selectedProposal.accepted_draft_version_id}
                          </p>
                        ) : null}
                      </div>
                    </article>
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                    当前还没有可查看的策略优化建议详情。
                  </div>
                )}
              </section>
              {statusMessage ? <p className="m-0 text-sm text-slate-700">{statusMessage}</p> : null}
            </section>
          </div>
        )
      }
    />
  );
}

export function StrategyCandidatesPage({ availability }: FormalPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="候选版本"
      queryState={state}
      purpose="兼容查看旧候选入口，正式策略创建和发布请统一回到策略中心。"
      inputDescription="当前页面不再承载正式策略草稿、审核或发布。"
      processingDescription="系统保留该入口用于过渡，不再作为正式策略事实源。"
      outputDescription="如需正式策略，请返回策略中心查看当前版本或保存新草稿。"
      businessAction={{ label: '返回策略中心', to: '/strategies' }}
      result={availability ? undefined : <p className="text-sm text-slate-700">该页面仅保留兼容入口，正式策略流程已迁移到“策略中心”。</p>}
    />
  );
}

function resolveErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '策略中心操作失败，请稍后重试。';
}

function formatPercentDelta(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '暂无';
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatConfidence(value: number | null | undefined) {
  if (value === null || value === undefined) {
    return '未知';
  }
  return `${(value * 100).toFixed(1)}%`;
}

function renderVersionSnapshot(snapshot: StrategyRevisionProposal['affected_strategy_version']) {
  const versionLabel = snapshot.version_no !== null && snapshot.version_no !== undefined ? `v${snapshot.version_no}` : '未知版本';
  const title = snapshot.title ?? snapshot.strategy_version_id;
  const lifecycle = snapshot.lifecycle_label ?? snapshot.lifecycle_state ?? '未说明';
  return `${title} · ${versionLabel} · ${lifecycle}`;
}

function proposalActionLabel(action: string) {
  switch (action) {
    case 'start_review':
      return '开始复核';
    case 'return_to_draft':
      return '退回复核前';
    case 'reject':
      return '驳回建议';
    case 'archive':
      return '归档建议';
    case 'supersede':
      return '标记为已被替代';
    case 'generate_draft':
      return '生成草稿';
    default:
      return action;
  }
}

function proposalChangeLabel(field: string) {
  switch (field) {
    case 'title':
      return '策略名称';
    case 'summary':
      return '策略摘要';
    case 'risk_policy_json':
      return '风险政策';
    case 'selection_policy_json':
      return '市场状态与降级政策';
    case 'universe_json':
      return '目标股票范围';
    case 'rule_memberships':
      return '规则池';
    case 'proposed_weight_changes':
      return '规则权重调整';
    default:
      return field;
  }
}

function summarizeDiffValue(value: unknown) {
  if (value === null || value === undefined) {
    return '未设置';
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `${value.length} 项`;
  }
  return '已变更';
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1">
      <p className="m-0 text-xs font-medium text-slate-500">{label}</p>
      <p className="m-0 text-sm text-slate-800">{value}</p>
    </div>
  );
}

function LabeledInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1 text-sm text-slate-700">
      <span>{label}</span>
      <input className="rounded-lg border border-slate-200 px-3 py-2" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function LabeledTextarea({
  label,
  value,
  onChange,
  className,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) {
  return (
    <label className={`grid gap-1 text-sm text-slate-700 ${className ?? ''}`}>
      <span>{label}</span>
      <textarea className="min-h-24 rounded-lg border border-slate-200 px-3 py-2" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function LabeledSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="grid gap-1 text-sm text-slate-700">
      <span>{label}</span>
      <select className="rounded-lg border border-slate-200 px-3 py-2" aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">请选择</option>
        {options.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  );
}
