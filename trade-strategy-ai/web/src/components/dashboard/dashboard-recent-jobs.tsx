import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useRecentJobs } from '@/features/jobs/use-recent-jobs';

function formatTimestamp(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function statusVariant(status: string) {
  if (status === 'success') return 'success';
  if (status === 'failed' || status === 'cancelled') return 'destructive';
  if (status === 'running' || status === 'pending') return 'warning';
  return 'default';
}

export function DashboardRecentJobsPanel() {
  const { data, error, isLoading, isFetching, refetch } = useRecentJobs();
  const jobs = data?.items ?? [];
  const failedJobs = jobs.filter((job) => job.status === 'failed');
  const visibleJobs = failedJobs.length ? failedJobs : jobs;

  return (
    <Card className="flex h-[min(72vh,44rem)] flex-col overflow-hidden border-slate-200 bg-white shadow-sm shadow-slate-200/40">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-slate-900">最近任务</CardTitle>
            <CardDescription>优先展示失败任务；如果没有失败任务，则显示最近运行记录。</CardDescription>
          </div>
          <button
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-sky-300 hover:bg-sky-50"
            onClick={() => refetch()}
            type="button"
          >
            {isFetching ? '刷新中' : '刷新'}
          </button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 space-y-3 overflow-y-auto pr-1">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full rounded-2xl" />
            <Skeleton className="h-20 w-full rounded-2xl" />
            <Skeleton className="h-20 w-full rounded-2xl" />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error.message}
          </div>
        ) : !visibleJobs.length ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">暂无最近任务。</div>
        ) : (
          visibleJobs.map((job) => (
            <article
              className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:border-sky-300 hover:bg-sky-50/70"
              key={job.id}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-slate-900">{job.job_type}</p>
                  <p className="break-all text-xs text-slate-500">{job.id}</p>
                </div>
                <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
              </div>
              <div className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
                <div>创建者：{job.created_by}</div>
                <div>开始时间：{formatTimestamp(job.started_at)}</div>
                <div>结束时间：{formatTimestamp(job.finished_at)}</div>
                <div className="md:text-right">
                  <Link className="font-medium text-sky-700 hover:underline" to={`/jobs/${encodeURIComponent(job.id)}`}>
                    查看任务详情
                  </Link>
                </div>
              </div>
            </article>
          ))
        )}
        {failedJobs.length === 0 && jobs.length ? (
          <p className="text-xs text-slate-500">当前没有失败任务，以上显示最近运行记录。</p>
        ) : null}
      </CardContent>
    </Card>
  );
}
