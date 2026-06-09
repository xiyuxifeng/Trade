# NW-V2-S2-006 Market Regime Feature Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于已落库的 Market Snapshot 生成、持久化并查询 market_regime_features，为 V3 的 regime-aware 能力提供可解释的 V2 派生数据。

**Architecture:** 只新增一条派生链：`Market Snapshot -> Market Regime Features -> DB/API/Artifact`。计算逻辑只读取现有快照的 sections/items/quality report，不重新抓 provider，也不引入第二套 snapshot 体系。服务层负责生成与落库，repository 负责查询，API 负责暴露给 UI，artifact 负责审计和回溯。

**Tech Stack:** Python, SQLAlchemy, Alembic, FastAPI, Pydantic, pytest, existing market snapshot repositories/services.

---

### Task 1: Define market regime feature model and DB migration

**Files:**
- Create: `src/models/market_regime.py`
- Create: `src/db/migrations/versions/2026_05_17_0001_add_market_regime_features_table.py`
- Modify: `src/models/__init__.py` if needed to export the new model

- [ ] **Step 1: Write the failing model and migration tests**

```python
def test_market_regime_feature_model_roundtrip():
    feature = MarketRegimeFeature(
        snapshot_id="snap-001",
        trade_date=date(2026, 5, 16),
        market="CN",
        feature_version="market-regime-features-v1",
        quality_status="partial",
        available_feature_count=6,
        partial_feature_count=2,
        missing_feature_count=1,
        feature_payload_json={"trend": {"value": "bullish"}},
        summary_json={"overall_status": "partial"},
        storage_ref={"snapshot_id": "snap-001"},
    )
    payload = feature.to_dict()
    assert payload["snapshot_id"] == "snap-001"
    assert payload["feature_version"] == "market-regime-features-v1"

def test_market_regime_feature_migration_creates_table():
    inspector = sa.inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("market_regime_features")}
    assert {"snapshot_id", "trade_date", "market", "feature_version", "feature_payload_json", "summary_json"}.issubset(columns)
    unique_constraints = inspector.get_unique_constraints("market_regime_features")
    assert any(constraint["name"] == "uq_market_regime_features_snapshot_feature_version" for constraint in unique_constraints)
```

- [ ] **Step 2: Run the model/migration tests and verify they fail**

Run: `python -m pytest tests/unit/models/test_market_regime.py tests/db/migrations/test_market_regime_features_migration.py -q`

Expected: FAIL because the model, repository, or migration is not yet implemented.

- [ ] **Step 3: Implement the model and migration**

```python
class MarketRegimeFeature(TimestampMixin, Base):
    __tablename__ = "market_regime_features"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "feature_version", name="uq_market_regime_features_snapshot_feature_version"),
        Index("ix_market_regime_features_trade_date_market", "trade_date", "market"),
        Index("ix_market_regime_features_feature_version", "feature_version"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False, default="CN")
    feature_version: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="partial")
    available_feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    partial_feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_payload_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
    storage_ref: Mapped[dict[str, Any]] = mapped_column(JSONVariant, default=dict, nullable=False)
```

The migration should create `market_regime_features` with the same columns and indexes, using the repo's existing Alembic style and PostgreSQL JSONB variants.

- [ ] **Step 4: Re-run the tests and verify they pass**

Run: `python -m pytest tests/unit/models/test_market_regime.py tests/db/migrations/test_market_regime_features_migration.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/models/market_regime.py src/db/migrations/versions/2026_05_17_0001_add_market_regime_features_table.py tests/unit/models/test_market_regime.py tests/db/migrations/test_market_regime_features_migration.py
git commit -m "feat(market): add regime feature model"
```

---

### Task 2: Implement market regime feature service and repository

**Files:**
- Create: `src/db/repositories/market_regime_feature_repository.py`
- Create: `src/services/market_regime_feature_service.py`
- Modify: `src/services/__init__.py`
- Modify: `src/services/market_snapshot_service.py` if helper reuse is needed
- Modify: `src/services/market_snapshot_query_service.py` only if it can safely reuse shared helper logic
- Test: `tests/unit/services/test_market_regime_feature_service.py`
- Test: `tests/unit/repositories/test_market_regime_feature_repository.py`

- [ ] **Step 1: Write the failing repository and service tests**

```python
async def test_build_market_regime_features_writes_artifact_and_db():
    result = await service.build_market_regime_features(snapshot_id="snap-001")
    assert result.status in {"ok", "partial"}
    assert result.payload["snapshot_id"] == "snap-001"
    assert result.payload["feature_version"] == "market-regime-features-v1"
    assert Path(result.payload["artifact_path"]).exists()

async def test_build_market_regime_features_returns_partial_when_sections_missing():
    result = await service.build_market_regime_features(snapshot_id="snap-002")
    assert result.status == "partial"
    assert result.payload["missing_feature_count"] > 0
    assert any(item["missing_reason"] for item in result.payload["features"].values())

async def test_repository_get_and_list_market_regime_features():
    detail = await repository.get_by_snapshot_id(session, "snap-001")
    assert detail is not None
    assert detail.snapshot_id == "snap-001"
    rows = await repository.list_features(session, trade_date=date(2026, 5, 16), market="CN", limit=10, offset=0)
    assert len(rows) >= 1
    assert rows[0].market == "CN"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python -m pytest tests/unit/services/test_market_regime_feature_service.py tests/unit/repositories/test_market_regime_feature_repository.py -q`

Expected: FAIL because the service/repository do not exist yet.

- [ ] **Step 3: Implement the repository and service**

```python
class MarketRegimeFeatureRepository:
    async def upsert_feature(self, session: AsyncSession, feature: MarketRegimeFeature) -> MarketRegimeFeature:
        """Insert or update a feature row keyed by snapshot_id + feature_version."""
        raise NotImplementedError

    async def get_by_snapshot_id(self, session: AsyncSession, snapshot_id: str) -> MarketRegimeFeature | None:
        """Load a single feature row by snapshot_id."""
        raise NotImplementedError

    async def list_features(self, session: AsyncSession, *, trade_date: date | None = None, market: str | None = None, limit: int | None = None, offset: int = 0) -> list[MarketRegimeFeature]:
        """List feature rows with pagination."""
        raise NotImplementedError

class MarketRegimeFeatureService(BaseService):
    async def build_market_regime_features(self, *, snapshot_id: str, feature_version: str = "market-regime-features-v1") -> ServiceResult:
        """Build, persist, and artifactize regime features for one snapshot."""
        raise NotImplementedError

    async def get_feature_detail(self, snapshot_id: str, feature_version: str | None = None) -> ServiceResult:
        """Fetch a single feature payload for one snapshot."""
        raise NotImplementedError

    async def list_features(self, *, trade_date: date | str | None = None, snapshot_id: str | None = None, market: str | None = None, limit: int = 50, offset: int = 0) -> ServiceResult:
        """List regime feature rows for API/UI consumption."""
        raise NotImplementedError
```

Service behavior must:
- read the snapshot through the existing snapshot repositories
- derive the 9 feature keys from existing sections/items
- mark missing keys with `value = null` and `missing_reason`
- compute `quality_status` from available vs missing features
- write a JSON artifact under `data/processed/market_regime_features/{trade_date}/{snapshot_id}/{feature_version}.json`
- persist the same payload into `market_regime_features`

- [ ] **Step 4: Re-run the service and repository tests**

Run: `python -m pytest tests/unit/services/test_market_regime_feature_service.py tests/unit/repositories/test_market_regime_feature_repository.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/db/repositories/market_regime_feature_repository.py src/services/market_regime_feature_service.py src/services/__init__.py tests/unit/services/test_market_regime_feature_service.py tests/unit/repositories/test_market_regime_feature_repository.py
git commit -m "feat(market): build regime feature service"
```

---

### Task 3: Expose market regime features through the UI API contract

**Files:**
- Modify: `api/routers/ui/market.py`
- Modify: `api/schemas/market.py`
- Modify: `src/services/market_snapshot_query_service.py` if the API can reuse list/detail helpers
- Modify: `src/services/__init__.py` if the new service is exported there
- Test: `tests/api/routers/test_market_ui.py`
- Test: `tests/unit/services/test_market_regime_feature_service.py` if API contract needs shared payload checks

- [ ] **Step 1: Write the failing API tests**

```python
async def test_market_regime_features_endpoints_return_feature_payload(client: AsyncClient):
    resp = await client.get("/api/ui/v1/market/regime-features", params={"trade_date": "2026-05-16", "market": "CN"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"]["total"] >= 0
    assert "items" in body

async def test_market_regime_feature_detail_endpoint_returns_404_for_missing_snapshot(client: AsyncClient):
    resp = await client.get("/api/ui/v1/market/snapshots/snap-missing/regime-features")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run the API tests and verify they fail**

Run: `python -m pytest tests/api/routers/test_market_ui.py -q`

Expected: FAIL because the endpoints are not implemented yet.

- [ ] **Step 3: Implement API schemas and routes**

```python
class MarketRegimeFeatureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    snapshot_id: str
    trade_date: str
    market: str
    feature_version: str
    quality_status: str
    available_feature_count: int
    partial_feature_count: int
    missing_feature_count: int
    created_at: str | None = None
    updated_at: str | None = None

class MarketRegimeFeatureListResponse(BaseModel):
    filters: dict[str, Any] = Field(default_factory=dict)
    page: MarketQueryPage
    items: list[MarketRegimeFeatureSummary] = Field(default_factory=list)
```

Add:
- `GET /api/ui/v1/market/regime-features`
- `GET /api/ui/v1/market/snapshots/{snapshot_id}/regime-features`

Map service errors consistently:
- `snapshot_not_found` -> 404
- `invalid_query` -> 422
- `partial_data` -> 206
- `empty_data` -> 404

- [ ] **Step 4: Re-run the API tests**

Run: `python -m pytest tests/api/routers/test_market_ui.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/routers/ui/market.py api/schemas/market.py src/services/market_snapshot_query_service.py tests/api/routers/test_market_ui.py
git commit -m "feat(api): expose market regime features"
```

---

### Task 4: Wire exports, docs, and task tracking

**Files:**
- Modify: `src/services/__init__.py`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md` if UI linkage needs an explicit completion note
- Create or modify: `docs/New-Web-Market-Regime-Features.md`
- Modify: `daily-sessions/2026-05-17.md`
- Modify: `daily-report/2026-05-17.md`

- [ ] **Step 1: Add any missing exports and documentation**

```python
from src.services.market_regime_feature_service import MarketRegimeFeatureService
```

Document:
- feature source sections
- partial behavior
- artifact path
- API endpoints

- [ ] **Step 2: Update TaskList state and daily records**

Mark `NW-V2-S2-006` as completed only after all tests pass and the API returns the correct contract.

Keep the daily records concise:
- one-line summary
- verification command
- next action

- [ ] **Step 3: Run the full targeted regression**

Run:

```bash
python -m pytest tests/unit/models/test_market_regime.py tests/unit/repositories/test_market_regime_feature_repository.py tests/unit/services/test_market_regime_feature_service.py tests/api/routers/test_market_ui.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/services/__init__.py docs/New-Web-Market-Regime-Features.md docs/New-Web-Linked-TaskLists/New-Web-TaskList.md docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md daily-sessions/2026-05-17.md daily-report/2026-05-17.md
git commit -m "docs(market): close regime feature task"
```

---

## Self-Review Notes

- The plan covers all spec requirements:
  - feature generation
  - missing_reason / partial semantics
  - DB persistence
  - repository queries
  - API exposure
  - artifact output
- No placeholder tasks remain.
- The implementation stays within the V2 boundary and does not add CLI surface or a second snapshot system.
