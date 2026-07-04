import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { PageHeader } from '@/components/layout/page-header';
import { ErrorState } from '@/components/state/ErrorState';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { cancelJob, listJobDefinitions, listJobs, pauseJob, retryJob, resumeJob } from '@/lib/api/jobs';
import type { JobDefinitionSummary, JobsListResponse } from '@/types/jobs';
import { JobTable } from '@/components/jobs/JobTable';

const PAGE_SIZE = 20;

export function JobListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { canAccess, isAuthenticated, principal } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const status = searchParams.get('status') ?? '';
  const jobType = searchParams.get('job_type') ?? '';
  const createdBy = searchParams.get('created_by') ?? '';
  const pageParam = Number.parseInt(searchParams.get('page') ?? '1', 10);
  const page = Number.isFinite(pageParam) && pageParam > 0 ? pageParam - 1 : 0;

  const canViewJobs = isAuthenticated && canAccess('viewer');

  const definitionsQuery = useQuery<JobDefinitionSummary[]>({
    queryKey: ['job-definitions'],
    queryFn: () => listJobDefinitions(),
    enabled: canViewJobs,
    staleTime: 60_000,
  });

  const jobDefinitionsByType = useMemo(() => {
    return Object.fromEntries((definitionsQuery.data ?? []).map((definition) => [definition.job_type, definition]));
  }, [definitionsQuery.data]);

  function updateFilters(next: { status?: string; jobType?: string; createdBy?: string; page?: number }) {
    const params = new URLSearchParams(searchParams);

    if (next.status !== undefined) {
      if (next.status) params.set('status', next.status);
      else params.delete('status');
    }

    if (next.jobType !== undefined) {
      if (next.jobType) params.set('job_type', next.jobType);
      else params.delete('job_type');
    }

    if (next.createdBy !== undefined) {
      if (next.createdBy) params.set('created_by', next.createdBy);
      else params.delete('created_by');
    }

    if (next.page !== undefined) {
      if (next.page > 0) params.set('page', String(next.page + 1));
      else params.delete('page');
    }

    setSearchParams(params, { replace: true });
  }

  const jobsQuery = useQuery<JobsListResponse, ApiError>({
    queryKey: ['jobs', { status, jobType, createdBy, page }],
    queryFn: () =>
      listJobs({
        status: status || undefined,
        job_type: jobType || undefined,
        created_by: createdBy || undefined,
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
    enabled: canViewJobs,
    staleTime: 10_000,
    refetchInterval: (query) => {
      const items = (query.state.data?.items ?? []) as Array<{ status?: string }>;
      return items.some((item) => item.status === 'running' || item.status === 'pending') ? 5000 : false;
    },
  });

  const jobs = jobsQuery.data?.items ?? [];
  const total = jobsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.min(page + 1, totalPages);
  const statusCounts = useMemo(() => {
    const fallback = {
      pending: 0,
      running: 0,
      paused: 0,
      success: 0,
      failed: 0,
      cancelled: 0,
    };
    const rawCounts = jobsQuery.data?.status_counts;
    if (rawCounts) {
      return {
        ...fallback,
        ...rawCounts,
      };
    }

    return jobs.reduce((acc, job) => {
      if (job.status in acc) {
        acc[job.status as keyof typeof acc] += 1;
      }
      return acc;
    }, { ...fallback });
  }, [jobs, jobsQuery.data?.status_counts]);

  const summary = useMemo(() => {
    const running = jobs.filter((item) => item.status === 'running').length;
    const failed = jobs.filter((item) => item.status === 'failed').length;
    return { running, failed };
  }, [jobs]);

  const invalidateJobs = async () => {
    await queryClient.invalidateQueries({ queryKey: ['jobs'] });
  };

  const pauseMutation = useMutation({
    mutationFn: (jobId: string) => pauseJob(jobId, 'web console request'),
    onSuccess: invalidateJobs,
  });

  const resumeMutation = useMutation({
    mutationFn: (jobId: string) => resumeJob(jobId),
    onSuccess: invalidateJobs,
  });

  const cancelMutation = useMutation({
    mutationFn: (jobId: string) => cancelJob(jobId, 'web console request'),
    onSuccess: invalidateJobs,
  });

  const retryMutation = useMutation({
    mutationFn: (jobId: string) => retryJob(jobId, 'web console request'),
    onSuccess: invalidateJobs,
  });

  if (!canViewJobs) {
    return (
      <main className="page-stack">
        <PageHeader kicker="系统任务" title="任务管理" description="统一查看后台任务状态、进度、日志、结果和可用操作。" />
        <section className="page-card">
          <p className="text-lg font-semibold text-slate-900">没有权限访问任务中心</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，查看任务中心至少需要 viewer 权限。</p>
        </section>
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="系统任务"
        title="任务管理"
        description="查看当前和历史任务，筛选状态、任务类型和创建者，并处理可暂停、可恢复、可取消或可重试的任务。"
      />

      <section className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>最近任务</CardTitle>
                <CardDescription>按状态、任务类型和创建者筛选。</CardDescription>
              </div>
              <div className="flex flex-wrap gap-2">
                {canAccess('operator') ? (
                  <Button onClick={() => navigate('/system/jobs/new')}>
                    新建任务
                  </Button>
                ) : null}
                <Button variant="outline" onClick={() => jobsQuery.refetch()} disabled={jobsQuery.isFetching}>
                  {jobsQuery.isFetching ? '刷新中' : '刷新'}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <Input
                placeholder="按创建者过滤"
                value={createdBy}
                onChange={(event) => {
                  updateFilters({ createdBy: event.target.value, page: 0 });
                }}
              />
              <Select
                aria-label="按任务类型过滤"
                value={jobType}
                onChange={(event) => {
                  updateFilters({ jobType: event.target.value, page: 0 });
                }}
              >
                <option value="">所有任务类型</option>
                {(definitionsQuery.data ?? []).map((definition) => (
                  <option key={definition.job_type} value={definition.job_type}>
                    {definition.title}
                  </option>
                ))}
              </Select>
              <Select
                value={status}
                onChange={(event) => {
                  updateFilters({ status: event.target.value, page: 0 });
                }}
              >
                <option value="">所有状态</option>
                <option value="pending">等待中</option>
                <option value="running">运行中</option>
                <option value="paused">已暂停</option>
                <option value="success">成功</option>
                <option value="failed">失败</option>
                <option value="cancelled">已取消</option>
              </Select>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">总计</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{total}</p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">当前页</p>
                <p className="mt-2 text-2xl font-semibold text-sky-700">
                  {currentPage} / {totalPages}
                </p>
              </div>
              <div className="rounded-xl border border-slate-200 bg-white p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">当前页运行中 / 失败</p>
                <p className="mt-2 text-2xl font-semibold text-rose-600">
                  {summary.running} / {summary.failed}
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-sm font-medium text-slate-900">状态分布</p>
                <p className="text-xs text-slate-500">统计范围：当前筛选条件下的全部任务。</p>
              </div>
              <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">待处理</p>
                  <p className="mt-2 text-2xl font-semibold text-amber-700">{statusCounts.pending ?? 0}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">运行中</p>
                  <p className="mt-2 text-2xl font-semibold text-sky-700">{statusCounts.running ?? 0}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">已暂停</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-700">{statusCounts.paused ?? 0}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">成功</p>
                  <p className="mt-2 text-2xl font-semibold text-emerald-700">{statusCounts.success ?? 0}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">失败</p>
                  <p className="mt-2 text-2xl font-semibold text-rose-600">{statusCounts.failed ?? 0}</p>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">已取消</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-700">{statusCounts.cancelled ?? 0}</p>
                </div>
              </div>
            </div>

            {jobsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
                <Skeleton className="h-14 w-full" />
              </div>
            ) : jobsQuery.error ? (
              <ErrorState
                {...buildErrorRecoveryState(jobsQuery.error, 'jobs')}
                onRetry={() => {
                  void jobsQuery.refetch();
                }}
              />
            ) : !jobs.length ? (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                暂无符合条件的任务。
              </div>
            ) : (
                <JobTable
                  jobs={jobs}
                  canOperate={canAccess('operator')}
                  jobDefinitionsByType={jobDefinitionsByType}
                  onViewDetail={(jobId) => navigate(`/system/jobs/${encodeURIComponent(jobId)}`)}
                  onPause={(jobId) => pauseMutation.mutate(jobId)}
                  onResume={(jobId) => resumeMutation.mutate(jobId)}
                  onCancel={(jobId) => cancelMutation.mutate(jobId)}
                  onRetry={(jobId) => retryMutation.mutate(jobId)}
                />
              )}

            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-slate-600">
                每页显示 {PAGE_SIZE} 条，当前第 {currentPage} 页，共 {total} 条。
              </p>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => updateFilters({ page: Math.max(0, page - 1) })} disabled={page === 0}>
                  上一页
                </Button>
                <Button
                  variant="outline"
                  onClick={() => updateFilters({ page: page + 1 })}
                  disabled={(page + 1) * PAGE_SIZE >= total}
                >
                  下一页
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
