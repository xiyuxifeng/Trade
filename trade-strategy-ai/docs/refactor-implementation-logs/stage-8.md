# Stage 8 策略中心实施日志

## 当前摘要

- Stage：`Stage 8 策略中心`
- 当前活动：`2026-06-21 RT-S8-003 策略优化建议`
- 当前状态：`RT-S8-003 ACCEPTED`
- 当前 Task：`RT-S8-003 策略优化建议`
- 下一可执行项：仅可在用户明确授权后开始 `Stage 8 Gate`
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

## 2026-06-20 RT-S8-001 策略草稿与发布

### Task Status

`ACCEPTED`

### Scope

本次仅实现 RT-S8-001 正式策略草稿/审核/发布基础能力：

- canonical strategy repository；
- canonical strategy center service；
- `/api/ui/v1/strategies` 正式 API；
- `/strategies` 正式策略中心页面与 client/types；
- bounded migration：正式审核字段、当前策略 FK、审计表；
- focused backend / API / frontend / migration tests；
- 实施记录更新。

未实现：

- `RT-S8-002` 策略验证、对比、回滚；
- `RT-S8-003` StrategyRevisionProposal flow；
- Stage 9 / Stage 10；
- 生产策略发布或生产数据写入；
- E2E 浏览器验收。

### Key Decisions

- 正式策略写入只走 `Strategy`、`StrategyVersion`、`StrategyRuleMembership`。
- 当前正式策略指针只通过 `strategies.current_published_version_id` 更新，并增加 FK 约束防止悬挂。
- 草稿、提交审核、发布均写入 `strategy_version_audits`，保留 before/after state、actor、reason、source surface。
- UI 统一回到 `/strategies` 正式策略中心；`/strategies/candidates` 保留兼容提示页，不再作为正式事实源。
- 缺失 canonical 输入不做 legacy 回填；只暴露 canonical rule/profile/policy/snapshot options。
- 发布操作只允许 reviewed/audited transition，不静默覆盖既有 published/current 版本。

### Files Changed

- `src/models/stage2_canonical.py`
- `src/db/repositories/strategy_repo.py`
- `src/services/strategy_center_service.py`
- `src/db/migrations/versions/2026_06_20_0001_stage8_strategy_center_foundation.py`
- `api/app.py`
- `api/routers/ui/__init__.py`
- `api/routers/ui/strategies.py`
- `tests/unit/services/test_strategy_center_service.py`
- `tests/api/routers/test_strategies.py`
- `tests/api/test_api_app_factory.py`
- `tests/api/test_ui_openapi_contract.py`
- `tests/unit/models/test_stage2_canonical_models.py`
- `tests/unit/db/test_migrations.py`
- `web/src/types/strategies.ts`
- `web/src/lib/api/strategies.ts`
- `web/src/lib/api/strategies.test.ts`
- `web/src/pages/strategies/StrategyOverviewPage.tsx`
- `web/src/pages/strategies/index.test.tsx`
- `web/src/pages/product-entry-pages.test.tsx`
- `docs/refactor-implementation-logs/stage-8.md`
- `docs/Refactor-Implementation-Log.md`

### Database Migration

新增 `2026_06_20_0001_stage8_strategy_center_foundation.py`：

- `strategy_versions` 增加 `title`、`summary`、`review_status`、`review_reason`、`reviewed_at`、`reviewed_by`；
- `strategies.current_published_version_id` 增加 FK `fk_strategies_current_version`；
- 新增 `strategy_version_audits` 表及索引；
- downgrade 在存在 reviewed/published strategy data 或 audit data 时拒绝回退。

修复项：

- 初次 PostgreSQL `upgrade head` 暴露 `formal_lifecycle` 枚举事务内使用 `pending_review` 的问题；
- 通过把回填逻辑从 `lifecycle_state = 'pending_review'` 改为 `lifecycle_state = 'in_review' -> review_status = 'pending_review'` 修复；
- 修复后 fresh upgrade、safe re-run、downgrade、re-upgrade 全部通过。

### Verification

Backend / API:

- `python -m pytest tests/unit/services/test_strategy_center_service.py tests/api/routers/test_strategies.py tests/api/test_api_app_factory.py tests/api/test_ui_openapi_contract.py tests/unit/db/test_migrations.py`
  - `18 passed`

Migration unit contract:

- `python -m pytest tests/unit/db/test_migrations.py`
  - `11 passed`

Frontend:

- `pnpm test -- src/lib/api/strategies.test.ts src/pages/strategies/index.test.tsx src/app/route-config.test.tsx src/pages/product-entry-pages.test.tsx`
  - `25 passed`

Frontend type safety:

- `pnpm typecheck`
  - passed

Migration runtime verification on temporary PostgreSQL database `rt_s8_001_migration_0620`:

- fresh `upgrade head` -> passed to `2026_06_20_0001`
- re-`upgrade head` -> passed as no-op
- `current` -> `2026_06_20_0001 (head)`
- `downgrade 2026_06_19_0014` -> passed
- `current` -> `2026_06_19_0014`
- re-`upgrade head` -> passed
- final `current` -> `2026_06_20_0001 (head)`

Static checks:

- `git diff --check`
  - passed

## 2026-06-20 RT-S8-002 策略验证和回滚

### Task Status

`ACCEPTED`

### Scope

本次仅实现 RT-S8-002 正式策略验证、当前版对比、版本 diff 和审计回滚：

- canonical strategy validation read model；
- `/api/ui/v1/strategies/{version_id}/validate|comparison|diff|rollback`；
- canonical BacktestRun / BacktestResult / RuleApplicabilityProfile evidence aggregation；
- `/strategies` 验证面板、当前版对比、版本差异、回退原因确认；
- focused backend / API / frontend / OpenAPI / typecheck 验证；
- Stage 8 / 主实施日志更新。

未实现：

- `RT-S8-003` StrategyRevisionProposal flow；
- Stage 9 每日盘前选择或 `TradingDayPlan`；
- Stage 10 盘后复盘/归因/提案生成；
- legacy `BacktestService`、live Provider、strategy jobs、compatibility view 作为正式验证输入；
- 新 schema migration。

### Key Decisions

- 正式策略验证继续复用 `StrategyVersion.evidence_json`，在其中增加 `validation_summary`，不建立第二套正式策略事实源。
- 策略验证只读取 canonical `DatasetSnapshot`、`MarketSnapshot`、`BacktestRun`、`BacktestResult`、`RuleApplicabilityProfile`、`AuthorProfileVersion`、`StrategyVersion` 和 `StrategyRuleMembership`。
- `validation_summary.state` 统一落到 `not_run / passed / unavailable / partial / invalid / insufficient_coverage / insufficient_sample`，并明确把 `unavailable`、`insufficient_sample`、`insufficient_coverage` 作为非通过状态展示。
- reviewer decision 通过验证摘要的 `reviewer_decision` 暴露；通过时自动记录 `approved`，不足或缺失时保持 `review_required`。
- 当前版对比与版本 diff 使用 canonical strategy service 计算，不引入新的持久化表。
- 回滚只移动 `strategies.current_published_version_id`，并在 `strategy_version_audits` 记录 `rollback_to_current`；不修改、删除或覆盖任何历史 `StrategyVersion` 行。

### Files Changed

- `src/services/strategy_center_service.py`
- `src/db/repositories/strategy_repo.py`
- `api/routers/ui/strategies.py`
- `tests/unit/services/test_strategy_center_service.py`
- `tests/api/routers/test_strategies.py`
- `tests/api/test_ui_openapi_contract.py`
- `web/src/types/strategies.ts`
- `web/src/lib/api/strategies.ts`
- `web/src/lib/api/strategies.test.ts`
- `web/src/pages/strategies/StrategyOverviewPage.tsx`
- `web/src/pages/strategies/index.test.tsx`
- `docs/refactor-implementation-logs/stage-8.md`
- `docs/Refactor-Implementation-Log.md`

### Database Migration

- 无新增 migration。
- 继续复用 `strategy_version_audits` 和 `StrategyVersion.evidence_json`。
- 本 Task 不需要修改 `BacktestRun` / `BacktestResult` 公共 schema，因此未触发 `ESCALATION_REQUIRED`。

### Verification

Backend / API:

- `python -m pytest tests/unit/services/test_strategy_center_service.py tests/api/routers/test_strategies.py`
  - `5 passed`

OpenAPI / app factory:

- `python -m pytest tests/api/test_ui_openapi_contract.py tests/api/test_api_app_factory.py`
  - `4 passed`

Frontend:

- `node web/node_modules/vitest/vitest.mjs run src/lib/api/strategies.test.ts src/pages/strategies/index.test.tsx`
  - `3 passed`

Frontend type safety:

- `node web/node_modules/typescript/bin/tsc --noEmit -p web/tsconfig.json`
  - passed

Static checks:

- `git diff --check`
  - passed

### Acceptance Review

- 验证接口不会调用 legacy `BacktestService`、live Provider 或 legacy backtest tables；所有证据都来自 strategy version 已绑定的 canonical IDs。
- `validation_summary` 能区分 `passed`、`unavailable`、`partial`、`insufficient_coverage` 和 `insufficient_sample`，并在 UI 中直接可见。
- 当前版对比和版本 diff 均基于 canonical `StrategyVersion` 与 `StrategyRuleMembership`，没有引入第二套正式策略 source。
- 回滚后历史 `StrategyVersion` 行数保持不变，只有当前指针变更，并写入 `strategy_version_audits`。
- 同一 `business_key` 仍只保留一个 current pointer。
- Stage 9 / Stage 10 行为仍未开始。

### Residual Risks

- 当前验证摘要使用 `evidence_json.validation_summary`，后续如果策略验证维度继续膨胀，可能需要单独 normalized read relation，但本 Task 下尚不需要。
- 当前 UI 仍以正式策略中心单页承载验证、对比、diff 和回退；若后续版本量显著增长，可能需要独立版本列表或筛选体验增强。
- 本 Task 仍未引入浏览器级 E2E；现阶段依赖 focused API / frontend / OpenAPI / typecheck 证据。

### Task Conclusion

`RT-S8-002 ACCEPTED`。

下一未开始 Task 仍为 `RT-S8-003 策略优化建议`，不得自动开始。

### Legacy Isolation Evidence

Formal RT-S8-001 path files:

- `api/routers/ui/strategies.py`
- `src/services/strategy_center_service.py`
- `src/db/repositories/strategy_repo.py`
- `web/src/lib/api/strategies.ts`
- `web/src/pages/strategies/StrategyOverviewPage.tsx`

对以上文件执行 legacy dependency grep：

- `TraderStrategyVersion`
- `strategy_studio`
- `optimize`
- `SnapshotLoader`
- `config_path`
- `strategy_library`
- live `Provider`
- mutable latest-record wording

结果：`no matches`

结论：RT-S8-001 formal path 不调用 legacy strategy jobs、`TraderStrategyVersion`、live Providers、file JSON、mutable latest records、legacy strategy-studio / optimize write paths。

### Acceptance Summary

- `/strategies` 已从 compatibility candidate shell 改为正式策略中心。
- 用户可查看正式策略当前状态、规则池、基础权重、作者画像版本、风险政策、仓位约束、目标股票范围、市场状态选择政策、降级政策。
- 用户可基于 canonical rule/profile/policy inputs 保存策略草稿。
- 用户可提交审核、发布为当前正式策略。
- 发布链路具备审计与 current pointer traceability。
- 未引入第二正式事实源。

### Residual Risks

- RT-S8-001 仅实现发布基础，不包含 RT-S8-002 的正式 diff / comparison / rollback UI；
- `/strategies/candidates` 仍保留兼容提示页，后续仍需在退役阶段清理；
- 未运行浏览器级 E2E，仅完成 focused frontend tests 与 typecheck；
- 临时数据库 `rt_s8_001_migration_0620` 仍存在于本地 PostgreSQL，后续可清理。

### Conclusion

`RT-S8-001 ACCEPTED`。

Stage 8 仍未完成；下一推荐任务仅在再次授权后开始 `RT-S8-002 策略验证和回滚`。

## 2026-06-21 RT-S8-003 策略优化建议

### Task Status

`ACCEPTED`

### Scope

本次仅实现 RT-S8-003 proposal-only 策略优化建议能力：

- canonical `OptimizationProposal` strategy revision repository / service / API；
- `/strategies` 正式策略中心建议列表、详情、复核动作、生成草稿动作；
- 接受建议时复用 `StrategyCenterService` 草稿创建逻辑；
- proposal lifecycle audit 和 evidence state 透传；
- focused backend / API / OpenAPI / frontend / typecheck 验证；
- Stage 8 / 主实施日志更新。

未实现：

- Stage 8 Gate；
- Stage 9 每日盘前；
- Stage 10 盘后复盘、归因或自动提案生成；
- strategy publish/current pointer 变更；
- dedicated `StrategyRevisionProposal` table；
- legacy `/api/ui/v1/optimize` 或 legacy strategy job 作为正式 proposal 输入。

### Delegation

使用 `refactor-orchestrator`。

- Parent：负责 canonical repository/service/API、契约核对、测试、日志与最终验收。
- `Executor Gamma`：仅处理 `/strategies` proposal list/detail/action 的前端实现与测试草稿。

子代理未接触 migration、策略发布、current pointer 写入或 Stage 9/10 行为。

### Key Decisions

- 正式 `StrategyRevisionProposal` 继续使用 `OptimizationProposal(proposal_type = strategy_revision)` 作为唯一正式 carrier，没有建立第二套 proposal facts。
- proposal evidence 只锚定 canonical `StrategyVersion`、validation summary 和已有 canonical evidence IDs；缺失信息继续暴露为 `unavailable / partial / invalid / insufficient_coverage / insufficient_sample`，不做静默成功降级。
- 建议接受动作只允许“生成草稿”，并且只会创建或链接 `draft` 状态 `StrategyVersion`，同时回写 `accepted_draft_version_id`。
- proposal acceptance 通过 lifecycle validator 从 `in_review -> accepted`，不会发布策略，不会修改 `strategies.current_published_version_id`，不会覆盖任何 published/current `StrategyVersion` 行。
- UI 文案明确区分“建议 -> 草稿 -> 审核 -> 发布 -> 当前使用”，避免把建议接受误写成发布。

### Files Changed

- `src/db/repositories/strategy_repo.py`
- `src/services/strategy_center_service.py`
- `api/routers/ui/strategies.py`
- `tests/unit/services/test_strategy_center_service.py`
- `tests/api/routers/test_strategies.py`
- `tests/api/test_ui_openapi_contract.py`
- `web/src/types/strategies.ts`
- `web/src/lib/api/strategies.ts`
- `web/src/lib/api/strategies.test.ts`
- `web/src/pages/strategies/StrategyOverviewPage.tsx`
- `web/src/pages/strategies/index.test.tsx`
- `web/src/pages/product-entry-pages.test.tsx`
- `docs/refactor-implementation-logs/stage-8.md`
- `docs/Refactor-Implementation-Log.md`

### Database Migration

- 无新增 migration。
- 继续复用既有 canonical `OptimizationProposal.accepted_draft_version_id` 追踪建议接受后的草稿版本。
- 本 Task 未修改 `StrategyVersion` published/current contract，也未触发 destructive rewrite。

### Verification

Backend / API / OpenAPI:

- `python -m pytest tests/unit/services/test_strategy_center_service.py tests/api/routers/test_strategies.py tests/api/test_ui_openapi_contract.py`
  - `8 passed`

Frontend:

- `pnpm test -- src/lib/api/strategies.test.ts src/pages/strategies/index.test.tsx src/pages/product-entry-pages.test.tsx`
  - `15 passed`

Frontend type safety:

- `pnpm typecheck`
  - passed

Static checks:

- `git diff --check`
  - passed

### Acceptance Review

- proposal list/detail/create/review/accept-to-draft 均走 canonical strategy center API，不依赖 legacy `/api/ui/v1/optimize`、legacy strategy jobs、legacy `BacktestService`、live Provider、file JSON 或 mutable latest records。
- proposal 详情可查看状态、受影响策略版本、理由、置信度、建议变更、证据状态、partial reasons 与 limitations。
- `reject / archive / supersede` 生命周期由 formal review API 支持并保留 traceability；accepted proposal 会记录 `accepted_draft_version_id`。
- 接受建议后只会生成或链接 `draft StrategyVersion`；不会发布草稿，不会变更 `strategies.current_published_version_id`，不会修改当前 published `StrategyVersion` 行。
- `/strategies` 页面按钮使用“生成草稿”而不是“发布策略”，并明确把建议流和正式发布流拆开。
- Stage 9 / Stage 10 行为仍未开始。

### Residual Risks

- 当前 `/strategies` proposal action 按钮仍是固定暴露，主要依赖后端生命周期校验拒绝非法动作；后续可补充基于 `available_actions` 的前端禁用态细化。
- 本 Task 未增加浏览器级 E2E；当前依赖 focused API / frontend / OpenAPI / typecheck 证据。
- `/strategies/candidates` compatibility notice page 仍未退役，但未作为 formal proposal input。

### Task Conclusion

`RT-S8-003 ACCEPTED`。

Stage 8 仍未完成。下一步仅可在用户明确授权后开始 `Stage 8 Gate`，不得自动开始。
