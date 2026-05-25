import { useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ArtifactPanel } from '@/components/artifacts/artifact-panel';
import { formatTimestamp, maskAbsolutePath } from '@/components/artifacts/artifact-utils';
import { ConfigSnapshotPanel } from '@/components/profiles/ConfigSnapshotPanel';
import { PageHeader } from '@/components/layout/page-header';
import { JsonViewer, LoadingState, LogViewer, SectionCard, StatusBadge } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { StepTimeline } from '@/components/jobs/StepTimeline';
import { JobProgress } from '@/components/jobs/JobProgress';
import { useAuth } from '@/features/auth/auth-context';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { cancelJob, createJob, getJob, getJobLogs } from '@/lib/api/jobs';
import type { JobRecord, JobDetailResponse } from '@/types/jobs';
import type { StepTimelineItem } from '@/types/job';

function buildTimelineItems(job: JobRecord): StepTimelineItem[] {
  const statusByOperation: Record<string, StepTimelineItem['status']> = {
    create: 'pending',
    start: 'running',
    heartbeat: 'running',
    complete: 'success',
    fail: 'failed',
    cancel: 'cancelled',
    retry: 'pending',
  };

  return job.audit_events.map((event, index) => {
    const payload = event.payload as Record<string, unknown>;
    const details = payload?.details ?? payload;
    const errorPayload = job.error && (event.operation === 'fail' || event.operation === 'cancel' || event.operation === 'complete')
      ? job.error
      : null;
    const errorSummary = typeof errorPayload === 'string'
      ? errorPayload
      : errorPayload && typeof errorPayload === 'object'
        ? errorPayload.message || errorPayload.type || null
        : null;

    return {
      id: event.id,
      stepName: event.operation,
      title: `${event.actor} · ${event.operation}`,
      status: statusByOperation[event.operation] ?? 'success',
      startedAt: event.event_at,
      finishedAt: event.event_at,
      durationMs: null,
      errorSummary: errorSummary ? String(errorSummary) : null,
      details,
      metadata: {
        actor: event.actor,
        source: event.source,
      },
      order: index,
    };
  });
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 break-all text-sm text-slate-900">{value ?? '未记录'}</p>
    </div>
  );
}

export function JobDetailPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const params = useParams<{ jobId?: string }>();
  const { canAccess } = useAuth();
  const jobId = params.jobId?.trim() || '';
  const canOperateJobs = canAccess('operator');

  const detailQuery = useQuery({
    queryKey: ['job-detail', jobId],
    queryFn: () => getJob(jobId),
    enabled: Boolean(jobId),
    refetchInterval: (query) => {
      const jobStatus = (query.state.data as JobDetailResponse | undefined)?.job?.status;
      return jobStatus === 'running' || jobStatus === 'pending' ? 5000 : false;
    },
  });

  const detail = detailQuery.data?.job ?? null;

  const logsQuery = useQuery({
    queryKey: ['job-logs', jobId],
    queryFn: () => getJobLogs(jobId),
    enabled: Boolean(jobId) && Boolean(detail),
    refetchInterval: detail?.status === 'running' || detail?.status === 'pending' ? 5000 : false,
  });

  const rerunMutation = useMutation({
    mutationFn: async () => {
      if (!detail) {
        throw new Error('No job selected');
      }
      return createJob({
        job_type: detail.job_type,
        params: detail.params as Record<string, unknown>,
        created_by: 'web',
        max_retries: detail.max_retries,
        retry_backoff_seconds: detail.retry_backoff_seconds,
        timeout_seconds: detail.timeout_seconds,
      });
    },
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      await queryClient.invalidateQueries({ queryKey: ['job-detail', jobId] });
      await queryClient.invalidateQueries({ queryKey: ['job-logs', jobId] });
      if (data.job?.id) {
        navigate(`/jobs/${encodeURIComponent(data.job.id)}`);
      }
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelJob(jobId, 'web console request'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      await queryClient.invalidateQueries({ queryKey: ['job-detail', jobId] });
      await queryClient.invalidateQueries({ queryKey: ['job-logs', jobId] });
    },
  });

  const timelineItems = useMemo(() => (detail ? buildTimelineItems(detail) : []), [detail]);
  const errorObject = detail?.error ?? null;
  const configSnapshot = detail?.config_snapshot ?? null;
  const profileSnapshot = detail?.profile_snapshot ?? null;
  const logs = logsQuery.data?.items ?? [];

  if (!jobId) {
    return (
      <main className="page-stack">
        <ErrorState
          category="validation error"
          title="任务详情参数缺失"
          description="缺少任务 ID，无法打开详情页。"
          suggestion="请从任务列表重新打开一个 Job 详情。"
          actions={[{ label: '返回任务列表', to: '/jobs' }]}
        />
      </main>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader kicker="任务" title="任务详情" description="正在加载任务、步骤、日志、产物和配置快照。" />
        <div className="space-y-4">
          <LoadingState label="正在加载任务详情" description="正在获取任务、步骤、日志、产物和配置快照。" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-56 w-full" />
        </div>
      </main>
    );
  }

  if (detailQuery.error) {
    return (
      <main className="page-stack">
        <ErrorState
          {...buildErrorRecoveryState(detailQuery.error, 'job-detail')}
          onRetry={() => {
            void detailQuery.refetch();
          }}
        />
      </main>
    );
  }

  if (!detail) {
    return (
      <main className="page-stack">
        <ErrorState
          category="data empty"
          title="任务不存在"
          description="无法读取任务详情。"
          suggestion="请返回任务列表重新选择一个 Job。"
          actions={[{ label: '返回任务列表', to: '/jobs' }]}
        />
      </main>
    );
  }

  const runningRefresh = detail.status === 'running' || detail.status === 'pending';

  return (
    <main className="page-stack">
      <PageHeader
        kicker="任务"
        title="任务详情"
        description="查看任务输入、执行过程、结果、失败原因、产物和配置快照。"
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="outline" onClick={() => navigate('/jobs')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回任务列表
        </Button>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => {
              detailQuery.refetch();
              logsQuery.refetch();
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {runningRefresh ? '自动刷新中' : '刷新'}
          </Button>
          <Button variant="secondary" onClick={() => rerunMutation.mutate()} disabled={rerunMutation.isPending || !canOperateJobs}>
            {rerunMutation.isPending ? '重新运行中' : '重新运行任务'}
          </Button>
          <Button
            variant="destructive"
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending || !canOperateJobs || !['pending', 'running'].includes(detail.status) || detail.cancel_requested}
          >
            {cancelMutation.isPending ? '取消中' : '取消任务'}
          </Button>
        </div>
      </div>

      {runningRefresh ? (
        <div className="rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
          任务仍在运行，页面会自动刷新状态。
        </div>
      ) : null}

      <section className="grid items-start gap-6 2xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
        <div className="min-w-0 space-y-6">
          <SectionCard
            title={`${detail.job_type}`}
            description={detail.id}
            action={<StatusBadge value={detail.status} />}
          >
            <div className="grid gap-3 md:grid-cols-3">
              <Field label="创建者" value={detail.created_by} />
              <Field label="重试次数" value={detail.retry_count} />
              <Field label="确认键" value={detail.idempotency_key} />
              <Field label="创建时间" value={formatTimestamp(detail.created_at)} />
              <Field label="开始时间" value={formatTimestamp(detail.started_at)} />
              <Field label="结束时间" value={formatTimestamp(detail.finished_at)} />
            </div>
          </SectionCard>

          <SectionCard title="参数快照" description="展示任务提交时的参数和关联配置快照。">
            <div className="grid gap-4">
              <div className="grid gap-3 md:grid-cols-2">
                <JsonViewer value={detail.params} title="参数" />
                <JsonViewer value={detail.result} title="执行结果" />
              </div>
              {detail.progress ? (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">执行进度</p>
                  <JobProgress progress={detail.progress} className="mt-3" />
                </div>
              ) : null}
              <div className="grid gap-3 md:grid-cols-3">
                <Field label="快照 ID" value={configSnapshot?.config_snapshot_id} />
                <Field label="快照哈希" value={configSnapshot?.config_hash} />
                <Field label="快照来源" value={maskAbsolutePath(configSnapshot?.config_source)} />
              </div>
              {configSnapshot?.profile_id && configSnapshot?.config_snapshot_id ? (
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    onClick={() =>
                      navigate(
                        `/profiles/${encodeURIComponent(configSnapshot.profile_id!)}/snapshots/${encodeURIComponent(
                          configSnapshot.config_snapshot_id!,
                        )}`,
                      )
                    }
                  >
                    查看 Profile 快照
                  </Button>
                </div>
              ) : null}
              <ConfigSnapshotPanel snapshot={configSnapshot} />
              {profileSnapshot ? (
                <>
                  <div className="grid gap-3 md:grid-cols-3">
                    <Field label="Profile 快照 ID" value={profileSnapshot.profile_snapshot_id} />
                    <Field label="Profile ID" value={profileSnapshot.profile_id} />
                    <Field label="Profile 快照路径" value={profileSnapshot.snapshot_path} />
                  </div>
                  <JsonViewer value={profileSnapshot} title="Profile 快照" />
                </>
              ) : null}
            </div>
          </SectionCard>

          <SectionCard
            title="步骤时间线"
            description="Job 审计事件已归一为步骤时间线，后续 Step Timeline 接入后会直接替换数据源。"
            className="flex h-[min(72vh,44rem)] flex-col overflow-hidden"
          >
            <div className="flex min-h-0 flex-1 flex-col">
              <div className="flex items-center justify-between gap-3 text-xs text-slate-500">
                <span>{timelineItems.length} 个步骤</span>
                <span>{runningRefresh ? '自动刷新中' : '静态展示'}</span>
              </div>
              <div className="mt-4 min-h-0 flex-1 overflow-y-auto pr-1">
                <StepTimeline items={timelineItems} />
              </div>
            </div>
          </SectionCard>
        </div>

        <div className="min-w-0 space-y-6">
          <SectionCard
            title="错误"
            description={detail.status === 'failed' || detail.status === 'cancelled' ? '失败或取消时会显示原因和建议。' : '任务正常时此处展示为空态。'}
          >
            {errorObject ? (
              <ErrorState
                {...buildErrorRecoveryState(errorObject, 'job-detail')}
                onRetry={canOperateJobs ? () => rerunMutation.mutate() : undefined}
                retryLabel="重新运行"
              />
            ) : (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">暂无错误。</div>
            )}
          </SectionCard>

          <SectionCard
            title="日志"
            description="展示最近的日志片段。"
            action={
              <Button variant="outline" size="sm" onClick={() => logsQuery.refetch()} disabled={logsQuery.isFetching}>
                {logsQuery.isFetching ? '刷新中' : '刷新日志'}
            </Button>
          }
          >
            {logsQuery.error ? (
              <ErrorState
                {...buildErrorRecoveryState(logsQuery.error, 'job-detail')}
                onRetry={() => {
                  void logsQuery.refetch();
                }}
              />
            ) : (
              <LogViewer lines={logsQuery.isLoading ? ['正在加载日志...'] : logs} emptyLabel="尚无日志。" />
            )}
          </SectionCard>

          <SectionCard title="产物" description="只展示后端返回的产物引用，不推断文件系统路径。">
            <ArtifactPanel artifacts={detail.artifacts} />
          </SectionCard>
        </div>
      </section>
    </main>
  );
}
