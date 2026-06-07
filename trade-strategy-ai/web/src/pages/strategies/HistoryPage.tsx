import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, LoadingState } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { listJobs } from '@/lib/api/jobs';
import { StrategyWorkspaceHistory } from '@/features/strategy-workspace';
import { isWorkspacePermissionDenied } from '@/features/strategy-workspace';
import type { JobRecord } from '@/types/jobs';
import { isStrategyWorkspaceJobType } from '@/features/strategy-workspace/strategy-workspace-utils';

function sortJobsByCreatedAtDesc(items: JobRecord[]) {
  return [...items].sort((left, right) => right.created_at.localeCompare(left.created_at));
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
  const [draftStatusFilter, setDraftStatusFilter] = useState(searchParams.get('status') ?? '');
  const [draftJobTypeFilter, setDraftJobTypeFilter] = useState(searchParams.get('job_type') ?? '');
  const [draftDateFrom, setDraftDateFrom] = useState(searchParams.get('date_from') ?? '');
  const [draftDateTo, setDraftDateTo] = useState(searchParams.get('date_to') ?? '');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') ?? '');
  const [jobTypeFilter, setJobTypeFilter] = useState(searchParams.get('job_type') ?? '');
  const [dateFrom, setDateFrom] = useState(searchParams.get('date_from') ?? '');
  const [dateTo, setDateTo] = useState(searchParams.get('date_to') ?? '');

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

  const handleSearch = () => {
    setStatusFilter(draftStatusFilter);
    setJobTypeFilter(draftJobTypeFilter);
    setDateFrom(draftDateFrom);
    setDateTo(draftDateTo);

    const next = new URLSearchParams();
    if (draftStatusFilter) next.set('status', draftStatusFilter);
    if (draftJobTypeFilter) next.set('job_type', draftJobTypeFilter);
    if (draftDateFrom) next.set('date_from', draftDateFrom);
    if (draftDateTo) next.set('date_to', draftDateTo);
    setSearchParams(next, { replace: true });
  };

  const handleReset = () => {
    setDraftStatusFilter('');
    setDraftJobTypeFilter('');
    setDraftDateFrom('');
    setDraftDateTo('');
    setStatusFilter('');
    setJobTypeFilter('');
    setDateFrom('');
    setDateTo('');
    setSearchParams(new URLSearchParams(), { replace: true });
  };

  if (jobsQuery.isLoading) {
      return (
        <main className="page-stack">
        <PageHeader
          kicker="兼容入口"
          title="运行历史"
          description="筛选兼容入口相关任务的运行历史，并跳转到任务详情查看日志、产物和重试。"
          actionLabel="返回兼容入口"
          onAction={() => navigate('/strategies')}
        />
        <LoadingState label="正在加载兼容入口历史" description="稍后会展示市场上下文准备、规则版本构建、盘前分析和盘后复盘任务。" />
      </main>
    );
  }

  if (queryError) {
      return (
        <main className="page-stack">
        <PageHeader
          kicker="兼容入口"
          title="运行历史"
          description="筛选兼容入口相关任务的运行历史，并跳转到任务详情查看日志、产物和重试。"
          actionLabel="返回兼容入口"
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
          kicker="兼容入口"
          title="运行历史"
          description="筛选兼容入口相关任务的运行历史，并跳转到任务详情查看日志、产物和重试。"
          actionLabel="返回兼容入口"
          onAction={() => navigate('/strategies')}
        />
        <EmptyState
          title="暂无兼容入口运行历史。"
          description="提交市场上下文准备、规则版本构建、盘前分析或盘后复盘后，这里会出现历史记录。"
          actionLabel="进入任务列表"
          onAction={() => navigate('/jobs')}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="兼容入口"
        title="运行历史"
        description="筛选兼容入口相关任务的运行历史，并跳转到任务详情查看日志、产物和重试。"
        actionLabel="返回兼容入口"
        onAction={() => navigate('/strategies')}
      />

      <section className="grid gap-4">
        <Card className="border-slate-200 bg-white shadow-sm">
          <CardHeader>
            <Badge variant="info" className="w-fit">
              筛选条件
            </Badge>
            <CardTitle className="mt-2 text-slate-950">按日期 / 状态 / 类型筛选</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">状态</span>
                <Select className="border-slate-200 bg-white text-slate-900" onChange={(event) => setDraftStatusFilter(event.target.value)} value={draftStatusFilter}>
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
                <Select className="border-slate-200 bg-white text-slate-900" onChange={(event) => setDraftJobTypeFilter(event.target.value)} value={draftJobTypeFilter}>
                  <option value="">全部</option>
                  <option value="snapshot-build">snapshot-build</option>
                  <option value="strategy-build">strategy-build</option>
                  <option value="run-pre-market">run-pre-market</option>
                  <option value="run-after-close">run-after-close</option>
                </Select>
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">开始日期</span>
                <Input className="border-slate-200 bg-white text-slate-900" onChange={(event) => setDraftDateFrom(event.target.value)} type="date" value={draftDateFrom} />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">结束日期</span>
                <Input className="border-slate-200 bg-white text-slate-900" onChange={(event) => setDraftDateTo(event.target.value)} type="date" value={draftDateTo} />
              </label>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={handleSearch} type="button">
                搜索
              </Button>
              <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={handleReset} type="button" variant="outline">
                重置
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-4">
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
