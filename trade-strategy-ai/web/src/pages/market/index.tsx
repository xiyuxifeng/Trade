import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, LoadingState, SectionCard } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { cn } from '@/lib/utils';
import { listArtifacts } from '@/lib/api/artifacts';
import { listJobs } from '@/lib/api/jobs';
import { getStockInfoStatus, listMarketDatasets, listMarketSnapshots } from '@/lib/api/market';
import type { ArtifactRecord } from '@/types/artifacts';
import type { JobRecord } from '@/types/jobs';
import type { StockInfoStatusResponse } from '@/types/market';

const MARKET_JOB_TYPES = new Set([
  'kaipan-fetch',
  'kaipan-normalize',
  'kaipan-run',
  'ohlcv-crawl',
  'market-state-build',
  'snapshot-build',
]);

function sortJobsByCreatedAtDesc(items: JobRecord[]) {
  return [...items].sort((left, right) => right.created_at.localeCompare(left.created_at));
}

function sortArtifactsByModifiedAtDesc(items: ArtifactRecord[]) {
  return [...items].sort((left, right) => (right.modified_at ?? '').localeCompare(left.modified_at ?? ''));
}

function FlowStepCard({
  number,
  title,
  description,
  statusLabel,
  statusTone,
  primaryLabel,
  primaryHref,
  secondaryLinks,
}: {
  number: string;
  title: string;
  description: string;
  statusLabel: string;
  statusTone: 'info' | 'success' | 'warning';
  primaryLabel: string;
  primaryHref: string;
  secondaryLinks: readonly { label: string; href: string }[];
}) {
  return (
    <article className="flex h-full flex-col rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm shadow-slate-200/40">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{number}</p>
          <h3 className="mt-1 text-lg font-semibold tracking-tight text-slate-950">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
        </div>
        <span
          className={cn(
            'inline-flex shrink-0 rounded-full px-3 py-1 text-xs font-medium',
            statusTone === 'success' && 'bg-emerald-50 text-emerald-700',
            statusTone === 'info' && 'bg-sky-50 text-sky-700',
            statusTone === 'warning' && 'bg-amber-50 text-amber-700',
          )}
        >
          {statusLabel}
        </span>
      </div>

      <div className="mt-auto flex flex-wrap gap-2 pt-4">
        <Link className="inline-flex h-10 items-center justify-center rounded-xl bg-slate-950 px-4 text-sm font-medium text-white transition-colors hover:bg-slate-800" to={primaryHref}>
          {primaryLabel}
        </Link>
        {secondaryLinks.map((link) => (
          <Link
            key={link.href}
            className="inline-flex h-10 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            to={link.href}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </article>
  );
}

export function MarketPage() {
  const snapshotsQuery = useQuery({
    queryKey: ['market-overview', 'snapshots'],
    queryFn: () => listMarketSnapshots({ limit: 1, offset: 0 }),
    staleTime: 30_000,
  });

  const datasetsQuery = useQuery({
    queryKey: ['market-overview', 'datasets'],
    queryFn: () => listMarketDatasets({ limit: 1, offset: 0 }),
    staleTime: 30_000,
  });

  const jobsQuery = useQuery({
    queryKey: ['market-overview', 'jobs'],
    queryFn: () => listJobs({ limit: 10 }),
    staleTime: 30_000,
  });

  const artifactsQuery = useQuery({
    queryKey: ['market-overview', 'artifacts'],
    queryFn: () => listArtifacts({ limit: 6 }),
    staleTime: 30_000,
  });

  const marketJobs = useMemo(
    () => sortJobsByCreatedAtDesc((jobsQuery.data?.items ?? []).filter((job) => MARKET_JOB_TYPES.has(job.job_type))),
    [jobsQuery.data?.items],
  );
  const failedJobs = useMemo(() => marketJobs.filter((job) => job.status === 'failed'), [marketJobs]);
  const latestSnapshot = snapshotsQuery.data?.items?.[0] ?? null;
  const latestDataset = datasetsQuery.data?.items?.[0] ?? null;
  const latestMarketJob = marketJobs[0] ?? null;
  const artifacts = useMemo(() => sortArtifactsByModifiedAtDesc((artifactsQuery.data?.items ?? []).slice(0, 6)), [artifactsQuery.data?.items]);
  const stockInfoStatusQuery = useQuery<StockInfoStatusResponse>({
    queryKey: ['market-overview', 'stock-info-status'],
    queryFn: () => getStockInfoStatus(7),
    staleTime: 30_000,
  });
  const stockInfoIsFresh = Boolean(stockInfoStatusQuery.data?.is_fresh);
  const snapshotsLoading = snapshotsQuery.isLoading;
  const datasetsLoading = datasetsQuery.isLoading;
  const jobsLoading = jobsQuery.isLoading;
  const artifactsLoading = artifactsQuery.isLoading;
  const stockInfoLoading = stockInfoStatusQuery.isLoading;
  const marketFlowSteps = [
    {
      number: '01',
      title: '先抓取',
      description: '先把原始市场数据备齐。',
      statusLabel: jobsLoading
        ? '正在加载任务'
        : latestMarketJob?.job_type === 'ohlcv-crawl' || latestMarketJob?.job_type === 'kaipan-run'
          ? '最近有抓取任务'
          : '等待抓取',
      statusTone: jobsLoading
        ? 'info'
        : latestMarketJob?.job_type === 'ohlcv-crawl' || latestMarketJob?.job_type === 'kaipan-run'
          ? 'info'
          : 'warning',
      primaryLabel: '打开 Kaipan 页面',
      primaryHref: '/market/kaipan',
      secondaryLinks: [],
    },
    {
      number: '02',
      title: '生成快照',
      description: '把抓取结果收敛成统一市场上下文快照，供后续分析复用。',
      statusLabel: snapshotsLoading ? '正在加载快照' : latestSnapshot ? '已有最近快照' : '等待生成快照',
      statusTone: snapshotsLoading ? 'info' : latestSnapshot ? 'success' : 'warning',
      primaryLabel: '打开快照页',
      primaryHref: '/market/snapshots',
      secondaryLinks: [
        { label: '查看市场上下文构建任务', href: '/jobs?job_type=snapshot-build' },
        { label: '查看市场上下文产物', href: '/artifacts?jobType=snapshot-build&source=market-snapshot-browser' },
      ],
    },
    {
      number: '03',
      title: '浏览数据集',
      description: '查看快照派生的数据集、分页样本和详情回链。',
      statusLabel: datasetsLoading ? '正在加载数据集' : latestDataset ? '已有最近数据集' : '等待数据集',
      statusTone: datasetsLoading ? 'info' : latestDataset ? 'success' : 'warning',
      primaryLabel: '打开数据集浏览',
      primaryHref: '/market/datasets',
      secondaryLinks: [
        { label: '查看快照列表', href: '/market/snapshots' },
      ],
    },
    {
      number: '04',
      title: '基础信息检查',
      description: '先确认股票与指数基础信息是否齐备，再进入 OHLCV 抓取。',
      statusLabel: stockInfoLoading ? '正在检查基础信息' : stockInfoIsFresh ? '基础信息已就绪' : '需要检查基础信息',
      statusTone: stockInfoLoading ? 'info' : stockInfoIsFresh ? 'success' : 'warning',
      primaryLabel: '前往 OHLCV 页面',
      primaryHref: '/market/ohlcv',
      secondaryLinks: [
        { label: '查看 OHLCV 任务', href: '/jobs?job_type=ohlcv-crawl' },
        { label: '查看 OHLCV 产物', href: '/artifacts?jobType=ohlcv-crawl' },
      ],
    },
  ] as const;

  return (
    <main className="page-stack">
      <PageHeader
        kicker="市场上下文"
        title="市场上下文"
        description="按正常数据流向操作：先抓取，再生成快照，再浏览数据集，最后做基础信息检查。"
      />

      <section className="grid gap-2 rounded-[28px] border border-slate-200 bg-white p-3 shadow-sm shadow-slate-200/40 xl:grid-cols-4">
        {marketFlowSteps.map((step) => (
          <div key={step.number} className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
            <p className="text-[11px] uppercase tracking-[0.16em] text-slate-500">{step.number}</p>
            <p className="mt-1 text-sm font-semibold text-slate-950">{step.title}</p>
            <p className="mt-1 text-xs leading-5 text-slate-600">{step.description}</p>
            <div className="mt-2">
              <span
                className={cn(
                  'inline-flex rounded-full px-2.5 py-1 text-[11px] font-medium',
                  step.statusTone === 'success' && 'bg-emerald-50 text-emerald-700',
                  step.statusTone === 'info' && 'bg-sky-50 text-sky-700',
                  step.statusTone === 'warning' && 'bg-amber-50 text-amber-700',
                )}
              >
                {step.statusLabel}
              </span>
            </div>
          </div>
        ))}
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)] xl:items-stretch">
        <section className="grid h-full grid-rows-4 gap-4">
          {marketFlowSteps.map((step) => (
            <FlowStepCard
              key={step.number}
              number={step.number}
              title={step.title}
              description={step.description}
              statusLabel={step.statusLabel}
              statusTone={step.statusTone}
              primaryLabel={step.primaryLabel}
              primaryHref={step.primaryHref}
              secondaryLinks={step.secondaryLinks}
            />
          ))}
        </section>

        <aside className="xl:sticky xl:top-6 xl:self-start">
          <SectionCard className="h-full" title="流程状态" description="查看当前进度和下一步。">
            <div className="space-y-3">
              {snapshotsQuery.error || datasetsQuery.error || jobsQuery.error || artifactsQuery.error ? (
                <ErrorState
                  {...buildErrorRecoveryState(
                    snapshotsQuery.error ?? datasetsQuery.error ?? jobsQuery.error ?? artifactsQuery.error,
                    'market',
                  )}
                  onRetry={() => {
                    void snapshotsQuery.refetch();
                    void datasetsQuery.refetch();
                    void jobsQuery.refetch();
                    void artifactsQuery.refetch();
                  }}
                />
              ) : null}
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">最近数据状态</p>
                  <p className="mt-1 text-base font-semibold text-slate-950">
                    {snapshotsLoading ? '加载中' : latestSnapshot ? latestSnapshot.quality_status || 'n/a' : '暂无'}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {snapshotsLoading
                      ? '正在读取最近快照概览'
                      : latestSnapshot
                        ? `${latestSnapshot.trade_date} · ${latestSnapshot.market} · ${latestSnapshot.snapshot_id}`
                        : '暂无快照记录'}
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">数据集总数</p>
                  <p className="mt-1 text-base font-semibold text-slate-950">{datasetsLoading ? '加载中' : datasetsQuery.data?.page.total ?? 0}</p>
                  <p className="mt-1 text-xs text-slate-500">当前可浏览的市场数据集数量</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">快照总数</p>
                  <p className="mt-1 text-base font-semibold text-slate-950">{snapshotsLoading ? '加载中' : snapshotsQuery.data?.page.total ?? 0}</p>
                  <p className="mt-1 text-xs text-slate-500">当前可浏览的市场上下文快照数量</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">失败任务</p>
                  <p className="mt-1 text-base font-semibold text-slate-950">{jobsLoading ? '加载中' : failedJobs.length}</p>
                  <p className="mt-1 text-xs text-slate-500">最近失败的市场相关 Job</p>
                </div>
              </div>

            </div>
          </SectionCard>
        </aside>
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <SectionCard
          title="最近失败任务"
          description="仅显示最需要处理的市场相关失败任务。"
          action={<Link className="text-sm font-medium text-sky-700 hover:underline" to="/jobs?status=failed">查看任务中心</Link>}
        >
          {jobsLoading ? (
            <LoadingState label="正在加载最近任务" description="稍后会显示最近提交的市场任务和执行结果。" />
          ) : jobsQuery.error ? (
            <ErrorState
              {...buildErrorRecoveryState(jobsQuery.error, 'market')}
              onRetry={() => {
                void jobsQuery.refetch();
              }}
            />
          ) : failedJobs.length ? (
            <div className="space-y-3">
              {failedJobs.slice(0, 4).map((job) => (
                <div key={job.id} className="rounded-2xl border border-rose-200 bg-rose-50 p-4">
                  <p className="font-medium text-slate-900">{job.job_type}</p>
                  <p className="mt-1 text-sm text-slate-600">{typeof job.error === 'string' ? job.error : job.error?.message ?? '任务失败'}</p>
                  <div className="mt-3 flex items-center gap-3">
                    <Link className="text-sm font-medium text-sky-700 hover:underline" to={`/jobs/${job.id}`}>
                      查看 Job 详情
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="当前没有需要处理的市场告警。" description="当市场任务失败时，会在这里显示。" />
          )}
        </SectionCard>

        <SectionCard
          title="最近产物"
          description="查看市场链路生成的快照、报告和导出文件。"
          action={<Link className="text-sm font-medium text-sky-700 hover:underline" to="/artifacts">查看产物中心</Link>}
        >
          {artifactsLoading ? (
            <LoadingState label="正在加载最近产物" description="稍后会显示市场链路生成的快照、报告和导出文件。" />
          ) : artifactsQuery.error ? (
            <ErrorState
              {...buildErrorRecoveryState(artifactsQuery.error, 'market')}
              onRetry={() => {
                void artifactsQuery.refetch();
              }}
            />
          ) : artifacts.length ? (
            <div className="max-h-72 space-y-3 overflow-auto pr-1">
              {artifacts.map((artifact) => (
                <div key={artifact.artifact_id} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <p className="font-medium text-slate-900">{artifact.name}</p>
                  <p className="mt-1 text-sm text-slate-500">
                    {artifact.kind} · {artifact.source} · {artifact.modified_at ?? '未记录'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="暂无最近产物。" description="当市场链路生成产物后，这里会显示最新记录。" />
          )}
        </SectionCard>
      </section>
    </main>
  );
}
