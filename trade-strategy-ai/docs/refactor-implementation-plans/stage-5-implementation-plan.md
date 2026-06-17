# Stage 5 基础数据、数据调度与数据质量实施计划

## 1. Stage 5 目标和权威来源

Stage 5 目标是在不进入 Stage 6 回测执行的前提下，建立稳定、可追溯、可修复的 OHLCV、Kaipan、指标、市场状态和系统数据调度底座。

权威来源：

- `docs/Trade-Refactor-TaskList.md`
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
- `docs/AI-Conversation-Templates.md`
- `docs/AI-Conversation-Project-Constraints-1.md`
- `docs/AI-Conversation-Project-Constraints-2.md`
- `docs/AI-Conversation-Task-Matrix.md`
- `docs/Refactor-Implementation-Log.md`
- `docs/refactor-implementation-logs/stage-4.md`
- Stage 2 canonical domain and migration contracts
- Stage 4 Gate accepted evidence and Pre-Stage-5 cleanup evidence

Bootstrap only produced this plan and log updates. It did not implement `RT-S5-001`, `RT-S5-002`, or `RT-S5-003`.

## 2. Accepted Stage 4 Entry Conditions

- Stage 4 Gate decision is `ACCEPTED`.
- Pre-Stage-5 cleanup review is verified and fixed.
- Canonical writer only remains in force.
- No dual-write or legacy writer fallback may be restored.
- Fixed-set gate remains intact for rule-governance mutations.
- Revision-bound provenance and truthful unavailable semantics remain accepted contracts.
- Stage 5 may start only after explicit user authorization; that authorization was provided for Bootstrap only.

## 3. Repository and Working-Tree Baseline

- Repository: `xiyuxifeng/Trade`
- Project root: `trade-strategy-ai`
- Branch: `main`
- HEAD: `a72243a644d2b404ba8117458f7813e856a3b556`
- Working tree before Bootstrap edits: clean
- Bootstrap changes: documentation only under `docs/`
- Subagent use: three bounded read-only Explorer agents were used for OHLCV/snapshot, Kaipan/market-state, and scheduler/system-management inspection.

## 4. Exact Stage 5 Tasks

### RT-S5-001 OHLCV 数据体系

Implement historical backfill, daily post-close incremental update, stock/index/ETF support, trading-calendar-aware gap detection, repair/backfill, indicator update, canonical `DatasetSnapshot`, and fixed data versions for later backtests.

### RT-S5-002 Kaipan 数据体系

Implement pre-market and post-market ingestion and normalization, `MarketSnapshot`, coverage and data-quality states, historical backfill when available, and truthful limitation states when historical Kaipan is unavailable.

### RT-S5-003 调度和系统管理

Create the formal `系统管理 -> 数据与调度` surface. Normal users see readiness, latest update, missing coverage, impact, and one-click repair. Administrators may update now, backfill a date range, recompute indicators, recompute market state, and inspect failures/logs.

## 5. Current-State Findings and Conflicts

- OHLCV currently persists to `ohlcv_bars` with unique `(symbol, trade_date)`, but rows lack explicit asset type, exchange, frequency, adjustment, source time, ingestion time, availability time, provider provenance, and quality state.
- `OHLCVService._upsert_bars()` currently coerces missing numeric fields to `0.0` for core price/volume fields. Stage 5 must replace this with validation and rejected/partial records; missing data must not become zero.
- `OHLCVService` supports a historical date range, but there is no dedicated trading-calendar-aware gap repair planner.
- `AkshareProvider` accepts adjustment options, but OHLCV persistence does not store adjustment policy.
- `dataset_snapshots` is the Stage 2 canonical `DatasetSnapshot` source. Runtime code still reads through `MarketDataset` / `market_datasets`, which is now a compatibility view. Stage 5 must close this runtime mismatch through a canonical repository/service path, not by re-enabling compatibility writes.
- `market_snapshots` and its sections/items/quality reports are the canonical structured snapshot family.
- `market_universe` file snapshots, `data/kaipan/snapshots`, and `market_state.json` remain live compatibility/file paths.
- Current Kaipan flow separates fetch and normalize, supports `09-25` and `17-30`, and records partial states, but lacks frozen dataset-by-dataset provenance and stable availability semantics.
- Market-state internals still use `regime` naming. This is allowed internally as compatibility, but normal user UI must show `市场状态`.
- Scheduler control is fragmented across JobRunner, MarketService scheduler, KaipanService scheduler, pipeline scheduler, workflow service, CLI scheduler, and article pipeline schedule service.
- Current user-facing market/system pages still expose terms such as `Job`, `Job Center`, `kaipan-fetch`, `kaipan-normalize`, `ohlcv-crawl`, `market-state-build`, and `snapshot-build`.

## 6. Frozen Data, Time, and Snapshot Contracts

### Trading Date and Timezone

- Canonical market is `CN` unless explicitly extended.
- `trade_date` is a China market trading date in `Asia/Shanghai`.
- Scheduling decisions use `Asia/Shanghai`.
- Runtime timestamps are timezone-aware UTC unless they represent a market-local trading date.
- Calendar decisions must use a market calendar, not contiguous natural days.
- Weekend/holiday dates are not silently treated as missing trading data.

### Market and Calendar Boundaries

- Supported Stage 5 market boundary is China A-share style daily data.
- OHLCV must support stock, index, and ETF.
- `StockInfo` can assist asset classification, but Stage 5 must persist classification/provenance instead of relying only on symbol inference.
- All backfill and repair ranges must report requested range, effective trading-day range, skipped non-trading days, and unavailable dates.

### Event, Source, Ingestion, and Availability Time

Each formal data record or snapshot must distinguish:

- `event_time`: time the market event belongs to when available.
- `source_time`: time provided by upstream source or derived from source payload.
- `captured_at`: time the system fetched or observed raw input.
- `ingested_at`: time normalized data was written to canonical storage.
- `available_at`: earliest time downstream consumers may legally use the data.

If a source does not provide a time, the field remains unavailable with reason; it is not copied from another field without provenance.

### No Future-Data Leakage

- A process for `trade_date=D` must not use data with `available_at` after the decision time being produced.
- Pre-market outputs may use only pre-market Kaipan slots and prior completed OHLCV/indicators/market-state data.
- Post-close outputs may use close data only after post-close availability.
- Stage 6 backtests must later bind to immutable snapshots and must not call live providers; Stage 5 only prepares the data contracts and snapshots.

### Symbol, Asset, Exchange, Frequency, and Adjustment

- Symbol identity must include canonical symbol, exchange, asset type, and source symbol.
- OHLCV frequency must be explicit. Stage 5 scope is daily OHLCV unless explicitly extended later.
- Adjustment policy must be explicit: unadjusted, forward adjusted, backward adjusted, or unknown.
- Unknown adjustment policy blocks formal readiness for backtest datasets unless the user sees a truthful limitation.

### Idempotency, Deduplication, Gap Detection, Repair, and Retry

- Ingestion idempotency key must include source, market, symbol, asset type, exchange, frequency, adjustment policy, trade_date, source payload fingerprint, and source version when available.
- Re-ingesting the same source payload is a no-op or version-equivalent observation, not a duplicate formal row.
- Conflicting payloads for the same identity create a quality conflict and require explicit repair or new versioning.
- Gap detection must be trading-calendar-aware.
- Repair is allowed through explicit user/admin actions and scheduled health checks.
- Retry must record attempt count, reason, failure classification, and last error without hiding partial success.

### Data-Quality and Coverage States

Allowed formal states:

- `ready`
- `partial`
- `missing`
- `invalid`
- `conflict`
- `insufficient_coverage`
- `unavailable`

Missing data is never converted to `false`, `0`, condition-not-met, or success.

### DatasetSnapshot and MarketSnapshot

- `DatasetSnapshot` formal source is `dataset_snapshots`.
- `MarketSnapshot` formal source is `market_snapshots` and child tables.
- Snapshots are immutable once `frozen_at` is set.
- Recomputing creates a new version/fingerprint, not an in-place mutation of a frozen snapshot.
- Snapshots must include content fingerprint, data versions, market, date/range, source manifests, quality report, and provenance.
- `market_datasets` is compatibility read-only and must not become a writer while canonical writer routing is enabled.

### Provenance and Source Metadata

Every formal Stage 5 output must record:

- provider/source name;
- provider/source version when known;
- raw source reference or fingerprint;
- normalization version;
- code version or service version where available;
- market calendar version;
- run ID or operation ID;
- operator/system actor;
- coverage and quality state.

### Truthful Unavailable and Degraded Behavior

- If a source is unavailable, users see what happened, what is affected, and how to repair or proceed in degraded mode.
- Degraded mode must state which downstream operations are blocked or limited.
- Historical Kaipan unavailability is a limitation, not a failed OHLCV condition.

## 7. In-Scope and Out-of-Scope Behavior

In scope:

- OHLCV ingestion, backfill, incremental update, gap detection, repair, provenance, and DatasetSnapshot contract.
- Kaipan pre/post-market ingestion, normalization, coverage, quality, and MarketSnapshot contract.
- Indicator recompute boundary and market-state recompute boundary.
- Data readiness API/contract for normal users and administrators.
- Scheduler and system-management design boundary for Stage 5.
- Compatibility and retirement rules for old data/scheduler surfaces.

Out of scope:

- Stage 6 backtest execution.
- RuleApplicabilityProfile computation.
- Strategy publication or daily trading plan generation.
- Future Prompt activation.
- Replacing all internal `regime` code names solely for translation.
- Deleting legacy routes before migration, observation, and rollback evidence exist.

## 8. Database and Migration Impact

Expected migrations:

- Add OHLCV provenance/time/quality fields or a companion raw/provenance table.
- Persist symbol identity fields: canonical symbol, source symbol, exchange, asset type, frequency, adjustment policy.
- Add or repair canonical DatasetSnapshot repository/runtime path over `dataset_snapshots`.
- Add OHLCV coverage/gap/repair records or a general data coverage table.
- Add Kaipan raw/normalized provenance, source time, slot, coverage, and availability fields where current file-only metadata is insufficient.
- Ensure MarketSnapshot immutability/versioning fields are complete and enforced.
- Add scheduler/run metadata needed by the formal data-readiness API only after RT-S5-001/002 contracts are stable.

Migration requirements:

- Safe rerun.
- No silent data loss.
- Pre/post counts for OHLCV, indicators, market snapshots, dataset snapshots, Kaipan raw/normalized records, and quality reports.
- Rejected/conflict rows preserve raw payload references and reasons.
- Downgrade/recovery path documented and tested.

## 9. OHLCV Design Boundary

RT-S5-001 owns:

- canonical daily OHLCV identity and quality contract;
- historical backfill and daily post-close incremental update;
- stock/index/ETF support;
- trading-calendar-aware gap detection and repair;
- indicator recompute after data repair;
- canonical DatasetSnapshot creation over OHLCV and indicators;
- Stage 6 support contract without running Stage 6 backtests.

RT-S5-001 must not:

- treat missing values as zero;
- use live providers during snapshot-bound downstream reads;
- publish backtest conclusions;
- rely on `market_datasets` writes.

## 10. Kaipan Design Boundary

RT-S5-002 owns:

- `09-25` pre-market and `17-30` post-close slot semantics;
- raw capture and normalization provenance;
- slot-specific source/captured/ingested/available times;
- coverage/quality states by dataset and section;
- canonical MarketSnapshot freezing;
- historical backfill when source data is actually available;
- truthful historical limitation when it is not.

RT-S5-002 must not:

- merge pre-market and post-close data without slot provenance;
- infer missing historical Kaipan;
- let missing Kaipan become a false rule condition;
- create a second formal MarketSnapshot entry point.

## 11. Indicator and Market-State Boundary

- Indicators are derived from canonical OHLCV only.
- Indicator recompute must record input OHLCV fingerprint/range, indicator version, and computed_at.
- Market-state generation depends on canonical MarketSnapshot and indicator/OHLCV coverage.
- Stage 5 may recompute market-state records to verify data readiness, but it must not compute rule applicability or backtest performance.
- User-facing text is `市场状态`; internal `regime` names remain compatibility-only until a later planned rename/retirement.

## 12. Scheduling and System-Management Boundary

RT-S5-003 is later and separate.

Stage 5 target surface:

```text
系统管理
→ 数据与调度
```

Normal users see:

- data readiness;
- latest update;
- missing coverage;
- impact;
- one-click repair.

Administrators may:

- update now;
- backfill a date range;
- recompute indicators;
- recompute market state;
- inspect failures/logs.

Implementation boundary:

- Prefer a thin Stage 5 data-readiness/system-management facade over existing MarketService and KaipanService internals.
- Do not let normal users choose raw job types.
- Keep JobRunner/job registry as internal execution infrastructure until formal retirement criteria pass.
- Scheduler unification must not start before RT-S5-001/002 data contracts are stable.

## 13. Compatibility and Retirement Rules

Compatibility-only until verified retirement:

- `/market`, `/market/kaipan`, `/market/ohlcv`, `/market/snapshots`, `/market/datasets`
- `/api/ui/v1/kaipan/*`
- `/api/ui/v1/market/ohlcv/run|stop|status`
- legacy `/api/ui/v1/snapshots` and public `/snapshots`
- file-based `market_universe` snapshots
- `market_datasets` compatibility view
- technical job/workflow/pipeline/artifact pages

Retirement requires:

- new formal route/API is available;
- all consumers migrated or compatibility adapters documented;
- reference scan has no formal dependency;
- tests cover old route as redirect/compatibility-only or removed;
- rollback/recovery evidence exists;
- no second formal entry point remains.

## 14. Task Dependency Graph and Execution Order

Recommended order:

1. `RT-S5-001` OHLCV data体系.
2. `RT-S5-002` Kaipan data体系.
3. `RT-S5-003` 调度和系统管理.
4. Stage 5 Gate.

`RT-S5-001` and `RT-S5-002` may share one Parent session in separate acceptance batches if the Parent keeps contracts frozen between batches and does not start `RT-S5-003` early.

`RT-S5-003` must remain later because its UI/actions depend on stable OHLCV and Kaipan readiness/repair contracts.

## 15. Per-Task Acceptance Criteria

### RT-S5-001

- Historical backfill and daily post-close incremental update work for stock, index, and ETF.
- OHLCV rows preserve identity, frequency, adjustment, source, captured/ingested/available times, and quality.
- Gap detection is trading-calendar-aware.
- Repair/backfill is idempotent, retryable, and auditable.
- Indicators recompute from canonical OHLCV and record version/provenance.
- Canonical DatasetSnapshot is immutable/versioned/traceable.
- Missing/conflicting data is explicit and blocks or degrades downstream use truthfully.
- Stage 6 receives a snapshot contract but no Stage 6 backtest is run.

### RT-S5-002

- Pre-market and post-close Kaipan data remain slot-separated.
- Raw and normalized records preserve source/captured/ingested/available times.
- MarketSnapshot is immutable/versioned/traceable.
- Coverage and quality states are visible at dataset/section level.
- Historical availability and limitations are explicit.
- Missing Kaipan never becomes false or zero.
- No duplicate formal MarketSnapshot source is created.

### RT-S5-003

- Formal entry is `系统管理 -> 数据与调度`.
- Normal users see business-language readiness, impact, and repair actions.
- Administrators can update, backfill, recompute indicators, recompute market state, inspect failures/logs.
- User-facing copy avoids `Job`, `Workflow`, `Pipeline`, `Artifact`, `Provider`, `Schema`, `CLI`, table names, file paths, `kaipan-fetch`, `kaipan-normalize`, `ohlcv-crawl`, and `market-state-build`.
- Runtime assurance records run ID, steps, duration, errors, retries, data ranges, coverage, and time semantics.
- Legacy technical surfaces are compatibility-only with retirement criteria.

## 16. Test, Migration, Rollback, Recovery, and Operational Verification

Required verification categories:

- Unit tests for OHLCV identity, adjustment, time semantics, gap detection, repair idempotency, and indicator recompute.
- Unit tests for Kaipan slot separation, provenance, normalization, coverage, and unavailable states.
- API tests for readiness, missing coverage, repair requests, partial/unavailable responses, and permission boundaries.
- Database migration upgrade/downgrade/re-upgrade tests.
- Existing-data migration tests with pre/post counts and rejected/conflict reports.
- Frontend tests for loading, empty, error, partial, permission denied, unavailable, business Chinese, and no forbidden normal-user terms.
- Scheduler/service tests for idempotency, retry, resume, and no duplicate runs.
- `git diff --check`.
- Stage 5 Gate must include operational evidence with at least one successful backfill/update, one missing-data report, one repair, and one snapshot freeze.

If a verification cannot run, the implementation log must record the skipped command, reason, alternative checks, and residual risk.

## 17. Stage 5 Gate Evidence

Gate must prove:

- All three Stage 5 tasks are represented and accepted.
- `RT-S5-003` started only after data contracts stabilized.
- No Stage 6 backtest execution was pulled in.
- Time semantics and no-future-data-leakage rules are explicit in code/tests/docs.
- DatasetSnapshot and MarketSnapshot are immutable, versioned, and traceable.
- Missing data remains truthful.
- There is no second formal data source or duplicate formal entry point.
- Normal-user surfaces avoid internal technical terms.
- Rollback/recovery evidence exists for migrations and failed operations.

## 18. Risks, Mitigations, and Non-Blocking Risks

Blocking risks before RT-S5-001 acceptance:

- Runtime code still reads datasets through `MarketDataset` / `market_datasets` compatibility.
- OHLCV values can currently be coerced to zero.
- No trading-calendar-aware OHLCV repair planner exists.
- Adjustment policy is not persisted.

Mitigations:

- Build canonical DatasetSnapshot runtime repository/service over `dataset_snapshots`.
- Replace missing numeric coercion with validation and quality/rejection paths.
- Add calendar-aware gap/repair service.
- Persist adjustment policy and block unknown policy where required.

Non-blocking risks:

- Some internal code names still use `regime`.
- Legacy file artifacts remain as transitional storage references.
- Live-provider integration may be limited by credentials/network and should have fake-provider deterministic tests plus optional manual operational evidence.

## 19. Recommended Model and Prompt Strategy

- Stage 5 Bootstrap / Gate / contract changes: Parent `gpt-5.5`.
- RT-S5-001 and RT-S5-002 implementation sessions: Parent `gpt-5.4` with at most one bounded Executor after contracts are frozen.
- RT-S5-003: separate Parent session after RT-S5-001/002 accepted.
- Use Explorers only for bounded read-heavy inspection.
- No LLM Prompt runtime changes are in Stage 5 scope.

## 20. Exact Next Prompt for RT-S5-001

```text
$refactor-orchestrator Use the refactor-orchestrator skill.

Perform RT-S5-001 only for trade-strategy-ai.

Repository:
- xiyuxifeng/Trade
- project root: trade-strategy-ai

Current state:
- Stage 4 Gate: ACCEPTED
- Pre-Stage-5 Cleanup Review: VERIFIED_AND_FIXED
- Stage 5 Bootstrap: READY
- Stage 5 implementation plan: docs/refactor-implementation-plans/stage-5-implementation-plan.md

Task:
- RT-S5-001 OHLCV data system only.

Do not implement RT-S5-002 or RT-S5-003.
Do not run Stage 6 backtests.
Do not activate future Prompt behavior.

Required reading:
- docs/Trade-Refactor-TaskList.md
- docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md
- docs/AI-Conversation-Templates.md
- docs/AI-Conversation-Project-Constraints-1.md
- docs/AI-Conversation-Project-Constraints-2.md
- docs/AI-Conversation-Task-Matrix.md
- docs/refactor-implementation-plans/stage-5-implementation-plan.md
- docs/Refactor-Implementation-Log.md
- docs/refactor-implementation-logs/stage-5.md
- current OHLCV, indicator, DatasetSnapshot, MarketSnapshot, scheduler/job, API, Web, database, migration, and tests

Preserve:
- canonical writer only
- no dual-write or legacy writer fallback
- fixed-set gate for rule-governance mutations
- truthful unavailable/degraded semantics
- no fabricated data, coverage, snapshot, market state, or readiness
- no second formal data source or duplicate formal entry point

Implement RT-S5-001 end-to-end:
- daily OHLCV identity for stock/index/ETF
- trading-date and Asia/Shanghai scheduling semantics
- explicit source/event/captured/ingested/available time semantics
- source, asset type, exchange, frequency, and adjustment semantics
- idempotent historical backfill and daily post-close incremental update
- trading-calendar-aware gap detection and repair
- retry/resume behavior
- data quality and coverage states
- indicator recompute boundary
- canonical immutable/versioned DatasetSnapshot over dataset_snapshots
- Stage 6 support contract without Stage 6 execution
- user/admin API and Web readiness/repair behavior only as needed for RT-S5-001
- tests, migration, rollback/recovery evidence, and implementation log update

Before completion:
- verify missing OHLCV is not false/zero/success
- verify no future-data leakage rules are explicit
- verify DatasetSnapshot is immutable/versioned/traceable
- verify market_datasets remains compatibility-only
- verify no RT-S5-002/003 or Stage 6 behavior was pulled in
- update docs/Refactor-Implementation-Log.md and docs/refactor-implementation-logs/stage-5.md

Do not commit or push.
```
