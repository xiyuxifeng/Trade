# NW-V2-S2-005 Market Snapshot Query API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide stable Web API endpoints for querying Market Snapshot and Market Dataset from the database-backed market data store, without reading files or exposing server paths.

**Architecture:** Keep all query logic in a dedicated `MarketSnapshotQueryService` that reads from repository classes backed by the DB storage introduced in `NW-V2-S2-004`. The FastAPI router should only validate input, enforce auth, and map service results to API responses. This task extends the existing market UI API surface; it does not add CLI commands, provider calls, or file-based query paths.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy async repositories, existing `JobService` / `ArtifactService` conventions, pytest, httpx test client.

---

## File Structure

### Purpose-driven file map

- Modify `api/routers/ui/market.py`: add Market Snapshot / Dataset query endpoints and map query-service errors to HTTP status codes.
- Modify `api/schemas/market.py`: add request/response models for snapshot list, snapshot detail, section detail, quality report, dataset list, and structured error payloads.
- Create `src/services/market_snapshot_query_service.py`: implement all read-only query methods on top of `MarketSnapshotRepository`, `MarketSnapshotSectionRepository`, `MarketSnapshotItemRepository`, `MarketDatasetRepository`, and `MarketDataQualityRepository`.
- Modify `src/db/repositories/*.py` only if a query shape is missing for pagination, filtering, or `section`/`topic` lookups.
- Modify `tests/api/routers/test_market_ui.py` or create `tests/api/routers/test_market_snapshot_query_ui.py`: cover API contract, status mapping, pagination, and error cases.
- Create `tests/unit/services/test_market_snapshot_query_service.py`: cover repository-backed query behavior independent of HTTP.
- Create `docs/New-Web-Market-Snapshot-API.md`: document endpoints, filters, error shapes, and compatibility boundaries.
- Update `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`, `daily-sessions/2026-05-16.md`, and `daily-report/2026-05-16.md` only after implementation and verification pass.

## Scope Check

This task only covers the API query layer for already persisted market data.

It must not:
- add new CLI commands
- call providers directly
- read market snapshot files as the primary source
- expose absolute filesystem paths
- bypass profile/config permission checks
- create a second market data fact source outside the DB repositories

It must:
- serve Web UI consumers
- support external system reads through the same stable contract
- return structured, user-facing errors
- keep query logic outside the router

## Task 1: Query Service and Schema Contract

**Files:**
- Create: `src/services/market_snapshot_query_service.py`
- Modify: `api/schemas/market.py`
- Test: `tests/unit/services/test_market_snapshot_query_service.py`

- [ ] **Step 1: Write the failing service tests**

```python
@pytest.mark.asyncio
async def test_list_snapshots_filters_trade_date_market_and_paginates():
    service = MarketSnapshotQueryService(snapshot_repository=fake_snapshot_repo, ...)
    result = await service.list_snapshots(trade_date="2026-05-16", market="CN", limit=10, offset=0)
    assert result.status == "ok"
    assert result.payload["items"][0]["snapshot_id"] == "snap-001"
    assert result.payload["page"]["limit"] == 10
    assert result.payload["page"]["offset"] == 0


@pytest.mark.asyncio
async def test_get_snapshot_detail_returns_sections_items_and_quality():
    service = MarketSnapshotQueryService(...)
    result = await service.get_snapshot_detail("snap-001")
    assert result.status == "ok"
    assert result.payload["snapshot"]["snapshot_id"] == "snap-001"
    assert result.payload["sections"][0]["section_id"] == "overview"
    assert result.payload["quality_report"]["overall_status"] in {"ok", "partial"}


@pytest.mark.asyncio
async def test_get_dataset_detail_returns_dataset_and_items():
    service = MarketSnapshotQueryService(...)
    result = await service.get_dataset_detail("snap-001:dataset")
    assert result.status == "ok"
    assert result.payload["dataset"]["dataset_id"] == "snap-001:dataset"
```

- [ ] **Step 2: Run the tests and confirm they fail for missing service methods**

Run: `../.venv/bin/python -m pytest tests/unit/services/test_market_snapshot_query_service.py -v`
Expected: fail because `MarketSnapshotQueryService` methods or schema models are not implemented yet.

- [ ] **Step 3: Implement the minimal query service and response models**

```python
class MarketSnapshotQueryService(BaseService):
    async def list_snapshots(self, *, trade_date=None, market=None, quality_status=None, limit=50, offset=0): ...
    async def get_snapshot_detail(self, snapshot_id: str): ...
    async def list_snapshot_sections(self, snapshot_id: str): ...
    async def get_snapshot_section(self, snapshot_id: str, section: str): ...
    async def list_datasets(self, *, trade_date=None, market=None, dataset_type=None, limit=50, offset=0): ...
    async def get_dataset_detail(self, dataset_id: str): ...
    async def get_quality_report(self, snapshot_id: str): ...
```

Response models should include:
- `MarketSnapshotListResponse`
- `MarketSnapshotDetailResponse`
- `MarketSnapshotSectionResponse`
- `MarketSnapshotQualityResponse`
- `MarketDatasetListResponse`
- `MarketDatasetDetailResponse`
- `MarketQueryError`

Implementation rules:
- use repository methods for all reads
- keep pagination metadata in `page`
- never return raw file paths
- return `ServiceResult(status="error")` with a structured payload for not found / invalid query / empty data / permission issues

- [ ] **Step 4: Re-run the service tests**

Run: `../.venv/bin/python -m pytest tests/unit/services/test_market_snapshot_query_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/market_snapshot_query_service.py api/schemas/market.py tests/unit/services/test_market_snapshot_query_service.py
git commit -m "feat(market): add snapshot query service"
```

## Task 2: UI Market Router Exposure

**Files:**
- Modify: `api/routers/ui/market.py`
- Test: `tests/api/routers/test_market_ui.py`
- Optional: create `tests/api/routers/test_market_snapshot_query_ui.py` if the existing file becomes too broad

- [ ] **Step 1: Write the failing API tests**

```python
@pytest.mark.asyncio
async def test_snapshot_list_detail_and_quality_endpoints(client):
    resp = await client.get("/api/ui/v1/market/snapshots", params={"trade_date": "2026-05-16", "market": "CN"})
    assert resp.status_code == 200
    assert "items" in resp.json()

    detail = await client.get("/api/ui/v1/market/snapshots/snap-001")
    assert detail.status_code == 200
    assert detail.json()["snapshot"]["snapshot_id"] == "snap-001"

    quality = await client.get("/api/ui/v1/market/snapshots/snap-001/quality")
    assert quality.status_code == 200
    assert quality.json()["overall_status"] in {"ok", "partial"}
```

```python
@pytest.mark.asyncio
async def test_snapshot_api_returns_structured_errors_for_invalid_query(client):
    resp = await client.get("/api/ui/v1/market/snapshots", params={"limit": 9999})
    assert resp.status_code == 422
    assert resp.json()["detail"][0]["type"] == "invalid_query"
```

- [ ] **Step 2: Run the tests and verify the router does not yet satisfy the new contract**

Run: `../.venv/bin/python -m pytest tests/api/routers/test_market_ui.py -v`
Expected: fail until the new endpoints and response mapping are added.

- [ ] **Step 3: Implement router endpoints and error mapping**

Routes to add:
- `GET /api/ui/v1/market/snapshots`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/sections`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/sections/{section}`
- `GET /api/ui/v1/market/datasets`
- `GET /api/ui/v1/market/datasets/{dataset_id}`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/quality`

Router rules:
- keep `verify_api_key`
- call `MarketSnapshotQueryService`
- translate service errors to HTTP 400 / 404 / 403 / 422 as appropriate
- keep existing `/symbols` and `/ohlcv` endpoints intact

- [ ] **Step 4: Re-run the API tests**

Run: `../.venv/bin/python -m pytest tests/api/routers/test_market_ui.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add api/routers/ui/market.py tests/api/routers/test_market_ui.py
git commit -m "feat(api): expose market snapshot query endpoints"
```

## Task 3: Documentation, TaskList, and Session Closeout

**Files:**
- Create: `docs/New-Web-Market-Snapshot-API.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `daily-sessions/2026-05-16.md`
- Modify: `daily-report/2026-05-16.md`

- [ ] **Step 1: Write the API doc**

Document:
- endpoint list
- supported filters: `trade_date`, `market`, `section`, `symbol`, `topic`, `quality_status`, pagination
- response shape for list/detail/quality/dataset
- error contract
- compatibility boundary: DB query source only, no file-path contract

- [ ] **Step 2: Update TaskList only after code and tests pass**

Mark `NW-V2-S2-005` completed only when:
- the service tests pass
- the router tests pass
- the API doc is written
- the response does not expose absolute paths

- [ ] **Step 3: Update daily session and daily report**

Write a short completion note that mentions:
- market snapshot query API endpoints added
- filters supported
- errors and pagination verified
- no CLI surface added

- [ ] **Step 4: Final verification**

Run:
- `../.venv/bin/python -m pytest tests/unit/services/test_market_snapshot_query_service.py tests/api/routers/test_market_ui.py -v`
- `git diff --check`

Expected:
- all tests pass
- no diff check failures

## Self-Review

### 1. Spec coverage
- Query list by `trade_date`, `market`, `quality_status`, pagination: Task 1 and Task 2
- Snapshot detail by `snapshot_id`: Task 1 and Task 2
- Section list/detail by `section`: Task 1 and Task 2
- Dataset list/detail by `dataset_id`: Task 1 and Task 2
- Quality report by `snapshot_id`: Task 1 and Task 2
- Structured errors for empty / invalid / missing / permission cases: Task 1 and Task 2
- API docs and TaskList sync: Task 3

### 2. Placeholder scan
- No `TBD`, `TODO`, or “implement later” text is used.
- Every task has exact file paths.
- Every code-changing step includes a concrete test or implementation sketch.

### 3. Type consistency
- The service methods used in router tests match the methods defined in Task 1.
- The response names are aligned across schema, service, and router:
  - `MarketSnapshotListResponse`
  - `MarketSnapshotDetailResponse`
  - `MarketSnapshotQualityResponse`
  - `MarketDatasetListResponse`
  - `MarketDatasetDetailResponse`
- Pagination fields are consistently called `limit`, `offset`, and `page`.

---
