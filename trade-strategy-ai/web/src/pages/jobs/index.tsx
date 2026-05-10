import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
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
import { useAuth } from '@/features/auth/auth-context';
import { ApiError } from '@/lib/api/http';
import { cancelJob, createJob, getJob, getJobLogs, listJobs } from '@/lib/api/jobs';
import type { JobArtifactRef, JobAuditEvent, JobDetailResponse, JobsListResponse } from '@/types/jobs';
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
        <div>
          <p className="font-medium text-slate-100">{artifact.kind}</p>
          <p className="mt-1 break-all text-xs text-slate-500">{artifact.path}</p>
        </div>
        <Button variant="outline" size="sm" onClick={onOpenArtifacts}>
          Open in Artifacts
        </Button>
      </div>
      <div className="mt-3">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Metadata</p>
        <pre className="mt-2 max-h-40 overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200">
          {JSON.stringify(artifact.metadata, null, 2)}
        </pre>
      </div>
    </div>
  );
}

function AuditEventCard({ event }: { event: JobAuditEvent }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-100">
            {event.actor} · {event.operation}
          </p>
          <p className="mt-1 text-xs text-slate-500">{event.source}</p>
        </div>
        <p className="text-xs text-slate-500">{formatTimestamp(event.event_at)}</p>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <Field label="Params summary" value={JSON.stringify(event.params_summary)} />
        <Field label="Payload" value={JSON.stringify(event.payload)} />
      </div>
    </div>
  );
}

export function JobsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { canAccess, principal } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const jobIdFromQuery = searchParams.get('jobId');
  const [status, setStatus] = useState('');
  const [jobType, setJobType] = useState('');
  const [createdBy, setCreatedBy] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(() => jobIdFromQuery);
  const [rerunOpen, setRerunOpen] = useState(false);
  const canOperateJobs = canAccess('operator');

  useEffect(() => {
    setSelectedJobId(jobIdFromQuery);
  }, [jobIdFromQuery]);

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
        setSearchParams((current) => {
          const next = new URLSearchParams(current);
          next.set('jobId', data.job.id);
          return next;
        });
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
        kicker="Jobs"
        title="Task Center"
        description="View recent jobs, inspect details, review logs, rerun work, and follow artifact references."
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.6fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Recent jobs</CardTitle>
                <CardDescription>Sortable by status, job type and creator.</CardDescription>
              </div>
              <Button variant="outline" onClick={() => jobsQuery.refetch()} disabled={jobsQuery.isFetching}>
                {jobsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-3">
              <Input placeholder="Filter by creator" value={createdBy} onChange={(event) => setCreatedBy(event.target.value)} />
              <Input placeholder="Filter by job type" value={jobType} onChange={(event) => setJobType(event.target.value)} />
              <Select value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="">All statuses</option>
                <option value="pending">pending</option>
                <option value="running">running</option>
                <option value="success">success</option>
                <option value="failed">failed</option>
                <option value="cancelled">cancelled</option>
              </Select>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Total</p>
                <p className="mt-2 text-2xl font-semibold text-slate-100">{summary.total}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Running</p>
                <p className="mt-2 text-2xl font-semibold text-sky-300">{summary.running}</p>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Failed</p>
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
                      <TableHead>Job</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created by</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead>Actions</TableHead>
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
                          <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
                        </TableCell>
                        <TableCell>{job.created_by}</TableCell>
                        <TableCell>{formatTimestamp(job.created_at)}</TableCell>
                        <TableCell>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedJobId(job.id);
                              setSearchParams((current) => {
                                const next = new URLSearchParams(current);
                                next.set('jobId', job.id);
                                return next;
                              });
                            }}
                          >
                            Details
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
            <CardTitle>Operational notes</CardTitle>
            <CardDescription>What the task center surfaces immediately.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <ul className="list-disc space-y-2 pl-5 text-slate-400">
              <li>Open any job for params, logs, result metadata and artifact references.</li>
              <li>Cancel is available from the drawer for in-flight jobs.</li>
              <li>Filters are intentionally simple to keep the first operational pass fast.</li>
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
          setSearchParams((current) => {
            const next = new URLSearchParams(current);
            next.delete('jobId');
            return next;
          });
        }}
      >
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Job details</DrawerTitle>
            <DrawerDescription>
              {selectedJobId ? `Inspecting ${selectedJobId}` : 'No job selected'}
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
                <Badge variant={statusVariant(detail.status)}>{detail.status}</Badge>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <Field label="Created by" value={detail.created_by} />
                <Field label="Worker" value={detail.worker_id} />
                <Field label="Started" value={formatTimestamp(detail.started_at)} />
                <Field label="Finished" value={formatTimestamp(detail.finished_at)} />
                <Field label="Job dir" value={selectedJobQuery.data?.job_dir} />
                <Field label="Result path" value={selectedJobQuery.data?.result_path} />
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-200">Parameters</p>
                <pre className="max-h-56 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                  {JSON.stringify(detail.params, null, 2)}
                </pre>
              </div>

              <div className="grid gap-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-slate-200">Audit trail</p>
                  <p className="text-xs text-slate-500">{detail.audit_events.length} events</p>
                </div>
                {!detail.audit_events.length ? (
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                    No audit events yet.
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {detail.audit_events.map((event) => (
                      <AuditEventCard event={event} key={event.id} />
                    ))}
                  </div>
                )}
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-200">Logs</p>
                <pre className="max-h-56 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                  {jobLogsQuery.isLoading
                    ? 'Loading logs...'
                    : jobLogsQuery.error
                      ? getErrorMessage(jobLogsQuery.error)
                      : logs.length
                        ? logs.join('\n')
                        : 'No logs yet.'}
                </pre>
              </div>

              <div className="grid gap-3">
                <p className="text-sm font-medium text-slate-200">Artifacts</p>
                {!detail.artifacts.length ? (
                  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                    No artifacts attached.
                  </div>
                ) : (
                  <div className="grid gap-3">
                    {detail.artifacts.map((artifact, index) => (
                      <ArtifactCard
                        artifact={artifact}
                        key={`${artifact.kind}-${artifact.path}-${index}`}
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
              Close
            </Button>
            <Button variant="secondary" onClick={() => setRerunOpen(true)} disabled={!detail || rerunMutation.isPending || !canOperateJobs}>
              {rerunMutation.isPending ? 'Rerunning' : 'Rerun job'}
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
              {cancelMutation.isPending ? 'Cancelling' : 'Cancel job'}
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
            <DialogTitle>Confirm rerun</DialogTitle>
            <DialogDescription>
              This will create a new job with the same job type and parameter snapshot as the selected job.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Job type" value={detail?.job_type} />
              <Field label="Created by" value={detail?.created_by} />
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Parameters</p>
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
              Cancel
            </Button>
            <Button onClick={() => rerunMutation.mutate()} disabled={!detail || rerunMutation.isPending || !canOperateJobs}>
              {rerunMutation.isPending ? 'Submitting' : 'Confirm rerun'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
