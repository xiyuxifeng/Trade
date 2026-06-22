import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import type { PageAvailability } from '@/components/layout/business-page-shell';
import { StatusBadge } from '@/components/kit';
import {
  acceptAfterCloseProposalToDraft,
  generateAfterCloseProposals,
  getAfterCloseReview,
  getTradingDayPlan,
  listAfterCloseProposals,
  reviewAfterCloseProposal,
} from '@/lib/api/daily';
import { ApiError } from '@/lib/api/http';
import { formatLocalDateInputOffset } from '@/lib/date';
import type {
  AfterCloseAttributionSignal,
  AfterCloseCoverageState,
  AfterCloseProposal,
  AfterCloseProposalCollectionResponse,
  AfterCloseReviewResponse,
  AfterCloseSignalResult,
  TradingDayPlanResponse,
} from '@/types/daily';

const AFTER_CLOSE_STATE_LABELS: Record<AfterCloseCoverageState, string> = {
  ready: '已确认',
  partial: '部分缺失',
  unavailable: '暂不可用',
  conflict: '证据冲突',
  invalid: '证据无效',
  insufficient_coverage: '覆盖不足',
  degraded: '已降级',
};

const SIDE_LABELS = {
  BUY: '买入',
  SELL: '卖出',
  HOLD: '观望',
} as const;

const PROPOSAL_TARGET_LABELS: Record<string, string> = {
  RuleVersion: '规则',
  AuthorProfileVersion: '作者画像',
  StrategyVersion: '正式策略',
};

function isPermissionDenied(error: unknown) {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

function pageAvailabilityForReview(state: AfterCloseCoverageState | undefined): PageAvailability {
  if (!state) {
    return 'unavailable';
  }
  if (state === 'ready') {
    return 'ready';
  }
  if (state === 'unavailable') {
    return 'unavailable';
  }
  return 'partial';
}

function formatPercent(value: unknown) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '暂不可用';
  }
  return `${(value * 100).toFixed(2)}%`;
}

function formatMetricState(state: AfterCloseCoverageState) {
  return AFTER_CLOSE_STATE_LABELS[state] ?? state;
}

function formatMetricReason(reason: string | null | undefined) {
  const labels: Record<string, string> = {
    approved_execution_supplement_missing: '执行补充证据未提供，成交相关结果暂不可用。',
    post_close_market_state_missing: '盘后市场状态暂不可用，当前不能判断是否发生变化。',
    no_matching_daily_rule_selection_item: '当前没有找到与盘前规则选择完全对应的规则证据。',
    baseline_unavailable: '缺少可复核的入场基线，当前不能计算结果。',
    signal_entry_price_missing: '缺少入场基线，当前不能计算结果。',
    signal_entry_price_invalid: '入场基线无效，当前不能计算结果。',
    baseline_previous_close_missing_or_invalid: '缺少前收盘基线，当前不能计算结果。',
    actual_row_unavailable: '缺少正式盘后行情，当前不能确认结果。',
    post_close_actual_row_missing: '缺少正式盘后行情，当前不能确认结果。',
    actual_row_not_available: '盘后行情尚未冻结完成，当前不能确认结果。',
  };
  if (!reason) {
    return '当前未记录额外说明。';
  }
  return labels[reason] ?? `当前状态：${reason}`;
}

function formatActualResultValue(signal: AfterCloseSignalResult) {
  const actual = signal.actual_result;
  if (actual.state !== 'ready') {
    return formatMetricReason(actual.reason);
  }
  const labels: Record<string, string> = {
    up: '与盘前方向一致',
    down: '与盘前方向相反',
    flat: '盘后基本持平',
    moved: '盘后出现明显波动',
  };
  return labels[String(actual.value)] ?? String(actual.value ?? '暂不可用');
}

function isFavorableSignal(signal: AfterCloseSignalResult) {
  const ret = signal.return;
  if (ret.state === 'ready' && typeof ret.value === 'number') {
    return ret.value >= 0;
  }
  const actual = signal.actual_result;
  if (actual.state !== 'ready') {
    return false;
  }
  if (signal.side === 'BUY') {
    return actual.value === 'up' || actual.value === 'flat';
  }
  if (signal.side === 'SELL') {
    return actual.value === 'down' || actual.value === 'flat';
  }
  return actual.value === 'flat';
}

function buildSuccessReasons(plan: TradingDayPlanResponse | undefined, review: AfterCloseReviewResponse | undefined) {
  if (!review?.generated) {
    return [];
  }
  return review.signal_results
    .filter((signal) => signal.state === 'ready' && isFavorableSignal(signal))
    .map((signal) => {
      const matchedRules = signal.matched_rule.rule_version_ids.length ? signal.matched_rule.rule_version_ids.join('、') : '对应规则';
      const planSignal = plan?.signals.find((item) => item.signal_id === signal.signal_id || item.symbol === signal.symbol);
      const confidence = planSignal?.confidence_label ? `，盘前置信度 ${planSignal.confidence_label}` : '';
      return `${signal.symbol} 的${SIDE_LABELS[signal.side]}判断与盘后结果一致，命中规则 ${matchedRules}${confidence}。`;
    });
}

function buildFailureReasons(review: AfterCloseReviewResponse | undefined) {
  if (!review?.generated) {
    return [];
  }
  const attributionBySignalId = new Map(
    (review.attribution?.signals ?? []).map((item) => [item.signal_id, item] as const),
  );
  return review.signal_results
    .filter((signal) => !isFavorableSignal(signal) || signal.state !== 'ready')
    .map((signal) => {
      const attribution = attributionBySignalId.get(signal.signal_id);
      if (attribution?.user_explanation) {
        return `${signal.symbol}：${attribution.user_explanation}`;
      }
      return `${signal.symbol}：${formatMetricReason(signal.actual_result.reason ?? signal.market_state_change.reason ?? signal.executed.reason)}`;
    });
}

function buildDifferenceRows(plan: TradingDayPlanResponse | undefined, review: AfterCloseReviewResponse | undefined) {
  if (!plan || !review?.generated) {
    return [];
  }
  return review.signal_results.map((signal) => {
    const planSignal = plan.signals.find((item) => item.signal_id === signal.signal_id || item.symbol === signal.symbol);
    const prediction = planSignal ? `${SIDE_LABELS[planSignal.side]}，${planSignal.confidence_label}` : `${SIDE_LABELS[signal.side]}，盘前预测已生成`;
    const actual = formatActualResultValue(signal);
    let difference = '盘前预测与盘后结果方向基本一致。';
    if (signal.market_state_change.state === 'unavailable') {
      difference = '盘后市场状态暂不可用，当前不能判断市场状态是否变化。';
    } else if (!isFavorableSignal(signal)) {
      difference = '盘后结果没有验证盘前方向，需重点复核。';
    } else if (signal.executed.state === 'unavailable') {
      difference = '盘后方向已确认，但成交补充证据暂未提供。';
    }
    return {
      symbol: signal.symbol,
      prediction,
      actual,
      difference,
    };
  });
}

function formatProposalActionLabel(action: string) {
  const labels: Record<string, string> = {
    start_review: '开始复核',
    continue_observing: '继续观察',
    reject: '拒绝',
    accept_to_draft: '生成策略草稿',
  };
  return labels[action] ?? action;
}

function proposalActionHint(proposal: AfterCloseProposal) {
  if (proposal.proposal_type === 'strategy_revision') {
    return '只会生成草稿，不会直接发布，也不会改动当前正式策略。';
  }
  return '当前只允许复核、继续观察或拒绝，不会直接改写正式对象。';
}

function formatTraceabilityItem(label: string, value: unknown) {
  if (value === null || value === undefined || value === '') {
    return (
      <div className="grid gap-1 md:grid-cols-[10rem,1fr]">
        <span className="font-medium text-slate-700">{label}</span>
        <span>暂未绑定</span>
      </div>
    );
  }
  return (
    <div className="grid gap-1 md:grid-cols-[10rem,1fr]">
      <span className="font-medium text-slate-700">{label}</span>
      <span className="break-all">{String(value)}</span>
    </div>
  );
}

function SummaryStateCard({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className="mt-2 text-sm font-medium text-slate-950">{value}</p>
    </div>
  );
}

function PredictionSection({ plan }: { plan: TradingDayPlanResponse | undefined }) {
  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">盘前预测</h2>
          <p className="mt-1 text-sm text-slate-700">这里只展示正式盘前计划中已经确认的目标、方向和风险提示。</p>
        </div>
        <StatusBadge value={plan?.plan_status ?? 'unavailable'} />
      </div>
      {!plan?.signals.length ? (
        <p className="text-sm text-slate-700">今日尚未生成可复核的盘前信号，当前不能展示盘前预测。</p>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {plan.signals.map((signal) => (
            <div key={signal.signal_id ?? signal.symbol} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="m-0 text-sm font-medium text-slate-950">{signal.symbol}{signal.name ? ` · ${signal.name}` : ''}</p>
                <StatusBadge value={signal.state} />
              </div>
              <div className="mt-3 grid gap-2 text-sm text-slate-700">
                <div><span className="font-medium text-slate-900">盘前方向：</span>{SIDE_LABELS[signal.side]}，{signal.confidence_label}</div>
                <div><span className="font-medium text-slate-900">入场条件：</span>{signal.entry_condition}</div>
                <div><span className="font-medium text-slate-900">失效条件：</span>{signal.invalidation_condition}</div>
                <div><span className="font-medium text-slate-900">仓位建议：</span>{signal.suggested_position}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function ActualResultsSection({ review }: { review: AfterCloseReviewResponse | undefined }) {
  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">实际结果</h2>
          <p className="mt-1 text-sm text-slate-700">系统只展示正式盘后证据已经确认的结果，不会把缺失值当作成功。</p>
        </div>
        <StatusBadge value={review?.signal_outcome_state ?? 'unavailable'} />
      </div>
      {!review?.generated || !review.signal_results.length ? (
        <p className="text-sm text-slate-700">正式盘后结果尚未生成，当前不能展示实际结果。</p>
      ) : (
        <div className="grid gap-3">
          {review.signal_results.map((signal) => (
            <div key={signal.signal_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="m-0 text-sm font-medium text-slate-950">{signal.symbol} · {SIDE_LABELS[signal.side]}</p>
                <StatusBadge value={signal.state} />
              </div>
              <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                <div><span className="font-medium text-slate-900">盘后判断：</span>{formatActualResultValue(signal)}</div>
                <div><span className="font-medium text-slate-900">收益：</span>{signal.return.state === 'ready' ? formatPercent(signal.return.value) : formatMetricReason(signal.return.reason)}</div>
                <div><span className="font-medium text-slate-900">盘中最大有利：</span>{signal.mfe.state === 'ready' ? formatPercent(signal.mfe.value) : formatMetricReason(signal.mfe.reason)}</div>
                <div><span className="font-medium text-slate-900">盘中最大不利：</span>{signal.mae.state === 'ready' ? formatPercent(signal.mae.value) : formatMetricReason(signal.mae.reason)}</div>
                <div><span className="font-medium text-slate-900">成交补充：</span>{signal.executed.state === 'ready' ? String(signal.executed.value) : formatMetricReason(signal.executed.reason)}</div>
                <div><span className="font-medium text-slate-900">盘后市场状态：</span>{signal.market_state_change.state === 'ready' ? (signal.market_state_change.value === 'changed' ? '已变化' : '未变化') : formatMetricReason(signal.market_state_change.reason)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function DifferenceSection({
  plan,
  review,
}: {
  plan: TradingDayPlanResponse | undefined;
  review: AfterCloseReviewResponse | undefined;
}) {
  const rows = buildDifferenceRows(plan, review);
  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">差异</h2>
      {!rows.length ? (
        <p className="text-sm text-slate-700">当前还没有足够的正式盘后证据，暂时无法展示差异。</p>
      ) : (
        <div className="grid gap-3">
          {rows.map((row) => (
            <div key={row.symbol} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
              <p className="m-0 font-medium text-slate-950">{row.symbol}</p>
              <p className="mt-2"><span className="font-medium text-slate-900">盘前预测：</span>{row.prediction}</p>
              <p className="mt-1"><span className="font-medium text-slate-900">盘后实际：</span>{row.actual}</p>
              <p className="mt-1"><span className="font-medium text-slate-900">差异说明：</span>{row.difference}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function AttributionSection({
  title,
  items,
  emptyMessage,
}: {
  title: string;
  items: string[];
  emptyMessage: string;
}) {
  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
      <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
      {items.length ? (
        <div className="space-y-2">
          {items.map((item, index) => (
            <div key={`${title}-${index}`} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              {item}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-700">{emptyMessage}</p>
      )}
    </section>
  );
}

function ProposalSection({
  review,
  proposals,
  loading,
  onGenerate,
  onReview,
  onAccept,
  actionLoading,
}: {
  review: AfterCloseReviewResponse | undefined;
  proposals: AfterCloseProposalCollectionResponse | undefined;
  loading: boolean;
  onGenerate: () => void;
  onReview: (proposal: AfterCloseProposal, action: 'start_review' | 'continue_observing' | 'reject') => void;
  onAccept: (proposal: AfterCloseProposal) => void;
  actionLoading: boolean;
}) {
  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">建议操作</h2>
          <p className="mt-1 text-sm text-slate-700">规则、作者画像和正式策略会分开展示，并遵守各自的安全边界。</p>
        </div>
        <button
          type="button"
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={onGenerate}
          disabled={!review?.post_market_review_id || actionLoading}
        >
          整理今日建议
        </button>
      </div>
      {!review?.generated ? (
        <p className="text-sm text-slate-700">正式盘后复盘尚未生成，当前不能整理建议操作。</p>
      ) : loading ? (
        <p className="text-sm text-slate-700">正在读取今日建议操作。</p>
      ) : !proposals || !proposals.items.length ? (
        <p className="text-sm text-slate-700">本次尚未整理建议操作。你可以先整理今日建议，再决定是否进入复核。</p>
      ) : (
        <div className="grid gap-3">
          {proposals.items.map((proposal) => (
            <div key={proposal.proposal_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="m-0 text-sm font-medium text-slate-950">{proposal.proposal_type_label}</p>
                  <p className="mt-1 text-sm text-slate-700">
                    目标：{PROPOSAL_TARGET_LABELS[proposal.target.asset_type] ?? proposal.target.asset_type} · {proposal.target.label}
                  </p>
                </div>
                <StatusBadge value={proposal.lifecycle_label} />
              </div>
              <div className="mt-3 grid gap-2 text-sm text-slate-700 md:grid-cols-2">
                <div><span className="font-medium text-slate-900">证据状态：</span>{proposal.evidence_label}</div>
                <div><span className="font-medium text-slate-900">建议方向：</span>{proposal.recommendation_label}</div>
                <div><span className="font-medium text-slate-900">当前状态：</span>{proposal.lifecycle_label}</div>
                <div><span className="font-medium text-slate-900">可信度：</span>{proposal.confidence == null ? '暂未评估' : `${Math.round(proposal.confidence * 100)}%`}</div>
              </div>
              <p className="mt-3 text-sm text-slate-700">{proposal.rationale}</p>
              <p className="mt-2 text-xs text-slate-600">{proposalActionHint(proposal)}</p>
              {proposal.partial_reasons.length ? (
                <div className="mt-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  {proposal.partial_reasons.join('；')}
                </div>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-2">
                {proposal.available_actions.includes('start_review') ? (
                  <button
                    type="button"
                    className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={() => onReview(proposal, 'start_review')}
                    disabled={actionLoading}
                  >
                    {formatProposalActionLabel('start_review')}
                  </button>
                ) : null}
                {proposal.available_actions.includes('continue_observing') ? (
                  <button
                    type="button"
                    className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-800 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={() => onReview(proposal, 'continue_observing')}
                    disabled={actionLoading}
                  >
                    {formatProposalActionLabel('continue_observing')}
                  </button>
                ) : null}
                {proposal.available_actions.includes('reject') ? (
                  <button
                    type="button"
                    className="inline-flex h-10 items-center justify-center rounded-lg border border-rose-200 bg-white px-4 text-sm font-medium text-rose-700 transition-colors hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={() => onReview(proposal, 'reject')}
                    disabled={actionLoading}
                  >
                    {formatProposalActionLabel('reject')}
                  </button>
                ) : null}
                {proposal.available_actions.includes('accept_to_draft') ? (
                  <button
                    type="button"
                    className="inline-flex h-10 items-center justify-center rounded-lg border border-sky-200 bg-sky-50 px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-sky-100 disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={() => onAccept(proposal)}
                    disabled={actionLoading}
                  >
                    {formatProposalActionLabel('accept_to_draft')}
                  </button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function buildAdvancedDetails(review: AfterCloseReviewResponse | undefined) {
  if (!review?.generated) {
    return <p>正式盘后复盘尚未生成。</p>;
  }
  const actuals = (review.evidence.actuals ?? {}) as Record<string, unknown>;
  return (
    <div className="grid gap-2 text-xs">
      {formatTraceabilityItem('盘后复盘编号', review.post_market_review_id)}
      {formatTraceabilityItem('盘后行情快照', review.post_close_market_snapshot_id)}
      {formatTraceabilityItem('盘后市场状态', review.post_close_market_state_id)}
      {formatTraceabilityItem('行情内容指纹', actuals.market_snapshot_content_fingerprint)}
      {formatTraceabilityItem('数据快照指纹', actuals.dataset_content_fingerprint)}
      {formatTraceabilityItem('证据指纹', (review.evidence as Record<string, unknown>).evidence_fingerprint)}
      {formatTraceabilityItem('数据状态', actuals.coverage_state)}
    </div>
  );
}

export function TodayAfterClosePage({ availability }: { availability?: PageAvailability } = {}) {
  const tradeDate = useMemo(() => formatLocalDateInputOffset(0), []);
  const queryClient = useQueryClient();
  const [pageMessage, setPageMessage] = useState<string | null>(null);

  if (availability) {
    return (
      <ProductPageAdapter
        title="今日盘后"
        queryState={availability}
        purpose="复盘今天盘前预测在盘后是否成立，并决定后续处理动作。"
        inputDescription="需要已批准的每日运行计划，以及正式盘后结果、结构化归因和建议记录。"
        processingDescription="系统只读取正式盘前计划、盘后行情证据、结构化归因和建议状态。"
        outputDescription="输出盘前预测、实际结果、差异、成功原因、失败原因和建议操作。"
        businessAction={{ label: '返回今日总览', to: '/daily/overview' }}
      />
    );
  }

  const planQuery = useQuery({
    queryKey: ['daily-after-close', 'plan', tradeDate],
    queryFn: () => getTradingDayPlan(tradeDate),
    staleTime: 15_000,
  });

  const reviewQuery = useQuery({
    queryKey: ['daily-after-close', 'review', planQuery.data?.trading_day_plan_id ?? 'missing-plan'],
    queryFn: () => getAfterCloseReview(planQuery.data!.trading_day_plan_id!),
    enabled: Boolean(planQuery.data?.trading_day_plan_id),
    staleTime: 15_000,
  });

  const proposalsQuery = useQuery({
    queryKey: ['daily-after-close', 'proposals', reviewQuery.data?.post_market_review_id ?? 'missing-review'],
    queryFn: () => listAfterCloseProposals(reviewQuery.data!.post_market_review_id!),
    enabled: Boolean(reviewQuery.data?.post_market_review_id),
    staleTime: 15_000,
  });

  const generateMutation = useMutation({
    mutationFn: (postMarketReviewId: string) => generateAfterCloseProposals(postMarketReviewId),
    onSuccess: async () => {
      setPageMessage('今日建议已整理完成。');
      await queryClient.invalidateQueries({ queryKey: ['daily-after-close', 'proposals'] });
    },
  });

  const reviewProposalMutation = useMutation({
    mutationFn: ({ proposalId, action }: { proposalId: string; action: 'start_review' | 'continue_observing' | 'reject' }) =>
      reviewAfterCloseProposal(proposalId, { action }),
    onSuccess: async () => {
      setPageMessage('建议状态已更新。');
      await queryClient.invalidateQueries({ queryKey: ['daily-after-close', 'proposals'] });
    },
  });

  const acceptProposalMutation = useMutation({
    mutationFn: (proposalId: string) => acceptAfterCloseProposalToDraft(proposalId, { reason: '盘后页面发起草稿复核' }),
    onSuccess: async () => {
      setPageMessage('策略修订建议已生成草稿，当前正式策略不会被直接发布或改写。');
      await queryClient.invalidateQueries({ queryKey: ['daily-after-close', 'proposals'] });
    },
  });

  const plan = planQuery.data;
  const review = reviewQuery.data;
  const proposals = proposalsQuery.data;
  const loading = planQuery.isLoading || (Boolean(plan?.trading_day_plan_id) && reviewQuery.isLoading);
  const error = planQuery.error ?? reviewQuery.error ?? proposalsQuery.error;
  const permissionDenied = isPermissionDenied(error);

  let queryState: PageAvailability = 'ready';
  let stateTitle: string | undefined;
  let stateDescription: string | undefined;
  let impact: string | undefined;
  let recoveryAction: { label: string; to: string } | undefined;

  if (loading) {
    queryState = 'loading';
  } else if (permissionDenied) {
    queryState = 'permission_denied';
  } else if (error) {
    queryState = 'error';
  } else if (!plan?.generated || !plan.trading_day_plan_id) {
    queryState = 'unavailable';
    stateTitle = '尚未生成盘前计划';
    stateDescription = plan?.happened ?? '今天还没有可复核的正式盘前计划。';
    impact = '当前不能读取对应的正式盘后复盘。';
    recoveryAction = { label: '查看今日盘前', to: '/daily/pre-market' };
  } else if (!review?.generated) {
    queryState = 'unavailable';
    stateTitle = '盘后结果暂不可用';
    stateDescription = review?.happened ?? '今天还没有生成正式盘后复盘。';
    impact = review?.affected ?? '当前不能展示实际结果、差异和建议操作。';
    recoveryAction = { label: '返回今日盘前', to: '/daily/pre-market' };
  } else {
    queryState = pageAvailabilityForReview(review.state);
    stateTitle = queryState === 'ready' ? undefined : AFTER_CLOSE_STATE_LABELS[review.state];
    stateDescription = review.happened;
    impact = review.affected;
    recoveryAction = queryState === 'ready' ? undefined : { label: '查看今日盘前', to: '/daily/pre-market' };
  }

  const actionLoading = generateMutation.isPending || reviewProposalMutation.isPending || acceptProposalMutation.isPending;
  const successReasons = buildSuccessReasons(plan, review);
  const failureReasons = buildFailureReasons(review);

  return (
    <ProductPageAdapter
      title="今日盘后"
      queryState={queryState}
      purpose="复盘今天盘前预测在盘后是否成立，并决定后续处理动作。"
      inputDescription="需要已批准的每日运行计划，以及正式盘后结果、结构化归因和建议记录。"
      processingDescription="系统只读取正式盘前计划、盘后行情证据、结构化归因和建议状态。"
      outputDescription="输出盘前预测、实际结果、差异、成功原因、失败原因和建议操作。"
      businessAction={{ label: '返回今日总览', to: '/daily/overview' }}
      currentStep="先核对盘前预测与盘后实际结果，再决定是否处理今日建议。"
      stateTitle={stateTitle}
      stateDescription={stateDescription}
      impact={impact}
      recoveryAction={recoveryAction}
      advancedAdminDetails={buildAdvancedDetails(review)}
      input={
        <div className="grid gap-3 md:grid-cols-3">
          <SummaryStateCard title="交易日" value={tradeDate} />
          <SummaryStateCard title="盘前计划" value={plan?.approval_state === 'approved' ? '已批准' : plan?.approval_state === 'rejected' ? '已拒绝' : '待确认'} />
          <SummaryStateCard title="数据状态" value={review ? formatMetricState(review.state) : '暂不可用'} />
        </div>
      }
      result={
        <div className="space-y-4">
          {pageMessage ? (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
              {pageMessage}
            </div>
          ) : null}

          <div className="rounded-2xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge value={review?.state ?? 'unavailable'} />
              <span className="text-sm font-medium text-slate-950">{review?.happened ?? '正式盘后复盘尚未生成。'}</span>
            </div>
            <div className="mt-3 grid gap-2 text-sm text-slate-700">
              <div><span className="font-medium text-slate-900">影响：</span>{review?.affected ?? '当前不能显示完整的正式盘后结果。'}</div>
              <div><span className="font-medium text-slate-900">处理方式：</span>{review?.repair_guidance ?? '请先完成正式盘后复盘。'}</div>
            </div>
          </div>

          <PredictionSection plan={plan} />
          <ActualResultsSection review={review} />
          <DifferenceSection plan={plan} review={review} />
          <AttributionSection title="成功原因" items={successReasons} emptyMessage="当前没有形成可单独归纳的成功原因，页面只保留已确认的正向结果。" />
          <AttributionSection title="失败原因" items={failureReasons} emptyMessage="当前没有检测到需要单独归因的失败原因。" />
          <ProposalSection
            review={review}
            proposals={proposals}
            loading={proposalsQuery.isLoading}
            actionLoading={actionLoading}
            onGenerate={() => {
              if (review?.post_market_review_id) {
                setPageMessage(null);
                generateMutation.mutate(review.post_market_review_id);
              }
            }}
            onReview={(proposal, action) => {
              setPageMessage(null);
              reviewProposalMutation.mutate({ proposalId: proposal.proposal_id, action });
            }}
            onAccept={(proposal) => {
              setPageMessage(null);
              acceptProposalMutation.mutate(proposal.proposal_id);
            }}
          />

          <div className="flex flex-wrap gap-2">
            <Link className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50" to="/daily/pre-market">
              返回今日盘前
            </Link>
            <Link className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50" to="/daily/overview">
              返回今日总览
            </Link>
          </div>
        </div>
      }
      help={
        <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
          页面只会展示正式证据已经确认的盘后结果。成交补充未提供时，会明确显示为“暂不可用”，不会默认为成功；盘后市场状态缺失时，也只会显示“暂不可用”。
        </div>
      }
    />
  );
}
