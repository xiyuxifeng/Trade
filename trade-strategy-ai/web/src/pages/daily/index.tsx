import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';

import { ProductPageAdapter } from '@/components/layout/product-page-adapter';
import type { PageAvailability } from '@/components/layout/business-page-shell';
import { StatusBadge } from '@/components/kit';
import { listBenchmarkOptions } from '@/lib/api/market';
import { listJobs } from '@/lib/api/jobs';
import { listProfiles } from '@/lib/api/profiles';
import { describeStrategyWorkspaceJobType, formatWorkspaceTimestamp, isWorkspacePermissionDenied } from '@/features/strategy-workspace/strategy-workspace-utils';
import { StrategyAfterClosePage as StrategyAfterCloseWorkspacePage, StrategyPreMarketPage as StrategyPreMarketWorkspacePage } from '@/features/strategy-workspace';

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
        purpose="整理并生成今日盘前分析。"
        inputDescription="需要画像、日期和基准指数。"
        processingDescription="系统读取真实盘前处理状态。"
        outputDescription="输出当前可确认的盘前结果。"
        businessAction={{ label: '返回今日总览', to: '/daily/overview' }}
      />
    );
  }
  return <StrategyPreMarketWorkspacePage productMode navigationTarget="/daily" />;
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
