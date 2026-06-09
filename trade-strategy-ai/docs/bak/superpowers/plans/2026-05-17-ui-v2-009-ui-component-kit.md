# UI-V2-009 UI Component Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified V2 UI component kit so Job, Profile, Market, and Strategy pages share the same light-theme workbench primitives instead of each page reimplementing its own base state and layout components.

**Architecture:** Keep the existing V2 visual language from `UI-V2-002`: white surfaces, light borders, restrained blue accents, and explicit loading / empty / error / retry states. Introduce a focused shared kit under `web/src/components/kit` and migrate the current V2 pages to consume it through thin adapters where needed. Do not change workflow contracts, API contracts, route structure, or CLI surfaces.

**Tech Stack:** React, TypeScript, TanStack Query, React Router, existing `@/components/ui/*` primitives, existing page and feature modules, and the current Vitest + Testing Library setup.

---

## File Structure

### Purpose-driven file map

- Create: `web/src/components/kit/index.ts` - single public export for the shared V2 kit.
- Create: `web/src/components/kit/section-card.tsx` - reusable light-theme section shell.
- Create: `web/src/components/kit/status-badge.tsx` - generic status badge for job/profile/market/strategy states.
- Create: `web/src/components/kit/risk-badge.tsx` - reusable severity / risk badge with V2 colors.
- Create: `web/src/components/kit/loading-state.tsx` - shared loading surface.
- Create: `web/src/components/kit/empty-state.tsx` - shared empty surface with action button support.
- Create: `web/src/components/kit/confirm-dialog.tsx` - shared confirmation dialog wrapper for destructive or high-risk actions.
- Create: `web/src/components/kit/json-viewer.tsx` - shared readable JSON block with copy-safe formatting.
- Create: `web/src/components/kit/log-viewer.tsx` - shared log viewer with empty and loading states.
- Create: `web/src/components/kit/schema-form.tsx` - thin shared form shell for structured V2 forms.
- Create: `web/src/components/kit/kit.test.tsx` - regression coverage for shared primitives and exports.
- Modify: `web/src/components/layout/page-header.tsx` - keep the existing implementation, but align the public export path through the kit barrel.
- Modify: `web/src/components/state/ErrorState.tsx` - keep the current visual language, but export through the kit barrel so pages import one shared surface.
- Modify: `web/src/components/artifacts/artifact-list.tsx` - keep the current grouped artifact UI, but expose it through the kit barrel as a shared primitive.
- Modify: `web/src/components/profiles/ProfileStatusBadge.tsx` - thin wrapper over the generic `StatusBadge`.
- Modify: `web/src/components/profiles/ProfileEmptyState.tsx` - thin wrapper over the generic `EmptyState`.
- Modify: `web/src/pages/jobs/JobDetailPage.tsx` - replace local shell and viewer duplication with shared kit components.
- Modify: `web/src/pages/jobs/JobDetailPage.test.tsx` - lock the new shared component output.
- Modify: `web/src/pages/profiles/ProfileListPage.tsx` - replace local empty / badge / section patterns with shared kit components.
- Modify: `web/src/pages/profiles/ProfileDetailPage.tsx` - replace local section and badge patterns with shared kit components.
- Modify: `web/src/pages/profiles/ProfileEditPage.tsx` - reuse the shared form shell and status badge where the page currently duplicates base UI.
- Modify: `web/src/pages/profiles/ProfileImportPage.tsx` - reuse the shared form and loading/empty surfaces where needed.
- Modify: `web/src/features/market-workspace/market-workspace-shell.tsx` - replace page-local shells with shared kit components.
- Modify: `web/src/features/market-workspace/market-workspace-summary.tsx` - reuse shared cards/badges instead of custom wrappers.
- Modify: `web/src/features/market-workspace/market-workspace-errors.tsx` - align with shared `ErrorState` and `EmptyState`.
- Modify: `web/src/features/market-workspace/market-workspace-recent-jobs.tsx` - reuse shared status / empty / loading primitives.
- Modify: `web/src/features/market-workspace/market-workspace-artifacts.tsx` - reuse shared `ArtifactList`, `JsonViewer`, and `LogViewer`.
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx` - replace local `SectionCard` / state shells with shared kit components.
- Modify: `web/src/features/strategy-workspace/strategy-workspace-actions.tsx` - use the shared `ConfirmDialog`.
- Modify: `web/src/features/strategy-workspace/strategy-workspace-history.tsx` - reuse shared `LoadingState`, `EmptyState`, `ErrorState`, and status badges.
- Modify: `web/src/features/strategy-workspace/strategy-workspace-artifacts.tsx` - reuse shared `ArtifactList`, `JsonViewer`, and `SectionCard`.
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx` - ensure the shell still renders the V2 workbench copy after refactor.
- Modify: `web/src/features/strategy-workspace/strategy-workspace-actions.test.tsx` - ensure confirm flow and job submission still work.
- Modify: `web/src/features/strategy-workspace/strategy-workspace-history.test.tsx` - lock the shared loading / empty / error states.
- Modify: `web/src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx` - lock the shared artifact and JSON viewer output.
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md` only after implementation and verification pass.
- Modify: `daily-sessions/2026-05-17.md` and `daily-report/2026-05-17.md` only after implementation and verification pass.

## Scope Check

This task only covers V2 shared UI primitives and their adoption by V2 pages.

It must not:
- add or strengthen CLI commands
- change API or workflow contracts
- change job runner behavior
- introduce a second visual language
- force a V1 migration
- move business logic into the component kit

It must:
- reduce duplicate page chrome and base-state UI
- preserve the existing V2 light workbench look
- keep shared components thin and reusable
- allow V1 to consume the kit later without forcing a V1 rewrite now
- keep Job, Profile, Market, and Strategy pages on the same surface vocabulary

---

## Task 1: Create the shared V2 kit and compatibility exports

**Files:**
- Create: `web/src/components/kit/index.ts`
- Create: `web/src/components/kit/section-card.tsx`
- Create: `web/src/components/kit/status-badge.tsx`
- Create: `web/src/components/kit/risk-badge.tsx`
- Create: `web/src/components/kit/loading-state.tsx`
- Create: `web/src/components/kit/empty-state.tsx`
- Create: `web/src/components/kit/confirm-dialog.tsx`
- Create: `web/src/components/kit/json-viewer.tsx`
- Create: `web/src/components/kit/log-viewer.tsx`
- Create: `web/src/components/kit/schema-form.tsx`
- Create: `web/src/components/kit/kit.test.tsx`
- Modify: `web/src/components/layout/page-header.tsx`
- Modify: `web/src/components/state/ErrorState.tsx`
- Modify: `web/src/components/artifacts/artifact-list.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  ConfirmDialog,
  EmptyState,
  ErrorState,
  JsonViewer,
  LoadingState,
  LogViewer,
  PageHeader,
  RiskBadge,
  SchemaForm,
  SectionCard,
  StatusBadge,
} from '@/components/kit';

describe('kit', () => {
  it('exports the shared V2 workbench primitives', () => {
    render(
      <SectionCard title="章节标题" description="章节说明">
        <PageHeader kicker="正式入口" title="标题" description="说明" />
        <StatusBadge value="validated" />
        <RiskBadge value="high" />
        <LoadingState label="加载中" />
        <EmptyState title="暂无数据" description="先完成一次提交再查看。" />
        <ErrorState
          category="data empty"
          title="任务不存在"
          description="无法读取任务详情。"
          suggestion="请返回任务列表重新选择一个 Job。"
        />
        <JsonViewer value={{ ok: true }} />
        <LogViewer lines={['line-1', 'line-2']} />
        <SchemaForm title="表单" description="说明" />
        <ConfirmDialog open={false} title="确认" description="确认继续？" />
      </SectionCard>,
    );

    expect(screen.getByText('章节标题')).toBeInTheDocument();
    expect(screen.getByText('正式入口')).toBeInTheDocument();
    expect(screen.getByText('加载中')).toBeInTheDocument();
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/components/kit/kit.test.tsx`

Expected: FAIL because the kit barrel and the shared primitives do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```tsx
// web/src/components/kit/index.ts
export { PageHeader } from '@/components/layout/page-header';
export { ErrorState } from '@/components/state/ErrorState';
export { ArtifactList } from '@/components/artifacts/artifact-list';
export { SectionCard } from './section-card';
export { StatusBadge } from './status-badge';
export { RiskBadge } from './risk-badge';
export { LoadingState } from './loading-state';
export { EmptyState } from './empty-state';
export { ConfirmDialog } from './confirm-dialog';
export { JsonViewer } from './json-viewer';
export { LogViewer } from './log-viewer';
export { SchemaForm } from './schema-form';
```

```tsx
// web/src/components/kit/section-card.tsx
export function SectionCard({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[28px] border border-slate-200 bg-white p-6 shadow-sm">
      {/* V2 light workbench section shell */}
    </section>
  );
}
```

```tsx
// web/src/components/kit/loading-state.tsx
export function LoadingState({ label }: { label: string }) {
  return <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">{label}</div>;
}
```

- [ ] **Step 4: Re-run the test**

Run: `cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/components/kit/kit.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/kit web/src/components/layout/page-header.tsx web/src/components/state/ErrorState.tsx web/src/components/artifacts/artifact-list.tsx
git commit -m "feat(ui): add shared v2 component kit"
```

---

## Task 2: Refactor Job and Profile pages onto the shared kit

**Files:**
- Modify: `web/src/pages/jobs/JobDetailPage.tsx`
- Modify: `web/src/pages/jobs/JobDetailPage.test.tsx`
- Modify: `web/src/pages/profiles/ProfileListPage.tsx`
- Modify: `web/src/pages/profiles/ProfileListPage.test.tsx`
- Modify: `web/src/pages/profiles/ProfileDetailPage.tsx`
- Modify: `web/src/pages/profiles/ProfileDetailPage.test.tsx`
- Modify: `web/src/pages/profiles/ProfileEditPage.tsx`
- Modify: `web/src/pages/profiles/ProfileEditPage.test.tsx`
- Modify: `web/src/pages/profiles/ProfileImportPage.tsx`
- Modify: `web/src/pages/profiles/ProfileImportPage.test.tsx`
- Modify: `web/src/components/profiles/ProfileStatusBadge.tsx`
- Modify: `web/src/components/profiles/ProfileEmptyState.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
it('keeps Job Detail on the shared section / json / artifact kit', async () => {
  mockedGetJob.mockResolvedValueOnce({
    job: {
      id: 'job-1',
      job_type: 'strategy-build',
      status: 'success',
      params: { config_path: 'config/app.yaml' },
      result: { payload: { report: { total: 2 } } },
      artifacts: [],
      error: null,
      created_by: 'web',
      idempotency_key: null,
      retry_count: 0,
      max_retries: 3,
      retry_backoff_seconds: 0,
      timeout_seconds: null,
      cancel_requested: false,
      cancel_requested_at: null,
      worker_id: null,
      lock_token: null,
      lock_acquired_at: null,
      heartbeat_at: null,
      scheduled_at: null,
      started_at: '2026-05-17T08:00:00Z',
      finished_at: '2026-05-17T08:05:00Z',
      audit_events: [],
      created_at: '2026-05-17T08:00:00Z',
      updated_at: '2026-05-17T08:05:00Z',
      config_snapshot_path: null,
      config_snapshot: null,
    },
    job_dir: '/tmp/job-1',
    log_path: '/tmp/job-1/job.log',
    params_path: '/tmp/job-1/params.json',
    result_path: '/tmp/job-1/result.json',
    artifacts_path: '/tmp/job-1/artifacts.json',
  } as never);

  renderWithRouter([{ path: '/jobs/:jobId', element: <JobDetailPage /> }], ['/jobs/job-1']);

  expect(await screen.findByText('任务详情')).toBeInTheDocument();
  expect(screen.getByText('参数快照')).toBeInTheDocument();
  expect(screen.getByText('执行结果')).toBeInTheDocument();
});
```

```tsx
it('renders the profile list with shared empty and badge surfaces', async () => {
  mockedListProfiles.mockResolvedValueOnce({ count: 0, total: 0, skip: 0, limit: 50, items: [] } as never);
  renderWithRouter([{ path: '/profiles', element: <ProfileListPage /> }], ['/profiles']);
  expect(await screen.findByText('配置管理工作台')).toBeInTheDocument();
  expect(screen.getByText('暂无配置')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/pages/jobs/JobDetailPage.test.tsx src/pages/profiles/ProfileListPage.test.tsx src/pages/profiles/ProfileDetailPage.test.tsx src/pages/profiles/ProfileEditPage.test.tsx src/pages/profiles/ProfileImportPage.test.tsx`

Expected: FAIL because the pages still contain local shells and compatibility wrappers are not wired to the kit yet.

- [ ] **Step 3: Write the minimal implementation**

```tsx
// JobDetailPage.tsx
import { ArtifactList, ErrorState, JsonViewer, LogViewer, SectionCard } from '@/components/kit';
```

```tsx
// ProfileStatusBadge.tsx
import { StatusBadge } from '@/components/kit';
export function ProfileStatusBadge({ status }: { status: ProfileValidationStatus }) {
  return <StatusBadge value={status} />;
}
```

```tsx
// ProfileEmptyState.tsx
import { EmptyState } from '@/components/kit';
export function ProfileEmptyState(props: ProfileEmptyStateProps) {
  return <EmptyState {...props} />;
}
```

- [ ] **Step 4: Re-run the tests**

Run: `cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/pages/jobs/JobDetailPage.test.tsx src/pages/profiles/ProfileListPage.test.tsx src/pages/profiles/ProfileDetailPage.test.tsx src/pages/profiles/ProfileEditPage.test.tsx src/pages/profiles/ProfileImportPage.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/jobs/JobDetailPage.tsx web/src/pages/jobs/JobDetailPage.test.tsx web/src/pages/profiles/ProfileListPage.tsx web/src/pages/profiles/ProfileListPage.test.tsx web/src/pages/profiles/ProfileDetailPage.tsx web/src/pages/profiles/ProfileDetailPage.test.tsx web/src/pages/profiles/ProfileEditPage.tsx web/src/pages/profiles/ProfileEditPage.test.tsx web/src/pages/profiles/ProfileImportPage.tsx web/src/pages/profiles/ProfileImportPage.test.tsx web/src/components/profiles/ProfileStatusBadge.tsx web/src/components/profiles/ProfileEmptyState.tsx
git commit -m "refactor(ui): share job and profile ui primitives"
```

---

## Task 3: Refactor Market and Strategy pages onto the shared kit

**Files:**
- Modify: `web/src/features/market-workspace/market-workspace-shell.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-summary.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-errors.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-recent-jobs.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-artifacts.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-shell.test.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-actions.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-history.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-artifacts.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-actions.test.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-history.test.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it('renders market and strategy workspaces with the shared kit shell', async () => {
  renderWithRouter([{ path: '/market', element: <MarketWorkspaceShell /> }], ['/market']);
  expect(await screen.findByText('市场工作台')).toBeInTheDocument();
  expect(screen.getByText('V2 浅色工作台')).toBeInTheDocument();
});
```

```tsx
it('keeps strategy actions behind the shared confirm dialog', async () => {
  renderWithRouter([{ path: '/strategies', element: <StrategyWorkspaceShell /> }], ['/strategies']);
  expect(await screen.findByRole('button', { name: '构建策略版本' })).toBeInTheDocument();
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/features/market-workspace/market-workspace-shell.test.tsx src/features/strategy-workspace/strategy-workspace-shell.test.tsx src/features/strategy-workspace/strategy-workspace-actions.test.tsx src/features/strategy-workspace/strategy-workspace-history.test.tsx src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx`

Expected: FAIL because the workspaces still use local shells or page-local state components.

- [ ] **Step 3: Write the minimal implementation**

```tsx
import { ConfirmDialog, EmptyState, ErrorState, LoadingState, SectionCard, JsonViewer, LogViewer, ArtifactList } from '@/components/kit';
```

```tsx
// strategy-workspace-actions.tsx
<ConfirmDialog
  open={confirmOpen}
  title={confirmTitle}
  description={confirmDescription}
  confirmLabel={confirmLabel}
  cancelLabel="取消"
  onConfirm={handleConfirm}
  onOpenChange={setConfirmOpen}
/>
```

```tsx
// market-workspace-errors.tsx
return <ErrorState {...buildErrorRecoveryState(error, 'market')} />;
```

- [ ] **Step 4: Re-run the tests**

Run: `cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/features/market-workspace/market-workspace-shell.test.tsx src/features/strategy-workspace/strategy-workspace-shell.test.tsx src/features/strategy-workspace/strategy-workspace-actions.test.tsx src/features/strategy-workspace/strategy-workspace-history.test.tsx src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/market-workspace web/src/features/strategy-workspace
git commit -m "refactor(ui): share market and strategy ui primitives"
```

---

## Task 4: Final regression, TaskList sync, and concise session notes

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-17.md`
- Modify: `daily-report/2026-05-17.md`

- [ ] **Step 1: Run the targeted regression suite**

Run:

```bash
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run \
  src/components/kit/kit.test.tsx \
  src/pages/jobs/JobDetailPage.test.tsx \
  src/pages/profiles/ProfileListPage.test.tsx \
  src/pages/profiles/ProfileDetailPage.test.tsx \
  src/pages/profiles/ProfileEditPage.test.tsx \
  src/pages/profiles/ProfileImportPage.test.tsx \
  src/features/market-workspace/market-workspace-shell.test.tsx \
  src/features/strategy-workspace/strategy-workspace-shell.test.tsx \
  src/features/strategy-workspace/strategy-workspace-actions.test.tsx \
  src/features/strategy-workspace/strategy-workspace-history.test.tsx \
  src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Check for formatting drift**

Run: `git diff --check`

Expected: no whitespace or patch-format errors.

- [ ] **Step 3: Update the task list and session notes**

```md
### [x] UI-V2-009 P1 UI Component Kit

完成情况：

- 已抽出统一的 V2 组件基座，并被 Job / Profile / Market / Strategy 页面复用。
- 已保留 V2 的浅色工作台视觉，不引入第二套 UI 语言。
- 已通过相关前端回归测试。
```

```md
## Current Context
完成 `UI-V2-009` 后，下一步进入 `NW-V2-S4-001` 正式 Web 工作台收口。

## Resume Point
继续准备 `NW-V2-S4-001`，优先确认 Dashboard 到 Profile / Market / Strategy / Jobs / Artifacts 的正式收口路径。
```

- [ ] **Step 4: Commit**

```bash
git add docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-17.md daily-report/2026-05-17.md
git commit -m "docs(ui): close ui v2 component kit"
```

---

## Self-Review

### 1. Spec coverage

- Shared kit primitives: covered by Task 1.
- Job and Profile reuse: covered by Task 2.
- Market and Strategy reuse: covered by Task 3.
- TaskList / session / report synchronization: covered by Task 4.
- V2 visual consistency: enforced in the architecture and all tasks.
- No CLI expansion / no API contract changes / no V1 migration: covered by scope checks.

### 2. Placeholder scan

- No `TBD`, `TODO`, or vague "handle edge cases later" language.
- Every task has exact files, exact commands, and concrete expected results.
- Every implementation step shows a real code shape, not a generic instruction.

### 3. Type consistency

- Shared components are introduced once in `web/src/components/kit/index.ts` and then imported from that barrel.
- Compatibility wrappers (`ProfileStatusBadge`, `ProfileEmptyState`) remain thin, so page code does not break while the shared kit becomes canonical.
- The plan keeps the current page module names and route names unchanged.

