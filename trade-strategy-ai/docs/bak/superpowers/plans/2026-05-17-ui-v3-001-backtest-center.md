# UI-V3-001 Backtest Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a formal `/backtest` Web workbench that reuses the existing backtest API and Job submission path, keeps the UI consistent with `UI-V2-002`, and exposes the core run / result / reproducibility flow without adding CLI-first behavior.

**Architecture:** Keep the existing `/backtests` legacy page intact. Replace the `/backtest` placeholder with a light-theme workbench built around the existing backtest API client, but reduce the initial information density to a single primary control area, a recent-result summary, and a recent-results list. Use the same canonical job submission contract as the backtest pipeline spec, and only surface report / validation / JSON artifacts through the API client and selected-result details.

**Tech Stack:** TypeScript, React, React Query, React Router, existing UI component library, existing backtest API client, Vitest, Testing Library.

---

### Task 1: Lock the `/backtest` contract in tests first

**Files:**
- Create: `web/src/pages/backtest/index.test.tsx`
- Modify: `web/src/lib/api/backtests.test.ts`
- Modify: `web/src/lib/api/backtests.ts`
- Modify: `web/src/types/backtests.ts`

- [ ] **Step 1: Write the failing tests**

Add a page test that requires the formal workbench to show the `Backtest Center` heading, one primary form area, a recent-result summary, and a recent-results list:

```tsx
it('renders the formal backtest workbench', async () => {
  renderWithRouter([{ path: '/backtest', element: <BacktestPage /> }], ['/backtest']);

  expect(await screen.findByRole('heading', { name: '回测中心' })).toBeInTheDocument();
  expect(screen.getByText('正式入口')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '运行回测' })).toBeInTheDocument();
  expect(screen.getByText('最近结果')).toBeInTheDocument();
  expect(screen.getByText('最近任务')).toBeInTheDocument();
});
```

Update the API client tests so the submission helpers require the new canonical fields:

```ts
expect(buildBacktestRunParams({
  traderId: 'trader_a',
  dateFrom: '2026-05-01',
  dateTo: '2026-05-05',
  strategyVersionId: 'sv-1',
  mode: 'full',
  configPath: 'config/app.yaml',
  symbols: ['000001.SZ'],
  useSnapshotOnly: true,
  scoringProfile: 'stage5',
})).toEqual({
  trader_id: 'trader_a',
  date_from: '2026-05-01',
  date_to: '2026-05-05',
  strategy_version_id: 'sv-1',
  mode: 'full',
  config_path: 'config/app.yaml',
  symbols: ['000001.SZ'],
  use_snapshot_only: true,
  scoring_profile: 'stage5',
});
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
cd web && pnpm vitest run src/pages/backtest/index.test.tsx src/lib/api/backtests.test.ts
```

Expected:

- `/backtest` still renders the placeholder page before implementation
- the backtest API client does not yet expose the canonical submission fields

---

### Task 2: Implement the formal `/backtest` workbench with the UI-V2-002 light theme

**Files:**
- Create: `web/src/features/backtest/backtest-center.tsx`
- Modify: `web/src/pages/backtest/index.tsx`
- Modify: `web/src/lib/api/backtests.ts`
- Modify: `web/src/types/backtests.ts`
- Modify: `web/src/app/router.tsx` only if the `/backtest` route needs to point to a different component export

- [ ] **Step 1: Write the minimal implementation**

Build a light-theme workbench that keeps the first screen narrow and explicit:

```tsx
<main className="page-stack">
  <PageHeader
    kicker="正式工作台"
    title="回测中心"
    description="运行回测、查看最近结果、复核报告和可复现性。"
    actionLabel="打开任务中心"
    onAction={() => navigate('/jobs')}
  />

  <section className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(320px,0.55fr)]">
    <Card>回测参数与运行按钮</Card>
    <Card>最近结果摘要与 fingerprint</Card>
  </section>

  <section className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
    <Card>最近结果列表</Card>
    <Card>当前选中结果的报告 / 验真 / JSON 标签页</Card>
  </section>
</main>
```

The form must expose:

- `trader_id`
- `date_from`
- `date_to`
- `strategy_version_id`
- `symbols`
- `mode`
- `use_snapshot_only`
- `scoring_profile`
- `config_path`

The page must:

1. Use `listBacktestResults()` to load the recent results list.
2. Use `getBacktestResult()` for the selected result.
3. Use `downloadBacktestReport()` and `downloadBacktestValidationReport()` for report tabs.
4. Submit jobs through `createJob()` using the canonical backtest param builders.
5. Keep loading, empty, error, retry, and permission denied states visible.
6. Keep the first screen light, clear, and consistent with `UI-V2-002` cards and spacing.

Update the backtest API client so the new canonical fields are sent:

```ts
export type BacktestJobSubmission = {
  traderId: string;
  dateFrom: string;
  dateTo: string;
  strategyVersionId: string;
  mode: 'full' | 'replay' | 'rule_validation';
  configPath: string;
  symbols: string[];
  useSnapshotOnly: boolean;
  scoringProfile: string;
};
```

```ts
export function buildBacktestRunParams(submission: BacktestJobSubmission): Record<string, unknown> {
  return {
    trader_id: submission.traderId,
    date_from: submission.dateFrom,
    date_to: submission.dateTo,
    strategy_version_id: submission.strategyVersionId || undefined,
    mode: submission.mode,
    config_path: submission.configPath,
    symbols: submission.symbols,
    use_snapshot_only: submission.useSnapshotOnly,
    scoring_profile: submission.scoringProfile,
  };
}
```

Use the same fields for reproducibility and validation job submissions.

- [ ] **Step 2: Run the focused tests to verify it passes**

Run:

```bash
cd web && pnpm vitest run src/pages/backtest/index.test.tsx src/lib/api/backtests.test.ts
```

Expected:

- `/backtest` renders the formal light-theme workbench
- backtest jobs send the canonical Web contract fields

---

### Task 3: Add regression coverage for the new workbench behavior

**Files:**
- Modify: `web/src/pages/backtest/index.test.tsx`
- Modify: `web/src/lib/api/backtests.test.ts`

- [ ] **Step 1: Write the failing tests**

Add coverage for:

1. Empty result set shows a useful empty state with reset actions.
2. Selecting a result shows the summary, report, validation report, and JSON tabs.
3. The run button submits `backtest-run` with the full canonical params.
4. The validate and reproducibility buttons submit the right job types.

```tsx
expect(mockedCreateJob).toHaveBeenCalledWith(
  expect.objectContaining({
    job_type: 'backtest-run',
    params: expect.objectContaining({
      symbols: ['000001.SZ'],
      use_snapshot_only: true,
      scoring_profile: 'stage5',
    }),
  }),
);
```

- [ ] **Step 2: Run the focused tests to verify it passes**

Run:

```bash
cd web && pnpm vitest run src/pages/backtest/index.test.tsx src/lib/api/backtests.test.ts
```

Expected:

- New workbench behavior is stable and deterministic
- The legacy `/backtests` page remains isolated

