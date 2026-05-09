# WEB-S6-008B Data Import Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Web data import workbench for trade-log import and crawl state migration with audit-friendly previews.

**Architecture:** Keep upload and migration logic on the backend through a dedicated UI BFF. The frontend should provide one upload-oriented page and one migration page, each centered around parameter preview, dry-run support, and clear result summaries. The design keeps high-risk writes isolated and easy to verify.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, React, React Router, shadcn/ui, TanStack Query, Vitest, pytest

---

### Task 1: Add import UI BFF routes

**Files:**
- Create: `api/routers/ui/imports.py`
- Create: `web/src/features/imports/index.ts`
- Modify: `api/routers/ui/__init__.py`
- Modify: `api/app.py`
- Test: `tests/api/routers/ui/test_imports.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_import_trade_logs_dry_run_returns_summary(client, tmp_path):
    sample = tmp_path / "sample.csv"
    sample.write_text("date,symbol,qty\n2026-05-09,000001.SZ,10\n", encoding="utf-8")
    with sample.open("rb") as fh:
        response = await client.post(
            "/api/ui/v1/imports/trade-logs",
            data={"dry_run": "true"},
            files={"file": ("sample.csv", fh, "text/csv")},
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["dry_run"] is True
    assert "rows_seen" in payload
```

```python
async def test_migrate_crawl_state_returns_job_or_summary(client):
    response = await client.post("/api/ui/v1/imports/crawl-state/migrate", json={})
    assert response.status_code == 200
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
PYTHONPATH=. pytest tests/api/routers/ui/test_imports.py -q
```
Expected: fail because route module does not exist yet.

For the final route tests, use `app.dependency_overrides` to inject `verify_api_key` and `get_setup_service` fakes so the tests stay isolated from DB and config side effects.

- [ ] **Step 3: Implement the minimal import routes**

```python
def _config_path() -> Path:
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


def get_setup_service() -> SetupService:
    return SetupService()


@router.post("/trade-logs", dependencies=[Depends(verify_api_key)])
async def import_trade_logs(
    file: UploadFile = File(...),
    dry_run: bool = Form(False),
    source: str = Form("csv_import"),
    service: SetupService = Depends(get_setup_service),
):
    from tempfile import TemporaryDirectory

    suffix = Path(file.filename or "sample.csv").suffix or ".csv"
    with TemporaryDirectory(prefix="trade-strategy-ai-import-") as tmp_dir:
        target = Path(tmp_dir) / f"trade-log{suffix}"
        target.write_bytes(await file.read())
        result = await service.import_trade_logs(
            config_path=_config_path(),
            csv_path=target,
            source=source,
            dry_run=dry_run,
        )
    return result.payload
```

```python
@router.post("/crawl-state/migrate", dependencies=[Depends(verify_api_key)])
async def migrate_crawl_state(service: SetupService = Depends(get_setup_service)):
    result = await service.migrate_crawl_state(config_path=_config_path())
    return result.payload
```

- [ ] **Step 4: Run the tests again and make sure they pass**

Run:
```bash
PYTHONPATH=. pytest tests/api/routers/ui/test_imports.py -q
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add api/routers/ui/imports.py api/routers/ui/__init__.py api/app.py tests/api/routers/ui/test_imports.py
git commit -m "feat(web-s6-008b): add import ui bff routes"
```

### Task 2: Add the import workbench frontend API and types

**Files:**
- Create: `web/src/lib/api/imports.ts`
- Create: `web/src/types/imports.ts`
- Test: `web/src/lib/api/imports.test.ts`

- [ ] **Step 1: Write the failing tests**

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';
import { importTradeLogs, migrateCrawlState } from './imports';

describe('imports api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('posts to the versioned imports endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ rows_seen: 0, dry_run: true }),
    } as Response);

    const file = new File(['date,symbol,qty\n2026-05-09,000001.SZ,10\n'], 'sample.csv', { type: 'text/csv' });
    await importTradeLogs({ file, dryRun: true });

    expect(fetch).toHaveBeenCalledWith(
      '/api/ui/v1/imports/trade-logs',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Accept: 'application/json',
          'X-API-Key': 'demo-key',
        }),
        body: expect.any(FormData),
      }),
    );
  });

  it('posts the crawl-state migration request', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ migrated: true }),
    } as Response);

    await migrateCrawlState({});

    expect(fetch).toHaveBeenCalledWith(
      '/api/ui/v1/imports/crawl-state/migrate',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Accept: 'application/json',
          'X-API-Key': 'demo-key',
          'Content-Type': 'application/json',
        }),
      }),
    );
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pnpm test web/src/lib/api/imports.test.ts
```
Expected: fail because the module does not exist yet.

- [ ] **Step 3: Implement the minimal client helpers**

```ts
import { API_KEY_STORAGE_KEY, fetchJson, getApiBaseUrl } from './http';

export async function importTradeLogs(payload: ImportTradeLogsRequest) {
  const form = new FormData();
  form.append('file', payload.file);
  form.append('dry_run', String(payload.dryRun));
  if (payload.source) {
    form.append('source', payload.source);
  }

  const headers = new Headers();
  headers.set('Accept', 'application/json');
  if (typeof window !== 'undefined') {
    const apiKey = window.localStorage.getItem(API_KEY_STORAGE_KEY);
    if (apiKey) {
      headers.set('X-API-Key', apiKey);
    }
  }

  const response = await fetch(`${getApiBaseUrl()}/imports/trade-logs`, {
    method: 'POST',
    headers,
    body: form,
  });
  if (!response.ok) {
    throw new Error(response.statusText || 'trade log import failed');
  }
  return (await response.json()) as ImportTradeLogsResponse;
}
```

```ts
export function migrateCrawlState(payload: MigrateCrawlStateRequest) {
  return fetchJson<MigrateCrawlStateResponse>('/imports/crawl-state/migrate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 4: Run the tests again and make sure they pass**

Run:
```bash
pnpm test web/src/lib/api/imports.test.ts
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api/imports.ts web/src/types/imports.ts web/src/lib/api/imports.test.ts
git commit -m "feat(web-s6-008b): add import api client"
```

### Task 3: Build the import and migration pages

**Files:**
- Create: `web/src/features/imports/import-center.tsx`
- Create: `web/src/pages/imports/index.tsx`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/navigation.ts`
- Test: `web/src/pages/imports/index.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
import { render, screen } from '@testing-library/react';
import { ImportsPage } from './index';

it('renders the imports page title', () => {
  render(<ImportsPage />);
  expect(screen.getByText('Imports')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pnpm test web/src/pages/imports/index.test.tsx
```
Expected: fail because the page does not exist yet.

- [ ] **Step 3: Implement the page with upload and migration sections**

```tsx
export function ImportsPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Imports" description="Upload trade logs and migrate crawl state with audit-friendly previews." />
      <ImportCenter />
    </main>
  );
}
```

```tsx
export function ImportCenter() {
  return (
    <section className="dashboard-grid">
      <Card>
        <CardHeader>
          <CardTitle>Trade log import</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Accept a CSV, Excel, HTML, or PDF file, persist a temporary backend copy, and show dry-run results before any write.</p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Crawl state migration</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Show which crawl sources will be migrated, then run the migration only after explicit confirmation.</p>
        </CardContent>
      </Card>
    </section>
  );
}
```

- [ ] **Step 4: Run the tests again and make sure they pass**

Run:
```bash
pnpm test web/src/pages/imports/index.test.tsx
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/imports web/src/pages/imports web/src/app/router.tsx web/src/app/navigation.ts
git commit -m "feat(web-s6-008b): add import pages"
```

### Task 4: Verify upload, dry-run, and audit flows

**Files:**
- Modify: `docs/Web-TaskList.md`
- Modify: `daily-sessions/2026-05-09.md`
- Modify: `daily-report/2026-05-09.md`

- [ ] **Step 1: Run backend and frontend validation**

Run:
```bash
PYTHONPATH=. pytest tests/api/routers/ui/test_imports.py -q
pnpm test web/src/lib/api/imports.test.ts web/src/pages/imports/index.test.tsx
pnpm typecheck
pnpm lint
```
Expected: all pass.

- [ ] **Step 2: Validate the audit boundary**

Confirm the upload page limits file type, file size, and destination directory, and that dry-run never persists records. The route should reject unsupported file extensions and should never accept a raw `csv_path` from the browser.

- [ ] **Step 3: Record the handoff**

Write the exact next continuation point for `WEB-S6-008C` in `daily-sessions`, and summarize the delivered import work in `daily-report`.
