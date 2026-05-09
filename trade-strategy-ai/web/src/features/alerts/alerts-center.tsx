import { useEffect, useMemo, useState } from 'react';
import dayjs from 'dayjs';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageHeader } from '@/components/layout/page-header';
import { ApiError } from '@/lib/api/http';
import {
  acknowledgeAlert,
  getAlertHistory,
  listAlertHistory,
  resolveAlert,
  sendTestAlert,
} from '@/lib/api/alerts';
import type { AlertHistoryItem, AlertHistoryResponse } from '@/types/alerts';

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return '告警数据加载失败';
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return '未记录';
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function sortAlertsDesc(items: AlertHistoryItem[]) {
  return [...items].sort((left, right) => {
    const rightTime = right.created_at ?? right.sent_at ?? '';
    const leftTime = left.created_at ?? left.sent_at ?? '';
    const timeDiff = rightTime.localeCompare(leftTime);
    if (timeDiff !== 0) return timeDiff;
    return right.id.localeCompare(left.id);
  });
}

function statusVariant(status: string) {
  if (status === 'resolved') return 'success';
  if (status === 'acknowledged') return 'info';
  if (status === 'pending' || status === 'sent') return 'warning';
  return 'default';
}

function levelVariant(level: string) {
  if (level === 'CRITICAL') return 'destructive';
  if (level === 'WARNING') return 'warning';
  return 'info';
}

function SummaryCard({ title, value, accent = 'text-slate-100' }: { title: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold ${accent}`}>{value}</p>
    </div>
  );
}

function AlertRow({
  item,
  active,
  onSelect,
}: {
  item: AlertHistoryItem;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
        active
          ? 'border-sky-500/40 bg-sky-500/10 text-sky-100'
          : 'border-slate-800 bg-slate-950/60 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
      }`}
      onClick={onSelect}
      type="button"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-medium">{item.title}</p>
          <p className="break-all text-xs text-slate-500">{item.alert_id}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge variant={statusVariant(item.status)}>{item.status}</Badge>
          <Badge variant={levelVariant(item.level)}>{item.level}</Badge>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
        <span className="rounded-full border border-slate-800/80 px-2 py-1">{item.channel}</span>
        <span className="rounded-full border border-slate-800/80 px-2 py-1">{formatTimestamp(item.created_at)}</span>
        <span className="rounded-full border border-slate-800/80 px-2 py-1">x{item.aggregated_count}</span>
      </div>
      {item.message ? <p className="mt-3 line-clamp-2 text-sm text-slate-400">{item.message}</p> : null}
    </button>
  );
}

function AlertDetailSummary({ alert }: { alert: AlertHistoryItem }) {
  const tags = alert.tags.length ? alert.tags.join(', ') : 'n/a';
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <SummaryCard title="Alert ID" value={alert.alert_id} accent="text-sky-300" />
      <SummaryCard title="Channel" value={alert.channel} />
      <SummaryCard title="Aggregated" value={alert.aggregated_count} accent="text-emerald-300" />
      <SummaryCard title="Tags" value={tags} />
    </div>
  );
}

export function AlertsCenter() {
  const queryClient = useQueryClient();
  const today = useMemo(() => dayjs().format('YYYY-MM-DD'), []);
  const defaultStart = useMemo(() => dayjs().subtract(30, 'day').format('YYYY-MM-DD'), []);

  const [status, setStatus] = useState('');
  const [level, setLevel] = useState('');
  const [tag, setTag] = useState('');
  const [dateFrom, setDateFrom] = useState(defaultStart);
  const [dateTo, setDateTo] = useState(today);
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(50);
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  function resetFilters() {
    setStatus('');
    setLevel('');
    setTag('');
    setDateFrom(defaultStart);
    setDateTo(today);
    setSkip(0);
    setLimit(50);
  }

  const historyQuery = useQuery<AlertHistoryResponse, Error>({
    queryKey: ['alerts', 'history', status, level, tag, dateFrom, dateTo, skip, limit],
    queryFn: () =>
      listAlertHistory({
        status: status || undefined,
        level: level || undefined,
        tag: tag || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        skip,
        limit,
      }),
    staleTime: 10_000,
  });

  const alerts = useMemo(() => sortAlertsDesc(historyQuery.data?.items ?? []), [historyQuery.data?.items]);

  useEffect(() => {
    if (!alerts.length) {
      setSelectedAlertId(null);
      return;
    }
    if (!selectedAlertId || !alerts.some((item) => item.id === selectedAlertId)) {
      setSelectedAlertId(alerts[0].id);
    }
  }, [alerts, selectedAlertId]);

  const selectedAlert = useMemo(
    () => alerts.find((item) => item.id === selectedAlertId) ?? null,
    [alerts, selectedAlertId],
  );

  const detailQuery = useQuery<AlertHistoryItem, Error>({
    queryKey: ['alerts', 'detail', selectedAlertId],
    queryFn: () => getAlertHistory(selectedAlertId as string),
    enabled: Boolean(selectedAlertId),
  });

  const acknowledgeMutation = useMutation({
    mutationFn: () => acknowledgeAlert(selectedAlertId as string, 'web'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setActionMessage('Alert acknowledged.');
      setActionError(null);
    },
    onError: (error) => {
      setActionError(getErrorMessage(error));
      setActionMessage(null);
    },
  });

  const resolveMutation = useMutation({
    mutationFn: () => resolveAlert(selectedAlertId as string, 'web'),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setActionMessage('Alert resolved.');
      setActionError(null);
    },
    onError: (error) => {
      setActionError(getErrorMessage(error));
      setActionMessage(null);
    },
  });

  const testAlertMutation = useMutation({
    mutationFn: () => sendTestAlert(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setActionMessage('Test alert sent.');
      setActionError(null);
      setTestDialogOpen(false);
    },
    onError: (error) => {
      setActionError(getErrorMessage(error));
      setActionMessage(null);
    },
  });

  const selectedDetail = detailQuery.data ?? null;
  const summary = useMemo(() => {
    const total = historyQuery.data?.total ?? 0;
    const pending = alerts.filter((item) => item.status === 'pending' || item.status === 'sent').length;
    const acknowledged = alerts.filter((item) => item.status === 'acknowledged').length;
    const resolved = alerts.filter((item) => item.status === 'resolved').length;
    return { total, pending, acknowledged, resolved };
  }, [alerts, historyQuery.data?.total]);

  const activeFilters = useMemo(() => {
    const items = [
      status ? `Status: ${status}` : null,
      level ? `Level: ${level}` : null,
      tag ? `Tag: ${tag}` : null,
      dateFrom !== defaultStart || dateTo !== today ? `Date: ${dateFrom} ~ ${dateTo}` : null,
      skip ? `Skip: ${skip}` : null,
      limit !== 50 ? `Limit: ${limit}` : null,
    ].filter((item): item is string => Boolean(item));
    return items;
  }, [dateFrom, dateTo, defaultStart, level, limit, skip, status, tag, today]);

  return (
    <main className="page-stack">
      <PageHeader
        kicker="Alerts"
        title="Alerts Center"
        description="Review alert history, acknowledge or resolve incidents, and send a test alert after confirming webhook wiring."
        actionLabel="Send test alert"
        onAction={() => setTestDialogOpen(true)}
      />

      <section className="grid gap-6 xl:grid-cols-[minmax(360px,0.92fr)_minmax(0,1.08fr)]">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Alert history</CardTitle>
                  <CardDescription>Filter by status, level, tag, and date range.</CardDescription>
                </div>
                <Button variant="outline" onClick={() => historyQuery.refetch()} disabled={historyQuery.isFetching}>
                  {historyQuery.isFetching ? '刷新中' : '刷新'}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Status</span>
                  <Select value={status} onChange={(event) => setStatus(event.target.value)}>
                    <option value="">All statuses</option>
                    <option value="pending">pending</option>
                    <option value="sent">sent</option>
                    <option value="acknowledged">acknowledged</option>
                    <option value="resolved">resolved</option>
                  </Select>
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Level</span>
                  <Select value={level} onChange={(event) => setLevel(event.target.value)}>
                    <option value="">All levels</option>
                    <option value="CRITICAL">CRITICAL</option>
                    <option value="WARNING">WARNING</option>
                    <option value="INFO">INFO</option>
                  </Select>
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Tag</span>
                  <Input value={tag} onChange={(event) => setTag(event.target.value)} placeholder="snapshot" />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Date from</span>
                  <Input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Date to</span>
                  <Input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Skip</span>
                  <Input type="number" min={0} value={skip} onChange={(event) => setSkip(Number(event.target.value) || 0)} />
                </label>
                <label className="space-y-2 text-sm text-slate-300">
                  <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Limit</span>
                  <Input type="number" min={1} max={100} value={limit} onChange={(event) => setLimit(Math.max(1, Number(event.target.value) || 50))} />
                </label>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs uppercase tracking-[0.16em] text-slate-500">Quick actions</span>
                <Button size="sm" variant="ghost" onClick={resetFilters}>
                  Reset filters
                </Button>
              </div>

              <div className="grid gap-3 md:grid-cols-4">
                <SummaryCard title="Total" value={summary.total} accent="text-sky-300" />
                <SummaryCard title="Pending" value={summary.pending} accent="text-amber-300" />
                <SummaryCard title="Acknowledged" value={summary.acknowledged} accent="text-emerald-300" />
                <SummaryCard title="Resolved" value={summary.resolved} accent="text-sky-300" />
              </div>

              <div className="text-xs text-slate-500">
                {historyQuery.data ? `${historyQuery.data.total} total / ${alerts.length} shown` : '等待告警数据加载'}
                {activeFilters.length ? <p className="mt-1 max-w-sm">{activeFilters.join(' · ')}</p> : <p className="mt-1">No active filters.</p>}
              </div>

              {historyQuery.isLoading ? (
                <div className="space-y-3">
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                  <Skeleton className="h-20 w-full" />
                </div>
              ) : historyQuery.error ? (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                  {getErrorMessage(historyQuery.error)}
                </div>
              ) : !alerts.length ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 text-sm text-slate-400">
                  <p className="text-base font-medium text-slate-200">当前筛选范围内暂无告警历史。</p>
                  <p className="mt-2">可以放宽日期范围、切换状态或级别，然后重新查询。</p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button size="sm" onClick={resetFilters}>
                      Reset filters
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="grid gap-3">
                  {alerts.map((item) => (
                    <AlertRow
                      key={item.id}
                      active={item.id === selectedAlertId}
                      item={item}
                      onSelect={() => setSelectedAlertId(item.id)}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {actionMessage ? (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-100">
              {actionMessage}
            </div>
          ) : null}

          {actionError ? (
            <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
              {actionError}
            </div>
          ) : null}
        </div>

        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <CardTitle>Alert details</CardTitle>
                <CardDescription>
                  {selectedAlert ? `${selectedAlert.title} · ${selectedAlert.alert_id}` : 'Select an alert to inspect details.'}
                </CardDescription>
              </div>
              {selectedAlert ? (
                <div className="flex flex-wrap gap-2">
                  <Badge variant={statusVariant(selectedAlert.status)}>{selectedAlert.status}</Badge>
                  <Badge variant={levelVariant(selectedAlert.level)}>{selectedAlert.level}</Badge>
                </div>
              ) : null}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedAlert ? (
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-400">
                No alert selected yet.
              </div>
            ) : detailQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-[28rem] w-full" />
              </div>
            ) : detailQuery.error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
                {getErrorMessage(detailQuery.error)}
              </div>
            ) : selectedDetail ? (
              <Tabs defaultValue="summary" className="w-full">
                <TabsList className="flex flex-wrap">
                  <TabsTrigger value="summary">Summary</TabsTrigger>
                  <TabsTrigger value="json">JSON</TabsTrigger>
                </TabsList>

                <TabsContent value="summary" className="space-y-4">
                  <AlertDetailSummary alert={selectedDetail} />

                  <div className="grid gap-3 md:grid-cols-3">
                    <SummaryCard title="Created at" value={formatTimestamp(selectedDetail.created_at)} accent="text-sky-300" />
                    <SummaryCard title="Sent at" value={formatTimestamp(selectedDetail.sent_at)} />
                    <SummaryCard title="Aggregation key" value={selectedDetail.aggregation_key ?? 'n/a'} accent="text-emerald-300" />
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <h4 className="text-sm font-semibold text-slate-100">Message</h4>
                      <p className="mt-3 whitespace-pre-wrap text-sm text-slate-300">{selectedDetail.message ?? 'No message available.'}</p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {selectedDetail.tags.map((item) => (
                          <Badge key={item} variant="default">
                            {item}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <h4 className="text-sm font-semibold text-slate-100">Actions</h4>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button onClick={() => acknowledgeMutation.mutate()} disabled={acknowledgeMutation.isPending || resolveMutation.isPending}>
                          Acknowledge
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => resolveMutation.mutate()}
                          disabled={acknowledgeMutation.isPending || resolveMutation.isPending}
                        >
                          Resolve
                        </Button>
                      </div>
                      <p className="mt-3 text-xs text-slate-500">Actions update the record in the history table immediately after success.</p>
                    </div>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <h4 className="text-sm font-semibold text-slate-100">Timeline</h4>
                      <dl className="mt-3 space-y-2 text-sm text-slate-300">
                        <div className="flex items-center justify-between gap-3">
                          <dt className="text-slate-500">Acknowledged</dt>
                          <dd>{formatTimestamp(selectedDetail.acknowledged_at)}</dd>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                          <dt className="text-slate-500">Resolved</dt>
                          <dd>{formatTimestamp(selectedDetail.resolved_at)}</dd>
                        </div>
                      </dl>
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
                      <h4 className="text-sm font-semibold text-slate-100">Metadata</h4>
                      <pre className="mt-3 max-h-60 overflow-auto rounded-xl border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-200">
                        {JSON.stringify(selectedDetail.alert_metadata, null, 2)}
                      </pre>
                    </div>
                  </div>
                </TabsContent>

                <TabsContent value="json">
                  <pre className="max-h-[40rem] overflow-auto rounded-2xl border border-slate-800 bg-slate-950/80 p-4 text-xs text-slate-200">
                    {JSON.stringify(selectedDetail, null, 2)}
                  </pre>
                </TabsContent>
              </Tabs>
            ) : null}
          </CardContent>
        </Card>
      </section>

      <Dialog open={testDialogOpen} onOpenChange={setTestDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Send test alert?</DialogTitle>
            <DialogDescription>
              This will send a webhook test message so you can verify the alerting configuration before using it in production.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTestDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => testAlertMutation.mutate()} disabled={testAlertMutation.isPending}>
              {testAlertMutation.isPending ? 'Sending…' : 'Send test alert'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
