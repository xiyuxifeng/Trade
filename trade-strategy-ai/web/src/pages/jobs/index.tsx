import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from '@/components/ui/drawer';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/http';
import { cancelJob, getJob, getJobLogs, listJobs } from '@/lib/api/jobs';
import type { JobDetailResponse, JobsListResponse } from '@/types/jobs';
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

export function JobsPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState('');
  const [jobType, setJobType] = useState('');
  const [createdBy, setCreatedBy] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

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

  const cancelMutation = useMutation({
    mutationFn: () => cancelJob(selectedJobId as string, 'web console request'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
      await queryClient.invalidateQueries({ queryKey: ['job-detail', selectedJobId] });
      await queryClient.invalidateQueries({ queryKey: ['job-logs', selectedJobId] });
    },
  });

  const detail = selectedJobQuery.data?.job ?? null;
  const logs = jobLogsQuery.data?.items ?? [];

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
        description="View recent jobs, inspect details, review logs, and cancel running work."
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
                <table className="w-full border-collapse text-left text-sm">
                  <thead className="bg-slate-950/80 text-xs uppercase tracking-[0.16em] text-slate-500">
                    <tr>
                      <th className="px-4 py-3">Job</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Created by</th>
                      <th className="px-4 py-3">Created</th>
                      <th className="px-4 py-3">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobsQuery.data.items.map((job) => (
                      <tr
                        className="border-t border-slate-800/80 hover:bg-slate-900/70"
                        key={job.id}
                      >
                        <td className="px-4 py-3">
                          <div className="space-y-1">
                            <p className="font-medium text-slate-100">{job.job_type}</p>
                            <p className="text-xs text-slate-500 break-all">{job.id}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-300">{job.created_by}</td>
                        <td className="px-4 py-3 text-slate-300">{formatTimestamp(job.created_at)}</td>
                        <td className="px-4 py-3">
                          <Button variant="outline" size="sm" onClick={() => setSelectedJobId(job.id)}>
                            Details
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
          </CardContent>
        </Card>
      </section>

      <Drawer open={Boolean(selectedJobId)} onOpenChange={(open) => !open && setSelectedJobId(null)}>
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
                  <pre className="max-h-40 overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                    {JSON.stringify(detail.artifacts, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}

          <DrawerFooter>
            <Button variant="outline" onClick={() => setSelectedJobId(null)}>
              Close
            </Button>
            <Button
              variant="destructive"
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending || !detail || detail.status === 'success'}
            >
              {cancelMutation.isPending ? 'Cancelling' : 'Cancel job'}
            </Button>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </main>
  );
}
