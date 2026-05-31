# OHLCV Stock Info Precheck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 `/market/ohlcv` 入口内增加 `stock_info` 前置检查与更新提示，让用户在抓取 OHLCV 前能先确认股票基础信息是否新鲜，必要时一键刷新，而不是新增独立业务页面。

**Architecture:** 继续以 `/market/ohlcv` 作为唯一主入口，页面加载时先查询后端给出的 `stock_info` 状态摘要，再决定是直接展示抓取表单，还是提示用户先刷新基础信息。后端复用现有 `stock_info_update` pipeline 步骤，不改数据库 schema，不新增独立工作流，只在市场工作台补一个轻量的检查/刷新接口和 UI 状态展示。

**Tech Stack:** FastAPI, SQLAlchemy async, React, TanStack Query, existing market workspace UI.

---

### Task 1: Add backend stock info status and refresh endpoints

**Files:**
- Modify: `api/routers/ui/market.py`
- Modify: `api/schemas/market.py`
- Modify: `src/market_data/stock_info_service.py`
- Test: `tests/api/routers/test_market_ui.py`
- Test: `tests/unit/services/test_stock_info_service.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_get_stock_info_status_returns_freshness_and_counts(client):
    response = await client.get("/api/ui/v1/market/stock-info/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 0
    assert "is_fresh" in payload
    assert "latest_updated_at" in payload


async def test_refresh_stock_info_triggers_update(client, monkeypatch):
    called = {"value": False}

    async def fake_update():
        called["value"] = True
        return {"total": 10, "inserted": 1, "updated": 9, "skipped": 0}

    monkeypatch.setattr("src.market_data.stock_info_service.fetch_and_store_stock_list", fake_update)
    response = await client.post("/api/ui/v1/market/stock-info/refresh")
    assert response.status_code == 200
    assert called["value"] is True
```

- [ ] **Step 2: Run the targeted tests to confirm they fail**

Run: `python -m pytest tests/api/routers/test_market_ui.py tests/unit/services/test_stock_info_service.py -q`
Expected: FAIL because the new endpoints and payload fields do not exist yet.

- [ ] **Step 3: Implement the minimal backend changes**

```python
@router.get("/stock-info/status")
async def get_stock_info_status(...):
    # Return counts, freshness, latest update time, benchmark coverage, and a human-readable hint.


@router.post("/stock-info/refresh")
async def refresh_stock_info(...):
    # Reuse stock_info_update logic to refresh stock_info and benchmark indices.
```

- [ ] **Step 4: Run the targeted tests to confirm they pass**

Run: `python -m pytest tests/api/routers/test_market_ui.py tests/unit/services/test_stock_info_service.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/routers/ui/market.py api/schemas/market.py src/market_data/stock_info_service.py tests/api/routers/test_market_ui.py tests/unit/services/test_stock_info_service.py
git commit -m "feat(market): add stock info precheck endpoints"
```

### Task 2: Add OHLCV workspace precheck UI

**Files:**
- Modify: `web/src/features/market-workspace/market-workspace-shell.tsx`
- Modify: `web/src/lib/api/market.ts`
- Modify: `web/src/types/market.ts`
- Test: `web/src/features/market-workspace/market-workspace-shell.test.tsx`
- Test: `web/src/lib/api/market.test.ts`

- [ ] **Step 1: Write the failing tests**

```tsx
it("shows stock info freshness warning before OHLCV submission", async () => {
  mockedGetStockInfoStatus.mockResolvedValue({
    total: 5515,
    is_fresh: false,
    latest_updated_at: "2026-05-01T00:00:00Z",
    benchmark_count: 10,
    message: "stock_info 已过期，请先刷新",
  });
  render(<MarketWorkspaceShell mode="ohlcv" />);
  expect(await screen.findByText("stock_info 已过期，请先刷新")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the targeted tests to confirm they fail**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm test -- src/features/market-workspace/market-workspace-shell.test.tsx src/lib/api/market.test.ts`
Expected: FAIL because the new API and UI state do not exist yet.

- [ ] **Step 3: Implement the minimal UI changes**

```tsx
const stockInfoStatusQuery = useQuery({
  queryKey: ['market-workspace-stock-info-status', selectedProfileId],
  queryFn: () => getStockInfoStatus(selectedProfileId),
});

const refreshStockInfoMutation = useMutation({
  mutationFn: () => refreshStockInfo(selectedProfileId),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['market-workspace-stock-info-status'] }),
});
```

- [ ] **Step 4: Run the targeted tests to confirm they pass**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm test -- src/features/market-workspace/market-workspace-shell.test.tsx src/lib/api/market.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/market-workspace/market-workspace-shell.tsx web/src/lib/api/market.ts web/src/types/market.ts web/src/features/market-workspace/market-workspace-shell.test.tsx web/src/lib/api/market.test.ts
git commit -m "feat(market-ui): add stock info precheck in ohlcv workspace"
```

### Task 3: Verify no regression in existing market workflow

**Files:**
- Test: `tests/api/routers/test_market_ui.py`
- Test: `tests/unit/services/test_stock_info_service.py`
- Test: `web/src/features/market-workspace/market-workspace-shell.test.tsx`
- Test: `web/src/lib/api/market.test.ts`

- [ ] **Step 1: Run the full affected test slice**

Run: `python -m pytest tests/api/routers/test_market_ui.py tests/unit/services/test_stock_info_service.py -q`
Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm test -- src/features/market-workspace/market-workspace-shell.test.tsx src/lib/api/market.test.ts`

- [ ] **Step 2: Run typecheck**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm typecheck`

- [ ] **Step 3: Inspect diff for formatting and contract drift**

Run: `git diff --check`

- [ ] **Step 4: Commit the verified feature**

```bash
git add -A
git commit -m "feat(market): gate ohlcv on stock info freshness"
```
