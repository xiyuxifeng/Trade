# WEB-S6-008C Kaipan and Data Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Web Kaipan operations and data health workbench for fetch, normalize, status, run, and dashboard reporting.

**Architecture:** Expose Kaipan and dashboard functionality through a dedicated UI BFF, then render two focused operational pages. Kaipan actions stay backend-controlled and are treated as long-running or high-risk operations. The data-health page is read-only and surfaces the dashboard report and HTML artifact safely.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, React, React Router, shadcn/ui, TanStack Query, Vitest, pytest

---

### Task 1: Add Kaipan and data-health UI BFF routes

**Files:**
- Create: `api/routers/ui/kaipan.py`
- Create: `api/routers/ui/data_health.py`
- Create: `web/src/features/kaipan/index.ts`
- Create: `web/src/features/data-health/index.ts`
- Modify: `api/routers/ui/__init__.py`
- Modify: `api/app.py`
- Test: `tests/api/routers/ui/test_kaipan.py`
- Test: `tests/api/routers/ui/test_data_health.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_kaipan_status_returns_latest_slot(client):
    response = await client.get("/api/ui/v1/kaipan/status")
    assert response.status_code == 200
    payload = response.json()
    assert "latest_slot" in payload
```

```python
async def test_kaipan_fetch_returns_payload(client):
    response = await client.post("/api/ui/v1/kaipan/fetch?slot=all")
    assert response.status_code == 200
    payload = response.json()
    assert "slot_results" in payload
```

```python
async def test_kaipan_normalize_returns_results(client):
    response = await client.post("/api/ui/v1/kaipan/normalize", json={"slot": "all"})
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
```

```python
async def test_kaipan_run_returns_payload(client):
    response = await client.post("/api/ui/v1/kaipan/run", json={"start_scheduler": False})
    assert response.status_code == 200
    payload = response.json()
    assert "started" in payload or "pre_market" in payload
```

```python
async def test_dashboard_returns_report(client):
    response = await client.get("/api/ui/v1/data-health/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert "report" in payload
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
PYTHONPATH=. pytest tests/api/routers/ui/test_kaipan.py tests/api/routers/ui/test_data_health.py -q
```
Expected: fail because the route modules do not exist yet.

For the final route tests, use `app.dependency_overrides` to inject `verify_api_key`, `get_kaipan_service`, and `get_dashboard_service` fakes so the tests stay isolated from scheduler, filesystem, and report generation side effects.

- [ ] **Step 3: Implement the minimal BFF routes**

```python
def _config_path() -> Path:
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


def get_kaipan_service() -> KaipanService:
    return KaipanService()


@router.post("/fetch", dependencies=[Depends(verify_api_key)])
async def fetch_kaipan(
    trade_date: str | None = None,
    slot: str = "all",
    service: KaipanService = Depends(get_kaipan_service),
):
    result = service.fetch(config_path=_config_path(), trade_date=trade_date, slot=slot)
    return result.payload
```

```python
@router.get("/status", dependencies=[Depends(verify_api_key)])
async def kaipan_status(service: KaipanService = Depends(get_kaipan_service)):
    result = service.status(config_path=_config_path())
    return result.payload
```

```python
@router.post("/normalize", dependencies=[Depends(verify_api_key)])
async def normalize_kaipan(
    request: KaipanNormalizeRequest,
    service: KaipanService = Depends(get_kaipan_service),
):
    result = service.normalize(config_path=_config_path(), trade_date=request.trade_date, slot=request.slot)
    return result.payload
```

```python
@router.post("/run", dependencies=[Depends(verify_api_key)])
async def run_kaipan(
    request: KaipanRunRequest,
    service: KaipanService = Depends(get_kaipan_service),
):
    result = service.run(config_path=_config_path(), start_scheduler=request.start_scheduler, block=request.block)
    return result.payload
```

```python
def get_dashboard_service() -> DashboardService:
    return DashboardService()


@router.get("/dashboard", dependencies=[Depends(verify_api_key)])
async def data_health_dashboard(service: DashboardService = Depends(get_dashboard_service)):
    result = await service.build_report(config_path=_config_path(), mode="html")
    return result.payload
```

- [ ] **Step 4: Run the tests again and make sure they pass**

Run:
```bash
PYTHONPATH=. pytest tests/api/routers/ui/test_kaipan.py tests/api/routers/ui/test_data_health.py -q
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add api/routers/ui/kaipan.py api/routers/ui/data_health.py api/routers/ui/__init__.py api/app.py tests/api/routers/ui/test_kaipan.py tests/api/routers/ui/test_data_health.py
git commit -m "feat(web-s6-008c): add operational ui bff routes"
```

### Task 2: Add Kaipan and dashboard frontend clients

**Files:**
- Create: `web/src/lib/api/kaipan.ts`
- Create: `web/src/lib/api/dataHealth.ts`
- Create: `web/src/types/kaipan.ts`
- Create: `web/src/types/dataHealth.ts`
- Test: `web/src/lib/api/kaipan.test.ts`
- Test: `web/src/lib/api/dataHealth.test.ts`

Define the Kaipan DTOs explicitly in `web/src/types/kaipan.ts`:
- `KaipanFetchRequest` / `KaipanFetchResponse` with `trade_date` and `slot`
- `KaipanStatusResponse`
- `KaipanNormalizeRequest` / `KaipanNormalizeResponse` with `trade_date` and `slot`
- `KaipanRunRequest` / `KaipanRunResponse` with `start_scheduler` and `block`

Define the dashboard DTOs explicitly in `web/src/types/dataHealth.ts`:
- `DashboardReportResponse`

- [ ] **Step 1: Write the failing tests**

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';
import { kaipanFetch, kaipanNormalize, kaipanRun, kaipanStatus } from './kaipan';

describe('kaipan api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('uses the versioned status endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ latest_slot: '2026-05-09_17-30' }),
    } as Response);

    await kaipanStatus();

    expect(fetch).toHaveBeenCalledWith(
      '/api/ui/v1/kaipan/status',
      expect.objectContaining({
        headers: expect.objectContaining({
          Accept: 'application/json',
          'X-API-Key': 'demo-key',
        }),
      }),
    );
  });

  it('posts the fetch request', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ slot_results: {} }),
    } as Response);

    await kaipanFetch({ slot: 'all' });

    expect(fetch).toHaveBeenCalledWith(
      '/api/ui/v1/kaipan/fetch?slot=all',
      expect.objectContaining({
        method: 'POST',
      }),
    );
  });

  it('posts normalize and run requests', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [] }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ started: false }),
      } as Response);

    await kaipanNormalize({ slot: 'all' });
    await kaipanRun({ start_scheduler: false });

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      '/api/ui/v1/kaipan/normalize',
      expect.objectContaining({
        method: 'POST',
      }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      '/api/ui/v1/kaipan/run',
      expect.objectContaining({
        method: 'POST',
      }),
    );
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pnpm test web/src/lib/api/kaipan.test.ts web/src/lib/api/dataHealth.test.ts
```
Expected: fail because the modules do not exist yet.

- [ ] **Step 3: Implement the minimal client helpers**

```ts
import { fetchJson } from './http';

export function kaipanFetch(params: KaipanFetchRequest) {
  const query = new URLSearchParams();
  if (params.trade_date) query.set('trade_date', params.trade_date);
  if (params.slot) query.set('slot', params.slot);
  const suffix = query.toString() ? `?${query.toString()}` : '';
  return fetchJson<KaipanFetchResponse>(`/kaipan/fetch${suffix}`, {
    method: 'POST',
  });
}

export function kaipanStatus() {
  return fetchJson<KaipanStatusResponse>('/kaipan/status');
}
```

```ts
export function kaipanNormalize(payload: KaipanNormalizeRequest) {
  return fetchJson<KaipanNormalizeResponse>('/kaipan/normalize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

```ts
export function kaipanRun(payload: KaipanRunRequest) {
  return fetchJson<KaipanRunResponse>('/kaipan/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

```ts
export function buildDashboardReport() {
  return fetchJson<DashboardReportResponse>('/data-health/dashboard');
}
```

- [ ] **Step 4: Run the tests again and make sure they pass**

Run:
```bash
pnpm test web/src/lib/api/kaipan.test.ts web/src/lib/api/dataHealth.test.ts
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api/kaipan.ts web/src/lib/api/dataHealth.ts web/src/types/kaipan.ts web/src/types/dataHealth.ts web/src/lib/api/kaipan.test.ts web/src/lib/api/dataHealth.test.ts
git commit -m "feat(web-s6-008c): add operations api clients"
```

### Task 3: Build the Kaipan and data-health pages

**Files:**
- Create: `web/src/features/kaipan/kaipan-center.tsx`
- Create: `web/src/features/data-health/data-health-center.tsx`
- Create: `web/src/pages/kaipan/index.tsx`
- Create: `web/src/pages/data-health/index.tsx`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/navigation.ts`
- Test: `web/src/pages/kaipan/index.test.tsx`
- Test: `web/src/pages/data-health/index.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
import { render, screen } from '@testing-library/react';
import { KaipanPage } from './index';

it('renders the kaipan page title', () => {
  render(<KaipanPage />);
  expect(screen.getByText('Kaipan')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pnpm test web/src/pages/kaipan/index.test.tsx web/src/pages/data-health/index.test.tsx
```
Expected: fail because the pages do not exist yet.

- [ ] **Step 3: Implement the pages with operational controls and report viewing**

```tsx
export function KaipanPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Kaipan" description="Trigger fetch, normalize, status, and run flows." />
      <KaipanCenter />
    </main>
  );
}
```

```tsx
export function DataHealthPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Data Health" description="Inspect dashboard reports and operational alerts." />
      <DataHealthCenter />
    </main>
  );
}
```

```tsx
export function KaipanCenter() {
  return (
    <section className="dashboard-grid">
      <Card>
        <CardHeader>
          <CardTitle>Fetch and normalize</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Show the active trade date, slot selector, and the latest fetch / normalize summary.</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Status and run</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Expose the read-only status panel, plus the backend-controlled run action.</p>
        </CardContent>
      </Card>
    </section>
  );
}
```

- [ ] **Step 4: Run the tests again and make sure they pass**

Run:
```bash
pnpm test web/src/pages/kaipan/index.test.tsx web/src/pages/data-health/index.test.tsx
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/kaipan web/src/features/data-health web/src/pages/kaipan web/src/pages/data-health web/src/app/router.tsx web/src/app/navigation.ts
git commit -m "feat(web-s6-008c): add operations pages"
```

### Task 4: Verify Kaipan and data-health operational flows

**Files:**
- Modify: `docs/Web-TaskList.md`
- Modify: `daily-sessions/2026-05-09.md`
- Modify: `daily-report/2026-05-09.md`

- [ ] **Step 1: Run backend and frontend validation**

Run:
```bash
PYTHONPATH=. pytest tests/api/routers/ui/test_kaipan.py tests/api/routers/ui/test_data_health.py -q
pnpm test web/src/lib/api/kaipan.test.ts web/src/lib/api/dataHealth.test.ts web/src/pages/kaipan/index.test.tsx web/src/pages/data-health/index.test.tsx
pnpm typecheck
pnpm lint
```
Expected: all pass.

- [ ] **Step 2: Validate safety constraints**

Confirm Kaipan actions remain backend-controlled, `status` stays read-only, and dashboard HTML uses the existing safe preview path.

- [ ] **Step 3: Record the handoff**

Write the exact completion notes for `WEB-S6-008` in `daily-sessions` and `daily-report`, and mark the task boundaries clearly in `docs/Web-TaskList.md`.
