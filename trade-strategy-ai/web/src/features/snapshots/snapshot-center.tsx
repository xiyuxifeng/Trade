import { useEffect, useMemo, useState, type ReactNode } from 'react';
import dayjs from 'dayjs';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/layout/page-header';
import { ApiError } from '@/lib/api/http';
import { createJob } from '@/lib/api/jobs';
import { getSnapshot, listSnapshots } from '@/lib/api/snapshots';
import type { JobSubmissionRequest } from '@/types/jobs';
import type { SnapshotDetail, SnapshotListResponse, SnapshotSummaryItem, SnapshotType } from '@/types/snapshots';
import { useNavigate } from 'react-router-dom';

const DEFAULT_CONFIG_PATH = 'config/app.yaml';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return '快照数据加载失败';
}

function sortSnapshotsDesc(items: SnapshotSummaryItem[]) {
  return [...items].sort((left, right) => {
    const dateDiff = right.trade_date.localeCompare(left.trade_date);
    if (dateDiff !== 0) return dateDiff;
    return right.slot.localeCompare(left.slot);
  });
}

function typeLabel(type: SnapshotType) {
  if (type === 'hot_topics') return '热题材';
  if (type === 'topic_constituents') return '题材成分';
  if (type === 'strong_symbols') return '强势标的';
  return '候选池';
}

function SnapshotSummaryCard({
  title,
  value,
  accent = 'text-slate-100',
}: {
  title: string;
  value: string | number;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function SnapshotRow({
  snapshot,
  active,
  onSelect,
}: {
  snapshot: SnapshotSummaryItem;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      data-testid={`snapshot-row-${snapshot.snapshot_id}`}
      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
        active
          ? 'border-sky-500/40 bg-sky-500/10 text-sky-100'
          : 'border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
      }`}
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium">{snapshot.trade_date} {snapshot.slot}</p>
          <p className="mt-1 break-all text-xs text-slate-500">{snapshot.snapshot_id}</p>
        </div>
        <Badge variant={active ? 'info' : 'default'}>{typeLabel(snapshot.type)}</Badge>
      </div>
    </button>
  );
}

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <h4 className="text-sm font-semibold text-slate-100">{title}</h4>
      <div className="mt-3">{children}</div>
    </div>
  );
}

function SnapshotDetailView({ detail }: { detail: SnapshotDetail }) {
  const hotTopics = detail.hot_topics?.topics ?? [];
  const constituents = detail.topic_constituents?.constituents ?? [];
  const strongSymbols = detail.strong_symbols?.symbols ?? [];

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div data-testid="snapshot-detail-trade-date">
          <SnapshotSummaryCard title="Trade date" value={detail.trade_date} accent="text-sky-300" />
        </div>
        <div data-testid="snapshot-detail-slot">
          <SnapshotSummaryCard title="Slot" value={detail.slot} accent="text-sky-300" />
        </div>
        <SnapshotSummaryCard title="Hot topics" value={hotTopics.length} />
        <SnapshotSummaryCard title="Strong symbols" value={strongSymbols.length} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Hot topics">
          {hotTopics.length ? (
            <ul className="space-y-2 text-sm text-slate-300">
              {hotTopics.map((item) => (
                <li key={`${item.kind}-${item.topic_id}`} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span>{item.topic_name}</span>
                    <span className="text-xs text-slate-500">{item.kind}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    score {item.score ?? 'n/a'} · increase {item.increase_pct ?? 'n/a'}%
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">暂无热题材。</p>
          )}
        </SectionCard>

        <SectionCard title="Topic constituents">
          {constituents.length ? (
            <ul className="space-y-2 text-sm text-slate-300">
              {constituents.map((item) => (
                <li key={`${item.kind}-${item.topic_id}-${item.symbol}`} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span>{item.topic_name ?? '未命名题材'}</span>
                    <span className="text-xs text-slate-500">{item.symbol ?? 'unknown'}</span>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">暂无题材成分。</p>
          )}
        </SectionCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Strong symbols">
          {strongSymbols.length ? (
            <ul className="space-y-2 text-sm text-slate-300">
              {strongSymbols.map((item) => (
                <li key={`${item.kind}-${item.symbol}`} className="rounded-xl border border-slate-800/70 bg-slate-950/50 px-3 py-2">
                  <div className="flex items-center justify-between gap-3">
                    <span>{item.name ?? item.symbol ?? 'unknown'}</span>
                    <span className="text-xs text-slate-500">{item.kind}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">strength {item.strength_score ?? 'n/a'}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-400">暂无强势标的。</p>
          )}
        </SectionCard>

        <SectionCard title="Raw JSON">
          <pre
            className="max-h-[30rem] overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200"
            data-testid="snapshot-detail-json"
          >
            {JSON.stringify(detail, null, 2)}
          </pre>
        </SectionCard>
      </div>
    </div>
  );
}

function toBuildParams(form: {
  dateStart: string;
  dateEnd: string;
  slot: string;
  snapshotType: SnapshotType | 'all';
  force: boolean;
  offline: boolean;
}) {
  return {
    config_path: DEFAULT_CONFIG_PATH,
    date: form.dateStart === form.dateEnd ? form.dateStart : undefined,
    start_date: form.dateStart,
    end_date: form.dateEnd,
    slot: form.slot,
    snapshot_type: form.snapshotType,
    force: form.force,
    offline: form.offline,
  };
}

export function SnapshotsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const today = useMemo(() => dayjs().format('YYYY-MM-DD'), []);
  const defaultStart = useMemo(() => dayjs().subtract(30, 'day').format('YYYY-MM-DD'), []);
  const [dateStart, setDateStart] = useState(defaultStart);
  const [dateEnd, setDateEnd] = useState(today);
  const [slot, setSlot] = useState('17-30');
  const [snapshotType, setSnapshotType] = useState<SnapshotType | 'all'>('all');
  const [force, setForce] = useState(false);
  const [offline, setOffline] = useState(false);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(null);
  const [submittedJobId, setSubmittedJobId] = useState<string | null>(null);

  const snapshotsQuery = useQuery<SnapshotListResponse, ApiError>({
    queryKey: ['snapshots', { dateStart, dateEnd, snapshotType }],
    queryFn: () =>
      listSnapshots({
        date_start: dateStart,
        date_end: dateEnd,
        type: snapshotType === 'all' ? undefined : snapshotType,
        limit: 50,
      }),
    staleTime: 10_000,
  });

  const snapshots = useMemo(() => sortSnapshotsDesc(snapshotsQuery.data?.items ?? []), [snapshotsQuery.data?.items]);

  useEffect(() => {
    if (!snapshots.length) {
      setSelectedSnapshotId(null);
      return;
    }
    if (!selectedSnapshotId || !snapshots.some((item) => item.snapshot_id === selectedSnapshotId)) {
      setSelectedSnapshotId(snapshots[0].snapshot_id);
    }
  }, [selectedSnapshotId, snapshots]);

  const selectedSnapshot = useMemo(
    () => snapshots.find((item) => item.snapshot_id === selectedSnapshotId) ?? null,
    [selectedSnapshotId, snapshots],
  );

  const detailQuery = useQuery({
    queryKey: ['snapshot-detail', selectedSnapshotId],
    queryFn: () => getSnapshot(selectedSnapshotId as string),
    enabled: Boolean(selectedSnapshotId),
  });

  const buildMutation = useMutation({
    mutationFn: async () => {
      const request: JobSubmissionRequest = {
        job_type: 'snapshot-build',
        params: toBuildParams({ dateStart, dateEnd, slot, snapshotType, force, offline }),
        created_by: 'web',
        max_retries: 3,
        retry_backoff_seconds: 0,
        timeout_seconds: null,
      };
      return createJob(request);
    },
    onSuccess: async (result) => {
      setSubmittedJobId(result.job?.id ?? null);
      await queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const summary = useMemo(() => {
    const total = snapshotsQuery.data?.total ?? 0;
    const hotTopics = detailQuery.data?.item.hot_topics?.topics.length ?? 0;
    const strongSymbols = detailQuery.data?.item.strong_symbols?.symbols.length ?? 0;
    return { total, hotTopics, strongSymbols };
  }, [detailQuery.data?.item.hot_topics?.topics.length, detailQuery.data?.item.strong_symbols?.symbols.length, snapshotsQuery.data?.total]);

  return (
    <main className="page-stack">
      <PageHeader
        kicker="Snapshots"
        title="快照中心"
        description="构建候选池快照，查看 hot topics、topic constituents 和 strong symbols 的历史结果。"
        actionLabel="Open Jobs"
        onAction={() => navigate('/jobs')}
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(320px,0.8fr)_minmax(0,1.2fr)]">
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>构建快照</CardTitle>
                <CardDescription>快照构建必须通过 Job 提交，避免直接在页面内执行长任务。</CardDescription>
              </div>
              <Button variant="outline" onClick={() => snapshotsQuery.refetch()} disabled={snapshotsQuery.isFetching}>
                {snapshotsQuery.isFetching ? '刷新中' : '刷新'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-300">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Start date</span>
                <Input type="date" value={dateStart} onChange={(event) => setDateStart(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">End date</span>
                <Input type="date" value={dateEnd} onChange={(event) => setDateEnd(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Slot</span>
                <Input value={slot} onChange={(event) => setSlot(event.target.value)} placeholder="17-30" />
              </label>
              <label className="space-y-2 text-sm text-slate-300">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Snapshot type</span>
                <Select value={snapshotType} onChange={(event) => setSnapshotType(event.target.value as SnapshotType | 'all')}>
                  <option value="all">all</option>
                  <option value="hot_topics">hot_topics</option>
                  <option value="topic_constituents">topic_constituents</option>
                  <option value="strong_symbols">strong_symbols</option>
                </Select>
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-300">
                <input checked={force} onChange={(event) => setForce(event.target.checked)} type="checkbox" />
                Force rebuild
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-slate-300">
                <input checked={offline} onChange={(event) => setOffline(event.target.checked)} type="checkbox" />
                Offline mode
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <SnapshotSummaryCard title="Total" value={summary.total} />
              <SnapshotSummaryCard title="Selected hot topics" value={summary.hotTopics} accent="text-sky-300" />
              <SnapshotSummaryCard title="Selected strong symbols" value={summary.strongSymbols} accent="text-amber-300" />
            </div>

            <div className="flex flex-wrap gap-3">
              <Button onClick={() => buildMutation.mutate()} disabled={buildMutation.isPending}>
                {buildMutation.isPending ? '提交中' : '构建快照'}
              </Button>
              {submittedJobId ? (
                <Button variant="outline" onClick={() => navigate(`/jobs?jobId=${encodeURIComponent(submittedJobId)}`)}>
                  View Job
                </Button>
              ) : null}
            </div>

            {buildMutation.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(buildMutation.error)}
              </div>
            ) : null}

            {submittedJobId ? (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
                Snapshot job submitted: {submittedJobId}
              </div>
            ) : null}

            {snapshotsQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : snapshotsQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(snapshotsQuery.error)}
              </div>
            ) : !snapshots.length ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                当前范围内暂无快照。
              </div>
            ) : (
              <div className="space-y-3">
                {snapshots.map((snapshot) => (
                  <SnapshotRow
                    active={snapshot.snapshot_id === selectedSnapshotId}
                    key={snapshot.snapshot_id}
                    onSelect={() => setSelectedSnapshotId(snapshot.snapshot_id)}
                    snapshot={snapshot}
                  />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>快照详情</CardTitle>
                <CardDescription>
                  {selectedSnapshot ? `${selectedSnapshot.trade_date} ${selectedSnapshot.slot}` : '请选择一条快照记录。'}
                </CardDescription>
              </div>
              {selectedSnapshot ? <Badge variant="info">{typeLabel(selectedSnapshot.type)}</Badge> : null}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedSnapshot ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                当前范围内没有可展示的快照。
              </div>
            ) : detailQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-[28rem] w-full" />
              </div>
            ) : detailQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(detailQuery.error)}
              </div>
            ) : detailQuery.data?.item ? (
              <Tabs defaultValue="summary" className="w-full">
                <TabsList>
                  <TabsTrigger value="summary">Summary</TabsTrigger>
                  <TabsTrigger value="json">JSON</TabsTrigger>
                </TabsList>
                <TabsContent value="summary">
                  <SnapshotDetailView detail={detailQuery.data.item} />
                </TabsContent>
                <TabsContent value="json">
                  <pre
                    className="max-h-[40rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200"
                    data-testid="snapshot-json"
                  >
                    {JSON.stringify(detailQuery.data.item, null, 2)}
                  </pre>
                </TabsContent>
              </Tabs>
            ) : null}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
