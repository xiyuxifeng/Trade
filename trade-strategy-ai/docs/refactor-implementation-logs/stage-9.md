# Stage 9 每日盘前实施日志

## 当前摘要

- Stage：`Stage 9 每日盘前`
- 当前活动：`Stage 9 Gate`
- 当前状态：`Stage 9 Gate ACCEPTED`
- 当前 Task：`RT-S9-001 / RT-S9-002 / RT-S9-003 均 ACCEPTED`
- 下一可执行项：等待用户明确授权后开始 `Stage 10 Bootstrap`
- 不得自动开始：不得自动启动 `Stage 10 每日盘后`

## 2026-06-21 Stage 9 Bootstrap

### Bootstrap Decision

`READY`

### Scope

本次只审计当前实现、冻结 Stage 9 每日盘前契约、创建 Stage 9 实施计划/日志并更新主实施日志。

未实施：

- 生产代码；
- 数据库迁移；
- API；
- 前端页面；
- Prompt；
- `DailyRuleSelection` 生成；
- `DailyStrategyInstance` 生成；
- `TradingDayPlan` 生成；
- Stage 10 盘后行为；
- E2E；
- 提交或推送。

### Entry Verification

- Stage 8 Gate：`ACCEPTED`。
- `RT-S8-001 策略草稿与发布`：`ACCEPTED`。
- `RT-S8-002 策略验证和回滚`：`ACCEPTED`。
- `RT-S8-003 策略优化建议`：`ACCEPTED`。
- Stage 9 Bootstrap 前未开始：未发现 Stage 9 plan/log。
- Branch：`main`。
- HEAD：`ceee5a55d223b7f3a4124d144a007189fec03647`。
- Bootstrap 前 working tree：clean。
- Bootstrap 前完整 diff：empty。

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定使用 single-controller fallback，选择 `0` 个 subagent。

Runtime probe verified:

- `.codex/skills/refactor-orchestrator/SKILL.md` exists.
- `.codex/agents/refactor-explorer-mini.toml` exists and declares `gpt-5.4-mini`, `read-only`.
- `.codex/agents/refactor-executor-mini.toml` exists and declares `gpt-5.4-mini`, `workspace-write`.

Runtime probe could not independently verify:

- Native subagent spawning in this session.
- Explorer effective read-only permissions.
- Spawned custom agents actually use `gpt-5.4-mini`.

Bootstrap is documentation and contract-freezing only, so Parent completed the bounded repository mapping directly. No Executor was used because Bootstrap prohibits production implementation.

### Verified Facts

- Formal strategy source-of-truth is canonical `StrategyVersion` in `strategy_versions`, scoped by canonical `Strategy` in `strategies`.
- Current formal strategy is read from `Strategy.current_published_version_id`.
- Formal strategy rule pool is `StrategyRuleMembership`.
- Strategy validation summary exists in `StrategyVersion.evidence_json.validation_summary`; publication is guarded by `validation_summary.state == "passed"`.
- `StrategyRevisionProposal` is represented by canonical `OptimizationProposal(proposal_type = strategy_revision)`.
- Proposal acceptance creates or links only draft `StrategyVersion` and records `accepted_draft_version_id`; it does not publish or mutate `Strategy.current_published_version_id`.
- Formal Stage 9 canonical data sources exist:
  - `DatasetSnapshot`
  - `MarketSnapshot`
  - `BacktestRun`
  - `BacktestResult`
  - `RuleApplicabilityProfile`
  - `AuthorProfileVersion(profile_kind = method)`
  - `AuthorProfileVersion(profile_kind = rule)`
  - `AuthorProfileVersion(profile_kind = validated)`
- Existing daily schema exists:
  - `DailyRuleSelection`
  - `DailyRuleSelectionItem`
  - `DailyStrategyInstance`
  - `TradingDayPlan`
  - `Signal`
- Current formal Stage 9 implementation is missing:
  - no formal daily pre-market readiness service/API/UI;
  - no formal `DailyRuleSelection` generation service/API/UI;
  - no formal `DailyStrategyInstance` or `TradingDayPlan` generation service/API/UI.
- Current `/daily/pre-market` delegates to legacy strategy workspace pre-market UI.
- Legacy pre-market UI submits `snapshot-build` and `run-pre-market` jobs and may resolve `config_path`; this cannot be the formal Stage 9 input path.
- `/strategies/pre-market` is compatibility-only and marked for Stage 9 retirement boundary.
- `/run/pre_market`, `run-pre-market` Job, ManagerAgent pre-market service, file reports, legacy strategy library, legacy strategy service, legacy backtest service, live Provider, mutable latest records, `config_path`, Job/Workflow/Pipeline/Artifact/file JSON are not formal Stage 9 sources.

### Frozen Contracts

- `DailyRuleSelection` is daily rule-selection output, not a formal strategy.
- `DailyStrategyInstance` is runtime-only, not `StrategyVersion`.
- `TradingDayPlan` is the user-facing daily plan.
- `StrategyVersion` remains stable and is not rebuilt daily.
- Stage 9 must not modify `StrategyVersion`, published/current strategy pointers, author profiles, rule versions, rule applicability profiles, or proposal status.
- Every daily output must trace to `trade_date`, `strategy_version_id`, `dataset_snapshot_id`, `market_snapshot_id`, current market state / `market_state_id`, rule applicability profile IDs, author profile version IDs, data quality state, and selection reasons.
- Missing data remains `unavailable`, `partial`, `conflict`, `invalid`, `insufficient_coverage`, or `degraded`; never false/zero/success.
- Repair actions may link to existing system-management paths, but Stage 9 does not implement broad Stage 11 automation.
- Daily generation must not call live Providers.

### Final Task Order

1. `RT-S9-001 自动前置检查`
2. `RT-S9-002 每日规则选择`
3. `RT-S9-003 每日策略实例和盘前计划`

`RT-S9-001` and `RT-S9-002` may be implemented in one Stage 9 Task Session only if frozen contracts remain stable and work is done serially. `RT-S9-003` must be implemented later as a separate Task Session. Stage 9 must not be combined with Stage 10.

### Task Card Summary

- `RT-S9-001`：实现正式盘前自动前置检查，覆盖 Kaipan 盘前数据、最新 OHLCV、当前市场状态、当前正式策略、规则适用性、作者验证画像和数据质量；只读 canonical sources；输出 ready/degraded/blocked。
- `RT-S9-002`：基于固定优先级生成 `DailyRuleSelection`，记录启用、降权、暂停规则和 deterministic selection reasons；不得修改正式策略。
- `RT-S9-003`：基于已接受规则选择生成 `DailyStrategyInstance` 和 `TradingDayPlan`；展示今日市场判断、规则、候选标的、信号、入场/失效条件、止盈止损、建议仓位、风险提示和置信度；不得启动盘后归因或提案。

### Validation

Performed:

- Read root and project `AGENTS.md`.
- Read required Stage Bootstrap protocol and constraints.
- Read formal TaskList and Stage 9 requirements.
- Read current implementation log and Stage 8 detailed log.
- Verified Stage 8 Gate and `RT-S8-001/002/003` are accepted.
- Verified Stage 9 plan/log did not exist before Bootstrap.
- Verified current branch, HEAD, clean status and empty diff before documentation edits.
- Mapped current Stage 9-related models, repositories, routes, API, frontend pages and tests.
- Created Stage 9 implementation plan and bounded Task Cards.
- Created Stage 9 log.
- Updated main implementation log to point at Stage 9 Bootstrap.

Tests not run:

- Backend/frontend tests were not run because Bootstrap is documentation-only and no runtime, migration, prompt, API or UI code changed.

### Files Changed

- `docs/refactor-implementation-plans/stage-9-implementation-plan.md`
- `docs/refactor-implementation-logs/stage-9.md`
- `docs/Refactor-Implementation-Log.md`

### Risks

Blocking:

- None at Bootstrap.

Non-blocking:

- Existing `/daily/pre-market` is formal-looking but still delegates to legacy job workspace; Stage 9 must replace or isolate it as formal daily plan UI.
- Current daily canonical tables may need additional explicit traceability fields; if JSON payload cannot safely represent required IDs and states, implementation must escalate before migration/schema changes.
- `DailyRuleSelection.lifecycle_state` lacks explicit degraded/blocked states; implementation may use quality/status payload only if the contract remains testable and user-visible.
- Pre-market `MarketSnapshot.slot` semantics must be explicit so Stage 9 does not consume post-market snapshots.
- Existing broad list repository helpers may need date/slot-specific canonical queries.

### Bootstrap Conclusion

`Bootstrap READY`.

Next executable Task is `RT-S9-001 自动前置检查`, recommended model/session `gpt-5.4` Task Implementation. `RT-S9-001` and `RT-S9-002` may share a later serial implementation session only if frozen contracts remain unchanged. Escalate to `gpt-5.5` if schema/source-of-truth, deterministic selection priority, live Provider avoidance, canonical coverage, strategy mutation boundary, Stage 10 behavior, Stage 11 automation, or second fact source decisions are required.

## 2026-06-21 RT-S9-001 自动前置检查

### Task Decision

`ACCEPTED`

### Scope

本次仅实现正式盘前自动前置检查，不实现：

- `DailyRuleSelection` 生成；
- `DailyStrategyInstance` 生成；
- `TradingDayPlan` 生成；
- `StrategyVersion` 变更；
- `Strategy.current_published_version_id` 变更；
- rule/applicability/author profile/proposal 状态变更；
- Stage 10 盘后行为；
- Stage 11 调度自动化；
- live Provider 调用；
- legacy Job / Workflow / Pipeline / Artifact / file JSON / `config_path` 作为 formal input。

### Delegation

使用 `refactor-orchestrator`。Parent 基于本任务的单一 canonical source-of-truth 约束、紧耦合 UI/API/service 验证链和较小实现面，决定采用 single-controller fallback，选择 `0` 个 subagent。

### Implementation Summary

新增正式 Stage 9 readiness repository / service / API / client / page：

- 后端新增 `PreMarketReadinessRepository`，只读 canonical `Strategy`、`StrategyVersion`、`StrategyRuleMembership`、`DatasetSnapshot`、`MarketSnapshot`、`MarketRegimeRecord`、`RuleApplicabilityProfile`、`AuthorProfileVersion`。
- 后端新增 `PreMarketReadinessService`，对 `trade_date` 执行正式盘前检查，固定 pre-market slot 语义为 `09-25`，输出 `ready / degraded / blocked` 与 `partial / unavailable / error / permission_denied` 对应 UI 状态。
- 新增 `/api/ui/v1/daily/pre-market/readiness` 正式只读接口。
- `/daily/pre-market` 已改为读取正式 readiness 接口，不再以 legacy pre-market job / file report 作为官方结果源。
- 前端页面以业务中文展示：
  - 发生了什么；
  - 影响了什么；
  - 用户可以修复什么；
  - 是否允许降级继续。

### Canonical Checks

实现的自动检查项：

1. `Kaipan 盘前数据`
2. `最新 OHLCV`
3. `当前市场状态`
4. `当前正式策略`
5. `规则适用性`
6. `作者验证画像`
7. `数据质量`

每次 readiness 结果都追踪：

- `trade_date`
- `strategy_version_id`
- `dataset_snapshot_id`
- `market_snapshot_id`
- `market_state_id` 或显式 unavailable
- `rule_applicability_profile_ids`
- `author_method_profile_version_id`
- `author_rule_profile_version_id`
- `author_validated_profile_version_id`
- `data_quality_state`

### Design Decisions

- 不新增 schema，不写入持久化 readiness 记录；当前任务只需要 formal read model，现有 canonical schema 足够表达 immutable references。
- 明确盘前快照 slot 为 `09-25`，避免误用 post-market `MarketSnapshot`。
- 正式策略只从 `Strategy.current_published_version_id` 读取当前发布版本。
- 数据质量不把缺失覆盖为 false/0/成功；缺失保持 `unavailable / degraded / blocked`。
- repair action 仅链接现有业务页面：`/system/data`、`/rules/backtests`、`/strategies`。

### Legacy Isolation Verification

已验证 formal Stage 9 文件未把以下对象作为 formal input：

- legacy pre-market job；
- `snapshot-build` job；
- `Workflow` / `Pipeline` / `Artifact`；
- `config_path`；
- live Provider；
- file JSON report；
- legacy strategy workspace pre-market page。

`/daily/pre-market` 当前正式查询路径为 `getPreMarketReadiness(tradeDate)`，不再委托 legacy pre-market workspace 页面。

### Files Changed

- `api/app.py`
- `api/routers/ui/__init__.py`
- `api/routers/ui/daily_pre_market.py`
- `src/db/repositories/pre_market_readiness_repo.py`
- `src/services/pre_market_readiness_service.py`
- `tests/api/routers/ui/test_daily_pre_market.py`
- `tests/api/test_api_app_factory.py`
- `tests/api/test_ui_openapi_contract.py`
- `tests/unit/services/test_pre_market_readiness_service.py`
- `web/src/components/kit/status-badge.tsx`
- `web/src/lib/api/contract.test.ts`
- `web/src/lib/api/daily.ts`
- `web/src/pages/daily/index.test.tsx`
- `web/src/pages/daily/index.tsx`
- `web/src/pages/daily/pre-market.test.tsx`
- `web/src/types/daily.ts`

### Database Migration

无。

### Verification

已运行：

- `python -m pytest tests/unit/services/test_pre_market_readiness_service.py`
- `python -m pytest tests/api/routers/ui/test_daily_pre_market.py`
- `python -m pytest tests/api/test_ui_openapi_contract.py`
- `python -m pytest tests/api/test_api_app_factory.py`
- `/bin/zsh -lc 'PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm test -- src/pages/daily/pre-market.test.tsx src/pages/daily/index.test.tsx src/lib/api/contract.test.ts'`
- `/bin/zsh -lc 'PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm typecheck'`
- `git diff --check`

结果：

- backend/API tests：`9 passed`
- frontend tests：`10 passed`
- frontend typecheck：passed
- diff hygiene：passed

### Acceptance Notes

本次验收确认：

- `/daily/pre-market` 已显示真实 `ready / degraded / blocked` 正式前置检查状态；
- loading / error / partial / permission_denied / unavailable / degraded / blocked 均有覆盖测试；
- non-ready canonical coverage 不会被显示为 success；
- RT-S9-002 / RT-S9-003 输出未生成；
- Stage 10 未开始；
- 未触发 schema/source-of-truth escalation 条件。

### Residual Risks

- 当前 `TodayOverviewPage` 仍以 compatibility-only job 摘要展示今日总览卡片；它不再是 `/daily/pre-market` 的正式事实源，但 Stage 9 后续仍可考虑收敛总览入口的 daily summary source。
- 尚未运行浏览器级 E2E；当前依赖 focused backend/API/frontend/typecheck 验证。

### Conclusion

`RT-S9-001 ACCEPTED`。

下一推荐任务：`RT-S9-002 每日规则选择`。

## 2026-06-21 RT-S9-002 每日规则选择

### Task Decision

`ACCEPTED`

### Scope

本次仅实现正式 `DailyRuleSelection` 生成、查询和 `/daily/pre-market` 规则选择展示，不实现：

- `DailyStrategyInstance`
- `TradingDayPlan`
- `Signal`
- `StrategyVersion` 变更
- `Strategy.current_published_version_id` 变更
- `RuleVersion` / `RuleApplicabilityProfile` / `AuthorProfileVersion` 生命周期变更
- `StrategyRevisionProposal` / `OptimizationProposal` 状态变更
- Stage 10 盘后行为
- live Provider
- legacy strategy selection artifacts / job / report / `config_path`

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定采用 single-controller fallback，选择 `0` 个 subagent。

原因：

- 当前会话仍无法独立证明 native child spawning 和 child effective permissions；
- RT-S9-002 依赖固定的 canonical source-of-truth 和 deterministic selection priority，Parent 直接实现与复核成本更低；
- 未出现值得并行拆分的非重叠写入面。

### Implementation Summary

新增正式 Stage 9 每日规则选择 repository / service / API / client / UI / tests：

- 后端新增 `DailyRuleSelectionRepository`，只读 `StrategyVersion`、`StrategyRuleMembership`、`MarketRegimeRecord`、`RuleApplicabilityProfile`、`AuthorProfileVersion`，并只写 canonical `DailyRuleSelection` / `DailyRuleSelectionItem`。
- 后端新增 `DailyRuleSelectionService`，先调用已接受的 formal readiness 结果，再按固定优先级生成 `selected / reduced / suspended` 规则决策。
- 新增 `/api/ui/v1/daily/pre-market/rule-selection` 正式只读/按需生成接口。
- 前端 `getDailyRuleSelection(tradeDate)` 接入正式接口。
- `/daily/pre-market` 增加“今日规则选择”区块，展示启用、降权、暂停规则，以及业务中文原因、降级输入和未解决输入。

### Deterministic Selection Contract

本次实现固定使用以下优先级，并把首个改变决策的 tier 记为 `controlling_priority_tier`：

1. `formal_rule_applicability`
2. `current_market_state`
3. `formal_strategy`
4. `data_quality`
5. `author_validated_profile`
6. `author_method_profile`

每条规则决策都记录：

- `rule_version_id`
- `strategy_rule_membership_id`
- `decision`
- `controlling_priority_tier`
- `evidence_ids`
- `quality_states`
- `reason_tiers`
- `reason_list`
- `degraded_inputs`
- `unresolved_inputs`

同一 canonical 输入会生成相同 `input_signature`；若同日同策略版本同市场状态的最新记录签名一致，则直接复用现有 `DailyRuleSelection`，避免产生第二套正式 daily-selection 事实源。

### Traceability And Persistence

`DailyRuleSelection` 持久化到 canonical `daily_rule_selections` / `daily_rule_selection_items`，并在 top-level JSON bucket + item payload 中保留：

- `trade_date`
- `strategy_version_id`
- `dataset_snapshot_id`
- `market_snapshot_id`
- `market_state_id`
- `rule_applicability_profile_ids`
- `author_method_profile_version_id`
- `author_rule_profile_version_id`
- `author_validated_profile_version_id`
- `data_quality_state`
- `readiness_status`
- deterministic `input_signature`
- degraded / unresolved inputs

未新增 schema。当前 frozen contract 下，现有 canonical table + bounded JSON payload 足以安全承载 RT-S9-002 所需 traceability。

### Design Decisions

- readiness `blocked` 时只返回 blocked 结果，不创建成功的 `DailyRuleSelection` 记录。
- 缺失正式规则适用性不会默认变成 selected；缺失时直接 `suspended` 并暴露 `missing_rule_applicability`。
- 规则适用性 `partial / insufficient_sample / insufficient_coverage` 会显式保留为 `reduced` 或 unresolved/degraded reason，不会被压平成成功。
- 当前正式策略只作为 rule pool 和 membership source，不会被重写、发布、回滚或重新绑定。
- RT-S9-003 / Stage 10 对象完全未生成。

### Files Changed

- `api/routers/ui/daily_pre_market.py`
- `src/db/repositories/daily_rule_selection_repo.py`
- `src/services/daily_rule_selection_service.py`
- `tests/api/routers/ui/test_daily_pre_market_rule_selection.py`
- `tests/api/test_ui_openapi_contract.py`
- `tests/unit/services/test_daily_rule_selection_service.py`
- `web/src/lib/api/contract.test.ts`
- `web/src/lib/api/daily.ts`
- `web/src/pages/daily/index.tsx`
- `web/src/pages/daily/pre-market.test.tsx`
- `web/src/types/daily.ts`

### Database Migration

无。

### Verification

已运行：

- `python -m pytest tests/unit/services/test_daily_rule_selection_service.py tests/api/routers/ui/test_daily_pre_market_rule_selection.py tests/api/test_ui_openapi_contract.py`
- `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node /Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/node_modules/vitest/vitest.mjs run src/pages/daily/pre-market.test.tsx src/lib/api/contract.test.ts`
- `/Users/wanghui/.nvm/versions/node/v18.20.8/bin/node /Users/wanghui/.nvm/versions/node/v18.20.8/lib/node_modules/pnpm/bin/pnpm.cjs typecheck`
- `git diff --check`

结果：

- backend/API tests：`4 passed`
- frontend tests：`5 passed`
- frontend typecheck：passed
- diff hygiene：passed

专项确认：

- same canonical inputs 复用同一 `DailyRuleSelection`，决策顺序与 reason tiers 保持一致；
- blocked readiness 不会创建成功 selection；
- missing applicability 不会默认 selected；
- `/api/ui/v1/daily/pre-market/rule-selection` 已纳入 OpenAPI/UI contract；
- 未生成 `DailyStrategyInstance` / `TradingDayPlan` / `Signal`；
- 未修改 `StrategyVersion` 或 current strategy pointer；
- formal selection backend 未接入 legacy job/report/config/live-provider 输入。

### Legacy Isolation Verification

selection backend/API 文件复核未发现以下正式输入：

- legacy pre-market job
- `snapshot-build`
- `config_path`
- live Provider
- legacy strategy service / strategy library
- legacy backtest service
- file JSON report
- compatibility view

补充说明：

- `web/src/pages/daily/index.tsx` 的“今日总览”区块仍保留 RT-S9-001 之前已有的 compatibility-only job 摘要卡片，这不是 RT-S9-002 规则选择的正式事实源。
- 本次新增的 `/daily/pre-market` 规则选择区块只消费 `getDailyRuleSelection(tradeDate)`。

### Residual Risks

- `DailyRuleSelection` 顶层 traceability 目前保存在 canonical JSON payload 中，而不是独立列；在当前 frozen contract 下可接受，但后续若 Stage 9/10 需要更强 SQL-level filtering，可再评估 schema hardening。
- `/daily` 总览页仍展示 compatibility-only job 摘要卡片；不影响 RT-S9-002 正式选择事实源，但后续可继续收敛总览入口。
- 尚未运行浏览器级 E2E；当前依赖 focused backend/API/frontend/typecheck 验证。

### Conclusion

`RT-S9-002 ACCEPTED`。

下一推荐任务：`RT-S9-003 每日策略实例和盘前计划`。

## 2026-06-21 RT-S9-003 每日策略实例和盘前计划

### Task Decision

`ACCEPTED`

### Scope

本次仅实现基于已接受 `DailyRuleSelection` 的正式 `DailyStrategyInstance` / `TradingDayPlan` 生成、审核和 `/daily/pre-market` 计划展示，不实现：

- `StrategyVersion` 重建、发布、回滚或变更；
- `Strategy.current_published_version_id` 变更；
- `RuleVersion` / `RuleApplicabilityProfile` / `AuthorProfileVersion` 生命周期变更；
- `StrategyRevisionProposal` / `OptimizationProposal` 状态变更；
- Stage 10 信号结果评估、盘后归因或提案生成；
- live Provider；
- legacy pre-market job / file report / `config_path` / compatibility job cards 作为 formal input；
- 第二套正式 daily-plan source-of-truth。

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定采用 single-controller fallback，选择 `0` 个 subagent。

原因：

- 当前会话仍无法独立证明 native child spawning、custom child model 与 effective permission 边界；
- RT-S9-003 涉及同一 formal Stage 9 flow 上的 repository/service/API/UI/test 串行落地与复核，拆分 subagent 的收益不足；
- 未出现需要并行写入的独立实现面。

### Implementation Summary

新增正式 Stage 9 daily trading plan repository / service / API / client / UI / tests：

- 后端新增 `DailyTradingPlanRepository`，读取 canonical `DailyRuleSelection`、`StrategyVersion`、`StrategyRuleMembership`、`DatasetSnapshot`、`MarketSnapshot`、`MarketRegimeRecord`、`RuleApplicabilityProfile`、`AuthorProfileVersion`，并只写 canonical `DailyStrategyInstance`、`TradingDayPlan`、`Signal`。
- 后端新增 `DailyTradingPlanService`，仅在 `DailyRuleSelection` 可接受时生成 runtime-only `DailyStrategyInstance` 和 user-facing `TradingDayPlan`，并支持计划 `approved / rejected` 审核流。
- 新增 `/api/ui/v1/daily/pre-market/plan` 正式查询/按需生成接口。
- 新增 `/api/ui/v1/daily/pre-market/plan/review` 正式审核接口。
- 前端 `/daily/pre-market` 增加“每日运行计划”区块，以业务中文展示市场判断、启用/暂停规则、候选标的、信号、入场条件、失效条件、止盈止损、建议仓位、风险提示、置信度与批准/驳回动作，并明确标注“不是正式策略”。

### Runtime Contract

本次实现固定遵守：

- `DailyStrategyInstance` 是 runtime-only，不是 `StrategyVersion`；
- `TradingDayPlan` 是 user-facing daily plan，不是 `StrategyVersion`；
- 计划只能基于已接受 `DailyRuleSelection` 生成；
- selection `blocked / unavailable / degraded-without-planable-output` 时不会静默生成成功计划；
- 计划审核只变更 runtime instance / plan / signal state，不触碰正式策略与画像/规则/提案对象；
- unavailable / degraded / unresolved 输入保持显式可见，不会被压平成 false / 0 / success。

### Traceability And Persistence

`DailyStrategyInstance` / `TradingDayPlan` 均复用 canonical 表，并在 bounded JSON payload 中保留完整 traceability：

- `trade_date`
- `strategy_version_id`
- `daily_rule_selection_id`
- `dataset_snapshot_id`
- `market_snapshot_id`
- `market_state_id`
- `rule_applicability_profile_ids`
- `author_method_profile_version_id`
- `author_rule_profile_version_id`
- `author_validated_profile_version_id`
- `data_quality_state`
- `readiness_status`
- selected / reduced / suspended 决策摘要
- deterministic selection reasons
- degraded / unresolved inputs

当前 frozen Stage 9 contract 下，现有 canonical table + bounded JSON payload 足以安全承载 RT-S9-003 所需 traceability，因此未新增 schema，也未触发 schema hardening escalation。

### Design Decisions

- `DailyRuleSelection` 是生成 `DailyStrategyInstance` / `TradingDayPlan` 的唯一 formal precondition；selection 不可用时直接返回 blocked/unavailable，不生成成功计划。
- 计划信号、候选标的、入场/失效条件、止盈止损、建议仓位与风险提示都从正式策略版本 + 当日规则选择 traceability 派生，不回写正式策略。
- 计划审核状态采用 runtime review flow，明确支持 `approved / rejected`，并同步更新 plan 和 signal review state。
- `/daily/pre-market` 的正式计划区块只消费 formal Stage 9 API，不把 `/daily` 总览里的 compatibility-only job cards 当成计划来源。
- 后端内部仍使用 canonical `MarketRegimeRecord` 模型读取市场状态，但 UI 一律呈现“市场状态”，不暴露 `Regime` 术语。

### Files Changed

- `api/routers/ui/daily_pre_market.py`
- `src/db/repositories/daily_trading_plan_repo.py`
- `src/services/daily_trading_plan_service.py`
- `tests/api/routers/ui/test_daily_pre_market_plan.py`
- `tests/api/test_api_app_factory.py`
- `tests/api/test_ui_openapi_contract.py`
- `tests/unit/services/test_daily_trading_plan_service.py`
- `web/src/lib/api/contract.test.ts`
- `web/src/lib/api/daily.ts`
- `web/src/pages/daily/index.tsx`
- `web/src/pages/daily/pre-market.test.tsx`
- `web/src/types/daily.ts`

### Database Migration

无。

### Verification

已运行：

- `python -m pytest tests/unit/services/test_daily_trading_plan_service.py tests/api/routers/ui/test_daily_pre_market_plan.py tests/api/test_ui_openapi_contract.py tests/api/test_api_app_factory.py -q`
- `/bin/zsh -lc 'PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:/usr/bin:/bin:/usr/sbin:/sbin pnpm test -- src/pages/daily/pre-market.test.tsx src/lib/api/contract.test.ts'`
- `/bin/zsh -lc 'PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:/usr/bin:/bin:/usr/sbin:/sbin pnpm typecheck'`
- `git diff --check`
- `rg -n "run-pre-market|snapshot-build|config_path|ManagerAgent|legacy strategy service|legacy backtest service|Workflow|Pipeline|Artifact|Provider|Regime" src/services/daily_trading_plan_service.py src/db/repositories/daily_trading_plan_repo.py api/routers/ui/daily_pre_market.py web/src/pages/daily/index.tsx`

结果：

- backend/API tests：`9 passed`
- frontend tests：`7 passed`
- frontend typecheck：passed
- diff hygiene：passed
- legacy isolation grep：formal plan service/repository/router 未接入被禁 legacy input；命中仅包括 `web/src/pages/daily/index.tsx` 既有 compatibility-only overview job 卡片和后端内部 `MarketRegimeRecord` 模型引用

专项确认：

- accepted `DailyRuleSelection` 能稳定生成 `DailyStrategyInstance` / `TradingDayPlan`；
- blocked/unavailable selection 不会生成成功计划；
- degraded inputs 会保留在计划 payload 与风险提示中；
- OpenAPI/UI contract 已覆盖正式计划查询和审核接口；
- approval / rejection flow 已覆盖；
- 未生成 Stage 10 结果评估、归因或 proposal；
- 未修改 `StrategyVersion`、current strategy pointer、rule/profile/proposal 状态；
- `/daily/pre-market` 使用正式 Stage 9 flow，未把 `/daily` 总览 compatibility 卡片作为 formal source。

### Residual Risks

- `DailyRuleSelection` 与 `TradingDayPlan` 的顶层 traceability 仍位于 canonical JSON payload，而不是独立列；当前 frozen contract 下可接受，但若后续需要更强 SQL-level filtering，可在后续 hardening 中评估。
- `/daily` 总览页仍保留 compatibility-only job 摘要卡片；本次未把它们纳入 formal Stage 9 flow，但后续仍可继续收敛概览入口。
- 尚未运行浏览器级 E2E；当前依赖 focused backend/API/frontend/typecheck 验证。

### Conclusion

`RT-S9-003 ACCEPTED`。

Stage 9 Gate 不得自动开始；需等待后续明确授权。

## 2026-06-21 Stage 9 Gate

### Gate Decision

`ACCEPTED`

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定委派 2 个 read-only `refactor_explorer_mini`：

- Explorer A：后端 / repository / service / API traceability、determinism、mutation boundary、Stage 10 boundary。
- Explorer B：前端 / UI language / API contract / route wiring / legacy isolation。

Parent 保留最终 Gate 验收、风险分类、修复决策和正式文档更新。两个 subagent 均未修改文件；最终验收未委派。

### Verified Task Status

- `RT-S9-001 自动前置检查`：`ACCEPTED`。
- `RT-S9-002 每日规则选择`：`ACCEPTED`。
- `RT-S9-003 每日策略实例和盘前计划`：`ACCEPTED`。
- `Stage 10`：未开始；本次未实现盘后归因、信号结果评估、post-market review、Rule / Author / Strategy proposal generation。

### Gate Checklist Results

- `/daily/pre-market` 已使用 formal Stage 9 readiness / rule-selection / plan API，不以 legacy pre-market job、`run-pre-market`、`snapshot-build`、ManagerAgent、file report、Job / Workflow / Pipeline / Artifact、`config_path`、live Provider 或 compatibility view 作为正式输入。
- Readiness 覆盖 Kaipan 盘前数据、最新 OHLCV、当前市场状态、当前正式策略、规则适用性、作者验证画像和数据质量。
- 缺失或降级数据保持 `blocked / unavailable / degraded / partial`，不会转换为 success、false、0 或 empty success。
- `DailyRuleSelection` 是每日选择输出，不是 `StrategyVersion`；blocked readiness 不生成成功 selection。
- `DailyStrategyInstance` 和 `TradingDayPlan` 是 runtime/user-facing daily output；blocked / unavailable selection 不生成成功 plan。
- `TradingDayPlan` 展示今日市场判断、启用规则、暂停规则、候选标的、信号、入场条件、失效条件、止盈止损、建议仓位、风险提示、置信度和 approval / rejection state，并明确标注“不是正式策略”。
- `StrategyVersion`、`Strategy.current_published_version_id`、`RuleVersion`、`RuleApplicabilityProfile`、`AuthorProfileVersion`、`StrategyRevisionProposal` / `OptimizationProposal` 状态未被 Stage 9 daily flow 修改。
- Daily 输出 traceability 保留 `trade_date`、`strategy_version_id`、`daily_rule_selection_id`、`dataset_snapshot_id`、`market_snapshot_id`、`market_state_id`、规则适用性画像 ID、作者画像版本 ID、data quality、readiness、selected / reduced / suspended decisions、deterministic reasons、degraded / unresolved inputs。
- UI 已改为业务中文展示，不再在 `/daily/pre-market` 普通用户文案中展示 `DatasetSnapshot`、`MarketSnapshot`、snake_case traceability keys、`Regime` 或英文 selected / reduced / suspended / BUY / SELL / HOLD。

### Bounded Repairs

- 修复 deterministic applicability selection：repository 查询增加稳定 `order_by`，service 按 `reviewed_at / created_at / applicability_profile_id` 选择同 rule/dataset 下的确定性最新画像。
- 修复 latest OHLCV readiness：只选择 `market == "CN"` 且 `dataset_type in ("ohlcv_1d", "ohlcv_daily", "ohlcv_partial")` 的 dataset snapshot，避免误选非 OHLCV snapshot。
- 修复 `/daily/pre-market` 用户语言泄漏：把 raw traceability keys 映射为业务中文；把 `canonical DatasetSnapshot / MarketSnapshot` 文案改为“已冻结的历史行情 / 盘前市场快照”。
- 修复状态文案：`selected / reduced / suspended / BUY / SELL / HOLD / approved / rejected` 映射为中文状态。
- 修复 selection / plan 错误区块：补充“影响”和“处理方式”。
- 清理 `plan/review` router 重复 `ValueError` 分支。

### Files Changed In Gate Repair

- `api/routers/ui/daily_pre_market.py`
- `src/db/repositories/pre_market_readiness_repo.py`
- `src/db/repositories/daily_rule_selection_repo.py`
- `src/services/pre_market_readiness_service.py`
- `src/services/daily_rule_selection_service.py`
- `tests/unit/services/test_pre_market_readiness_service.py`
- `tests/unit/services/test_daily_rule_selection_service.py`
- `web/src/components/kit/status-badge.tsx`
- `web/src/pages/daily/index.tsx`
- `web/src/pages/daily/pre-market.test.tsx`

### Database Migration

无。Stage 9 Gate repair 未新增或修改 schema。

### Verification

已运行：

- `python -m pytest tests/unit/services/test_pre_market_readiness_service.py tests/unit/services/test_daily_rule_selection_service.py tests/unit/services/test_daily_trading_plan_service.py tests/api/routers/ui/test_daily_pre_market.py tests/api/routers/ui/test_daily_pre_market_rule_selection.py tests/api/routers/ui/test_daily_pre_market_plan.py tests/api/test_ui_openapi_contract.py tests/api/test_api_app_factory.py -q`
- `python -m pytest tests/api/routers/ui/test_daily_pre_market.py tests/api/routers/ui/test_daily_pre_market_rule_selection.py tests/api/routers/ui/test_daily_pre_market_plan.py tests/api/test_ui_openapi_contract.py tests/api/test_api_app_factory.py -q`
- `/bin/zsh -lc 'PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm test -- src/pages/daily/pre-market.test.tsx src/pages/daily/index.test.tsx src/lib/api/contract.test.ts'`
- `/bin/zsh -lc 'PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH pnpm typecheck'`
- `rg -n "run-pre-market|snapshot-build|config_path|ManagerAgent|legacy strategy service|legacy backtest service|Workflow|Pipeline|Artifact|Provider|Regime|DatasetSnapshot|MarketSnapshot|daily overview|job_type|listJobs|selected|reduced|suspended|BUY|SELL|HOLD|strategy_version_id|dataset_snapshot_id|market_snapshot_id" ...formal Stage 9 paths...`
- `git diff --check`

结果：

- focused backend/API/service/OpenAPI tests：`18 passed`
- focused API/router/OpenAPI tests after router repair：`9 passed`
- focused frontend /daily/pre-market and contract tests：`12 passed`
- `pnpm typecheck`：passed
- `git diff --check`：passed
- legacy isolation grep：formal Stage 9 service/repository/router/client path 未接入被禁 legacy input；命中项为内部模型/type/test 字段、后端允许的 `MarketRegimeRecord`/`DatasetSnapshot`/`MarketSnapshot` 代码引用、以及已知 `/daily` overview compatibility-only job summary cards。

### Residual Risks And Classification

- `DailyRuleSelection` / `TradingDayPlan` top-level traceability 存在 canonical JSON payload 中，而不是独立列：`non-blocking`。当前 frozen Stage 9 contract 允许 bounded JSON payload；Gate repair 增加了 determinism 和测试，不需要 schema hardening。
- `/daily` overview 仍有 compatibility-only job summary cards：`non-blocking`。这些卡片未作为 `/daily/pre-market` formal source；Stage 9 Gate 只要求 formal pre-market path 隔离 legacy input。
- Browser-level E2E 未运行：`non-blocking`。项目级 AGENTS 允许当前 Stage 以 focused API/frontend/typecheck 验证替代完整浏览器验收；本次已运行 focused page tests 和 typecheck。
- `DailyRuleSelectionRepository.create_selection()` 未加与 daily plan repository 完全一致的 `canonical_write_scope` guard：`non-blocking`。当前写入对象是 Stage 9 canonical daily selection 表，不修改 formal strategy/profile/rule/proposal；可作为后续 hardening。

### Stage 10 Boundary

已确认本次 Stage 9 Gate repair 未新增 Stage 10 table/service/API/UI，未生成 signal result evaluation、post-market attribution、RuleRevisionProposal、AuthorRevisionProposal 或 StrategyRevisionProposal。

### Conclusion

`Stage 9 Gate ACCEPTED`。

下一允许动作：用户明确授权后开始 `Stage 10 Bootstrap`。不得自动开始 Stage 10。
