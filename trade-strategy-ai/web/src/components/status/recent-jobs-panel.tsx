import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatusBadge } from '@/components/kit';
import { ApiError } from '@/lib/api/http';
import { cn } from '@/lib/utils';
import { useRecentJobs } from '@/features/jobs/use-recent-jobs';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '无法加载最近任务';
}

function formatTimestamp(value: string | null) {
  if (!value) {
    return '未记录';
  }
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function RecentJobsPanel() {
  const { data, error, isLoading, isFetching, refetch } = useRecentJobs();

  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle>最近任务</CardTitle>
            <CardDescription>展示最新的运行状态和触发入口。</CardDescription>
          </div>
          <Button variant="outline" onClick={() => refetch()} disabled={isFetching}>
            {isFetching ? '刷新中' : '刷新'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
            {getErrorMessage(error)}
          </div>
        ) : !data?.items.length ? (
          <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
            暂无最近任务。
          </div>
        ) : (
          data.items.map((job) => (
            <article
              className={cn(
                'cursor-pointer rounded-2xl border border-slate-200 bg-white p-4 transition-colors hover:border-sky-300 hover:bg-sky-50/70',
              )}
              key={job.id}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <p className="font-medium text-slate-900">{job.job_type}</p>
                  <p className="text-xs text-slate-500">{job.id}</p>
                </div>
                <StatusBadge value={job.status} />
              </div>

              <div className="mt-3 grid gap-2 text-xs text-slate-600 md:grid-cols-2">
                <div>
                  <span className="text-slate-500">创建者：</span> {job.created_by}
                </div>
                <div>
                  <span className="text-slate-500">创建时间：</span> {formatTimestamp(job.created_at)}
                </div>
              </div>
            </article>
          ))
        )}
      </CardContent>
    </Card>
  );
}
