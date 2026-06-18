# Stage 5 基础数据、数据调度与数据质量实施日志

## Current Status

- Stage：`Stage 5 基础数据、数据调度与数据质量`
- Stage 状态：`[x] 已完成`
- 当前活动：`2026-06-18 Stage 5 Review and Gate` 已完成。
- 当前已接受：`Stage 5 Bootstrap`、`RT-S5-001`、`RT-S5-002`、`RT-S5-003`、`Stage 5 Gate`
- 下一可执行 Task：`Stage 6 Bootstrap`
- 不得自动开始：`Stage 6 Bootstrap` 需用户明确触发。
- 计划：`docs/refactor-implementation-plans/stage-5-implementation-plan.md`

## 2026-06-17 Stage 5 Bootstrap

### Scope

本次只执行 Stage 5 Bootstrap，不实施 production code。

目标：

- 确认 Stage 4 accepted entry condition；
- 确认 branch、HEAD、working tree baseline；
- 检查 OHLCV、Kaipan、indicator、market-state、DatasetSnapshot、MarketSnapshot、scheduler、job、database、API、CLI 和 Web 当前实现；
- 冻结 Stage 5 数据、时间、快照和兼容边界；
- 判断 `RT-S5-001` / `RT-S5-002` / `RT-S5-003` 的执行顺序；
- 创建 Stage 5 implementation plan；
- 更新实施日志。

未执行：

- 未实施 `RT-S5-001`。
- 未实施 `RT-S5-002`。
- 未实施 `RT-S5-003`。
- 未执行 Stage 6 回测。
- 未提交或推送。

### Repository Baseline

- Repository remote：`git@github.com:xiyuxifeng/Trade.git`
- Project root：`trade-strategy-ai`
- Branch：`main`
- HEAD：`a72243a644d2b404ba8117458f7813e856a3b556`
- Working tree before Bootstrap edits：clean
- Bootstrap changed only documentation under `docs/`.

### Entry Condition

Accepted upstream state:

- Stage 4 Gate：`ACCEPTED`
- Pre-Stage-5 cleanup review：verified and fixed
- Stage 4 detailed log states Stage 5 Bootstrap may begin after explicit user authorization.
- User explicitly authorized Stage 5 Bootstrap only.

Preserved upstream contracts:

- canonical writer only;
- no dual-write or legacy writer fallback;
- fixed-set gate remains intact for rule-governance mutations;
- revision-bound provenance and truthful unavailable semantics;
- no fabricated data, coverage, market state, snapshot, or readiness;
- no second formal data source or duplicate formal entry point;
- no Stage 6 backtest execution;
- no future Prompt activation.

### Documents Inspected

- `docs/Trade-Refactor-TaskList.md`
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
- `docs/PROMPT_REVIEW_AND_MIGRATION.md`
- `docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
- `docs/AI-Conversation-Templates.md`
- `docs/AI-Conversation-Project-Constraints-1.md`
- `docs/AI-Conversation-Project-Constraints-2.md`
- `docs/AI-Conversation-Task-Matrix.md`
- `docs/Refactor-Implementation-Log.md`
- `docs/refactor-implementation-logs/stage-4.md`
- `docs/refactor-implementation-plans/stage-2-implementation-plan.md`
- `docs/refactor-implementation-plans/stage-4-implementation-plan.md`
- `docs/Refactor-Migration-Matrix.md`
- `docs/Refactor-Current-State-Audit.md`

### Implementation Areas Inspected

OHLCV and indicators:

- `src/models/ohlcv_bar.py`
- `src/market_data/ohlcv_service.py`
- `src/services/market_service.py`
- `src/providers/akshare_provider.py`
- `src/indicators/indicator_service.py`
- `src/models/indicator.py`
- `cli/ohlcv.py`
- `src/pipeline/tasks/ohlcv_crawl_task.py`

DatasetSnapshot and MarketSnapshot:

- `src/models/stage2_canonical.py`
- `src/models/market_dataset.py`
- `src/models/market_data_snapshot.py`
- `src/models/market_data_snapshot_section.py`
- `src/models/market_data_snapshot_item.py`
- `src/models/market_data_quality_report.py`
- `src/models/market_snapshot.py`
- `src/services/market_data_storage_service.py`
- `src/services/market_snapshot_service.py`
- `src/services/market_snapshot_query_service.py`
- `src/db/repositories/market_dataset_repository.py`
- `src/db/repositories/market_snapshot_repository.py`
- `src/db/repositories/market_snapshot_section_repository.py`
- `src/db/repositories/market_snapshot_item_repository.py`
- `src/db/repositories/market_data_quality_repository.py`

Kaipan, market-state, and snapshots:

- `src/services/kaipan_service.py`
- `src/providers/kaipan_provider.py`
- `src/providers/kaipan_normalizer.py`
- `src/providers/kaipan_scheduler.py`
- `src/services/market_snapshot_builders.py`
- `src/services/market_regime_feature_service.py`
- `src/services/market_regime_service.py`
- `src/services/market_regime_rules.py`
- `src/models/market_regime.py`
- `src/models/market_regime_record.py`

Scheduler, jobs, system-management, API, and Web:

- `src/services/job_registry.py`
- `src/services/job_runner.py`
- `src/services/job_service.py`
- `src/services/job_control.py`
- `src/services/system_service.py`
- `src/services/ops_service.py`
- `src/services/dashboard_service.py`
- `src/pipeline/scheduler.py`
- `src/rule_backtest/scheduler.py`
- `src/services/workflow_service.py`
- `src/services/pipeline_application_service.py`
- `api/app.py`
- `api/routers/ui/market.py`
- `api/routers/ui/kaipan.py`
- `api/routers/ui/snapshots.py`
- `api/routers/snapshots.py`
- `web/src/app/route-config.tsx`
- `web/src/pages/market/index.tsx`
- `web/src/features/market-workspace/market-workspace-shell.tsx`
- `web/src/features/system-management/system-management-workspace.tsx`

Migrations and tests:

- `src/db/migrations/env.py`
- `src/db/migrations/versions/2026_04_29_0001_add_ohlcv_indicators_tables.py`
- `src/db/migrations/versions/2026_05_16_0002_create_market_data_storage_tables.py`
- `src/db/migrations/versions/2026_05_17_0001_add_market_regime_features_table.py`
- `src/db/migrations/versions/2026_05_18_0001_add_market_regimes_table.py`
- `src/db/migrations/versions/2026_06_14_0003_stage2_domain_schema.py`
- `src/db/migrations/versions/2026_06_14_0004_stage2_compatibility_views.py`
- `src/db/migrations/versions/2026_06_14_0005_stage2_gate_schema_repair.py`
- Stage 5-relevant tests under `tests/unit/market_data`, `tests/unit/services`, `tests/unit/backtest`, `tests/unit/db`, `tests/api`, and `web/src`.

### Delegation

Used three bounded read-only Explorer agents:

- OHLCV, DatasetSnapshot, MarketSnapshot, data-quality, gap detection, repair/retry, migrations, tests.
- Kaipan, indicator, market-state, MarketSnapshot, readiness/degraded behavior, provenance, tests.
- Scheduler, workers, CLI, APIs, Web system-management/data readiness, repair flows, operational docs, tests.

No subagent edited files or made final acceptance decisions.

### Current-State Findings

- `ohlcv_bars` is the current OHLCV persistence table.
- Current OHLCV identity is too weak for Stage 5 because it lacks explicit asset type, exchange, frequency, adjustment policy, source/provenance, availability time, and quality state.
- Current OHLCV service can coerce missing numeric values to `0.0`; Stage 5 must reject or mark such data instead of defaulting.
- Historical backfill exists as a date-range call, but no trading-calendar-aware gap repair planner exists.
- `dataset_snapshots` is the Stage 2 formal DatasetSnapshot source.
- Runtime code still reads datasets through `MarketDataset` / `market_datasets`, which is a compatibility view and read-only under canonical writer routing.
- `market_snapshots` and child tables are the structured MarketSnapshot source.
- File-based `market_universe`, `data/kaipan/snapshots`, and `market_state.json` remain live compatibility dependencies.
- Kaipan supports `09-25` and `17-30`, but Stage 5 must freeze slot-specific source/captured/ingested/available time semantics.
- Scheduler/control surfaces are fragmented across jobs, workflows, pipelines, CLI schedulers, MarketService scheduler, KaipanService scheduler, and article pipeline schedule service.
- Web compatibility pages still expose technical terms in body copy.

### Frozen Contracts

The frozen contracts are written in:

- `docs/refactor-implementation-plans/stage-5-implementation-plan.md`

Key decisions:

- `trade_date` is China market trading date in `Asia/Shanghai`.
- Scheduler decisions use `Asia/Shanghai`.
- Runtime timestamps are timezone-aware UTC unless they are market-local dates.
- Every formal data output separates event/source/captured/ingested/available time.
- Pre-market data cannot use post-close availability.
- Post-close data cannot be used before it is available.
- Stage 6 backtests must later bind to immutable snapshots and must not call live providers.
- OHLCV identity includes canonical symbol, source symbol, exchange, asset type, frequency, and adjustment policy.
- `DatasetSnapshot` formal source is `dataset_snapshots`.
- `MarketSnapshot` formal source is `market_snapshots` and child tables.
- `market_datasets` remains compatibility read-only while canonical writer routing is enabled.
- Missing data remains `missing`, `partial`, `unavailable`, `invalid`, `conflict`, or `insufficient_coverage`; it is not converted to false, zero, or success.

### Execution Decision

Decision: `READY`.

Recommended execution order:

1. `RT-S5-001 OHLCV 数据体系`
2. `RT-S5-002 Kaipan 数据体系`
3. `RT-S5-003 调度和系统管理`
4. Stage 5 Gate

`RT-S5-001` and `RT-S5-002` may share one Parent session in separate acceptance batches. `RT-S5-003` must remain later and separate until the data contracts are stable.

### Bootstrap Validation

Completed validation:

- Verified all three Stage 5 tasks are represented in the plan.
- Verified `RT-S5-003` is explicitly later and not started.
- Verified no Stage 6 backtest execution is included.
- Verified data/time semantics and no-future-data-leakage rules are explicit.
- Verified DatasetSnapshot and MarketSnapshot immutability/versioning/traceability are explicit.
- Verified missing data remains truthful.
- Reviewed docs for contradictions with Stage 2/4 accepted contracts.

Tests run:

- No test suite was run because Bootstrap is analysis and planning only.

### Blocking Issues

No blocker prevents starting `RT-S5-001`.

The following are blockers for accepting `RT-S5-001` if not fixed during that task:

- OHLCV missing numeric values can currently become zero.
- OHLCV identity lacks adjustment/frequency/source/provenance/time semantics.
- No trading-calendar-aware OHLCV gap repair planner exists.
- DatasetSnapshot runtime path is not yet cleanly canonical over `dataset_snapshots`.

### Non-Blocking Risks

- Internal `regime` naming remains in code.
- Legacy file-based snapshots and market-state artifacts remain live compatibility dependencies.
- Existing tests cover current technical surfaces more than the intended Stage 5 business surface.
- Live-provider tests may require credentials/network; deterministic fake-provider tests are required and live operational evidence can be separately recorded.

### Logs and Docs

Created:

- `docs/refactor-implementation-plans/stage-5-implementation-plan.md`
- `docs/refactor-implementation-logs/stage-5.md`

## 2026-06-18 RT-S5-003 调度和系统管理

- Task ID：`RT-S5-003`
- 状态：`[x] 已完成`
- Repository recovery：
  - remote：`git@github.com:xiyuxifeng/Trade.git`
  - branch：`main`
  - recovered HEAD：`243d71357bc639543142b2d2a7f3fe0f9d5173d7`
  - fast-forward update：`git fetch --prune origin` 和 `git pull --ff-only origin main` 后仍为 same HEAD
  - working tree before implementation：clean
  - partial commit `243d71357bc639543142b2d2a7f3fe0f9d5173d7` exists in current branch history and remained preserved
- Partial commit recovery conclusion：
  - recovered partial commit changed only `src/services/data_scheduling_service.py` and `tests/unit/services/test_data_scheduling_service.py`
  - already present work was a thin readiness/schedule policy skeleton with fixed schedule windows, basic repair-step planning, and initial unit tests
  - missing before this session: formal API router, Web page, JobRunner/job-registry integration, truthful legacy write rejection, operation identity/dedup evidence, progress tracking, operator mutation surface, and implementation/test/docs closure
- 修改范围：
  - backend/API：`api/app.py`、`api/routers/ui/system_data.py`、`api/routers/ui/market.py`、`api/routers/ui/kaipan.py`
  - orchestration/runtime：`src/services/data_scheduling_service.py`、`src/services/job_registry.py`、`src/services/job_runner.py`
  - tests：`tests/api/routers/test_system_data_api.py`、`tests/api/routers/test_market_ui.py`、`tests/api/routers/ui/test_kaipan.py`、`tests/unit/services/test_data_scheduling_service.py`、`tests/unit/services/test_job_registry.py`、`tests/unit/services/test_job_runner.py`
  - Web：`web/src/types/system.ts`、`web/src/lib/api/system.ts`、`web/src/pages/system/index.tsx`、`web/src/pages/product-entry-pages.test.tsx`
- 关键决定：
  - formal Stage 5 mutation surface is `系统管理 -> 数据与调度` and `/api/ui/v1/system/data/*`
  - readiness remains derived from canonical data facts, not from `Job success`
  - truthful readiness precedence is `conflict -> invalid -> insufficient_coverage -> unavailable`, then running/failed/cancelled/missing/partial, and only then `ready`
  - deterministic operation identity uses action + target scope + concrete planned steps and intentionally ignores trigger source, so equivalent manual/scheduled requests deduplicate into the same formal run
  - `system-data-operation` is the only formal Stage 5 job type for update/repair/backfill/recompute orchestration; it reuses existing job infrastructure instead of creating a second scheduler or workflow engine
  - legacy UI write endpoints for OHLCV/Kaipan (`/market/ohlcv/run|stop`, `/kaipan/fetch|normalize|run|stop`) are now compatibility-only and reject with explicit `409` guidance to `系统管理 -> 数据与调度`
  - legacy job/workflow/pipeline/CLI primitives remain internal or compatibility-only; Stage 5 formal user-facing mutation no longer goes through those raw paths
  - JobRunner now writes formal progress for `system-data-operation`
- Readiness contract evidence：
  - readiness payload now exposes canonical facts for OHLCV trade-date coverage, indicator coverage, DatasetSnapshot state, pre-market/post-close MarketSnapshot state, market-state state, latest availability time, missing coverage, and unavailable reasons
  - running or successful jobs alone do not make readiness `ready`
  - cancelled/failed latest operation remains truthful when canonical data is still missing
  - pre-market and post-close slot statuses remain distinct and are not collapsed into one success state
- Scheduling and dependency order：
  - `09:20-09:25`：盘前 Kaipan 更新 -> 市场状态重算
  - `17:00`：收盘后行情更新 -> 指标重算 -> 市场状态重算
  - `17:30`：盘后 Kaipan 更新 -> 市场状态重算
  - `22:00-23:59`：夜间健康检查与最小修复
- Repair-plan behavior：
  - repair uses deterministic minimal steps derived from current facts and current phase
  - pre-market repair only targets pre-market snapshot and dependent market-state work
  - post-close repair targets only missing OHLCV/indicator/post-close snapshot/market-state steps needed for the target trade date
  - backfill keeps explicit start/end date scope and recomputes indicators only for the requested trade-date range
- Authorization / audit / retry / resume / cancellation / idempotency：
  - all formal mutation endpoints require `operator`
  - viewer/anonymous callers are rejected before operation creation and corresponding API tests verify denial
  - job creation goes through canonical `JobService` with idempotency key and audit source
  - cancel/retry/resume are delegated to existing job control, but only through the canonical `system-data-operation` surface
  - duplicate manual and scheduled requests for the same scope reuse one formal operation identity
- Canonical vs compatibility path decisions：
  - canonical：`/api/ui/v1/system/data/*` + `system-data-operation`
  - compatibility-only rejection：legacy OHLCV/Kaipan UI mutation endpoints
  - read-only compatibility retained：legacy OHLCV/Kaipan status endpoints and existing market/system read pages
  - workflow/pipeline/job registry internals remain implementation infrastructure and do not become a second formal Stage 5 business surface
  - CLI legacy `ohlcv` / scheduler / raw market-state utilities remain compatibility/internal tooling; retirement condition is Stage 5 Review + later legacy cleanup batch, not this task
- Runtime integration notes：
  - `DataSchedulingService.execute_operation()` now invokes accepted canonical services for OHLCV crawl, Kaipan fetch/normalize, MarketSnapshot build, and MarketRegime build
  - indicator recompute uses the canonical async indicator service session factory rather than an invalid session-scope instance
  - market-state recompute chooses a ready same-day canonical MarketSnapshot, preferring `17-30` then `09-25`, rather than a broken slot comparison
- Web outcome：
  - `/system/data` now renders formal Chinese `数据与调度` content instead of placeholder copy
  - normal users see readiness, impact, missing scope, time windows, and recent operation truthfully
  - operators can trigger `立即更新数据`、`一键补齐`、`重算指标`、`重算市场状态`、`回灌历史数据` and can cancel/retry/resume allowed formal operations
  - page covers loading / partial / unavailable / error / permission denied / empty and does not expose raw job names on the normal-user surface
- 数据库迁移：无新增 migration；本任务建立 orchestration facade 和 formal surfaces，不改变 accepted RT-S5-001/002 schema contracts
- 已运行测试：
  - baseline before continuing：
    - `../.venv/bin/python -m pytest tests/unit/services/test_data_scheduling_service.py -q`
    - `../.venv/bin/python -m pytest tests/api/routers/test_market_ui.py -q`
    - `pnpm vitest run src/pages/system/index.test.tsx src/app/route-config.test.tsx src/pages/market/index.test.tsx`
  - focused backend/API/job/service suite：
    - `../.venv/bin/python -m pytest tests/unit/services/test_job_runner.py tests/unit/services/test_job_registry.py tests/unit/services/test_data_scheduling_service.py tests/api/routers/test_system_data_api.py tests/api/routers/test_market_ui.py tests/api/routers/ui/test_kaipan.py -q`
  - frontend targeted suite：
    - `pnpm vitest run src/pages/product-entry-pages.test.tsx src/pages/system/index.test.tsx src/app/route-config.test.tsx`
  - required verification：
    - `pnpm typecheck`
    - `../.venv/bin/python -m compileall src api cli`
    - `git diff --check`
    - `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
- 测试结果：
  - focused backend/API/job/service suite：`63 passed`
  - frontend targeted suite：`23 passed`
  - `pnpm typecheck`：passed
  - `compileall`：passed
  - `git diff --check`：passed
  - Stage 3 fixed-set regression：
    - sandbox run failed with `Operation not permitted` during persistence
    - rerun outside sandbox passed with `{"status":"passed","article_count":12,"processed_count":12,"cached_count":12,"human_attention_count":6,"persistence_failures":[],"provider_failures":[],"semantic_failures":[],"validation_failures":[]}`
- Self-review findings and repairs：
  - found and fixed truthful readiness precedence gaps for `invalid` / `conflict` / `cancelled`
  - found and fixed missing progress tracking for `system-data-operation` inside JobRunner
  - found and fixed legacy OHLCV/Kaipan write endpoints still mutating outside the formal facade
  - found and fixed indicator recompute session-factory misuse
  - found and fixed broken market-state snapshot slot selection
- 未完成项：
  - Stage 5 Review has not started
  - broader legacy CLI/workflow/pipeline retirement is deferred to later cleanup/retirement work after Review evidence
- 已知风险：
  - legacy CLI and internal workflow primitives still exist as compatibility/internal tools; this task classifies them but does not yet retire them
  - readiness facts are currently derived from latest canonical records; if future Stage 5 Review requires richer persisted coverage/audit tables, that should be treated as a follow-up refinement rather than a blocker to RT-S5-003 acceptance
  - fixed-set regression required unsandboxed execution because sandbox persistence produced local permission errors
- 验收结论：`RT-S5-003 ACCEPTED`。Formal data-readiness facade, operator authorization, deterministic operation identity, canonical mutation surface, truthful legacy-path rejection, JobRunner/job-registry integration, Web/API surfaces, and focused regression evidence satisfy the frozen Stage 5 contract. Stage 5 Review may begin after explicit user instruction, but must not auto-start.

Updated:

- `docs/Refactor-Implementation-Log.md`

### Bootstrap Conclusion

`READY`

`RT-S5-001` may begin after explicit user authorization. Do not begin `RT-S5-001` automatically.

## 2026-06-17 RT-S5-001 OHLCV 数据体系

### Decision

`ACCEPTED`

### Scope Executed

- Canonical OHLCV identity for stock, index, and ETF now includes `symbol`, `exchange`, `asset_type`, `frequency`, `adjustment_policy`, and `trade_date`.
- Added explicit provenance/time fields: `source_symbol`, `source`, `source_payload_fingerprint`, `event_time`, `source_time`, `source_time_reason`, `captured_at`, `ingested_at`, and `available_at`.
- Enforced `Asia/Shanghai` trading-date semantics for day-bar event/availability boundaries.
- Historical backfill, incremental update, and repair now preserve idempotency under canonical payload fingerprinting.
- Added trading-calendar-aware gap planning and deterministic repair path.
- Added truthful indicator recompute boundary by invalidating affected cached indicators from the earliest changed trade date forward.
- Added canonical immutable `DatasetSnapshot` freeze path over `dataset_snapshots`.
- Switched dataset query runtime path from `MarketDataset` compatibility reads to canonical `DatasetSnapshotRepository`.

### Implementation Notes

- Missing or malformed numeric OHLCV fields now raise validation errors instead of becoming `0.0`.
- Unknown adjustment policy is rejected.
- Duplicate provider rows for the same canonical identity are deduped when payloads match and rejected when payloads conflict.
- `available_at` is set to post-close availability and therefore cannot be reused as pre-market availability.
- `DatasetSnapshotRepository.save()` now canonicalizes the content fingerprint from snapshot content, preventing placeholder-fingerprint writes from becoming the formal identity.
- `market_datasets` remains compatibility-only. The user-facing dataset browsing route still exists, but the backend data source is now `dataset_snapshots`.

### Files Changed

- `src/models/ohlcv_bar.py`
- `src/market_data/ohlcv_service.py`
- `src/models/stage2_canonical.py`
- `src/db/repositories/dataset_snapshot_repository.py`
- `src/db/repositories/__init__.py`
- `src/services/dataset_snapshot_service.py`
- `src/services/market_service.py`
- `src/services/market_snapshot_query_service.py`
- `cli/ohlcv.py`
- `src/pipeline/tasks/ohlcv_crawl_task.py`
- `src/db/migrations/versions/2026_06_17_0008_stage5_ohlcv_contract.py`
- `tests/unit/market_data/test_ohlcv_service.py`
- `tests/unit/db/repositories/test_dataset_snapshot_repository.py`
- `tests/unit/services/test_dataset_snapshot_service.py`
- `tests/unit/services/test_market_snapshot_query_service.py`
- `tests/unit/services/test_snapshot_market_service.py`
- `tests/unit/pipeline/test_ohlcv_crawl_task.py`
- `tests/unit/models/test_ohlcv_bar.py`
- `tests/unit/db/test_migrations.py`

### Verification

Commands run:

- `../.venv/bin/python -m pytest tests/unit/cli/test_ohlcv.py tests/unit/pipeline/test_ohlcv_crawl_task.py tests/unit/models/test_ohlcv_bar.py tests/unit/market_data/test_ohlcv_service.py tests/unit/db/repositories/test_dataset_snapshot_repository.py tests/unit/services/test_market_snapshot_query_service.py tests/unit/services/test_dataset_snapshot_service.py tests/unit/services/test_snapshot_market_service.py tests/unit/db/test_migrations.py tests/api/routers/test_market_ui.py -q`
- `pnpm test -- src/pages/market/datasets/index.test.tsx src/pages/market/index.test.tsx src/lib/api/market.test.ts`
- `pnpm typecheck`
- `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
- `../.venv/bin/python -m compileall src api cli`
- `git diff --check`

Results:

- Backend/API/database/CLI/job/migration targeted suite: `51 passed`
- Frontend targeted suite: `10 passed`
- TypeScript: passed
- Stage 3 fixed-set regression: `passed`
- `compileall`: passed
- `git diff --check`: passed

### Remaining Risks

- Migration evidence in this batch is based on migration-definition tests, downgrade guard logic, and code-path review. A separate real PostgreSQL upgrade/downgrade/re-upgrade operational replay is still advisable before Stage 5 Gate.
- Stage 6 snapshot-bound backtest runtime is out of scope here; this task only establishes the canonical OHLCV and DatasetSnapshot contract that Stage 6 must consume.
- Formal normal-user `系统管理 -> 数据与调度` surface remains owned by `RT-S5-003`.

### Next Task

`RT-S5-002` may begin in a separate acceptance batch. Do not begin it automatically.

## 2026-06-17 RT-S5-002 Kaipan 数据体系

### Decision

`ACCEPTED`

### Scope Executed

- Froze canonical Kaipan slot semantics at `09-25` pre-market and `17-30` post-close.
- Extended `MarketSnapshot` / `MarketSnapshotSection` contracts with explicit slot, source/captured/ingested/available time, section source dataset, payload fingerprint, normalization version, content fingerprint, and frozen time.
- Made MarketSnapshot freeze idempotent on canonical content and versioned by `content_fingerprint`.
- Removed the blocking `(market, trade_date, slot, data_version)` unique constraint so changed content for the same slot can form a new frozen version instead of mutating the old one.
- Preserved truthful unavailable behavior for missing historical Kaipan data.
- Kept `market_datasets` compatibility-write rejection in place and updated affected tests/read paths accordingly.
- Verified market-state feature/regime construction degrades truthfully when snapshot coverage is insufficient.

### Implementation Notes

- Canonical section payloads now strip volatile fields such as `fetched_at` before fingerprinting, so reruns with unchanged content reuse the same frozen snapshot identity.
- Snapshot/service output now exposes slot-specific `available_at` and `content_fingerprint`; `09-25` and `17-30` snapshots cannot collide.
- Section provenance defaults remain truthful: when a section is unavailable or missing, time fields stay absent rather than being synthesized.
- File-based snapshot paths remain compatibility-only; formal freeze semantics are carried by `market_snapshots` and child tables.
- A pre-existing package import cycle involving `src.models` and `src.alerting.db` was repaired with a lazy `AlertHistory` export so the affected Kaipan/market-state suites could run again.

### Files Changed

- `src/models/market_snapshot.py`
- `src/models/market_data_snapshot.py`
- `src/models/market_data_snapshot_section.py`
- `src/services/market_snapshot_builders.py`
- `src/services/market_snapshot_service.py`
- `src/services/market_data_storage_service.py`
- `src/db/repositories/market_snapshot_repository.py`
- `src/db/repositories/market_snapshot_section_repository.py`
- `src/services/market_regime_service.py`
- `src/models/__init__.py`
- `src/db/migrations/versions/2026_06_17_0009_stage5_kaipan_contract.py`
- `data/kaipan/raw/.gitkeep`
- `data/kaipan/snapshots/.gitkeep`
- `tests/providers/test_kaipan_pipeline.py`
- `tests/unit/db/repositories/test_market_data_repositories.py`
- `tests/unit/db/test_migrations.py`
- `tests/unit/models/test_market_snapshot.py`
- `tests/unit/services/test_market_data_storage_service.py`
- `tests/unit/services/test_market_regime_feature_service.py`
- `tests/unit/services/test_market_snapshot_service.py`

### Verification

Commands run:

- `../.venv/bin/python -m pytest tests/unit/models/test_market_snapshot.py tests/unit/providers/test_kaipan_provider.py tests/unit/providers/test_kaipan_normalizer.py tests/providers/test_kaipan_scheduler.py tests/providers/test_kaipan_pipeline.py tests/unit/services/test_market_snapshot_builders.py tests/unit/services/test_market_snapshot_registry.py tests/unit/services/test_market_snapshot_service.py tests/unit/services/test_market_data_storage_service.py tests/unit/services/test_market_snapshot_query_service.py tests/unit/services/test_market_regime_feature_service.py tests/unit/services/test_market_regime_service.py tests/unit/services/test_snapshot_market_service.py tests/unit/services/test_kaipan_dashboard_service.py tests/api/routers/ui/test_kaipan.py tests/api/routers/test_ui_snapshots.py tests/api/routers/test_market_ui.py tests/unit/db/repositories/test_market_data_repositories.py tests/unit/db/test_migrations.py -q`
- `pnpm vitest run src/features/market-workspace/market-workspace-shell.test.tsx src/pages/market/snapshots/index.test.tsx src/pages/market/index.test.tsx`
- `pnpm typecheck`
- `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
- `../.venv/bin/python -m compileall src api cli`
- `git diff --check`

Results:

- Focused backend/API/provider/database/migration/market-state suite: `119 passed`
- Frontend targeted suite: `14 passed`
- TypeScript: passed
- Stage 3 fixed-set regression: `passed` with `article_count=12`, `processed_count=12`, `validation_failures=[]`
- `compileall`: passed
- `git diff --check`: passed

### Remaining Risks

- Migration evidence is still based on migration-definition tests, downgrade guards, sqlite-backed runtime verification, and code review. A separate real PostgreSQL upgrade/downgrade/re-upgrade replay remains advisable before Stage 5 Gate.
- Historical Kaipan operational success still depends on provider credentials/network and whether the upstream source actually has the requested historical payloads.
- Formal normal-user data-readiness/system-management surface remains owned by `RT-S5-003`.

### Next Task

`RT-S5-003` may begin in a separate acceptance batch. Do not begin it automatically.

## 2026-06-18 Stage 5 Review and Gate

### Decision

`ACCEPTED`

### Findings Discovered

- Generic job/workflow paths could still submit raw Stage 5 data job types (`ohlcv-crawl`、`kaipan-fetch`、`kaipan-normalize`、`kaipan-run`、`snapshot-build`、`market-state-build`), bypassing the formal `system-data-operation` entry.
- `DatasetSnapshotService.freeze_ohlcv_snapshot()` fingerprinted aggregate metadata but not individual OHLCV row payload/content, so repaired same-symbol/same-date rows could reuse an old frozen snapshot.
- Normal-user `/system/data` page copy exposed the English technical term `readiness`.
- Low-level `JobService.create_job()` could still create raw Stage 5 data jobs even after `JobRunner.submit_job()` and UI API validation were repaired.

### Repairs Applied

- Marked raw Stage 5 data job definitions as compatibility-only and made `validate_job_submission()` reject them with replacement guidance to `system-data-operation` / `系统管理 -> 数据与调度`.
- Added targeted `JobService.create_job()` rejection for raw Stage 5 data job types so internal callers cannot bypass the formal data entry point.
- Updated workflow/job tests so legacy scheduler/raw data paths are rejected and existing compatibility jobs do not execute formal writes.
- Added OHLCV row-level fingerprints to DatasetSnapshot manifest/fingerprint inputs, ordered by the full canonical OHLCV identity.
- Replaced user-visible `readiness` copy with Chinese business wording `就绪状态` and added a page-shell regression test.
- Preserved formal `system-data-operation` external dependency failure classification for provider alerts.

### Verification

Commands run and results:

- `../.venv/bin/python -m pytest tests/unit/cli/test_ohlcv.py tests/unit/pipeline/test_ohlcv_crawl_task.py tests/unit/models/test_ohlcv_bar.py tests/unit/market_data/test_ohlcv_service.py tests/unit/db/repositories/test_dataset_snapshot_repository.py tests/unit/services/test_dataset_snapshot_service.py tests/unit/services/test_market_snapshot_query_service.py tests/unit/services/test_snapshot_market_service.py tests/unit/db/test_migrations.py tests/api/routers/test_market_ui.py -q` -> `53 passed`
- `../.venv/bin/python -m pytest tests/unit/models/test_market_snapshot.py tests/unit/providers/test_kaipan_provider.py tests/unit/providers/test_kaipan_normalizer.py tests/providers/test_kaipan_scheduler.py tests/providers/test_kaipan_pipeline.py tests/unit/services/test_market_snapshot_builders.py tests/unit/services/test_market_snapshot_registry.py tests/unit/services/test_market_snapshot_service.py tests/unit/services/test_market_data_storage_service.py tests/unit/services/test_market_regime_feature_service.py tests/unit/services/test_market_regime_service.py tests/unit/services/test_kaipan_dashboard_service.py tests/api/routers/ui/test_kaipan.py tests/api/routers/test_ui_snapshots.py tests/unit/db/repositories/test_market_data_repositories.py -q` -> `87 passed`
- `../.venv/bin/python -m pytest tests/unit/services/test_job_runner.py tests/unit/services/test_job_registry.py tests/unit/services/test_job_service.py tests/unit/services/test_data_scheduling_service.py tests/api/routers/test_system_data_api.py tests/api/routers/test_jobs_api.py tests/unit/services/test_workflow_service.py tests/unit/services/test_workflow_runner.py tests/api/routers/test_workflows.py -q` -> `93 passed`
- `../.venv/bin/python -m pytest tests/unit/services/test_stage2_writer_routing.py tests/regression/stage3 tests/unit/stage3 tests/integration/test_stage3_single_article.py tests/integration/test_stage3_batch.py tests/integration/test_stage3_legacy_compatibility.py tests/api/routers/ui/test_article_metadata.py -q` -> `39 passed`
- `../.venv/bin/python -m pytest tests/unit/services/test_optimize_rule_pool_service.py tests/integration/test_stage4_rule_governance.py tests/integration/test_stage4_rule_lifecycle.py tests/integration/test_stage4_rule_review.py tests/api/routers/test_rule_lifecycle.py tests/api/routers/test_rule_review.py tests/api/routers/test_rule_pool.py tests/api/routers/ui/test_strategy_studio.py tests/unit/services/test_rule_governance_service.py tests/unit/db/test_stage4_rule_governance_migration.py tests/unit/cli/test_rule_pool_cli.py -q` -> `41 passed`
- `pnpm vitest run src/pages/system/index.test.tsx src/pages/product-entry-pages.test.tsx src/app/route-config.test.tsx src/pages/market/index.test.tsx src/features/market-workspace/market-workspace-shell.test.tsx src/pages/market/snapshots/index.test.tsx` -> `6 files passed`, `38 tests passed`
- `pnpm typecheck` -> `TypeScript: No errors found`
- `../.venv/bin/python -m compileall src api cli` -> passed
- `git diff --check` -> passed
- `../.venv/bin/python -m cli.main stage3-regression run --fixed-set` -> `{"status":"passed","article_count":12,"cached_count":12,"processed_count":12,"human_attention_count":6,"persistence_failures":[],"provider_failures":[],"semantic_failures":[],"validation_failures":[]}`

### PostgreSQL Migration Evidence

- Sandbox PostgreSQL connection to localhost was blocked with `Operation not permitted`; the same checks were rerun through approved unsandboxed local PostgreSQL access.
- PostgreSQL version: `PostgreSQL 15.17 (Homebrew)`.
- Fresh database `trade_stage5_gate_fresh`: `upgrade head` reached `2026_06_17_0009`; verified `dataset_snapshots`、`ohlcv_bars`、`market_snapshots`、`market_snapshot_sections`; verified `uq_ohlcv_identity_trade_date`; verified Stage 5 OHLCV and section provenance/time columns.
- Fresh downgrade: `downgrade 2026_06_16_0007` succeeded; verified old `uq_ohlcv_symbol_date`; verified Stage 5 OHLCV and section columns removed.
- Fresh re-upgrade: `upgrade head` succeeded through `2026_06_17_0008` and `2026_06_17_0009`.
- Existing-data database `trade_stage5_gate_existing`: upgraded to `2026_06_16_0007`, inserted deterministic legacy data (`ohlcv_bars=2`, `market_snapshots=1`, `market_snapshot_sections=1`), then upgraded to head.
- Existing-data post-upgrade checks: row counts preserved (`2/1/1`); OHLCV backfilled `exchange` (`SZ`/`SH`), `asset_type=stock`, `frequency=1d`, `adjustment_policy=unadjusted`, `source=legacy_import`, `source_time_reason=provider_time_unavailable`, `event_time=2026-05-15 15:00:00+08`, `available_at=2026-05-15 17:00:00+08`; duplicate OHLCV identity count `0`.
- Existing-data MarketSnapshot checks: snapshot retained `content_fingerprint=fp-market-0925`; section backfilled `trade_date=2026-05-15`, `slot=09-25`, `source_dataset=hot_topics`, `raw_payload_fingerprint=d7e5fe6a0c702d8f8fae58c2fb8ff58a`, `normalization_version=kaipan-normalizer-v2`; duplicate legacy snapshot identity count `0`.
- Existing-data downgrade/recovery: downgrade to `2026_06_16_0007` preserved row counts (`2/1/1`) and restored old OHLCV constraint; re-upgrade to head preserved row counts (`2/1/1`), duplicate OHLCV identity count `0`, required Stage 5 OHLCV null count `0`, required Stage 5 section null count `0`.
- Temporary PostgreSQL databases `trade_stage5_gate_fresh` and `trade_stage5_gate_existing` were dropped after verification.

### Canonical and Legacy Path Review

- Formal data mutations are owned by `/api/ui/v1/system/data/*`, `DataSchedulingService`, and `system-data-operation`.
- Readiness is derived from canonical data facts and repair plan status, not generic job success.
- Duplicate manual/scheduled formal operations are deduplicated by idempotency keys and operation state.
- Formal mutation endpoints require `operator` role and write audit events.
- `SystemDataFacade` remains a thin orchestration/facade layer over domain services; data quality, readiness, and repair logic remain in canonical services.
- Legacy API/UI mutation endpoints for OHLCV/Kaipan are compatibility-only rejected; raw data job/workflow paths are compatibility-only rejected; low-level job creation now also rejects raw Stage 5 data jobs.
- Legacy internal CLI/workflow/tooling retirement remains deferred where deletion would require additional migration, observation, or rollback evidence; current Gate requires no deletion.

### Remaining Non-Blocking Risks

- Legacy internal tooling retirement remains deferred; each path must retain compatibility-only/read-only/rejected behavior until retirement evidence is complete.
- Readiness coverage persistence is still intentionally shallow for Stage 5 and should be deepened if Stage 6 needs historical readiness audit queries.
- Historical Kaipan availability remains truthful but provider/network/credential dependent; deterministic fake providers were used where live upstream evidence was not available.
- No Stage 6 backtest execution, strategy behavior, or future Prompt activation was introduced.

### Next Step

Stage 6 Bootstrap may begin only after explicit user instruction. Do not begin Stage 6 automatically.
