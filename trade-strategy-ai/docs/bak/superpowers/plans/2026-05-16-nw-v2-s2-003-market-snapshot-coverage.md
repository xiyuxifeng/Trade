# NW-V2-S2-003 Market Snapshot Coverage Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `snapshot-build` into a structured Market Snapshot pipeline that covers the first batch of Kaipan-derived market sections, emits quality-aware artifacts, and stays extensible for future sections without redesigning the core schema.

**Architecture:** Keep `snapshot-build` as the canonical entry, but move the market snapshot shape to a dedicated schema with a section registry. Each section is built by a small builder that returns a standard `SectionSnapshot` object with explicit quality metadata, so new sections can be added by registering another builder instead of rewriting the pipeline. Preserve the current file-backed compatibility path for now; this task is about making the snapshot richer and more structured, not changing the storage/query architecture.

**Tech Stack:** Python, dataclasses / Pydantic-compatible models, pytest, existing Kaipan provider/service code, current `snapshot-build` job/artifact pipeline.

---

## First-Batch Section Scope

This task expands the snapshot with the most realistic high-value sections from `docs/kaipan.md` and the current codebase:

1. `overview`
   - Market sentiment
   - Market capacity
   - Indices
2. `limit_up_down`
   - 涨跌停总数
   - 涨停板统计
   - 涨停表现
   - 涨停信息
   - 涨停板列表 / 破板列表
   - 涨停原因 / 盘面亮点 / 大幅回撤
3. `sector_activity`
   - 板块涨停历史
   - 板块强度
   - 行业涨幅
   - 地区涨幅
   - 权重表现
4. `auction`
   - 竞价总体信息
   - 竞价数量统计
   - 竞价列表
   - 尾盘抢筹
   - 板块竞价
   - 板块内股票竞价
5. `ohlcv`
   - 日线行情 / 回灌摘要

Existing baseline sections remain part of the same schema and must continue to work:

- `hot_topics`
- `topic_constituents`
- `strong_symbols`
- `market_state`

Future sections such as `dragon_tiger`, `breadth`, `sentiment_detail`, `event_data`, `live_news`, and `new_high_trend` must be easy to register later without changing the core snapshot schema.

## First-Batch Source Mapping

This table maps the first batch of sections to the current codebase and `docs/kaipan.md` entry points. Some sources already exist as provider methods; others are intentionally represented as aggregate sections that can be partially filled at first.

| Section | Primary source in current codebase | `docs/kaipan.md` source categories | Notes |
|---|---|---|---|
| `overview` | `src/providers/kaipan_provider.py` + `src/services/persona_service.py` | 市场情绪 / 市场量能 / 指数数据 | Use existing provider methods where available; allow partial payload if any part is missing. |
| `limit_up_down` | `src/providers/kaipan_provider.py` | 涨跌停数总数 / 涨停板数量统计 / 涨停表现 / 涨停信息 / 涨停板列表 / 破板个股列表 / 涨停原因 / 盘面亮点 / 大幅回撤 | Aggregate multiple provider endpoints into one explanatory section. |
| `sector_activity` | `src/providers/kaipan_provider.py` | 板块涨停历史 / 板块强度 / 行业涨幅 / 地区涨幅 / 权重表现 | Already aligned with current provider methods such as `fetch_board_strength` and `fetch_industry_ranking`. |
| `auction` | `src/providers/kaipan_provider.py` | 竞价总体信息 / 竞价数量统计 / 竞价列表 / 尾盘抢筹 / 板块竞价 / 板块内股票竞价 | Start with the provider methods already exposed around `HisHomeDingPan` / `MorningBidding*`. |
| `ohlcv` | `src/market_data/service.py` + `src/services/job_runner.py` | 股票数据里的日线 / 区间统计相关内容 | Use the existing daily frame cache / market data fallback first, then later move to DB-backed query storage in `NW-V2-S2-004`. |
| `hot_topics` | `src/pipeline/tasks/snapshot_tasks.py` + `src/market_universe/snapshot_service.py` | 风口概念 / 题材数据 | Keep the current MarketUniverse path, but adapt its output to the new section format. |
| `topic_constituents` | `src/pipeline/tasks/snapshot_tasks.py` + `src/market_universe/snapshot_service.py` | 题材数据 / 涨停原因 / 板块内成分解释 | Keep existing topic constituent builder logic and add quality metadata. |
| `strong_symbols` | `src/pipeline/tasks/snapshot_tasks.py` + `src/market_universe/snapshot_service.py` | 风口概念 / 股票数据 / 盘面亮点 | Keep existing strong symbol selector logic and add quality metadata. |
| `market_state` | `src/services/persona_service.py` | 市场概览 / 盘面解释 | Treat this as an explanatory section that helps Job Detail and future UI explain the regime context. |

**Interface preconditions**

- New section builders should be able to read `config_path`, `profile_id`, `trade_date`, `slot`, `market`, and `offline` from a single build context.
- Section builders should return a standard `MarketSnapshotSection` whether the section is complete, partial, or missing.
- Missing sources must set `missing_reason` instead of failing the entire snapshot unless the section is explicitly marked required.

---

### Task 1: Define the Market Snapshot schema and section registry

**Files:**
- Create: `src/models/market_snapshot.py`
- Create: `src/services/market_snapshot_service.py`
- Create: `src/services/market_snapshot_registry.py`
- Test: `tests/unit/models/test_market_snapshot.py`
- Test: `tests/unit/services/test_market_snapshot_service.py`
- Test: `tests/unit/services/test_market_snapshot_registry.py`

**Target interfaces**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class MarketSnapshotSection:
    section_id: str
    provider: str | None
    source_time: datetime | None
    record_count: int
    missing_reason: str | None
    quality_status: str
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketSnapshot:
    snapshot_id: str
    trade_date: str
    market: str
    data_version: str
    provider_sources: list[str]
    created_at: datetime
    data_quality: dict[str, Any]
    sections: dict[str, MarketSnapshotSection]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketSnapshotBuildContext:
    config_path: str
    profile_id: str | None
    trade_date: str
    slot: str
    market: str = "CN"
    offline: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class MarketSnapshotSectionBuilder(Protocol):
    section_id: str

    def build(self, context: MarketSnapshotBuildContext) -> MarketSnapshotSection: ...
```

**Planned behavior**
- `MarketSnapshot` must be JSON-safe and easy to serialize into job results.
- `sections` must be a dictionary keyed by section id, so new sections can be added without modifying top-level fields.
- `MarketSnapshotSection` must always carry `provider`, `source_time`, `record_count`, `missing_reason`, and `quality_status`, even when the section is missing or partial.
- The registry must support:
  - registering a builder by `section_id`
  - enumerating enabled sections in deterministic order
  - looking up builders by `section_id`

- [ ] **Step 1: Write the failing tests**

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FakeBuilder:
    section_id: str

    def build(self, context):
        return MarketSnapshotSection(
            section_id=self.section_id,
            provider="fake",
            source_time=datetime(2026, 5, 16, 8, 0),
            record_count=1,
            missing_reason=None,
            quality_status="ok",
            payload={"section_id": self.section_id},
        )


def test_market_snapshot_serializes_sections():
    snapshot = MarketSnapshot(
        snapshot_id="snapshot-2026-05-16",
        trade_date="2026-05-16",
        market="CN",
        data_version="v1",
        provider_sources=["kaipan", "market"],
        created_at=datetime(2026, 5, 16, 8, 0),
        data_quality={"overall": "partial"},
        sections={
            "overview": MarketSnapshotSection(
                section_id="overview",
                provider="kaipan",
                source_time=datetime(2026, 5, 16, 8, 0),
                record_count=3,
                missing_reason=None,
                quality_status="ok",
                payload={"sentiment": 56, "capacity": 23417, "indices": []},
            ),
        },
    )

    data = snapshot.to_dict()
    assert data["snapshot_id"] == "snapshot-2026-05-16"
    assert data["sections"]["overview"]["quality_status"] == "ok"
    assert data["sections"]["overview"]["record_count"] == 3


def test_registry_can_register_and_resolve_builders():
    registry = MarketSnapshotRegistry()
    registry.register(FakeBuilder("overview"))

    builder = registry.get("overview")
    assert builder is not None
    assert builder.section_id == "overview"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../.venv/bin/python -m pytest tests/unit/models/test_market_snapshot.py tests/unit/services/test_market_snapshot_registry.py -q`

Expected: fail because `MarketSnapshot`, `MarketSnapshotSection`, and registry helpers are not implemented yet.

- [ ] **Step 3: Write the minimal implementation**

Implement the dataclasses and registry helpers above, plus `to_dict` / `model_dump` friendly conversion helpers if needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `../.venv/bin/python -m pytest tests/unit/models/test_market_snapshot.py tests/unit/services/test_market_snapshot_registry.py -q`

Expected: pass.

---

### Task 2: Implement the first-batch section builders from `docs/kaipan.md`

**Files:**
- Create: `src/services/market_snapshot_builders.py`
- Modify: `src/services/market_snapshot_service.py`
- Modify: `src/pipeline/tasks/snapshot_tasks.py`
- Modify: `src/services/snapshot_service.py`
- Test: `tests/unit/services/test_market_snapshot_builders.py`
- Test: `tests/unit/services/test_market_snapshot_service.py`
- Test: `tests/unit/services/test_snapshot_service.py`

**Planned builder set**

```python
SECTION_IDS = (
    "overview",
    "limit_up_down",
    "sector_activity",
    "auction",
    "ohlcv",
    "hot_topics",
    "topic_constituents",
    "strong_symbols",
    "market_state",
)
```

**Builder mapping**
- `overview`
  - Aggregate market sentiment, market capacity, and indices.
  - If one part is missing, the section stays `partial` and records the missing component in `missing_reason`.
- `limit_up_down`
  - Aggregate涨停/跌停相关信息 from the existing Kaipan provider methods that already exist in the repo, especially the methods around涨停原因、涨停信息、龙虎榜/破板相关数据.
- `sector_activity`
  - Aggregate板块强度、行业涨幅、地区涨幅、权重表现.
- `auction`
  - Aggregate盘前竞价和板块竞价相关数据.
- `ohlcv`
  - Use the existing OHLCV / market data fallback to produce a structured section summary.
- `hot_topics`, `topic_constituents`, `strong_symbols`
  - Keep the current MarketUniverse payloads, but make them emit the same `MarketSnapshotSection` shape.
- `market_state`
  - Reuse `PersonaService.build_market_state` output as an explanatory section so Job Detail and future UI can explain market regime context.

**Implementation rules**
- Do not add a second snapshot schema.
- Do not let each section write its own top-level artifact shape.
- Do not hard-code future section names into the orchestrator; register them.
- If a section cannot be built, return a `MarketSnapshotSection` with:
  - `quality_status="missing"` or `quality_status="partial"`
  - a specific `missing_reason`
  - `record_count=0`

- [ ] **Step 1: Write the failing tests**

```python
def test_overview_section_reports_missing_parts():
    result = build_overview_section(
        MarketSnapshotBuildContext(
            config_path="config/app.yaml",
            profile_id="default",
            trade_date="2026-05-16",
            slot="17-30",
        )
    )
    assert result.section_id == "overview"
    assert result.quality_status in {"partial", "missing"}
    assert result.record_count >= 0


def test_limit_up_down_section_uses_quality_metadata():
    result = build_limit_up_down_section(
        MarketSnapshotBuildContext(
            config_path="config/app.yaml",
            profile_id="default",
            trade_date="2026-05-16",
            slot="17-30",
        )
    )
    assert result.section_id == "limit_up_down"
    assert result.missing_reason is not None or result.quality_status == "ok"


def test_auction_section_records_count_and_provider():
    result = build_auction_section(
        MarketSnapshotBuildContext(
            config_path="config/app.yaml",
            profile_id="default",
            trade_date="2026-05-16",
            slot="09-25",
        )
    )
    assert result.section_id == "auction"
    assert result.provider in {"kaipan", "market", "unknown"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../.venv/bin/python -m pytest tests/unit/services/test_market_snapshot_builders.py tests/unit/services/test_snapshot_service.py -q`

Expected: fail because the section builders and adapter are not wired yet.

- [ ] **Step 3: Write the minimal implementation**

Implement the first-batch builders as small, focused functions that return `MarketSnapshotSection`.
Use the current Kaipan provider methods where they already exist:
- `fetch_board_strength`
- `fetch_industry_ranking`
- `fetch_pre_market_bid`
- `fetch_pre_market_stats`
- `fetch_limit_up_reason`
- `fetch_limit_up_info`
- `fetch_lhb_list`
- `fetch_hot_topics`
- `fetch_topic_constituents`
- `fetch_strong_symbols`

Keep `snapshot_tasks.py` as the current compatibility bridge for the existing three MarketUniverse sections and route them through the registry rather than duplicating serialization logic.

- [ ] **Step 4: Run tests to verify they pass**

Run: `../.venv/bin/python -m pytest tests/unit/services/test_market_snapshot_builders.py tests/unit/services/test_snapshot_service.py -q`

Expected: pass.

---

### Task 3: Wire `snapshot-build` to emit snapshot summary and quality report artifacts

**Files:**
- Modify: `src/services/market_snapshot_service.py`
- Modify: `src/services/snapshot_service.py`
- Modify: `src/services/job_runner.py`
- Modify: `src/pipelines/market_data_pipeline_spec.py`
- Modify: `src/services/job_registry.py` only if a new artifact kind needs to be registered there
- Test: `tests/unit/services/test_job_runner.py`
- Test: `tests/unit/pipelines/test_market_data_pipeline_spec.py`

**Output contract**

`snapshot-build` must return:
- `snapshot_id`
- `snapshot_summary_path`
- `quality_report_path`
- `snapshot_paths` or equivalent per-section output paths
- `results` / warnings that explain which sections were partial or missing

**Artifact kinds to declare**
- `snapshot-summary-json`
- `snapshot-quality-json`
- keep `snapshot-json` for the underlying snapshot payload

**Implementation rules**
- `snapshot_summary_json` should summarize:
  - snapshot_id
  - trade_date
  - market
  - data_version
  - section coverage
  - missing sections
- `quality_report_json` should capture:
  - section quality_status
  - record_count
  - missing_reason
  - provider list
- Job Detail must be able to show these artifacts without reading server paths directly.
- New sections must bind automatically through the registry, not with hand-written `if` blocks for each new section.

- [ ] **Step 1: Write the failing tests**

```python
import asyncio

from src.pipelines.market_data_pipeline_spec import MARKET_DATA_PIPELINE_SPEC
from src.services.snapshot_service import SnapshotService


def test_snapshot_build_returns_summary_and_quality_artifacts():
    snapshot_service = SnapshotService()
    result = asyncio.run(
        snapshot_service.build_snapshot(
        config_path="config/app.yaml",
        date="2026-05-16",
        slot="17-30",
        snapshot_type="all",
        force=False,
        offline=True,
        )
    )
    assert result.status in {"ok", "partial"}
    assert "snapshot_id" in result.payload
    assert "snapshot_summary_path" in result.payload
    assert "quality_report_path" in result.payload


def test_market_pipeline_spec_declares_snapshot_summary_artifact():
    kinds = [artifact.kind for artifact in MARKET_DATA_PIPELINE_SPEC.output_artifacts]
    assert "snapshot-summary-json" in kinds
    assert "snapshot-quality-json" in kinds
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `../.venv/bin/python -m pytest tests/unit/services/test_job_runner.py tests/unit/pipelines/test_market_data_pipeline_spec.py -q`

Expected: fail because the new artifacts are not yet emitted or declared.

- [ ] **Step 3: Write the minimal implementation**

Extend `snapshot_service.build_snapshot()` to aggregate the section registry output into:
- a stable `snapshot_id`
- a summary JSON artifact
- a quality report JSON artifact

Extend `JobRunner._bind_result_artifacts()` to bind the new artifact paths when present.

Update `market_data_pipeline_spec.py` so `snapshot-build` exposes the new artifacts in the spec and UI contract.

- [ ] **Step 4: Run tests to verify they pass**

Run: `../.venv/bin/python -m pytest tests/unit/services/test_job_runner.py tests/unit/pipelines/test_market_data_pipeline_spec.py -q`

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/models/market_snapshot.py src/services/market_snapshot_registry.py src/services/market_snapshot_builders.py src/services/snapshot_service.py src/services/job_runner.py src/pipeline/tasks/snapshot_tasks.py src/pipelines/market_data_pipeline_spec.py tests/unit/models/test_market_snapshot.py tests/unit/services/test_market_snapshot_registry.py tests/unit/services/test_market_snapshot_builders.py tests/unit/services/test_snapshot_service.py tests/unit/services/test_job_runner.py tests/unit/pipelines/test_market_data_pipeline_spec.py docs/New-Web-Market-Snapshot-Schema.md
git commit -m "feat(market): expand snapshot coverage"
```

---

## Extensibility Rules

Future sections must be addable by following this pattern:

1. Implement a new `MarketSnapshotSectionBuilder`.
2. Register it in the section registry with a stable `section_id`.
3. Add a test that checks `quality_status`, `missing_reason`, and `record_count`.
4. Update the snapshot schema docs if the section introduces new payload fields.

This means future work should not require:
- changing the top-level `MarketSnapshot` shape
- changing job orchestration logic
- changing UI contract for already existing sections

---

## Self-Review

- `NW-V2-S2-003` requirement coverage:
  - Expand snapshot data coverage: covered by Task 2 and Task 3.
  - Preserve structure for future sections: covered by registry-based builder interface.
  - Do not change query/storage architecture yet: preserved by scope.
  - Emit summary and quality artifacts: covered by Task 3.
- Placeholder scan:
  - No TBD / TODO placeholders.
  - Section names are explicit and aligned with `docs/kaipan.md`.
- Type consistency:
  - `MarketSnapshot`, `MarketSnapshotSection`, and `MarketSnapshotBuildContext` are the only new core types.
  - `section_id` is the canonical key across schema, registry, and artifacts.
