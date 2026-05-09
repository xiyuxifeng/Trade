# WEB-S6-005 Backtests Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Web backtests workbench that can submit backtest-related Jobs, browse stored backtest results, inspect markdown reports and rule validation reports, and surface a lightweight metrics summary.

**Architecture:** The page will stay as a single analysis workspace with a left rail for filters, job submission, and result selection, and a right panel for summary, records, markdown reports, validation output, and raw JSON. Frontend data access will be split into a dedicated `backtests` API module that talks to the existing root-level `/backtest_results` endpoints, while Job submission continues to use the shared Jobs API under `/api/ui/v1`. This keeps browse flows and long-running execution flows separate without introducing duplicate storage or new backtest backend behavior.

**Tech Stack:** React, TypeScript, TanStack Query, React Router, shadcn/ui, Tailwind CSS, Vitest, Testing Library

---

### Task 1: Backtests API client and types

**Files:**
- Create: `web/src/lib/api/backtests.ts`
- Create: `web/src/types/backtests.ts`
- Create: `web/src/lib/api/backtests.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
it('calls the root backtest_results endpoint and sends the stored API key', async () => {
  window.localStorage.setItem('trade-strategy-ai.apiKey', 'demo-key');
  await listBacktestResults({ skip: 0, limit: 10 });
  expect(fetch).toHaveBeenCalledWith(
    expect.stringContaining('/backtest_results/?skip=0&limit=10'),
    expect.objectContaining({
      headers: expect.objectContaining({ 'X-API-Key': 'demo-key' }),
    }),
  );
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `corepack pnpm test src/lib/api/backtests.test.ts -v`
Expected: FAIL because the new client does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```ts
export function listBacktestResults(query) {
  return fetchRootJson(`/backtest_results/?${params.toString()}`);
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `corepack pnpm test src/lib/api/backtests.test.ts -v`
Expected: PASS.

### Task 2: Backtests center page component

**Files:**
- Create: `web/src/features/backtests/backtests-center.tsx`
- Modify: `web/src/pages/backtests/index.tsx`
- Create: `web/src/pages/backtests/index.test.tsx`

- [ ] **Step 1: Write the failing test**

```ts
it('submits backtest jobs and renders the selected result details', async () => {
  renderWithRouter([{ path: '/backtests', element: <BacktestsPage /> }], ['/backtests']);
  await user.click(screen.getByRole('button', { name: 'Run backtest' }));
  await user.click(screen.getByRole('button', { name: 'Validate rules' }));
  await user.click(screen.getByRole('button', { name: 'Reproducibility check' }));
  expect(createJob).toHaveBeenCalledWith(expect.objectContaining({ job_type: 'backtest-run' }));
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `corepack pnpm test src/pages/backtests/index.test.tsx -v`
Expected: FAIL because the page is still a placeholder.

- [ ] **Step 3: Write minimal implementation**

```tsx
export function BacktestsCenter() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Backtests" title="Backtests Center" description="Browse results and submit validation jobs." />
    </main>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `corepack pnpm test src/pages/backtests/index.test.tsx -v`
Expected: PASS.

### Task 3: Detail workspace, charts, and markdown previews

**Files:**
- Modify: `web/src/features/backtests/backtests-center.tsx`
- Modify: `web/src/pages/backtests/index.test.tsx`

- [ ] **Step 1: Write the failing test**

```ts
it('shows summary, records, report, validation, and JSON tabs for the selected result', async () => {
  expect(await screen.findByRole('tab', { name: 'Summary' })).toBeInTheDocument();
  expect(await screen.findByRole('tab', { name: 'Records' })).toBeInTheDocument();
  expect(await screen.findByRole('tab', { name: 'Report' })).toBeInTheDocument();
  expect(await screen.findByRole('tab', { name: 'Validation' })).toBeInTheDocument();
  expect(await screen.findByRole('tab', { name: 'JSON' })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `corepack pnpm test src/pages/backtests/index.test.tsx -v`
Expected: FAIL until the workspace UI is implemented.

- [ ] **Step 3: Write minimal implementation**

```tsx
function BacktestSummaryCards({ detail }) {
  return <div>{/* total_days, total_trades, valid_trades, skipped_trades, win_rate, avg_return_pct */}</div>;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `corepack pnpm test src/pages/backtests/index.test.tsx -v`
Expected: PASS.

### Task 4: Route hookup and regression verification

**Files:**
- Modify: `web/src/pages/backtests/index.tsx`
- Modify: `web/src/app/router.tsx` if needed
- Modify: `web/src/app/navigation.ts` if needed
- Verify: `web/src/pages/backtests/index.test.tsx`

- [ ] **Step 1: Confirm the route exports the real page component**

```ts
export { BacktestsCenter as BacktestsPage } from '@/features/backtests/backtests-center';
```

- [ ] **Step 2: Run the page test and full frontend checks**

Run:

```bash
corepack pnpm test src/pages/backtests/index.test.tsx
corepack pnpm typecheck
corepack pnpm lint
corepack pnpm build
```

Expected: all pass.

- [ ] **Step 3: Commit-ready cleanup**

```bash
git diff --check
```

Expected: no whitespace or patch formatting issues.

