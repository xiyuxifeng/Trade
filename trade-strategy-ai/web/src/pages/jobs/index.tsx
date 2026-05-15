import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from '@/components/ui/drawer';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { StepTimeline } from '@/components/jobs/StepTimeline';
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { cancelJob, createJob, getJob, getJobLogs, listJobs } from '@/lib/api/jobs';
import type { JobArtifactRef, JobDetailResponse, JobsListResponse } from '@/types/jobs';
import type { StepTimelineItem } from '@/types/job';
import { PageHeader } from '@/components/layout/page-header';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '任务数据加载失败';
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

function canCancelJob(status: string, cancelRequested: boolean) {
  return (status === 'pending' || status === 'running') && !cancelRequested;
}

function formatTimestamp(value: string | null) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 break-all text-sm text-slate-100">{value ?? '未记录'}</p>
    </div>
  );
}

function ArtifactCard({
  artifact,
  onOpenArtifacts,
}: {
  artifact: JobArtifactRef;
  onOpenArtifacts: () => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium text-slate-100">{artifact.title}</p>
          <p className="mt-1 text-xs text-slate-500">
            {artifact.kind}
            {artifact.step_id ? ` · step ${artifact.step_id}` : ''}
          </p>
          <p className="mt-2 text-sm text-slate-300">{artifact.summary ?? '暂无摘要。'}</p>
        </div>
        <Button variant="outline" size="sm" onClick={onOpenArtifacts}>
          在产物中心查看
        </Button>
      </div>
      <div className="mt-3">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">元数据 (Metadata)</p>
        <pre className="mt-2 max-h-40 overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200">
          {JSON.stringify(artifact.metadata, null, 2)}
        </pre>
      </div>
      <div className="mt-3 text-xs text-slate-500">
        {artifact.safe_download_url ? '包含安全下载入口。' : '暂无下载入口。'}
      </div>
    </div>
  );
}

function stringifyError(error: unknown) {
  if (typeof error === 'string') {
    return error.trim() || '任务失败';
  }
  if (error && typeof error === 'object') {
    const payload = error as Record<string, unknown>;
    if (typeof payload.message === 'string' && payload.message.trim()) {
      return payload.message;
    }
    return JSON.stringify(payload, null, 2);
  }
  return '任务失败';
}

function maskAbsolutePath(value: string | null | undefined) {
  if (!value) {
    return '未记录';
  }
  if (value.startsWith('/') || /^[A-Za-z]:[\\/]/.test(value)) {
    return '[已隐藏路径]';
  }
  return value;
}

function sanitizeForDisplay(value: unknown): unknown {
  if (typeof value === 'string') {
    return maskAbsolutePath(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeForDisplay(item));
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>);
    return Object.fromEntries(entries.map(([key, item]) => [key, sanitizeForDisplay(item)]));
  }
  return value;
}

function stringifyJson(value: unknown) {
  if (value === null || value === undefined) {
    return '未记录';
  }
  return JSON.stringify(sanitizeForDisplay(value), null, 2);
}

function buildTimelineItems(detail: NonNullable<JobDetailResponse['job']>): StepTimelineItem[] {
  const timelineItems: StepTimelineItem[] = detail.audit_events.map((event, index) => ({
    id: event.id,
    stepName: event.operation,
    title: `${event.actor} · ${event.operation}`,
    status: 'success',
    startedAt: event.event_at,
    finishedAt: event.event_at,
    durationMs: null,
    details: {
      source: event.source,
      params_summary: event.params_summary,
      payload: event.payload,
    },
    metadata: {
      actor: event.actor,
      source: event.source,
    },
    order: index,
  }));

  if (detail.error) {
    timelineItems.push({
      id: `${detail.id}-error`,
      stepName: 'job-error',
      title: '任务错误',
      status: detail.status === 'cancelled' ? 'cancelled' : 'failed',
      startedAt: detail.finished_at ?? detail.updated_at,
      finishedAt: detail.finished_at ?? detail.updated_at,
      durationMs: null,
      errorSummary: stringifyError(detail.error),
      details: detail.error as Record<string, unknown> | string,
      order: timelineItems.length,
    });
  }

  return timelineItems;
}

export function JobsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const params = useParams<{ jobId?: string }>();
  const { canAccess, principal } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const jobIdFromRoute = params.jobId?.trim();
  const jobIdFromQuery = searchParams.get('jobId')?.trim();
  const [status, setStatus] = useState('');
  const [jobType, setJobType] = useState('');
  const [createdBy, setCreatedBy] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(() => jobIdFromRoute ?? jobIdFromQuery ?? null);
  const [rerunOpen, setRerunOpen] = useState(false);
  const canOperateJobs = canAccess('operator');

  useEffect(() => {
    setSelectedJobId(jobIdFromRoute ?? jobIdFromQuery ?? null);
  }, [jobIdFromQuery, jobIdFromRoute]);

  const jobsQuery = useQuery<JobsListResponse, ApiError>({
    queryKey: ['jobs', { status, jobType, createdBy }],
    queryFn: () =>
      listJobs({
        status: status || undefined,
        job_type: jobType || undefined,
        created_by: createdBy || undefined,
        limit: 50,
      }),
    staleTime: 10_000,
  });

  const selectedJobQuery = useQuery<JobDetailResponse, ApiError>({
    queryKey: ['job-detail', selectedJobId],
    queryFn: () => getJob(selectedJobId as string),
    enabled: Boolean(selectedJobId),
  });

  const jobLogsQuery = useQuery({
    queryKey: ['job-logs', selectedJobId],
    queryFn: () => getJobLogs(selectedJobId as string),
    enabled: Boolean(selectedJobId),
  });

  const detail = selectedJobQuery.data?.job ?? null;
  const logs = jobLogsQuery.data?.items ?? [];

  const cancelMutation = useMutation({
    mutationFn: () => cancelJob(selectedJobId as string, 'web console request'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      await queryClient.invalidateQueries({ queryKey: ['job-detail', selectedJobId] });
      await queryClient.invalidateQueries({ queryKey: ['job-logs', selectedJobId] });
    },
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
      await queryClient.invalidateQueries({ queryKey: ['recent-jobs'] });
      setRerunOpen(false);
      if (data.job?.id) {
        setSelectedJobId(data.job.id);
        navigate(`/jobs/${encodeURIComponent(data.job.id)}`);
      }
    },
  });

  const summary = useMemo(() => {
    const total = jobsQuery.data?.total ?? 0;
    const running = jobsQuery.data?.items.filter((item) => item.status === 'running').length ?? 0;
    const failed = jobsQuery.data?.items.filter((item) => item.status === 'failed').length ?? 0;
    return { total, running, failed };
  }, [jobsQuery.data]);

  return (
    <main className="page-stack">
      <PageHeader
        kicker="任务"
        title="任务中心"
        description="查看最近的任务，检查详情，审阅日志，重新运行任务，并追踪产物引用。"
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.6fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>最近任务</CardTitle>
                <CardDescription>按状态、任务类型和创建者排序。</CardDescription>
              </div>
              <Button variant="outline" onClick={() => jobsQuery.refetch()} disabled={jobsQuery.isFetching}>
                {jobsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <Input placeholder="按创建者过滤" value={createdBy} onChange={(event) => setCreatedBy(event.target.value)} />
              <Input placeholder="按任务类型过滤" value={jobType} onChange={(event) => setJobType(event.target.value)} />
              <Select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="">所有状态</option>
                <option value="pending">等待中</option>
                <option value="running">运行中</option>
                <option value="success">成功</option>
                <option value="failed">失败</option>
                <option value="cancelled">已取消</option>
              </Select>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">总计</p>
                <p className="mt-2 text-2xl font-semibold text-slate-100">{summary.total}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">运行中</p>
                <p className="mt-2 text-2xl font-semibold text-sky-300">{summary.running}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">失败</p>
                <p className="mt-2 text-2xl font-semibold text-rose-300">{summary.failed}</p>
              </div>
            </div>

            {jobsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : jobsQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(jobsQuery.error)}
              </div>
            ) : !jobsQuery.data?.items.length ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                暂无符合条件的任务。
              </div>
            ) : (
              <div className="overflow-hidden rounded-2xl border border-slate-800">
                <Table>
                  <TableHeader className="bg-slate-950/80">
                    <TableRow>
                      <TableHead>任务</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>创建者</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {jobsQuery.data.items.map((job) => (
                      <TableRow key={job.id}>
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-medium text-slate-100">{job.job_type}</p>
                            <p className="break-all text-xs text-slate-500">{job.id}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusVariant(job.status)}>{getStatusLabel(job.status)}</Badge>
                        </TableCell>
                        <TableCell>{job.created_by}</TableCell>
                        <TableCell>{formatTimestamp(job.created_at)}</TableCell>
                        <TableCell>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedJobId(job.id);
                              navigate(`/jobs/${encodeURIComponent(job.id)}`);
                            }}
                          >
                            详情
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>操作说明</CardTitle>
            <CardDescription>任务中心立即展示的内容。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <ul className="list-disc space-y-2 pl-5 text-slate-400">
              <li>打开任何任务以查看参数、日志、结果元数据和产物引用。</li>
              <li>对于正在运行的任务，可以从详情页取消执行。</li>
              <li>过滤器设计简单，以确保第一波操作能够快速完成。</li>
            </ul>
            {!canOperateJobs ? (
              <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
                当前身份为 {principal.role}，只能查看任务详情，重新执行和取消任务需要 operator 权限。
              </div>
            ) : null}
          </CardContent>
        </Card>
      </section>

      <Drawer
        open={Boolean(selectedJobId)}
        onOpenChange={(open) => {
          if (open) return;
          setSelectedJobId(null);
          if (jobIdFromRoute) {
            navigate('/jobs', { replace: true });
            return;
          }
          setSearchParams((current) => {
            const next = new URLSearchParams(current);
            next.delete('jobId');
            return next;
          });
        }}
      >
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>任务详情</DrawerTitle>
            <DrawerDescription>
              {selectedJobId ? `正在检查 ${selectedJobId}` : '未选择任务'}
            </DrawerDescription>
          </DrawerHeader>

          {!detail ? (
            <div className="space-y-3">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : (
            <div className="grid gap-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-lg font-semibold text-slate-100">{detail.job_type}</p>
                  <p className="text-xs text-slate-500 break-all">{detail.id}</p>
                </div>
                <Badge variant={statusVariant(detail.status)}>{getStatusLabel(detail.status)}</Badge>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <Field label="创建者" value={detail.created_by} />
                <Field label="执行器" value={detail.worker_id} />
                <Field label="开始时间" value={formatTimestamp(detail.started_at)} />
                <Field label="完成时间" value={formatTimestamp(detail.finished_at)} />
                <Field label="配置快照 ID" value={detail.config_snapshot?.config_snapshot_id} />
                <Field label="配置哈希" value={detail.config_snapshot?.config_hash} />
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-200">参数</p>
                <pre className="max-h-56 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                  {stringifyJson(detail.params)}
                </pre>
              </div>

              <div className="grid gap-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-slate-200">步骤时间线</p>
                  <p className="text-xs text-slate-500">{detail.audit_events.length} 个事件</p>
                </div>
                <StepTimeline items={buildTimelineItems(detail)} />
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-200">日志</p>
                <pre className="max-h-56 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                  {jobLogsQuery.isLoading
                    ? '正在加载日志...'
                    : jobLogsQuery.error
                      ? getErrorMessage(jobLogsQuery.error)
                      : logs.length
                        ? logs.join('\n')
                        : '尚无日志。'}
                </pre>
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-200">配置快照</p>
                {!detail.config_snapshot ? (
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">该任务未关联配置快照。</div>
                ) : (
                  <>
                    <div className="grid gap-3 md:grid-cols-3">
                      <Field label="来源" value={maskAbsolutePath(detail.config_snapshot.config_source)} />
                      <Field label="时间" value={formatTimestamp(detail.config_snapshot.captured_at)} />
                      <Field label="快照路径" value={detail.config_snapshot.snapshot_path ? '已生成' : '未记录'} />
                    </div>
                    <pre className="max-h-56 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                      {stringifyJson(detail.config_snapshot.masked_snapshot)}
                    </pre>
                  </>
                )}
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-200">产物</p>
                {!detail.artifacts.length ? (
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                    该任务未产生任何产物。
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {detail.artifacts.map((artifact, index) => (
                      <ArtifactCard
                        artifact={artifact}
                        key={`${artifact.artifact_id}-${index}`}
                        onOpenArtifacts={() => navigate(`/artifacts?jobId=${encodeURIComponent(detail.id)}`)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <DrawerFooter>
            <Button variant="outline" onClick={() => setSelectedJobId(null)}>
              关闭
            </Button>
            <Button variant="secondary" onClick={() => setRerunOpen(true)} disabled={!detail || rerunMutation.isPending || !canOperateJobs}>
              {rerunMutation.isPending ? '重新运行中' : '重新运行任务'}
            </Button>
            <Button
              variant="destructive"
              onClick={() => cancelMutation.mutate()}
              disabled={
                cancelMutation.isPending ||
                !detail ||
                !canCancelJob(detail.status, detail.cancel_requested) ||
                !canOperateJobs
              }
            >
              {cancelMutation.isPending ? '取消中' : '取消任务'}
            </Button>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>

      <Dialog
        open={rerunOpen}
        onOpenChange={(open) => {
          setRerunOpen(open);
          if (!open) {
            rerunMutation.reset();
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>确认重新运行</DialogTitle>
            <DialogDescription>
              这将使用与所选任务相同的任务类型和参数快照创建一个新任务。
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="任务类型" value={detail?.job_type} />
              <Field label="创建者" value={detail?.created_by} />
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">参数</p>
              <pre className="mt-3 max-h-64 overflow-auto text-xs text-slate-200">
                {JSON.stringify(detail?.params ?? {}, null, 2)}
              </pre>
            </div>
            {rerunMutation.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(rerunMutation.error)}
              </div>
            ) : null}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setRerunOpen(false);
                rerunMutation.reset();
              }}
            >
              取消
            </Button>
            <Button onClick={() => rerunMutation.mutate()} disabled={!detail || rerunMutation.isPending || !canOperateJobs}>
              {rerunMutation.isPending ? '提交中' : '确认重新运行'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
