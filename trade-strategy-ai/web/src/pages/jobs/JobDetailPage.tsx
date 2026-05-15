import { useMemo, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ArtifactPanel } from '@/components/artifacts/artifact-panel';
import { formatTimestamp, maskAbsolutePath, stringifyJson } from '@/components/artifacts/artifact-utils';
import { PageHeader } from '@/components/layout/page-header';
import { StepTimeline } from '@/components/jobs/StepTimeline';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { cancelJob, createJob, getJob, getJobLogs } from '@/lib/api/jobs';
import type { JobError, JobRecord, JobDetailResponse } from '@/types/jobs';
import type { StepTimelineItem } from '@/types/job';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '任务详情加载失败';
}

function statusVariant(status: string) {
  if (status === 'success') return 'success';
  if (status === 'failed' || status === 'cancelled') return 'destructive';
  if (status === 'running') return 'info';
  return 'warning';
}

function getStatusLabel(status: string) {
  const mapping: Record<string, string> = {
    pending: '等待中',
    running: '运行中',
    success: '成功',
    failed: '失败',
    cancelled: '已取消',
  };
  return mapping[status] || status;
}

function getRetrySuggestion(error: JobError | string | null) {
  if (!error) {
    return '如问题已修复，可以重新运行任务。';
  }
  const type = typeof error === 'string' ? '' : error.type || '';
  if (type === 'timeout') {
    return '可检查超时配置后重试。';
  }
  if (type === 'cancelled' || type === 'cancel_requested') {
    return '该任务已被取消，确认后再重新提交。';
  }
  if (type === 'unsupported_job_type') {
    return '需要先补齐白名单定义或调整任务类型。';
  }
  if (type === 'handler_error' || type === 'runner_error') {
    return '先检查日志和结果摘要，再决定是否重试。';
  }
  return '可以先查看日志和错误详情，再判断是否重试。';
}

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
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 break-all text-sm text-slate-100">{value ?? '未记录'}</p>
    </div>
  );
}

function SectionCard({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>{title}</CardTitle>
            {description ? <CardDescription>{description}</CardDescription> : null}
          </div>
          {action}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function ErrorBlock({ error }: { error: JobError | string | null }) {
  if (!error) {
    return <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">暂无错误。</div>;
  }

  const errorObject = typeof error === 'string' ? { message: error } : error;
  const technicalDetail = stringifyJson(errorObject);

  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-3">
        <Field label="错误类型" value={errorObject.type ?? '未提供'} />
        <Field label="用户消息" value={errorObject.message ?? '未提供'} />
        <Field label="重试建议" value={getRetrySuggestion(error)} />
      </div>
      <details className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
        <summary className="cursor-pointer text-sm font-medium text-slate-100">技术详情</summary>
        <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200">
          {technicalDetail}
        </pre>
      </details>
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
  const sanitizedParams = useMemo(() => stringifyJson(detail?.params), [detail?.params]);
  const sanitizedResult = useMemo(() => stringifyJson(detail?.result), [detail?.result]);
  const errorObject = detail?.error ?? null;
  const configSnapshot = detail?.config_snapshot ?? null;
  const logs = logsQuery.data?.items ?? [];

  if (!jobId) {
    return (
      <main className="page-stack">
        <SectionCard title="任务不存在" description="缺少任务 ID，无法打开详情页。">
          <Button onClick={() => navigate('/jobs')}>返回任务列表</Button>
        </SectionCard>
      </main>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader kicker="任务" title="任务详情" description="正在加载任务、步骤、日志、产物和配置快照。" />
        <div className="space-y-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-56 w-full" />
        </div>
      </main>
    );
  }

  if (detailQuery.error) {
    const error = detailQuery.error;
    const title = error instanceof ApiError && error.status === 404
      ? '任务不存在'
      : error instanceof ApiError && (error.status === 401 || error.status === 403)
        ? '没有权限访问该任务'
        : '任务详情加载失败';
    const description = error instanceof ApiError && error.status === 404
      ? '系统没有找到该 Job 记录。'
      : error instanceof ApiError && (error.status === 401 || error.status === 403)
        ? '当前身份无法查看该任务详情。'
        : getErrorMessage(error);

    return (
      <main className="page-stack">
        <SectionCard
          title={title}
          description={description}
          action={
            <Button variant="outline" onClick={() => detailQuery.refetch()}>
              重试
            </Button>
          }
        >
          <Button variant="secondary" onClick={() => navigate('/jobs')}>
            返回任务列表
          </Button>
        </SectionCard>
      </main>
    );
  }

  if (!detail) {
    return (
      <main className="page-stack">
        <SectionCard title="任务不存在" description="无法读取任务详情。">
          <Button onClick={() => navigate('/jobs')}>返回任务列表</Button>
        </SectionCard>
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
        <div className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-4 py-3 text-sm text-sky-100">
          任务仍在运行，页面会自动刷新状态。
        </div>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)]">
        <div className="space-y-6">
          <SectionCard
            title={`${detail.job_type}`}
            description={detail.id}
            action={<Badge variant={statusVariant(detail.status)}>{getStatusLabel(detail.status)}</Badge>}
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
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">参数</p>
                  <pre className="mt-3 max-h-72 overflow-auto rounded-xl border border-slate-800 bg-slate-950/90 p-3 text-xs text-slate-200">
                    {sanitizedParams}
                  </pre>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">执行结果</p>
                  <pre className="mt-3 max-h-72 overflow-auto rounded-xl border border-slate-800 bg-slate-950/90 p-3 text-xs text-slate-200">
                    {sanitizedResult}
                  </pre>
                </div>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <Field label="快照 ID" value={configSnapshot?.config_snapshot_id} />
                <Field label="快照哈希" value={configSnapshot?.config_hash} />
                <Field label="快照来源" value={maskAbsolutePath(configSnapshot?.config_source)} />
              </div>
              {configSnapshot ? (
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">脱敏配置快照</p>
                  <pre className="mt-3 max-h-72 overflow-auto rounded-xl border border-slate-800 bg-slate-950/90 p-3 text-xs text-slate-200">
                    {stringifyJson(configSnapshot.masked_snapshot)}
                  </pre>
                </div>
              ) : (
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                  该任务没有配置快照。
                </div>
              )}
            </div>
          </SectionCard>

          <SectionCard
            title="步骤时间线"
            description="Job 审计事件已归一为步骤时间线，后续 Step Timeline 接入后会直接替换数据源。"
          >
            <div className="flex items-center justify-between gap-3 pb-3 text-xs text-slate-500">
              <span>{timelineItems.length} 个步骤</span>
              <span>{runningRefresh ? '自动刷新中' : '静态展示'}</span>
            </div>
            <StepTimeline items={timelineItems} />
          </SectionCard>
        </div>

        <div className="space-y-6">
          <SectionCard
            title="错误"
            description={detail.status === 'failed' || detail.status === 'cancelled' ? '失败或取消时会显示原因和建议。' : '任务正常时此处展示为空态。'}
          >
            <ErrorBlock error={errorObject} />
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
            <pre className="max-h-72 overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
              {logsQuery.isLoading
                ? '正在加载日志...'
                : logsQuery.error
                  ? getErrorMessage(logsQuery.error)
                  : logs.length
                    ? logs.join('\n')
                    : '尚无日志。'}
            </pre>
          </SectionCard>

          <SectionCard title="产物" description="只展示后端返回的产物引用，不推断文件系统路径。">
            <ArtifactPanel artifacts={detail.artifacts} />
          </SectionCard>
        </div>
      </section>
    </main>
  );
}
