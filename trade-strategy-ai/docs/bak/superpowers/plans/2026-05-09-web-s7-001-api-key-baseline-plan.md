# WEB-S7-001 API Key Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Web UI API 收口到统一、严格、可测试的 API Key 鉴权基线，并把前端请求头注入统一起来。

**Architecture:** 后端继续使用单一 `verify_api_key` 入口，但改成“显式关闭才匿名、开启后必须命中 key”的严格语义。前端把所有 UI 请求的鉴权头注入集中到共享 API client，不再在各个模块里手工拼 `X-API-Key`。最后用一组后端和前端回归测试锁定授权、未授权和空 key 配置的行为。

**Tech Stack:** FastAPI、Pydantic/配置加载、pytest、Vitest、TypeScript、fetch。

---

### Task 1: 收紧后端 UI API Key 鉴权语义

**Files:**
- Modify: `api/dependencies.py`
- Create: `tests/unit/api/test_dependencies.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from fastapi import HTTPException

from api.dependencies import verify_api_key


@pytest.mark.asyncio
async def test_verify_api_key_allows_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": False, "api_keys": []}},
    )
    assert await verify_api_key(None) == "anonymous"


@pytest.mark.asyncio
async def test_verify_api_key_accepts_matching_key(monkeypatch):
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": ["demo-key"]}},
    )
    assert await verify_api_key("demo-key") == "demo-key"


@pytest.mark.asyncio
async def test_verify_api_key_rejects_missing_or_unknown_key(monkeypatch):
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": ["demo-key"]}},
    )
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(None)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_verify_api_key_rejects_empty_key_list(monkeypatch):
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": []}},
    )
    with pytest.raises(HTTPException) as exc:
        await verify_api_key("demo-key")
    assert exc.value.status_code == 403
```

- [ ] **Step 2: Run the tests and confirm the current behavior is wrong**

Run:

```bash
pytest tests/unit/api/test_dependencies.py -v
```

Expected:

- Fails because `enabled=true` + empty `api_keys` still falls through to anonymous in the current implementation.

- [ ] **Step 3: Implement the strict auth baseline**

Update `verify_api_key()` so that:

- `enabled=False` returns `"anonymous"`.
- `enabled=True` requires a non-empty `X-API-Key` that matches `api_keys`.
- `enabled=True` and empty `api_keys` still denies access.
- Unauthorized access always raises the same 403 error detail.

If `get_current_key()` stays in place, align it with the same enable/disable semantics so it never masks an invalid enabled configuration.

- [ ] **Step 4: Run the tests again**

Run:

```bash
pytest tests/unit/api/test_dependencies.py -v
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add api/dependencies.py tests/unit/api/test_dependencies.py
git commit -m "fix(web-s7-001): tighten api key auth baseline"
```

### Task 2: Unify frontend API Key header injection

**Files:**
- Modify: `web/src/lib/api/http.ts`
- Modify: `web/src/lib/api/imports.ts`
- Modify: `web/src/lib/api/backtests.ts`
- Modify: `web/src/lib/api/alerts.ts`
- Modify: `web/src/lib/api/artifacts.ts`
- Create: `web/src/lib/api/http.test.ts`
- Create: `web/src/lib/api/artifacts.test.ts`

- [ ] **Step 1: Write the failing tests**

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { API_KEY_STORAGE_KEY, fetchJson } from '@/lib/api/http';
import { listAlertHistory } from '@/lib/api/alerts';

describe('api auth header injection', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn());
    window.localStorage.clear();
  });

  it('adds X-API-Key for versioned json requests', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => ({}) } as Response);
    await fetchJson('/system/status');
    const [, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });

  it('adds X-API-Key for root alerts requests', async () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, 'demo-key');
    vi.mocked(fetch).mockResolvedValueOnce({ ok: true, json: async () => ({ count: 0, total: 0, items: [] }) } as Response);
    await listAlertHistory();
    const [, init] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect((init?.headers as Headers).get('X-API-Key')).toBe('demo-key');
  });
});
```

- [ ] **Step 2: Run the frontend API tests and confirm the duplicated header logic still exists**

Run:

```bash
pnpm test -- web/src/lib/api/http.test.ts web/src/lib/api/imports.test.ts web/src/lib/api/alerts.test.ts web/src/lib/api/backtests.test.ts web/src/lib/api/artifacts.test.ts
```

Expected:

- At least one test fails until the shared auth helper is wired through all callers.

- [ ] **Step 3: Refactor the client to one shared auth path**

Make `web/src/lib/api/http.ts` the single place that knows how to read `trade-strategy-ai.apiKey` and build authenticated headers. Then:

- switch `imports.ts` to reuse the shared JSON fetch path instead of its own manual `fetch()`
- switch `alerts.ts`, `backtests.ts`, and `artifacts.ts` to reuse the shared header builder instead of duplicating `localStorage` reads
- keep the endpoint URLs unchanged
- preserve upload and download behavior, including non-JSON requests

- [ ] **Step 4: Run the frontend API tests again**

Run:

```bash
pnpm test -- web/src/lib/api/http.test.ts web/src/lib/api/imports.test.ts web/src/lib/api/alerts.test.ts web/src/lib/api/backtests.test.ts web/src/lib/api/artifacts.test.ts
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api/http.ts web/src/lib/api/http.test.ts web/src/lib/api/imports.ts web/src/lib/api/imports.test.ts web/src/lib/api/alerts.ts web/src/lib/api/alerts.test.ts web/src/lib/api/backtests.ts web/src/lib/api/backtests.test.ts web/src/lib/api/artifacts.ts web/src/lib/api/artifacts.test.ts
git commit -m "fix(web-s7-001): unify ui api key injection"
```

### Task 3: Add route-level auth regression coverage and run the full baseline

**Files:**
- Create: `tests/api/routers/ui/test_ui_auth_baseline.py`

- [ ] **Step 1: Write the failing regression test**

```python
import pytest

from httpx import ASGITransport, AsyncClient
from api.main import app


@pytest.mark.asyncio
async def test_ui_route_rejects_missing_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/ui/v1/system/status")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ui_route_allows_matching_key(monkeypatch):
    monkeypatch.setattr(
        "api.dependencies._get_api_config",
        lambda: {"auth": {"enabled": True, "api_keys": ["demo-key"]}},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": "demo-key"},
    ) as client:
        response = await client.get("/api/ui/v1/system/status")
    assert response.status_code == 200
```

- [ ] **Step 2: Run the regression test and confirm the current route coverage is incomplete**

Run:

```bash
pytest tests/api/routers/ui/test_ui_auth_baseline.py -v
```

Expected:

- Fails until at least one real UI route is covered without overriding `verify_api_key`.

- [ ] **Step 3: Implement the route-level smoke test**

Cover one read route and one write route against the real app wiring:

- `GET /api/ui/v1/system/status`
- `POST /api/ui/v1/imports/crawl-state/migrate`

Use the real dependency chain, with `api.dependencies._get_api_config` monkeypatched to simulate:

- `enabled=False` for anonymous access
- `enabled=True` with a valid key for authorized access
- `enabled=True` with empty key list for the deny case

- [ ] **Step 4: Run the full verification matrix**

Run:

```bash
pytest tests/unit/api/test_dependencies.py tests/api/routers/ui/test_ui_auth_baseline.py -v
pnpm test -- web/src/lib/api/http.test.ts web/src/lib/api/imports.test.ts web/src/lib/api/alerts.test.ts web/src/lib/api/backtests.test.ts web/src/lib/api/artifacts.test.ts
pnpm typecheck
pnpm lint
```

Expected:

- PASS

- [ ] **Step 5: Commit**

```bash
git add tests/api/routers/ui/test_ui_auth_baseline.py tests/api/routers/ui/test_system_status.py
git commit -m "test(web-s7-001): cover ui api auth baseline"
```

---

## Coverage Check

- Spec requirement: UI API can be enabled or disabled by config.
  - Covered by Task 1.
- Spec requirement: Unauthorized requests are denied with a consistent error.
  - Covered by Task 1 and Task 3.
- Spec requirement: Empty `api_keys` must not silently allow access.
  - Covered by Task 1.
- Spec requirement: Frontend injects `X-API-Key` through one shared path.
  - Covered by Task 2.
- Spec requirement: Upload and download requests continue to work.
  - Covered by Task 2.
- Spec requirement: Regression coverage exists at route level and client level.
  - Covered by Task 2 and Task 3.
