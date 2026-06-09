# UI-V2-005 Market Data Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the formal Market Data Workspace as a light-theme, Chinese-first Web workbench for running and reviewing market data jobs without strengthening CLI entry points.

**Architecture:** Reuse the existing `/market` web route as the canonical workspace shell and keep all execution behind the Job Center / existing UI APIs. The page should combine a top-level status summary, runnable market task cards, recent job history, error classification, and artifact/job deep links. All user-visible copy must follow the `UI-V2-002` wording style: Chinese-first, low cognitive load, and consistent empty/loading/error/retry states.

**Tech Stack:** React, TypeScript, TanStack Query, existing `@/lib/api/*` client layer, existing UI component library, current route registry and job APIs.

---

### Task 1: Add a typed Market Workspace API surface

**Files:**
- Modify: `web/src/lib/api/market.ts`
- Modify: `web/src/types/market.ts`
- Modify: `web/src/lib/api/contract.test.ts`
- Create: `web/src/lib/api/market-workspace.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect } from 'vitest';
import { listMarketSnapshots, listMarketDatasets, getMarketSnapshotQuality } from '@/lib/api/market';

describe('market workspace API contract', () => {
  it('builds the market snapshot list url with filters', async () => {
    // assert fetchJson is called with /api/ui/v1/market/snapshots?market=cn&trade_date=2026-05-16
  });

  it('builds the market dataset detail url', async () => {
    // assert fetchJson is called with /api/ui/v1/market/datasets/ds_001
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/bin/python -m vitest run web/src/lib/api/market-workspace.test.ts -v`

- [ ] **Step 3: Write minimal implementation**

```ts
export async function listMarketSnapshots(params: { market?: string; trade_date?: string; limit?: number; skip?: number }) {
  return fetchJson<SnapshotListResponse>(`/market/snapshots?${query}`);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/bin/python -m vitest run web/src/lib/api/market-workspace.test.ts -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api/market.ts web/src/types/market.ts web/src/lib/api/contract.test.ts web/src/lib/api/market-workspace.test.ts
git commit -m "feat(ui): add market workspace api surface"
```

### Task 2: Rework `/market` into the formal workspace shell

**Files:**
- Modify: `web/src/pages/market/index.tsx`
- Create: `web/src/features/market-workspace/market-workspace-shell.tsx`
- Create: `web/src/features/market-workspace/market-workspace-summary.tsx`
- Create: `web/src/features/market-workspace/market-workspace-runners.tsx`
- Create: `web/src/features/market-workspace/market-workspace-recent-jobs.tsx`
- Create: `web/src/features/market-workspace/market-workspace-artifacts.tsx`
- Create: `web/src/features/market-workspace/market-workspace-errors.tsx`
- Create: `web/src/features/market-workspace/index.ts`
- Modify: `web/src/pages/market/index.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from '@testing-library/react';
import { MarketPage } from '@/pages/market';

it('shows the market workspace summary and runnable tasks', async () => {
  render(<MarketPage />);
  expect(await screen.findByText('市场数据工作台')).toBeInTheDocument();
  expect(screen.getByText('最近任务')).toBeInTheDocument();
  expect(screen.getByText('运行指定任务')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/bin/python -m vitest run web/src/pages/market/index.test.tsx -v`

- [ ] **Step 3: Write minimal implementation**

```tsx
export function MarketWorkspaceShell() {
  return (
    <main className="page-stack">
      <PageHeader kicker="市场数据" title="市场数据工作台" description="在 Web 中运行和查看市场数据链路。" />
      {/* summary, runners, recent jobs, artifacts, errors */}
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/bin/python -m vitest run web/src/pages/market/index.test.tsx -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/market/index.tsx web/src/pages/market/index.test.tsx web/src/features/market-workspace
git commit -m "feat(ui): add market workspace shell"
```

### Task 3: Wire runnable market jobs, recent history, and artifact links

**Files:**
- Modify: `web/src/features/market-workspace/market-workspace-runners.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-recent-jobs.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-artifacts.tsx`
- Modify: `web/src/features/market-workspace/market-workspace-errors.tsx`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/navigation.ts`
- Modify: `web/src/app/route-registry.ts`
- Modify: `web/src/lib/api/contract.test.ts`
- Modify: `web/src/pages/jobs/JobDetailPage.tsx`
- Create: `web/src/features/market-workspace/market-workspace-shell.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it('links each market task to a runnable job action and job detail', async () => {
  render(<MarketWorkspaceShell />);
  expect(screen.getByRole('link', { name: '查看最近任务' })).toHaveAttribute('href', '/jobs');
  expect(screen.getByRole('link', { name: '跳转 Job 详情' })).toHaveAttribute('href', '/jobs/');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `../.venv/bin/python -m vitest run web/src/features/market-workspace/market-workspace-shell.test.tsx -v`

- [ ] **Step 3: Write minimal implementation**

```tsx
const MARKET_RUNNERS = [
  { key: 'kaipan-fetch', label: '抓取 Kaipan', jobType: 'kaipan-fetch' },
  { key: 'kaipan-normalize', label: '标准化 Kaipan', jobType: 'kaipan-normalize' },
  { key: 'snapshot-build', label: '构建快照', jobType: 'snapshot-build' },
];
```

- [ ] **Step 4: Run test to verify it passes**

Run: `../.venv/bin/python -m vitest run web/src/features/market-workspace/market-workspace-shell.test.tsx -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/features/market-workspace web/src/app/router.tsx web/src/app/navigation.ts web/src/app/route-registry.ts web/src/lib/api/contract.test.ts web/src/pages/jobs/JobDetailPage.tsx
git commit -m "feat(ui): wire market workspace actions and history"
```

### Task 4: Finalize review, TaskList sync, and session notes

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-16.md`
- Modify: `daily-report/2026-05-16.md`

- [ ] **Step 1: Verify the workspace meets the acceptance criteria**

Run:
`../.venv/bin/python -m vitest run web/src/pages/market/index.test.tsx web/src/features/market-workspace/market-workspace-shell.test.tsx web/src/lib/api/market-workspace.test.ts -v`

Expected:
- Market Data Workspace renders in Chinese-first light theme.
- Runnable market jobs are visible.
- Recent jobs, errors, artifacts, and Job Detail navigation are available.
- No CLI-only workflow is required for the main path.

- [ ] **Step 2: Mark `UI-V2-005` complete in the UI TaskList**

Update the task entry and add a short completion note that the workspace is Web-first, shares the `UI-V2-002` visual language, and keeps execution behind Job Center.

- [ ] **Step 3: Update session/report with a concise summary**

Keep only:
- what was implemented
- what was verified
- what remains next

- [ ] **Step 4: Commit**

```bash
git add docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-16.md daily-report/2026-05-16.md
git commit -m "docs(ui): record market workspace completion"
```

## Self-Review Checklist

- The plan covers the full `UI-V2-005` requirement set: workflows, runnable tasks, recent jobs, errors, artifacts, and job detail navigation.
- The plan keeps the implementation on the Web path and does not introduce new CLI surface area.
- The plan preserves the `UI-V2-002` visual language and Chinese-first copy.
- No placeholder steps remain.
- File paths are exact and limited to the existing `/market` workspace plus the shared API/type layer.

