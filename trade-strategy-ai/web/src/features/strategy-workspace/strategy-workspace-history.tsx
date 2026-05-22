import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { ErrorState } from '@/components/state/ErrorState';
import { EmptyState, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { formatWorkspaceTimestamp } from './strategy-workspace-utils';
import type { JobRecord } from '@/types/jobs';

const STRATEGY_JOB_TYPES = new Set(['strategy-build', 'run-pre-market', 'run-after-close']);

function describeStrategyJob(job: JobRecord) {
  const params = job.params ?? {};
  const profileId = typeof params.profile_id === 'string' ? params.profile_id : null;
  const traderId = typeof params.trader_id === 'string' ? params.trader_id : null;
  const strategyDate = typeof params.strategy_date === 'string' ? params.strategy_date : null;
  const asOfDate = typeof params.as_of_date === 'string' ? params.as_of_date : null;

  return [profileId ? `profile ${profileId}` : null, traderId ? `trader ${traderId}` : null, strategyDate ? `strategy ${strategyDate}` : asOfDate ? `as_of ${asOfDate}` : null]
    .filter(Boolean)
    .join(' · ');
}

type StrategyWorkspaceHistoryProps = {
  jobs: JobRecord[];
  isLoading: boolean;
  error: unknown;
  onRetry: () => void;
};

export function StrategyWorkspaceHistory({ jobs, isLoading, error, onRetry }: StrategyWorkspaceHistoryProps) {
  const navigate = useNavigate();
  const strategyJobs = useMemo(
    () =>
      [...jobs]
        .filter((job) => STRATEGY_JOB_TYPES.has(job.job_type))
        .sort((left, right) => right.created_at.localeCompare(left.created_at)),
    [jobs],
  );

  return (
    <SectionCard
      title="策略任务历史"
      description="仅展示 `strategy-build`、`run-pre-market` 和 `run-after-close`。"
      action={
        <Button className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50" onClick={onRetry} variant="outline">
          刷新
        </Button>
      }
    >
      {isLoading ? (
        <LoadingState label="正在加载策略任务历史" description="稍后会展示最近的策略执行记录。" />
      ) : error ? (
        <ErrorState {...buildErrorRecoveryState(error, 'strategy')} onRetry={onRetry} />
      ) : strategyJobs.length ? (
        <div className="space-y-3">
          {strategyJobs.map((job) => (
            <button
              key={job.id}
              className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left transition-colors hover:border-sky-200 hover:bg-sky-50/70"
              onClick={() => navigate(`/jobs/${job.id}`)}
              type="button"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-base font-medium text-slate-950">{job.id}</p>
                  <p className="mt-1 text-sm text-slate-600">{job.job_type}</p>
                </div>
                <StatusBadge value={job.status} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
                <span className="rounded-full border border-slate-200 px-2 py-1">{describeStrategyJob(job) || '参数待查看'}</span>
                <span className="rounded-full border border-slate-200 px-2 py-1">创建于 {formatWorkspaceTimestamp(job.created_at)}</span>
              </div>
              {job.error ? (
                <p className="mt-3 text-sm text-rose-700">
                  {typeof job.error === 'string' ? job.error : job.error.message ?? '任务失败'}
                </p>
              ) : null}
            </button>
          ))}
        </div>
      ) : (
        <EmptyState title="暂无策略任务。" description="提交 `strategy-build`、`run-pre-market` 或 `run-after-close` 后，这里会展示最近执行记录。" />
      )}
    </SectionCard>
  );
}
