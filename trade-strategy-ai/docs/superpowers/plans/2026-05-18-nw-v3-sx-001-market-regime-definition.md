# NW-V3-SX-001 Market Regime Definition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Market Regime 从 Demo 式临时判断升级为面向 Web 最终交付的 canonical 市场状态事实源，支持可解释、可版本化、多标签、可回测复现的 regime 输出，并让 Web UI 可直接查看。

**Architecture:** 先固化 regime 的数据契约，再实现纯规则判定层，最后把结果暴露给 API 和现有 `market-browser` UI。实现顺序必须沿着 `Market Snapshot -> Market Regime Features -> Market Regime -> API/UI` 单向推进，不新增第二套事实源，不让前端参与计算，不从 provider 直接重抓数据。

**Tech Stack:** Python 3.11, SQLAlchemy 2.x, Alembic, Pydantic, FastAPI, pytest, React, TanStack Query, TypeScript.

---

### Task 1: Canonical Regime Schema and Persistence

**Files:**
- Create: `src/models/market_regime_record.py`
- Create: `src/db/repositories/market_regime_repository.py`
- Create: `src/db/migrations/versions/2026_05_18_0001_add_market_regimes_table.py`
- Modify: `src/db/repositories/__init__.py`
- Modify: `src/services/__init__.py`
- Modify: `tests/unit/db/test_migrations.py`
- Create: `tests/unit/models/test_market_regime_record.py`
- Create: `tests/unit/db/test_market_regime_repository.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/models/test_market_regime_record.py`
```python
from datetime import date, datetime, UTC

from src.models.market_regime_record import MarketRegimeRecord, RegimeLabelRecord, RegimeFeatureRecord


def test_market_regime_record_dump_contains_versioned_labels():
    record = MarketRegimeRecord(
        regime_id="regime-001",
        trade_date=date(2026, 5, 16),
        snapshot_id="snap-001",
        market="CN",
        regime_version="market-regime-v1",
        source_feature_version="market-regime-features-v1",
        primary_label="weak_bull",
        labels=[
            RegimeLabelRecord(
                label="weak_bull",
                label_type="primary",
                score=0.72,
                confidence=0.81,
                status="active",
                evidence=[],
                reason="trend positive but breadth incomplete",
            )
        ],
        features=[
            RegimeFeatureRecord(
                feature_key="trend",
                raw_value={"ret_20d": 0.08},
                normalized_value=0.8,
                source_section="overview",
                source_field="trend",
                source_version="market-regime-features-v1",
                confidence=0.9,
                weight=0.3,
                missing_reason=None,
            )
        ],
        confidence=0.81,
        quality_status="ok",
        missing_reason=None,
        created_at=datetime.now(UTC),
    )

    dumped = record.to_dict()
    assert dumped["primary_label"] == "weak_bull"
    assert dumped["source_feature_version"] == "market-regime-features-v1"
    assert dumped["labels"][0]["label"] == "weak_bull"
    assert dumped["features"][0]["feature_key"] == "trend"
```

`tests/unit/db/test_market_regime_repository.py`
```python
from datetime import date

import pytest

from src.db.repositories.market_regime_repository import MarketRegimeRepository
from src.models.market_regime_record import MarketRegimeRecord


@pytest.mark.asyncio()
async def test_upsert_and_get_market_regime(market_data_session_factory):
    repo = MarketRegimeRepository()
    async with market_data_session_factory() as session:
        record = MarketRegimeRecord(
            regime_id="regime-001",
            trade_date=date(2026, 5, 16),
            snapshot_id="snap-001",
            market="CN",
            regime_version="market-regime-v1",
            source_feature_version="market-regime-features-v1",
            primary_label="weak_bull",
            labels=[],
            features=[],
            confidence=0.81,
            quality_status="ok",
            missing_reason=None,
        )
        saved = await repo.upsert_regime(session, record)
        await session.commit()

        fetched = await repo.get_by_snapshot_and_version(session, "snap-001", "market-regime-v1")

    assert saved.regime_id == "regime-001"
    assert fetched is not None
    assert fetched.snapshot_id == "snap-001"
```

`tests/unit/db/test_migrations.py`
```python
from pathlib import Path


def test_market_regimes_migration_defines_expected_schema() -> None:
    migration_file = (
        Path(__file__).parent.parent.parent.parent
        / "src/db/migrations/versions/2026_05_18_0001_add_market_regimes_table.py"
    )
    content = migration_file.read_text(encoding="utf-8")

    assert "revision = \"2026_05_18_0001\"" in content
    assert "market_regimes" in content
    assert "uq_market_regimes_snapshot_regime_version" in content
    assert "source_feature_version" in content
    assert "primary_label" in content
    assert "labels_json" in content or "labels" in content
    assert "features_json" in content or "features" in content
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pytest tests/unit/models/test_market_regime_record.py tests/unit/db/test_market_regime_repository.py tests/unit/db/test_migrations.py -v
```

Expected:
- Fails because `MarketRegimeRecord`, `RegimeLabelRecord`, `RegimeFeatureRecord`, `MarketRegimeRepository`, and the migration file do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement the exact schema as SQLAlchemy ORM + JSON payloads in `src/models/market_regime_record.py`:

```python
class MarketRegimeRecord(TimestampMixin, Base):
    __tablename__ = "market_regimes"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "regime_version", name="uq_market_regimes_snapshot_regime_version"),
        Index("ix_market_regimes_trade_date_market", "trade_date", "market"),
        Index("ix_market_regimes_snapshot_id", "snapshot_id"),
        Index("ix_market_regimes_regime_version", "regime_version"),
    )
```

The record must expose:

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "regime_id": self.regime_id,
        "trade_date": self.trade_date.isoformat(),
        "snapshot_id": self.snapshot_id,
        "market": self.market,
        "regime_version": self.regime_version,
        "source_feature_version": self.source_feature_version,
        "primary_label": self.primary_label,
        "labels": [label.to_dict() for label in self.labels_json],
        "features": [feature.to_dict() for feature in self.features_json],
        "confidence": self.confidence,
        "quality_status": self.quality_status,
        "missing_reason": self.missing_reason,
        "storage_ref": self.storage_ref,
        "created_at": self.created_at.isoformat() if self.created_at else None,
        "updated_at": self.updated_at.isoformat() if self.updated_at else None,
    }
```

Implement `MarketRegimeRepository` with:

```python
async def upsert_regime(self, session: AsyncSession, regime: MarketRegimeRecord) -> MarketRegimeRecord: ...
async def get_by_snapshot_and_version(self, session: AsyncSession, snapshot_id: str, regime_version: str) -> MarketRegimeRecord | None: ...
async def list_regimes(self, session: AsyncSession, *, trade_date: date | None = None, snapshot_id: str | None = None, market: str | None = None, regime_version: str | None = None, limit: int | None = None, offset: int = 0) -> list[MarketRegimeRecord]: ...
async def count_regimes(self, session: AsyncSession, *, trade_date: date | None = None, snapshot_id: str | None = None, market: str | None = None, regime_version: str | None = None) -> int: ...
```

Create the Alembic migration for `market_regimes` with the same columns and indexes as the ORM model, plus a foreign key to `market_snapshots.snapshot_id`.

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
pytest tests/unit/models/test_market_regime_record.py tests/unit/db/test_market_regime_repository.py tests/unit/db/test_migrations.py -v
```

Expected:
- PASS

- [ ] **Step 5: Commit**

```bash
git add src/models/market_regime_record.py src/db/repositories/market_regime_repository.py src/db/migrations/versions/2026_05_18_0001_add_market_regimes_table.py src/db/repositories/__init__.py src/services/__init__.py tests/unit/models/test_market_regime_record.py tests/unit/db/test_market_regime_repository.py tests/unit/db/test_migrations.py
git commit -m "feat: add canonical market regime record"
```

---

### Task 2: Regime Scoring Service and Artifact Builder

**Files:**
- Create: `src/services/market_regime_rules.py`
- Create: `src/services/market_regime_service.py`
- Modify: `src/services/__init__.py`
- Modify: `src/lib/api/` is not needed in this task
- Create: `tests/unit/services/test_market_regime_rules.py`
- Create: `tests/unit/services/test_market_regime_service.py`

- [ ] **Step 1: Write the failing tests**

`tests/unit/services/test_market_regime_rules.py`
```python
def test_score_primary_label_strong_bull():
    features = {
        "trend": {"value": {"ret_20d": 0.11, "ret_5d": 0.04}, "confidence": 0.9},
        "breadth": {"value": {"up_ratio": 0.68}, "confidence": 0.88},
        "volatility": {"value": "mid", "confidence": 0.8},
        "liquidity": {"value": "good", "confidence": 0.85},
        "turnover_level": {"value": "high", "confidence": 0.8},
    }

    result = score_market_regime(features, regime_version="market-regime-v1")

    assert result.primary_label == "strong_bull"
    assert any(label.label == "strong_bull" for label in result.labels)
    assert result.quality_status == "ok"
    assert result.confidence > 0.7
```

```python
def test_score_market_regime_marks_partial_when_key_features_missing():
    features = {
        "trend": {"value": None, "missing_reason": "missing benchmark window", "confidence": 0.0},
        "breadth": {"value": None, "missing_reason": "missing breadth ratio", "confidence": 0.0},
        "volatility": {"value": "unknown", "confidence": 0.2},
    }

    result = score_market_regime(features, regime_version="market-regime-v1")

    assert result.quality_status in {"partial", "low_confidence"}
    assert result.primary_label in {"range", "weak_bear", "panic"}
    assert result.missing_reason is not None
```

`tests/unit/services/test_market_regime_service.py`
```python
import pytest
from datetime import date
from types import SimpleNamespace

from src.services.market_regime_service import MarketRegimeService


class FakeSnapshotRepository:
    async def get_by_snapshot_id(self, session, snapshot_id: str):
        return SimpleNamespace(snapshot_id=snapshot_id, trade_date=date(2026, 5, 16), market="CN")


class FakeFeatureRepository:
    async def get_by_snapshot_and_version(self, session, snapshot_id: str, feature_version: str):
        return SimpleNamespace(
            snapshot_id=snapshot_id,
            trade_date=date(2026, 5, 16),
            market="CN",
            feature_version=feature_version,
            quality_status="ok",
            feature_payload_json={
                "trend": {
                    "feature_key": "trend",
                    "value": {"ret_20d": 0.11},
                    "source_section": "overview",
                    "confidence": 0.9,
                    "missing_reason": None,
                },
                "breadth": {
                    "feature_key": "breadth",
                    "value": {"up_ratio": 0.68},
                    "source_section": "overview",
                    "confidence": 0.9,
                    "missing_reason": None,
                },
                "volatility": {
                    "feature_key": "volatility",
                    "value": "mid",
                    "source_section": "market_state",
                    "confidence": 0.8,
                    "missing_reason": None,
                },
                "liquidity": {
                    "feature_key": "liquidity",
                    "value": "good",
                    "source_section": "market_state",
                    "confidence": 0.8,
                    "missing_reason": None,
                },
                "turnover_level": {
                    "feature_key": "turnover_level",
                    "value": "high",
                    "source_section": "market_state",
                    "confidence": 0.8,
                    "missing_reason": None,
                },
            },
            summary_json={"source_sections": ["overview", "market_state"]},
            storage_ref={"source": "db"},
            to_dict=lambda: {},
        )


@pytest.mark.asyncio()
async def test_build_market_regime_uses_feature_snapshot_and_persists_artifact(tmp_path):
    service = MarketRegimeService(
        feature_repository=FakeFeatureRepository(),
        snapshot_repository=FakeSnapshotRepository(),
        artifact_root=tmp_path,
    )

    result = await service.build_market_regime(
        snapshot_id="snap-001",
        regime_version="market-regime-v1",
        feature_version="market-regime-features-v1",
    )

    assert result.status in {"ok", "partial"}
    assert result.payload["regime"]["snapshot_id"] == "snap-001"
    assert result.payload["regime"]["regime_version"] == "market-regime-v1"
    assert result.payload["artifact_ref"]["artifact_type"] == "market-regime-json"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pytest tests/unit/services/test_market_regime_rules.py tests/unit/services/test_market_regime_service.py -v
```

Expected:
- Fails because `score_market_regime()` and `MarketRegimeService` are not implemented yet.

- [ ] **Step 3: Write the minimal implementation**

`src/services/market_regime_rules.py` should contain pure, testable functions only:

```python
def score_market_regime(features: dict[str, Any], *, regime_version: str) -> MarketRegimeEvaluation:
    primary_label = determine_primary_label(features)
    labels = build_labels(features, primary_label)
    confidence = compute_confidence(features, labels)
    quality_status = determine_quality_status(features, confidence)
    return MarketRegimeEvaluation(...)
```

Scoring rules must:

1. Use the versioned feature payload from `market_regime_features`.
2. Derive a primary label from trend, breadth, volatility, liquidity, and risk.
3. Add structural labels for `theme_hot` and `low_liquidity`.
4. Emit evidence for each label.
5. Compute confidence from signal consistency, feature completeness, and boundary distance.

`src/services/market_regime_service.py` should:

1. Read the snapshot and the latest or requested feature version.
2. Call the pure scoring helper.
3. Persist the final record through `MarketRegimeRepository`.
4. Write a JSON artifact to:

```text
data/processed/market_regimes/{trade_date}/{snapshot_id}/{regime_version}.json
```

5. Return a `ServiceResult` with `regime`, `artifact_ref`, and `warnings`.

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
pytest tests/unit/services/test_market_regime_rules.py tests/unit/services/test_market_regime_service.py -v
```

Expected:
- PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/market_regime_rules.py src/services/market_regime_service.py src/services/__init__.py tests/unit/services/test_market_regime_rules.py tests/unit/services/test_market_regime_service.py
git commit -m "feat: derive canonical market regime from snapshot features"
```

---

### Task 3: API Contract and Web Client

**Files:**
- Modify: `api/schemas/market.py`
- Modify: `api/routers/ui/market.py`
- Create: `tests/api/routers/test_market_regime_api.py`
- Modify: `web/src/lib/api/market.ts`
- Modify: `web/src/types/market.ts`
- Modify: `web/src/lib/api/market.test.ts`

- [ ] **Step 1: Write the failing tests**

`tests/api/routers/test_market_regime_api.py`
```python
@pytest.mark.asyncio()
async def test_get_market_regime_detail(client: AsyncClient) -> None:
    response = await client.get("/api/ui/v1/market/snapshots/snap-001/regime?regime_version=market-regime-v1")

    assert response.status_code == 200
    body = response.json()
    assert body["regime"]["snapshot_id"] == "snap-001"
    assert body["regime"]["primary_label"] in {"strong_bull", "weak_bull", "range", "weak_bear", "panic"}
    assert "labels" in body["regime"]
```

```python
@pytest.mark.asyncio()
async def test_list_market_regimes(client: AsyncClient) -> None:
    response = await client.get("/api/ui/v1/market/regimes?trade_date=2026-05-16&market=CN")

    assert response.status_code == 200
    body = response.json()
    assert body["page"]["count"] >= 0
```

`web/src/lib/api/market.test.ts`
```typescript
import { describe, expect, it, vi } from 'vitest';
import { getMarketRegime, listMarketRegimes } from '@/lib/api/market';

describe('market api client', () => {
  it('builds regime urls', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } })));

    await listMarketRegimes({ tradeDate: '2026-05-16', market: 'CN', regimeVersion: 'market-regime-v1' });
    await getMarketRegime('snap-001', 'market-regime-v1');

    const calls = vi.mocked(fetch).mock.calls.map(([url]) => String(url));
    expect(calls).toContain('/api/ui/v1/market/regimes?trade_date=2026-05-16&market=CN&regime_version=market-regime-v1');
    expect(calls).toContain('/api/ui/v1/market/snapshots/snap-001/regime?regime_version=market-regime-v1');
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pytest tests/api/routers/test_market_regime_api.py -v
pnpm vitest run web/src/lib/api/market.test.ts
```

Expected:
- API test fails because the new regime endpoints do not exist yet.
- Frontend test fails because the new client functions do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Add Pydantic response schemas in `api/schemas/market.py`:

```python
class MarketRegimeLabel(BaseModel): ...
class MarketRegimeFeature(BaseModel): ...
class MarketRegimeSummary(BaseModel): ...
class MarketRegimeDetailResponse(BaseModel): ...
class MarketRegimeListResponse(BaseModel): ...
```

Add FastAPI routes in `api/routers/ui/market.py`:

```python
@router.get("/regimes", response_model=MarketRegimeListResponse)
async def list_market_regimes(...): ...

@router.get("/snapshots/{snapshot_id}/regime", response_model=MarketRegimeDetailResponse)
async def get_market_regime(...): ...
```

Update the web client in `web/src/lib/api/market.ts`:

```typescript
export function listMarketRegimes(params = {}) { ... }
export function getMarketRegime(snapshotId: string, regimeVersion?: string) { ... }
```

Update `web/src/types/market.ts` with the new regime response types so the UI can render `primary_label`, `labels`, `features`, `confidence`, `quality_status`, and `missing_reason` without `any`.

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
pytest tests/api/routers/test_market_regime_api.py -v
pnpm vitest run web/src/lib/api/market.test.ts
```

Expected:
- PASS

- [ ] **Step 5: Commit**

```bash
git add api/schemas/market.py api/routers/ui/market.py tests/api/routers/test_market_regime_api.py web/src/lib/api/market.ts web/src/types/market.ts web/src/lib/api/market.test.ts
git commit -m "feat: expose canonical market regime api"
```

---

### Task 4: Market Regime Viewer in the Existing Market Browser

**Files:**
- Modify: `web/src/features/market-browser/market-snapshot-browser-shell.tsx`
- Modify: `web/src/features/market-browser/market-snapshot-browser-detail.tsx`
- Modify: `web/src/features/market-browser/market-snapshot-browser-regime-features.tsx`
- Modify: `web/src/pages/market/index.tsx`
- Modify: `web/src/pages/market/index.test.tsx`
- Modify: `web/src/features/market-browser/market-snapshot-browser-detail.tsx`
- Modify: `web/src/features/market-browser/market-snapshot-browser-regime-features.tsx`
- Create: `web/src/features/market-browser/market-snapshot-browser-regime.test.tsx`

- [ ] **Step 1: Write the failing tests**

`web/src/features/market-browser/market-snapshot-browser-regime.test.tsx`
```tsx
import { renderWithRouter } from '@/test/test-utils';
import { screen } from '@testing-library/react';
import { MarketPage } from '@/pages/market';

it('shows primary label, labels, confidence, and evidence', async () => {
  renderWithRouter([{ path: '/market', element: <MarketPage /> }], ['/market?snapshot_id=snap-001&trade_date=2026-05-16&market=CN']);

  expect(await screen.findByText('Market Regime')).toBeInTheDocument();
  expect(await screen.findByText('weak_bull')).toBeInTheDocument();
  expect(screen.getByText('confidence')).toBeInTheDocument();
});
```

`web/src/pages/market/index.test.tsx`
```tsx
expect(await screen.findByText('Market Regime')).toBeInTheDocument();
expect(screen.getByText('labels')).toBeInTheDocument();
expect(screen.getByText('missing_reason')).toBeInTheDocument();
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
```bash
pnpm vitest run web/src/features/market-browser/market-snapshot-browser-regime.test.tsx web/src/pages/market/index.test.tsx
```

Expected:
- Fails because the market browser still only renders regime features, not the canonical regime viewer.

- [ ] **Step 3: Write the minimal implementation**

Extend `web/src/features/market-browser/market-snapshot-browser-shell.tsx` so it queries the new regime endpoints alongside the existing feature endpoints. Keep the existing snapshot/detail/quality flow intact.

Add a dedicated `MarketRegime` panel in `web/src/features/market-browser/market-snapshot-browser-detail.tsx` that renders:

1. `primary_label`
2. `labels`
3. `confidence`
4. `quality_status`
5. `missing_reason`
6. label-level evidence

Keep the existing `Market Regime Features` panel below it so the page remains a single browser for both the derived feature layer and the final regime layer.

If a dedicated subcomponent is needed for readability, create:

```text
web/src/features/market-browser/market-regime-panel.tsx
```

and keep it presentation-only.

- [ ] **Step 4: Run the tests to verify they pass**

Run:
```bash
pnpm vitest run web/src/features/market-browser/market-snapshot-browser-regime.test.tsx web/src/pages/market/index.test.tsx
```

Expected:
- PASS

- [ ] **Step 5: Commit**

```bash
git add web/src/features/market-browser/market-snapshot-browser-shell.tsx web/src/features/market-browser/market-snapshot-browser-detail.tsx web/src/features/market-browser/market-snapshot-browser-regime-features.tsx web/src/features/market-browser/market-snapshot-browser-regime.test.tsx web/src/pages/market/index.tsx web/src/pages/market/index.test.tsx
git commit -m "feat: add canonical market regime viewer"
```

---

## Self-Review

### 1. Spec coverage

- 字段定义：覆盖了 `MarketRegimeRecord`、标签、特征、证据。
- 规则设计：覆盖了分层打分、硬门槛兜底、置信度、版本化。
- 标准定义：覆盖了主状态、结构标签、质量状态。
- 数据清单：覆盖了现有数据、缺失数据、必须补数据与优先级。
- Web 交付：覆盖了 API contract 和现有 `market-browser` UI。

### 2. Placeholder scan

- 没有使用 `TBD`、`TODO`、`implement later` 之类占位语。
- 每个 task 都给出了具体文件、具体测试、具体命令和具体预期。

### 3. Type consistency

- `MarketRegimeRecord` / `RegimeLabelRecord` / `RegimeFeatureRecord` 在 schema、repo、service、API 和 UI 里保持同一套命名。
- `regime_version` 与 `source_feature_version` 在所有层保持一致。
- API 路径统一使用：
  - `/api/ui/v1/market/regimes`
  - `/api/ui/v1/market/snapshots/{snapshot_id}/regime`

### 4. Gaps

- UI-V3-010 已包含在本计划中，因为现有 `market-browser` 已经承载了 regime features，并且扩展到 canonical regime viewer 是同一条交付链。
- 如果后续实现时发现前端只需要展示而不需要新增列表查询，可以把 Task 4 再拆成“数据接入”和“展示组件”两个更细的子任务。
