import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { JobRecord } from '@/types/jobs';

function classifyJobError(job: JobRecord) {
  const error = job.error;
  const rawType = typeof error === 'string' ? '' : error?.type ?? '';
  const rawMessage = typeof error === 'string' ? error : error?.message ?? '';
  const text = `${rawType} ${rawMessage}`.toLowerCase();
  if (text.includes('permission') || text.includes('config')) return '配置';
  if (text.includes('provider') || text.includes('api') || text.includes('kaipan')) return 'provider';
  if (text.includes('data') || text.includes('empty') || text.includes('missing')) return '数据';
  return '系统';
}

type MarketWorkspaceErrorsProps = {
  failedJobs: JobRecord[];
};

export function MarketWorkspaceErrors({ failedJobs }: MarketWorkspaceErrorsProps) {
  return (
    <Card className="border-slate-200 bg-white/90 shadow-sm text-slate-900">
      <CardHeader>
        <CardTitle className="text-slate-900">重点告警</CardTitle>
        <CardDescription className="text-slate-500">只展示最需要处理的市场任务失败信息。</CardDescription>
      </CardHeader>
      <CardContent>
        {failedJobs.length ? (
          <div className="space-y-3">
            {failedJobs.map((job) => (
              <div key={job.id} className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">{job.job_type}</p>
                    <p className="mt-1 text-sm text-slate-600">
                      {typeof job.error === 'string' ? job.error : job.error?.message ?? '任务失败'}
                    </p>
                  </div>
                  <Badge variant="destructive">{classifyJobError(job)}</Badge>
                </div>
                <div className="mt-3">
                  <a className="text-sm font-medium text-sky-700 hover:text-sky-800" href={`/jobs/${job.id}`}>
                    查看 Job 详情
                  </a>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-500">
            当前没有需要处理的市场告警。
          </p>
        )}
      </CardContent>
    </Card>
  );
}
