import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { RecentArtifactsPanel } from '@/components/status/recent-artifacts-panel';
import { RecentJobsPanel } from '@/components/status/recent-jobs-panel';
import { SystemStatusPanel } from '@/features/system-status/system-status-panel';

const quickNotes = [
  'API base defaults to /api/ui/v1',
  'X-API-Key is read from localStorage when present',
  'Overview page reflects live system health, jobs, and artifacts',
];

export function OverviewRoute() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="概览"
        title="运维概览"
        description="数据密集的入口页面，显示当前系统状态、最近任务和最新产物。"
      />

      <section className="hero-panel">
        <div>
          <p className="page-kicker">trade-strategy-ai</p>
          <h1>控制台概览</h1>
          <p className="hero-copy">
            控制台现已连接到实时系统健康数据，以及最新的任务和产物快照。
          </p>
        </div>

        <div className="hero-rail">
          {quickNotes.map((note) => (
            <div className="hero-chip" key={note}>
              {note}
            </div>
          ))}
        </div>
      </section>

      <section className="dashboard-grid dashboard-grid-overview">
        <SystemStatusPanel />

        <div className="grid gap-6">
          <RecentJobsPanel />
          <RecentArtifactsPanel />
        </div>
      </section>

      <section className="dashboard-grid">
        <Card>
          <CardHeader>
            <CardTitle>设计理念</CardTitle>
            <CardDescription>足够密集以支持运维，足够简单以支持快速扫描。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <ul className="list-disc space-y-2 pl-5 text-slate-400">
              <li>系统状态保持突出显示，以便在首次加载时能明显发现故障。</li>
              <li>最近的任务和产物被组织在一起，以支持快速的运行审查。</li>
              <li>每个卡片都为自己的数据源保留了加载、空值和错误状态。</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>下一步</CardTitle>
            <CardDescription>路由外壳已为任务中心和产物中心准备就绪。</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <p>WEB-S4-006 将用可交互的页面内容替换这些摘要卡片。</p>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
