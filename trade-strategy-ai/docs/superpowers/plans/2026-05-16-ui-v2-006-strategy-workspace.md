# UI-V2-006 Strategy Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the formal Strategy Workspace as a light-theme, Chinese-first Web workbench for strategy version construction, pre-market, and after-close execution without expanding CLI entry points.

**Architecture:** Reuse the existing `/strategies` canonical route and keep all execution behind the existing Job / Workflow / Artifact APIs. The workspace should be split into focused feature components: one shell for page state and query orchestration, one action layer for confirmation and job submission, one history layer for recent jobs, and one results layer for strategy versions and artifact explanations. The page must follow the same visual language as `UI-V2-002`: white cards, light borders, restrained blue accents, and explicit loading / empty / error / retry states.

**Tech Stack:** React, TypeScript, TanStack Query, React Router, existing `@/lib/api/*` clients, existing UI component library, current profile / job / strategy APIs, and the shared `Dialog` component.

---

## File Structure

### Purpose-driven file map

- Modify: `web/src/pages/strategies/index.tsx` - render the formal strategy workspace shell.
- Modify: `web/src/pages/strategies/index.test.tsx` - verify the formal entry page and visible workspace copy.
- Create: `web/src/features/strategy-workspace/index.ts` - public export for the workspace feature.
- Create: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx` - page-level orchestration, state, and layout composition.
- Create: `web/src/features/strategy-workspace/strategy-workspace-utils.ts` - helper for selecting the latest profile snapshot config path and formatting workspace errors.
- Create: `web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx` - cover profile loading, config path derivation, and empty/error states.
- Create: `web/src/features/strategy-workspace/strategy-workspace-actions.tsx` - confirmation dialogs and `createJob` submission for `strategy-build`, `run-pre-market`, and `run-after-close`.
- Create: `web/src/features/strategy-workspace/strategy-workspace-actions.test.tsx` - verify confirmation flow and submitted job params.
- Create: `web/src/features/strategy-workspace/strategy-workspace-history.tsx` - recent strategy job list and job detail navigation.
- Create: `web/src/features/strategy-workspace/strategy-workspace-history.test.tsx` - verify loading, empty, error, and navigation states.
- Create: `web/src/features/strategy-workspace/strategy-workspace-artifacts.tsx` - strategy version list, version detail, artifact / report links, and empty states.
- Create: `web/src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx` - verify version selection, artifact links, and result explanation.
- Update: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md` only after implementation and verification pass.
- Update: `daily-sessions/2026-05-16.md` and `daily-report/2026-05-16.md` only after verification pass.

## Scope Check

This task only covers the Strategy Workspace Web entry and its supporting UI composition.

It must not:
- add or strengthen CLI commands
- calculate strategy rankings in the browser
- infer rule applicability in the browser
- add a second formal strategy route
- bypass the Job / Workflow / Artifact contract
- expose server absolute paths or raw secrets

It must:
- let users choose `trader / date / profile`
- map the selected Profile to a usable `config_path`
- submit strategy-related jobs through the Job API
- show recent strategy jobs and strategy versions
- explain outputs through artifacts and report links
- keep the page visually consistent with `UI-V2-002`

---

## Task 1: Build the shell and profile-to-config mapping

**Files:**
- Modify: `web/src/pages/strategies/index.tsx`
- Modify: `web/src/pages/strategies/index.test.tsx`
- Create: `web/src/features/strategy-workspace/index.ts`
- Create: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx`
- Create: `web/src/features/strategy-workspace/strategy-workspace-utils.ts`
- Create: `web/src/features/strategy-workspace/strategy-workspace-shell.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { StrategiesPage } from '@/pages/strategies';
import { listProfiles, getProfile } from '@/lib/api/profiles';

vi.mock('@/lib/api/profiles', () => ({
  listProfiles: vi.fn(),
  getProfile: vi.fn(),
}));

it('renders the formal strategy workspace and derives config_path from the latest profile snapshot', async () => {
  vi.mocked(listProfiles).mockResolvedValue({
    count: 1,
    total: 1,
    skip: 0,
    limit: 20,
    items: [
      {
        profile_id: 'default',
        name: '默认配置',
        environment: 'production',
        version: 3,
        sections: {},
        secret_refs: {},
        validation_status: 'validated',
        created_by: 'web',
        created_at: '2026-05-16T00:00:00Z',
        updated_at: '2026-05-16T00:00:00Z',
        archived_at: null,
      },
    ],
  } as never);
  vi.mocked(getProfile).mockResolvedValue({
    profile: { profile_id: 'default', name: '默认配置', environment: 'production', version: 3, sections: {}, secret_refs: {}, validation_status: 'validated', created_by: 'web', created_at: '2026-05-16T00:00:00Z', updated_at: '2026-05-16T00:00:00Z', archived_at: null },
    linked_jobs: [],
    snapshots: [
      { snapshot_id: 'snap-2', profile_id: 'default', job_id: 'job-2', source: 'import', config_path: 'config/strategy-v3.yaml', config_hash: 'hash-2', masked_snapshot: {}, masked_sections: [], validation_status: 'validated', captured_at: '2026-05-16T08:00:00Z', snapshot_path: 'ignored' },
      { snapshot_id: 'snap-1', profile_id: 'default', job_id: 'job-1', source: 'import', config_path: 'config/strategy-v2.yaml', config_hash: 'hash-1', masked_snapshot: {}, masked_sections: [], validation_status: 'validated', captured_at: '2026-05-15T08:00:00Z', snapshot_path: 'ignored' },
    ],
  } as never);

  renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);

  expect(await screen.findByRole('heading', { name: '策略工作台' })).toBeInTheDocument();
  expect(screen.getByText('V2 正式入口')).toBeInTheDocument();
  expect(screen.getByText('config/strategy-v3.yaml')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/pages/strategies/index.test.tsx src/features/strategy-workspace/strategy-workspace-shell.test.tsx`

Expected: FAIL because the formal shell, profile mapping, and helper exports do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```ts
export function selectLatestSnapshotConfigPath(detail: ProfileDetailResponse | null): string | null {
  const snapshots = [...(detail?.snapshots ?? [])].sort((left, right) => right.captured_at.localeCompare(left.captured_at));
  return snapshots[0]?.config_path ?? null;
}
```

```tsx
export function StrategyWorkspaceShell() {
  return (
    <main className="page-stack">
      <PageHeader
        kicker="正式入口"
        title="策略工作台"
        description="在 Web 中构建策略版本、运行盘前和盘后任务，并查看结果解释。"
      />
      {/* profile selector, config_path preview, action area, history, artifact panels */}
    </main>
  );
}
```

- [ ] **Step 4: Re-run the tests**

Run: `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/pages/strategies/index.test.tsx src/features/strategy-workspace/strategy-workspace-shell.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/strategies/index.tsx web/src/pages/strategies/index.test.tsx web/src/features/strategy-workspace
git commit -m "feat(ui): add strategy workspace shell"
```

---

## Task 2: Add confirmation dialogs and strategy job submission

**Files:**
- Create: `web/src/features/strategy-workspace/strategy-workspace-actions.tsx`
- Create: `web/src/features/strategy-workspace/strategy-workspace-actions.test.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { StrategiesPage } from '@/pages/strategies';
import { createJob } from '@/lib/api/jobs';

vi.mock('@/lib/api/jobs', () => ({
  createJob: vi.fn(),
  listJobs: vi.fn(),
}));

it('opens a confirmation dialog before submitting strategy-build and sends the selected config_path', async () => {
  const user = userEvent.setup();
  vi.mocked(createJob).mockResolvedValue({
    created: true,
    job: { id: 'job-strategy-1' },
    job_dir: '/tmp/job-strategy-1',
    log_path: '/tmp/job-strategy-1/log.txt',
    params_path: '/tmp/job-strategy-1/params.json',
    result_path: '/tmp/job-strategy-1/result.json',
    artifacts_path: '/tmp/job-strategy-1/artifacts',
  } as never);

  renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);

  await user.click(await screen.findByRole('button', { name: '构建策略版本' }));
  expect(screen.getByRole('dialog', { name: '确认构建策略版本' })).toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: '确认提交' }));
  expect(createJob).toHaveBeenCalledWith(
    expect.objectContaining({
      job_type: 'strategy-build',
      params: expect.objectContaining({
        config_path: 'config/strategy-v3.yaml',
        trader_id: 'trader_a',
      }),
    }),
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/features/strategy-workspace/strategy-workspace-actions.test.tsx src/pages/strategies/index.test.tsx`

Expected: FAIL because the confirmation dialog and submission wiring do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```tsx
const STRATEGY_ACTIONS = [
  { jobType: 'strategy-build', label: '构建策略版本', confirmTitle: '确认构建策略版本' },
  { jobType: 'run-pre-market', label: '盘前运行', confirmTitle: '确认盘前运行' },
  { jobType: 'run-after-close', label: '盘后运行', confirmTitle: '确认盘后运行' },
];
```

```tsx
<Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>{confirmTitle}</DialogTitle>
      <DialogDescription>本操作会触发正式 Job，请确认参数和日期。</DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline" onClick={() => setConfirmOpen(false)}>取消</Button>
      <Button onClick={handleSubmit}>确认提交</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

- [ ] **Step 4: Re-run the tests**

Run: `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/features/strategy-workspace/strategy-workspace-actions.test.tsx src/pages/strategies/index.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/features/strategy-workspace/strategy-workspace-actions.tsx web/src/features/strategy-workspace/strategy-workspace-actions.test.tsx web/src/features/strategy-workspace/strategy-workspace-shell.tsx
git commit -m "feat(ui): add strategy workspace actions"
```

---

## Task 3: Add recent job history and artifact/version explanation panels

**Files:**
- Create: `web/src/features/strategy-workspace/strategy-workspace-history.tsx`
- Create: `web/src/features/strategy-workspace/strategy-workspace-history.test.tsx`
- Create: `web/src/features/strategy-workspace/strategy-workspace-artifacts.tsx`
- Create: `web/src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx`
- Modify: `web/src/features/strategy-workspace/strategy-workspace-shell.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithRouter } from '@/test/test-utils';
import { StrategiesPage } from '@/pages/strategies';
import { listJobs } from '@/lib/api/jobs';
import { listStrategyVersions } from '@/lib/api/strategyStudio';
import { listArtifacts } from '@/lib/api/artifacts';

vi.mock('@/lib/api/jobs', () => ({ createJob: vi.fn(), listJobs: vi.fn() }));
vi.mock('@/lib/api/strategyStudio', () => ({ listStrategyVersions: vi.fn(), getStrategyVersion: vi.fn() }));
vi.mock('@/lib/api/artifacts', () => ({ listArtifacts: vi.fn(), getArtifact: vi.fn(), downloadArtifact: vi.fn() }));

it('shows recent strategy jobs, version history, and artifact links', async () => {
  vi.mocked(listJobs).mockResolvedValue({ count: 1, total: 1, skip: 0, limit: 20, items: [{ id: 'job-1', job_type: 'strategy-build', status: 'success', params: {}, result: null, error: null, artifacts: [], created_by: 'web', idempotency_key: null, retry_count: 0, max_retries: 3, retry_backoff_seconds: 0, timeout_seconds: null, cancel_requested: false, cancel_requested_at: null, worker_id: null, lock_token: null, lock_acquired_at: null, heartbeat_at: null, scheduled_at: null, started_at: '2026-05-16T08:00:00Z', finished_at: '2026-05-16T08:05:00Z', audit_events: [], created_at: '2026-05-16T08:00:00Z', updated_at: '2026-05-16T08:05:00Z', config_snapshot_path: null, config_snapshot: null }] } as never);
  vi.mocked(listStrategyVersions).mockResolvedValue({ status: 'ok', count: 1, total: 1, skip: 0, limit: 20, items: [{ version_id: 'ver-1', trader_id: 'trader_a', strategy_date: '2026-05-16', status: 'released', version_type: 'candidate', parent_version_id: null, recommendations_count: 2, source_article_ids_count: 1, released_at: null, has_rules_snapshot: true }] } as never);
  vi.mocked(listArtifacts).mockResolvedValue({ count: 0, total: 0, skip: 0, limit: 12, items: [] } as never);

  renderWithRouter([{ path: '/strategies', element: <StrategiesPage /> }], ['/strategies']);

  expect(await screen.findByText('最近策略任务')).toBeInTheDocument();
  expect(screen.getByText('ver-1')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: '前往产物中心' })).toHaveAttribute('href', '/artifacts');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/features/strategy-workspace/strategy-workspace-history.test.tsx src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx src/pages/strategies/index.test.tsx`

Expected: FAIL because the history and artifact panels do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

```tsx
export function StrategyWorkspaceHistory({ jobs }: { jobs: JobRecord[] }) {
  if (!jobs.length) {
    return <EmptyState title="暂无策略任务" description="先提交一次策略构建或盘前/盘后任务。" />;
  }
  return <JobList items={jobs} />;
}
```

```tsx
export function StrategyWorkspaceArtifacts({ versions, selectedVersion, onSelectVersion }: Props) {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      <VersionList versions={versions} onSelectVersion={onSelectVersion} />
      <VersionDetail detail={selectedVersion} />
    </section>
  );
}
```

- [ ] **Step 4: Re-run the tests**

Run: `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/features/strategy-workspace/strategy-workspace-history.test.tsx src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx src/pages/strategies/index.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/features/strategy-workspace/strategy-workspace-history.tsx web/src/features/strategy-workspace/strategy-workspace-history.test.tsx web/src/features/strategy-workspace/strategy-workspace-artifacts.tsx web/src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx web/src/features/strategy-workspace/strategy-workspace-shell.tsx
git commit -m "feat(ui): add strategy workspace history and artifacts"
```

---

## Task 4: Final verification and task bookkeeping

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-16.md`
- Modify: `daily-report/2026-05-16.md`

- [ ] **Step 1: Verify the workspace meets the acceptance criteria**

Run:

```bash
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run \
  src/pages/strategies/index.test.tsx \
  src/features/strategy-workspace/strategy-workspace-shell.test.tsx \
  src/features/strategy-workspace/strategy-workspace-actions.test.tsx \
  src/features/strategy-workspace/strategy-workspace-history.test.tsx \
  src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx
```

Expected:
- the strategy workspace renders in Chinese-first light theme
- the page shows `trader / date / profile`
- job submission happens through the Job API
- confirmation is required before strategy, pre-market, and after-close runs
- recent jobs, versions, and artifact links are available
- no CLI-only flow is needed for the main path

- [ ] **Step 2: Mark `UI-V2-006` complete in the UI TaskList**

Update the task entry and add a completion note that the workspace is Web-first, shares the `UI-V2-002` visual language, and keeps execution behind the existing Job / Workflow / Artifact APIs.

- [ ] **Step 3: Update session/report with a concise summary**

Keep only:
- what was implemented
- what was verified
- what remains next

- [ ] **Step 4: Final verification**

Run:

```bash
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run \
  src/pages/strategies/index.test.tsx \
  src/features/strategy-workspace/strategy-workspace-shell.test.tsx \
  src/features/strategy-workspace/strategy-workspace-actions.test.tsx \
  src/features/strategy-workspace/strategy-workspace-history.test.tsx \
  src/features/strategy-workspace/strategy-workspace-artifacts.test.tsx
git diff --check
```

Expected:
- all tests pass
- `git diff --check` passes

- [ ] **Step 5: Commit**

```bash
git add docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-16.md daily-report/2026-05-16.md
git commit -m "docs(ui): record strategy workspace completion"
```

## Self-Review Checklist

- The plan covers the full `UI-V2-006` requirement set: strategy build, pre-market, after-close, confirmation, recent jobs, versions, artifacts, and explanation links.
- The plan keeps execution on the Web path and does not introduce any new CLI surface area.
- The plan preserves the `UI-V2-002` visual language and Chinese-first copy.
- No placeholder steps remain.
- File paths are exact and limited to the existing `/strategies` workspace plus the shared profile / job / strategy / artifact API layer.

