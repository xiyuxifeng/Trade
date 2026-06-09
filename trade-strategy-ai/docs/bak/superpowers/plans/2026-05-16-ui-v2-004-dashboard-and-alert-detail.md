# UI-V2-004 Dashboard 首页与告警详情页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 V2 工作台首页改成“系统状态优先”的正式 Dashboard，并补一条独立的告警详情页链路，承接重点告警点击与深度查看。

**Architecture:** 保留 `/dashboard` 作为首页承载点，围绕现有 `SystemStatusPanel`、`RecentJobsPanel`、`RecentArtifactsPanel` 和告警历史 API 组织新的 Dashboard 布局。新增一个独立的告警详情页路由 `/alerts/:recordId`，让 Dashboard 只展示告警摘要，详情与处理动作进入单独页面，避免首页变成信息海报或告警中心。

**Tech Stack:** React 18, React Router, TanStack Query, Vitest, Testing Library, existing `fetchRootJson` API clients.

---

### Task 1: Dashboard 首屏重排与重点告警摘要

**Files:**
- Create: `web/src/components/dashboard/dashboard-status-summary.tsx`
- Create: `web/src/components/dashboard/dashboard-alert-strip.tsx`
- Create: `web/src/features/dashboard/use-dashboard-alert-summary.ts`
- Modify: `web/src/routes/overview.tsx`
- Modify: `web/src/pages/overview/index.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it('renders a system-first dashboard with alert summaries', () => {
  mockOverviewState(
    {
      data: {
        status: 'ok',
        config_path: '/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/config/app.yaml',
        project_root: '/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai',
        run_mode: 'api',
        database: {
          name: 'primary',
          status: 'ok',
          latency_ms: 18,
          details: {},
          error: null,
        },
        directories: {},
        warnings: [],
      },
    },
    {
      data: {
        count: 1,
        total: 1,
        skip: 0,
        limit: 5,
        items: [
          {
            id: 'job-1',
            job_type: 'snapshot-build',
            status: 'failed',
            created_by: 'web',
            started_at: '2026-05-16T09:00:00Z',
            finished_at: '2026-05-16T09:02:00Z',
          },
        ],
      },
    },
    {
      data: {
        count: 1,
        total: 1,
        skip: 0,
        limit: 5,
        items: [
          {
            artifact_id: 'artifact-1',
            name: 'snapshot.summary.json',
            path: 'data/processed/snapshots/snapshot.summary.json',
            kind: 'json',
            source: 'job',
            exists: true,
            size_bytes: 2048,
            modified_at: '2026-05-16T09:02:00Z',
            previewable: true,
            job_id: 'job-1',
            metadata: {},
            preview: '{}',
            download_name: 'snapshot.summary.json',
          },
        ],
      },
    },
  );

  renderWithRouter([{ path: '/dashboard', element: <OverviewPage /> }], ['/dashboard']);

  expect(screen.getByText('系统总览')).toBeInTheDocument();
  expect(screen.getByText('重点告警')).toBeInTheDocument();
  expect(screen.getByText('最近失败任务')).toBeInTheDocument();
  expect(screen.getByText('最近产物')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: '查看告警详情' })).toHaveAttribute('href', '/alerts/alert-1');
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node /Users/wanghui/.npm/_npx/*/node_modules/vitest/vitest.mjs run web/src/pages/overview/index.test.tsx -t "renders a system-first dashboard with alert summaries"
```

Expected: fail because `dashboard-status-summary.tsx` and `dashboard-alert-strip.tsx` do not exist yet, and `overview.tsx` still renders the old layout.

- [ ] **Step 3: Write minimal implementation**

```tsx
export function DashboardStatusSummary() {
  const { data: system } = useSystemStatus();
  const { data: jobs } = useRecentJobs();
  const { data: artifacts } = useRecentArtifacts();
  const { data: alerts } = useDashboardAlertSummary();

  const failedJobs = jobs?.items?.filter((job) => job.status === 'failed').length ?? 0;
  const recentArtifacts = artifacts?.items?.length ?? 0;
  const criticalAlerts = alerts?.items?.length ?? 0;

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <SummaryCard title="系统健康" value={system?.status ?? 'unknown'} />
      <SummaryCard title="今日运行" value={system?.run_mode ?? 'unknown'} />
      <SummaryCard title="失败任务" value={failedJobs} />
      <SummaryCard title="最近产物" value={recentArtifacts} />
      <SummaryCard title="Profile" value={system?.profile_status ?? 'unknown'} />
      <SummaryCard title="Market" value={system?.market_status ?? 'unknown'} />
      <SummaryCard title="重点告警" value={criticalAlerts} accent="text-amber-500" />
    </section>
  );
}
```

```tsx
export function DashboardAlertStrip() {
  const { data, isLoading, error, refetch } = useDashboardAlertSummary();

  if (isLoading) {
    return <AlertStripSkeleton />;
  }

  if (error) {
    return <AlertStripError message="重点告警加载失败" onRetry={() => refetch()} />;
  }

  return (
    <section aria-label="重点告警">
      <div className="flex flex-wrap gap-3">
        {data?.items.map((alert) => (
          <Link key={alert.id} to={`/alerts/${alert.id}`} className="alert-chip">
            <span className="alert-chip-level">{alert.level}</span>
            <span className="alert-chip-title">{alert.title}</span>
            <span className="alert-chip-time">{formatTimestamp(alert.created_at)}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
```

```tsx
export function OverviewRoute() {
  return (
    <main className="page-stack">
      <PageHeader kicker="概览" title="运维总览" description="系统状态优先的正式工作台入口。" />
      <DashboardStatusSummary />
      <DashboardAlertStrip />
      <section className="dashboard-grid dashboard-grid-overview">
        <RecentJobsPanel />
        <RecentArtifactsPanel />
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run:

```bash
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node /Users/wanghui/.npm/_npx/*/node_modules/vitest/vitest.mjs run web/src/pages/overview/index.test.tsx -t "renders a system-first dashboard with alert summaries"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/dashboard/dashboard-status-summary.tsx web/src/components/dashboard/dashboard-alert-strip.tsx web/src/features/dashboard/use-dashboard-alert-summary.ts web/src/routes/overview.tsx web/src/pages/overview/index.test.tsx
git commit -m "feat(ui): reshape dashboard around system status"
```

### Task 2: 独立告警详情页与路由

**Files:**
- Create: `web/src/pages/alerts/AlertDetailPage.tsx`
- Create: `web/src/features/alerts/alert-detail-panel.tsx`
- Create: `web/src/features/alerts/use-alert-detail.ts`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/features/alerts/alerts-center.tsx`
- Modify: `web/src/pages/alerts/index.tsx`
- Test: `web/src/pages/alerts/AlertDetailPage.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it('renders an alert detail page with acknowledge and resolve actions', async () => {
  renderWithRouter([{ path: '/alerts/:recordId', element: <AlertDetailPage /> }], ['/alerts/alert-1']);

  expect(await screen.findByText('告警详情')).toBeInTheDocument();
  expect(screen.getByText('alert-1')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '确认告警' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '解决告警' })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:

```bash
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node /Users/wanghui/.npm/_npx/*/node_modules/vitest/vitest.mjs run web/src/pages/alerts/AlertDetailPage.test.tsx -t "renders an alert detail page with acknowledge and resolve actions"
```

Expected: fail because the page, route, and shared alert detail panel do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```tsx
export function AlertDetailPage() {
  const { recordId = '' } = useParams<{ recordId: string }>();
  const detailQuery = useQuery({
    queryKey: ['alerts', 'detail', recordId],
    queryFn: () => getAlertHistory(recordId),
    enabled: Boolean(recordId),
  });

  return <AlertDetailPanel alert={detailQuery.data ?? null} />;
}
```

```tsx
export function AlertDetailPanel({ alert }: { alert: AlertHistoryItem | null }) {
  if (!alert) {
    return <EmptyState title="告警不存在" description="请返回 Dashboard 或告警中心重新选择一条记录。" />;
  }

  return (
    <main className="page-stack">
      <PageHeader
        kicker="告警"
        title={alert.title}
        description={alert.message ?? '告警详情与处理上下文。'}
      />
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="space-y-6">
          <AlertNarrativeCard alert={alert} />
          <AlertTimelineCard alert={alert} />
        </div>
        <AlertMetadataCard alert={alert} />
      </section>
    </main>
  );
}
```

```tsx
{
  path: 'alerts/:recordId',
  element: <AlertDetailPage />,
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run:

```bash
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node /Users/wanghui/.npm/_npx/*/node_modules/vitest/vitest.mjs run web/src/pages/alerts/AlertDetailPage.test.tsx -t "renders an alert detail page with acknowledge and resolve actions"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/alerts/AlertDetailPage.tsx web/src/features/alerts/alert-detail-panel.tsx web/src/features/alerts/use-alert-detail.ts web/src/app/router.tsx web/src/features/alerts/alerts-center.tsx web/src/pages/alerts/index.tsx web/src/pages/alerts/AlertDetailPage.test.tsx
git commit -m "feat(ui): add alert detail page"
```

### Task 3: 回归测试、TaskList 与会话同步

**Files:**
- Modify: `web/src/pages/overview/index.test.tsx`
- Modify: `web/src/pages/alerts/index.test.tsx`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-16.md`
- Modify: `daily-report/2026-05-16.md`

- [ ] **Step 1: Write the failing regression tests**

```tsx
it('navigates from dashboard alert summaries to the detail page', async () => {
  renderWithRouter(
    [
      { path: '/dashboard', element: <OverviewPage /> },
      { path: '/alerts/:recordId', element: <AlertDetailPage /> },
    ],
    ['/dashboard'],
  );

  await user.click(screen.getByRole('link', { name: '查看告警详情' }));
  expect(await screen.findByText('告警详情')).toBeInTheDocument();
});
```

```tsx
it('keeps the alert center history page intact while exposing detail links', () => {
  renderWithRouter([{ path: '/alerts', element: <AlertsPage /> }], ['/alerts']);
  expect(screen.getByText('告警中心')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: '查看详情' })).toHaveAttribute('href', '/alerts/alert-1');
});
```

- [ ] **Step 2: Run the regression tests and confirm they fail**

Run:

```bash
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node /Users/wanghui/.npm/_npx/*/node_modules/vitest/vitest.mjs run web/src/pages/overview/index.test.tsx web/src/pages/alerts/index.test.tsx web/src/pages/alerts/AlertDetailPage.test.tsx
```

Expected: fail until the dashboard links, alert detail route, and alert center links are all wired.

- [ ] **Step 3: Update TaskList and session notes**

Add a completion note for `UI-V2-004` only after the tests pass and the pages meet the spec:

```md
- [x] UI-V2-004 P0 Dashboard 首页
  - 已完成系统状态优先的首页重排。
  - 已把重点告警改为摘要 + 详情页跳转。
  - 已保留告警中心作为历史页，详情页独立承接深度查看。
```

- [ ] **Step 4: Run the full UI regression set**

Run:

```bash
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node /Users/wanghui/.npm/_npx/*/node_modules/vitest/vitest.mjs run web/src/pages/overview/index.test.tsx web/src/pages/alerts/index.test.tsx web/src/pages/alerts/AlertDetailPage.test.tsx web/src/app/route-registry.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/overview/index.test.tsx web/src/pages/alerts/index.test.tsx docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-16.md daily-report/2026-05-16.md
git commit -m "docs(ui): record dashboard and alert detail work"
```

## Self-Review Checklist

- Dashboard 首屏是否明确回答“系统是否正常”。
- 告警是否只在首页展示摘要，而不是把首页变成告警中心。
- 告警详情是否独立承接深度查看和动作。
- 文案是否保持中文优先，与 `UI-V2-002` 风格一致。
- 是否有任何 CLI 强化、Demo 式入口或新告警规则编辑混入。
- 是否有遗漏的 loading / empty / error / retry / not-found 状态。
- 是否存在和现有路由或告警中心冲突的路径命名。
