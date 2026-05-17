import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, ErrorState, JsonViewer, LoadingState, SectionCard, StatusBadge } from '@/components/kit';
import { formatTimestamp } from '@/components/artifacts/artifact-utils';
import { useAuth } from '@/features/auth/auth-context';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { getJobAuditDetail, listJobAudits } from '@/lib/api/job-audits';
import type { JobAuditListItem } from '@/types/job-audits';

function buildSearchParams(base: URLSearchParams, patch: Record<string, string | null | undefined>) {
  const next = new URLSearchParams(base);
  Object.entries(patch).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') {
      next.delete(key);
      return;
    }
    next.set(key, value);
  });
  return next;
}

function confirmedLabel(value: boolean | null) {
  if (value === true) return '已确认';
  if (value === false) return '未确认';
  return '未记录';
}

function AuditSummaryCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
    </div>
  );
}

function EventTableRow({
  item,
  selected,
  onSelect,
}: {
  item: JobAuditListItem;
  selected: boolean;
  onSelect: (jobId: string) => void;
}) {
  return (
    <TableRow
      className={selected ? 'bg-sky-50/80 hover:bg-sky-50/80' : 'hover:bg-slate-50'}
      onClick={() => onSelect(item.job_id)}
      role="button"
      tabIndex={0}
    >
      <TableCell className="min-w-36 whitespace-nowrap text-slate-700">
        <div className="space-y-1">
          <p className="font-medium text-slate-950">{formatTimestamp(item.event_at)}</p>
          <p className="text-xs text-slate-500">{item.job_id}</p>
        </div>
      </TableCell>
      <TableCell className="text-slate-700">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={item.confirmed ? 'success' : 'warning'}>{confirmedLabel(item.confirmed)}</Badge>
          <Badge variant="info">{item.operation}</Badge>
        </div>
      </TableCell>
      <TableCell className="text-slate-700">{item.job_type}</TableCell>
      <TableCell className="text-slate-700">{item.actor}</TableCell>
      <TableCell className="text-slate-700">
        <StatusBadge value={item.job_status} />
      </TableCell>
    </TableRow>
  );
}

export function AdminAuditWorkspace() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { canAccess } = useAuth();
  const canManage = canAccess('admin');

  const actor = searchParams.get('actor') ?? '';
  const jobType = searchParams.get('job_type') ?? '';
  const operation = searchParams.get('operation') ?? '';
  const startDate = searchParams.get('start_date') ?? '';
  const endDate = searchParams.get('end_date') ?? '';
  const confirmed = searchParams.get('confirmed') ?? 'all';
  const jobId = searchParams.get('job_id') ?? '';

  const listQuery = useQuery({
    queryKey: ['job-audits', actor, jobType, operation, startDate, endDate, confirmed],
    queryFn: () =>
      listJobAudits({
        actor: actor || undefined,
        job_type: jobType || undefined,
        operation: operation || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        confirmed: confirmed === 'all' ? null : confirmed === 'true',
        skip: 0,
        limit: 20,
      }),
    enabled: canManage,
    staleTime: 30_000,
  });

  const auditItems = listQuery.data?.items ?? [];
  const selectedJobId = jobId || auditItems[0]?.job_id || '';

  useEffect(() => {
    if (!canManage || !auditItems.length) {
      return;
    }
    const currentJobExists = auditItems.some((item) => item.job_id === jobId);
    if (!jobId || !currentJobExists) {
      setSearchParams(
        buildSearchParams(searchParams, {
          job_id: auditItems[0]?.job_id ?? null,
        }),
        { replace: true },
      );
    }
  }, [auditItems, canManage, jobId, searchParams, setSearchParams]);

  const detailQuery = useQuery({
    queryKey: ['job-audit-detail', selectedJobId],
    queryFn: () => getJobAuditDetail(selectedJobId),
    enabled: canManage && Boolean(selectedJobId),
    staleTime: 30_000,
  });

  const detail = detailQuery.data ?? null;
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  useEffect(() => {
    if (!detail?.items.length) {
      setSelectedEventId(null);
      return;
    }
    if (!selectedEventId || !detail.items.some((item) => item.id === selectedEventId)) {
      setSelectedEventId(detail.items[0].id);
    }
  }, [detail, selectedEventId]);

  const selectedEvent = useMemo(() => {
    if (!detail?.items.length) {
      return null;
    }
    return detail.items.find((item) => item.id === selectedEventId) ?? detail.items[0];
  }, [detail, selectedEventId]);

  if (!canManage) {
    return (
      <main className="page-stack">
        <ErrorState
          category="permission denied"
          title="没有权限访问审计中心"
          description="当前身份需要 admin 权限。"
          suggestion="请切换到管理员账号后重试，或返回管理中心。"
          actions={[{ label: '返回管理中心', to: '/admin' }]}
        />
      </main>
    );
  }

  if (listQuery.error) {
    return (
      <main className="page-stack">
        <ErrorState
          {...buildErrorRecoveryState(listQuery.error, 'admin-audit')}
          onRetry={() => {
            void listQuery.refetch();
          }}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="配置与管理"
        title="权限与审计"
        description="查看关键操作、确认轨迹和 Job 审计详情，保持和现有正式工作台一致的浅色界面。"
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          to="/admin"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回管理中心
        </Link>
        <Button
          variant="outline"
          className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
          onClick={() => {
            listQuery.refetch();
            detailQuery.refetch();
          }}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <AuditSummaryCard label="审计事件" value={listQuery.data?.summary.total ?? 0} />
        <AuditSummaryCard label="已确认" value={listQuery.data?.summary.confirmed_count ?? 0} />
        <AuditSummaryCard label="高风险操作" value={listQuery.data?.summary.high_risk_count ?? 0} />
        <AuditSummaryCard label="关联 Job" value={listQuery.data?.summary.unique_jobs ?? 0} />
      </section>

      <SectionCard title="筛选条件" description="按 actor、job type、operation、日期和确认状态过滤审计记录。">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <label className="space-y-2 text-sm text-slate-600">
            <span>Actor</span>
            <Input
              className="border-slate-200 bg-white text-slate-700 placeholder:text-slate-400"
              value={actor}
              onChange={(event) => {
                setSearchParams(
                  buildSearchParams(searchParams, {
                    actor: event.target.value || null,
                    job_id: null,
                  }),
                );
              }}
              placeholder="web / worker / admin"
            />
          </label>
          <label className="space-y-2 text-sm text-slate-600">
            <span>Job Type</span>
            <Input
              className="border-slate-200 bg-white text-slate-700 placeholder:text-slate-400"
              value={jobType}
              onChange={(event) => {
                setSearchParams(
                  buildSearchParams(searchParams, {
                    job_type: event.target.value || null,
                    job_id: null,
                  }),
                );
              }}
              placeholder="backtest-run / pipeline-run"
            />
          </label>
          <label className="space-y-2 text-sm text-slate-600">
            <span>Operation</span>
            <Input
              className="border-slate-200 bg-white text-slate-700 placeholder:text-slate-400"
              value={operation}
              onChange={(event) => {
                setSearchParams(
                  buildSearchParams(searchParams, {
                    operation: event.target.value || null,
                    job_id: null,
                  }),
                );
              }}
              placeholder="create / cancel / review"
            />
          </label>
          <label className="space-y-2 text-sm text-slate-600">
            <span>开始日期</span>
            <Input
              className="border-slate-200 bg-white text-slate-700"
              type="date"
              value={startDate}
              onChange={(event) => {
                setSearchParams(
                  buildSearchParams(searchParams, {
                    start_date: event.target.value || null,
                    job_id: null,
                  }),
                );
              }}
            />
          </label>
          <label className="space-y-2 text-sm text-slate-600">
            <span>结束日期</span>
            <Input
              className="border-slate-200 bg-white text-slate-700"
              type="date"
              value={endDate}
              onChange={(event) => {
                setSearchParams(
                  buildSearchParams(searchParams, {
                    end_date: event.target.value || null,
                    job_id: null,
                  }),
                );
              }}
            />
          </label>
          <label className="space-y-2 text-sm text-slate-600">
            <span>确认状态</span>
            <Select
              className="border-slate-200 bg-white text-slate-700"
              value={confirmed}
              onChange={(event) => {
                setSearchParams(
                  buildSearchParams(searchParams, {
                    confirmed: event.target.value === 'all' ? null : event.target.value,
                    job_id: null,
                  }),
                );
              }}
            >
              <option value="all">全部</option>
              <option value="true">已确认</option>
              <option value="false">未确认</option>
            </Select>
          </label>
          <div className="flex items-end gap-2 md:col-span-2 xl:col-span-5">
            <Button
              variant="outline"
              className="border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              onClick={() => {
                setSearchParams(
                  buildSearchParams(searchParams, {
                    actor: null,
                    job_type: null,
                    operation: null,
                    start_date: null,
                    end_date: null,
                    confirmed: null,
                    job_id: null,
                  }),
                );
              }}
            >
              重置筛选
            </Button>
          </div>
        </div>
      </SectionCard>

      <SectionCard title="审计事件列表" description="只展示结构化审计事件，不暴露 secret 或服务器绝对路径。">
        {listQuery.isLoading ? (
          <LoadingState label="正在加载审计事件" description="正在获取 Job 审计列表和确认轨迹。" />
        ) : auditItems.length ? (
          <div className="space-y-4">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间 / Job</TableHead>
                  <TableHead>操作</TableHead>
                  <TableHead>Job Type</TableHead>
                  <TableHead>Actor</TableHead>
                  <TableHead>状态</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                        {auditItems.map((item) => (
                          <EventTableRow
                            key={item.id}
                            item={item}
                            selected={item.job_id === selectedJobId}
                    onSelect={(nextJobId) => {
                      setSearchParams(
                        buildSearchParams(searchParams, {
                          job_id: nextJobId,
                        }),
                      );
                    }}
                  />
                ))}
              </TableBody>
            </Table>
            <p className="text-xs text-slate-500">
              当前仅显示最近 {listQuery.data?.page.limit ?? 20} 条事件；分页可以在需要时再扩展，不在这里堆控制台能力。
            </p>
          </div>
        ) : (
          <EmptyState
            title="没有匹配的审计记录"
            description="当前筛选条件下没有审计事件。"
            actionLabel="清空筛选"
            onAction={() => {
              setSearchParams(new URLSearchParams());
            }}
          />
        )}
      </SectionCard>

      <SectionCard title="Job 审计详情" description={detail?.job.id ?? '选择一条事件后查看对应 Job。'}>
        {detailQuery.isLoading ? (
          <LoadingState label="正在加载审计详情" description="正在获取 Job 摘要、审计事件和产物引用。" />
        ) : detailQuery.error ? (
          <ErrorState
            {...buildErrorRecoveryState(detailQuery.error, 'admin-audit-detail')}
            onRetry={() => {
              void detailQuery.refetch();
            }}
          />
        ) : detail ? (
          <div className="space-y-6">
            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Job ID</p>
                <p className="mt-1 break-all text-sm text-slate-950">{detail.job.id}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Job Type</p>
                <p className="mt-1 text-sm text-slate-950">{detail.job.job_type}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">状态</p>
                <div className="mt-1">
                  <StatusBadge value={detail.job.status} />
                </div>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">创建者</p>
                <p className="mt-1 text-sm text-slate-950">{detail.job.created_by ?? '未记录'}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">事件数</p>
                <p className="mt-1 text-sm text-slate-950">{detail.summary.event_count}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">已确认</p>
                <p className="mt-1 text-sm text-slate-950">{detail.summary.confirmed_count}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">产物</p>
                <p className="mt-1 text-sm text-slate-950">{detail.summary.has_artifacts ? '有' : '无'}</p>
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs uppercase tracking-[0.16em] text-slate-500">审计轨迹</p>
                    <h3 className="mt-1 text-lg font-semibold text-slate-950">事件列表</h3>
                  </div>
                    <Link className="text-sm font-medium text-sky-700 hover:underline" to={`/jobs/${detail.job.id}`}>
                      打开 Job 详情
                    </Link>
                  </div>
                  <div className="mt-4 overflow-auto rounded-2xl border border-slate-200">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>时间</TableHead>
                          <TableHead>操作</TableHead>
                          <TableHead>确认</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detail.items.map((item) => (
                          <TableRow
                            key={item.id}
                            className={selectedEvent?.id === item.id ? 'bg-sky-50/80 hover:bg-sky-50/80' : 'hover:bg-slate-50'}
                            onClick={() => setSelectedEventId(item.id)}
                            role="button"
                            tabIndex={0}
                          >
                            <TableCell className="whitespace-nowrap text-slate-700">{formatTimestamp(item.event_at)}</TableCell>
                            <TableCell className="text-slate-700">
                              <div className="flex flex-wrap items-center gap-2">
                                <Badge variant="info">{item.operation}</Badge>
                                <span className="text-xs text-slate-500">{item.actor}</span>
                              </div>
                            </TableCell>
                            <TableCell className="text-slate-700">{confirmedLabel(item.confirmed)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">关联产物</p>
                  {detail.job.artifacts.length ? (
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      {detail.job.artifacts.map((artifact) => (
                        <div key={artifact.artifact_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                          <p className="text-sm font-medium text-slate-950">{artifact.title}</p>
                          <p className="mt-1 text-xs text-slate-500">{artifact.kind}</p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {artifact.safe_download_url ? (
                              <a className="text-sm font-medium text-sky-700 hover:underline" href={artifact.safe_download_url}>
                                下载
                              </a>
                            ) : null}
                            <Link className="text-sm font-medium text-sky-700 hover:underline" to="/artifacts">
                              打开产物中心
                            </Link>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm text-slate-600">该 Job 暂无关联产物。</p>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">当前事件</p>
                  <p className="mt-1 text-lg font-semibold text-slate-950">{selectedEvent?.operation ?? '未选择'}</p>
                  <p className="mt-1 text-sm text-slate-600">
                    {selectedEvent ? `${selectedEvent.actor} · ${formatTimestamp(selectedEvent.event_at)}` : '选择一条事件查看请求上下文和 payload。'}
                  </p>
                  {selectedEvent ? (
                    <div className="mt-4 space-y-3">
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">确认状态</p>
                          <p className="mt-1 text-sm text-slate-950">{confirmedLabel(selectedEvent.confirmed)}</p>
                        </div>
                        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">来源</p>
                          <p className="mt-1 text-sm text-slate-950">{selectedEvent.source}</p>
                        </div>
                      </div>
                      <JsonViewer value={selectedEvent.params_summary} title="params_summary" />
                      <JsonViewer value={selectedEvent.payload} title="payload" />
                    </div>
                  ) : null}
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">请求上下文</p>
                  <JsonViewer value={detail.request_context} title="request_context" />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <EmptyState
            title="暂无审计详情"
            description="先从上面的审计列表选择一个 Job。"
          />
        )}
      </SectionCard>
    </main>
  );
}
