import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import type { PageAvailability } from '@/components/layout/business-page-shell';
import { StatusBadge } from '@/components/kit';
import { getDailyRuleSelection, getPreMarketReadiness } from '@/lib/api/daily';
import { listBenchmarkOptions } from '@/lib/api/market';
import { listJobs } from '@/lib/api/jobs';
import { listProfiles } from '@/lib/api/profiles';
import { ApiError } from '@/lib/api/http';
import { formatLocalDateInputOffset } from '@/lib/date';
import type { DailyRuleDecision, DailyRuleSelectionResponse, PreMarketCheck, PreMarketReadinessResponse } from '@/types/daily';
import { describeStrategyWorkspaceJobType, formatWorkspaceTimestamp, isWorkspacePermissionDenied } from '@/features/strategy-workspace/strategy-workspace-utils';
import { StrategyAfterClosePage as StrategyAfterCloseWorkspacePage } from '@/features/strategy-workspace';

function TodaySummaryCard({
  title,
  latestJobType,
  latestStatus,
  latestTime,
  summary,
  to,
}: {
  title: string;
  latestJobType: string;
  latestStatus: string | null;
  latestTime: string | null;
  summary: string;
  to: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {latestStatus ? <StatusBadge value={latestStatus} /> : <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200">暂无记录</span>}
        <span className="text-sm text-slate-600">{latestTime ? formatWorkspaceTimestamp(latestTime) : '暂无最近结果'}</span>
      </div>
      <p className="mt-2 text-sm font-medium text-slate-950">{describeStrategyWorkspaceJobType(latestJobType)}</p>
      <p className="mt-2 text-sm leading-6 text-slate-700">{summary}</p>
      <div className="mt-4">
        <Link className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-100" to={to}>
          查看详情
        </Link>
      </div>
    </div>
  );
}

export function TodayOverviewPage({ availability }: { availability?: PageAvailability } = {}) {
  if (availability) {
    return (
      <ProductPageAdapter
        title="今日总览"
        queryState={availability}
        purpose="汇总今天的盘前和盘后状态。"
        inputDescription="需要当前可用画像、执行日期和基准指数。"
        processingDescription="系统读取真实盘前与盘后状态。"
        outputDescription="输出今日状态和下一步入口。"
        businessAction={{ label: '查看今日盘前', to: '/daily/pre-market' }}
      />
    );
  }
  const profilesQuery = useQuery({
    queryKey: ['daily-overview', 'profiles'],
    queryFn: () => listProfiles({ skip: 0, limit: 50 }),
    staleTime: 30_000,
  });

  const benchmarkOptionsQuery = useQuery({
    queryKey: ['daily-overview', 'benchmark-options'],
    queryFn: () => listBenchmarkOptions(50),
    staleTime: 30_000,
  });

  const preMarketJobsQuery = useQuery({
    queryKey: ['daily-overview', 'pre-market-jobs'],
    queryFn: () => listJobs({ job_type: 'run-pre-market', limit: 1 }),
    staleTime: 15_000,
  });

  const afterCloseJobsQuery = useQuery({
    queryKey: ['daily-overview', 'after-close-jobs'],
    queryFn: () => listJobs({ job_type: 'run-after-close', limit: 1 }),
    staleTime: 15_000,
  });

  const loading = profilesQuery.isLoading || benchmarkOptionsQuery.isLoading || preMarketJobsQuery.isLoading || afterCloseJobsQuery.isLoading;
  const error = profilesQuery.error ?? preMarketJobsQuery.error ?? afterCloseJobsQuery.error;
  const permissionDenied = isWorkspacePermissionDenied(error);
  const hasProfiles = (profilesQuery.data?.items ?? []).length > 0;
  const benchmarkOptions = benchmarkOptionsQuery.data?.items ?? [];
  const hasBenchmarkOptions = benchmarkOptions.length > 0;
  const queryState = loading
    ? 'loading'
    : permissionDenied
      ? 'permission_denied'
        : error
          ? 'error'
          : benchmarkOptionsQuery.error
            ? 'partial'
          : !hasProfiles
            ? 'empty'
            : !hasBenchmarkOptions
              ? 'unavailable'
            : 'ready';

  const profileNames = useMemo(() => (profilesQuery.data?.items ?? []).map((profile) => profile.name), [profilesQuery.data?.items]);
  const currentProfiles = profileNames.length ? profileNames.join('、') : '暂无可用画像';
  const currentBenchmark = benchmarkOptionsQuery.error
    ? '默认基准，其他选项暂不可用'
    : benchmarkOptions.find((item) => item.symbol === '000300.SH')?.name
      ?? benchmarkOptions[0]?.name
      ?? '暂无可用基准';
  const latestPreMarketJob = preMarketJobsQuery.data?.items?.[0] ?? null;
  const latestAfterCloseJob = afterCloseJobsQuery.data?.items?.[0] ?? null;

  return (
    <ProductPageAdapter
      title="今日总览"
      queryState={queryState}
      purpose="汇总今天的盘前和盘后状态，帮助你快速进入下一步。"
      inputDescription="需要当前可用画像、执行日期和基准指数。"
      processingDescription="系统会检查今天可用的数据，并保留盘前与盘后的最新进展。"
      outputDescription="输出今日盘前、今日盘后和下一步入口。"
      businessAction={{ label: '查看今日盘前', to: '/daily/pre-market' }}
      stateTitle={benchmarkOptionsQuery.error ? '部分完成' : undefined}
      stateDescription={benchmarkOptionsQuery.error ? '基准指数选项暂时缺失，页面已回退到默认基准。' : undefined}
      impact={benchmarkOptionsQuery.error ? '你仍可查看今日总览，但部分基准选项暂时不可见。' : undefined}
      recoveryAction={
        benchmarkOptionsQuery.error || queryState !== 'ready'
          ? { label: '返回今日盘前', to: '/daily/pre-market' }
          : undefined
      }
      input={
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">可用画像</p>
            <p className="mt-2 text-sm font-medium text-slate-950">{currentProfiles}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">执行日期</p>
            <p className="mt-2 text-sm font-medium text-slate-950">{new Date().toLocaleDateString('zh-CN')}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">基准指数</p>
            <p className="mt-2 text-sm font-medium text-slate-950">{currentBenchmark}</p>
          </div>
        </div>
      }
      result={
        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2">
            <TodaySummaryCard
              title="今日盘前"
              latestJobType={latestPreMarketJob?.job_type ?? 'run-pre-market'}
              latestStatus={latestPreMarketJob?.status ?? null}
              latestTime={latestPreMarketJob?.created_at ?? null}
              summary={latestPreMarketJob ? '盘前分析已保留最近进展，可继续进入正式盘前页。' : '今天的盘前分析还没有最新结果。'}
              to="/daily/pre-market"
            />
            <TodaySummaryCard
              title="今日盘后"
              latestJobType={latestAfterCloseJob?.job_type ?? 'run-after-close'}
              latestStatus={latestAfterCloseJob?.status ?? null}
              latestTime={latestAfterCloseJob?.created_at ?? null}
              summary={latestAfterCloseJob ? '盘后复盘已保留最近进展，可继续进入正式盘后页。' : '今天的盘后复盘还没有最新结果。'}
              to="/daily/after-close"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <Link className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50" to="/daily/pre-market">
              查看今日盘前
            </Link>
            <Link className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 transition-colors hover:bg-slate-50" to="/daily/after-close">
              查看今日盘后
            </Link>
          </div>
        </div>
      }
    />
  );
}

export function TodayPreMarketPage({ availability }: { availability?: PageAvailability } = {}) {
  if (availability) {
    return (
      <ProductPageAdapter
        title="今日盘前"
        queryState={availability}
        purpose="先确认今天是否具备正式盘前输入，再决定是否继续后续流程。"
        inputDescription="需要交易日以及正式盘前检查依赖。"
        processingDescription="系统读取正式策略、快照、市场状态和规则适用性。"
        outputDescription="输出今天的盘前就绪状态、影响和修复入口。"
        businessAction={{ label: '返回今日总览', to: '/daily/overview' }}
      />
    );
  }

  const tradeDate = useMemo(() => formatLocalDateInputOffset(0), []);
  const readinessQuery = useQuery({
    queryKey: ['daily-pre-market-readiness', tradeDate],
    queryFn: () => getPreMarketReadiness(tradeDate),
    staleTime: 15_000,
  });

  const permissionDenied = readinessQuery.error instanceof ApiError && (readinessQuery.error.status === 401 || readinessQuery.error.status === 403);
  const response = readinessQuery.data;
  const queryState: PageAvailability = readinessQuery.isLoading
    ? 'loading'
    : permissionDenied
      ? 'permission_denied'
      : readinessQuery.error
        ? 'error'
        : response?.state ?? 'empty';

  const primaryRepairAction = response?.repair_actions?.[0];
  const stateDescription = queryState === 'error'
    ? '读取正式盘前检查时发生错误。'
    : response?.happened;
  const impact = queryState === 'error'
    ? '当前无法确认今天是否可以继续正式盘前流程。'
    : response?.affected;

  return (
    <ProductPageAdapter
      title="今日盘前"
      queryState={queryState}
      purpose="先确认今天是否具备正式盘前输入，再决定是否继续后续流程。"
      inputDescription="需要交易日，以及正式策略、历史行情、盘前市场快照、当前市场状态、规则适用性和作者验证画像。"
      processingDescription="系统只读取 canonical DatasetSnapshot、MarketSnapshot、市场状态、正式策略和画像绑定，检查今天是否就绪。"
      outputDescription="输出 ready / degraded / blocked 的盘前检查结果、影响说明和修复入口。"
      businessAction={{ label: '返回今日总览', to: '/daily/overview' }}
      currentStep="先完成正式盘前前置检查，再决定是否进入下一步。"
      stateTitle={queryState === 'error' ? '出现问题' : response?.summary_title}
      stateDescription={stateDescription}
      impact={impact}
      recoveryAction={primaryRepairAction}
      input={
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">交易日</p>
            <p className="mt-2 text-sm font-medium text-slate-950">{tradeDate}</p>
          </div>
          <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">盘前时段</p>
            <p className="mt-2 text-sm font-medium text-slate-950">{response?.slot ?? '09-25'}</p>
          </div>
        </div>
      }
      result={response ? <PreMarketReadinessResult response={response} /> : undefined}
      help={
        response ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            {response.can_proceed
              ? response.can_proceed_in_degraded_mode
                ? '可按降级模式继续后续流程。'
                : '可以继续正式盘前流程。'
              : '当前不能继续后续流程。'}
          </div>
        ) : undefined
      }
    />
  );
}

export function TodayAfterClosePage({ availability }: { availability?: PageAvailability } = {}) {
  if (availability) {
    return (
      <ProductPageAdapter
        title="今日盘后"
        queryState={availability}
        purpose="复盘今日执行结果。"
        inputDescription="需要画像和复盘日期。"
        processingDescription="系统读取真实盘后处理状态。"
        outputDescription="输出当前可确认的盘后结果。"
        businessAction={{ label: '返回今日总览', to: '/daily/overview' }}
      />
    );
  }
  return <StrategyAfterCloseWorkspacePage productMode navigationTarget="/daily" />;
}

export const DailyOverviewPage = TodayOverviewPage;
export const DailyPreMarketPage = TodayPreMarketPage;
export const DailyAfterClosePage = TodayAfterClosePage;

function formatTraceabilityValue(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return '未绑定';
  }
  if (Array.isArray(value)) {
    return value.length ? value.join('、') : '未绑定';
  }
  return String(value);
}

function PreMarketCheckCard({ item }: { item: PreMarketCheck }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="m-0 text-sm font-medium text-slate-950">{item.label}</p>
          <p className="mt-1 text-sm text-slate-700">{item.happened}</p>
        </div>
        <StatusBadge value={item.status} />
      </div>
      <div className="mt-3 grid gap-2 text-sm text-slate-700">
        <div>
          <span className="font-medium text-slate-900">影响：</span>
          {item.affected}
        </div>
        <div>
          <span className="font-medium text-slate-900">处理方式：</span>
          {item.repair_guidance}
        </div>
        {item.status === 'degraded' ? <div>可按降级模式继续。</div> : null}
      </div>
      <div className="mt-3 grid gap-2 border-t border-slate-100 pt-3 text-xs text-slate-600">
        {Object.entries(item.traceability).map(([key, value]) => (
          <div key={key} className="grid gap-1 md:grid-cols-[9rem,1fr]">
            <span className="font-medium text-slate-700">{key}</span>
            <span className="break-all">{formatTraceabilityValue(value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function PreMarketReadinessResult({ response }: { response: PreMarketReadinessResponse }) {
  const selectionQuery = useQuery({
    queryKey: ['daily-rule-selection', response.trade_date],
    queryFn: () => getDailyRuleSelection(response.trade_date),
    staleTime: 15_000,
    enabled: response.can_proceed,
  });

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge value={response.readiness_status} />
          <span className="text-sm font-medium text-slate-950">{response.summary_title}</span>
        </div>
        <p className="mt-3 text-sm text-slate-700">{response.happened}</p>
        <div className="mt-3 grid gap-2 text-sm text-slate-700">
          <div>
            <span className="font-medium text-slate-900">影响：</span>
            {response.affected}
          </div>
          <div>
            <span className="font-medium text-slate-900">处理方式：</span>
            {response.repair_guidance}
          </div>
          <div>
            <span className="font-medium text-slate-900">是否可继续：</span>
            {response.can_proceed
              ? response.can_proceed_in_degraded_mode
                ? '可按降级模式继续后续流程。'
                : '可以继续正式盘前流程。'
              : '当前不能继续后续流程。'}
          </div>
        </div>
      </div>

      <div className="grid gap-3">
        {response.checks.map((item) => (
          <PreMarketCheckCard key={item.code} item={item} />
        ))}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-sm font-medium text-slate-950">本次绑定的正式输入</p>
        <div className="mt-3 grid gap-2 text-xs text-slate-600">
          {Object.entries(response.traceability).map(([key, value]) => (
            <div key={key} className="grid gap-1 md:grid-cols-[12rem,1fr]">
              <span className="font-medium text-slate-700">{key}</span>
              <span className="break-all">{formatTraceabilityValue(value)}</span>
            </div>
          ))}
        </div>
      </div>

      <DailyRuleSelectionPanel readiness={response} selection={selectionQuery.data} loading={selectionQuery.isLoading} error={selectionQuery.error} />
    </div>
  );
}

function DailyRuleSelectionPanel({
  readiness,
  selection,
  loading,
  error,
}: {
  readiness: PreMarketReadinessResponse;
  selection?: DailyRuleSelectionResponse;
  loading: boolean;
  error: unknown;
}) {
  if (!readiness.can_proceed) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-sm font-medium text-slate-950">今日规则选择</p>
        <p className="mt-3 text-sm text-slate-700">正式盘前检查还没有通过，当前不生成每日规则选择。</p>
      </div>
    );
  }
  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-sm font-medium text-slate-950">今日规则选择</p>
        <p className="mt-3 text-sm text-slate-700">正在生成今日规则选择。</p>
      </div>
    );
  }
  if (error || !selection) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <p className="text-sm font-medium text-slate-950">今日规则选择</p>
        <p className="mt-3 text-sm text-slate-700">读取今日规则选择时发生错误。</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-950">今日规则选择</p>
          <p className="mt-2 text-sm text-slate-700">{selection.happened}</p>
        </div>
        <StatusBadge value={selection.selection_status} />
      </div>
      <div className="grid gap-2 text-sm text-slate-700">
        <div>
          <span className="font-medium text-slate-900">影响：</span>
          {selection.affected}
        </div>
        <div>
          <span className="font-medium text-slate-900">处理方式：</span>
          {selection.repair_guidance}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <DailyRuleDecisionColumn title="启用规则" items={selection.enabled_rules} />
        <DailyRuleDecisionColumn title="降权规则" items={selection.reduced_rules} />
        <DailyRuleDecisionColumn title="暂停规则" items={selection.suspended_rules} />
      </div>
    </div>
  );
}

function DailyRuleDecisionColumn({ title, items }: { title: string; items: DailyRuleDecision[] }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-sm font-medium text-slate-950">{title}</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <div key={`${title}-${item.rule_version_id}`} className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="m-0 text-sm font-medium text-slate-950">{item.rule_version_id}</p>
                <StatusBadge value={item.decision} />
              </div>
              <p className="mt-2 text-sm text-slate-700">{item.controlling_priority_label}</p>
              <div className="mt-2 grid gap-1 text-xs text-slate-600">
                {item.reason_list.map((reason) => (
                  <div key={`${item.rule_version_id}-${reason}`}>{reason}</div>
                ))}
                {item.degraded_inputs.length ? <div>降级输入：{item.degraded_inputs.join('、')}</div> : null}
                {item.unresolved_inputs.length ? <div>未解决输入：{item.unresolved_inputs.join('、')}</div> : null}
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white px-3 py-4 text-sm text-slate-600">当前没有规则。</div>
        )}
      </div>
    </div>
  );
}
