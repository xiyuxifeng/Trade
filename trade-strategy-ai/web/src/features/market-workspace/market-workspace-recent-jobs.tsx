import { SectionCard, StatusBadge, LoadingState, EmptyState } from '@/components/kit';
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
    <SectionCard
      title="最近任务"
      description="查看最近提交的市场任务和它们的执行结果。"
      action={
        <a
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          href="/jobs"
        >
          查看任务中心
        </a>
      }
    >
      {loading ? (
        <LoadingState label="正在加载最近任务" description="稍后会显示最近提交的市场任务和执行结果。" />
      ) : jobs.length ? (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div key={job.id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-900">{job.job_type}</p>
                  <p className="mt-1 text-sm text-slate-500">{formatDate(job.created_at)}</p>
                </div>
                <StatusBadge value={job.status} />
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
        <EmptyState title="暂无最近任务。" description="当市场任务被提交后，这里会显示最新记录。" />
      )}
    </SectionCard>
  );
}
