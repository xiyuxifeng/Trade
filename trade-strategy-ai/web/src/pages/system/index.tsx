import { SystemHubPage } from './SystemHubPage';
import type { PageAvailability } from '@/components/layout/business-page-shell';
import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import { SystemStatusPanel } from '@/features/system-status/system-status-panel';
import { useMutation, useQuery } from '@tanstack/react-query';
import { listProfiles } from '@/lib/api/profiles';
import {
  cancelSystemDataOperation,
  createSystemDataOperation,
  getSystemDataReadiness,
  getSystemDataSchedule,
  listSystemRunTraces,
  listSystemDataOperations,
  resumeSystemDataOperation,
  retrySystemDataOperation,
} from '@/lib/api/system';
import { EmptyState, LoadingState } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { useAuth } from '@/features/auth/auth-context';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import type { SystemDataOperation, SystemDataReadinessStatus, SystemRunTraceItem } from '@/types/system';

function describeValidationStatus(status: string) {
  if (status === 'validated') return '已校验';
  if (status === 'draft') return '草稿';
  if (status === 'invalid_config') return '校验失败';
  if (status === 'archived') return '已归档';
  return '状态待确认';
}

function SystemConfigurationSummary() {
  const query = useQuery({
    queryKey: ['formal-system', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  if (query.isLoading) {
    return <LoadingState label="正在加载配置" description="正在读取已保存的业务配置。" />;
  }
  if (query.error) {
    return <p>配置读取失败，当前配置状态不可用，请稍后重试。</p>;
  }
  const items = query.data?.items ?? [];
  if (!items.length) {
    return <p>暂无可用配置，不会显示为已就绪。</p>;
  }
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.profile_id} className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="font-medium text-slate-950">{item.name}</p>
          <p className="mt-1 text-sm text-slate-600">校验状态：{describeValidationStatus(item.validation_status)}</p>
        </div>
      ))}
    </div>
  );
}

function formatTime(value: string | null) {
  if (!value) return '未记录';
  return value.replace('T', ' ').replace('Z', ' UTC');
}

function mapReadinessAvailability(status: SystemDataReadinessStatus): PageAvailability {
  if (status === 'ready') return 'ready';
  if (status === 'running') return 'partial';
  if (status === 'missing' || status === 'unavailable') return 'unavailable';
  if (status === 'invalid') return 'invalid';
  if (status === 'conflict') return 'conflict';
  if (status === 'insufficient_coverage') return 'degraded';
  if (status === 'failed') return 'error';
  return 'partial';
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    ready: '已就绪',
    running: '执行中',
    missing: '缺失',
    partial: '部分完成',
    unavailable: '暂不可用',
    invalid: '状态无效',
    conflict: '数据冲突',
    insufficient_coverage: '覆盖不足',
    failed: '执行失败',
    cancelled: '已取消',
    pending: '等待执行',
    success: '执行成功',
  };
  return labels[status] ?? status;
}

function readinessImpact(status: SystemDataReadinessStatus) {
  const mapping: Record<SystemDataReadinessStatus, string> = {
    ready: '研究、回测和市场状态依赖可继续使用。',
    running: '系统正在更新正式数据，结果可能尚未完整。',
    missing: '缺失数据会阻断市场状态、回测或每日流程。',
    partial: '部分数据已到位，但下游结果仍可能受限。',
    unavailable: '当前无法取得必要数据，系统不能宣布就绪。',
    invalid: '正式数据存在无效状态，不能继续依赖。',
    conflict: '正式数据之间存在冲突，需要先修复再继续。',
    insufficient_coverage: '覆盖范围不足，不能把结果当成正式就绪。',
    failed: '最近一次正式操作失败，需要人工处理。',
    cancelled: '最近一次正式操作已取消，当前仍未达到正式就绪条件。',
  };
  return mapping[status];
}

function phaseLabel(phase: string) {
  const labels: Record<string, string> = {
    before_pre_market: '盘前窗口前',
    pre_market: '盘前窗口',
    trading: '盘中观察',
    close_processing: '收盘后处理',
    post_close: '盘后窗口',
  };
  return labels[phase] ?? phase;
}

function dependencyLabel(step: string) {
  const labels: Record<string, string> = {
    refresh_pre_market_kaipan: '刷新盘前市场数据',
    recompute_market_state: '重算市场状态',
    refresh_ohlcv_close: '更新收盘后行情',
    recompute_indicators: '重算指标',
    refresh_post_close_kaipan: '刷新盘后市场数据',
    health_check_and_repair: '执行夜间健康检查与最小修复',
  };
  return labels[step] ?? step;
}

function latestOperationMessage(operation: SystemDataOperation | undefined) {
  if (!operation) return null;
  return `${operation.label} · ${statusLabel(operation.status)} · 最后更新时间 ${formatTime(operation.updated_at)}`;
}

const systemDataCompatibilityLinks = [
  { label: '市场数据总览', href: '/market' },
  { label: '市场快照详情', href: '/market/snapshots' },
  { label: '回测数据版本详情', href: '/market/datasets' },
  { label: '盘前盘后数据维护', href: '/market/kaipan' },
  { label: '历史行情维护', href: '/market/ohlcv' },
] as const;

function SystemDataSummary() {
  const { canAccess, principal } = useAuth();
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const isOperator = canAccess('operator');

  const readinessQuery = useQuery({
    queryKey: ['formal-system', 'data-readiness'],
    queryFn: getSystemDataReadiness,
    staleTime: 15_000,
  });
  const scheduleQuery = useQuery({
    queryKey: ['formal-system', 'data-schedule'],
    queryFn: getSystemDataSchedule,
    staleTime: 60_000,
  });
  const operationsQuery = useQuery({
    queryKey: ['formal-system', 'data-operations'],
    queryFn: () => listSystemDataOperations(20, 0),
    staleTime: 5_000,
  });

  const refreshAll = async () => {
    await Promise.all([
      readinessQuery.refetch(),
      scheduleQuery.refetch(),
      operationsQuery.refetch(),
    ]);
  };

  const submitMutation = useMutation({
    mutationFn: createSystemDataOperation,
    onSuccess: async (payload) => {
      const operation = payload.operation;
      setFeedback(operation ? `已提交：${operation.label}。当前状态：${statusLabel(operation.status)}。` : '操作已提交。');
      await refreshAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : '操作提交失败。');
    },
  });
  const cancelMutation = useMutation({
    mutationFn: ({ operationId, reason }: { operationId: string; reason?: string }) => cancelSystemDataOperation(operationId, reason),
    onSuccess: async () => {
      setFeedback('已提交取消请求。');
      await refreshAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : '取消失败。');
    },
  });
  const retryMutation = useMutation({
    mutationFn: ({ operationId }: { operationId: string }) => retrySystemDataOperation(operationId),
    onSuccess: async () => {
      setFeedback('已提交重试请求。');
      await refreshAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : '重试失败。');
    },
  });
  const resumeMutation = useMutation({
    mutationFn: ({ operationId }: { operationId: string }) => resumeSystemDataOperation(operationId),
    onSuccess: async () => {
      setFeedback('已提交继续执行请求。');
      await refreshAll();
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : '继续执行失败。');
    },
  });

  if ((readinessQuery.isLoading || scheduleQuery.isLoading) && !readinessQuery.data && !scheduleQuery.data) {
    return <LoadingState label="正在检查数据与调度" description="正在读取正式数据就绪状态、时间窗口和最近操作记录。" />;
  }

  const readinessError = readinessQuery.error;
  const scheduleError = scheduleQuery.error;
  if (readinessError || scheduleError) {
    const error = (readinessError ?? scheduleError) as ApiError | Error;
    const message = error instanceof ApiError && error.status === 403
      ? '当前账号没有权限查看数据与调度状态。'
      : '数据与调度状态暂不可用，请稍后重试。';
    return <p>{message}</p>;
  }

  if (!readinessQuery.data || !scheduleQuery.data) {
    return <EmptyState title="暂无数据状态" description="当前没有可用的正式就绪状态或调度窗口信息。" />;
  }

  const readiness = readinessQuery.data;
  const schedule = scheduleQuery.data;
  const operations = operationsQuery.data?.items ?? [];
  const latestOperation = operations[0];
  const latestMessage = latestOperationMessage(latestOperation);
  const mutationPending =
    submitMutation.isPending ||
    cancelMutation.isPending ||
    retryMutation.isPending ||
    resumeMutation.isPending;

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">当前状态</p>
          <p className="mt-2 font-medium text-slate-950">{statusLabel(readiness.status)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">目标交易日</p>
          <p className="mt-2 font-medium text-slate-950">{readiness.target_trade_date}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">当前时段</p>
          <p className="mt-2 font-medium text-slate-950">{phaseLabel(readiness.phase)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500">最近成功更新时间</p>
          <p className="mt-2 font-medium text-slate-950">{formatTime(readiness.latest_successful_update_at)}</p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <p className="font-medium text-slate-950">状态说明</p>
        <p className="mt-2 text-sm text-slate-700">{readiness.summary}</p>
        <p className="mt-2 text-sm text-slate-600">影响：{readinessImpact(readiness.status)}</p>
        {latestMessage ? <p className="mt-2 text-sm text-slate-600">最近操作：{latestMessage}</p> : null}
        {readiness.facts.unavailable_reasons.length ? (
          <p className="mt-2 text-sm text-amber-700">不可用原因：{readiness.facts.unavailable_reasons.join('；')}</p>
        ) : null}
        {readiness.facts.missing_coverages.length ? (
          <p className="mt-2 text-sm text-amber-700">缺失范围：{readiness.facts.missing_coverages.join('；')}</p>
        ) : null}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <p className="font-medium text-slate-950">数据源兼容入口</p>
        <p className="mt-2 text-sm text-slate-600">
          系统管理中的数据源统一归到本页查看；旧数据页保留为兼容入口，便于继续打开已有深链。
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {systemDataCompatibilityLinks.map((entry) => (
            <Link
              key={entry.href}
              className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700 transition-colors hover:border-slate-300 hover:bg-white"
              to={entry.href}
            >
              {entry.label}
            </Link>
          ))}
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="font-medium text-slate-950">正式数据检查</p>
          <div className="mt-3 grid gap-2 text-sm text-slate-700">
            <p>历史行情：{readiness.facts.latest_ohlcv_trade_date ?? '未就绪'}</p>
            <p>指标：{readiness.facts.latest_indicator_trade_date ?? '未就绪'}</p>
            <p>数据快照：{statusLabel(readiness.facts.dataset_snapshot_status)}</p>
            <p>盘前市场数据：{statusLabel(readiness.facts.pre_market_snapshot_status)}</p>
            <p>盘后市场数据：{statusLabel(readiness.facts.post_close_snapshot_status)}</p>
            <p>市场状态：{statusLabel(readiness.facts.market_state_status)}</p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="font-medium text-slate-950">推荐修复</p>
          {readiness.repair_plan.steps.length ? (
            <div className="mt-3 space-y-2">
              {readiness.repair_plan.steps.map((step) => (
                <div key={`${step.action}-${step.target_trade_date}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                  <p className="font-medium text-slate-900">{step.label}</p>
                  <p className="mt-1 text-sm text-slate-600">{step.reason}</p>
                  <p className="mt-1 text-xs text-slate-500">目标交易日：{step.target_trade_date}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-600">当前没有需要执行的一键补齐计划。</p>
          )}
          {isOperator && readiness.repair_available ? (
            <div className="mt-3">
              <Button
                onClick={() => submitMutation.mutate({ action: 'repair' })}
                disabled={mutationPending}
              >
                {submitMutation.isPending ? '提交中' : '一键补齐'}
              </Button>
            </div>
          ) : null}
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <p className="font-medium text-slate-950">业务时间窗口</p>
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          {schedule.entries.map((entry) => (
            <div key={entry.key} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="font-medium text-slate-900">{entry.label}</p>
              <p className="mt-1 text-sm text-slate-600">
                执行时间：{entry.window_start} - {entry.window_end}（{schedule.timezone}）
              </p>
              <p className="mt-1 text-sm text-slate-600">
                处理顺序：{entry.dependency_order.map(dependencyLabel).join(' -> ')}
              </p>
              {isOperator ? (
                <div className="mt-3">
                  <Button
                    variant="outline"
                    onClick={() => submitMutation.mutate({ action: 'run_schedule_window', schedule_key: entry.key })}
                    disabled={mutationPending}
                  >
                    执行这个时间窗口
                  </Button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      {isOperator ? (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="font-medium text-slate-950">手动处理</p>
          <p className="mt-2 text-sm text-slate-600">
            当前身份：{principal.api_key_label ?? principal.role}。所有正式变更都会进入统一操作记录。
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button onClick={() => submitMutation.mutate({ action: 'update_now' })} disabled={mutationPending}>立即更新数据</Button>
            <Button variant="outline" onClick={() => submitMutation.mutate({ action: 'recompute_indicators' })} disabled={mutationPending}>重算指标</Button>
            <Button variant="outline" onClick={() => submitMutation.mutate({ action: 'recompute_market_state' })} disabled={mutationPending}>重算市场状态</Button>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <label className="grid gap-1 text-sm text-slate-700">
              开始日期
              <input className="rounded-lg border border-slate-300 px-3 py-2" type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
            </label>
            <label className="grid gap-1 text-sm text-slate-700">
              结束日期
              <input className="rounded-lg border border-slate-300 px-3 py-2" type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
            </label>
          </div>
          <div className="mt-3">
            <Button
              variant="outline"
              disabled={mutationPending || !startDate || !endDate}
              onClick={() => submitMutation.mutate({ action: 'backfill', start_date: startDate, end_date: endDate })}
            >
              回灌历史数据
            </Button>
          </div>
        </div>
      ) : null}

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <p className="font-medium text-slate-950">最近处理记录</p>
        {operationsQuery.isLoading && !operations.length ? (
          <div className="mt-3">
            <LoadingState label="正在加载处理记录" description="稍后会显示最近的数据更新、补齐和重算操作。" />
          </div>
        ) : operations.length ? (
          <div className="mt-3 space-y-3">
            {operations.map((item) => (
              <div key={item.operation_id} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">{item.label}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      状态：{statusLabel(item.status)} · 目标交易日：{item.target_trade_date ?? '未指定'}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">更新时间：{formatTime(item.updated_at)}</p>
                  </div>
                  {isOperator ? (
                    <div className="flex flex-wrap gap-2">
                      {item.status === 'running' || item.status === 'pending' ? (
                        <Button variant="outline" onClick={() => cancelMutation.mutate({ operationId: item.operation_id, reason: 'operator requested' })} disabled={mutationPending}>
                          取消
                        </Button>
                      ) : null}
                      {item.status === 'failed' ? (
                        <Button variant="outline" onClick={() => retryMutation.mutate({ operationId: item.operation_id })} disabled={mutationPending}>
                          重试
                        </Button>
                      ) : null}
                      {item.status === 'cancelled' ? (
                        <Button variant="outline" onClick={() => resumeMutation.mutate({ operationId: item.operation_id })} disabled={mutationPending}>
                          继续执行
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-600">最近还没有正式处理记录。</p>
        )}
        {feedback ? <p className="mt-3 text-sm text-sky-700">{feedback}</p> : null}
      </div>
    </div>
  );
}

function SystemRunsSummary() {
  const { canAccess } = useAuth();
  const showDiagnostics = canAccess('operator');
  const query = useQuery({
    queryKey: ['formal-system', 'run-traces'],
    queryFn: () => listSystemRunTraces(10),
    staleTime: 15_000,
  });

  if (query.isLoading) {
    return <LoadingState label="正在加载运行状态" description="正在整理正式运行记录、步骤状态和修复建议。" />;
  }
  if (query.error || !query.data) {
    return <p>运行状态暂不可用，请稍后重试。</p>;
  }
  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-sm text-slate-600">最近正式运行</p>
          <p className="mt-2 font-medium text-slate-950">{query.data.count} 项</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-sm text-slate-600">仍需处理</p>
          <p className="mt-2 font-medium text-slate-950">
            {query.data.items.filter((item) => item.status !== 'ready').length} 项
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-sm text-slate-600">可直接继续</p>
          <p className="mt-2 font-medium text-slate-950">
            {query.data.items.filter((item) => item.status === 'ready').length} 项
          </p>
        </div>
      </div>
      {query.data.items.length ? (
        <div className="space-y-3">
          {query.data.items.map((item) => (
            <RunTraceCard key={item.run_id} item={item} showDiagnostics={showDiagnostics} />
          ))}
        </div>
      ) : (
        <EmptyState title="暂无正式运行记录" description="当前还没有可展示的正式运行追踪。" />
      )}
    </div>
  );
}

function formatTraceStatus(status: string) {
  const labels: Record<string, string> = {
    ready: '已完成',
    partial: '部分可用',
    unavailable: '暂不可用',
    error: '执行失败',
  };
  return labels[status] ?? status;
}

function renderSimpleValue(value: unknown) {
  if (value == null) return '未记录';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return JSON.stringify(value);
}

function RunTraceCard({ item, showDiagnostics }: { item: SystemRunTraceItem; showDiagnostics: boolean }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-950">{item.business_label}</p>
          <p className="mt-1 text-sm text-slate-600">
            状态：{formatTraceStatus(item.status)} · 开始时间：{formatTime(item.started_at)}
          </p>
        </div>
        <Link className="text-sm font-medium text-slate-700 hover:text-slate-950" to={item.next_action.target_path}>
          {item.next_action.label}
        </Link>
      </div>
      <div className="mt-3 space-y-2 text-sm text-slate-700">
        <div><span className="font-medium text-slate-900">发生了什么：</span>{item.happened}</div>
        <div><span className="font-medium text-slate-900">影响：</span>{item.affected}</div>
        <div><span className="font-medium text-slate-900">处理方式：</span>{item.repair_guidance}</div>
      </div>
      {item.steps.length ? (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="font-medium text-slate-900">关键步骤</p>
          <div className="mt-2 space-y-2">
            {item.steps.map((step) => (
              <div key={step.step_id} className="rounded-lg border border-slate-200 bg-white p-3">
                <p className="font-medium text-slate-900">{step.business_label}</p>
                <p className="mt-1 text-sm text-slate-600">
                  状态：{formatTraceStatus(step.status)} · 重试次数：{step.retry_count ?? '未记录'}
                </p>
                <p className="mt-1 text-sm text-slate-600">修复建议：{step.repair_guidance}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {showDiagnostics && item.admin_diagnostics ? (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="font-medium text-slate-900">查看运维诊断详情</p>
          <p className="mt-1 text-sm text-slate-600">技术状态：{formatTraceStatus(item.admin_diagnostics.technical_status)}</p>
          {item.admin_diagnostics.linked_ids ? (
            <div className="mt-2 space-y-1 text-sm text-slate-700">
              {Object.entries(item.admin_diagnostics.linked_ids).map(([key, values]) => (
                <div key={key}>
                  <span className="font-medium text-slate-900">{key}：</span>
                  {values.join('、')}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      {showDiagnostics && item.prompt_calls.length ? (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="font-medium text-slate-900">Prompt 调用</p>
          <div className="mt-2 space-y-2">
            {item.prompt_calls.map((call) => (
              <div key={`${call.run_id}-${call.prompt_version}`} className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
                <p className="font-medium text-slate-900">{call.provider ?? '未记录'} / {call.model}</p>
                <p className="mt-1">Prompt 版本：{call.prompt_version}</p>
                <p className="mt-1">Schema 版本：{call.schema_version}</p>
                <p className="mt-1">校验状态：{call.validation_state}</p>
                <p className="mt-1">Token：{renderSimpleValue(call.tokens.total_tokens)}</p>
                <p className="mt-1">成本：{call.cost.amount ?? '未记录'} {call.cost.currency ?? ''}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {showDiagnostics && item.data_fetches.length ? (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="font-medium text-slate-900">数据抓取</p>
          <div className="mt-2 space-y-2">
            {item.data_fetches.map((fetch, index) => (
              <div key={`${fetch.source}-${index}`} className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
                <p className="font-medium text-slate-900">{fetch.source}</p>
                <p className="mt-1">来源提供方：{fetch.provider ?? '未记录'}</p>
                <p className="mt-1">日期范围：{fetch.date_range.date_from ?? '未记录'} - {fetch.date_range.date_to ?? '未记录'}</p>
                <p className="mt-1">可用时间：{formatTime(fetch.available_at)}</p>
                <p className="mt-1">覆盖率：{renderSimpleValue(fetch.coverage)}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      {showDiagnostics && item.backtests.length ? (
        <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="font-medium text-slate-900">正式回测证据</p>
          <div className="mt-2 space-y-2">
            {item.backtests.map((backtest) => (
              <div key={backtest.dataset_snapshot_id} className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-700">
                <p className="font-medium text-slate-900">数据快照：{backtest.dataset_snapshot_id}</p>
                <p className="mt-1">规则版本：{backtest.rule_version.rule_version_id ?? '未记录'} / v{backtest.rule_version.rule_version_no ?? '未记录'}</p>
                <p className="mt-1">规则指纹：{backtest.rule_version.rule_version_fingerprint ?? '未记录'}</p>
                <p className="mt-1">市场状态模型版本：{backtest.market_state_model_version ?? '未记录'}</p>
                <p className="mt-1">代码版本：{backtest.code_version}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function SystemPage() {
  return <SystemHubPage />;
}

type FormalSystemPageProps = {
  availability?: PageAvailability;
};

export function SystemStatusPage({ availability }: FormalSystemPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="系统状态"
      queryState={state}
      purpose="查看服务和关键依赖是否能够支持当前业务操作。"
      inputDescription="本页无需输入，状态来自现有系统检查。"
      processingDescription="系统读取真实检查结果，不隐藏失败或缺失项。"
      outputDescription="输出为当前可用性、影响范围和建议处理动作。"
      businessAction={{ label: '查看配置管理', to: '/system/configuration' }}
      result={availability ? undefined : <SystemStatusPanel productMode />}
    />
  );
}

export function SystemConfigurationPage({ availability }: FormalSystemPageProps = {}) {
  const state = availability ?? 'partial';
  return (
    <ProductPageAdapter
      title="配置管理"
      queryState={state}
      purpose="维护业务运行所需的受控配置。"
      inputDescription="输入来自现有配置记录和已保存版本。"
      processingDescription="正式业务化配置界面仍在迁移，现有配置能力继续保留。"
      outputDescription="输出为现有配置记录；内部文件和路径不在正式页面展示。"
      businessAction={{ label: '查看现有配置', to: '/profiles' }}
      result={availability ? undefined : <SystemConfigurationSummary />}
    />
  );
}

export function SystemDataPage({ availability }: FormalSystemPageProps = {}) {
  const readinessQuery = useQuery({
    queryKey: ['formal-system', 'data-readiness', 'page-shell'],
    queryFn: getSystemDataReadiness,
    staleTime: 15_000,
    enabled: availability == null,
  });

  let state: PageAvailability = availability ?? 'loading';
  let stateTitle: string | undefined;
  let stateDescription: string | undefined;
  let impact: string | undefined;
  let recoveryAction: { label: string; onClick: () => void } | undefined;

  if (availability == null) {
    if (readinessQuery.isLoading && !readinessQuery.data) {
      state = 'loading';
      stateTitle = '正在检查就绪状态';
      stateDescription = '系统正在读取正式数据事实与最近操作状态。';
    } else if (readinessQuery.error instanceof ApiError && readinessQuery.error.status === 403) {
      state = 'permission_denied';
      stateTitle = '无权限查看数据与调度';
      stateDescription = '当前账号无法查看就绪状态和处理记录。';
    } else if (readinessQuery.error) {
      state = 'error';
      stateTitle = '数据与调度状态加载失败';
      stateDescription = '暂时无法读取正式就绪状态。';
    } else if (readinessQuery.data) {
      state = mapReadinessAvailability(readinessQuery.data.status);
      stateTitle = statusLabel(readinessQuery.data.status);
      stateDescription = readinessQuery.data.summary;
      impact = readinessImpact(readinessQuery.data.status);
      recoveryAction = readinessQuery.data.repair_available
        ? { label: '刷新当前状态', onClick: () => { void readinessQuery.refetch(); } }
        : undefined;
    } else {
      state = 'empty';
    }
  }

  return (
    <ProductPageAdapter
      title="数据与调度"
      queryState={state}
      purpose="查看正式数据是否就绪，并在需要时按最小范围补齐、回灌和重算。"
      inputDescription="输入包括当前交易日、历史日期范围和操作员选择的正式处理动作。"
      processingDescription="系统基于正式数据事实判断就绪状态，并通过统一门面协调更新、补齐、回灌和重算。"
      outputDescription="输出包括就绪状态、缺失影响、业务时间窗口、最近处理记录和下一步可执行动作。"
      businessAction={{ label: '返回系统状态', to: '/system/status' }}
      stateTitle={stateTitle}
      stateDescription={stateDescription}
      impact={impact}
      recoveryAction={recoveryAction}
      result={availability ? undefined : <SystemDataSummary />}
    />
  );
}

export function SystemRunsPage({ availability }: FormalSystemPageProps = {}) {
  const query = useQuery({
    queryKey: ['formal-system', 'run-traces', 'page-shell'],
    queryFn: () => listSystemRunTraces(10),
    staleTime: 15_000,
    enabled: availability == null,
  });

  let state: PageAvailability = availability ?? 'loading';
  let stateTitle: string | undefined;
  let stateDescription: string | undefined;
  let impact: string | undefined;

  if (availability == null) {
    if (query.isLoading && !query.data) {
      state = 'loading';
      stateTitle = '正在整理正式运行记录';
      stateDescription = '系统正在聚合步骤状态、错误影响和修复建议。';
    } else if (query.error) {
      state = 'error';
      stateTitle = '运行追踪暂不可用';
      stateDescription = '当前无法读取正式运行追踪信息。';
      impact = '普通用户暂时只能依赖业务页状态，管理员无法在本页查看详细运行链路。';
    } else if (query.data && query.data.items.length === 0) {
      state = 'empty';
      stateTitle = '暂无正式运行记录';
      stateDescription = '当前还没有可展示的正式运行追踪。';
      impact = '不会展示虚假的成功状态。';
    } else if (query.data) {
      const hasProblem = query.data.items.some((item) => item.status !== 'ready');
      state = hasProblem ? 'partial' : 'ready';
      stateTitle = hasProblem ? '存在待处理运行' : '正式运行状态已就绪';
      stateDescription = hasProblem
        ? '部分运行仍需继续处理或补齐输入。'
        : '最近正式运行已完整记录，可继续查看业务结果。';
      impact = hasProblem
        ? '普通用户会看到真实影响和下一步，管理员可继续查看诊断详情。'
        : '当前可继续查看对应业务结果。';
    }
  }

  return (
    <ProductPageAdapter
      title="运行与告警"
      queryState={state}
      purpose="查看业务处理状态、失败影响和恢复建议。"
      inputDescription="输入来自正式业务运行记录、Prompt 调用、数据快照和回测证据。"
      processingDescription="系统会聚合正式运行状态、步骤、依赖和修复建议，并对普通用户与管理员分层展示。"
      outputDescription="输出包括业务状态、下一步动作；管理员还可查看运行步骤、关联记录和诊断细节。"
      businessAction={{ label: '返回系统状态', to: '/system/status' }}
      stateTitle={stateTitle}
      stateDescription={stateDescription}
      impact={impact}
      result={availability ? undefined : <SystemRunsSummary />}
    />
  );
}
