# NW-V2-S2-004 Market Data DB Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将市场数据从“文件为主的事实源”收敛为“数据库为主的查询源”，保留文件导出/调试/归档兼容层，并为后续 Web 查询与外部系统接入提供稳定的数据模型。

**Architecture:** 采用现有 SQLAlchemy async + Alembic migration + Repository 模式，新增统一的 market data 主表、section 表、item 表、dataset 表和质量报告表。`snapshot-build` 继续作为 Web/Job 体系内的编排入口，新的持久化逻辑放在服务层和 repository 层，不在 Router 或 CLI 里拼接业务逻辑。

**Tech Stack:** SQLAlchemy async、Alembic、JSONB、现有 `JobService` / `JobRunner` / `ArtifactService` / `MarketSnapshotService` / `MarketService`、pytest、sqlite async 测试数据库。

---

## Scope Check

这份计划只覆盖 `NW-V2-S2-004` 的 DB 存储与查询底座：

- 建表
- ORM 模型
- Repository
- 持久化写入服务
- 基础查询服务
- artifact 元数据收敛
- 测试与文档

不覆盖：

- `NW-V2-S2-005` 对外查询 API
- `UI-V2-010` / `UI-V2-011` 页面
- 新 CLI 产品入口
- 完整回测 / rule selection

---

## File Map

### New files

- `src/models/market_data_snapshot.py`
- `src/models/market_data_snapshot_section.py`
- `src/models/market_data_snapshot_item.py`
- `src/models/market_dataset.py`
- `src/models/market_data_quality_report.py`
- `src/db/repositories/market_snapshot_repository.py`
- `src/db/repositories/market_snapshot_section_repository.py`
- `src/db/repositories/market_snapshot_item_repository.py`
- `src/db/repositories/market_dataset_repository.py`
- `src/db/repositories/market_data_quality_repository.py`
- `src/services/market_data_storage_service.py`
- `tests/unit/models/test_market_data_snapshot_models.py`
- `tests/unit/db/repositories/test_market_data_repositories.py`
- `tests/unit/services/test_market_data_storage_service.py`
- `docs/New-Web-Market-Data-Storage.md`
- `src/db/migrations/versions/2026_05_16_0002_create_market_data_storage_tables.py`

### Modify files

- `src/models/base.py` only if a shared helper or naming convention is required
- `src/models/__init__.py`
- `src/db/repositories/__init__.py`
- `src/services/snapshot_service.py`
- `src/services/market_snapshot_service.py`
- `src/services/job_runner.py`
- `src/services/__init__.py`
- `src/services/artifact_service.py` only if safe metadata exposure needs a small adjustment
- `src/pipelines/market_data_pipeline_spec.py` only if the DB artifact contract needs to be surfaced
- `tests/unit/services/test_market_snapshot_service.py` if DB write metadata affects snapshot service behavior
- `tests/unit/services/test_job_runner.py` if artifact bindings need a regression assertion
- `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- `daily-sessions/2026-05-16.md`
- `daily-report/2026-05-16.md`

---

## Task 1: Define Market Data ORM Models

**Files:**
- Create: `src/models/market_data_snapshot.py`
- Create: `src/models/market_data_snapshot_section.py`
- Create: `src/models/market_data_snapshot_item.py`
- Create: `src/models/market_dataset.py`
- Create: `src/models/market_data_quality_report.py`
- Modify: `src/models/__init__.py`
- Test: `tests/unit/models/test_market_data_snapshot_models.py`

- [ ] **Step 1: Write the failing tests**

Write tests that assert:
- `market_snapshots` has the expected identity fields and unique constraint on `snapshot_id`
- `market_snapshot_sections` has unique `(snapshot_id, section_id)`
- `market_snapshot_items` exposes `symbol`, `section_id`, `dataset_id`, `payload_json`
- `market_datasets` exposes `dataset_id` and `snapshot_id`
- `market_data_quality_reports` exposes `overall_status` and JSON report fields

Run:
```bash
../.venv/bin/python -m pytest tests/unit/models/test_market_data_snapshot_models.py -v
```
Expected: fail because models do not exist yet.

- [ ] **Step 2: Implement the minimal ORM models**

Implement SQLAlchemy ORM classes using the existing `Base` and `TimestampMixin` pattern. Prefer JSON/JSONB hybrid columns where needed. Keep the models focused:

```python
class MarketSnapshot(TimestampMixin, Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_id", name="uq_market_snapshots_snapshot_id"),
        Index("ix_market_snapshots_trade_date_market", "trade_date", "market"),
        Index("ix_market_snapshots_profile_trade_date", "profile_id", "trade_date"),
    )
    ...
```

Use the same style for section/item/dataset/quality report models.

- [ ] **Step 3: Run the model tests**

Run:
```bash
../.venv/bin/python -m pytest tests/unit/models/test_market_data_snapshot_models.py -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/models/market_data_snapshot.py src/models/market_data_snapshot_section.py src/models/market_data_snapshot_item.py src/models/market_dataset.py src/models/market_data_quality_report.py src/models/__init__.py tests/unit/models/test_market_data_snapshot_models.py
git commit -m "feat(market-data): add storage orm models"
```

---

## Task 2: Add Alembic Migration

**Files:**
- Create: `src/db/migrations/versions/2026_05_16_0002_create_market_data_storage_tables.py`
- Test: `tests/unit/db/repositories/test_market_data_repositories.py`

- [ ] **Step 1: Write the failing repository tests**

Write a repository-level test that creates tables, inserts a snapshot, section, item, dataset, and quality report, then queries them back through the repository layer.

Run:
```bash
../.venv/bin/python -m pytest tests/unit/db/repositories/test_market_data_repositories.py -v
```
Expected: fail because tables/migration/repositories are not available.

- [ ] **Step 2: Implement the migration**

Add one migration that creates:
- `market_snapshots`
- `market_snapshot_sections`
- `market_snapshot_items`
- `market_datasets`
- `market_data_quality_reports`

Make sure:
- foreign keys point from section/item/report/dataset to `market_snapshots`
- indexes match the query plan in the spec
- rollback drops tables in reverse order

- [ ] **Step 3: Run migration-oriented tests**

Run:
```bash
../.venv/bin/python -m pytest tests/unit/db/repositories/test_market_data_repositories.py -v
```
Expected: PASS after repositories are added in later tasks.

- [ ] **Step 4: Commit**

```bash
git add src/db/migrations/versions/2026_05_16_0002_create_market_data_storage_tables.py tests/unit/db/repositories/test_market_data_repositories.py
git commit -m "feat(market-data): add storage migration"
```

---

## Task 3: Implement Repositories

**Files:**
- Create: `src/db/repositories/market_snapshot_repository.py`
- Create: `src/db/repositories/market_snapshot_section_repository.py`
- Create: `src/db/repositories/market_snapshot_item_repository.py`
- Create: `src/db/repositories/market_dataset_repository.py`
- Create: `src/db/repositories/market_data_quality_repository.py`
- Modify: `src/db/repositories/__init__.py`
- Test: `tests/unit/db/repositories/test_market_data_repositories.py`

- [ ] **Step 1: Write failing repository tests**

Cover the required repository queries:
- by `snapshot_id`
- by `trade_date`
- by `symbol`
- by `section`
- by `dataset_id`

Include one test that verifies duplicate snapshot writes do not create duplicate rows.

Run:
```bash
../.venv/bin/python -m pytest tests/unit/db/repositories/test_market_data_repositories.py -v
```
Expected: fail until repository classes exist.

- [ ] **Step 2: Implement repository methods**

Each repository should only own one responsibility. Keep SQL in the repository layer and keep service code thin.

Example method set:
```python
class MarketSnapshotRepository:
    async def upsert_snapshot(self, session: AsyncSession, snapshot: MarketSnapshot) -> MarketSnapshot: ...
    async def get_by_snapshot_id(self, session: AsyncSession, snapshot_id: str) -> MarketSnapshot | None: ...
    async def list_by_trade_date(self, session: AsyncSession, trade_date: date, market: str | None = None) -> list[MarketSnapshot]: ...
```

- [ ] **Step 3: Run repository tests**

Run:
```bash
../.venv/bin/python -m pytest tests/unit/db/repositories/test_market_data_repositories.py -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/db/repositories/market_snapshot_repository.py src/db/repositories/market_snapshot_section_repository.py src/db/repositories/market_snapshot_item_repository.py src/db/repositories/market_dataset_repository.py src/db/repositories/market_data_quality_repository.py src/db/repositories/__init__.py tests/unit/db/repositories/test_market_data_repositories.py
git commit -m "feat(market-data): add repositories"
```

---

## Task 4: Add Market Data Storage Service

**Files:**
- Create: `src/services/market_data_storage_service.py`
- Modify: `src/services/market_snapshot_service.py`
- Modify: `src/services/snapshot_service.py`
- Modify: `src/services/__init__.py`
- Test: `tests/unit/services/test_market_data_storage_service.py`
- Test: `tests/unit/services/test_market_snapshot_service.py`

- [ ] **Step 1: Write the failing service tests**

Write tests that assert:
- a structured Market Snapshot can be persisted to DB
- sections are stored independently
- items are stored with `payload_json`
- quality report is stored
- repeated writes are idempotent for the same `snapshot_id`

Run:
```bash
../.venv/bin/python -m pytest tests/unit/services/test_market_data_storage_service.py -v
```
Expected: fail before the service exists.

- [ ] **Step 2: Implement the storage service**

Add a service that accepts `MarketSnapshot` and writes:
- snapshot row
- section rows
- item rows
- dataset rows
- quality report row

Keep `snapshot-build` 现有文件产物不变，新增 DB 持久化只是多一条正式事实源。

Pseudo-contract:
```python
class MarketDataStorageService(BaseService):
    async def save_snapshot(self, snapshot: MarketSnapshot) -> ServiceResult: ...
    async def load_snapshot(self, snapshot_id: str) -> ServiceResult: ...
```

- [ ] **Step 3: Wire storage into the snapshot build flow**

Call storage service from the existing market snapshot orchestration path, not from Router and not from CLI.  
Return payload should include safe IDs:
- `snapshot_id`
- `dataset_id`
- `storage_ref`
- summary / quality artifact refs

- [ ] **Step 4: Run service tests**

Run:
```bash
../.venv/bin/python -m pytest tests/unit/services/test_market_data_storage_service.py tests/unit/services/test_market_snapshot_service.py -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/market_data_storage_service.py src/services/market_snapshot_service.py src/services/snapshot_service.py src/services/__init__.py tests/unit/services/test_market_data_storage_service.py tests/unit/services/test_market_snapshot_service.py
git commit -m "feat(market-data): persist snapshots to db"
```

---

## Task 5: Surface Safe Artifact Metadata

**Files:**
- Modify: `src/services/job_runner.py`
- Modify: `src/services/artifact_service.py` only if needed for metadata exposure
- Modify: `src/pipelines/market_data_pipeline_spec.py` only if artifact contract needs a new field
- Test: `tests/unit/services/test_job_runner.py`

- [ ] **Step 1: Write the failing artifact metadata test**

Write a regression test ensuring:
- artifact metadata can point back to `snapshot_id` / `dataset_id`
- no absolute filesystem path is exposed to the public `result.json`
- safe download remains possible

Run:
```bash
../.venv/bin/python -m pytest tests/unit/services/test_job_runner.py -v
```
Expected: fail if metadata is not yet wired.

- [ ] **Step 2: Implement safe metadata wiring**

Ensure that:
- `JobRunner` binds snapshot artifacts with safe IDs
- `result.json` stays sanitized
- any path reference stays internal to the worker/artifact binding layer

- [ ] **Step 3: Run artifact tests**

Run:
```bash
../.venv/bin/python -m pytest tests/unit/services/test_job_runner.py -v
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/services/job_runner.py src/services/artifact_service.py src/pipelines/market_data_pipeline_spec.py tests/unit/services/test_job_runner.py
git commit -m "feat(market-data): keep artifact metadata safe"
```

---

## Task 6: Document and Sync TaskList

**Files:**
- Modify: `docs/New-Web-Market-Data-Storage.md`
- Modify: `docs/New-Web-Linked-TaskLists/New-Web-TaskList.md`
- Modify: `daily-sessions/2026-05-16.md`
- Modify: `daily-report/2026-05-16.md`

- [ ] **Step 1: Write the docs update**

Document:
- table structure
- write/query flow
- compatibility boundary
- storage ref / artifact ref rules
- why there is no new CLI product surface

- [ ] **Step 2: Mark task progress in TaskList**

Only after tests pass and the storage chain is verified, update `NW-V2-S2-004` completion notes and any affected UI binding notes.

- [ ] **Step 3: Update session/report**

Record:
- what was added
- what remains for `NW-V2-S2-005`
- whether any compatibility layer still needs a later removal task

- [ ] **Step 4: Commit**

```bash
git add docs/New-Web-Market-Data-Storage.md docs/New-Web-Linked-TaskLists/New-Web-TaskList.md daily-sessions/2026-05-16.md daily-report/2026-05-16.md
git commit -m "docs(market-data): record db storage design"
```

---

## Self-Review Checklist

Before implementation begins, verify:

1. Every required DB table in the spec has a corresponding task.
2. `payload_json` is only used as extension data, not as the primary query source.
3. No task introduces a new product-level CLI command.
4. No task routes around the existing Web / Job / Workflow体系.
5. The tests cover idempotency, query paths, and safe artifact metadata.
6. The docs and TaskList updates are placed at the end, after behavior is verified.

