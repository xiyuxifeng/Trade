# System Jobs, Runs, and Page Shell Cleanup Plan

## Purpose

This document consolidates the product cleanup work around System Management into three bounded implementation tasks. The goal is to make the system easier for users to understand and operate before delivery:

1. `/system/runs` should explain what happened, what is affected, and what the user should do next.
2. Job management should be a first-class system feature with dual entry points: business pages for normal users and `/system/jobs` for operators/admins.
3. Pages should not all be forced into the same `Input / Processing / Output` layout when that structure does not match the user task.

The tasks below intentionally avoid splitting the work too finely. Each task includes required scope, implementation notes, and validation expectations.

---

## Current Problems

### 1. `/system/runs` is too technical and flat

The current page mixes formal business traces, E2E/repair artifacts, data fetch details, UUIDs, fingerprints, backtest reproducibility details, and partial-state repair text in a single flat list. Users cannot quickly tell:

- whether the system is currently healthy;
- whether anything blocks them;
- which item needs action;
- what the next action is;
- which details are only for operators.

The current API accepts only `limit`; the frontend currently requests a small recent set. There is no real pagination, status filtering, business-type filtering, or grouped overview.

### 2. Job management exists but is not exposed as a formal system entry

The backend already has job definition, creation, listing, detail, logs, timeline, artifacts, pause, resume, cancel, and retry APIs. The frontend also has legacy Job list/table/progress/control components. However, `/jobs` and `/jobs/:jobId` are compatibility routes that redirect to `/system/runs`, and `/system/runs` does not actually provide job management.

Users need to freely start, pause, resume, cancel, retry, and inspect jobs. This needs a dedicated formal system entry.

### 3. Too many pages use `Input / Processing Status / Output` mechanically

`ProductPageAdapter` and `BusinessPageShell` currently push pages into a workflow-shaped layout. This is useful for workflow pages, but it is noisy for overview, list, library, and management pages. Pages such as system status, runs, job management, article library, rules library, authors, and configuration should use a cleaner layout.

---

## Target System Management Structure

Recommended navigation under System Management:

```text
/system
├─ /system/status          System status and dependencies
├─ /system/configuration   Configuration and profile management
├─ /system/data            Data and scheduling
├─ /system/jobs            Job management
└─ /system/runs            Runs and alerts overview
```

Recommended separation:

- `/system/jobs`: operational control of jobs.
- `/system/runs`: business-readable run/alert explanation.
- Business pages: normal user actions that create jobs without exposing internal job JSON.
- Operator/admin advanced panels: technical IDs, fingerprints, raw metadata, and diagnostic details.

---

## Required Reading Before Implementation

Before starting any of the tasks, read the current project constraints and implementation history that control navigation, system management, traceability, and user-facing availability semantics.

### Required for all tasks

- `docs/AI-Conversation-Project-Constraints-1.md`
- `docs/AI-Conversation-Project-Constraints-2.md`
- `docs/AI-Conversation-Templates.md`
- `docs/RT-S12-002-preflight-residual-risk-triage.md`
- `docs/refactor-implementation-logs/stage-11.md`
- `docs/refactor-implementation-logs/stage-12.md`
- `web/src/app/route-config.tsx`
- `web/src/components/layout/business-page-shell.tsx`
- `web/src/components/layout/product-page-adapter.tsx`
- `web/src/pages/system/index.tsx`

### Required for Task 2

- `api/routers/ui/jobs.py`
- `src/services/job_service.py`
- `src/services/job_registry.py`
- worker implementation files that pick up and execute jobs
- `web/src/lib/api/jobs.ts`
- `web/src/types/jobs.ts`
- `web/src/pages/jobs/JobListPage.tsx`
- `web/src/pages/jobs/JobDetailPage.tsx`
- `web/src/components/jobs/JobTable.tsx`
- `web/src/components/jobs/JobControls.tsx`
- `web/src/components/jobs/JobProgress.tsx`
- existing tests under `tests/api/routers/ui/`, `tests/services/`, and `web/src/**/__tests__` or adjacent `*.test.tsx` files related to jobs

### Required for Task 3

- `api/routers/ui/system.py`
- `src/services/system_run_trace_service.py`
- `src/services/system_service.py`
- `src/services/system_rollout_service.py`
- `src/services/system_cost_control_service.py`
- `web/src/lib/api/system.ts`
- tests covering `/api/ui/v1/system/runs` and `SystemRunsPage`

If any file above has moved, find the current equivalent before implementing. Do not continue using stale assumptions if route ownership, API shape, or page ownership has changed.

---

## Documentation Update Requirements

The implementation must update documentation when behavior changes. This is part of acceptance, not optional cleanup.

At minimum, update or create documentation for:

1. **System navigation and user-facing page ownership**
   - Record that `/system/jobs` is the formal Job Management entry.
   - Record that `/system/runs` is Runs & Alerts, not a Job control page.
   - Record that `/jobs` and `/jobs/:jobId` are compatibility redirects to `/system/jobs` paths.

2. **Page layout matrix**
   - Record which pages use workflow, overview, management, detail, or library layout.
   - Record which pages intentionally hide `Input`, `Processing Status`, or `Output` sections.

3. **Job lifecycle and control semantics**
   - Record which job types support create, pause, resume, cancel, and retry.
   - Record which job types intentionally do not support a control action and why.
   - Record the expected progress fields and user-facing progress meaning.

4. **Runs & Alerts semantics**
   - Record default view behavior, pagination/load-more behavior, filter semantics, and operator-only diagnostics.
   - Record how `partial`, `degraded`, `unavailable`, and `error` should be explained to users.

5. **Implementation logs**
   - Update the relevant stage implementation log after each task with: changed files, test commands/results, known residual risks, and any escalation decisions.

Recommended documentation targets:

- this document, if the final design differs from the plan;
- `docs/refactor-implementation-logs/stage-12.md` or the active implementation log;
- user/admin documentation if a user-facing manual exists for system management;
- any route/navigation matrix or page ownership document currently used by the project.

---

# Task 1 — System Page Information Architecture and Page Shell Foundation

## Goal

Create the UI foundation that allows pages to use the right layout instead of always showing `Input / Processing Status / Output`. This task should also create/update the page matrix that guides which pages are workflow pages and which are overview, management, detail, or library pages.

## Scope

### Required implementation

1. Introduce one of the following approaches:

   Preferred:

   ```ts
   type PageLayoutMode = 'workflow' | 'overview' | 'management' | 'detail' | 'library';
   ```

   Minimum acceptable:

   ```ts
   showInputSection?: boolean;
   showProcessingSection?: boolean;
   showOutputSection?: boolean;
   ```

2. Keep backward compatibility for existing pages during rollout.

   Existing pages should continue to render unless explicitly changed.

3. Define a page matrix in documentation or code comments covering at least:

   - `/system/status`
   - `/system/configuration`
   - `/system/data`
   - `/system/jobs`
   - `/system/runs`
   - `/research/articles`
   - `/research/add`
   - `/research/results`
   - `/rules/review`
   - `/rules/library`
   - `/rules/backtests`
   - `/rules/results`
   - `/authors`
   - `/daily/overview`
   - `/daily/pre-market`
   - `/daily/after-close`
   - `/strategies`

4. Start with conservative migration:

   Keep full workflow layout for pages that truly create/process data.

   Suggested full workflow pages:

   - add/import article
   - article processing/re-run
   - data repair/fetch/backfill actions
   - create backtest
   - generate pre-market plan
   - generate after-close review

   Suggested non-workflow pages:

   - system status
   - configuration overview/list
   - job management
   - runs and alerts
   - article library
   - rules library
   - authors
   - results/read-only views

5. Do not remove state handling.

   Even if `Processing Status` is removed visually from a page, the page must still handle loading, empty, partial, degraded, unavailable, error, invalid, conflict, and permission states clearly.

## Non-goals

- Do not rewrite every page in this task.
- Do not redesign `/system/runs` completely in this task.
- Do not implement job management in this task.

## Documentation updates

- Update the page layout matrix.
- Update any page-shell usage documentation or tests that previously assumed all product pages show `Input / Processing Status / Output`.
- Update the active implementation log with the migration approach and affected pages.

## Page Layout Matrix

Task 1 uses a conservative rollout rule:

- `workflow` remains the default layout for backward compatibility.
- Pages only switch to non-workflow layouts when the page shell contract is explicitly migrated.
- Hiding a workflow section must not remove truthful `loading` / `empty` / `partial` / `degraded` / `unavailable` / `error` / `invalid` / `conflict` / `permission_denied` messaging.

| Path | Target layout | Task 1 state | Notes |
| --- | --- | --- | --- |
| `/system/status` | `overview` | migrated | Hide workflow-only `Input` / `Processing Status`; keep availability messaging visible. |
| `/system/configuration` | `management` | migrated | Read-only config summary does not need workflow framing. |
| `/system/data` | `workflow` | unchanged | Still centers on repair, backfill, and recompute actions. |
| `/system/jobs` | `management` | deferred | Reserved for Task 2; not implemented in Task 1. |
| `/system/runs` | `detail` | deferred | Current shell stays workflow-shaped until the bounded Task 3 redesign. |
| `/research/articles` | `library` | deferred | Matrix defined now; shell migration can happen later without breaking current pages. |
| `/research/add` | `workflow` | migrated | Explicitly pinned to workflow layout to prove default-compatible migration. |
| `/research/results` | `detail` | deferred | Current shell remains workflow-compatible. |
| `/rules/review` | `workflow` | unchanged | Review flow still needs input, status, and output framing. |
| `/rules/library` | `library` | deferred | Matrix defined now; current page remains backward-compatible. |
| `/rules/backtests` | `workflow` | unchanged | Creating and rerunning backtests remains workflow-oriented. |
| `/rules/results` | `detail` | deferred | Current shell remains workflow-compatible. |
| `/authors` | `library` | migrated | Read-only version library hides meaningless workflow sections. |
| `/daily/overview` | `overview` | deferred | Current shell remains workflow-compatible in Task 1. |
| `/daily/pre-market` | `workflow` | unchanged | Generation flow remains workflow-oriented. |
| `/daily/after-close` | `workflow` | unchanged | Review generation flow remains workflow-oriented. |
| `/strategies` | `management` | deferred | Current shell remains workflow-compatible in Task 1. |

## Validation

Required checks:

- Typecheck and lint for frontend.
- Unit tests for `BusinessPageShell` / `ProductPageAdapter` layout behavior.
- Snapshot or DOM tests proving hidden sections are not rendered when disabled.
- Existing product page state matrix tests updated or replaced so they validate the intended layout mode instead of assuming all pages have `Input / Processing / Output`.
- Verify at least one workflow page still shows all three sections.
- Verify at least one management/list page no longer shows meaningless `Input / Processing / Output` sections.

## Acceptance criteria

- Page layout is configurable.
- Existing pages do not break.
- Non-workflow pages can remove noisy sections.
- Future pages have a clear matrix to choose the correct layout.

---

# Task 2 — Formal Job Management Dual Entry and Lifecycle Validation

## Goal

Make Job Management a formal system feature. Users should be able to start jobs through business pages, while operators/admins can manage all jobs centrally under `/system/jobs`.

## Scope

### Required routes

Add formal routes:

```text
/system/jobs
/system/jobs/:jobId
/system/jobs/new
```

Update compatibility routes:

```text
/jobs        -> /system/jobs
/jobs/:jobId -> /system/jobs/:jobId
```

Do not redirect `/jobs` to `/system/runs` after this task.

### Required UI behavior

`/system/jobs` must provide:

- current jobs;
- historical jobs;
- filters by status, job type, and creator;
- pagination or load-more;
- status counts;
- job progress;
- refresh and auto-refresh for `pending` / `running` jobs;
- pause, resume, cancel, retry controls where supported;
- clear disabled/permission state for non-operators;
- readable job type labels instead of raw-only internal names;
- safe display of Job ID, with full ID available through copy/detail rather than dominating the table.

`/system/jobs/:jobId` must provide:

- job status and metadata;
- progress;
- logs;
- timeline;
- artifacts;
- error details;
- pause/resume/cancel/retry where supported;
- back link to `/system/jobs`.

`/system/jobs/new` must provide an operator/admin advanced job creation flow:

```text
select job type -> show validated parameters -> confirm -> create job -> navigate to detail
```

High-risk jobs must require confirmation. Normal users should not be forced to use this internal creation flow.

### Dual entry design

Business pages should create jobs using user-facing actions, not raw job JSON.

Examples:

| Business area | User-facing action | Result |
|---|---|---|
| Research | process/reprocess articles | creates article processing job |
| Data & Scheduling | fetch OHLCV / fetch Kaipan / repair data | creates data operation job |
| Rules & Backtests | run backtest | creates backtest job |
| Daily Pre-market | generate plan | creates pre-market job |
| Daily After-close | generate review | creates after-close job |

After job creation, show either:

- a link to `/system/jobs/:jobId`; or
- a toast/status card saying the job was created and can be monitored in Job Management.

### Backend/worker requirements

This task must verify behavior beyond API existence:

- `pause` must not only update a database field; workers must respect pause points where the job definition claims pause support.
- `cancel` must stop further work at supported cancellation points.
- `resume` must continue paused jobs from a safe checkpoint.
- `retry` must respect retry limits and not corrupt previous artifacts.
- progress must be monotonic enough for users to trust it: `current`, `total`, `percent`, `status`, `updated_at`, and any sub-progress should remain consistent.

If some job type cannot support pause/resume/cancel safely, its definition must say so and the UI must not show unsupported controls.

### Suggested test helper

If real jobs are too heavy for lifecycle testing, add a test-only or diagnostic job definition that can:

- run for several steps;
- update progress;
- pause at checkpoints;
- resume;
- cancel;
- fail intentionally;
- retry successfully.

This must be guarded so it is not exposed as a normal production job unless explicitly enabled.

## Non-goals

- Do not move `/system/runs` responsibilities into `/system/jobs`.
- Do not expose raw internal JSON to normal users.
- Do not pretend unsupported job controls are available.

## Documentation updates

- Update route/navigation documentation to make `/system/jobs` the formal Job Management entry.
- Update job lifecycle/control documentation with supported and unsupported actions per job type.
- Update business page documentation where user-facing actions now create jobs.
- Update the active implementation log with worker lifecycle test evidence and any unsupported job controls.

## Validation

Backend tests:

- list job definitions;
- validate job submissions;
- create job;
- list with status/job_type/created_by filters;
- paginate with skip/limit;
- read detail/logs/timeline/artifacts;
- pause pending/running job where supported;
- resume paused job where supported;
- cancel pending/running/paused job where supported;
- retry failed job where supported;
- enforce operator/admin requirements for mutating actions;
- verify unsupported controls are rejected or hidden according to definition;
- verify idempotency key does not create duplicates.

Frontend tests:

- `/system/jobs` renders for viewer+ roles;
- viewer can view but cannot operate;
- operator can operate;
- `/jobs` redirects to `/system/jobs`;
- `/jobs/:jobId` redirects to `/system/jobs/:jobId`;
- filters update query parameters and data;
- pagination works;
- auto-refresh runs for pending/running jobs;
- progress bar and labels render correctly;
- controls match status and job definition flags;
- action success invalidates/refetches job data;
- job detail displays logs, timeline, artifacts, and errors.

E2E/lifecycle gate:

Run at least one actual worker-backed lifecycle test:

```text
create job -> observe pending/running -> progress updates -> pause -> resume -> cancel or success -> failed retry path where applicable
```

Document any job types that cannot be fully lifecycle-tested and why.

## Acceptance criteria

- `/system/jobs` is the formal job management entry.
- `/system/runs` is no longer the accidental replacement for job management.
- Users can start jobs from business pages without raw job JSON.
- Operators/admins can create advanced jobs and manage all jobs centrally.
- Progress and lifecycle controls are tested with at least one real worker-backed flow.

---

# Task 3 — Runs & Alerts Cleanup, Pagination, and Page Simplification Rollout

## Goal

Turn `/system/runs` into a user-readable Runs & Alerts overview and complete the cleanup of noisy non-workflow page sections using the foundation from Task 1.

## Scope

### `/system/runs` target behavior

`/system/runs` should answer four user questions first:

1. Is the system OK right now?
2. What needs attention?
3. What is affected?
4. What should I do next?

Default view should not expose technical IDs, fingerprints, raw metadata, or E2E/repair labels.

### Required page structure

Recommended structure:

```text
1. Top summary, no pagination
   - overall state
   - needs attention count
   - blocking count
   - ready count
   - latest failure or warning

2. Needs attention, capped list
   - show the top 3-5 actionable items
   - each item includes impact and next action
   - link to filtered history for more

3. Historical run groups, paginated or load-more
   - default 20 groups per page/load
   - grouped by trade date / strategy version / business chain where possible
   - each group summarizes related traces

4. Technical details, collapsed
   - operator/admin only by default
   - input/output references
   - data fetches
   - prompt calls
   - backtests
   - fingerprints
   - raw diagnostics
```

### Pagination/filtering requirement

Historical runs must support pagination or load-more. Recommended API shape:

```text
GET /api/ui/v1/system/runs?mode=overview&status=&type=&date_from=&date_to=&limit=20&cursor=
```

Minimum acceptable API shape:

```text
GET /api/ui/v1/system/runs?status=&type=&date_from=&date_to=&skip=0&limit=20
```

The page should support filters for at least:

- status: all / needs attention / failed / partial / ready;
- business type: all / data / prompt / backtest / pre-market / after-close / daily-rule-selection / trading-plan / system-job;
- date range if practical.

### Content cleanup rules

Default user view should hide or translate:

- UUIDs;
- fingerprints;
- raw `dataset_snapshot_id` / `market_snapshot_id` labels;
- `rt-s12-*` test labels;
- `local_*_repair` provider names;
- raw metadata payloads.

Operator/admin detail can still expose them in a collapsed diagnostic panel.

`partial` must always explain:

- why it is partial;
- whether it blocks the user;
- what is safe to continue;
- what next action is available.

### Page simplification rollout

Using the Task 1 shell foundation, migrate the highest-noise pages away from meaningless `Input / Processing / Output` sections.

Priority pages:

- `/system/runs`
- `/system/jobs`
- `/system/status`
- `/system/configuration`
- `/research/articles`
- `/rules/library`
- `/rules/results`
- `/authors`

Do not remove workflow sections from pages that actually execute workflows unless the page is redesigned with an equivalent status/action model.

## Non-goals

- Do not remove the underlying traceability data.
- Do not delete diagnostics required for audit/reproducibility.
- Do not make `/system/runs` a second job control page.
- Do not hide real failures just to make the page look clean.

## Documentation updates

- Update Runs & Alerts documentation with summary, needs-attention, history pagination/load-more, filters, and diagnostic visibility semantics.
- Update user/admin documentation if `/system/runs` or `/system/jobs` behavior is described there.
- Update the active implementation log with API changes, migration choices, test results, and any residual risks.
- Update this plan if the final API shape differs materially from the recommended or minimum acceptable API shape.

## Validation

Backend/API tests:

- overview summary returns stable counts;
- needs-attention items are capped and actionable;
- pagination/load-more returns deterministic ordering;
- filters work;
- operator/admin payload includes diagnostics;
- viewer payload does not expose raw diagnostics by default;
- `partial` items contain user-readable reason, impact, and next action.

Frontend tests:

- top summary renders without long technical text;
- needs-attention section renders top items and links to filtered history;
- history supports pagination/load-more;
- filters update API calls;
- technical details are collapsed by default;
- viewer cannot see raw diagnostics by default;
- operator/admin can expand diagnostics;
- `rt-s12-*`, raw fingerprints, and raw UUID-heavy blocks are not shown in the default view;
- migrated pages no longer show meaningless `Input / Processing / Output` sections.

E2E/user flow tests:

- open `/system/runs` and confirm the user can identify current status and next action without expanding diagnostics;
- create or use a partial/degraded run and confirm the page explains impact and remediation;
- navigate from `/system/runs` next action to the appropriate business page or `/system/data`;
- verify `/system/jobs` remains the place for job controls.

## Acceptance criteria

- `/system/runs` is readable as a business status and alert page.
- Historical records are paginated or load-more capable.
- Technical details remain available but no longer dominate the default view.
- Non-workflow pages are visually cleaner and no longer show irrelevant sections.
- Job control remains clearly separated in `/system/jobs`.

---

## Recommended Execution Order

1. Task 1 — Foundation and page matrix.
2. Task 2 — Formal Job Management and lifecycle validation.
3. Task 3 — Runs cleanup, pagination, and page simplification rollout.

This order is recommended because Task 1 reduces layout risk, Task 2 restores the missing user-required Job Management feature, and Task 3 can then clean `/system/runs` without needing to carry job control responsibilities.

---

## Global Verification Gate

After all tasks complete, run or verify:

### Frontend

- Typecheck.
- Lint.
- Unit/component tests for layout modes and page shell behavior.
- Route tests for `/system/jobs`, `/system/runs`, and legacy redirects.
- Job table/detail/progress/control tests.
- Runs overview/filter/pagination tests.

### Backend

- Job API tests.
- Job service lifecycle tests.
- Worker pause/resume/cancel/retry behavior tests.
- System runs overview API tests.
- Permission tests for viewer/operator/admin.

### E2E / realistic flow

At least one small worker-backed lifecycle flow must be executed:

```text
business page creates job -> job appears in /system/jobs -> progress updates -> control action works -> final state is visible -> /system/runs shows business result/alert without raw technical noise
```

### Regression checks

- Existing business pages still work.
- Existing `/api/ui/v1/jobs` clients still work.
- Existing `/api/ui/v1/system/runs` traceability is not silently removed.
- `/jobs` and `/jobs/:jobId` compatibility links resolve to the new formal Job Management paths.
- Technical diagnostics remain available to operator/admin.

---

## Model Recommendation

Use a stronger parent model for Task 1 planning and Task 2 lifecycle review because Job lifecycle and worker behavior are correctness-sensitive.

Suggested split:

- Task 1: Parent 5.4 is acceptable; use 5.5 if changing the shell contract deeply.
- Task 2: Parent 5.5 recommended for planning/review; implementation can use 5.4 if the scope stays bounded and tests are strong.
- Task 3: Parent 5.4 is acceptable for UI cleanup; use 5.5 for review if API aggregation/pagination semantics become complex.

Each implementation task should include a review-and-fix loop: re-read the diff, run the affected tests, fix failures, and repeat until the task meets its acceptance criteria or explicitly reports an escalation reason.
