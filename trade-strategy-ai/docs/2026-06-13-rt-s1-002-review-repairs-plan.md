# RT-S1-002 Review Repairs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the remaining RT-S1-002 review blocker and high/medium findings without starting RT-S1-003 or Stage 2.

**Architecture:** Formal routes reuse existing domain hooks, actions, and result components through explicit business-safe product modes. `route-config.tsx` remains the only route/navigation/permission/metadata/compatibility source. Tests derive rendered routes from that source and verify truthful states and business-safe copy.

**Tech Stack:** React 18, TypeScript, React Router, TanStack Query, Vitest, Testing Library.

---

### Task 1: Business-safe real domain capabilities

**Files:**
- Modify: `web/src/pages/rules/index.tsx`
- Modify: `web/src/pages/authors/index.tsx`
- Modify: `web/src/pages/strategies/StrategyOverviewPage.tsx`
- Modify: `web/src/pages/system/index.tsx`
- Modify scoped existing domain components only where an explicit `productMode` boundary is required.
- Test: `web/src/pages/product-entry-pages.test.tsx`

- [ ] Add failing viewer tests proving each formal page renders real data/actions without rendering the administrator details control or forbidden engineering terms.
- [ ] Run the scoped test and verify failures identify static-only wrappers.
- [ ] Add minimal product-mode boundaries that reuse existing hooks/actions/results while preserving compatibility defaults.
- [ ] Run scoped domain and compatibility tests and verify both modes pass.

### Task 2: Route-derived state matrix

**Files:**
- Modify: `web/src/app/route-config.tsx` only if a non-duplicated render classification is required.
- Modify: `web/src/pages/product-page-state-matrix.test.tsx`

- [ ] Replace the standalone Adapter-only matrix with a test whose page list is derived from `routeConfig`.
- [ ] Cover formal pages, compatibility pages, parameterized details, run details, system pages, and Chinese 404 without defining a second route list.
- [ ] Verify loading, empty, error, partial, permission denied, and unavailable state contracts for routes that support injected availability; verify truthful fixed boundaries for compatibility pages.
- [ ] Run the matrix and route tests.

### Task 3: Business Chinese result status

**Files:**
- Modify: `web/src/features/strategy-workspace/strategy-lifecycle-page.tsx`
- Test: `web/src/pages/daily/index.test.tsx`

- [ ] Add failing tests for English/internal after-close status, partial markers, and fallback reasons.
- [ ] Add a bounded display mapper that returns business Chinese and never changes stored/API values.
- [ ] Run daily and strategy lifecycle tests.

### Task 4: Parent verification and implementation log

**Files:**
- Modify: `docs/Refactor-Implementation-Log.md`

- [ ] Run the RT-S1-002 focused suite.
- [ ] Run `pnpm typecheck`.
- [ ] Run `git diff --check`.
- [ ] Inspect the complete final diff for scope, duplicate facts, forbidden terms, and accidental RT-S1-003/Stage 2 changes.
- [ ] Record exact evidence and keep RT-S1-002 `[-]` until shared Stage 1 gates pass.
