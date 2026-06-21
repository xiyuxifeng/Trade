# Stage 10 每日盘后实施计划

## Bootstrap Decision

`READY`

本计划只冻结 Stage 10 每日盘后的实现边界、共享契约和 Task Cards。不得在 Bootstrap 中实现生产代码，不得评估信号结果，不得生成归因，不得生成 `RuleOptimizationProposal`、`AuthorProfileRevisionProposal` 或 `StrategyRevisionProposal`，不得启动 Stage 11 系统自动化或告警行为。

## Delegation

使用 `refactor-orchestrator`。

- Parent 决策：本次委派 2 个 read-only `refactor_explorer_mini`。
- Explorer Alpha：审计 Stage 9 canonical runtime outputs、traceability、legacy input 隔离和相关测试。
- Explorer Gamma：审计 Stage 10 post-market/proposal/UI/API/database surfaces、strategy/proposal 边界和 legacy after-close 路径。
- 未使用 Executor：Bootstrap 禁止生产代码实现。
- Parent 保留契约冻结、Task Card、风险分类和正式文档更新。

## Entry Verification

- Stage 9 Gate：`ACCEPTED`。
- `RT-S9-001 / RT-S9-002 / RT-S9-003`：均为 `ACCEPTED`。
- Stage 10 Bootstrap 前未开始：Stage 9 日志确认未新增 Stage 10 table/service/API/UI，未生成 signal result evaluation、post-market attribution 或 proposal。
- Branch：`main`。
- HEAD：`c2df735c025ea952e065fabeb2a5e693f83cbc7d`。
- Bootstrap 前 working tree：clean。
- Bootstrap 前完整 diff：empty。

## Verified Current Facts

### Formal Stage 9 Outputs

Current formal Stage 9 outputs are canonical:

- `DailyRuleSelection`
- `DailyRuleSelectionItem`
- `DailyStrategyInstance`
- `TradingDayPlan`
- `Signal`

Traceability is available through canonical IDs and bounded JSON payload:

- `DailyRuleSelection` stores `strategy_version_id`, `market_state_id`, `trade_date`, `revision_no`, rule decision JSON, `quality_status`, and `lifecycle_state`.
- `DailyRuleSelectionItem` stores `daily_rule_selection_id`, `rule_version_id`, decision, and payload.
- `DailyStrategyInstance` stores `strategy_version_id`, `daily_rule_selection_id`, `market_snapshot_id`, `trade_date`, `revision_no`, runtime payload, and lifecycle state.
- `TradingDayPlan` stores `daily_strategy_instance_id`, `trade_date`, `revision_no`, payload, lifecycle state, and approval fields.
- `Signal` stores canonical `strategy_version_id`, `trading_day_plan_id`, `daily_strategy_instance_id`, `rule_version_ids`, `signal_state`, `decision_mode`, degradation fields, and compatibility-only `legacy_strategy_version_id`.

Stage 9 residual risks carried forward:

- `DailyRuleSelection` / `TradingDayPlan` top-level traceability lives in canonical JSON payload, not independent columns. This remains acceptable unless Stage 10 cannot safely trace or test signal outcomes and attribution.
- `/daily/overview` still has compatibility-only job summary cards. Stage 10 must not use them as formal input or formal output.
- Browser-level E2E was not run in Stage 9. Stage 10 implementation should add focused UI tests and decide at Gate whether browser E2E evidence is needed.
- `DailyRuleSelectionRepository.create_selection()` canonical write guard hardening remains non-blocking unless it directly blocks post-market correctness.

### Formal Strategy And Proposal Boundaries

- Formal strategy source-of-truth is canonical `Strategy` + `StrategyVersion` + `StrategyRuleMembership`.
- Current strategy is `Strategy.current_published_version_id` pointing to a published `StrategyVersion`.
- `StrategyVersion` is formal and is not regenerated daily.
- `DailyStrategyInstance` is runtime-only and cannot become a formal strategy.
- `OptimizationProposal` already supports `proposal_type` values:
  - `rule_optimization`
  - `author_profile_revision`
  - `strategy_revision`
- Existing canonical strategy service/UI currently handles `OptimizationProposal(proposal_type = strategy_revision)`.
- Existing strategy proposal acceptance can create or link only draft `StrategyVersion`; it does not publish and does not mutate `Strategy.current_published_version_id`.
- No active formal API/UI was found for `rule_optimization` or `author_profile_revision`.

### Current Stage 10 Surface

- Canonical table `post_market_reviews` exists as `PostMarketReview`.
- Canonical table `optimization_proposals` exists as `OptimizationProposal`.
- No dedicated formal `PostMarketReview` service/API/page was found.
- `/daily/after-close` is a canonical product route, but it currently wraps a legacy job/report based after-close workspace.
- `/workflows/after-close`, `/workflows/after-close/run`, and `/strategies/after-close` are compatibility-only paths pointing toward `/daily/after-close`.
- Existing postmortem/evaluation code has programmatic attribution and registered Stage 10 prompts, but future-stage LLM prompt path is inactive.

## Frozen Contracts

### RT-S10-001 Contract Escalation Decision

`Decision 1` is frozen for resumed `RT-S10-001`:

```text
Formal canonical post-close actual snapshot source is required and sufficient
for signal outcome metrics. Approved imported actuals are optional supplement
for execution-specific fields only.
```

Rationale:

- Current `DatasetSnapshot` freezes manifest, content fingerprint, row fingerprints, availability and storage metadata, but does not expose a formal read API that returns immutable per-symbol actual OHLCV values for every signal.
- Current `MarketSnapshot` / `MarketSnapshotSection` / `MarketSnapshotItem` can store structured market facts and symbol-tagged generic items, but existing builders only establish benchmark OHLCV and market-level sections. No formal post-close signal-symbol actuals section exists.
- Current `TradeLog` stores executed trade rows, but lacks approval/review, immutable import fingerprint, Signal/TradingDayPlan binding, conflict handling and coverage for unexecuted signals.
- Legacy postmortem/backtest/ranking code may contain reusable formulas, but it is not a formal Stage 10 source-of-truth and must not be used as formal input.

Rejected alternatives:

- `Decision 2` is rejected for the current repository state. Approved imported actuals are not sufficient unless expanded to cover every signaled symbol with immutable post-close OHLCV evidence and approval/fingerprint semantics. Current `trade_logs` do not satisfy that contract and cannot cover unexecuted signal close/MFE/MAE/return.
- `Decision 3` is not selected. The contract can be made safe inside Stage 10 by adding a bounded canonical post-close actual snapshot contract before outcome evaluation, without starting Stage 11. This is a Stage 10 source contract addition, not outcome implementation.

### Formal Post-Close Actual Snapshot Contract

Resumed `RT-S10-001` must first implement a bounded formal actuals source before computing outcomes. The source may be represented as:

```text
Option A: new canonical MarketSnapshot section/item contract for post-close
symbol OHLCV actuals.
```

Option A is preferred because `PostMarketReview.market_snapshot_id` already links to a post-close `MarketSnapshot`, and the existing snapshot/section/item tables already carry snapshot identity, section quality, item symbols, content fingerprints and frozen timestamps.

The exact frozen section contract is:

- Section ID: `post_close_symbol_ohlcv_actuals`.
- Snapshot slot: post-close slot, normally `17-30`, for the same `trade_date` as the approved `TradingDayPlan`.
- One item per required `symbol + trade_date` from the approved plan's pre-market `Signal` rows.
- Item `symbol` must equal the canonical signal symbol.
- Item `item_key` must be stable, e.g. `post_close_symbol_ohlcv_actuals:{symbol}:{trade_date}`.
- Item payload must include `symbol`, `trade_date`, `open`, `high`, `low`, `close`, optional `previous_close`, `volume`, `turnover`, `exchange`, `asset_type`, `frequency`, `adjustment_policy`, `source`, `source_time`, `captured_at`, `ingested_at`, `available_at`, `frozen_at`, `dataset_snapshot_id`, `dataset_content_fingerprint`, `row_fingerprint`, `quality_state`, `availability_state`, and `evidence_window`.
- Section payload/manifest must bind the contributing `DatasetSnapshot.dataset_snapshot_id`, `DatasetSnapshot.content_fingerprint`, row count, missing/conflict symbols, quality summary and actuals contract version.
- `MarketSnapshot.content_fingerprint` and section `raw_payload_fingerprint` must cover the actual rows and their dataset binding.
- If daily-bar approximation is used for intraday high/low, the payload must explicitly set `evidence_window = "daily_bar"` and `intraday_approximation = true`. If an intraday window is later available, it must use a separate documented `evidence_window` value rather than silently changing semantics.

The required read API/service contract is:

```text
PostCloseActualsRepository.get_actuals_for_signals(
    trading_day_plan_id,
    post_close_market_snapshot_id,
) -> PostCloseActualsReadResult
```

The read result must return:

- the approved `TradingDayPlan` identity and trade date;
- the post-close `MarketSnapshot.id`, `snapshot_id`, `content_fingerprint`, `frozen_at`, and `available_at`;
- the source `DatasetSnapshot.dataset_snapshot_id` and `content_fingerprint`;
- one actual row or one explicit non-success state for every pre-market `Signal`;
- per-row `row_fingerprint`;
- global coverage state: `ready`, `partial`, `unavailable`, `conflict`, `invalid`, `insufficient_coverage`, or `degraded`.

The repository/service must not:

- call live Providers;
- query mutable latest OHLCV rows without checking a frozen `DatasetSnapshot` and post-close `MarketSnapshot` binding;
- read legacy Job / Workflow / Pipeline / Artifact / file JSON / legacy post-market reports;
- infer missing rows as zero, false, success or condition satisfied.

Safe rerun:

- Rebuilding the same post-close actual snapshot with identical rows and bindings must be idempotent by content fingerprint.
- If source OHLCV content changes, the builder must create or bind a new immutable snapshot/fingerprint and must not mutate prior review evidence silently.
- Re-running signal outcome evaluation for the same `TradingDayPlan` and same post-close actual snapshot must reuse or replace the same `PostMarketReview` revision deterministically; using a different actual snapshot requires a new revision or explicit supersession evidence.

Bounded migration implication:

- A migration is required only if existing `MarketSnapshotSection` / `MarketSnapshotItem` JSON payloads and indexes cannot safely enforce or query this section contract. If JSON payload is used, tests must prove schema validation, uniqueness, row fingerprint binding and missing/conflict semantics.
- A new actuals table/repository remains allowed only if Option A proves unsafe during implementation review. That change would require another escalation before production implementation proceeds.

### Approved Imported Actuals Supplement Contract

Approved imported actuals are optional supplement and may only supply execution-specific evidence:

- whether the signal was executed;
- execution price;
- execution time;
- filled quantity;
- fees if available;
- user/import approval state;
- source broker/import identity and raw import fingerprint.

They must not be the only source for unexecuted signal close/MFE/MAE/return unless expanded to the same per-symbol immutable OHLCV actuals coverage as the formal post-close actual snapshot contract.

If implemented in `RT-S10-001`, the supplement must define:

- writer ownership: Stage 10 post-market actual import/review service, not raw `TradeLog` import alone;
- import source and immutable import fingerprint;
- approval/review state before use in outcome evaluation;
- `trade_date`, `symbol`, optional `signal_id`, optional `trading_day_plan_id`;
- safe dedup key over source/import/execution identity;
- conflict and unavailable states that block execution-specific success defaults;
- read API that joins supplement rows to signals without mutating signals or plans.

### PostMarketReview Contract

- `PostMarketReview` is daily runtime evidence, not formal strategy, rule, author profile, or applicability.
- It must be traceable to exactly one `TradingDayPlan` and its canonical signals.
- It may reference a post-market `MarketSnapshot` and closing/current `MarketRegimeRecord` / market state.
- It records signal outcomes, structured attribution, evidence, lifecycle state, quality state, and optional prompt run only when bounded LLM validation/explanation is used.
- It must not become a second formal strategy/proposal source.

### Signal Outcome Contract

Signal result evaluation is program-fact-first.

For each pre-market `Signal`, Stage 10 must record:

- whether it triggered
- whether it was executed
- actual result
- MFE
- MAE
- return
- matched rule
- market state change

Exact metric source:

- `triggered`: from pre-market `Signal.signal_state`, side, rule decision payload and plan approval evidence. Missing or contradictory trigger evidence must become `invalid` or `conflict`, not `false`.
- `executed`: from approved imported actuals supplement when available. If no approved execution evidence exists, state is `unavailable` or `not_confirmed` for execution-specific fields; it must not block market actual metrics for unexecuted signals.
- `actual result`: from the formal post-close actual row and signal side/entry policy. Missing entry baseline or actual row becomes `unavailable` / `insufficient_coverage`.
- `MFE` / `MAE`: from formal post-close actual high/low evidence. For Stage 10 daily-bar approximation, use daily high/low with `evidence_window = "daily_bar"` recorded in evidence; do not imply intraday path precision.
- `return`: from formal post-close actual close and explicit baseline. Baseline is the signal entry price when present and valid; otherwise previous close may be used only if the signal contract says return is benchmarked to previous close. Missing baseline becomes `invalid` or `unavailable`.
- `matched rule`: from canonical `Signal.rule_version_ids`, `triggered_rules`, and `DailyRuleSelectionItem`, never from free-text attribution.
- `market-state change`: compare pre-market `DailyRuleSelection.market_state_id` / `DailyStrategyInstance.market_snapshot_id` with post-close `PostMarketReview.market_state_id` / post-close `MarketRegimeRecord`. Missing post-close market state becomes `unavailable`, not unchanged.

Allowed outcome states include `unavailable`, `partial`, `conflict`, `invalid`, `insufficient_coverage`, and `degraded`. Missing actual/outcome data must never become false, zero, empty success, or condition satisfied.

Write destination:

- Outcome facts should be stored in `PostMarketReview.signal_results_json` unless implementation proves this unsafe.
- `PostMarketReview.evidence_json` must bind the approved plan, pre-market signals, post-close actual snapshot, dataset snapshot, row fingerprints, metric formula/policy version and unavailable/conflict reasons.
- `Signal.evaluation_result_id` remains compatibility placeholder and must not become the formal outcome source.
- `PostMarketReview.attribution_json` remains empty or unavailable in `RT-S10-001` unless `RT-S10-002` is explicitly authorized later.

### Structured Attribution Contract

Structured attribution is deterministic/program-fact-first.

Allowed attribution classes:

- data issue
- market-state identification issue
- rule issue
- strategy-composition issue
- execution issue
- unattributable

LLM may only validate and explain. LLM must not create or replace program facts. Low-confidence, evidence-conflict, or important signals may use `llm_attribution_v1`. Only after final structured attribution is complete, `llm_postmortem_notes_v1` may be used when needed for user-readable explanation.

### Proposal Contract

Stage 10 proposal types must remain separate:

- `RuleOptimizationProposal`
- `AuthorProfileRevisionProposal`
- `StrategyRevisionProposal`

They may use canonical `OptimizationProposal` only if type-specific evidence, target, lifecycle, acceptance behavior, and UI/API labels remain separate. They must not be merged into one generic “AI suggestion”.

Single-day results must not directly modify:

- `RuleVersion`
- `RuleApplicabilityProfile`
- `AuthorProfileVersion`
- `StrategyVersion`
- `Strategy.current_published_version_id`
- `DailyRuleSelection`
- `DailyStrategyInstance`
- `TradingDayPlan` source traceability
- current proposal status except through explicit proposal review actions

Proposal acceptance may create drafts or review records only where existing formal contracts allow; it cannot publish or mutate formal current objects.

### Formal Input Contract

Formal Stage 10 flow may consume only canonical:

- `DailyRuleSelection`
- `DailyRuleSelectionItem`
- `DailyStrategyInstance`
- `TradingDayPlan`
- `Signal`
- `DatasetSnapshot`
- `MarketSnapshot`
- `MarketRegimeRecord` / current market state
- `BacktestRun` / `BacktestResult` only if needed as historical evidence
- `RuleApplicabilityProfile`
- `AuthorProfileVersion`
- `Strategy`
- `StrategyVersion`
- `StrategyRuleMembership`
- `OptimizationProposal` where used as proposal carrier

Formal Stage 10 flow must not consume as formal input:

- legacy Job / Workflow / Pipeline / Artifact records
- file JSON reports
- `config_path`
- live Provider calls
- mutable latest records without immutable snapshot IDs
- legacy strategy service or strategy library
- legacy backtest service
- compatibility views
- legacy post-market reports
- `/daily/overview` compatibility job cards

## Task Order

1. `RT-S10-001 信号结果评估`
2. `RT-S10-002 结构化归因`
3. `RT-S10-003 优化建议`
4. `RT-S10-004 盘后用户页面`

Combination rule:

- `RT-S10-001` + `RT-S10-002` may be implemented in the same Task Session only if frozen contracts remain stable and work is done serially.
- `RT-S10-003` + `RT-S10-004` may be implemented in the same Task Session only if proposal contracts remain stable and work is done serially.
- Do not combine `RT-S10-001` with `RT-S10-003`.
- Do not combine Stage 10 with Stage 11.

## Task Card: RT-S10-001 信号结果评估

- Risk：`M3` source-of-truth, snapshot-bound actuals, missing-data semantics.
- Target：evaluate every pre-market `Signal` from an approved `TradingDayPlan` and persist program facts as daily runtime evidence.
- Current facts：canonical `Signal` rows are created by Stage 9; `PostMarketReview` exists; no dedicated formal outcome API/service/page exists; `Signal.evaluation_result_id` is only a placeholder and not a formal outcome source; no existing read API exposes immutable per-signal post-close OHLCV actuals with dataset snapshot binding and row fingerprints.
- Frozen contracts：`Decision 1` applies. A formal canonical post-close actual snapshot source is required and sufficient for actual result/MFE/MAE/return; approved imported actuals are optional execution supplement only. Program facts calculate trigger, execution, actual result, MFE, MAE, return, matched rule, and market-state change; no live Provider calls; missing data remains unavailable/partial/conflict/invalid/insufficient_coverage/degraded.
- Allowed paths：new bounded Stage 10 post-close actuals repository/service/API/tests; new `post_close_symbol_ohlcv_actuals` MarketSnapshot section/item builder/read contract; new Stage 10 post-market repository/service/API/client/page tests; `PostMarketReview.signal_results_json`; optional migration only if current schema cannot safely store/query required evidence; focused daily route wiring only if not replacing RT-S10-004 scope.
- Forbidden paths：legacy Job/Workflow/Pipeline/Artifact/file JSON, legacy post-market reports, `config_path`, live Providers, legacy backtest/strategy services, direct mutation of formal rules/profiles/strategies, Stage 11 automation.
- Expected user-visible result：盘后页 can show each signal’s 盘前预测、实际结果、差异 and truthful unavailable/partial states.
- Backend/API/frontend/database/doc scope：first create/read formal post-close actual snapshot rows for all signaled symbols; read canonical plan/signals, post-market snapshot/market state and optional approved imported execution actuals; persist/reuse one `PostMarketReview` revision for the plan; expose result status without attribution/proposals in this task unless separately authorized later.
- Focused tests：post-close actual snapshot builder/read contract; dataset snapshot/market snapshot/fingerprint binding; one actual row or explicit non-success state per signal; service outcome matrix; missing actual data; MFE/MAE/return from formal post-close actual snapshot; optional imported execution supplement; no live Provider; API contract; frontend unavailable/partial display if UI touched; legacy isolation grep; `git diff --check`.
- Special verification：actual result/MFE/MAE/return must be computed from the formal `post_close_symbol_ohlcv_actuals` snapshot contract; approved imported actuals may only supplement execution fields unless they satisfy full OHLCV coverage; missing values must not be defaulted to 0/false/success.
- Escalation triggers：outcomes require live Provider calls; formal post-close actual snapshot cannot be built/read safely from canonical storage; current MarketSnapshot section/item contract proves too weak and requires a new actuals table; a second formal outcome source appears; schema/source-of-truth change beyond the frozen Decision 1 contract is needed.
- Acceptance criteria：every pre-market signal has a clear result state and traceable program-fact evidence from a formal post-close actual snapshot, or an explicit unavailable/partial/conflict/invalid/insufficient_coverage/degraded reason; `PostMarketReview.signal_results_json` and `evidence_json` bind plan, signal, market snapshot, dataset snapshot, fingerprints and metric policy; no attribution/proposals are generated.

RT-S10-001 route boundary:

- `/daily/after-close` may remain compatibility-only during `RT-S10-001` if the formal service/API exposes truthful outcome status and tests prove no legacy input is used.
- Full replacement of `/daily/after-close` remains `RT-S10-004` unless the user explicitly authorizes combining UI replacement after `RT-S10-001` acceptance.

## Task Card: RT-S10-002 结构化归因

- Risk：`M3` deterministic attribution, LLM boundary, evidence conflict.
- Target：classify each evaluated signal using deterministic attribution categories and bounded LLM validation/explanation only where allowed.
- Current facts：legacy postmortem service has auto-attribution and inactive future LLM paths; registered prompts include `llm_attribution_v1` and `llm_postmortem_notes_v1`.
- Frozen contracts：program facts are final; LLM cannot recompute metrics or replace facts; categories are fixed; prompt outputs must be versioned and schema-validated if used.
- Allowed paths：Stage 10 attribution service/API/schema/tests, prompt runtime integration only for conditional validation/explanation, `PostMarketReview.attribution_json` and `prompt_run_id` where applicable.
- Forbidden paths：LLM-created metrics/facts, single free-text attribution as formal source, direct formal object mutation, proposal generation unless in a later RT-S10-003 task.
- Expected user-visible result：盤后 page can explain 成功原因/失败原因 with deterministic attribution labels and confidence/limitations.
- Backend/API/frontend/database/doc scope：add structured attribution payload under `PostMarketReview`; keep prompt run evidence only for low-confidence/conflict/important cases; expose user-readable explanation after structured attribution exists.
- Focused tests：classification for six categories; low-confidence/conflict LLM gate; prompt schema validation; prompt disabled/fallback behavior; no LLM fact replacement; API/frontend display tests.
- Special verification：LLM call records must include prompt/schema/model/token/cost/input_hash/run_id; raw LLM output is never the final formal fact source.
- Escalation triggers：attribution needs LLM to create facts; fixed categories cannot represent required outcome; prompt/schema/runtime contracts diverge; evidence conflict cannot be represented as conflict/unattributable.
- Acceptance criteria：every evaluated signal has one structured attribution class or explicit unattributable/conflict state, and user explanation is derived from final structured facts.

## Task Card: RT-S10-003 优化建议

- Risk：`M3` proposal governance, formal object mutation boundary.
- Target：generate separate rule, author-profile, and strategy revision suggestions from completed post-market evidence without publishing or overwriting formal objects.
- Current facts：`OptimizationProposal` enum already supports `rule_optimization`, `author_profile_revision`, `strategy_revision`; existing canonical service/UI only handles `strategy_revision`.
- Frozen contracts：proposal types remain separate; single-day results never directly modify `RuleVersion`, `RuleApplicabilityProfile`, `AuthorProfileVersion`, `StrategyVersion`, or current strategy pointer.
- Allowed paths：type-specific proposal service/API/UI/tests; reuse `OptimizationProposal` only with separated proposal type, target asset, evidence, lifecycle, and acceptance behavior; docs/log updates.
- Forbidden paths：generic “AI suggestion”; auto-publish; direct rule/profile/strategy mutation; proposal status mutation outside explicit review actions; Stage 11 alerts/automation.
- Expected user-visible result：user can see separate rule, author profile, and strategy suggestions, then accept, reject, or continue observing where allowed by formal proposal contracts.
- Backend/API/frontend/database/doc scope：define proposal target semantics for rule/profile/strategy; add review actions that create drafts/review records only where existing formal governance allows; do not generate actual proposal content during Bootstrap.
- Focused tests：three proposal types stay separate; acceptance cannot publish/current-use formal object; reject/observe actions audited; API/OpenAPI; frontend action states; legacy isolation grep.
- Special verification：acceptance of strategy proposal remains draft-only; rule/profile acceptance enters their review/draft lifecycle rather than mutating published versions.
- Escalation triggers：proposal types cannot remain separated; acceptance would publish or current-use formal object; existing rule/profile governance lacks a safe draft/review path; schema changes exceed frozen contract.
- Acceptance criteria：separate proposal records exist with traceable evidence, review state, and safe actions; no single-day evidence overwrites formal objects.

## Task Card: RT-S10-004 盘后用户页面

- Risk：`M2` cross-layer UI/API integration, legacy isolation.
- Target：replace `/daily/after-close` compatibility wrapper with the formal post-market review surface.
- Current facts：`/daily/after-close` is canonical route but currently wraps legacy job/report UI; old after-close routes are compatibility-only.
- Frozen contracts：formal page consumes only Stage 10 canonical API; it must not use job cards, legacy reports, artifacts, or file JSON as formal input/output.
- Allowed paths：`web/src/pages/daily/*`, `web/src/lib/api/daily*`, `web/src/types/daily*`, formal post-market router/client tests, route tests; optional focused components under existing daily patterns.
- Forbidden paths：exposing Job/Workflow/Pipeline/Artifact/Provider/Schema/CLI/internal paths; using `/daily/overview` job cards as formal results; starting Stage 11 automation; legacy report viewer as formal page.
- Expected user-visible result：page displays 盘前预测、实际结果、差异、成功原因、失败原因、建议操作 and truthful loading/empty/error/partial/permission_denied/unavailable states.
- Backend/API/frontend/database/doc scope：API must supply page-ready business Chinese fields or stable DTOs; frontend maps technical fields to business terms; proposal actions appear only after RT-S10-003 contracts are implemented.
- Focused tests：route/page rendering; all required fixed sections; no internal developer terminology; action states accept/reject/continue observing; permission/error/partial/unavailable; typecheck.
- Special verification：Stage 10 should run focused UI tests; Stage Gate should decide whether browser-level E2E is needed because Stage 9 did not run browser E2E.
- Escalation triggers：formal page needs legacy jobs/reports to show results; UI requires a second post-market fact source; proposal actions cannot be represented safely; Stage 11 automation/alerts become required.
- Acceptance criteria：ordinary user can understand prediction, actual outcome, difference, reasons, and suggested next action without internal developer terminology.

## Gates And Validation Plan

Task-level validation:

- focused backend unit/service tests
- API/router/OpenAPI tests
- migration tests if schema changes
- prompt regression/schema tests when LLM lane is touched
- frontend client/page/route tests
- legacy isolation grep for formal Stage 10 paths
- mutation-boundary tests for formal rule/profile/strategy objects
- `git diff --check`

Stage 10 Gate validation:

- every signal has clear result and attribution, or explicit unavailable/partial/conflict state
- single-day results do not overwrite formal rules, author profiles, strategies, or current pointers
- rule, author profile, and strategy proposals remain separate
- user can accept, reject, or continue observing suggestions where proposal contracts allow
- `/daily/after-close` is formal Stage 10 UI and does not expose internal developer terminology
- legacy after-close jobs/reports/artifacts remain compatibility-only and are not formal inputs/outputs
- focused UI tests pass; browser E2E evidence is either run or explicitly recorded as not required with residual risk

## Risks And Blockers

Blocking at Bootstrap：none.

Non-blocking risks for implementation:

- No dedicated formal `PostMarketReview` service/API/page exists yet.
- `Signal` has no first-class outcome table; current plan allows `PostMarketReview.signal_results_json`, but implementation must escalate if this cannot safely support traceability and tests.
- `/daily/after-close` is currently a legacy job/report wrapper and must be isolated or replaced.
- Existing `OptimizationProposal` service/UI handles only `strategy_revision`; rule and author profile proposal lanes need safe governance integration.
- Existing postmortem service has useful calculations but is not automatically a formal Stage 10 fact source; reuse must be bounded and canonical-input only.
- Browser-level E2E was not run in Stage 9; Stage 10 UI work should add focused page tests and revisit E2E at Gate.
