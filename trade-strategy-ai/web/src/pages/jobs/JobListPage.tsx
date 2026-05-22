import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
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
import { listJobs } from '@/lib/api/jobs';
import type { JobsListResponse } from '@/types/jobs';
import { JobTable } from '@/components/jobs/JobTable';

const PAGE_SIZE = 20;

export function JobListPage() {
  const navigate = useNavigate();
  const { canAccess, isAuthenticated, principal } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const status = searchParams.get('status') ?? '';
  const jobType = searchParams.get('job_type') ?? '';
  const createdBy = searchParams.get('created_by') ?? '';
  const pageParam = Number.parseInt(searchParams.get('page') ?? '1', 10);
  const page = Number.isFinite(pageParam) && pageParam > 0 ? pageParam - 1 : 0;

  const canViewJobs = isAuthenticated && canAccess('viewer');

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
  });

  const jobs = jobsQuery.data?.items ?? [];
  const total = jobsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.min(page + 1, totalPages);

  const summary = useMemo(() => {
    const running = jobs.filter((item) => item.status === 'running').length;
    const failed = jobs.filter((item) => item.status === 'failed').length;
    return { running, failed };
  }, [jobs]);

  if (!canViewJobs) {
    return (
      <main className="page-stack">
        <PageHeader kicker="任务" title="任务列表" description="查看系统中已记录的任务执行历史。" />
        <section className="page-card">
          <p className="text-lg font-semibold text-slate-900">没有权限访问任务列表</p>
          <p className="mt-2 text-sm text-slate-600">当前身份为 {principal.role}，查看任务列表至少需要 viewer 权限。</p>
        </section>
      </main>
    );
  }

  return (
    <main className="page-stack">
      {/* <PageHeader
        kicker="任务"
        title="任务列表"
        description="查看最近的任务记录，按状态、任务类型和创建者筛选，并跳转到任务详情。"
      /> */}

      <section className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>最近任务</CardTitle>
                <CardDescription>按状态、任务类型和创建者筛选。</CardDescription>
              </div>
              <Button variant="outline" onClick={() => jobsQuery.refetch()} disabled={jobsQuery.isFetching}>
                {jobsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
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
              <Input
                placeholder="按任务类型过滤"
                value={jobType}
                onChange={(event) => {
                  updateFilters({ jobType: event.target.value, page: 0 });
                }}
              />
              <Select
                value={status}
                onChange={(event) => {
                  updateFilters({ status: event.target.value, page: 0 });
                }}
              >
                <option value="">所有状态</option>
                <option value="pending">等待中</option>
                <option value="running">运行中</option>
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
              <JobTable jobs={jobs} onViewDetail={(jobId) => navigate(`/jobs/${encodeURIComponent(jobId)}`)} />
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
