import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { BarChart3, ClipboardCheck, RefreshCw, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { LoadingState } from '@/components/kit';
import { useAuth } from '@/features/auth/auth-context';
import { executeFormalBacktestRun, generateFormalApplicabilityProfileDraft, getFormalBacktestResult, reviewFormalApplicabilityProfile } from '@/lib/api/backtests';
import { ApiError } from '@/lib/api/http';
import type { FormalApplicabilityProfile, FormalMarketStateMetric } from '@/types/backtests';

function formatPct(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return `${(value * 100).toFixed(2)}%`;
}

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'n/a';
  }
  return value.toLocaleString('zh-CN');
}

function levelLabel(level: string) {
  if (level === 'level_1') return 'Level 1：历史行情';
  if (level === 'level_2') return 'Level 2：历史行情 + 市场状态';
  if (level === 'level_3') return 'Level 3：历史行情 + 市场状态 + Kaipan 数据';
  return level;
}

function sampleStateLabel(key: string) {
  const labels: Record<string, string> = {
    eligible: '可评估样本',
    evaluated_true: '条件成立',
    evaluated_false: '条件不成立',
    condition_unavailable: '条件数据不可用',
    data_missing: '数据缺失',
    unsupported: '暂不支持',
    invalid: '无效样本',
    skipped: '已跳过',
    conflict: '数据冲突',
    market_state_unavailable: '市场状态不可用',
    kaipan_unavailable: 'Kaipan 数据不可用',
  };
  return labels[key] ?? key;
}

function recommendationLabel(value: string) {
  const labels: Record<string, string> = {
    recommended: '建议使用',
    limited: '限定观察',
    not_recommended: '不建议使用',
    insufficient_sample: '样本不足',
    unavailable: '暂不可判断',
    conflict: '证据冲突',
    invalid: '无效',
  };
  return labels[value] ?? value;
}

function reviewStatusLabel(value: string) {
  const labels: Record<string, string> = {
    draft: '草稿',
    pending_review: '等待审核',
    approved: '已批准',
    rejected: '已驳回',
    invalidated: '已作废',
    superseded: '已被新版本替代',
  };
  return labels[value] ?? value;
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 404) {
    return '没有找到这次正式回测的结果，请确认运行编号或先生成结果。';
  }
  if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
    return '当前账号没有执行或查看这次结果的权限。';
  }
  return '结果读取失败，请稍后重试或确认这次回测的数据状态。';
}

function MetricRow({ metric }: { metric: FormalMarketStateMetric }) {
  return (
    <tr className="border-t border-slate-100">
      <td className="px-4 py-3 font-medium text-slate-950">{metric.market_state_label}</td>
      <td className="px-4 py-3 text-slate-700">{formatNumber(metric.eligible_sample_count)}</td>
      <td className="px-4 py-3 text-slate-700">{formatNumber(metric.evaluated_sample_count)}</td>
      <td className="px-4 py-3 text-slate-700">{formatNumber(metric.unavailable_sample_count)}</td>
      <td className="px-4 py-3 text-slate-700">{formatNumber(metric.invalid_sample_count)}</td>
      <td className="px-4 py-3 text-slate-700">{formatNumber(metric.conflict_sample_count)}</td>
      <td className="px-4 py-3 text-slate-700">{formatNumber(metric.hit_trade_count)}</td>
      <td className="px-4 py-3 text-slate-700">{formatPct(metric.win_rate)}</td>
      <td className="px-4 py-3 text-slate-700">{formatPct(metric.avg_return)}</td>
      <td className="px-4 py-3 text-slate-700">{formatPct(metric.max_drawdown)}</td>
      <td className="px-4 py-3 text-slate-700">{formatPct(metric.coverage)}</td>
    </tr>
  );
}

function ApplicabilityProfilePanel({
  profile,
  canReview,
  onApprove,
  onReject,
  reviewPending,
}: {
  profile: FormalApplicabilityProfile;
  canReview: boolean;
  onApprove: () => void;
  onReject: () => void;
  reviewPending: boolean;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 font-semibold text-slate-950">
            <ClipboardCheck className="h-4 w-4" />
            适用性画像草稿
          </p>
          <p className="mt-1 text-sm text-slate-600">画像只记录这次正式回测证据，需要人工审核后才可作为后续参考。</p>
        </div>
        <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-700">{reviewStatusLabel(profile.review_status)}</span>
      </div>
      <div className="mt-4 grid gap-3 text-sm md:grid-cols-4">
        <div>
          <p className="text-slate-500">样本</p>
          <p className="font-medium text-slate-950">{profile.sample_count}</p>
        </div>
        <div>
          <p className="text-slate-500">覆盖率</p>
          <p className="font-medium text-slate-950">{formatPct(profile.coverage)}</p>
        </div>
        <div>
          <p className="text-slate-500">置信度</p>
          <p className="font-medium text-slate-950">{formatPct(profile.confidence)}</p>
        </div>
        <div>
          <p className="text-slate-500">系统建议</p>
          <p className="font-medium text-slate-950">{recommendationLabel(profile.recommendation_status)}</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 text-sm md:grid-cols-4">
        <span>可用样本：{profile.eligible_sample_count}</span>
        <span>已评估：{profile.evaluated_sample_count}</span>
        <span>收益：{formatPct(profile.return_metric)}</span>
        <span>胜率：{formatPct(profile.win_rate)}</span>
        <span>最大回撤：{formatPct(profile.maximum_drawdown)}</span>
        <span>请求等级：{levelLabel(profile.requested_level)}</span>
        <span>有效等级：{levelLabel(profile.effective_level)}</span>
        <span>样本结论：{recommendationLabel(profile.insufficient_sample_status)}</span>
      </div>
      {profile.warnings.length || profile.limitations.length ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {[...profile.warnings, ...profile.limitations].map((item) => (
            <p key={item}>{item}</p>
          ))}
        </div>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-3">
        <Button disabled={!canReview || reviewPending || profile.review_status === 'approved'} onClick={onApprove}>
          批准画像
        </Button>
        <Button variant="outline" disabled={!canReview || reviewPending || profile.review_status === 'rejected'} onClick={onReject}>
          驳回画像
        </Button>
      </div>
      {!canReview ? <p className="mt-3 text-sm text-amber-700">当前账号可以查看画像；审核需要更高权限。</p> : null}
    </section>
  );
}

export function FormalBacktestResults() {
  const { canAccess, principal } = useAuth();
  const [runId, setRunId] = useState('');
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const resultQuery = useQuery({
    queryKey: ['formal-backtest-result', activeRunId],
    queryFn: () => getFormalBacktestResult(activeRunId as string),
    enabled: Boolean(activeRunId),
    retry: false,
  });

  const executeMutation = useMutation({
    mutationFn: () => executeFormalBacktestRun(runId),
    onSuccess: (result) => setActiveRunId(result.run_id),
  });

  const result = executeMutation.data ?? resultQuery.data ?? null;

  const draftMutation = useMutation({
    mutationFn: () => generateFormalApplicabilityProfileDraft(result?.run_id ?? runId, { result_id: result?.result_id ?? null, reason: '根据本次正式回测生成草稿' }),
  });

  const reviewMutation = useMutation({
    mutationFn: ({ profileId, reviewStatus }: { profileId: string; reviewStatus: 'approved' | 'rejected' }) =>
      reviewFormalApplicabilityProfile(profileId, { review_status: reviewStatus, reason: reviewStatus === 'approved' ? '人工确认回测证据可参考' : '人工认为证据暂不可用' }),
  });

  const profile = reviewMutation.data ?? draftMutation.data ?? null;
  const error = executeMutation.error ?? resultQuery.error;

  return (
    <div className="space-y-5" data-testid="formal-backtest-results-product">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-950">回测结果</p>
            <p className="mt-1 text-sm text-slate-600">输入正式回测运行编号，查看全周期和分市场状态结果、覆盖情况和可复现证据。</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
            当前身份：{principal.role}
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-3">
          <Input value={runId} onChange={(event) => setRunId(event.target.value)} placeholder="输入正式回测运行编号" className="max-w-xl" />
          <Button disabled={!runId} onClick={() => setActiveRunId(runId)}>
            查看本次结果
          </Button>
          <Button disabled={!runId || !canAccess('operator') || executeMutation.isPending} onClick={() => executeMutation.mutate()}>
            <RefreshCw className="h-4 w-4" />
            生成分市场状态结果
          </Button>
        </div>
        {!canAccess('operator') ? (
          <p className="mt-3 text-sm text-amber-700">当前账号可以查看已有结果；生成结果需要 operator 权限。</p>
        ) : null}
      </section>

      {(executeMutation.isPending || resultQuery.isFetching) ? <LoadingState label="正在读取回测结果" description="系统正在核对固定快照、市场状态和样本统计。" /> : null}
      {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{errorMessage(error)}</p> : null}

      {result ? (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="flex items-center gap-2 font-semibold text-slate-950">
                <BarChart3 className="h-4 w-4" />
                结果状态
              </p>
              <p className="mt-2 text-sm text-slate-700">{result.status === 'completed_valid' ? '结果有效' : '结果存在限制'}</p>
              <p className="mt-1 text-sm text-slate-600">请求等级：{levelLabel(result.requested_level)}</p>
              <p className="mt-1 text-sm text-slate-600">有效等级：{levelLabel(result.effective_level)}</p>
              <p className="mt-1 text-sm text-slate-600">市场状态模型：{result.market_state_model_version ?? '未记录'}</p>
              <p className="mt-1 text-sm text-slate-600">来源版本：{result.market_state_source_version ?? '未记录'}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="font-semibold text-slate-950">样本状态</p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-slate-600">
                {Object.entries(result.sample_state_counts).map(([key, value]) => (
                  <span key={key}>{sampleStateLabel(key)}: {value}</span>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="flex items-center gap-2 font-semibold text-slate-950">
                <ShieldCheck className="h-4 w-4" />
                可复现证据
              </p>
              <p className="mt-2 break-all text-sm text-slate-600">{result.reproducibility_fingerprint}</p>
            </div>
          </section>

          <section className="rounded-lg border border-slate-200 bg-white p-5">
            <p className="font-semibold text-slate-950">分市场状态表现</p>
            {result.per_market_state_metrics.length ? (
              <div className="mt-4 overflow-auto">
                <table className="w-full min-w-[900px] border-collapse text-left text-sm">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="px-4 py-3 font-medium">市场状态</th>
                      <th className="px-4 py-3 font-medium">可用样本</th>
                      <th className="px-4 py-3 font-medium">已评估</th>
                      <th className="px-4 py-3 font-medium">不可用</th>
                      <th className="px-4 py-3 font-medium">无效</th>
                      <th className="px-4 py-3 font-medium">冲突</th>
                      <th className="px-4 py-3 font-medium">命中</th>
                      <th className="px-4 py-3 font-medium">胜率</th>
                      <th className="px-4 py-3 font-medium">平均收益</th>
                      <th className="px-4 py-3 font-medium">最大回撤</th>
                      <th className="px-4 py-3 font-medium">覆盖率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.per_market_state_metrics.map((metric) => (
                      <MetricRow key={metric.market_state_label} metric={metric} />
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-3 text-sm text-slate-600">当前结果没有可计入分市场状态统计的样本。缺失市场状态不会被记为失败或亏损。</p>
            )}
          </section>

          {result.warnings.length || result.limitations.length ? (
            <section className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              {[...result.warnings, ...result.limitations].map((item) => (
                <p key={item}>{item}</p>
              ))}
            </section>
          ) : null}

          <section className="rounded-lg border border-slate-200 bg-white p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-slate-950">规则适用性画像</p>
                <p className="mt-1 text-sm text-slate-600">根据这次固定证据生成草稿，分别查看样本、覆盖率、置信度、系统建议和人工审核状态。</p>
              </div>
              <Button disabled={!canAccess('operator') || draftMutation.isPending} onClick={() => draftMutation.mutate()}>
                生成适用性画像草稿
              </Button>
            </div>
            {!canAccess('operator') ? <p className="mt-3 text-sm text-amber-700">生成草稿需要 operator 权限。</p> : null}
            {draftMutation.error ? <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">草稿生成失败，请确认这次回测结果有效且没有缺失正式证据。</p> : null}
          </section>

          {profile ? (
            <ApplicabilityProfilePanel
              profile={profile}
              canReview={canAccess('operator')}
              reviewPending={reviewMutation.isPending}
              onApprove={() => reviewMutation.mutate({ profileId: profile.profile_id, reviewStatus: 'approved' })}
              onReject={() => reviewMutation.mutate({ profileId: profile.profile_id, reviewStatus: 'rejected' })}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}
