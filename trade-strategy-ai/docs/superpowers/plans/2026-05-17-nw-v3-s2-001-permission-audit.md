# NW-V3-S2-001 Permission / Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Web-first permission and audit closed loop that lets admins query job audit history, inspect high-risk confirmations, and trace results without adding new CLI entry points.

**Architecture:** Reuse the existing `Job`, `JobAuditEvent`, `JobService`, and `StepTimelineService` facts as the single source of truth. Add a read-only audit query service and a dedicated UI workspace that stays visually aligned with the existing light, formal workbench pages. Keep writes in the current Job submission paths; only thread extra confirmation metadata into audit records and expose it through the new audit view.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, React, TanStack Query, existing shared UI kit (`PageHeader`, `SectionCard`, `LoadingState`, `ErrorState`, `EmptyState`, `StatusBadge`)

---

### Task 1: Add the canonical audit query API

**Files:**
- Create: `src/services/job_audit_query_service.py`
- Create: `api/routers/ui/job_audit.py`
- Modify: `api/routers/ui/__init__.py`
- Modify: `api/app.py`
- Create: `tests/unit/services/test_job_audit_query_service.py`
- Create: `tests/api/routers/test_job_audit.py`
- Modify: `tests/api/test_ui_openapi_contract.py`
- Modify: `tests/api/test_api_app_factory.py`

- [ ] **Step 1: Write the failing test**

```python
def test_job_audit_query_filters_by_actor_job_type_operation_and_date():
    service = JobAuditQueryService(session_scope_factory=_session_scope_factory)
    result = asyncio.run(service.list_events(actor="web", job_type="candidate-review", operation="create", date_from="2026-05-17", date_to="2026-05-17"))
    assert result.status == "ok"
    assert result.payload["items"][0]["job_type"] == "candidate-review"
    assert result.payload["items"][0]["confirmed"] is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/services/test_job_audit_query_service.py tests/api/routers/test_job_audit.py -q`
Expected: fail because the service and router do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement a read-only service that joins `JobAuditEvent` with `Job` and returns a flattened audit event list with these fields:
- `job_id`
- `job_type`
- `operation`
- `actor`
- `source`
- `confirmed`
- `event_at`
- `params_summary`
- `payload`
- `status`
- `artifact_count`
- `job_detail_url`

Add a router at `/api/ui/v1/job-audits` with:
- `GET /job-audits`
- `GET /job-audits/{job_id}`

Keep secrets masked by reusing the existing audit sanitization path from `JobService`.
Protect the router with `require_role("admin")` so only admins can view audit history.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/unit/services/test_job_audit_query_service.py tests/api/routers/test_job_audit.py tests/api/test_ui_openapi_contract.py tests/api/test_api_app_factory.py -q`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/job_audit_query_service.py api/routers/ui/job_audit.py api/routers/ui/__init__.py api/app.py tests/unit/services/test_job_audit_query_service.py tests/api/routers/test_job_audit.py tests/api/test_ui_openapi_contract.py tests/api/test_api_app_factory.py
git commit -m "feat(audit): add canonical job audit query api"
```

### Task 2: Thread confirmation metadata into audit records

**Files:**
- Modify: `src/services/job_service.py`
- Modify: `api/routers/ui/jobs.py`
- Modify: `api/routers/ui/pipelines.py`
- Modify: `api/routers/ui/workflows.py`
- Modify: `tests/api/routers/test_jobs_api.py`
- Modify: `tests/api/routers/test_pipelines.py`
- Modify: `tests/api/routers/test_workflows.py`
- Modify: `tests/unit/services/test_job_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_create_job_records_confirmed_flag_in_audit_context():
    result = asyncio.run(job_service.create_job(job_type="candidate-review", params={"candidate_version_id": "candidate-1"}, created_by="web", confirmed=True))
    audit_payload = result.payload["job"]["audit_events"][0]["payload"]
    assert audit_payload["request_context"]["confirmed"] is True
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit/services/test_job_service.py tests/api/routers/test_jobs_api.py -q`
Expected: fail because `confirmed` is not yet stored in audit payloads.

- [ ] **Step 3: Write the minimal implementation**

Update `JobService.create_job` to accept `confirmed: bool = False` and include it in the `create` audit event payload under `request_context.confirmed`.
Pass the request flag through:
- `api/routers/ui/jobs.py`
- `api/routers/ui/pipelines.py`
- `api/routers/ui/workflows.py`

Do not add a second confirmation mechanism; keep this as metadata only.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/unit/services/test_job_service.py tests/api/routers/test_jobs_api.py tests/api/routers/test_pipelines.py tests/api/routers/test_workflows.py -q`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/services/job_service.py api/routers/ui/jobs.py api/routers/ui/pipelines.py api/routers/ui/workflows.py tests/unit/services/test_job_service.py tests/api/routers/test_jobs_api.py
git commit -m "fix(audit): record confirmation metadata in job audits"
```

### Task 3: Build the light audit workspace UI

**Files:**
- Create: `web/src/types/job-audit.ts`
- Create: `web/src/lib/api/job-audit.ts`
- Create: `web/src/lib/api/job-audit.test.ts`
- Create: `web/src/features/audit/index.ts`
- Create: `web/src/features/audit/audit-center.tsx`
- Create: `web/src/pages/audit/index.tsx`
- Modify: `web/src/app/navigation.ts`
- Modify: `web/src/app/route-registry.ts`
- Create: `web/src/features/audit/audit-center.test.tsx`
- Create: `web/src/pages/audit/index.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
it('renders a light audit workspace with filters and detail panel', async () => {
  expect(await screen.findByRole('heading', { name: '权限与审计中心' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '刷新' })).toBeInTheDocument();
  expect(screen.getByLabelText('操作类型')).toBeInTheDocument();
  expect(screen.getByText('高风险操作')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `web/`: `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/features/audit/audit-center.test.tsx src/pages/audit/index.test.tsx src/lib/api/job-audit.test.ts`
Expected: fail because the page and client do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create a formal, light-themed workspace that stays consistent with `UI-V2-002` / `UI-V3-001`:
- white cards
- pale gray borders
- `PageHeader` at the top
- filter row for `actor`, `job_type`, `operation`, `date_from`, `date_to`, `confirmed`
- summary cards for total events, high-risk events, permission-denied events, confirmed events
- event list with a detail panel
- links to the source Job detail and related artifacts
- empty / loading / error / retry / permission-denied states

The page must not expose secrets and must not mimic a dark console.

- [ ] **Step 4: Run the test to verify it passes**

Run from `web/`: `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/features/audit/audit-center.test.tsx src/pages/audit/index.test.tsx src/lib/api/job-audit.test.ts src/app/navigation.test.ts src/app/route-registry.test.ts`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/types/job-audit.ts web/src/lib/api/job-audit.ts web/src/lib/api/job-audit.test.ts web/src/features/audit/index.ts web/src/features/audit/audit-center.tsx web/src/features/audit/audit-center.test.tsx web/src/pages/audit/index.tsx web/src/pages/audit/index.test.tsx web/src/app/navigation.ts web/src/app/route-registry.ts
git commit -m "feat(audit-ui): add permission and audit workspace"
```

### Task 4: Verify, review, and close the workstream

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-17.md`
- Modify: `daily-report/2026-05-17.md`

- [ ] **Step 1: Run the full relevant test set**

Run:
`python -m pytest tests/unit/services/test_job_audit_query_service.py tests/unit/services/test_job_service.py tests/unit/services/test_job_runner.py tests/unit/services/test_job_registry.py tests/api/routers/test_job_audit.py tests/api/routers/test_jobs_api.py tests/api/routers/test_pipelines.py tests/api/routers/test_workflows.py -q`

Run from `web/`:
`/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/features/audit/audit-center.test.tsx src/pages/audit/index.test.tsx src/lib/api/job-audit.test.ts src/app/navigation.test.ts src/app/route-registry.test.ts`

Expected: all pass.

- [ ] **Step 2: Review against the TaskList acceptance criteria**

Confirm the implementation satisfies:
- audit event list
- filter by actor/job_type/operation/date
- high-risk actions
- permission denied logs
- job audit detail
- no secret exposure
- no frontend permission bypass
- light, formal UI style consistent with existing pages

- [ ] **Step 3: Update TaskList and daily notes**

Mark `NW-V3-S2-001` and `UI-V3-007` complete only after the review passes.
Update the same-day `daily-sessions` and `daily-report` with the new resume point.

- [ ] **Step 4: Commit the final state**

```bash
git add docs/New-Web-Linked-TaskLists/New-Web-TaskList.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-17.md daily-report/2026-05-17.md
git commit -m "docs(audit): close permission and audit workstream"
```
