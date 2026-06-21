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

Allowed outcome states include `unavailable`, `partial`, `conflict`, `invalid`, `insufficient_coverage`, and `degraded`. Missing actual/outcome data must never become false, zero, empty success, or condition satisfied.

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
- Current facts：canonical `Signal` rows are created by Stage 9; `PostMarketReview` exists; no dedicated formal outcome API/service/page exists; `Signal.evaluation_result_id` is only a placeholder and not a formal outcome source.
- Frozen contracts：program facts calculate trigger, execution, actual result, MFE, MAE, return, matched rule, and market-state change; no live Provider calls; missing data remains unavailable/partial/conflict/invalid/insufficient_coverage/degraded.
- Allowed paths：new Stage 10 post-market repository/service/API/client/page tests; `PostMarketReview.signal_results_json`; optional migration only if current schema cannot safely store required evidence; focused daily route wiring.
- Forbidden paths：legacy Job/Workflow/Pipeline/Artifact/file JSON, legacy post-market reports, `config_path`, live Providers, legacy backtest/strategy services, direct mutation of formal rules/profiles/strategies, Stage 11 automation.
- Expected user-visible result：盘后页 can show each signal’s 盘前预测、实际结果、差异 and truthful unavailable/partial states.
- Backend/API/frontend/database/doc scope：read canonical plan/signals, post-market snapshot/market state and approved actuals; persist/reuse one `PostMarketReview` revision for the plan; expose result status without attribution/proposals in this task unless combined later with RT-S10-002.
- Focused tests：service outcome matrix; missing actual data; MFE/MAE/return from canonical snapshots/imported actuals; no live Provider; API contract; frontend unavailable/partial display; legacy isolation grep; `git diff --check`.
- Special verification：actual result/MFE/MAE/return must be computed from canonical snapshots or approved imported actuals; missing values must not be defaulted to 0/false/success.
- Escalation triggers：outcomes require live Provider calls; canonical snapshots cannot compute required metrics; a second formal outcome source appears; schema/source-of-truth change beyond frozen contracts is needed.
- Acceptance criteria：every pre-market signal has a clear result state and traceable program-fact evidence, or an explicit unavailable/partial/conflict reason.

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
