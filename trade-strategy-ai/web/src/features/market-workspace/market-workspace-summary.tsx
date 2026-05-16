import { SectionCard } from '@/components/kit';

type MarketWorkspaceSummaryProps = {
  taskCount: number;
  recentJobCount: number;
  failedJobCount: number;
  artifactCount: number;
};

function StatCard({ label, value, hint }: { label: string; value: string | number; hint: string }) {
  return (
    <SectionCard title={label} description={hint}>
      <p className="text-2xl font-semibold text-slate-950">{value}</p>
    </SectionCard>
  );
}

export function MarketWorkspaceSummary({
  taskCount,
  recentJobCount,
  failedJobCount,
  artifactCount,
}: MarketWorkspaceSummaryProps) {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <StatCard label="可运行任务" value={taskCount} hint="当前可在 Web 中直接提交的市场任务" />
      <StatCard label="最近任务" value={recentJobCount} hint="最近采样到的市场相关 Job" />
      <StatCard label="重点告警" value={failedJobCount} hint="最近失败的市场任务" />
      <StatCard label="最近产物" value={artifactCount} hint="可用于复盘的市场产物" />
    </section>
  );
}
