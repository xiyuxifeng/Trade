import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, LoadingState } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { listJobs } from '@/lib/api/jobs';
import { StrategyWorkspaceHistory } from '@/features/strategy-workspace';
import { formatLocalDateInputOffset } from '@/lib/date';
import { isWorkspacePermissionDenied } from '@/features/strategy-workspace';
import type { JobRecord } from '@/types/jobs';
import { isStrategyWorkspaceJobType } from '@/features/strategy-workspace/strategy-workspace-utils';

function sortJobsByCreatedAtDesc(items: JobRecord[]) {
  return [...items].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function SummaryTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 break-all text-sm font-medium text-slate-950">{value}</p>
    </div>
  );
}

function isBetweenDates(value: string, dateFrom: string, dateTo: string) {
  if (!dateFrom && !dateTo) return true;
  const day = value.slice(0, 10);
  if (dateFrom && day < dateFrom) return false;
  if (dateTo && day > dateTo) return false;
  return true;
}

export function StrategyHistoryPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const today = useMemo(() => formatLocalDateInputOffset(0), []);
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') ?? '');
  const [jobTypeFilter, setJobTypeFilter] = useState(searchParams.get('job_type') ?? '');
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') ?? '');
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') ?? '');

  useEffect(() => {
    const next = new URLSearchParams();
    if (statusFilter) next.set('status', statusFilter);
    if (jobTypeFilter) next.set('job_type', jobTypeFilter);
    if (dateFrom) next.set('date_from', dateFrom);
    if (dateTo) next.set('date_to', dateTo);
    setSearchParams(next, { replace: true });
  }, [dateFrom, dateTo, jobTypeFilter, setSearchParams, statusFilter]);

  const jobsQuery = useQuery({
    queryKey: ['strategy-history-page', 'jobs'],
    queryFn: () => listJobs({ limit: 200 }),
    staleTime: 30_000,
  });

  const strategyJobs = useMemo(
    () => sortJobsByCreatedAtDesc((jobsQuery.data?.items ?? []).filter((job) => isStrategyWorkspaceJobType(job.job_type))),
    [jobsQuery.data?.items],
  );

  const filteredJobs = useMemo(
    () =>
      strategyJobs.filter((job) => {
        if (statusFilter && job.status !== statusFilter) return false;
        if (jobTypeFilter && job.job_type !== jobTypeFilter) return false;
        if (!isBetweenDates(job.created_at, dateFrom, dateTo)) return false;
        return true;
      }),
    [dateFrom, dateTo, jobTypeFilter, statusFilter, strategyJobs],
  );

  const queryError = jobsQuery.error;
  const permissionDenied = isWorkspacePermissionDenied(queryError);

  if (jobsQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="运行历史"
          description="筛选策略工作台相关 Job 的运行历史，并跳转到任务中心查看详情。"
          actionLabel="返回策略首页"
          onAction={() => navigate('/strategies')}
        />
        <LoadingState label="正在加载策略历史" description="稍后会展示策略构建、快照、盘前和盘后任务。" />
      </main>
    );
  }

  if (queryError) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="运行历史"
          description="筛选策略工作台相关 Job 的运行历史，并跳转到任务中心查看详情。"
          actionLabel="返回策略首页"
          onAction={() => navigate('/strategies')}
        />
        <ErrorState
          {...buildErrorRecoveryState(queryError, 'strategy')}
          onRetry={permissionDenied ? undefined : () => void jobsQuery.refetch()}
        />
      </main>
    );
  }

  if (strategyJobs.length === 0) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="运行历史"
          description="筛选策略工作台相关 Job 的运行历史，并跳转到任务中心查看详情。"
          actionLabel="返回策略首页"
          onAction={() => navigate('/strategies')}
        />
        <EmptyState
          title="暂无策略运行历史。"
          description="提交 snapshot-build、strategy-build、run-pre-market 或 run-after-close 后，这里会出现历史记录。"
          actionLabel="进入任务中心"
          onAction={() => navigate('/jobs')}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
        <PageHeader
          kicker="策略"
          title="运行历史"
          description="筛选策略工作台相关 Job 的运行历史，并跳转到任务中心查看详情。"
          actionLabel="返回策略首页"
          onAction={() => navigate('/strategies')}
        />

      <section className="grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              筛选器
            </Badge>
            <CardTitle className="mt-2 text-slate-950">按日期 / 状态 / 类型筛选</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">状态</span>
                <Select className="border-slate-200 bg-white text-slate-900" onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}>
                  <option value="">全部</option>
                  <option value="pending">pending</option>
                  <option value="running">running</option>
                  <option value="success">success</option>
                  <option value="failed">failed</option>
                  <option value="canceled">canceled</option>
                </Select>
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">类型</span>
                <Select className="border-slate-200 bg-white text-slate-900" onChange={(event) => setJobTypeFilter(event.target.value)} value={jobTypeFilter}>
                  <option value="">全部</option>
                  <option value="snapshot-build">snapshot-build</option>
                  <option value="strategy-build">strategy-build</option>
                  <option value="run-pre-market">run-pre-market</option>
                  <option value="run-after-close">run-after-close</option>
                </Select>
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">开始日期</span>
                <Input className="border-slate-200 bg-white text-slate-900" onChange={(event) => setDateFrom(event.target.value)} type="date" value={dateFrom} />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">结束日期</span>
                <Input className="border-slate-200 bg-white text-slate-900" onChange={(event) => setDateTo(event.target.value)} type="date" value={dateTo} />
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <SummaryTile label="历史记录" value={strategyJobs.length} />
              <SummaryTile label="筛选后" value={filteredJobs.length} />
              <SummaryTile label="默认日期" value={today} />
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-950">任务中心入口</p>
                <p className="mt-1 text-sm text-slate-600">历史记录详情、日志、产物和重试都在任务中心查看。</p>
              </div>
              <Link className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-sky-700 hover:bg-slate-50" to="/jobs">
                打开任务中心
              </Link>
            </div>
          </div>

          <StrategyWorkspaceHistory
            error={null}
            isLoading={false}
            jobs={filteredJobs}
            onRetry={() => void jobsQuery.refetch()}
          />
        </div>
      </section>
    </main>
  );
}
