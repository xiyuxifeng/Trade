import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { BarChart3, RefreshCw, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { LoadingState } from '@/components/kit';
import { useAuth } from '@/features/auth/auth-context';
import { executeFormalBacktestRun, getFormalBacktestResult } from '@/lib/api/backtests';
import { ApiError } from '@/lib/api/http';
import type { FormalMarketStateMetric } from '@/types/backtests';

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
              <p className="mt-1 text-sm text-slate-600">市场状态模型：{result.market_state_model_version ?? '未记录'}</p>
              <p className="mt-1 text-sm text-slate-600">来源版本：{result.market_state_source_version ?? '未记录'}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="font-semibold text-slate-950">样本状态</p>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-slate-600">
                {Object.entries(result.sample_state_counts).map(([key, value]) => (
                  <span key={key}>{key}: {value}</span>
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
        </>
      ) : null}
    </div>
  );
}
