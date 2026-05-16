# Artifact Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the V2 formal Artifact Center as a cross-job artifact discovery and inspection page with safe preview, download, and source-job navigation.

**Architecture:** Keep `/artifacts` as the canonical UI entry and upgrade it into a formal working center that follows the same light dashboard language as `UI-V2-002`. The front end should remain a thin query-and-render layer over the UI BFF, while the back end extends the artifact query contract with `job_type` and date filtering derived from existing job metadata and `modified_at`, without exposing filesystem paths or duplicating job logic.

**Tech Stack:** React, React Router, React Query, FastAPI, SQLAlchemy, Vitest, pytest, Tailwind utility classes.

---

### Task 1: Extend the artifact query contract

**Files:**
- Modify: `trade-strategy-ai/api/routers/ui/artifacts.py`
- Modify: `trade-strategy-ai/src/services/artifact_service.py`
- Modify: `trade-strategy-ai/tests/api/routers/test_artifacts.py`
- Modify: `trade-strategy-ai/tests/api/test_ui_openapi_contract.py`

- [ ] **Step 1: Write the failing API tests**

Add a router test that expects `/api/ui/v1/artifacts` to accept `job_type` and `date` query parameters and pass them into the service layer.

```python
@pytest.mark.asyncio
async def test_list_artifacts_accepts_job_type_and_date(client: AsyncClient) -> None:
    response = await client.get("/api/ui/v1/artifacts?job_type=strategy-build&date=2026-05-16")
    assert response.status_code == 200
```

Add an OpenAPI contract assertion for the two new query parameters.

```python
params = paths["/api/ui/v1/artifacts"]["get"]["parameters"]
assert {param["name"] for param in params} >= {"job_type", "date"}
```

- [ ] **Step 2: Run the targeted tests and confirm they fail**

Run:

```bash
python -m pytest tests/api/routers/test_artifacts.py tests/api/test_ui_openapi_contract.py -q
```

Expected: fail because the router and service do not yet expose `job_type` and `date`.

- [ ] **Step 3: Implement the minimal contract support**

Add the new query parameters to the router and service signatures.

```python
@router.get("")
async def list_artifacts(
    kind: str | None = Query(default=None),
    source: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    date: str | None = Query(default=None),
    job_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    artifact_service: ArtifactService = Depends(get_artifact_service),
    _: str = Depends(verify_api_key),
) -> dict[str, Any]:
    result = await artifact_service.list_artifacts(
        kind=kind,
        source=source,
        job_type=job_type,
        date=date,
        job_id=job_id,
        q=q,
        skip=skip,
        limit=limit,
    )
```

Extend `ArtifactService.list_artifacts` to:

```python
async def list_artifacts(
    self,
    *,
    kind: str | None = None,
    source: str | None = None,
    job_type: str | None = None,
    date: str | None = None,
    job_id: str | None = None,
    q: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> ServiceResult:
```

Implement filtering by:

```python
if job_type is not None:
    records = [item for item in records if item.metadata.get("job_type") == job_type]
if date is not None:
    records = [item for item in records if item.modified_at and item.modified_at.startswith(date)]
```

Populate `metadata["job_type"]` from the job record when `job_id` is present, using the existing job service or a small read-only helper that reuses the current job ORM access pattern.

- [ ] **Step 4: Run the targeted tests and confirm they pass**

Run:

```bash
python -m pytest tests/api/routers/test_artifacts.py tests/api/test_ui_openapi_contract.py -q
```

Expected: pass with the new query contract.

---

### Task 2: Upgrade the Artifact Center page to the formal V2 layout

**Files:**
- Modify: `trade-strategy-ai/web/src/pages/artifacts/index.tsx`
- Modify: `trade-strategy-ai/web/src/lib/api/artifacts.ts`
- Modify: `trade-strategy-ai/web/src/types/artifacts.ts`
- Modify: `trade-strategy-ai/web/src/pages/artifacts/index.test.tsx`
- Create: `trade-strategy-ai/web/src/components/artifacts/artifact-center-hero.tsx`

- [ ] **Step 1: Write the failing UI tests**

Add a page test that expects the page to expose formal V2 filters and source-job navigation.

```tsx
expect(screen.getByText('产物中心')).toBeInTheDocument();
expect(screen.getByPlaceholderText('按 job type 过滤')).toBeInTheDocument();
expect(screen.getByPlaceholderText('按日期过滤')).toBeInTheDocument();
```

Add a test for the URL query sync.

```tsx
await user.selectOptions(screen.getByLabelText('Artifact kind'), 'json');
await waitFor(() => {
  expect(mockedListArtifacts).toHaveBeenLastCalledWith(
    expect.objectContaining({ kind: 'json' }),
  );
});
```

- [ ] **Step 2: Run the page test and confirm it fails**

Run:

```bash
pnpm vitest web/src/pages/artifacts/index.test.tsx
```

Expected: fail because the current page does not expose the formal V2 filters or the new source-job navigation contract.

- [ ] **Step 3: Implement the page upgrade**

Refactor the page into a light formal center with the same `UI-V2-002` surface language:

```tsx
<main className="page-stack">
  <PageHeader
    kicker="正式工作台"
    title="产物中心"
    description="跨 Job 检索、预览和下载正式产物。"
  />
```

Add filters for:

```tsx
<Input placeholder="搜索文本" ... />
<Input placeholder="按 job type 过滤" ... />
<Input placeholder="按日期过滤" ... />
<Select aria-label="Artifact kind" ... />
```

Render source-job navigation with a link that targets `/jobs/${artifact.job_id}` when available, and keep preview/download behavior via the UI BFF only.

Extend the API client/types so `listArtifacts` accepts `job_type` and `date`.

- [ ] **Step 4: Run the page test and confirm it passes**

Run:

```bash
pnpm vitest web/src/pages/artifacts/index.test.tsx
```

Expected: pass with the formal layout and filter interactions.

---

### Task 3: Align the artifact detail component and coverage

**Files:**
- Modify: `trade-strategy-ai/web/src/components/artifacts/artifact-panel.tsx`
- Modify: `trade-strategy-ai/web/src/components/artifacts/artifact-card.tsx`
- Modify: `trade-strategy-ai/web/src/components/artifacts/artifact-list.tsx`
- Modify: `trade-strategy-ai/web/src/components/artifacts/artifact-panel.test.tsx`
- Modify: `trade-strategy-ai/web/src/pages/jobs/JobDetailPage.tsx`

- [ ] **Step 1: Write the failing component tests**

Add assertions that the artifact cards expose source-job navigation and keep safe preview/download states.

```tsx
expect(screen.getByRole('link', { name: '查看来源 Job' })).toHaveAttribute('href', '/jobs/job-1');
expect(screen.getByText('该产物缺少安全下载入口，可能已丢失或尚未生成。')).toBeInTheDocument();
```

- [ ] **Step 2: Run the component tests and confirm they fail**

Run:

```bash
pnpm vitest web/src/components/artifacts/artifact-panel.test.tsx
```

Expected: fail until the source-job navigation and any related rendering updates are implemented.

- [ ] **Step 3: Implement the component refinements**

Keep the Job Detail artifact panel as a safe embedded view, but add a clear source-job link and preserve the existing preview sanitization.

```tsx
{artifact.job_id ? (
  <Link className="text-sky-700 hover:underline" to={`/jobs/${artifact.job_id}`}>
    查看来源 Job
  </Link>
) : null}
```

- [ ] **Step 4: Run the component tests and confirm they pass**

Run:

```bash
pnpm vitest web/src/components/artifacts/artifact-panel.test.tsx
```

Expected: pass with the new navigation affordance.

---

### Task 4: Sync task tracking and delivery records

**Files:**
- Modify: `trade-strategy-ai/docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md`
- Modify: `trade-strategy-ai/daily-sessions/2026-05-17.md`
- Modify: `trade-strategy-ai/daily-report/2026-05-17.md`

- [ ] **Step 1: Update the UI TaskList state**

Mark `UI-V2-007` only when the page, API contract, tests, and review all pass.

```md
### [x] UI-V2-007 P0 Artifact Center
```

- [ ] **Step 2: Update the daily session**

Record the implementation path, files, verification commands, and any residual risks in the `Resume Point` section.

- [ ] **Step 3: Update the daily report**

Summarize the final artifact center behavior, verification, and next recommended task.

- [ ] **Step 4: Commit**

Run:

```bash
git add api/routers/ui/artifacts.py src/services/artifact_service.py tests/api/routers/test_artifacts.py tests/api/test_ui_openapi_contract.py web/src/pages/artifacts/index.tsx web/src/lib/api/artifacts.ts web/src/types/artifacts.ts web/src/pages/artifacts/index.test.tsx web/src/components/artifacts/artifact-center-hero.tsx web/src/components/artifacts/artifact-panel.tsx web/src/components/artifacts/artifact-card.tsx web/src/components/artifacts/artifact-list.tsx web/src/components/artifacts/artifact-panel.test.tsx web/src/pages/jobs/JobDetailPage.tsx docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-17.md daily-report/2026-05-17.md
git commit -m "feat(ui): build artifact center v2"
```

