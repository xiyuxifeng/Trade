# Web Stage 4 Frontend Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Vite-based React frontend that exposes a task-center console aligned with the existing UI BFF, CLI commands, configuration surface, and project delivery goals.

**Architecture:** Use a single `web/` workspace with `pages` for routes, `features` for business areas, `components/ui` for shared primitives, and `lib/api` for all HTTP access. The first release should prioritize a task-driven dashboard: system status, jobs, workflows, artifacts, and market data, with later pages reusing the same shell and data-fetching patterns.

**Tech Stack:** Vite, React, TypeScript, Tailwind CSS, shadcn/ui, React Router, TanStack Query, Zod, React Hook Form, lucide-react, clsx, tailwind-merge, dayjs.

---

### Recommended Execution Order

1. Scaffold the frontend workspace.
2. Establish the design system foundation.
3. Build the API client and typed data contracts.
4. Implement the dashboard shell and full navigation skeleton.
5. Connect the overview page to live system summary data.
6. Implement the first batch of functional work areas: jobs, workflows, artifacts, and market.
7. Add verification, documentation, and Stage 4 entry alignment.

The shell/navigation task must include placeholder routes for the full Stage 4 navigation set from the design document:

- overview
- jobs
- workflows
- artifacts
- market
- strategies
- backtests
- reports
- settings
- ops

### Task 1: Scaffold the frontend workspace

**Files:**
- Create: `web/package.json`
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/app/providers.tsx`
- Create: `web/src/app/query-client.ts`
- Create: `web/src/app/router.tsx`
- Create: `web/src/styles/globals.css`

- [ ] **Step 1: Define the workspace scripts and base dependencies**

Add scripts for `dev`, `build`, `preview`, `lint`, and `typecheck`, and pin the initial frontend dependencies required by the stack above.

- [ ] **Step 2: Wire the application entrypoint**

Mount the router inside the app providers, register the TanStack Query client, and load global styles from `web/src/styles/globals.css`.

- [ ] **Step 3: Verify the scaffold builds**

Run: `pnpm install`

Run: `pnpm build`

Expected: the Vite app builds successfully with no unresolved imports or missing config files.

### Task 2: Establish the design system foundation

**Files:**
- Create: `web/tailwind.config.ts`
- Create: `web/postcss.config.js`
- Create: `web/components.json`
- Create: `web/src/components/ui/button.tsx`
- Create: `web/src/components/ui/card.tsx`
- Create: `web/src/components/ui/dialog.tsx`
- Create: `web/src/components/ui/drawer.tsx`
- Create: `web/src/components/ui/table.tsx`
- Create: `web/src/components/ui/tabs.tsx`
- Create: `web/src/components/ui/toast.tsx`
- Create: `web/src/components/ui/badge.tsx`
- Create: `web/src/components/ui/input.tsx`
- Create: `web/src/components/ui/select.tsx`
- Create: `web/src/components/ui/textarea.tsx`
- Create: `web/src/components/ui/skeleton.tsx`

- [ ] **Step 1: Add the Tailwind + shadcn wiring**

Set up Tailwind scanning for `web/src/**/*` and configure shadcn/ui so the first batch of primitives can be generated and customized locally.

- [ ] **Step 2: Add the primitives needed by Stage 4**

Implement the minimal UI set for tables, forms, dialogs, drawers, badges, and toasts so later pages can stay consistent.

- [ ] **Step 3: Verify the foundation renders**

Run: `pnpm build`

Expected: the design system files compile and are ready for use by page shells.

### Task 3: Build the API client and typed data contracts

**Files:**
- Create: `web/src/lib/api/http.ts`
- Create: `web/src/lib/api/system.ts`
- Create: `web/src/lib/api/jobs.ts`
- Create: `web/src/lib/api/workflows.ts`
- Create: `web/src/lib/api/artifacts.ts`
- Create: `web/src/lib/api/market.ts`
- Create: `web/src/types/system.ts`
- Create: `web/src/types/jobs.ts`
- Create: `web/src/types/workflows.ts`
- Create: `web/src/types/artifacts.ts`
- Create: `web/src/types/market.ts`

- [ ] **Step 1: Centralize fetch and error handling**

Create one HTTP wrapper that normalizes JSON parsing, HTTP failures, and API error payloads into a shared response shape.

- [ ] **Step 2: Implement the first UI BFF client**

Add typed wrappers for `/api/ui/v1/system/status`, `/api/ui/v1/jobs*`, `/api/ui/v1/workflows*`, `/api/ui/v1/artifacts*`, and `/api/ui/v1/market*`.

- [ ] **Step 3: Add contract-friendly types**

Define the minimum response types required for the first dashboard pages, keeping the contracts narrow enough to match the currently shipped API surface.

- [ ] **Step 4: Verify the client layer typechecks**

Run: `pnpm typecheck`

Expected: the client and contract layer compile without implicit `any` or missing field usage.

### Task 4: Implement the dashboard shell and navigation

**Files:**
- Create: `web/src/layouts/dashboard-layout.tsx`
- Create: `web/src/components/layout/sidebar.tsx`
- Create: `web/src/components/layout/topbar.tsx`
- Create: `web/src/components/layout/page-header.tsx`
- Create: `web/src/components/layout/status-strip.tsx`
- Create: `web/src/pages/overview/index.tsx`
- Create: `web/src/pages/jobs/index.tsx`
- Create: `web/src/pages/workflows/index.tsx`
- Create: `web/src/pages/artifacts/index.tsx`
- Create: `web/src/pages/market/index.tsx`
- Create: `web/src/pages/strategies/index.tsx`
- Create: `web/src/pages/backtests/index.tsx`
- Create: `web/src/pages/reports/index.tsx`
- Create: `web/src/pages/settings/index.tsx`
- Create: `web/src/pages/ops/index.tsx`
- Modify: `web/src/app/router.tsx`

- [ ] **Step 1: Define the navigation by user task**

Organize the sidebar around user outcomes: overview, jobs, workflows, artifacts, market, strategies, backtests, reports, settings, and ops. Keep the first five destinations fully functional and the later destinations as stable placeholder routes in Stage 4.

- [ ] **Step 2: Build the shell layout**

Add a responsive layout with sidebar, top bar, main content area, and a mobile-safe collapse pattern.

- [ ] **Step 3: Wire the first pages to the shell**

Create placeholder pages for overview, jobs, workflows, artifacts, market, strategies, backtests, reports, settings, and ops, then mount them through the router.

- [ ] **Step 4: Verify the shell is navigable**

Run: `pnpm build`

Expected: the shell compiles and each route resolves without runtime import errors.

### Task 5: Connect the overview page to live system status

**Files:**
- Modify: `web/src/pages/overview/index.tsx`
- Create: `web/src/features/system-status/use-system-status.ts`
- Create: `web/src/features/system-status/system-status-panel.tsx`
- Create: `web/src/features/system-status/use-recent-activity.ts`
- Create: `web/src/features/system-status/recent-jobs-panel.tsx`
- Create: `web/src/features/system-status/recent-artifacts-panel.tsx`
- Create: `web/src/components/status/metric-card.tsx`
- Create: `web/src/components/status/health-pill.tsx`

- [ ] **Step 1: Fetch `/api/ui/v1/system/status`**

Render the current run mode, database status, config path, key directory health, recent jobs, and recent artifacts directly on the overview page.

- [ ] **Step 2: Add loading, empty, and error states**

Make the overview page show a skeleton while loading, a clear fallback when data is missing, and a readable error state when the API fails.

- [ ] **Step 3: Verify the page is usable on first load**

Run: `pnpm build`

Expected: the overview page compiles and displays the first live status snapshot when the backend is available.

### Task 6: Implement the first batch of functional work areas

**Files:**
- Modify: `web/src/pages/jobs/index.tsx`
- Modify: `web/src/pages/workflows/index.tsx`
- Modify: `web/src/pages/artifacts/index.tsx`
- Modify: `web/src/pages/market/index.tsx`
- Create: `web/src/features/job-center/use-jobs.ts`
- Create: `web/src/features/job-center/job-list.tsx`
- Create: `web/src/features/job-center/job-detail-drawer.tsx`
- Create: `web/src/features/workflow-center/use-workflows.ts`
- Create: `web/src/features/workflow-center/workflow-list.tsx`
- Create: `web/src/features/artifact-center/use-artifacts.ts`
- Create: `web/src/features/artifact-center/artifact-list.tsx`
- Create: `web/src/features/market-center/use-market-symbols.ts`
- Create: `web/src/features/market-center/use-market-ohlcv.ts`
- Create: `web/src/features/market-center/market-symbol-list.tsx`
- Create: `web/src/features/market-center/market-ohlcv-panel.tsx`

- [ ] **Step 1: Make the jobs page operational**

Show the job list, job status, job logs entry, and cancel action on the jobs page.

- [ ] **Step 2: Make the workflow page operational**

Show workflow templates, trigger entry, run status, and result summary on the workflow page.

- [ ] **Step 3: Make the artifact page operational**

Show artifact list, preview entry, download entry, and safety hints for restricted content.

- [ ] **Step 4: Make the market page operational**

Show market symbols and OHLCV query results with filters for symbol and date range.

- [ ] **Step 5: Verify the first batch pages build**

Run: `pnpm build`

Expected: the first batch pages render without import errors and can consume the current UI BFF.

### Task 7: Add Stage 4 verification and documentation alignment

**Files:**
- Modify: `web/package.json`
- Create: `web/README.md`
- Modify: `docs/Web-TaskList.md`

- [ ] **Step 1: Add explicit validation scripts**

Keep `lint`, `typecheck`, and `build` as the minimum validation gate for Stage 4.

- [ ] **Step 2: Document the frontend launch path**

Write the local startup steps for `web/` and note the first supported UI BFF endpoints.

- [ ] **Step 3: Link this plan back into Stage 4**

Update `docs/Web-TaskList.md` so Stage 4 points to this implementation plan as the stable execution reference.

- [ ] **Step 4: Verify the documented workflow matches the code**

Run: `pnpm build`

Expected: the documented startup path and the actual workspace structure stay aligned.
