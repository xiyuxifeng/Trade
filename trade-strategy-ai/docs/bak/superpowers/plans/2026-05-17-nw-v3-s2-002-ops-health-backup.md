# NW-V3-S2-002 / UI-V3-004-005-006 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the V3 ops / health / backup-recovery Web flow as shallow, formal, light-themed pages that let admins inspect system health, recover stale jobs, manage backups, and review audit history without adding CLI-centric demo paths.

**Architecture:** Reuse existing read models and job/backup services wherever possible. Add one small admin recovery action for stale jobs, one read-only audit history query for backup/restore events, and keep the UI as three separate light workspaces that share the same page language as the earlier V3 formal pages. Avoid new console-style shells or shell-command execution paths.

**Tech Stack:** FastAPI, SQLAlchemy async session, React, TanStack Query, existing `Card/SectionCard/PageHeader/EmptyState/ErrorState/LoadingState` UI primitives, Vitest, Pytest.

---

### Task 1: Add stale-job recovery action and audit-history query backend

**Files:**
- Modify: `src/services/job_service.py`
- Modify: `src/services/ops_service.py`
- Create: `src/services/data_audit_query_service.py`
- Create: `api/routers/ui/data_audits.py`
- Modify: `api/routers/ui/ops.py`
- Modify: `api/routers/ui/__init__.py`
- Modify: `api/app.py`
- Modify: `src/services/__init__.py`
- Test: `tests/unit/services/test_job_service.py`
- Test: `tests/unit/services/test_ops_service.py`
- Test: `tests/unit/services/test_data_audit_query_service.py`
- Test: `tests/api/routers/test_ops.py`
- Test: `tests/api/routers/test_data_audits.py`
- Test: `tests/api/test_ui_openapi_contract.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_recover_stale_jobs_records_audit_event(...):
    ...
    result = await service.recover_stale_jobs(stale_before=..., audit_source={"channel": "ui", "path": "/api/ui/v1/ops/recover-stale"})
    assert result.status == "ok"
    assert result.payload["job_ids"] == [job_id]
    loaded = await service.get_job(job_id)
    assert loaded.payload["job"]["audit_events"][-1]["operation"] == "stale_recovery"
```

```python
async def test_list_data_audits_returns_backup_and_restore_history(...):
    ...
    result = await service.list_data_audits(event_types=["backup_project_state", "restore_project_state"])
    assert result.payload["summary"]["total"] == 2
    assert result.payload["items"][0]["event_type"] in {"backup_project_state", "restore_project_state"}
```

```python
async def test_ops_router_recover_stale_jobs(...):
    ...
    response = await client.post("/api/ui/v1/ops/recover-stale", json={"stale_before_minutes": 15})
    assert response.status_code == 200
    assert response.json()["count"] == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
python -m pytest tests/unit/services/test_job_service.py tests/unit/services/test_ops_service.py tests/unit/services/test_data_audit_query_service.py tests/api/routers/test_ops.py tests/api/routers/test_data_audits.py tests/api/test_ui_openapi_contract.py -q
```

Expected: fail because the new recovery/audit endpoints and audit query service do not exist yet, or stale recovery does not write audit events.

- [ ] **Step 3: Write minimal implementation**

```python
async def recover_stale_jobs(self, *, stale_before: datetime, audit_source: dict[str, Any] | None = None) -> ServiceResult:
    ...
    await self._record_job_audit(
        session=session,
        job=job,
        operation="stale_recovery",
        actor=(audit_source or {}).get("actor") or job.created_by,
        audit_source=audit_source,
        params_summary=job.params,
        payload={"stale_before": stale_before.isoformat(), "retry_count": job.retry_count},
        event_at=datetime.now(UTC),
    )
```

```python
@router.post("/recover-stale")
async def recover_stale_jobs(...):
    ...
    result = await service.recover_stale_jobs(stale_before_minutes=request.stale_before_minutes, audit_source=_audit_source_from_request(http_request))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
python -m pytest tests/unit/services/test_job_service.py tests/unit/services/test_ops_service.py tests/unit/services/test_data_audit_query_service.py tests/api/routers/test_ops.py tests/api/routers/test_data_audits.py tests/api/test_ui_openapi_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/job_service.py src/services/ops_service.py src/services/data_audit_query_service.py api/routers/ui/data_audits.py api/routers/ui/ops.py api/routers/ui/__init__.py api/app.py src/services/__init__.py tests/unit/services/test_job_service.py tests/unit/services/test_ops_service.py tests/unit/services/test_data_audit_query_service.py tests/api/routers/test_ops.py tests/api/routers/test_data_audits.py tests/api/test_ui_openapi_contract.py
git commit -m "feat(ops): add stale recovery and audit history"
```

### Task 2: Rework Admin Ops Console into a light formal workspace

**Files:**
- Modify: `web/src/features/ops/recovery-center.tsx`
- Modify: `web/src/pages/ops/index.tsx`
- Modify: `web/src/pages/ops/index.test.tsx`
- Modify: `web/src/lib/api/ops.ts`
- Modify: `web/src/lib/api/ops.test.ts`
- Create: `web/src/lib/api/data-audits.ts`
- Create: `web/src/lib/api/data-audits.test.ts`
- Create: `web/src/types/data-audits.ts`

- [ ] **Step 1: Write the failing tests**

```tsx
it('shows stale jobs, backup actions, and audit history in the formal admin ops workspace', async () => {
  ...
  expect(await screen.findByRole('heading', { name: '管理运维' })).toBeInTheDocument();
  expect(await screen.findByText('stale job recovery')).toBeInTheDocument();
  expect(await screen.findByText('备份 / 恢复审计')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/pages/ops/index.test.tsx src/lib/api/ops.test.ts src/lib/api/data-audits.test.ts
```

Expected: fail because the new light workspace and data audit client do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```tsx
<PageHeader kicker="配置与管理" title="管理运维" description="查看系统状态、恢复 stale job、管理备份，并查看最近审计记录。" />
```

```tsx
<SectionCard title="stale job recovery" ...>
  ...
  <Button onClick={() => recoverStaleJobsMutation.mutate({ stale_before_minutes: 10 })}>Recover stale jobs</Button>
</SectionCard>
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/pages/ops/index.test.tsx src/lib/api/ops.test.ts src/lib/api/data-audits.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/ops/recovery-center.tsx web/src/pages/ops/index.tsx web/src/pages/ops/index.test.tsx web/src/lib/api/ops.ts web/src/lib/api/ops.test.ts web/src/lib/api/data-audits.ts web/src/lib/api/data-audits.test.ts web/src/types/data-audits.ts
git commit -m "feat(ui): refresh admin ops console"
```

### Task 3: Rework Health Check Dashboard into a light formal workspace

**Files:**
- Modify: `web/src/pages/data-health/index.tsx`
- Modify: `web/src/features/data-health/operational-dashboard-center.tsx`
- Modify: `web/src/features/data-health/data-health-center.tsx`
- Modify: `web/src/pages/data-health/index.test.tsx`
- Modify: `web/src/lib/api/system.ts`
- Modify: `web/src/lib/api/dataHealth.ts`
- Modify: `web/src/lib/api/dataHealth.test.ts`
- Modify: `web/src/types/system.ts`
- Modify: `web/src/types/dataHealth.ts`

- [ ] **Step 1: Write the failing tests**

```tsx
it('renders a light health workspace with api/db/worker/storage summaries', async () => {
  ...
  expect(await screen.findByRole('heading', { name: '运维仪表盘' })).toBeInTheDocument();
  expect(await screen.findByText('API status')).toBeInTheDocument();
  expect(await screen.findByText('DB status')).toBeInTheDocument();
  expect(await screen.findByText('worker status')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/pages/data-health/index.test.tsx src/lib/api/dataHealth.test.ts
```

Expected: fail because the page still uses the old dark dashboard layout and missing summary blocks.

- [ ] **Step 3: Write minimal implementation**

```tsx
<PageHeader kicker="数据运维" title="运维仪表盘" description="系统可用性、数据新鲜度和健康校验状态。" />
```

```tsx
<section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
  <SummaryCard title="API status" value={status.database.status} />
  <SummaryCard title="DB status" value={status.database.status} />
  <SummaryCard title="worker status" value={dashboard.worker.status} />
  <SummaryCard title="storage status" value={status.directories['storage.output_dir'].exists ? 'ok' : 'missing'} />
</section>
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/pages/data-health/index.test.tsx src/lib/api/dataHealth.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/data-health/index.tsx web/src/features/data-health/operational-dashboard-center.tsx web/src/features/data-health/data-health-center.tsx web/src/pages/data-health/index.test.tsx web/src/lib/api/system.ts web/src/lib/api/dataHealth.ts web/src/lib/api/dataHealth.test.ts web/src/types/system.ts web/src/types/dataHealth.ts
git commit -m "feat(ui): refresh health dashboard"
```

### Task 4: Review, validate, and sync task lists

**Files:**
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `daily-sessions/2026-05-17.md`
- Modify: `daily-report/2026-05-17.md`

- [ ] **Step 1: Re-read the TaskList acceptance sections**

Confirm `NW-V3-S2-002`, `UI-V3-004`, `UI-V3-005`, `UI-V3-006`.

- [ ] **Step 2: Run the targeted regression suite**

Run:
```bash
python -m pytest tests/unit/services/test_job_service.py tests/unit/services/test_ops_service.py tests/unit/services/test_data_audit_query_service.py tests/api/routers/test_ops.py tests/api/routers/test_data_audits.py tests/api/test_ui_openapi_contract.py -q
cd web && /Users/wanghui/.nvm/versions/node/v18.20.8/bin/node ./node_modules/vitest/vitest.mjs run src/pages/ops/index.test.tsx src/pages/data-health/index.test.tsx src/lib/api/ops.test.ts src/lib/api/dataHealth.test.ts src/lib/api/data-audits.test.ts
git diff --check
```

- [ ] **Step 3: Review the implementation against the acceptance criteria**

Check that:
- ops page is light-themed and admin-only
- stale recovery is confirmed and audited
- health dashboard exposes the required status summaries
- backup/restore has confirmation and audit history
- no secrets are shown
- no CLI-only or shell execution paths were introduced

- [ ] **Step 4: Update session/report and mark tasks**

Mark only tasks that are truly complete in the TaskLists, then update `daily-sessions` and `daily-report` with the concrete verification results.

- [ ] **Step 5: Final commit**

```bash
git add docs/New-Web-Linked-TaskLists/New-Web-TaskList.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-17.md daily-report/2026-05-17.md
git commit -m "docs(v3): sync ops and health task progress"
```
