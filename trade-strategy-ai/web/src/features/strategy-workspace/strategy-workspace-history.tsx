import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { getWorkspaceErrorMessage, formatWorkspaceTimestamp } from './strategy-workspace-utils';
import type { JobRecord } from '@/types/jobs';

const STRATEGY_JOB_TYPES = new Set(['strategy-build', 'run-pre-market', 'run-after-close']);

function statusVariant(status: string) {
  if (status === 'success') return 'success';
  if (status === 'failed') return 'destructive';
  if (status === 'running' || status === 'queued' || status === 'pending') return 'warning';
  return 'info';
}

function describeStrategyJob(job: JobRecord) {
  const params = job.params ?? {};
  const traderId = typeof params.trader_id === 'string' ? params.trader_id : null;
  const strategyDate = typeof params.strategy_date === 'string' ? params.strategy_date : null;
  const asOfDate = typeof params.as_of_date === 'string' ? params.as_of_date : null;
  const configPath = typeof params.config_path === 'string' ? params.config_path : null;

  return [traderId ? `trader ${traderId}` : null, strategyDate ? `strategy ${strategyDate}` : asOfDate ? `as_of ${asOfDate}` : null, configPath ? configPath : null]
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
    <Card className="border-slate-200 bg-white shadow-sm">
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <Badge variant="info" className="w-fit">
              最近任务
            </Badge>
            <CardTitle className="mt-2 text-slate-950">策略任务历史</CardTitle>
            <CardDescription className="text-slate-600">
              仅展示 `strategy-build`、`run-pre-market` 和 `run-after-close`。
            </CardDescription>
          </div>
          <Button
            className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            onClick={onRetry}
            variant="outline"
          >
            刷新
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-24 w-full bg-slate-100" />
            <Skeleton className="h-24 w-full bg-slate-100" />
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
            <p className="font-medium">{getWorkspaceErrorMessage(error, '策略任务加载失败')}</p>
            <p className="mt-1 text-rose-700">请重试后继续查看任务详情。</p>
          </div>
        ) : strategyJobs.length ? (
          strategyJobs.map((job) => (
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
                <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
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
          ))
        ) : (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm leading-6 text-slate-600">
            暂无策略任务。提交 `strategy-build`、`run-pre-market` 或 `run-after-close` 后，这里会展示最近执行记录。
          </div>
        )}
      </CardContent>
    </Card>
  );
}
