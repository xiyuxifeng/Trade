import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { JobRecord } from '@/types/jobs';

type MarketWorkspaceRecentJobsProps = {
  jobs: JobRecord[];
  loading: boolean;
};

function formatDate(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function MarketWorkspaceRecentJobs({ jobs, loading }: MarketWorkspaceRecentJobsProps) {
  return (
    <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
      <CardHeader className="flex flex-row items-start justify-between gap-3">
        <div>
          <CardTitle className="text-slate-900">最近任务</CardTitle>
          <CardDescription className="text-slate-500">查看最近提交的市场任务和它们的执行结果。</CardDescription>
        </div>
        <a
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          href="/jobs"
        >
          查看任务中心
        </a>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            <div className="h-12 animate-pulse rounded-2xl bg-slate-100" />
            <div className="h-12 animate-pulse rounded-2xl bg-slate-100" />
            <div className="h-12 animate-pulse rounded-2xl bg-slate-100" />
          </div>
        ) : jobs.length ? (
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">{job.job_type}</p>
                    <p className="mt-1 text-sm text-slate-500">{formatDate(job.created_at)}</p>
                  </div>
                  <Badge variant={job.status === 'failed' ? 'destructive' : job.status === 'success' ? 'success' : 'info'}>
                    {job.status}
                  </Badge>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <a className="text-sm font-medium text-sky-700 hover:text-sky-800" href={`/jobs/${job.id}`}>
                    打开 Job 详情
                  </a>
                  <span className="text-xs text-slate-400">创建者：{job.created_by}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
            暂无最近任务。
          </p>
        )}
      </CardContent>
    </Card>
  );
}
