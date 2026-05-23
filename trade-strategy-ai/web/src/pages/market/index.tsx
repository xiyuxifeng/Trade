import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/layout/page-header';
import { EmptyState, LoadingState, SectionCard } from '@/components/kit';
import { ErrorState } from '@/components/state/ErrorState';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { listArtifacts } from '@/lib/api/artifacts';
import { listJobs } from '@/lib/api/jobs';
import { listMarketDatasets, listMarketSnapshots } from '@/lib/api/market';
import type { ArtifactRecord } from '@/types/artifacts';
import type { JobRecord } from '@/types/jobs';

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

function StatTile({ label, value, hint }: { label: string; value: string | number; hint: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-sm text-slate-600">{hint}</p>
    </div>
  );
}

function QuickLink({ label, href, description }: { label: string; href: string; description: string }) {
  return (
    <Link className="rounded-2xl border border-slate-200 bg-white p-4 transition-colors hover:bg-slate-50" to={href}>
      <p className="font-medium text-slate-950">{label}</p>
      <p className="mt-1 text-sm text-slate-600">{description}</p>
    </Link>
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
    queryFn: () => listJobs({ limit: 20 }),
    staleTime: 30_000,
  });

  const artifactsQuery = useQuery({
    queryKey: ['market-overview', 'artifacts'],
    queryFn: () => listArtifacts({ limit: 12 }),
    staleTime: 30_000,
  });

  const marketJobs = useMemo(
    () => sortJobsByCreatedAtDesc((jobsQuery.data?.items ?? []).filter((job) => MARKET_JOB_TYPES.has(job.job_type))),
    [jobsQuery.data?.items],
  );
  const failedJobs = useMemo(() => marketJobs.filter((job) => job.status === 'failed'), [marketJobs]);
  const latestSnapshot = snapshotsQuery.data?.items?.[0] ?? null;
  const latestDataset = datasetsQuery.data?.items?.[0] ?? null;
  const artifacts = useMemo(() => sortArtifactsByModifiedAtDesc((artifactsQuery.data?.items ?? []).slice(0, 6)), [artifactsQuery.data?.items]);

  const pageError = snapshotsQuery.error ?? datasetsQuery.error ?? jobsQuery.error ?? artifactsQuery.error;

  if (snapshotsQuery.isLoading || datasetsQuery.isLoading || jobsQuery.isLoading || artifactsQuery.isLoading) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="市场数据"
          title="市场数据"
          description="市场数据总览：从这里进入快照、数据集、Kaipan 和 OHLCV 子页面。"
        />
        <LoadingState label="正在加载市场总览" description="正在读取快照、数据集、任务和产物概览。" />
      </main>
    );
  }

  if (pageError) {
    return (
      <main className="page-stack">
        <PageHeader
          kicker="市场数据"
          title="市场数据"
          description="市场数据总览：从这里进入快照、数据集、Kaipan 和 OHLCV 子页面。"
        />
        <ErrorState
          {...buildErrorRecoveryState(pageError, 'market')}
          onRetry={() => {
            void snapshotsQuery.refetch();
            void datasetsQuery.refetch();
            void jobsQuery.refetch();
            void artifactsQuery.refetch();
          }}
        />
      </main>
    );
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="市场数据"
        title="市场数据"
        description="市场数据总览：从这里进入快照、数据集、Kaipan 和 OHLCV 子页面。"
      />

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile
          label="最近数据状态"
          value={latestSnapshot ? latestSnapshot.quality_status || 'n/a' : '暂无'}
          hint={latestSnapshot ? `${latestSnapshot.trade_date} · ${latestSnapshot.market} · ${latestSnapshot.snapshot_id}` : '暂无快照记录'}
        />
        <StatTile label="快照总数" value={snapshotsQuery.data?.page.total ?? 0} hint="当前可浏览的市场快照数量" />
        <StatTile label="数据集总数" value={datasetsQuery.data?.page.total ?? 0} hint="当前可浏览的市场数据集数量" />
        <StatTile label="最近失败任务" value={failedJobs.length} hint="最近失败的市场相关 Job" />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="市场快照" description="浏览快照、构建快照、查看 snapshot-build 任务和产物。">
          <div className="grid gap-3 md:grid-cols-2">
            <QuickLink label="快照浏览" href="/market/snapshots" description="查看快照列表、详情、质量与派生特征。" />
            <QuickLink label="构建快照" href="/strategies/pre-market" description="提交 snapshot-build 和盘前准备任务。" />
            <QuickLink label="查看 snapshot-build 任务" href="/jobs?job_type=snapshot-build" description="查看最近的快照构建任务。" />
            <QuickLink label="查看快照产物" href="/artifacts?jobType=snapshot-build&source=market-snapshot-browser" description="浏览快照构建产物与报告。" />
          </div>
        </SectionCard>

        <SectionCard title="市场数据集" description="浏览数据集并查看关联回链。">
          <div className="grid gap-3 md:grid-cols-2">
            <QuickLink label="数据集浏览" href="/market/datasets" description="查看市场数据集、分页样本与详情。" />
            <QuickLink label="前往快照" href="/market/snapshots" description="从数据集回到对应快照视图。" />
            <QuickLink label="查看最新数据集" href={latestDataset ? `/market/datasets?trade_date=${latestDataset.trade_date}&market=${latestDataset.market}&dataset_id=${encodeURIComponent(latestDataset.dataset_id)}` : '/market/datasets'} description="直接打开当前最新数据集记录。" />
            <QuickLink label="产物中心" href="/artifacts" description="查看数据集相关产物与导出文件。" />
          </div>
        </SectionCard>

        <SectionCard title="Kaipan 数据" description="手动抓取、归一化和健康检查都在子页面里完成。">
          <QuickLink label="进入 Kaipan 页面" href="/market/kaipan" description="抓取、归一化、任务历史和健康检查都在这里。" />
        </SectionCard>

        <SectionCard title="OHLCV 行情" description="抓取、回灌和最近任务都集中在子页面。">
          <QuickLink label="进入 OHLCV 页面" href="/market/ohlcv" description="增量、区间、指定 symbols 和最近任务都在这里。" />
        </SectionCard>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <SectionCard
          title="最近失败任务"
          description="仅显示最需要处理的市场相关失败任务。"
          action={<Link className="text-sm font-medium text-sky-700 hover:underline" to="/jobs?status=failed">查看任务中心</Link>}
        >
          {failedJobs.length ? (
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
          {artifacts.length ? (
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
