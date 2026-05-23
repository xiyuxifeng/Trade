type MarketWorkspaceSummaryProps = {
  taskCount: number;
  recentJobCount: number;
  failedJobCount: number;
  artifactCount: number;
};

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-slate-950">{value}</p>
    </div>
  );
}

export function MarketWorkspaceSummary({
  taskCount,
  recentJobCount,
  failedJobCount,
  artifactCount,
}: MarketWorkspaceSummaryProps) {
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <StatCard label="可运行任务" value={taskCount} />
      <StatCard label="最近任务" value={recentJobCount} />
      <StatCard label="重点告警" value={failedJobCount} />
      <StatCard label="最近产物" value={artifactCount} />
    </section>
  );
}
