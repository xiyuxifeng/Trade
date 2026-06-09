# UI-V2-010 Market Snapshot Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the canonical `/market` route into a formal Market Snapshot Browser that lets users filter snapshots, inspect a selected snapshot in place, review quality and regime features, and jump to Job or Artifact when needed.

**Architecture:** Keep the browser as a single canonical workbench page with a list pane and a detail pane. The page shell owns query-string state and high-level orchestration; focused subcomponents render filters, snapshot rows, detail sections, quality summary, and regime features. The frontend will reuse the backend market snapshot and regime feature APIs already exposed by `NW-V2-S2-005` and `NW-V2-S2-006`, so this task is UI-only and does not touch provider logic, workflows, or the market data generation pipeline.

**Tech Stack:** React, React Router, TanStack Query, the existing `fetchJson` API client, Vitest, React Testing Library, shared `ErrorState`, shared `SectionCard` / `LoadingState` / `EmptyState` / `StatusBadge` components.

---

### Task 1: Extend the market API client and response types for browser usage

**Files:**
- Modify: `web/src/types/market.ts`
- Modify: `web/src/lib/api/market.ts`
- Create: `web/src/lib/api/market.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it, vi } from 'vitest';
import { getMarketRegimeFeature, listMarketRegimeFeatures } from '@/lib/api/market';

describe('market api client', () => {
  it('builds regime feature list and detail urls', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response('{}', {
          status: 200,
          headers: { 'content-type': 'application/json' },
        }),
      ),
    );

    await listMarketRegimeFeatures({
      tradeDate: '2026-05-16',
      market: 'CN',
      featureVersion: 'market-regime-features-v1',
      limit: 10,
      offset: 0,
    });
    await getMarketRegimeFeature('snap-001', 'market-regime-features-v1');

    const calls = vi.mocked(fetch).mock.calls.map(([url]) => String(url));
    expect(calls).toContain(
      '/api/ui/v1/market/regime-features?trade_date=2026-05-16&market=CN&feature_version=market-regime-features-v1&limit=10&offset=0',
    );
    expect(calls).toContain(
      '/api/ui/v1/market/snapshots/snap-001/regime-features?feature_version=market-regime-features-v1',
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/lib/api/market.test.ts src/lib/api/market-workspace.test.ts
```

Expected:

- FAIL because `listMarketRegimeFeatures` / `getMarketRegimeFeature` do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add the browser-facing response types in `web/src/types/market.ts`:

```ts
export type MarketRegimeFeatureSummary = {
  id: string;
  snapshot_id: string;
  trade_date: string;
  market: string;
  feature_version: string;
  quality_status: string;
  available_feature_count: number;
  partial_feature_count: number;
  missing_feature_count: number;
  feature_payload_json: Record<string, unknown>;
  summary_json: Record<string, unknown>;
  storage_ref: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export type MarketRegimeFeatureListResponse = {
  filters: Record<string, unknown>;
  page: MarketQueryPage;
  items: MarketRegimeFeatureSummary[];
};

export type MarketRegimeFeatureDetailResponse = {
  feature: MarketRegimeFeatureSummary;
  feature_payload_json: Record<string, unknown>;
  summary_json: Record<string, unknown>;
  warnings: string[];
};
```

Add the matching client helpers in `web/src/lib/api/market.ts`:

```ts
export function listMarketRegimeFeatures(params: {
  tradeDate?: string;
  snapshotId?: string;
  market?: string;
  featureVersion?: string;
  limit?: number;
  offset?: number;
} = {}) {
  const query = buildQueryString({
    trade_date: params.tradeDate,
    snapshot_id: params.snapshotId,
    market: params.market,
    feature_version: params.featureVersion,
    limit: params.limit,
    offset: params.offset,
  });
  return fetchJson<MarketRegimeFeatureListResponse>(`/market/regime-features${query ? `?${query}` : ''}`);
}

export function getMarketRegimeFeature(snapshotId: string, featureVersion?: string) {
  const query = buildQueryString({ feature_version: featureVersion });
  return fetchJson<MarketRegimeFeatureDetailResponse>(
    `/market/snapshots/${snapshotId}/regime-features${query ? `?${query}` : ''}`,
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/lib/api/market.test.ts src/lib/api/market-workspace.test.ts
```

Expected:

- PASS
- URL assertions should match the backend contract exactly

- [ ] **Step 5: Commit**

```bash
git add web/src/types/market.ts web/src/lib/api/market.ts web/src/lib/api/market.test.ts
git commit -m "feat(ui): extend market api for snapshot browser"
```

---

### Task 2: Replace the canonical `/market` page with a snapshot browser shell

**Files:**
- Create: `web/src/features/market-browser/index.ts`
- Create: `web/src/features/market-browser/market-snapshot-browser-shell.tsx`
- Create: `web/src/features/market-browser/market-snapshot-browser-filters.tsx`
- Create: `web/src/features/market-browser/market-snapshot-browser-list.tsx`
- Create: `web/src/features/market-browser/market-snapshot-browser-detail.tsx`
- Create: `web/src/features/market-browser/market-snapshot-browser-regime-features.tsx`
- Create: `web/src/features/market-browser/market-snapshot-browser-shell.test.tsx`
- Modify: `web/src/pages/market/index.tsx`
- Modify: `web/src/pages/market/index.test.tsx`

- [ ] **Step 1: Write the failing test**

The page test should prove the canonical route now renders the browser title, loads data, keeps the list visible, and shows the selected snapshot detail in place.

```tsx
import { describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { MarketPage } from './index';
import { renderWithRouter } from '@/test/test-utils';
import { listMarketSnapshots, getMarketSnapshot, listMarketSnapshotSections, getMarketSnapshotQuality, listMarketRegimeFeatures, getMarketRegimeFeature } from '@/lib/api/market';

describe('MarketPage', () => {
  it('renders the market snapshot browser and detail pane', async () => {
    renderWithRouter([{ path: '/market', element: <MarketPage /> }], ['/market?snapshot_id=snap-001&trade_date=2026-05-16&market=CN']);

    expect(await screen.findByRole('heading', { name: 'Market Snapshot Browser' })).toBeInTheDocument();
    expect(screen.getByText('snap-001')).toBeInTheDocument();
    expect(screen.getByText(/质量报告/)).toBeInTheDocument();
  });
});
```

Add a second test that forces the detail query to fail while the list still renders:

```tsx
it('shows a shared error state when the selected snapshot is missing', async () => {
  // mock listMarketSnapshots success, getMarketSnapshot reject with ApiError(404, ...)
  expect(await screen.findByText('快照不存在')).toBeInTheDocument();
  expect(screen.getByText('snap-001')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/pages/market/index.test.tsx src/features/market-browser/market-snapshot-browser-shell.test.tsx
```

Expected:

- FAIL because the new browser shell files do not exist yet and `/market` still renders the old task-runner workspace.

- [ ] **Step 3: Write minimal implementation**

Build the browser shell under `web/src/features/market-browser/` and keep the canonical page thin:

```tsx
// web/src/pages/market/index.tsx
import { MarketSnapshotBrowserShell } from '@/features/market-browser';

export function MarketPage() {
  return <MarketSnapshotBrowserShell />;
}
```

The shell should:

- parse `trade_date`, `market`, `quality_status`, and `snapshot_id` from `useSearchParams`
- query the snapshot list first
- keep the selected snapshot in the URL
- load snapshot detail, section list, quality report, and regime features in parallel
- render the detail pane with `SectionCard`, `StatusBadge`, `LoadingState`, `EmptyState`, and `ErrorState`
- keep the list usable even if the detail pane fails
- use the existing shared `ErrorState` instead of a separate market-only error system
- link to `/jobs/:jobId` and `/artifacts`

Suggested component split:

- `market-snapshot-browser-shell.tsx` owns queries, URL state, selection, and layout
- `market-snapshot-browser-filters.tsx` renders the compact filter bar
- `market-snapshot-browser-list.tsx` renders the snapshot list and selection highlight
- `market-snapshot-browser-detail.tsx` renders the selected snapshot, quality report, sections, and links
- `market-snapshot-browser-regime-features.tsx` renders optional regime feature content

Example shell query flow:

```tsx
const [searchParams, setSearchParams] = useSearchParams();
const tradeDate = searchParams.get('trade_date') ?? formatLocalDateInputOffset(0);
const market = searchParams.get('market') ?? 'CN';
const qualityStatus = searchParams.get('quality_status') ?? '';
const selectedSnapshotId = searchParams.get('snapshot_id') ?? '';

const snapshotsQuery = useQuery({
  queryKey: ['market-snapshots', tradeDate, market, qualityStatus],
  queryFn: () => listMarketSnapshots({ tradeDate, market, qualityStatus, limit: 50, offset: 0 }),
});

const snapshotDetailQuery = useQuery({
  queryKey: ['market-snapshot-detail', selectedSnapshotId],
  queryFn: () => getMarketSnapshot(selectedSnapshotId),
  enabled: Boolean(selectedSnapshotId),
});
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/pages/market/index.test.tsx src/features/market-browser/market-snapshot-browser-shell.test.tsx
```

Expected:

- PASS
- The browser should expose a stable title, a list pane, and a detail pane without reintroducing CLI/task-runner language as the primary interaction

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/market/index.tsx web/src/pages/market/index.test.tsx web/src/features/market-browser
git commit -m "feat(ui): add market snapshot browser shell"
```

---

### Task 3: Align market naming, route metadata, and error recovery copy

**Files:**
- Modify: `web/src/app/navigation.ts`
- Modify: `web/src/app/route-registry.ts`
- Modify: `web/src/app/route-registry.test.ts`
- Modify: `web/src/lib/error-recovery.ts`
- Modify: `web/src/lib/error-recovery.test.ts`
- Modify: `web/src/pages/backtest/index.tsx`
- Modify: `web/src/pages/backtest/index.test.tsx`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-17.md`
- Modify: `daily-report/2026-05-17.md`

- [ ] **Step 1: Write the failing test**

Update the route and error-recovery tests so they lock the browser wording:

```ts
import { describe, expect, it } from 'vitest';
import { ApiError } from '@/lib/api/http';
import { buildErrorRecoveryState } from '@/lib/error-recovery';
import { resolveRouteByPathname } from '@/app/route-registry';

describe('market browser copy', () => {
  it('uses market snapshot browser wording in the route registry', () => {
    expect(resolveRouteByPathname('/market').description).toBe('市场快照浏览器');
  });

  it('uses market snapshot browser wording in shared error recovery', () => {
    const state = buildErrorRecoveryState(new ApiError(503, 'provider unavailable'), 'market');

    expect(state.title).toContain('市场快照浏览器');
    expect(state.actions.some((action) => action.to === '/market')).toBe(true);
  });
});
```

Update the backtest entry test to reflect the same browser label:

```tsx
expect(screen.getByText('前往市场快照浏览器')).toBeInTheDocument();
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/app/route-registry.test.ts src/lib/error-recovery.test.ts src/pages/backtest/index.test.tsx
```

Expected:

- FAIL because the existing route metadata and error-recovery copy still say `市场数据工作台`

- [ ] **Step 3: Write minimal implementation**

Update the market copy in the shared UI metadata:

```ts
// web/src/app/navigation.ts
{ label: '市场数据', path: '/market', description: '市场快照浏览器' },

// web/src/app/route-registry.ts
{ label: '市场数据', path: '/market', description: '市场快照浏览器', kind: 'canonical' },

// web/src/lib/error-recovery.ts
market: '市场快照浏览器',
```

Make the backtest cross-link copy consistent with the browser naming:

```tsx
// web/src/pages/backtest/index.tsx
<p>请先通过策略工作台、市场快照浏览器和产物中心完成前置数据检查。</p>
<Button ... onClick={() => navigate('/market')}>
  前往市场快照浏览器
</Button>
```

Sync the task records after the UI work is complete:

```md
- Mark `UI-V2-010` as `[x]` only after the browser page, API client, tests, and copy updates are all passing.
- Update `daily-sessions/2026-05-17.md` resume point to the next UI/main task.
- Update `daily-report/2026-05-17.md` with the completed browser work and validation results.
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web
/Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm vitest run src/app/route-registry.test.ts src/lib/error-recovery.test.ts src/pages/backtest/index.test.tsx
```

Expected:

- PASS
- The UI copy should now consistently call `/market` a browser instead of a task-runner workbench

- [ ] **Step 5: Commit**

```bash
git add web/src/app/navigation.ts web/src/app/route-registry.ts web/src/app/route-registry.test.ts web/src/lib/error-recovery.ts web/src/lib/error-recovery.test.ts web/src/pages/backtest/index.tsx web/src/pages/backtest/index.test.tsx docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-17.md daily-report/2026-05-17.md
git commit -m "feat(ui): formalize market snapshot browser copy"
```

---

## Plan Coverage Check

- `trade_date` / `market` / `quality_status` filtering: Task 2
- snapshot list: Task 2
- snapshot detail: Task 2
- quality report: Task 2
- sections: Task 2
- regime features: Task 1 + Task 2
- Job Detail link: Task 2
- Artifact Center link: Task 2
- loading / empty / partial / permission / API unavailable / invalid query states: Task 2 + Task 3
- shared error handling: Task 2 + Task 3
- `UI-V2-002` light theme alignment: Task 2 + Task 3
- TaskList / session / report sync: Task 3

## Risks and Watchpoints

- The browser page must stay a single canonical `/market` page; do not add a second mandatory detail route in the first pass.
- The page can get large if the list, detail, and regime-feature rendering are not split into subcomponents. Keep the shell small and push display logic into focused files.
- Do not revive the old `market-workspace` task-runner behavior as the primary interaction path.
- Do not read local files or call providers from the frontend.
- Do not mark `UI-V2-010` complete until tests and copy updates all pass.
