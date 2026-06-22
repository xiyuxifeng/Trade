# Stage 10 每日盘后实施日志

## Stage Summary

- Stage：`Stage 10 每日盘后`
- 当前活动：`RT-S10-004 已接受，等待 Stage 10 Gate / review`
- 当前状态：`Stage 10 进行中`
- 当前 Task：`RT-S10-001 / RT-S10-002 / RT-S10-003 / RT-S10-004 已接受`
- 下一可执行项：`Stage 10 Gate 或后续 review（需用户明确授权）`
- 不得自动开始：不得自动启动 `Stage 10 Gate` 或 `Stage 11`

## 2026-06-21 Stage 10 Bootstrap

### Scope

本次只审计当前实现、冻结 Stage 10 每日盘后契约、创建 Stage 10 实施计划/Task Cards 并更新主实施日志。

明确未执行：

- production code implementation
- signal result evaluation
- attribution generation
- `RuleOptimizationProposal` / `AuthorProfileRevisionProposal` / `StrategyRevisionProposal` generation
- Stage 11 automation or alerting

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定委派 2 个 read-only `refactor_explorer_mini`：

- Explorer Alpha：Stage 9 canonical runtime outputs、traceability、legacy input isolation、current tests。
- Explorer Gamma：Stage 10 post-market/proposal/UI/API/database surfaces、strategy/proposal boundary、legacy after-close paths。

未使用 Executor。Bootstrap 禁止生产代码实现。Parent 保留契约冻结、Task Card、风险分类和正式文档更新。

### Entry Verification

- Stage 9 Gate：`ACCEPTED`。
- `RT-S9-001 自动前置检查`：`ACCEPTED`。
- `RT-S9-002 每日规则选择`：`ACCEPTED`。
- `RT-S9-003 每日策略实例和盘前计划`：`ACCEPTED`。
- Stage 10 Bootstrap 前未开始：Stage 9 Gate 确认未新增 Stage 10 table/service/API/UI，未生成 signal result evaluation、post-market attribution 或 proposal。
- Branch：`main`。
- HEAD：`c2df735c025ea952e065fabeb2a5e693f83cbc7d`。
- Bootstrap 前 working tree：clean。
- Bootstrap 前完整 diff：empty。

### Verified Facts

- Formal Stage 9 outputs exist and are canonical：`DailyRuleSelection`、`DailyRuleSelectionItem`、`DailyStrategyInstance`、`TradingDayPlan`、`Signal`。
- Stage 9 outputs trace to canonical IDs and quality/lifecycle states through columns plus bounded JSON payload.
- Stage 9 residual risks are carried forward as non-blocking unless they directly block Stage 10 post-market correctness.
- Formal strategy source-of-truth remains `Strategy` + `StrategyVersion` + `StrategyRuleMembership` with `Strategy.current_published_version_id`.
- Existing `OptimizationProposal` enum supports `rule_optimization`、`author_profile_revision`、`strategy_revision`。
- Existing canonical strategy proposal flow currently handles only `strategy_revision` and acceptance is draft-only.
- `PostMarketReview` table exists, but no dedicated formal post-market review service/API/page was found.
- `/daily/after-close` exists as canonical route but currently wraps legacy job/report based after-close UI.
- `/workflows/after-close`、`/workflows/after-close/run`、`/strategies/after-close` are compatibility-only.
- Legacy Job / Workflow / Pipeline / Artifact / file JSON / `config_path` / live Provider / mutable latest records are not formal Stage 10 inputs.

### Frozen Contracts

- `PostMarketReview` is daily runtime evidence, not formal strategy.
- Signal result evaluation is program-fact-first and must compute trigger, execution, actual result, MFE, MAE, return, matched rule, and market-state change from canonical snapshots or approved imported actuals.
- Structured attribution is deterministic/program-fact-first; LLM may only validate/explain and cannot replace program facts.
- `llm_attribution_v1` is allowed only for low-confidence, evidence-conflict, or important signals.
- `llm_postmortem_notes_v1` is allowed only after final structured attribution exists and only for user-readable explanation.
- `RuleOptimizationProposal`、`AuthorProfileRevisionProposal`、`StrategyRevisionProposal` must remain separate proposal types.
- Single-day results must not directly modify `RuleVersion`、`RuleApplicabilityProfile`、`AuthorProfileVersion`、`StrategyVersion`、`Strategy.current_published_version_id`、`DailyRuleSelection`、`DailyStrategyInstance` or `TradingDayPlan` source traceability.
- Stage 10 must not call live Providers during attribution or proposal generation.
- Missing actual/outcome data remains unavailable, partial, conflict, invalid, insufficient_coverage, or degraded.

### Task Order

1. `RT-S10-001 信号结果评估`
2. `RT-S10-002 结构化归因`
3. `RT-S10-003 优化建议`
4. `RT-S10-004 盘后用户页面`

Combination rule：

- `RT-S10-001` + `RT-S10-002` may be implemented in one Task Session only if frozen contracts remain stable and work is done serially.
- `RT-S10-003` + `RT-S10-004` may be implemented in one Task Session only if proposal contracts remain stable and work is done serially.
- Do not combine `RT-S10-001` with `RT-S10-003`.
- Do not combine Stage 10 with Stage 11.

### Task Card Summary

- `RT-S10-001`：evaluate every pre-market `Signal`; persist program-fact outcome evidence in `PostMarketReview`; no live Providers or legacy report/job inputs.
- `RT-S10-002`：classify deterministic attribution into data issue, market-state identification issue, rule issue, strategy-composition issue, execution issue, or unattributable; LLM only validates/explains when gated.
- `RT-S10-003`：generate separated rule/profile/strategy proposal records and safe review actions; no direct mutation or publication of formal objects.
- `RT-S10-004`：replace `/daily/after-close` compatibility wrapper with formal post-market UI showing 盘前预测、实际结果、差异、成功原因、失败原因、建议操作.

Full Task Cards are in `docs/refactor-implementation-plans/stage-10-implementation-plan.md`.

### Verification

Bootstrap verification performed:

- Required docs read.
- Current branch/status/diff checked.
- Stage 9 Gate and RT-S9-001/002/003 acceptance verified from Stage 9 log and main log.
- Stage 10-related models/services/API/frontend/tests mapped.
- Two read-only explorer handoffs reviewed.

No production tests were run because no production code was changed.

### Residual Risks

- `PostMarketReview` lacks a formal service/API/page.
- `Signal` lacks first-class outcome persistence beyond generic fields; current frozen plan allows `PostMarketReview.signal_results_json`, but implementation must escalate if this cannot safely support traceability and tests.
- `/daily/after-close` still uses legacy job/report UI.
- Existing proposal service/UI only supports `strategy_revision`; rule and author profile proposal lanes need safe governance integration.
- Stage 9 browser-level E2E was not run; Stage 10 should add focused UI tests and revisit browser E2E at Gate.

### Conclusion

`Stage 10 Bootstrap READY`。

下一可执行 Task：`RT-S10-001 信号结果评估`。推荐使用 `gpt-5.4` Task Implementation session；如触发 schema/source-of-truth、live Provider avoidance、LLM fact boundary、proposal governance、formal object mutation 或 Stage 11 automation escalation，则切回 `gpt-5.5` Contract Escalation Review。

## 2026-06-21 RT-S10-001 信号结果评估

### Status

`[!] 阻塞`

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定委派 2 个 read-only `refactor_explorer_mini` 做有界调查：

- Explorer Beta：RT-S10-001 canonical backend / snapshot / PostMarketReview feasibility。
- Explorer Alpha：`/daily/after-close` formal/compat UI/API surface 与现有测试。

Parent 负责最终 source-of-truth 判断、阻塞确认和正式日志更新。当前 Session 无 subagent 写入。

### Scope

本次只执行 RT-S10-001 可行性核验与 frozen-contract implementation planning，未开始 RT-S10-002/003/004，未修改 production code、schema 或 formal API/UI。

### Verified Facts

- `PostMarketReview` 已是 canonical table，具备 `trading_day_plan_id`、`revision_no`、`market_snapshot_id`、`market_state_id`、`signal_results_json`、`evidence_json`、`quality_status` 和 `lifecycle_state` 字段，可承载单日运行证据；当前未发现 dedicated Stage 10 review service/API/page。
- `Signal` 已具备 canonical `strategy_version_id`、`trading_day_plan_id`、`daily_strategy_instance_id`、`rule_version_ids`、`signal_state`、`decision_mode`、`degraded` / `degradation_reason` 等字段，但 `evaluation_result_id` 仍是 legacy placeholder，不是 formal outcome source。
- Stage 9 canonical source 已完整存在：`DailyRuleSelection`、`DailyRuleSelectionItem`、`DailyStrategyInstance`、`TradingDayPlan`、`Signal` 的 repository/service/API/test 路径清晰，可稳定读取 approved `TradingDayPlan` 与其 `Signal`。
- `/daily/after-close` 仍直接返回 `StrategyAfterCloseWorkspacePage`，当前 formal daily surface 仍包裹 legacy job/report workspace；前端 `daily.ts` 也尚无 formal after-close API client。
- `MarketSnapshot` / `MarketSnapshotSection` / `MarketSnapshotItem` 当前 canonical contract 可存放 snapshot/section/item facts，但现有 builder 只确认：
  - `ohlcv` section 绑定 benchmark symbol 窗口；
  - `strong_symbols` section 提供候选标的；
  - 其余 sections 为市场广度/题材/情绪等市场级 facts。
- 当前 Stage 5/9 canonical flow 中，未发现现成的 per-signal post-close actual section，亦未发现 formal Stage 10 service 能从 canonical close snapshot 直接读取单个 signal symbol 的 `open/high/low/close` 路径。
- `DatasetSnapshot` 当前只冻结 dataset-level manifest/fingerprint/row_fingerprint/availability metadata；其 canonical record 不保存可直接用于 RT-S10-001 的 per-signal OHLCV bar values。
- `TradeLog` 存在导入能力，但当前导入路径只写 `trade_logs`，未发现 formal 审核/批准/冻结 contract，使其满足“approved imported actuals with immutable traceability”要求。

### Blocker

命中 frozen escalation trigger：

```text
canonical snapshots or approved imported actuals cannot compute required metrics
```

当前已验证 canonical inputs 可以确定：

- approved `TradingDayPlan`
- plan 下全部 `Signal`
- plan 对应的 pre-market `MarketSnapshot` / `MarketRegimeRecord`

但当前未验证到任一已存在 formal source 能为每个 signal 提供：

- actual result
- MFE
- MAE
- return

所需的 post-close immutable price-path evidence。

现有已知数据源缺口：

1. `MarketSnapshot` 当前只有 benchmark `ohlcv` section，不是 signal-symbol close snapshot。
2. `strong_symbols` / topic / sentiment sections 不提供 per-signal `high/low/close` path。
3. `DatasetSnapshot` 只有 manifest/fingerprint，不带可直接消费的 OHLCV values。
4. `TradeLog` 未形成本 Task 可用的 approved/canonical actuals contract，且不能覆盖未执行 signal 的 close/MFE/MAE 计算。

若继续实现 RT-S10-001，必须至少新增其一：

- 新的 formal canonical post-close actual snapshot source；或
- 已批准、可冻结、可追溯的 imported actuals contract。

这已超出当前 frozen Task Card 的现有 source-of-truth 前提，Parent 不能在本 Session 自行假定或扩展。

### Commands And Evidence

- `git status --short`：clean。
- `git diff`：empty（开始实现前）。
- `bash .codex/skills/refactor-orchestrator/scripts/runtime-probe.sh`：custom subagent config files 存在；native spawning / exact model / effective read-only 仍无法独立证明。
- Repository evidence reviewed:
  - `src/models/stage2_canonical.py`
  - `src/models/signal.py`
  - `src/models/market_data_snapshot.py`
  - `src/models/market_data_snapshot_section.py`
  - `src/models/market_data_snapshot_item.py`
  - `src/models/market_regime_record.py`
  - `src/models/trade_log.py`
  - `src/services/daily_trading_plan_service.py`
  - `src/services/dataset_snapshot_service.py`
  - `src/services/market_snapshot_builders.py`
  - `src/services/market_data_storage_service.py`
  - `api/routers/ui/daily_pre_market.py`
  - `web/src/pages/daily/index.tsx`
  - related tests and OpenAPI contract files

### Tests

未运行 production verification tests。

原因：

- 在 frozen contract 下先命中 source-of-truth blocker；
- 若没有 formal actuals source，继续补测试只会围绕假设数据源写出错误 contract。

替代检查：

- 完成 relevant model/repository/router/page/test audit；
- 复核 current git status / diff；
- 核验 legacy isolation 与 current formal route wiring。

### Acceptance Conclusion

`RT-S10-001` 当前不能接受，且不应进入代码实现。

需要 `ESCALATION_REQUIRED` 决策：

- 是否为 Stage 10 增补 formal canonical post-close actual snapshot contract；
- 或是否引入 approved imported actuals formal contract；
- 并明确其 immutable traceability、writer ownership、review/approval 和 safe-rerun boundary。

## 2026-06-21 RT-S10-001 Contract Escalation Review

### Status

`[-] 进行中`

`RT-S10-001` 的 source-of-truth 阻塞已解除为可执行契约，但 production implementation 尚未恢复、尚未接受。

### Scope

本次仅执行 gpt-5.5 contract escalation review，并更新 Stage 10 计划和日志。

明确未执行：

- production `RT-S10-001` outcome implementation
- signal outcome generation
- attribution generation
- `RuleOptimizationProposal` / `AuthorProfileRevisionProposal` / `StrategyRevisionProposal` generation
- `/daily/after-close` formal replacement
- Stage 11 automation

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定委派 2 个 read-only `refactor_explorer_mini`：

- Explorer Alpha：审计 canonical `DatasetSnapshot` / `MarketSnapshot` / OHLCV / snapshot read APIs 是否已能提供 immutable per-symbol post-close actuals。
- Explorer Gamma：审计 Stage 10 bootstrap/status、`Signal` / `TradeLog` / `PostMarketReview` / `/daily/after-close` 现状和测试缺口。

未使用 Executor。生产实现被禁止，Parent 保留 source-of-truth 决策、契约冻结、正式文档更新和最终判断。

### Entry Verification

- Stage 10 Bootstrap：`READY`。
- `RT-S10-001`：进入本次 review 前为 `[!] 阻塞`，未接受。
- 当前分支：`main`。
- 当前 HEAD：`b375ca37c52283d72ac898b2d08630778525d8be`。
- review 前 `git status --short`：clean。
- review 前 `git diff --stat` / `git diff`：empty。
- `bash .codex/skills/refactor-orchestrator/scripts/runtime-probe.sh`：`.codex/agents/refactor-explorer-mini.toml` 和 `.codex/agents/refactor-executor-mini.toml` 存在；native spawn、exact child model 和 effective read-only 权限仍属于运行时不可独立证明项。

### Verified Blockers

已复核并确认当前阻塞事实：

1. `PostMarketReview` 可存储 `signal_results_json` / `evidence_json`，但没有 formal write service/API/page。
2. `/daily/after-close` 当前仍在正常路径下返回 legacy `StrategyAfterCloseWorkspacePage`，依赖 `run-after-close` job/report workspace。
3. `MarketSnapshot` 当前 canonical builders 只确认 benchmark OHLCV 与市场级 sections；没有 formal per-signal-symbol post-close OHLCV actual section。
4. `DatasetSnapshot` 冻结 manifest/fingerprint/row_fingerprint/availability metadata，但没有 formal read API 暴露每个 signal 需要的 immutable OHLCV value rows。
5. `TradeLog` 是 raw executed-trade ingestion，缺少 approved/import review/fingerprint/signal binding contract，且无法覆盖未执行 signal 的 close/MFE/MAE/return。
6. 旧 postmortem/backtest/ranking 代码可计算 MFE/MAE/return，但不是 formal Stage 10 source-of-truth，也未接入 `PostMarketReview` writer。

### Selected Contract Decision

选择并冻结：

```text
Decision 1:
Formal canonical post-close actual snapshot source is required and sufficient
for signal outcome metrics. Approved imported actuals are optional supplement
for execution-specific fields.
```

表示 `RT-S10-001` 恢复时必须先建立 formal canonical post-close actual snapshot source，然后才能计算 signal outcome。不得用 legacy reports、live Provider、mutable latest OHLCV、`trade_logs` 或文件 JSON 代替。

### Rejected Alternatives

- `Decision 2` rejected：approved imported actuals 只有在覆盖所有 signaled symbols 且包含 immutable OHLCV actual values 时才可能 sufficient。当前 `trade_logs` 不具备 approval/fingerprint/signal binding，也不能覆盖 unexecuted signals。
- `Decision 3` rejected：不需要等待 Stage 11。可以在 Stage 10 内通过 bounded canonical post-close actual snapshot contract 解除 source-of-truth 阻塞。
- `Option C` rejected for now：单纯扩展 `DatasetSnapshot` read contract 不足以承载盘后 review 与 market snapshot / post-close market state 的业务绑定，除非另行升级为正式 actuals read API 并绑定 `PostMarketReview`。
- `Option B` deferred：new canonical actuals table/repository 只有在 Option A implementation review 证明 `MarketSnapshotSection` / `MarketSnapshotItem` 过弱时才允许再次升级。

### Frozen Source-Of-Truth Contract

优先采用：

```text
Option A:
new canonical MarketSnapshot section/item contract for post-close symbol OHLCV actuals
```

正式 section：

```text
post_close_symbol_ohlcv_actuals
```

必须满足：

- 对 approved `TradingDayPlan` 下每个 pre-market `Signal` 的 `symbol + trade_date` 提供一条 actual row，或一条明确 non-success state。
- 每条 actual row 包含 `symbol`、`trade_date`、`open`、`high`、`low`、`close`、optional `previous_close`、`volume`、`turnover`、instrument metadata、source/available/frozen timestamps、`dataset_snapshot_id`、`dataset_content_fingerprint`、`row_fingerprint`、`quality_state`、`availability_state` 和 `evidence_window`。
- section/manifest 绑定 contributing `DatasetSnapshot.dataset_snapshot_id`、`DatasetSnapshot.content_fingerprint`、row count、missing/conflict symbols、quality summary 和 actuals contract version。
- `MarketSnapshot.content_fingerprint`、section `raw_payload_fingerprint`、row `row_fingerprint` 必须可追溯。
- 若使用 daily-bar approximation，必须记录 `evidence_window = "daily_bar"` 与 `intraday_approximation = true`，不得暗示 intraday path precision。

正式 read API / service contract：

```text
PostCloseActualsRepository.get_actuals_for_signals(
    trading_day_plan_id,
    post_close_market_snapshot_id,
) -> PostCloseActualsReadResult
```

返回：

- approved `TradingDayPlan` identity and trade date；
- post-close `MarketSnapshot.id`、`snapshot_id`、`content_fingerprint`、`frozen_at`、`available_at`；
- source `DatasetSnapshot.dataset_snapshot_id` and `content_fingerprint`；
- one actual row or one explicit non-success state for every pre-market `Signal`；
- per-row `row_fingerprint`；
- coverage state: `ready` / `partial` / `unavailable` / `conflict` / `invalid` / `insufficient_coverage` / `degraded`。

### Outcome Calculation Contract

`RT-S10-001` 恢复时必须按以下口径：

- `triggered`：来自 canonical `Signal` state / side / rule decision / approved plan evidence；缺失或矛盾必须为 `invalid` 或 `conflict`，不得默认为 `false`。
- `executed`：来自 approved imported actuals supplement；没有 approved execution evidence 时只影响 execution-specific fields，不得阻断 unexecuted signal 的市场 actual metrics。
- `actual result`：来自 formal post-close actual row 和 signal side / entry policy。
- `MFE` / `MAE`：来自 formal post-close actual high/low；daily-bar approximation 必须在 evidence 中显式标注。
- `return`：来自 formal post-close actual close 和明确 baseline；entry baseline 缺失或不合法时为 `invalid` / `unavailable`。只有 signal contract 明确以 previous close 为基准时才能使用 previous close。
- `matched rule`：来自 `Signal.rule_version_ids` / `triggered_rules` / `DailyRuleSelectionItem`。
- `market-state change`：比较 pre-market `DailyRuleSelection.market_state_id` / `DailyStrategyInstance.market_snapshot_id` 与 post-close `PostMarketReview.market_state_id` / `MarketRegimeRecord`；缺失 post-close market state 为 `unavailable`，不得默认为 unchanged。

Write destination:

- 优先写入 `PostMarketReview.signal_results_json`。
- `PostMarketReview.evidence_json` 必须绑定 plan、signals、post-close market snapshot、dataset snapshot、row fingerprints、metric formula/policy version 和 unavailable/conflict reasons。
- `Signal.evaluation_result_id` 继续是 compatibility placeholder，不得成为 formal outcome source。
- `PostMarketReview.attribution_json` 在 `RT-S10-001` 中保持 empty/unavailable，除非之后明确授权 `RT-S10-002`。

### Approved Imported Actuals Supplement

Approved imported actuals 仅作为 execution supplement：

- executed or not confirmed；
- execution price；
- execution time；
- filled quantity；
- fee；
- import source；
- immutable import fingerprint；
- approval/review state；
- optional Signal / TradingDayPlan link。

它不得成为 unexecuted signal close/MFE/MAE/return 的唯一来源，除非另行扩展为覆盖所有 signaled symbols 的 immutable OHLCV actuals contract。

### Required Schema/API/Service Implications

- 需要新增 bounded Stage 10 post-close actuals builder/read contract，优先落在 `MarketSnapshot` section/item 层。
- 需要新增 formal actuals repository/service API，至少提供 `get_actuals_for_signals(...)`。
- 需要新增 schema validation/tests，确保 `post_close_symbol_ohlcv_actuals` payload rows 不被 free-form JSON 漂移破坏。
- 若现有 `MarketSnapshotSection` / `MarketSnapshotItem` 无法安全约束或查询该 contract，需要 bounded migration 或升级为 new canonical actuals table，并再次 escalation。
- 需要新增 `PostMarketReview` writer/service/API，将 outcome facts 和 evidence 写入 review revision。
- `/daily/after-close` 可在 `RT-S10-001` 保持 compatibility-only；完整替换仍属于 `RT-S10-004`，除非用户另行授权合并。

### Updated RT-S10-001 Acceptance Criteria

恢复 implementation 后，`RT-S10-001` 只有满足以下条件才可接受：

- formal `post_close_symbol_ohlcv_actuals` snapshot contract 已实现并验证；
- every pre-market `Signal` has either an actual row or an explicit non-success state；
- actual result / MFE / MAE / return 均来自 formal post-close actual snapshot；
- approved imported actuals 只补充 execution-specific fields；
- missing/conflict/invalid/insufficient coverage 不会被默认为 zero/false/success；
- `PostMarketReview.signal_results_json` 和 `evidence_json` 绑定 plan、signal、market snapshot、dataset snapshot、fingerprints 和 metric policy；
- no live Provider / legacy Job / Workflow / Pipeline / Artifact / file JSON / legacy post-market report / mutable latest source is formal input；
- no attribution / proposals / Stage 11 automation is generated。

### Tests

未运行 production tests。

原因：

- 本次只修改 contract documentation，未实现 production code。
- 当前 review 目标是解除 source-of-truth decision blocker，而不是验证实现。

替代检查：

- 读取 required docs、current git status/diff、相关 models/services/routes/tests。
- 运行 `refactor-orchestrator` runtime probe。
- 使用 2 个 read-only explorer 完成独立 repository mapping。

### Files Updated

- `docs/refactor-implementation-plans/stage-10-implementation-plan.md`
- `docs/refactor-implementation-logs/stage-10.md`
- `docs/Refactor-Implementation-Log.md`

### Acceptance Conclusion

`RT-S10-001` implementation may resume later under the frozen Decision 1 contract, but this Session did not resume implementation and did not accept `RT-S10-001`。

推荐 resumed implementation session：

- model/session：`gpt-5.4` Task Implementation
- escalation back to `gpt-5.5` if Option A proves unsafe, migration/source-of-truth changes exceed this contract, or implementation needs attribution/proposals/Stage 11 behavior。

## 2026-06-22 RT-S10-001 Signal Outcome Implementation

### Status

`[-] 进行中`

`RT-S10-001` 已恢复 implementation，并完成 formal post-close actuals contract、formal read API、`PostMarketReview` writer/service/API 和 focused verification。当前尚未执行 Stage 10 Gate，因此本 Task 不能标记为 `[x]`。

### Delegation

使用 `refactor-orchestrator`。

- Parent：负责 contract gate、implementation、review、verification 和正式日志更新。
- 1 个 read-only `refactor_explorer_mini`：审计 `MarketSnapshot` / `DatasetSnapshot` / `PostMarketReview` / Stage 9 canonical surfaces 是否足以支撑 Option A。
- 未委派 Executor：本次写入边界集中，且 source-of-truth / acceptance review 紧耦合于 Parent。

### Scope

本次仅实现 `RT-S10-001 信号结果评估`：

- formal `post_close_symbol_ohlcv_actuals` MarketSnapshot section/item contract validator 和 read model；
- `PostCloseActualsRepository.get_actuals_for_signals(...)` formal read API；
- `PostMarketReviewService` signal outcome evaluation / writer；
- formal after-close API endpoints；
- focused unit/API/OpenAPI verification；
- implementation log updates。

明确未执行：

- `RT-S10-002` 结构化归因；
- `RT-S10-003` 优化建议；
- `RT-S10-004` `/daily/after-close` full UI replacement；
- Stage 11 automation / alerting；
- live Provider calls；
- strategy / rule / profile / proposal mutation。

### Files Changed

- `src/services/post_close_actuals_service.py`
- `src/db/repositories/post_market_review_repo.py`
- `src/db/repositories/daily_trading_plan_repo.py`
- `src/db/repositories/__init__.py`
- `api/routers/ui/daily_after_close.py`
- `api/routers/ui/__init__.py`
- `api/app.py`
- `tests/unit/services/test_daily_trading_plan_service.py`
- `tests/api/routers/ui/test_daily_after_close.py`
- `tests/api/test_ui_openapi_contract.py`
- `docs/refactor-implementation-logs/stage-10.md`
- `docs/Refactor-Implementation-Log.md`

### Contract Compliance

已实现并验证的 frozen Decision 1 contract：

- formal section name：`post_close_symbol_ohlcv_actuals`；
- `PostCloseActualRow` 显式校验 `symbol`、`trade_date`、`open/high/low/close`、optional `previous_close`、`volume`、`turnover`、instrument metadata、source timestamps、`available_at`、`frozen_at`、`dataset_snapshot_id`、`dataset_content_fingerprint`、`row_fingerprint`、`quality_state`、`availability_state`、`evidence_window`、`actuals_contract_version`；
- section payload 显式绑定 `dataset_snapshot_id`、`dataset_content_fingerprint`、`row_count`、`missing_symbols`、`conflict_symbols`、`quality_summary`、`actuals_contract_version`；
- read path 检查 `MarketSnapshot.content_fingerprint`、section `raw_payload_fingerprint`、row `row_fingerprint` 可追溯；
- `daily_bar` approximation 仅在 `intraday_approximation = true` 时接受；
- 每个 approved pre-market `Signal` 返回一条 actual row 或 explicit `insufficient_coverage` / `conflict` / `invalid` / `unavailable` state；
- `PostMarketReview.signal_results_json` 和 `evidence_json` 记录 plan / signal / snapshot / dataset / row fingerprint / metric policy / unavailable reasons；
- `PostMarketReview.attribution_json` 固定为 unavailable，占位 `RT-S10-002_not_started`；
- `executed` 固定保持 unavailable，未引入 imported actuals supplement 冒充正式执行事实。

### Actuals Source Contract Result

Option A 在当前 schema 下可安全落地，理由如下：

- `market_snapshot_sections` 已有 `(snapshot_id, section_id)` uniqueness；
- `market_snapshot_items` 已有 `(snapshot_id, section_id, item_key)` uniqueness，且支持 `snapshot_id + section_id`、`snapshot_id + symbol`、`dataset_id` 查询；
- `raw_payload_fingerprint`、`content_fingerprint`、`dataset_snapshot_id`、`dataset_content_fingerprint`、`row_fingerprint` 均已纳入 formal validator 和 read checks；
- 未发现必须新增 actuals table 的强制证据；
- 因此本次未新增 migration。

### Outcome Semantics

- `triggered`：依据 canonical `Signal.signal_state` + `side` 计算；`approved/executed + BUY/SELL` 视为 triggered；`HOLD` 视为 explicit not-triggered；其余不明状态返回 `invalid`；
- `executed`：固定为 `unavailable`，reason=`approved_execution_supplement_missing`；未把缺失 execution evidence 当成 `false`；
- `actual result` / `MFE` / `MAE` / `return`：仅来自 formal post-close actual row；
- `return` baseline：Parent acceptance repair 后，valid `Signal.entry_price.value` / `price` 优先；只有 signal contract 显式声明 previous-close baseline 时才使用 row `previous_close`；缺失 baseline 返回 `unavailable`，绝不默认 `0`；
- `matched rule`：来自 `Signal.rule_version_ids` / `triggered_rules` 和 `DailyRuleSelectionItem` 交集；
- `market-state change`：比较 pre-market `DailyRuleSelection.market_state_id` 和 optional post-close market state；缺失 post-close market state 时返回 `unavailable`。

### Tests

已运行：

- `../.venv/bin/python -m pytest tests/unit/services/test_daily_trading_plan_service.py -q`
- `../.venv/bin/python -m pytest tests/api/routers/ui/test_daily_after_close.py tests/api/test_ui_openapi_contract.py -q`
- `../.venv/bin/python -m pytest tests/unit/db/repositories/test_market_data_repositories.py tests/unit/services/test_dataset_snapshot_service.py -q`
- `../.venv/bin/python -m py_compile src/services/post_close_actuals_service.py src/db/repositories/post_market_review_repo.py api/routers/ui/daily_after_close.py`
- `git diff --check`

结果：

- service tests：`9 passed`
- API/OpenAPI tests：`3 passed`
- adjacent repository/dataset tests：`5 passed`
- `py_compile`：passed
- `git diff --check`：passed

Focused verification covered：

- actual row lookup for every signal under approved `TradingDayPlan`
- missing symbol / conflict symbol coverage states
- triggered / hold-not-triggered cases
- actual result / MFE / MAE / return calculations
- missing `previous_close` keeps return unavailable
- no attribution / proposal generation in Stage 10 files
- formal API / OpenAPI wiring

未运行：

- frontend tests / `pnpm typecheck`：本次未修改前端 TypeScript client/page
- migration tests：本次无 schema migration
- browser E2E：本次未触及 formal `/daily/after-close` page replacement

### Known Risks

- 当前未消费 approved imported execution supplement；execution-specific actuals 仍为 unavailable，且不会被默认为 false/success。
- 本次新增的是 formal after-close API，不是 `/daily/after-close` full product UI；用户侧完整盘后页仍待 `RT-S10-004`。
- `PostMarketReview.quality_status` 当前按 coverage state 粗分 `complete/partial`；如后续 Gate 需要更细粒度映射，可在 frozen contract 内微调。
- 尚未对 imported actuals supplement 建立 approval/read contract；这仍属于后续 bounded work，而非本次 blocker。

### Acceptance Conclusion

`RT-S10-001` production implementation 已恢复并通过 focused verification，但当前 Session 尚未执行 Parent acceptance review，因此 Task 状态保持 `[-] 进行中`。

当前结论：

- formal actuals source contract：`implemented under Option A`
- no escalation required at implementation-review stage
- no second formal outcome source introduced
- no direct mutation of formal strategy/rule/profile/proposal objects
- `RT-S10-002` / `RT-S10-003` / `RT-S10-004` / Stage 11 仍未开始

下一步推荐：

- 对当前 diff 执行 Parent acceptance review；
- 如无新的 BLOCKER/HIGH findings，可将 `RT-S10-001` 标记为 accepted；
- 之后再由用户单独授权 `RT-S10-002`。

## 2026-06-22 RT-S10-001 Parent Acceptance Review

### Status

`[x] 已完成`

Parent acceptance decision：`ACCEPTED`。

Stage 10 仍为 `[-] 进行中`；本次只接受 `RT-S10-001`，未开始 `RT-S10-002`、`RT-S10-003`、`RT-S10-004` 或 Stage 11。

### Delegation

使用 `refactor-orchestrator` 规则；本环境未发现独立可调用的 `refactor-orchestrator` skill 文件，因此按已安装 refactor subagent roles 执行：

- Parent：读取 mandatory docs、完整 diff、changed files、相关 models/services/tests，执行 acceptance decision 与 bounded repairs。
- Explorer Beta：formal contract / outcome evidence review，发现 baseline policy 与 schema drift blockers。
- Explorer Alpha：boundary / legacy isolation review，发现 matched-rule evidence blocker。
- Explorer Gamma：test/API/frontend coverage review，确认无 frontend diff，提出 value-domain validation 与 post-close market-state lookup hardening 为 non-blocking。

### Reviewed Files

- `AGENTS.md`
- `trade-strategy-ai/AGENTS.md`
- `docs/Trade-Refactor-TaskList.md`
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
- `docs/PROMPT_REVIEW_AND_MIGRATION.md`
- `docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
- `docs/refactor-implementation-plans/stage-10-implementation-plan.md`
- `docs/refactor-implementation-logs/stage-10.md`
- `docs/Refactor-Implementation-Log.md`
- `src/services/post_close_actuals_service.py`
- `src/db/repositories/post_market_review_repo.py`
- `src/db/repositories/daily_trading_plan_repo.py`
- `src/db/repositories/__init__.py`
- `api/routers/ui/daily_after_close.py`
- `api/routers/ui/__init__.py`
- `api/app.py`
- `src/models/stage2_canonical.py`
- `src/models/signal.py`
- `src/models/market_data_snapshot.py`
- `src/models/market_data_snapshot_section.py`
- `src/models/market_data_snapshot_item.py`
- `tests/unit/services/test_daily_trading_plan_service.py`
- `tests/api/routers/ui/test_daily_after_close.py`
- `tests/api/test_ui_openapi_contract.py`

### Bounded Repairs During Review

- Hardened `PostCloseActualRow` with `extra="forbid"` and bounded value domains for `frequency`、`adjustment_policy`、`quality_state`、`availability_state`、`evidence_window`。
- Cross-checked actual rows against section-level `dataset_snapshot_id`、`dataset_content_fingerprint`、`row_fingerprints` and item `dataset_id`。
- Fixed baseline policy：valid `Signal.entry_price.value` / `price` is primary baseline；`previous_close` is used only when `Signal.entry_price.baseline_policy` explicitly declares `previous_close_daily_market_signal` / `previous_close`；missing baseline remains `unavailable`。
- Fixed matched-rule evidence：`Signal.rule_version_ids` and `Signal.triggered_rules` are unioned before intersecting `DailyRuleSelectionItem`，instead of ignoring `triggered_rules` when `rule_version_ids` is non-empty。
- Added focused tests for extra-field drift、invalid value-domain drift、dataset binding mismatch、entry-price baseline precedence、missing baseline policy、matched-rule union evidence。

### Contract Compliance

- Option A is accepted：`post_close_symbol_ohlcv_actuals` is the formal bounded `MarketSnapshotSection` / `MarketSnapshotItem` contract for post-close actuals.
- Every pre-market `Signal` returns either a validated actual row or explicit non-success state (`insufficient_coverage` / `conflict` / `invalid` / `unavailable`)。
- Actual result、MFE、MAE、return are computed only from formal post-close actual rows; no live Provider, legacy report, file JSON, mutable latest row or raw `trade_logs` are formal inputs.
- `PostMarketReview.signal_results_json` stores program-fact outcome evidence; `evidence_json` binds plan、signals、post-close market snapshot、dataset snapshot、row fingerprints、metric policy version and unavailable/conflict reasons.
- `Signal.evaluation_result_id` remains compatibility placeholder and is not written as formal outcome source.
- `PostMarketReview.attribution_json` remains unavailable with `RT-S10-002_not_started`; no attribution, proposals, LLM calls, Stage 11 automation or alerting were introduced.

### Tests

已运行：

- `../.venv/bin/python -m pytest tests/unit/services/test_daily_trading_plan_service.py tests/api/routers/ui/test_daily_after_close.py tests/api/test_ui_openapi_contract.py`
- `../.venv/bin/python -m pytest tests/unit/db/repositories/test_market_data_repositories.py tests/unit/services/test_dataset_snapshot_service.py`
- `../.venv/bin/python -m py_compile src/services/post_close_actuals_service.py src/db/repositories/post_market_review_repo.py api/routers/ui/daily_after_close.py`
- `git diff --check`
- RT-S10-001 implementation-path grep for LLM / proposal / legacy / Provider / config / Stage 11 / alerting terms

结果：

- service/API/OpenAPI：`18 passed`
- adjacent market snapshot / dataset tests：`5 passed`
- `py_compile`：passed
- `git diff --check`：passed
- boundary grep：no matches in RT-S10-001 implementation path

未运行：

- frontend tests / `pnpm typecheck`：本次未修改 frontend source 或 TypeScript types。
- migration tests：本次未新增 database migration。
- browser E2E：本次未替换 `/daily/after-close` formal UI，仍留给 `RT-S10-004`。

### Residual Risks And Classification

- execution supplement not implemented：`non-blocking for RT-S10-001`。Execution-specific fields remain explicit `unavailable` and are not defaulted to false/success。
- `/daily/after-close` formal user page not replaced：`non-blocking for RT-S10-001`。Full UI replacement is explicitly scoped to `RT-S10-004`。
- Stage 10 Gate not run：`non-blocking for RT-S10-001 acceptance`。Stage 10 remains in progress and Gate must run after authorized Stage 10 tasks are complete。
- post-close market-state ID is caller-supplied and not resolved to a canonical `MarketRegimeRecord` in this task：`non-blocking hardening`。Missing state remains `unavailable`; invalid supplied state lookup can be hardened before or during later Stage 10 review if required。

### Acceptance Conclusion

`RT-S10-001` is `ACCEPTED` under the frozen Stage 10 Decision 1 / Option A contract.

Next allowed action：wait for explicit user authorization for `RT-S10-002 结构化归因` or a separate Stage 10 Gate/review action. Do not start `RT-S10-002`、`RT-S10-003`、`RT-S10-004` or Stage 11 automatically.

## 2026-06-22 RT-S10-002 结构化归因

### Status

`[x] 已完成`

Parent acceptance decision：`ACCEPTED`。

Stage 10 仍为 `[-] 进行中`；本次只接受 `RT-S10-002`，未开始 `RT-S10-003`、`RT-S10-004` 或 Stage 11。

### Delegation

使用 `refactor-orchestrator`。

- Parent：负责 frozen contract、deterministic attribution policy、production implementation、verification、review 和正式日志更新。
- 1 个 `refactor_executor_mini`：仅负责 `tests/unit/services/test_daily_trading_plan_service.py` 的 RED 测试铺设，不修改 production code。
- Parent 在接收 handoff 后修正了部分红测断言，使其与 frozen Stage 10 contract 对齐：
  - `attribution_json.state` 保持事实覆盖状态，不把 category 写成 state；
  - `degraded` 是 state，不是正式 attribution category；
  - 缺失 post-close market-state evidence 不会被伪装成 market-state identification issue。

### Scope

本次仅实现 `RT-S10-002 结构化归因`：

- 基于 `RT-S10-001` 已持久化的 `signal_results_json` / `evidence_json` 生成 deterministic structured attribution；
- 把最终归因写入 `PostMarketReview.attribution_json`；
- 新增受限 attribution recompute service method，仍以已落库 program facts 为正式输入；
- focused unit verification；
- 正式实施日志更新。

明确未执行：

- `RT-S10-003` proposal generation；
- `RT-S10-004` `/daily/after-close` full UI replacement；
- LLM prompt runtime integration；
- live Provider calls；
- strategy / rule / profile / proposal mutation；
- Stage 11 automation / alerting。

### Files Changed

- `src/services/post_close_actuals_service.py`
- `tests/unit/services/test_daily_trading_plan_service.py`
- `docs/refactor-implementation-logs/stage-10.md`
- `docs/Refactor-Implementation-Log.md`

### Implementation Summary

- `evaluate_signal_outcomes(...)` 现在在写入 `PostMarketReview.signal_results_json` 后，同步生成 deterministic attribution payload 并写入 `PostMarketReview.attribution_json`。
- 新增 `SignalAttributionEvaluationRequest` / `SignalAttributionEvaluationResult` 和 `evaluate_signal_attribution(...)`，用于基于现有 `PostMarketReview` program facts 重新生成归因，不重算 RT-S10-001 outcome facts。
- 新增 `stage10-structured-attribution-v1` payload：
  - `state`：formal attribution coverage state（`ready/partial/unavailable/conflict/invalid/insufficient_coverage/degraded`）
  - `primary_category`
  - `signals[]`
  - `summary`
  - `llm_validation`
  - `review_evidence_fingerprint`
  - `proposal_state`
  - `attribution_fingerprint`
- 每个 signal attribution 统一输出：
  - `signal_id` / `symbol`
  - `state`
  - `category`
  - `confidence`
  - `reasons`
  - `program_facts`
  - `llm_validation`
  - `user_explanation`

### Deterministic Attribution Rules

- `data issue`
  - 当 `RT-S10-001` outcome evidence 已明确是 `partial/unavailable/conflict/invalid/insufficient_coverage/degraded` 时使用。
- `market-state identification issue`
  - 仅当盘后 program fact 已明确 `market_state_change = changed` 且 outcome 对信号不利时使用。
- `rule issue`
  - 仅当 matched rule evidence 为 ready、selection decision 未显示组合降权/混合、且 outcome 对信号不利时使用。
- `strategy-composition issue`
  - 仅当 matched rule evidence 为 ready、命中多个规则或存在 `reduced/blocked` 等混合 decision、且 outcome 对信号不利时使用。
- `execution issue`
  - 仅当 `executed.state = ready` 且存在 explicit execution evidence 时使用；缺失 execution supplement 继续保持 unavailable，不会默认归因为 execution issue。
- `unattributable`
  - 其余 truthfully 不能落入前五类的信号使用。

### LLM Boundary / No-LLM Proof

- 本次未接入 `llm_attribution_v1` 或 `llm_postmortem_notes_v1` runtime。
- `PostMarketReview.prompt_run_id` 保持 `None`。
- payload 仍记录 deterministic `llm_validation` gate：
  - `low_confidence_multiple_candidate_categories`
  - `evidence_conflict`
  - `important_signal`
- gate 只记录 eligibility，不触发 runtime call，也不会替换 program facts。

### Contract Compliance

- Attribution 只消费 `PostMarketReview.signal_results_json` / `evidence_json` 中的 RT-S10-001 program facts，不重新计算 `actual_result`、`MFE`、`MAE`、`return`、`triggered`、`executed`、`matched rule` 或 `market-state change`。
- 每个 evaluated signal 都会得到一个正式 category（含 `unattributable`）和一个独立的 formal state。
- `execution supplement` 缺失仍是 explicit unavailable，不会变成 execution issue。
- 未生成 `RuleOptimizationProposal`、`AuthorProfileRevisionProposal` 或 `StrategyRevisionProposal`。
- 未修改 `RuleVersion`、`RuleApplicabilityProfile`、`AuthorProfileVersion`、`StrategyVersion`、`Strategy.current_published_version_id`、`DailyRuleSelection`、`DailyStrategyInstance`、`TradingDayPlan` source traceability 或 signal outcome program facts。
- 未新增 API / OpenAPI / frontend / migration surface。

### Tests

已运行：

- `../.venv/bin/python -m pytest tests/unit/services/test_daily_trading_plan_service.py -q`
- `../.venv/bin/python -m py_compile src/services/post_close_actuals_service.py`
- `rg -n "llm_attribution_v1|llm_postmortem_notes_v1|OptimizationProposal|Stage 11|alert|Provider|config_path|Job|Workflow|Pipeline|Artifact" src/services/post_close_actuals_service.py tests/unit/services/test_daily_trading_plan_service.py`
- `git diff --check`

结果：

- unit tests：`25 passed`
- `py_compile`：passed
- boundary grep：only test fixture references to `OptimizationProposal` remained; no Stage 10 attribution implementation path introduced LLM runtime / proposal generation / Stage 11 / legacy formal input usage
- `git diff --check`：passed

Focused verification covered：

- all six attribution categories（其中 execution issue 通过 explicit persisted execution evidence 的 recompute path 验证）
- low-confidence / evidence-conflict / important-signal LLM gate eligibility
- attribution_json persistence
- unavailable / partial / conflict / invalid / degraded attribution states
- execution supplement missing does not become execution issue by default
- no LLM fact replacement
- no proposal generation

未运行：

- API/router/OpenAPI tests：本次未修改 API contract
- frontend tests / `pnpm typecheck`：本次未修改 frontend / TS types
- migration tests：本次未新增 database migration
- browser E2E：本次未触及 `/daily/after-close` full UI

### Residual Risks

- execution supplement 仍未实现；execution-specific positive/negative归因仍依赖后续 approved supplement contract。
- post-close market-state ID 仍是 caller-supplied residual risk；本次只消费既有 RT-S10-001 program facts，不在 RT-S10-002 内扩展 canonical lookup。
- `/daily/after-close` 仍未替换为 formal product page；完整用户侧展示仍属于 `RT-S10-004`。
- Stage 10 Gate 尚未运行。

### Acceptance Conclusion

`RT-S10-002` is `ACCEPTED` under the frozen Stage 10 contract.

Current conclusion：

- deterministic structured attribution is persisted in `PostMarketReview.attribution_json`
- no LLM runtime call was introduced
- no proposal objects were generated
- no formal strategy/rule/profile/current pointer mutation was introduced
- `RT-S10-003` / `RT-S10-004` / Stage 11 remain unstarted

Next allowed action：wait for explicit user authorization for `RT-S10-003 优化建议`、`RT-S10-004 盘后用户页面` or a later Stage 10 review/Gate action. Do not start any of them automatically.

## 2026-06-22 RT-S10-003 优化建议

### Status

`[x] 已完成`

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定本次不委派 subagent，按 single-controller fallback 执行：

- runtime probe 已验证 custom subagent config files 存在；
- 但当前 Session 中 native spawning availability / effective permission boundary / exact child runtime 均未被独立证明；
- 本 Task 的 contract、写入路径与验证集都集中在同一组 service/repo/router/tests，继续强行委派的收益低于协调成本。

### Scope

本次只实现 `RT-S10-003 优化建议`：

- 基于已接受的 `RT-S10-001` outcome evidence 与 `RT-S10-002` deterministic structured attribution 生成分离的正式建议记录；
- 新增 Stage 10 proposal generation/list/detail/review/accept API；
- 新增 focused backend/router tests；
- 更新 Stage 10 日志与主实施日志。

明确未执行：

- `/daily/after-close` formal page replacement
- Stage 11 automation / alerting
- live Provider calls
- legacy post-market reports / Job / Workflow / Pipeline / Artifact formal input
- LLM fact generation

### Contract Compliance

- 保持三条 proposal lane 独立：
  - `rule_optimization`
  - `author_profile_revision`
  - `strategy_revision`
- 仍复用 canonical `OptimizationProposal`，但 `proposal_type`、`target`、`evidence`、`review_binding`、`available_actions`、中文标签与 acceptance behavior 保持 type-specific。
- `PostMarketReview.signal_results_json` 与 `PostMarketReview.attribution_json` 只作为输入证据读取；本 Task 不回写 outcome facts 或 attribution facts。
- 每条建议绑定：
  - `post_market_review_id`
  - `trading_day_plan_id`
  - `daily_strategy_instance_id`
  - `strategy_version_id`
  - `signal_ids`
  - `attribution_categories`
  - `outcome_metrics`
  - `relevant_rule_version_ids`
  - `relevant_author_profile_version_ids`
  - `relevant_strategy_membership_ids`
  - `source_quality_states`
  - `deterministic_reason_list`
  - `stage10-optimization-proposal-v1`
- `rule_optimization` 与 `author_profile_revision` 只提供 `start_review / continue_observing / reject` 有界动作，不生成 formal draft，不直接变更 `RuleVersion`、`RuleApplicabilityProfile` 或 `AuthorProfileVersion`。
- `strategy_revision` 允许 `accept_to_draft`，但仍复用 Stage 8 已接受的 strategy proposal governance：
  - 只允许落到 draft；
  - 不发布；
  - 不修改 `Strategy.current_published_version_id`。
- 缺失 execution supplement 仍不会默认创建 execution-specific proposal。
- `post_close_market_state_id` 缺失仍保持 unavailable，不会变成 unchanged。

### Implementation Summary

- `src/services/post_close_actuals_service.py`
  - 新增 `OptimizationProposalGenerationRequest` / `OptimizationProposalReviewRequest` / `OptimizationProposalAcceptRequest`。
  - 新增 Stage 10 proposal generation/list/detail/review/accept service methods。
  - 新增 deterministic proposal evidence builder、type-specific target view、review binding、available actions 与 idempotent generation fingerprint。
  - 仅策略建议允许委托到现有 Stage 8 `StrategyCenterService.accept_proposal_to_draft(...)`。
- `src/db/repositories/strategy_repo.py`
  - 新增 generic proposal list helpers。
  - 新增 `get_rule_version(...)`、`get_author_profile_version(...)`。
- `api/routers/ui/daily_after_close.py`
  - 新增：
    - `POST /api/ui/v1/daily/after-close/proposals/generate`
    - `GET /api/ui/v1/daily/after-close/proposals`
    - `GET /api/ui/v1/daily/after-close/proposals/{proposal_id}`
    - `POST /api/ui/v1/daily/after-close/proposals/{proposal_id}/review`
    - `POST /api/ui/v1/daily/after-close/proposals/{proposal_id}/accept-to-draft`
- `tests/unit/services/test_daily_trading_plan_service.py`
  - 新增 RT-S10-003 focused service tests。
- `tests/api/routers/ui/test_daily_after_close.py`
  - 新增 proposal router tests。

### Verification

已运行：

- `rtk proxy pytest tests/unit/services/test_daily_trading_plan_service.py -q`
- `rtk proxy pytest tests/api/routers/ui/test_daily_after_close.py tests/api/test_ui_openapi_contract.py -q`
- `rtk git diff --check`
- `rtk rg -n "Job|Workflow|Pipeline|Artifact|config_path|live Provider|mutable latest|LLM" src/services/post_close_actuals_service.py api/routers/ui/daily_after_close.py tests/unit/services/test_daily_trading_plan_service.py tests/api/routers/ui/test_daily_after_close.py`

结果：

- `tests/unit/services/test_daily_trading_plan_service.py`：`30 passed`
- `tests/api/routers/ui/test_daily_after_close.py` + `tests/api/test_ui_openapi_contract.py`：`6 passed`
- `git diff --check`：passed
- legacy isolation grep：未发现本次 RT-S10-003 formal path 引入 legacy formal input；唯一命中为既有 RT-S10-002 LLM gate 文案，仍明确 `未调用 LLM`

Focused verification covered：

- three proposal lanes remain separated
- proposal_type / target / evidence binding
- no generic AI suggestion lane
- rule proposal review actions do not mutate `RuleVersion` or `RuleApplicabilityProfile`
- author proposal review actions do not mutate `AuthorProfileVersion`
- strategy proposal acceptance stays draft-only and keeps current strategy pointer unchanged
- `accept / reject / continue_observing` lifecycle coverage
- missing evidence keeps `partial/unavailable/continue_observing`
- missing execution supplement does not become execution proposal
- router/OpenAPI coverage for new endpoints
- no frontend/type changes

### Residual Risks

- execution supplement 仍未实现；execution-specific proposal reasons 继续 unavailable，除非后续有 explicit execution evidence。
- `post_close_market_state_id` 仍是 caller-supplied residual risk；缺失时 proposal evidence 继续记录 unavailable。
- `/daily/after-close` 正式用户页面仍未替换，完整页面仍属于 `RT-S10-004`。
- Stage 10 Gate 尚未运行。

### Acceptance Conclusion

`RT-S10-003` is `ACCEPTED` under the frozen Stage 10 contract.

Current conclusion：

- separate rule / author-profile / strategy proposal lanes now exist
- proposal generation consumes only finalized RT-S10-001 / RT-S10-002 evidence
- no LLM runtime call was introduced
- rule/profile proposal handling remains bounded to review/observe/reject
- strategy proposal acceptance remains draft-only and does not mutate current pointer
- no formal rule/profile/strategy/current pointer mutation occurs from generation or non-strategy review actions
- `RT-S10-004` 与 Stage 11 remain unstarted

Next allowed action：wait for explicit user authorization for `RT-S10-004 盘后用户页面` or a later Stage 10 Gate / review action. Do not start Stage 11 automatically.

## 2026-06-22 RT-S10-004 盘后用户页面

### Status

`[x] 已完成`

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定本次只委派 1 个 read-only `refactor_explorer_mini` 做有界盘点，生产实现与验收由 Parent 单控制完成：

- Explorer：核对 `/daily/after-close` 当前 route/page/client、Stage 10 formal API/service contracts、`RT-S10-001/002/003` 已改文件与测试、`/daily/pre-market` 现有正式页面约定。
- Parent：冻结读取边界、确认无需 contract escalation、实现 `/daily/after-close` formal replacement、执行 focused verification、更新正式日志。

未委派 Executor：

- 本 Task 的写入路径集中在单个 formal page、daily client/types 和 bounded after-close API response-shaping；
- 共享写集高度耦合，额外委派的协调成本高于收益。

### Scope

本次只实现 `RT-S10-004 盘后用户页面`：

- 用 formal user-facing page 替换 `/daily/after-close` 对 legacy `StrategyAfterCloseWorkspacePage` 的正常产品面；
- 新增只读 formal post-market review 聚合接口，供页面读取既有 Stage 10 canonical evidence；
- 新增 daily after-close frontend client/types；
- 新增 focused frontend/API/OpenAPI verification；
- 更新 Stage 10 日志与主实施日志。

明确未执行：

- RT-S10-001 outcome calculation changes
- RT-S10-002 attribution logic changes
- RT-S10-003 proposal governance changes
- Stage 11 automation / alerting
- live Provider calls
- legacy job/report workspace 作为 formal input
- execution supplement implementation

### Contract Compliance

- `/daily/after-close` 已不再导入或渲染 `StrategyAfterCloseWorkspacePage` 作为 formal page。
- formal page 只消费 canonical Stage 9 / Stage 10 inputs：
  - `TradingDayPlan`
  - `PostMarketReview.signal_results_json`
  - `PostMarketReview.attribution_json`
  - `OptimizationProposal` separated lanes
  - 已接受的 daily after-close API contracts
- 新增只读 `GET /api/ui/v1/daily/after-close/review`：
  - 只聚合既有 `PostMarketReview`、`TradingDayPlan` 和 persisted evidence；
  - 不生成 outcome / attribution / proposal facts；
  - 不改动 RT-S10-001/002/003 source-of-truth。
- proposal actions仍遵守 RT-S10-003 frozen boundary：
  - rule / author-profile：只允许 `start_review / continue_observing / reject`
  - strategy：仅允许 `accept_to_draft`
  - 不发布
  - 不修改 `Strategy.current_published_version_id`
- execution supplement 缺失继续显示 unavailable，不会默认成功。
- missing `post_close_market_state_id` 继续显示 unavailable，不会显示 unchanged。
- 普通用户文案保持业务中文；未在 normal copy 暴露 `Job`、`Workflow`、`Pipeline`、`Artifact`、`Provider`、`config_path`、`DatasetSnapshot`、`MarketSnapshot`、snake_case traceability keys 或 `Regime`。

### Implementation Summary

- `src/services/post_close_actuals_service.py`
  - 新增 `PostMarketReviewView`。
  - 新增 `get_post_market_review(...)` 只读聚合方法。
  - 新增 review payload state normalization / aggregation，保留 `ready / partial / unavailable / conflict / invalid / insufficient_coverage / degraded` truthfully。
- `api/routers/ui/daily_after_close.py`
  - 新增 `GET /api/ui/v1/daily/after-close/review`。
- `tests/api/routers/ui/test_daily_after_close.py`
  - 新增 formal review route test。
- `tests/api/test_ui_openapi_contract.py`
  - 新增 `/api/ui/v1/daily/after-close/review` contract coverage。
- `web/src/types/daily.ts`
  - 新增 after-close review / signal result / proposal typed contracts。
- `web/src/lib/api/daily.ts`
  - 新增 after-close review / proposal generate / list / review / accept client methods。
- `web/src/pages/daily/after-close-page.tsx`
  - 新增 formal post-market page。
  - 按正式页面结构展示：
    - `盘前预测`
    - `实际结果`
    - `差异`
    - `成功原因`
    - `失败原因`
    - `建议操作`
  - 新增 truthfully unavailable / partial / conflict / invalid / degraded guidance。
  - 新增 separated proposal action panel。
  - 技术 traceability 仅保留在 admin collapsed details。
- `web/src/pages/daily/index.tsx`
  - `/daily/after-close` 改为引用 formal `TodayAfterClosePage`，移除 legacy workspace wrapper。
- `web/src/pages/daily/index.test.tsx`
  - 删除 legacy after-close workspace assertions，保留 overview / pre-market focused tests。
- `web/src/pages/daily/after-close-page.test.tsx`
  - 新增 formal page states / sections / proposal action boundary tests。

### Verification

已运行：

- `pytest tests/api/routers/ui/test_daily_after_close.py tests/api/test_ui_openapi_contract.py`
- `pnpm vitest run src/pages/daily/index.test.tsx src/pages/daily/pre-market.test.tsx src/pages/daily/after-close-page.test.tsx`（`web/`）
- `pnpm typecheck`（`web/`）
- `git diff --check`
- `rg -n "StrategyAfterCloseWorkspacePage|StrategyAfterClosePage" web/src/pages/daily web/src/lib/api/daily.ts api/routers/ui/daily_after_close.py -g '!**/*.test.*'`

结果：

- API/OpenAPI：`7 passed`
- frontend vitest：`12 passed`
- `pnpm typecheck`：passed
- `git diff --check`：passed
- legacy workspace grep：formal `/daily/after-close` page path no longer imports or renders legacy workspace

Focused verification covered：

- `/daily/after-close` 不再使用 legacy workspace 作为 normal product surface
- page displays `盘前预测 / 实际结果 / 差异 / 成功原因 / 失败原因 / 建议操作`
- unavailable / partial / conflict render truthfully
- missing execution supplement displays unavailable, not success
- missing post-close market state displays unavailable, not unchanged
- proposal actions obey RT-S10-003 boundaries
- strategy accept-to-draft remains draft-only client path
- no internal developer terminology in normal user copy

未运行：

- browser E2E：本次未执行
- backend unit pytest for `PostMarketReviewService`：本次只做 bounded response-shaping 与 router coverage，未新增 service-level unit case

### Residual Risks

- execution supplement 仍未实现；成交相关字段继续 explicit unavailable。
- `post_close_market_state_id` 仍是 caller-supplied residual risk；缺失时 formal page 继续显示 unavailable。
- Stage 10 Gate 尚未运行。

### Acceptance Conclusion

`RT-S10-004` is `ACCEPTED` under the frozen Stage 10 contract.

Current conclusion：

- `/daily/after-close` 已替换为 formal user-facing post-market page
- page consumes canonical Stage 9 / Stage 10 APIs and persisted evidence only
- page does not create or alter outcome / attribution / proposal facts except existing explicit proposal review actions
- rule/profile proposal handling remains bounded to review / observe / reject
- strategy proposal acceptance remains draft-only and does not mutate current pointer
- Stage 10 仍为 `[-] 进行中`；Stage Gate 未运行

Next allowed action：wait for explicit user authorization for Stage 10 Gate / review action. Do not start Stage 11 automatically.

## 2026-06-22 Stage 10 Gate / Review

### Status

`ACCEPTED`

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定委派 2 个 read-only `refactor_explorer_mini`，并由 Parent 保留最终 Gate 判定：

- Explorer Beta：后端/API/测试契约审计，覆盖 `RT-S10-001 / RT-S10-002 / RT-S10-003`。
- Explorer Gamma：前端/docs/legacy isolation 审计，覆盖 `RT-S10-004` 和 `/daily/after-close` 用户页面。

未委派 Executor，因为 Gate 未发现 blocker/high finding；本次未做生产代码修复。

### Entry Verification

- `RT-S10-001`：已接受。
- `RT-S10-002`：已接受。
- `RT-S10-003`：已接受。
- `RT-S10-004`：已接受。
- Stage 11：未开始；未发现 Stage 11 automation、alerting 或 scheduling 新路径。
- Gate 前 working tree：clean。
- Gate 前完整 diff：empty。
- 本次 Stage 10 review 基线：`c2df735c025ea952e065fabeb2a5e693f83cbc7d..HEAD`。

### Reviewed Files

- `src/services/post_close_actuals_service.py`
- `src/db/repositories/post_market_review_repo.py`
- `src/db/repositories/daily_trading_plan_repo.py`
- `src/db/repositories/strategy_repo.py`
- `api/routers/ui/daily_after_close.py`
- `api/app.py`
- `api/routers/ui/__init__.py`
- `tests/unit/services/test_daily_trading_plan_service.py`
- `tests/api/routers/ui/test_daily_after_close.py`
- `tests/api/test_ui_openapi_contract.py`
- `web/src/pages/daily/after-close-page.tsx`
- `web/src/pages/daily/after-close-page.test.tsx`
- `web/src/pages/daily/index.tsx`
- `web/src/pages/daily/index.test.tsx`
- `web/src/lib/api/daily.ts`
- `web/src/types/daily.ts`
- `docs/Trade-Refactor-TaskList.md`
- `docs/refactor-implementation-plans/stage-10-implementation-plan.md`
- `docs/refactor-implementation-logs/stage-10.md`
- `docs/Refactor-Implementation-Log.md`
- `docs/AI-Conversation-Templates.md`

### Gate Checklist Results

- `RT-S10-001` accepted：pass。
- `RT-S10-002` accepted：pass。
- `RT-S10-003` accepted：pass。
- `RT-S10-004` accepted：pass。
- `post_close_symbol_ohlcv_actuals` actuals contract bounded and validated：pass。
- `actual_result` / `MFE` / `MAE` / `return` only derive from formal post-close actual rows：pass。
- `PostMarketReview.signal_results_json` and `evidence_json` bind plan, signals, snapshot, dataset, fingerprints and metric policy：pass。
- missing actuals remain explicit unavailable / partial / conflict / invalid / insufficient_coverage / degraded：pass。
- missing values are not defaulted to false / zero / success：pass。
- `Signal.evaluation_result_id` remains compatibility placeholder：pass。
- no live Provider, legacy reports, mutable latest source, file JSON, `config_path`, Job / Workflow / Pipeline / Artifact formal input：pass。
- deterministic structured attribution persisted in `PostMarketReview.attribution_json`：pass。
- every evaluated signal has structured attribution category or explicit non-success state：pass。
- fixed attribution categories preserved：pass。
- LLM does not create or replace facts；no runtime introduced, `prompt_run_id` remains `None`：pass。
- attribution does not mutate RT-S10-001 outcome facts：pass。
- proposal lanes remain separated as `rule_optimization` / `author_profile_revision` / `strategy_revision`：pass。
- no generic AI suggestion lane：pass。
- proposal generation consumes finalized RT-S10-001 / RT-S10-002 evidence：pass。
- rule/profile proposal actions remain review / continue observing / reject only：pass。
- strategy proposal acceptance remains draft-only：pass。
- `Strategy.current_published_version_id` is not modified by Stage 10 proposal generation or non-strategy review actions：pass。
- `/daily/after-close` is formal user-facing page, not legacy `StrategyAfterCloseWorkspacePage` wrapper：pass。
- page displays `盘前预测 / 实际结果 / 差异 / 成功原因 / 失败原因 / 建议操作`：pass。
- page consumes canonical Stage 9/10 API and persisted evidence only：pass。
- unavailable / partial / conflict / invalid / degraded states render truthfully：pass。
- execution-specific display remains unavailable when execution supplement is missing：pass。
- missing post-close market state displays unavailable, not unchanged：pass。
- normal user copy avoids forbidden internal terminology：pass。
- no unrelated changes included：pass。

### Findings

No BLOCKER or HIGH findings.

LOW findings retained as non-blocking:

- OpenAPI coverage for new after-close endpoints is path/request-body focused; response-schema locking is partial.
- `/strategies/after-close` remains a compatibility route to legacy after-close surface until later retirement.
- `/daily` overview still has internal job-summary plumbing, but rendered user copy is sanitized and `/daily/after-close` does not consume it as formal input.

### Verification

已运行：

- `pytest tests/api/routers/ui/test_daily_after_close.py tests/api/test_ui_openapi_contract.py tests/unit/services/test_daily_trading_plan_service.py -q`
- `pnpm vitest run "after-close-page" "daily/index.test.tsx"`（`web/`）
- `pnpm typecheck`（`web/`）
- `python -m py_compile src/services/post_close_actuals_service.py src/db/repositories/post_market_review_repo.py api/routers/ui/daily_after_close.py`
- `git diff --check c2df735c025ea952e065fabeb2a5e693f83cbc7d..HEAD -- trade-strategy-ai`
- `rg` legacy isolation / internal user-copy grep for `/daily/after-close`
- `rg` Stage 11 / alerting / automation guard grep for Stage 10 changed paths
- OpenAPI runtime path inspection for `/api/ui/v1/daily/after-close/*`

结果：

- backend/API pytest：`37 passed`
- frontend vitest：`7 passed`
- frontend typecheck：passed
- backend `py_compile`：passed
- `git diff --check`：passed
- Stage 11 / alerting / automation grep：no matches in Stage 10 formal paths
- legacy/internal-term grep：formal `/daily/after-close` normal page copy has no forbidden terms; remaining hits are TypeScript field names/API params or compatibility-only daily overview internals

### Residual Risks And Classification

- execution supplement is not implemented：non-blocking；execution-specific fields are displayed as unavailable and are not used as false/success.
- `post_close_market_state_id` remains caller-supplied：non-blocking hardening；missing state remains unavailable, not unchanged.
- Stage 10 Gate was not previously run：resolved by this Gate.
- OpenAPI response-schema assertions for after-close endpoints are partial：hardening。
- `/strategies/after-close` compatibility route remains：future-stage / retirement follow-up；not the formal `/daily/after-close` path.
- browser E2E was not run：non-blocking residual under current project UI rules; focused API/frontend/typecheck verification passed.

### Bounded Repairs

None. No BLOCKER or required HIGH finding was found.

### Gate Decision

`Stage 10 Gate ACCEPTED`

Stage 10 每日盘后满足当前 frozen acceptance criteria：

- every signal has clear result and attribution, or truthful unavailable / partial / conflict / invalid / degraded state;
- single-day results do not directly overwrite formal rules, author profiles, strategies, or current pointers;
- user can accept, reject, or continue observing suggestions under proposal boundaries;
- `/daily/after-close` is formal user-facing UI and does not expose internal developer terminology in normal copy.

Next allowed action：only after explicit user authorization, start Stage 11 Bootstrap / planning. Do not start Stage 11 implementation, automation, alerting or scheduling from this Gate.
