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
        kicker="Overview"
        title="Operations at a glance"
        description="A data-dense entry page that shows the current system state, recent jobs, and the latest artifacts."
      />

      <section className="hero-panel">
        <div>
          <p className="page-kicker">trade-strategy-ai</p>
          <h1>Control console overview</h1>
          <p className="hero-copy">
            The shell now connects to live system health data and the newest task and artifact
            snapshots.
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
            <CardTitle>Why this layout</CardTitle>
            <CardDescription>Dense enough for operations, simple enough for quick scanning.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <ul className="list-disc space-y-2 pl-5 text-slate-400">
              <li>System status stays prominent so failures are obvious on first load.</li>
              <li>Recent jobs and artifacts are stacked to support a quick operational review.</li>
              <li>Each card keeps loading, empty, and error states local to its own data source.</li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Next step</CardTitle>
            <CardDescription>Route shell is ready for the task center and artifact center.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-slate-300">
            <p>WEB-S4-006 will replace these summary cards with actionable page content.</p>
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
