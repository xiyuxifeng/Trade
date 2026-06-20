import { useMemo, useState } from 'react';

import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { ApiError } from '@/lib/api/http';
import {
  createStrategyDraft,
  getStrategyDraftOptions,
  listStrategies,
  publishStrategy,
  submitStrategyReview,
} from '@/lib/api/strategies';
import type { StrategyVersion } from '@/types/strategies';
import { useMutation, useQuery } from '@tanstack/react-query';

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
  const [localVersion, setLocalVersion] = useState<StrategyVersion | null>(null);
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

  const permissionDenied =
    (strategiesQuery.error instanceof ApiError && [401, 403].includes(strategiesQuery.error.status)) ||
    (optionsQuery.error instanceof ApiError && [401, 403].includes(optionsQuery.error.status));
  const unavailable =
    (strategiesQuery.error instanceof ApiError && strategiesQuery.error.status >= 500) ||
    (optionsQuery.error instanceof ApiError && optionsQuery.error.status >= 500);
  const state: PageAvailability =
    availability ??
    (strategiesQuery.isLoading || optionsQuery.isLoading
      ? 'loading'
      : permissionDenied
        ? 'permission_denied'
        : unavailable
          ? 'unavailable'
          : strategiesQuery.error || optionsQuery.error
            ? 'error'
            : strategiesQuery.data?.state === 'empty'
              ? 'empty'
              : strategiesQuery.data?.state === 'partial'
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
                  onClick={() => activeVersion && publish.mutate(activeVersion.strategy_version_id)}
                  disabled={!activeVersion}
                >
                  发布为当前策略
                </button>
              </div>
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
