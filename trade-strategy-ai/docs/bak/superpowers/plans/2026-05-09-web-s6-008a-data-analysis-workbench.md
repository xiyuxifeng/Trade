# WEB-S6-008A Data Analysis Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Web analysis workbench for signals, Persona sample generation, and MarketState construction.

**Architecture:** Reuse the existing `SignalService` and `PersonaService` behind versioned UI BFF routes. The frontend gets three focused pages under a shared control-console layout: signal browsing, Persona sample generation, and MarketState building. Each page stays mostly read-only, with the only write action being sample/file generation on the backend.

Each UI BFF module should expose a small dependency factory, read `CONFIG_PATH` through the same project-path helper used by `api/routers/ui/system.py`, and remain easy to override in tests.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, React, React Router, shadcn/ui, TanStack Query, Vitest, pytest

---

### Task 1: Add analysis UI BFF routes

**Files:**
- Create: `api/routers/ui/signals.py`
- Create: `api/routers/ui/persona.py`
- Create: `web/src/features/signals/index.ts`
- Create: `web/src/features/persona/index.ts`
- Create: `web/src/features/market-state/index.ts`
- Modify: `api/routers/ui/__init__.py`
- Modify: `api/app.py`
- Test: `tests/api/routers/ui/test_signals.py`
- Test: `tests/api/routers/ui/test_persona.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_list_signals_returns_summary(client):
    response = await client.get("/api/ui/v1/signals?limit=2")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] <= 2
    assert "signals" in payload
    assert "context_summary" in payload["signals"][0]
```

```python
async def test_build_sample_clusters_returns_path(client):
    response = await client.post("/api/ui/v1/persona/sample", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["clusters_path"].endswith(".json")
```

```python
async def test_build_market_state_returns_snapshot(client):
    response = await client.post(
        "/api/ui/v1/persona/market-state/build",
        json={"as_of": "2026-05-09", "from_akshare": False, "cache_csv": True},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "snapshot_path" in payload
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
PYTHONPATH=. pytest tests/api/routers/ui/test_signals.py tests/api/routers/ui/test_persona.py -q
```
Expected: fail with missing route/module errors.

For the final route tests, use `app.dependency_overrides` to inject `verify_api_key`, `get_signal_service`, and `get_persona_service` fakes so the tests stay isolated from DB and config side effects.

- [ ] **Step 3: Implement the minimal BFF routes**

```python
def _config_path() -> Path:
    return resolve_project_path(os.environ.get("CONFIG_PATH", "config/app.yaml"))


def get_signal_service() -> SignalService:
    return SignalService()


@router.get("/signals", dependencies=[Depends(verify_api_key)])
async def list_signals(
    symbol: str | None = None,
    since: str | None = None,
    limit: int = 100,
    service: SignalService = Depends(get_signal_service),
):
    result = service.list_signals(config_path=_config_path(), symbol=symbol, since=since, limit=limit)
    return result.payload
```

```python
def get_persona_service() -> PersonaService:
    return PersonaService()


@router.post("/persona/sample", dependencies=[Depends(verify_api_key)])
async def build_sample_clusters(service: PersonaService = Depends(get_persona_service)):
    result = service.build_sample_clusters(config_path=_config_path())
    return result.payload
```

```python
@router.post("/persona/market-state/build", dependencies=[Depends(verify_api_key)])
async def build_market_state(
    request: MarketStateBuildRequest,
    service: PersonaService = Depends(get_persona_service),
):
    result = service.build_market_state(
        config_path=_config_path(),
        as_of=request.as_of,
        from_akshare=request.from_akshare,
        cache_csv=request.cache_csv,
    )
    return result.payload
```

- [ ] **Step 4: Run the tests again and make sure they pass**

Run:
```bash
PYTHONPATH=. pytest tests/api/routers/ui/test_signals.py tests/api/routers/ui/test_persona.py -q
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add api/routers/ui/signals.py api/routers/ui/persona.py api/routers/ui/__init__.py api/app.py tests/api/routers/ui/test_signals.py tests/api/routers/ui/test_persona.py
git commit -m "feat(web-s6-008a): add analysis ui bff routes"
```

### Task 2: Add typed frontend clients and DTOs

**Files:**
- Create: `web/src/lib/api/signals.ts`
- Create: `web/src/lib/api/persona.ts`
- Create: `web/src/types/signals.ts`
- Create: `web/src/types/persona.ts`
- Create: `web/src/types/market-state.ts`
- Test: `web/src/lib/api/signals.test.ts`
- Test: `web/src/lib/api/persona.test.ts`

Define the analysis DTOs explicitly:
- `web/src/types/signals.ts`: signal list response and filters
- `web/src/types/persona.ts`: Persona sample and MarketState request/response helpers
- `web/src/types/market-state.ts`: `MarketStateBuildRequest` with `as_of`, `from_akshare`, `cache_csv`, plus `MarketStateBuildResponse`

- [ ] **Step 1: Write the failing tests**

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY } from '@/lib/api/http';
import { buildMarketState, buildSampleClusters } from './persona';

describe('persona api', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('posts to the versioned ui endpoint', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ clusters_path: 'data/processed/persona/clusters.sample.json' }),
    } as Response);

    await buildSampleClusters({});

    expect(fetch).toHaveBeenCalledWith(
      '/api/ui/v1/persona/sample',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Accept: 'application/json',
          'X-API-Key': 'demo-key',
        }),
      }),
    );
  });

  it('posts the market-state build request', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ snapshot_path: 'data/processed/market-state/latest.json' }),
    } as Response);

    await buildMarketState({ as_of: '2026-05-09', from_akshare: false, cache_csv: true });

    expect(fetch).toHaveBeenCalledWith(
      '/api/ui/v1/persona/market-state/build',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
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
pnpm test web/src/lib/api/signals.test.ts web/src/lib/api/persona.test.ts
```
Expected: fail because the modules do not exist yet.

- [ ] **Step 3: Implement the minimal client helpers**

```ts
import { fetchJson } from './http';

export function listSignals(params: SignalListParams = {}) {
  const suffix = new URLSearchParams(
    Object.entries(params).reduce<Record<string, string>>((acc, [key, value]) => {
      if (value !== undefined && value !== null && value !== '') acc[key] = String(value);
      return acc;
    }, {}),
  ).toString();
  return fetchJson<SignalListResponse>(suffix ? `/signals?${suffix}` : '/signals');
}
```

```ts
export function buildMarketState(payload: MarketStateBuildRequest) {
  return fetchJson<MarketStateBuildResponse>('/persona/market-state/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}
```

- [ ] **Step 4: Run the tests again and make sure they pass**

Run:
```bash
pnpm test web/src/lib/api/signals.test.ts web/src/lib/api/persona.test.ts
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api/signals.ts web/src/lib/api/persona.ts web/src/types/signals.ts web/src/types/persona.ts web/src/types/market-state.ts web/src/lib/api/signals.test.ts web/src/lib/api/persona.test.ts
git commit -m "feat(web-s6-008a): add analysis api clients"
```

### Task 3: Build the three analysis pages

**Files:**
- Create: `web/src/features/signals/signals-center.tsx`
- Create: `web/src/features/persona/persona-center.tsx`
- Create: `web/src/features/market-state/market-state-center.tsx`
- Create: `web/src/pages/signals/index.tsx`
- Create: `web/src/pages/persona/index.tsx`
- Create: `web/src/pages/market-state/index.tsx`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/navigation.ts`
- Test: `web/src/pages/signals/index.test.tsx`
- Test: `web/src/pages/persona/index.test.tsx`
- Test: `web/src/pages/market-state/index.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
import { render, screen } from '@testing-library/react';
import { SignalsPage } from './index';

it('renders the signals page header', () => {
  render(<SignalsPage />);
  expect(screen.getByText('Signals')).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pnpm test web/src/pages/signals/index.test.tsx web/src/pages/persona/index.test.tsx web/src/pages/market-state/index.test.tsx
```
Expected: fail because the pages are missing.

- [ ] **Step 3: Implement the pages with the shared console layout**

```tsx
export function SignalsPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Signals" description="Browse and filter strategy signals." />
      <SignalsCenter />
    </main>
  );
}
```

```tsx
export function PersonaPage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Persona" description="Generate sample persona clusters and inspect market state." />
      <PersonaCenter />
    </main>
  );
}
```

```tsx
export function MarketStatePage() {
  return (
    <main className="page-stack">
      <PageHeader kicker="Data Ops" title="Market State" description="Build and inspect the current market state snapshot." />
      <MarketStateCenter />
    </main>
  );
}
```

- [ ] **Step 3b: Re-export page entry points from feature indexes**

```ts
export { SignalsCenter as SignalsPage } from './signals-center';
```

```ts
export { PersonaCenter as PersonaPage } from './persona-center';
```

```ts
export { MarketStateCenter as MarketStatePage } from './market-state-center';
```

- [ ] **Step 4: Run the tests again and make sure they pass**

Run:
```bash
pnpm test web/src/pages/signals/index.test.tsx web/src/pages/persona/index.test.tsx web/src/pages/market-state/index.test.tsx
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/signals web/src/features/persona web/src/features/market-state web/src/pages/signals web/src/pages/persona web/src/pages/market-state web/src/app/router.tsx web/src/app/navigation.ts
git commit -m "feat(web-s6-008a): add analysis pages"
```

### Task 4: Verify the analysis slice end to end

**Files:**
- Modify: `docs/Web-TaskList.md`
- Modify: `daily-sessions/2026-05-09.md`
- Modify: `daily-report/2026-05-09.md`

- [ ] **Step 1: Run backend and frontend tests**

Run:
```bash
PYTHONPATH=. pytest tests/api/routers/ui/test_signals.py tests/api/routers/ui/test_persona.py -q
pnpm test web/src/lib/api/signals.test.ts web/src/lib/api/persona.test.ts web/src/pages/signals/index.test.tsx web/src/pages/persona/index.test.tsx web/src/pages/market-state/index.test.tsx
pnpm typecheck
pnpm lint
```
Expected: all pass.

- [ ] **Step 2: Update task status**

Mark `WEB-S6-008` complete only after the analysis slice is finished, the pages load, the BFF routes respond, and the tests pass.

- [ ] **Step 3: Record the handoff**

Write the exact next continuation point for `WEB-S6-008B` in `daily-sessions`, and summarize the delivered analysis work in `daily-report`.
