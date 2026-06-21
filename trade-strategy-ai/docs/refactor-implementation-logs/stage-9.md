# Stage 9 每日盘前实施日志

## 当前摘要

- Stage：`Stage 9 每日盘前`
- 当前活动：`RT-S9-001 自动前置检查`
- 当前状态：`RT-S9-001 ACCEPTED`
- 当前 Task：`RT-S9-001 自动前置检查`
- 下一可执行项：`RT-S9-002 每日规则选择`
- 不得自动开始：不得生成 `DailyStrategyInstance`、`TradingDayPlan`；不得启动 `Stage 10 每日盘后`

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
