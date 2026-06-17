# Stage 5 基础数据、数据调度与数据质量实施日志

## Current Status

- Stage：`Stage 5 基础数据、数据调度与数据质量`
- Stage 状态：`[-] 进行中`
- 当前活动：`2026-06-17 Stage 5 Bootstrap` 已完成。
- Bootstrap 决策：`READY`
- 下一可执行 Task：`RT-S5-001 OHLCV 数据体系`
- 不得自动开始：`RT-S5-001` 需要用户明确授权。
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

Updated:

- `docs/Refactor-Implementation-Log.md`

### Bootstrap Conclusion

`READY`

`RT-S5-001` may begin after explicit user authorization. Do not begin `RT-S5-001` automatically.
