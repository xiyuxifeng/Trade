import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
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
  const [status, setStatus] = useState('');
  const [jobType, setJobType] = useState('');
  const [createdBy, setCreatedBy] = useState('');
  const [page, setPage] = useState(0);

  const canViewJobs = isAuthenticated && canAccess('viewer');

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

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.6fr)]">
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
                  setPage(0);
                  setCreatedBy(event.target.value);
                }}
              />
              <Input
                placeholder="按任务类型过滤"
                value={jobType}
                onChange={(event) => {
                  setPage(0);
                  setJobType(event.target.value);
                }}
              />
              <Select
                value={status}
                onChange={(event) => {
                  setPage(0);
                  setStatus(event.target.value);
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
                <Button variant="outline" onClick={() => setPage((current) => Math.max(0, current - 1))} disabled={page === 0}>
                  上一页
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setPage((current) => current + 1)}
                  disabled={(page + 1) * PAGE_SIZE >= total}
                >
                  下一页
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>操作说明</CardTitle>
            <CardDescription>任务列表只负责查看和跳转，不承担执行逻辑。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-700">
            <ul className="list-disc space-y-2 pl-5 text-slate-600">
              <li>通过状态、任务类型和创建者过滤任务。</li>
              <li>点击“查看详情”进入任务详情查看日志、步骤、产物和配置快照。</li>
              <li>列表页不直接展示文件路径，也不修改任务状态。</li>
            </ul>
            {jobsQuery.error ? (
              <ErrorState
                {...buildErrorRecoveryState(jobsQuery.error, 'jobs')}
                className="mt-4"
                onRetry={() => {
                  void jobsQuery.refetch();
                }}
              />
            ) : null}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
