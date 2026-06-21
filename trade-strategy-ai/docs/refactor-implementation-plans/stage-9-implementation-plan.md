# Stage 9 每日盘前实施计划

## Bootstrap Decision

`READY`

本计划只冻结 Stage 9 每日盘前的实现边界、共享契约和 Task Cards。不得在 Bootstrap 中实现生产代码，不得生成 `DailyRuleSelection`、`DailyStrategyInstance` 或 `TradingDayPlan`，不得启动 Stage 10 盘后行为。

## Delegation

使用 `refactor-orchestrator`。

- Parent 决策：本次使用 single-controller fallback，选择 `0` 个 subagent。
- 原因：runtime probe 只能确认 orchestrator skill 和 agent TOML 存在，不能在本会话内证明 native subagent spawning、实际 child model 或 Explorer effective read-only permissions；Bootstrap 产物为文档和契约，Parent 可直接完成 bounded repository mapping。
- 未使用 Executor：Bootstrap 禁止生产代码实现。

## Entry Verification

- Stage 8 Gate：`ACCEPTED`。
- `RT-S8-001 / RT-S8-002 / RT-S8-003`：均为 `ACCEPTED`。
- Stage 9 Bootstrap 前未开始：未发现 `docs/refactor-implementation-plans/stage-9-implementation-plan.md` 或 `docs/refactor-implementation-logs/stage-9.md`。
- Branch：`main`。
- HEAD：`ceee5a55d223b7f3a4124d144a007189fec03647`。
- Bootstrap 前 working tree：clean。
- Bootstrap 前完整 diff：empty。

## Verified Current Facts

### Formal Strategy Center Output

- Formal strategy source-of-truth is canonical `Strategy` + `StrategyVersion` + `StrategyRuleMembership`.
- Current formal strategy is read from `Strategy.current_published_version_id`, which points to the current published `StrategyVersion`.
- Strategy publishing is guarded by `validation_summary.state == "passed"`.
- Strategy validation summary is stored in `StrategyVersion.evidence_json.validation_summary` and can be `not_run / passed / unavailable / partial / invalid / insufficient_coverage / insufficient_sample`.
- `StrategyRevisionProposal` is represented by canonical `OptimizationProposal(proposal_type = strategy_revision)`.
- Proposal acceptance creates or links only a draft `StrategyVersion`; it does not publish and does not modify `Strategy.current_published_version_id`.
- `StrategyVersion` is stable and must not be rebuilt daily.

### Canonical Data Sources

Stage 9 formal flow must consume only canonical:

- `DatasetSnapshot`
- `MarketSnapshot`
- `BacktestRun`
- `BacktestResult`
- `RuleApplicabilityProfile`
- `AuthorProfileVersion(profile_kind = method)`
- `AuthorProfileVersion(profile_kind = rule)`
- `AuthorProfileVersion(profile_kind = validated)`
- `Strategy`
- `StrategyVersion`
- `StrategyRuleMembership`

Existing canonical fields already support most traceability:

- `DatasetSnapshot`: `dataset_snapshot_id`, `content_fingerprint`, `trade_date`, `dataset_type`, `ohlcv_manifest`, `kaipan_manifest`, `market_state_definition_version`, `available_at`, `frozen_at`, `lifecycle_state`, `quality_report_id`, `storage_ref`.
- `MarketSnapshot`: `id`, `snapshot_id`, `trade_date`, `slot`, `quality_status`, `data_quality`, `available_at`, `effective_at`, `frozen_at`, `content_fingerprint`, `manifest_json`.
- `RuleApplicabilityProfile`: `applicability_profile_id`, `rule_version_id`, `dataset_snapshot_id`, `market_snapshot_ids`, `sample_count`, `coverage`, `recommendation_status`, `result_status`, `quality_status`, `insufficient_sample_status`, `applicable_regimes_json`, `blocked_regimes_json`, `neutral_regimes_json`.

### Existing Daily Objects

Stage 2 canonical schema already includes:

- `DailyRuleSelection`
- `DailyRuleSelectionItem`
- `DailyStrategyInstance`
- `TradingDayPlan`
- `Signal`

Current gaps before Stage 9 implementation:

- No formal Stage 9 repository/service/API/client/page exists for daily pre-market readiness, rule selection, daily strategy instance, or trading day plan.
- `/daily/pre-market` currently delegates to the legacy strategy workspace pre-market page.
- The legacy pre-market page submits `snapshot-build` and `run-pre-market` jobs and may resolve `config_path`.
- `/strategies/pre-market` is compatibility-only and points to Stage 9 retirement.
- Legacy `/run/pre_market`, `run-pre-market` Job, ManagerAgent pre-market service, file reports, strategy library objects, live Provider paths, `config_path`, mutable latest records, Job/Workflow/Pipeline/Artifact/file JSON must not be formal Stage 9 inputs.

## Frozen Contracts

### Daily Object Boundaries

- `DailyRuleSelection` is the daily rule-selection output. It is not a formal strategy.
- `DailyStrategyInstance` is a runtime object for one trade date. It is not `StrategyVersion`.
- `TradingDayPlan` is the user-facing daily plan.
- `StrategyVersion` remains stable and is not rebuilt daily.
- Stage 9 must not modify `StrategyVersion`, `Strategy.current_published_version_id`, published/current strategy pointers, author profiles, rule versions, rule applicability profiles, or proposal status.

### Formal Input Contract

Every daily output must trace to:

- `trade_date`
- `strategy_version_id`
- `dataset_snapshot_id`
- `market_snapshot_id`
- current market state / `market_state_id`
- `rule_applicability_profile_ids`
- author method/rule/validated profile version IDs
- data quality state
- deterministic selection reasons

Formal Stage 9 inputs may not come from:

- legacy Job / Workflow / Pipeline / Artifact records
- file JSON reports or snapshot files
- `config_path`
- live Provider calls
- mutable latest records without immutable snapshot IDs
- legacy strategy service or strategy library
- legacy backtest service or compatibility views
- `strategy-studio` / `optimize` legacy paths

### Availability And Missing Data Contract

- Missing data remains `unavailable`, `partial`, `conflict`, `invalid`, `insufficient_coverage`, or `degraded`.
- Missing data must never be converted to `false`, `0`, empty success, or condition satisfied.
- Repair actions may link to existing system-management repair paths, but Stage 9 Bootstrap does not authorize broad Stage 11 scheduling or automation.
- Daily generation must not call live Providers. If canonical snapshot coverage is missing, expose repair/degraded/blocked state.

### Deterministic Rule Selection Contract

`RT-S9-002` must evaluate rule decisions using this priority:

1. formal rule applicability
2. current market state
3. formal strategy
4. data quality
5. author validated profile
6. author method profile

Each rule decision must record:

- rule version ID and strategy membership ID when available
- selected / reduced / suspended decision
- decision tier that controlled the outcome
- evidence IDs and quality states used
- explicit reason list
- unresolved or degraded inputs

If the priority cannot be represented deterministically, implementation must stop and escalate.

## Task Order

1. `RT-S9-001 自动前置检查`
2. `RT-S9-002 每日规则选择`
3. `RT-S9-003 每日策略实例和盘前计划`

Combination rule:

- `RT-S9-001` + `RT-S9-002` may be implemented in the same Task Session only if frozen contracts remain stable and work is done serially.
- `RT-S9-003` must be implemented later as a separate Task Session.
- Stage 9 must not be combined with Stage 10.

## Task Card: RT-S9-001 自动前置检查

- Risk：`M3` source-of-truth, data readiness, time semantics.
- Target：create the formal pre-market readiness check for a `trade_date`.
- Current facts：canonical data/strategy/profile/applicability tables exist; no formal Stage 9 readiness service/API/UI exists; current daily page uses legacy job workspace.
- Frozen contracts：consume canonical snapshots, current published strategy, formal rule applicability, author profile versions, and validated data-quality state only.
- Allowed paths：new Stage 9 repository/service/API/schema/client/page/tests under existing backend/API/web/test structure; focused route update for `/daily/pre-market`; docs/log updates.
- Forbidden paths：legacy Job/Workflow/Pipeline/Artifact/file JSON, `config_path`, live Provider calls, legacy strategy/backtest services, broad Stage 11 scheduler automation, Stage 10 post-market behavior.
- Expected user-visible result：今日盘前 page can show ready/degraded/blocked pre-check status in business Chinese, including what happened, impact, and repair next step.
- Backend/API/frontend/database/doc scope：read-only canonical checks first; migration only if existing schema cannot persist required immutable references or status without overloading JSON.
- Focused tests：backend service readiness states; API contract; frontend loading/empty/error/partial/permission_denied/unavailable; legacy isolation grep; `git diff --check`.
- Special verification：prove no formal input comes from legacy job/report/config/live provider paths; prove non-ready canonical coverage remains unavailable/degraded/blocked.
- Escalation triggers：schema/source-of-truth change beyond frozen contracts; need live Provider; need legacy fallback; second formal data source; Stage 11 automation beyond linking repair.
- Acceptance criteria：automatic checks cover Kaipan pre-market data, latest OHLCV, current market state, current formal strategy, rule applicability, author validated profile, and data quality; result is traceable and user actionable.

## Task Card: RT-S9-002 每日规则选择

- Risk：`M3` deterministic selection, formal strategy boundary.
- Target：generate `DailyRuleSelection` from the accepted readiness result and current formal strategy.
- Current facts：`DailyRuleSelection` and item tables exist, but no formal selection service/API/UI exists.
- Frozen contracts：daily selection is not strategy publication; `StrategyVersion` and current pointer remain unchanged; selection priority is fixed.
- Allowed paths：Stage 9 service/repository/API/client/UI/tests; use canonical `DailyRuleSelection` and `DailyRuleSelectionItem`.
- Forbidden paths：modifying formal strategy/version/rule/profile/proposal status; legacy strategy selection artifacts; mutable latest applicability records without selected canonical profile IDs; live Provider calls.
- Expected user-visible result：page explains enabled, reduced, and suspended rules with reasons and degraded inputs.
- Backend/API/frontend/database/doc scope：persist selection revision with traceability to strategy version, market state, dataset snapshot, market snapshot, applicability profile IDs, author profile version IDs, data quality state, and selection reasons.
- Focused tests：selection priority table tests; unavailable/partial/conflict/insufficient coverage cases; API response traceability; frontend reason display; legacy isolation grep; `git diff --check`.
- Special verification：same inputs produce same decisions and same ordered reason tiers; missing applicability cannot become selected by default.
- Escalation triggers：priority cannot be deterministic; selection requires changing `StrategyVersion`; canonical coverage insufficient and implementation tries legacy fallback; second formal daily-selection fact source appears.
- Acceptance criteria：`DailyRuleSelection` generated only from canonical inputs, decisions are deterministic and traceable, and user-visible page separates enabled/reduced/suspended rules.

## Task Card: RT-S9-003 每日策略实例和盘前计划

- Risk：`M3` runtime object, user-facing plan, Stage 10 boundary.
- Target：generate `DailyStrategyInstance` and `TradingDayPlan` from an accepted daily rule selection.
- Current facts：canonical tables exist; current daily page still uses legacy run-pre-market job output and file report semantics.
- Frozen contracts：daily instance is runtime-only; plan is user-facing; no StrategyVersion rebuild; no post-market evaluation or optimization proposal generation.
- Allowed paths：Stage 9 service/repository/API/client/UI/tests; optional bounded migration only for missing traceability that cannot be represented safely in current schema.
- Forbidden paths：Stage 10 signal result evaluation, post-market attribution, Rule/Author/Strategy proposals, live Provider calls, strategy current pointer updates, author/rule/profile overwrites.
- Expected user-visible result：今日盘前 page displays 今日市场判断、启用规则、暂停规则、候选标的、信号、入场条件、失效条件、止盈止损、建议仓位、风险提示、置信度 and approval/rejection state.
- Backend/API/frontend/database/doc scope：persist daily runtime instance and plan revision; connect generated signals to plan/instance where needed; expose approval/rejection without touching formal strategy.
- Focused tests：service generation from selection; plan payload validation; API contract; frontend full state rendering; no Stage 10 writes; no StrategyVersion/profile/rule mutation; `git diff --check`.
- Special verification：plan traces all inputs and unavailable fields remain unavailable, not silently omitted or defaulted.
- Escalation triggers：daily instance needs to modify formal strategy/version; live Provider required; Stage 10 becomes necessary; schema/source-of-truth changes beyond frozen contract.
- Acceptance criteria：user can review and approve/reject a daily plan that is fully traceable, clearly marked as daily runtime output, and separate from formal strategy and post-market behavior.

## Gates And Validation Plan

Task-level validation:

- focused backend unit/service tests
- API/router/OpenAPI tests
- frontend client/page tests
- migration tests if schema changes
- legacy isolation grep for formal Stage 9 paths
- `git diff --check`

Stage 9 Gate validation:

- all RT-S9-001/002/003 acceptance criteria pass
- `/daily/pre-market` uses formal Stage 9 flow, not legacy job/file report as the official source
- `/strategies/pre-market` and `/workflows/pre-market*` are compatibility-only or redirected per route contract
- no Stage 10 objects or proposals are generated
- daily outputs are traceable to immutable canonical IDs and quality states
- user-visible errors explain what happened, what is affected, and how to repair or proceed

## Risks And Blockers

Blocking at Bootstrap：none.

Non-blocking risks for implementation:

- Existing daily pre-market UI is legacy workspace-based and must be replaced or isolated carefully.
- Current daily canonical tables may need additional traceability fields; if JSON payload is insufficient or unsafe, schema change must be escalated and migrated.
- `DailyRuleSelection.lifecycle_state` lacks explicit degraded/blocked states; implementation can use `quality_status` and payload state if contract remains clear, otherwise escalate.
- `MarketSnapshot.slot` currently uses values such as `17-30`; Stage 9 must explicitly select pre-market slot semantics and not reuse post-market snapshots by accident.
- Current `StrategyRepository.list_ready_dataset_snapshots()` and `list_market_snapshots()` are broad list helpers; Stage 9 may need date/slot-specific canonical queries.
