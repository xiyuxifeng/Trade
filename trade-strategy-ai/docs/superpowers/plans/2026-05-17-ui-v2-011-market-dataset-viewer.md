# Market Dataset Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `/market/datasets` as a standalone Market Dataset Viewer that reuses the existing market API, stays visually aligned with `UI-V2-002`, and lets users inspect dataset metadata, paginated sample rows, and quality information without turning `/market` into a second control center.

**Architecture:** Keep `/market` as the snapshot browser and add a separate dataset viewer route with its own shell, filters, list, detail panel, and sample-row pagination. Use the existing market API client and shared UI kit components; no backend, workflow, or CLI changes are needed for this task. Query semantics are split by capability: `dataset_id` is an exact lookup into the selected dataset detail, `trade_date / market / dataset_type / quality_status` drive the dataset catalog list, and `symbol / section` act as sample-row filters inside the selected dataset panel.

**Tech Stack:** React, React Router, TanStack Query, existing `web/src/lib/api/market.ts`, existing `web/src/types/market.ts`, Vitest, Testing Library, current UI kit.

---

### Task 1: Expose the canonical `/market/datasets` route and page entry

**Files:**
- Create: `web/src/pages/market/datasets/index.tsx`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/route-registry.ts`
- Modify: `web/src/pages/market/index.tsx`
- Test: `web/src/app/route-registry.test.ts`
- Test: `web/src/pages/market/index.test.tsx`

- [ ] **Step 1: Write the failing route and entry tests**

Add these assertions first:

```ts
expect(resolveRouteByPathname('/market/datasets').path).toBe('/market/datasets');
expect(resolveRouteByPathname('/market/datasets').kind).toBe('canonical');
expect(resolveRouteByPathname('/market/datasets').label).toBe('市场数据集');
```

In the market browser test, assert there is a visible link from `/market` to the dataset viewer:

```ts
expect(screen.getByRole('link', { name: '查看数据集' })).toHaveAttribute('href', '/market/datasets');
```

- [ ] **Step 2: Run the targeted tests and confirm they fail**

Run:

```bash
cd web && pnpm vitest run src/app/route-registry.test.ts src/pages/market/index.test.tsx
```

Expected:

- route test fails because `/market/datasets` is not registered yet
- market page test fails because the dataset viewer link does not exist yet

- [ ] **Step 3: Implement the route and page entry**

Add the canonical router entry and route registry record for `/market/datasets`, then add a visible link in the `/market` page header or page actions that takes the user to the new dataset viewer. Create the page shell at `web/src/pages/market/datasets/index.tsx` so the route resolves cleanly before the feature shell is built.

- [ ] **Step 4: Re-run the route and entry tests**

Run:

```bash
cd web && pnpm vitest run src/app/route-registry.test.ts src/pages/market/index.test.tsx
```

Expected:

- both tests pass
- `/market` still renders the snapshot browser
- `/market/datasets` resolves as a canonical route

- [ ] **Step 5: Commit the route wiring**

```bash
git add web/src/app/router.tsx web/src/app/route-registry.ts web/src/pages/market/index.tsx web/src/pages/market/datasets/index.tsx web/src/app/route-registry.test.ts web/src/pages/market/index.test.tsx
git commit -m "feat(ui): add market dataset viewer route"
```

### Task 2: Build the dataset viewer shell and query-state model

**Files:**
- Create: `web/src/features/market-datasets/index.ts`
- Create: `web/src/features/market-datasets/market-dataset-viewer-shell.tsx`
- Create: `web/src/features/market-datasets/market-dataset-viewer-filters.tsx`
- Create: `web/src/features/market-datasets/market-dataset-viewer-list.tsx`
- Create: `web/src/features/market-datasets/market-dataset-viewer-detail.tsx`
- Test: `web/src/pages/market/datasets/index.test.tsx`

- [ ] **Step 1: Write the failing shell test**

Mock the existing market API and verify the page renders a workbench shell with list/detail separation:

```ts
vi.mock('@/lib/api/market', () => ({
  listMarketDatasets: vi.fn(),
  getMarketDataset: vi.fn(),
  getMarketSnapshot: vi.fn(),
}));
```

Assert the page:

```ts
expect(await screen.findByRole('heading', { name: 'Market Dataset Viewer' })).toBeInTheDocument();
expect(screen.getByText('数据集列表')).toBeInTheDocument();
expect(screen.getByText('数据集详情')).toBeInTheDocument();
```

- [ ] **Step 2: Run the new page test and confirm it fails**

Run:

```bash
cd web && pnpm vitest run src/pages/market/datasets/index.test.tsx
```

Expected:

- the page test fails because the dataset viewer shell does not exist yet
- the test should make it obvious whether the route, shell, or API wiring is missing

- [ ] **Step 3: Implement the shell, filters, and catalog query**

Build a standalone dataset viewer shell that:

- uses `useSearchParams` to keep `dataset_id`, `trade_date`, `market`, `dataset_type`, `quality_status`, `symbol`, `section`, `limit`, and `offset` in the URL
- treats `dataset_id` as the exact lookup into the selected dataset detail
- uses `trade_date / market / dataset_type / quality_status` for the dataset catalog query
- keeps `symbol / section` as sample-row filters inside the selected dataset panel, so the task stays UI-only and does not require a backend search contract expansion
- uses the shared `PageHeader`, `SectionCard`, `LoadingState`, `EmptyState`, `ErrorState`, and `StatusBadge` components

Keep the initial layout simple:

- left column: dataset catalog list
- right column: dataset detail
- dataset selection must stay in the URL so the viewer can be shared and restored

- [ ] **Step 4: Re-run the page shell test**

Run:

```bash
cd web && pnpm vitest run src/pages/market/datasets/index.test.tsx
```

Expected:

- the shell renders the dataset viewer title
- the list/detail split is visible
- selecting a dataset updates the URL and keeps the right pane stable

- [ ] **Step 5: Commit the shell and query-state work**

```bash
git add web/src/features/market-datasets/index.ts web/src/features/market-datasets/market-dataset-viewer-shell.tsx web/src/features/market-datasets/market-dataset-viewer-filters.tsx web/src/features/market-datasets/market-dataset-viewer-list.tsx web/src/features/market-datasets/market-dataset-viewer-detail.tsx web/src/pages/market/datasets/index.test.tsx
git commit -m "feat(ui): add market dataset viewer shell"
```

### Task 3: Add dataset detail, sample rows, and full state handling

**Files:**
- Create: `web/src/features/market-datasets/market-dataset-viewer-sample-rows.tsx`
- Modify: `web/src/features/market-datasets/market-dataset-viewer-detail.tsx`
- Modify: `web/src/features/market-datasets/market-dataset-viewer-shell.tsx`
- Modify: `web/src/pages/market/datasets/index.test.tsx`

- [ ] **Step 1: Write the failing detail-state tests**

Cover these states explicitly in the page test:

```ts
expect(await screen.findByText('没有匹配的数据集')).toBeInTheDocument();
expect(await screen.findByText('数据集不存在')).toBeInTheDocument();
expect(await screen.findByText('没有权限访问数据集')).toBeInTheDocument();
expect(await screen.findByText('上游服务不可用')).toBeInTheDocument();
expect(await screen.findByText('无效查询参数')).toBeInTheDocument();
```

Also assert that the detail panel contains a paginated sample-row table when data exists:

```ts
expect(screen.getByText('分页样本')).toBeInTheDocument();
expect(screen.getByRole('button', { name: '下一页' })).toBeInTheDocument();
```

- [ ] **Step 2: Run the detail-state test and confirm it fails**

Run:

```bash
cd web && pnpm vitest run src/pages/market/datasets/index.test.tsx
```

Expected:

- the state assertions fail until the detail pane is implemented
- pagination controls do not exist yet

- [ ] **Step 3: Implement detail rendering and paginated sample rows**

Implement the detail panel so it shows:

- dataset metadata
- data quality summary
- snapshot回链
- paginated sample rows

Use the existing dataset detail response as the source of truth and do not load the entire dataset at once. Keep pagination local to the detail pane so the rest of the page does not flash or reset when the user changes rows.

For sample-row filtering:

- `symbol` and `section` should narrow the visible sample rows for the currently selected dataset
- if the current page does not contain a matching row, show an empty-state hint instead of inventing a new API path

For relationships:

- if the dataset exposes `snapshot_id`, link back to `/market?snapshot_id=<snapshot_id>`
- if the detail response includes a resolvable job reference in `storage_ref.metadata.job_id`, link to `/jobs/<jobId>` and `/artifacts?jobId=<jobId>`
- do not render a fake download action unless the response exposes a concrete artifact URL

Handle every required state with shared components:

- loading
- empty
- pagination loading
- permission denied
- dataset missing
- API unavailable
- invalid query

- [ ] **Step 4: Re-run the page test and the API contract test**

Run:

```bash
cd web && pnpm vitest run src/pages/market/datasets/index.test.tsx src/lib/api/contract.test.ts
```

Expected:

- dataset viewer states pass
- the existing API contract test still proves `listMarketDatasets` and `getMarketDataset` keep stable paths and auth behavior

- [ ] **Step 5: Commit the detail and pagination work**

```bash
git add web/src/features/market-datasets/market-dataset-viewer-shell.tsx web/src/features/market-datasets/market-dataset-viewer-detail.tsx web/src/features/market-datasets/market-dataset-viewer-sample-rows.tsx web/src/pages/market/datasets/index.test.tsx
git commit -m "feat(ui): add market dataset viewer detail"
```

### Task 4: Update docs, routing notes, and task tracking

**Files:**
- Modify: `docs/New-Web-UI-Routing.md`
- Modify: `docs/New-Web-UI-Information-Architecture.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-17.md`
- Modify: `daily-report/2026-05-17.md`

- [ ] **Step 1: Write the closing verification test command**

Use the full focused run that covers the route, page, and contract layers:

```bash
cd web && pnpm vitest run src/app/route-registry.test.ts src/pages/market/index.test.tsx src/pages/market/datasets/index.test.tsx src/lib/api/contract.test.ts
```

Expected:

- all dataset viewer assertions pass
- `/market` still behaves as the snapshot browser
- `/market/datasets` is the new standalone viewer

- [ ] **Step 2: Sync the documentation**

Update the routing and IA docs so they reflect the final split:

- `/market` = `Market Snapshot Browser`
- `/market/datasets` = `Market Dataset Viewer`
- the two pages share the market API but have distinct responsibilities

Update the task list and session notes only after the implementation truly satisfies the acceptance criteria.

- [ ] **Step 3: Commit the finished task**

```bash
git add docs/New-Web-UI-Routing.md docs/New-Web-UI-Information-Architecture.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-17.md daily-report/2026-05-17.md
git commit -m "docs(ui): close ui-v2-011 dataset viewer"
```

## Self-Review Checklist

Before starting implementation, verify:

1. Every spec requirement maps to one of the tasks above.
2. The plan does not introduce any backend contract change.
3. The plan keeps `/market` and `/market/datasets` separate.
4. The plan does not promise a full-text search API that does not exist.
5. The plan stays aligned with `UI-V2-002` styling and the existing shared UI kit.
6. There are no placeholders such as `TODO` or `TBD`.
