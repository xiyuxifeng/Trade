# UI-V1-001 Routing Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define a single canonical Web route set for V1, keep legacy routes as explicit compatibility shims, and document a clear retirement path for each legacy entry.

**Architecture:** The router will expose one canonical route set for new development and keep legacy aliases in a narrow compatibility layer. Existing functional pages remain intact, while unimplemented V1 pages use explicit placeholder shells. Route documentation becomes the source of truth for canonical paths, legacy mappings, and retirement stages.

**Tech Stack:** React, React Router, TypeScript, Vite, existing app layout components

---

### Task 1: Canonical route table and compatibility shims

**Files:**
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/pages/jobs/index.tsx`
- Modify: `web/src/pages/workflows/index.tsx`
- Modify: `web/src/routes/overview.tsx`

- [ ] **Step 1: Update the router to expose canonical V1 paths**

```tsx
// Canonical V1 routes:
// /dashboard
// /jobs
// /jobs/:jobId
// /workflows
// /workflows/:workflowId/run
// /articles
// /artifacts
// /settings
```

- [ ] **Step 2: Add explicit legacy aliases that only redirect or reuse existing pages**

```tsx
// Legacy compatibility shims:
// / -> /dashboard
// /overview -> /dashboard
// /jobs?jobId=... -> /jobs/:jobId
// /workflows/:workflowId -> /workflows/:workflowId/run
// /legacy/* -> placeholder shell
```

- [ ] **Step 3: Teach JobsPage to honor a path parameter before query selection**

```tsx
// If /jobs/:jobId is present, prefer that value.
// Otherwise keep compatibility with ?jobId=...
```

- [ ] **Step 4: Teach WorkflowsPage to honor /workflows/:workflowId/run as a canonical path**

```tsx
// Keep the existing workflow detail/run UI.
// Ensure the run tab remains reachable from the canonical route.
```

### Task 2: Placeholder pages for unimplemented V1 routes

**Files:**
- Create: `web/src/pages/articles/index.tsx`
- Create: `web/src/pages/legacy/index.tsx`
- Modify: `web/src/app/router.tsx`

- [ ] **Step 1: Add a clear placeholder page for `/articles`**

```tsx
// Display that the articles page is not implemented yet.
// Include the route purpose and a short note about the canonical path.
```

- [ ] **Step 2: Add a clear placeholder shell for `/legacy/*`**

```tsx
// Display that the route is only a temporary compatibility entry.
// Explain which canonical path should be used instead.
```

- [ ] **Step 3: Route unmatched paths to the existing not-found shell**

```tsx
// Keep 404 distinct from "page not implemented".
```

### Task 3: Route documentation and retirement policy

**Files:**
- Create: `docs/New-Web-UI-Routing.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`

- [ ] **Step 1: Write the canonical route table and legacy mapping table**

```md
| Canonical route | Legacy mapping | Allowed stage | Retirement stage |
```

- [ ] **Step 2: Add V1/V2/V3 retirement rules**

```md
V1: define canonical + legacy.
V2: freeze legacy and keep only compatibility.
V3: remove legacy aliases and temporary shells.
```

- [ ] **Step 3: Add task-list entries for V2 and V3 route closure**

```md
NW-V2-S4-003: route compatibility layer freeze
NW-V3-S3-002: final route retirement
```

### Task 4: Verification

**Files:**
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/pages/jobs/index.tsx`
- Modify: `web/src/pages/workflows/index.tsx`

- [ ] **Step 1: Run targeted web tests or route smoke checks**

```bash
cd /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web
npm test -- --runInBand
```

- [ ] **Step 2: Verify canonical and legacy routes resolve as expected**

```text
/dashboard -> overview page
/ -> dashboard alias
/legacy/* -> placeholder shell
```

- [ ] **Step 3: Verify no business logic moved into the router**

```text
Router only wires pages, redirects, and placeholders.
```

