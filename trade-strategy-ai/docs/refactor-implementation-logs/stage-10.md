# Stage 10 每日盘后实施日志

## Stage Summary

- Stage：`Stage 10 每日盘后`
- 当前活动：`Stage 10 Bootstrap`
- 当前状态：`Stage 10 Bootstrap READY`
- 当前 Task：`RT-S10-001 / RT-S10-002 / RT-S10-003 / RT-S10-004 未开始`
- 下一可执行项：`RT-S10-001 信号结果评估`
- 不得自动开始：不得自动启动 `RT-S10-001` implementation 或 `Stage 11`

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
