# Stage 8 策略中心实施日志

## 当前摘要

- Stage：`Stage 8 策略中心`
- 当前活动：`2026-06-20 Stage 8 Bootstrap`
- 当前状态：`Bootstrap READY`
- 当前 Task：无已开始 RT-S8 Task
- 下一可执行项：`RT-S8-001 策略草稿与发布`
- 不得自动开始：不得发布策略；不得启动 `Stage 9 每日盘前`；不得启动 `Stage 10 每日盘后`

## 2026-06-20 Stage 8 Bootstrap

### Bootstrap Decision

`READY`

### Scope

本次只审计当前实现、冻结 Stage 8 策略中心契约、创建 Stage 8 实施计划/日志并更新主实施日志。

未实施：生产代码、数据库迁移、API、前端页面、Prompt 文件、策略发布、每日盘前、每日盘后、E2E、提交或推送。

### Entry Verification

- Stage 7 Gate：`ACCEPTED`。
- Stage 8 Bootstrap 前未开始；未发现既有 Stage 8 plan。
- Branch：`main`。
- HEAD：`f53027faf5d16dbed1735d0fc4aafd6edc17687d`。
- Bootstrap 前 working tree：clean。
- Bootstrap 前完整 diff：empty。
- 用户授权范围：仅准备 Stage 8 implementation plan/log 和 bounded Task Cards。

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定使用两个 bounded read-only Explorer：

- Backend/data Explorer：映射 canonical `StrategyVersion`、`DailyStrategyInstance`、proposal、Stage 6/7 formal facts、legacy strategy paths。
- Frontend/API Explorer：映射 `/strategies`、strategy UI/API/client/tests、legacy wording 和 duplicate entry points。

未使用 Executor，因为 Bootstrap 禁止生产代码实现。

Runtime probe:

- refactor-orchestrator skill 和 mini-agent TOML 均存在。
- Explorer role TOML declares `gpt-5.4-mini` and `read-only`.
- Executor role TOML declares `gpt-5.4-mini` and `workspace-write`.
- Native subagent spawning succeeded.
- Effective child model/effective permissions were not independently verified beyond role config and read-only handoff evidence.

### Verified Facts

- Formal canonical strategy schema already exists in `src/models/stage2_canonical.py`:
  - `Strategy`
  - `StrategyVersion`
  - `StrategyRuleMembership`
  - `DailyRuleSelection`
  - `DailyStrategyInstance`
  - `OptimizationProposal`
- `StrategyVersion` has formal fields for lifecycle, parent, policies, universe, author profile version IDs, evidence, quality, publish actor/time.
- `Strategy` has `business_key` and `current_published_version_id`, but the current pointer is not an explicit FK in ORM.
- `OptimizationProposal` has `ProposalType.strategy_revision`; no dedicated `StrategyRevisionProposal` ORM/service/API exists.
- Formal Stage 6/7 fact sources are available:
  - `DatasetSnapshot`
  - `MarketSnapshot`
  - `BacktestRun`
  - `BacktestResult`
  - `RuleApplicabilityProfile`
  - `AuthorMethodProfile`
  - `AuthorRuleProfile`
  - `AuthorValidatedProfile`
- Current concrete formal Stage 8 write path is missing:
  - no concrete canonical strategy repository implementation;
  - `src/db/repositories/strategy_repo.py` is empty;
  - no formal strategy service/API/UI for draft, validation, publish, rollback, diff, proposal review.
- Current `/strategies` route is a formal-looking shell but still displays compatibility candidate data and says formal strategy versioning is not established.
- Existing strategy-related compatibility paths include `TraderStrategyVersion`, `strategy_library`, legacy strategy service, `strategy-build` jobs, `/api/ui/v1/strategy-studio`, `/api/ui/v1/optimize` backed by `TraderStrategyVersion`, `/strategy_versions`, legacy backtest/result tables, compatibility views, file JSON and `config_path`.

### Frozen Contracts

- Formal strategy source-of-truth is canonical `StrategyVersion` in `strategy_versions`, scoped by canonical `Strategy` in `strategies`.
- Formal strategy rule pool is `StrategyRuleMembership`.
- `StrategyRevisionProposal` is represented by `OptimizationProposal(proposal_type = strategy_revision)` unless implementation escalates before schema changes.
- `TraderStrategyVersion` and all legacy strategy job/file/API paths are compatibility-only and not formal Stage 8 inputs.
- `StrategyVersion` is not regenerated daily.
- `DailyStrategyInstance` is runtime-only and cannot be formal strategy.
- Proposal acceptance may create/link a draft strategy only; it cannot publish or mutate current/published strategy.
- Formal validation consumes only canonical DatasetSnapshot, MarketSnapshot, BacktestRun, BacktestResult, RuleApplicabilityProfile and Stage 7 author profile versions.
- Missing canonical data remains unavailable, partial, conflict, invalid or insufficient_coverage.
- Only one current strategy per strategy scope unless a later explicit contract changes the scope rule.
- Rollback must create/audit a version transition and cannot silently mutate history.

### Final Task Order

1. `RT-S8-001 策略草稿与发布`
2. `RT-S8-002 策略验证和回滚`
3. `RT-S8-003 策略优化建议`

`RT-S8-001` and `RT-S8-002` may be implemented in one Stage 8 Task Session only if frozen contracts remain stable and work is done serially. `RT-S8-003` must be implemented separately.

### Task Card Summary

- `RT-S8-001`: build canonical draft/review/publish foundation on `Strategy`, `StrategyVersion`, `StrategyRuleMembership`; do not use `TraderStrategyVersion` as formal input; show strategy composition to users.
- `RT-S8-002`: add validation, current-vs-candidate comparison, version diff and audited rollback; consume canonical Stage 6/7 facts only; do not mutate published/current history.
- `RT-S8-003`: implement proposal-only StrategyRevisionProposal flow through `OptimizationProposal`; accepted proposals create/link draft only; no direct publication/current mutation.

### Validation

Performed:

- Verified Stage 7 accepted in main log and Stage 7 log.
- Verified Stage 8 plan did not exist before Bootstrap.
- Verified branch, HEAD, clean status and empty diff before documentation edits.
- Read required global, task, constraint, prompt and Stage 7 documents.
- Mapped current Stage 8-related backend/database/API/frontend/test surfaces.
- Created Stage 8 plan and bounded Task Cards.
- Created Stage 8 log.
- Updated main implementation log to point at Stage 8 Bootstrap.

Tests not run:

- Backend/frontend tests were not run because Bootstrap is documentation-only and no runtime, migration, prompt, API or UI code changed.

### Files Changed

- `docs/refactor-implementation-plans/stage-8-implementation-plan.md`
- `docs/refactor-implementation-logs/stage-8.md`
- `docs/Refactor-Implementation-Log.md`

### Risks

Blocking:

- None at Bootstrap.

Non-blocking:

- Formal lifecycle may need explicit strategy-specific states or a tested substate mapping.
- `strategies.current_published_version_id` lacks explicit FK enforcement.
- Formal strategy validation must avoid legacy `backtest_result_runs` while backtest schema remains rule/rule-family centric.
- `/strategies` currently needs replacement from candidate compatibility shell to formal strategy center.
- Existing strategy-related UI still contains Job/Artifact/raw regime wording in daily/candidate surfaces; formal Stage 8 pages must not inherit it.

### Bootstrap Conclusion

`Bootstrap READY`.

Next executable Task is `RT-S8-001 策略草稿与发布`, recommended model/session `gpt-5.4` Task Implementation using the frozen plan, with escalation to `gpt-5.5` if lifecycle, migration, current-use ownership, rollback, proposal boundary or canonical data path needs contract changes.
