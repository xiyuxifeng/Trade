# Stage 12 旧入口退役与最终交付实施日志

## Current Snapshot

- Stage：`Stage 12 旧入口退役与最终交付`
- 当前活动：`Stage 12 Gate`
- 当前状态：`RT-S12-001 ACCEPTED`；`RT-S12-002 RT_S12_002_BROWSER_E2E_ACCEPTED`；`RT-S12-003 RT_S12_003_USER_DOCS_ACCEPTED`；`Stage 12 Gate STAGE_12_GATE_ACCEPTED`；`Post-delivery Task 2 Job Management formalization ACCEPTED`
- 当前 Task：Stage 12 Gate fresh rerun 已完成；当前设备环境重新验证通过，DB current/head 一致，Browser E2E 通过。
- 下一可执行项：无。Stage 12 已完成；不得自动开始任何新 Stage 或后续重构任务。
- 不得自动开始：不得自动开始任何新 Stage 或后续重构任务。

## 2026-07-04 Post-delivery Task 2 Job Management formalization

### Status

`ACCEPTED`

### Scope

- 执行 `docs/system-jobs-runs-page-cleanup-plan.md` Task 2。
- 不重做 `/system/runs`。
- 不改变 Job 数据库 schema。
- 不新增普通用户原始 JSON 创建路径。

### Implementation

- `web/src/app/route-config.tsx`
  - 新增正式 `/system/jobs`、`/system/jobs/new`、`/system/jobs/:jobId`。
  - `/jobs` 兼容重定向到 `/system/jobs`。
  - `/jobs/:jobId` 兼容重定向到 `/system/jobs/:jobId`。
- `web/src/pages/jobs/*`
  - `JobListPage` 作为正式任务管理页，显示筛选、分页、状态计数、进度、刷新/自动刷新和按定义启用的控制动作。
  - `JobDetailPage` 改为正式系统任务详情，返回 `/system/jobs`，默认收敛 raw 参数，失败任务只在支持 retry 时显示重试。
  - 新增 `JobNewPage`，操作员/管理员可按注册定义创建高级任务，高风险任务需要确认。
- `web/src/components/jobs/JobTable.tsx`
  - 默认显示短任务编号和用户可读任务类型标题，减少 raw UUID / raw `job_type` 主导。
- `web/src/pages/system/SystemHubPage.tsx`
  - 系统管理增加“任务管理”入口；“任务运行”指向 `/system/jobs`，“失败与告警”继续指向 `/system/runs`。
- `src/services/job_registry.py`
  - 修复 `system-data-operation` 定义中 `can_resume=true` 但 `can_pause=false` 的不一致。
- `src/services/job_service.py`
  - 进度写入统一边界化 `current`、`total`、`percent`、`remaining` 和 sub-progress。
  - `pause`、`resume`、`cancel`、`retry` 在 service 层按 JobDefinition 支持标记拒绝不支持动作。
  - 手动 retry 遵守 retry limit。
- `api/routers/ui/jobs.py`
  - `/validate` 使用 `confirmed`，保证高风险任务在确认后可被同一校验路径接受。
- Business page links
  - 任务创建后的用户可见链接改向 `/system/jobs` 或 `/system/jobs/:jobId`。
- Docs
  - `docs/system-jobs-runs-page-cleanup-plan.md` 记录 Task 2 路由所有权、bug inventory、生命周期语义和全 job type coverage matrix。
  - `docs/Refactor-Migration-Matrix.md` 更新 `/jobs` 迁移目标。
  - `docs/stage-12-user-docs/Admin-Operations-Guide.md` 增加“任务管理”管理员说明。

### Lifecycle evidence

- Backend RED tests first failed for unbounded progress and unsupported pause being accepted.
- Green fix adds service-level guards and progress normalization.
- Worker-backed lifecycle evidence is covered by `tests/unit/services/test_job_runner.py`:
  - running job pause at checkpoint.
  - running job cancel at checkpoint.
  - resume after pause.
  - retry path for failed supported jobs.
  - backtest/rule-pool progress writes.
- Heavy or provider-dependent job types are covered by registry/contract tests and documented as not fully live-executed in this task.

### Verification

- `python -m pytest tests/unit/services/test_job_service.py::test_update_job_progress_bounds_percent_and_remaining tests/unit/services/test_job_service.py::test_job_controls_reject_unsupported_actions_and_retry_limits -q`
  - result: `2 passed`
- `python -m pytest tests/unit/services/test_job_registry.py::test_every_job_definition_has_lifecycle_contract_metadata -q`
  - result: `1 passed`
- `cd web && pnpm test -- src/pages/jobs/index.test.tsx src/app/route-config.test.tsx src/components/jobs/JobProgress.test.tsx`
  - result: `23 passed`
- `python -m pytest tests/unit/services/test_job_registry.py tests/unit/services/test_job_service.py tests/unit/services/test_job_runner.py tests/api/routers/test_jobs.py tests/api/routers/test_jobs_api.py -q`
  - result: `80 passed`
- `cd web && pnpm typecheck`
  - result: passed
- `python -m py_compile api/routers/ui/jobs.py src/services/job_registry.py src/services/job_service.py src/services/job_runner.py`
  - result: passed
- Legacy direct `/jobs` link scan under `web/src/pages`, `web/src/features`, and `web/src/components`
  - result: no direct legacy links found outside compatibility route tests/routes
- `git diff --check`
  - result: passed
- Note: an earlier focused backend aggregate attempt hit one SQLite `database is locked` in `test_submit_backtest_jobs_write_progress_to_job_record`; isolated rerun passed and the final aggregate rerun passed.

### Residual risks

- Full live execution for every heavy/external-provider job type is intentionally not run; contract-level coverage and registry matrix document the reason.
- Some legacy/internal compatibility pages still contain internal terminology; normal business links now target formal `/system/jobs` paths, but broader legacy retirement remains outside Task 2.

### Acceptance

`ACCEPTED`. Task 2 scope is complete: `/system/jobs` is the formal Job Management entry, `/jobs` compatibility routes point to `/system/jobs`, `/system/runs` was not redesigned, lifecycle/progress/control bugs found during audit were fixed or documented as non-blocking, and every registered job type is covered in the matrix.

## 2026-07-01 Post-delivery shell layout foundation

### Status

`ACCEPTED`

### Scope

- 只实现 `docs/system-jobs-runs-page-cleanup-plan.md` Task 1 的页面壳层布局能力；
- 不实现 `/system/jobs`；
- 不重做 `/system/runs` 信息架构；
- 不改动 route/governance/schema/data-source contract；
- 不改变未迁移页面的默认 workflow shell。

### Implementation

- `web/src/components/layout/business-page-shell.tsx`
  - 新增 `layoutMode` 与显式 section visibility contract。
  - 默认 layout 仍为 `workflow`，保证旧页面不迁移时继续显示 `Input / Processing Status / Output`。
  - 当页面隐藏 `Processing Status` 时，将 truthful availability panel 内联到 `页面用途`，继续显示 `发生了什么 / 影响什么 / 应该怎么处理`。
- `web/src/components/layout/product-page-adapter.tsx`
  - 透传 `layoutMode` 与 section visibility props，保持旧调用点兼容。
- 保守迁移页面：
  - `/research/add` 明确固定为 `workflow`，作为兼容迁移示例。
  - `/authors` 切换为 `library`。
  - `/system/status` 切换为 `overview`。
  - `/system/configuration` 切换为 `management`。
- `docs/system-jobs-runs-page-cleanup-plan.md`
  - 补充页面布局矩阵、迁移状态和 deferred 页面说明。
- frontend tests
  - 更新 layout/page-state tests，去掉“所有正式页面都必须渲染 Input / Processing Status / Output”这一旧假设。
  - Gate review 恢复 `/research/results` 当前 article-analysis 审核动作回归测试，确保页面壳层调整没有降低既有业务动作覆盖。

### Verification

- `cd web && PATH=${NODE18_BIN}:$PATH pnpm test -- src/components/layout/business-page-shell.test.tsx src/components/layout/product-page-adapter.test.tsx src/pages/product-page-state-matrix.test.tsx src/pages/authors/index.test.tsx src/app/route-config.test.tsx src/pages/system/index.test.tsx src/pages/research/index.test.tsx`
  - 结果：`78 passed`
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm typecheck`
  - 结果：pass
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm lint`
  - 结果：pass
- `git diff --check`
  - 结果：pass

### Residual Risks

- 页面矩阵中 `deferred` 的非 workflow 页面仍保留旧 shell，后续逐页迁移时需要同步更新测试矩阵。
- 本次未变更 `/system/runs`，因此其更细的 `detail` 信息架构仍留待后续 bounded task。

### Decision

`ACCEPTED`

## 2026-06-30 Stage 12 Gate Fresh Rerun

### Status

`STAGE_12_GATE_ACCEPTED`

### Scope

- 重新执行 Stage 12 final Gate review、required verification 和 bounded fix loop。
- 本次不假设上一轮 blocker 仍然存在；从当前设备环境重新验证。
- 不改变 route/schema/governance/data-source/lifecycle/prompt/product contract。
- 无 production code 改动。
- 详细记录：[Stage 12 Gate](stage-12-gate.md)。

### Gate Review Result

- `RT-S12-001`: review pass；retired ordinary-user legacy routes remain redirect-only compatibility entries in the single route registry. Primary navigation exposes only formal product entries and allowed System Management entries.
- `RT-S12-002`: review pass；fresh Browser E2E passed through the formal product journey, and accepted RT-S12-002 final evidence remains separate from reference-chain records.
- `RT-S12-003`: review pass；formal user/admin/deployment docs remain under `docs/stage-12-user-docs/` and indexed from `docs/README.md`; delivered docs terminology/safety/link checks passed.
- Global contract: no second route/schema/governance/data-source/documentation source of truth found in the reviewed Stage 12 state; truthful missing/partial/unavailable/degraded/invalid/conflict handling remains documented and covered by focused UI tests.

### Prior Residual Reclassification

- Prior local DB current/head blocker is resolved in this environment: `current=2026_06_20_0001 (head)`, `head=2026_06_20_0001 (head)`.
- Prior E2E authentication blocker is resolved in this environment: `env-check` reports `ADMIN_API_KEY` set with redacted output, and fresh Browser E2E passed.
- Prior Playwright harness fix remains accepted and unchanged; runtime cache files are not committed.

### Review and bounded fix loop

- Loop 1: reclassified prior DB blocker by rerunning `db-check`, `alembic current`, and `alembic heads`; no fix needed.
- Loop 2: corrected an invalid focused backend test path by using current files from `rg --files`; reran corrected focused backend/API/service aggregate.
- Loop 3: corrected a docs safety grep regex; reran safety grep, markdown link validation, and route/docs consistency check.
- Loop 4: reclassified prior E2E authentication blocker by rerunning fresh Browser E2E; no fix needed.

### Verification

- `python -m scripts.web_local env-check`: pass, redacted output only; `DATABASE_URL` and `ADMIN_API_KEY` set from `.env`.
- `python -m cli.main db-check --config config/app.template.yaml`: pass, `DB OK: 1`.
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, `2026_06_20_0001 (head)`.
- `python -m alembic -c src/db/migrations/alembic.ini heads`: pass, `2026_06_20_0001 (head)`.
- Focused Stage 12 backend/API/service aggregate: pass, `82 passed`, warnings only.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm typecheck`: pass.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm test -- src/app/route-config.test.tsx`: pass, `12 passed`.
- Focused route/navigation/state frontend aggregate: pass, `43 passed`.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm build`: pass; includes typecheck, lint, and Vite build.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm e2e`: pass, `1 passed`.
- Delivered-doc terminology grep: no matches.
- Delivered-doc safety grep: no matches.
- Markdown link validation: pass, `markdown links ok`.
- Route/docs consistency check: pass, `route/docs consistency ok`.

### Unrun or partial verification

- Full backend suite was not run because Gate did not change backend source and the affected Stage 12 formal API/service path was covered by the focused aggregate plus fresh Browser E2E.
- Full frontend suite was not run because Gate did not change frontend source in this rerun and the affected route/navigation/state/E2E surface was covered by focused tests, build, and fresh Browser E2E.
- Prompt regression suite was not run because Gate did not modify prompts, prompt loader code, or schema contracts; replacement evidence is unchanged prompt artifacts plus RT-S12-002 recorded prompt/schema evidence.

### Decision

`STAGE_12_GATE_ACCEPTED`

Stage 12 is complete. Do not automatically start any new Stage or additional refactor work.

## 2026-06-30 Stage 12 Gate

### Status

`STAGE_12_GATE_BLOCKED`

### Scope

- 执行 Stage 12 final Gate review、required verification 和 bounded fix loop。
- 不改变 route/schema/governance/data-source/lifecycle/prompt/product contract。
- 仅修复 Playwright E2E harness 的 localhost proxy 敏感问题：`web/playwright.config.ts` 现在将 `127.0.0.1`、`localhost`、`::1` 加入 `NO_PROXY` / `no_proxy`。
- 详细记录：[Stage 12 Gate](stage-12-gate.md)。

### Gate Review Result

- `RT-S12-001`: review pass；retired ordinary-user legacy routes remain redirect-only in the single route registry; primary navigation exposes only formal product entries and allowed System Management entries.
- `RT-S12-002`: accepted evidence remains valid in `rt-s12-002-browser-e2e.md`; reference-chain records remain excluded from final pass evidence. Fresh Gate E2E rerun is blocked by current environment authentication.
- `RT-S12-003`: review pass；formal user/admin/deployment docs remain under `docs/stage-12-user-docs/` and indexed from `docs/README.md`; delivered docs terminology/safety/link checks passed.
- Global contract: no second route/schema/governance/data-source/documentation source of truth found in the reviewed Stage 12 Gate diff; truthful missing/partial/unavailable/degraded/invalid/conflict handling remains documented.

### Blocking Findings

- Local DB current/head mismatch remains: `current=2026_06_14_0006`, `head=2026_06_20_0001`.
- Bounded migration attempt failed because the configured DB user is not owner of `ohlcv_bars`; Alembic current stayed at `2026_06_14_0006`.
- Fresh `pnpm e2e` reaches the browser test after harness repair but remains on the login page because `ADMIN_API_KEY` is unset in the current environment.

### Bounded Fixes

- Restored local `@playwright/test 1.61.1` from lockfile so `pnpm e2e` uses the Node Playwright test runner instead of an unrelated Playwright CLI on PATH.
- Installed matching Playwright Chromium runtime into local cache; no runtime files were committed.
- Added localhost no-proxy protection to `web/playwright.config.ts`.

### Verification

- `python -m scripts.web_local env-check`: pass, redacted output only; `ADMIN_API_KEY` / `DATABASE_URL` unset in this shell.
- `python -m cli.main db-check --config config/app.template.yaml`: pass, `DB OK: 1`.
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, `2026_06_14_0006`.
- `python -m alembic -c src/db/migrations/alembic.ini heads`: pass, `2026_06_20_0001 (head)`.
- `python -m cli.main db-migrate --config config/app.template.yaml`: failed with insufficient table owner privilege on `ohlcv_bars`.
- Focused backend/API/service aggregate: pass, `69 passed`.
- `cd web && pnpm typecheck`: pass.
- `cd web && pnpm test -- src/app/route-config.test.tsx`: pass, `12 passed`.
- `cd web && pnpm build`: pass.
- `cd web && pnpm e2e`: failed after harness repair at authentication/login-page precondition.
- Delivered docs terminology grep: no matches.
- Delivered docs safety grep: no matches.
- Markdown link validation: pass.

### Decision

`STAGE_12_GATE_BLOCKED`

Stage 12 is not finally accepted. Minimum repair is to provide a DB migration role/owner that can advance the local database to head and provide a valid admin API key through the approved local environment mechanism, then rerun Stage 12 Gate verification and Browser E2E.

## 2026-06-30 RT-S12-003 用户文档

### Status

`RT_S12_003_USER_DOCS_ACCEPTED`

### Scope

- Documentation-only delivery for Stage 12 final user/admin/deployment handoff.
- No production code, frontend route, backend API, database migration, browser E2E data generation, live provider refresh, article recrawl, broad backfill, or LLM run was started.
- Formal documents were placed under `docs/stage-12-user-docs/` and indexed from `docs/stage-12-user-docs/README.md` plus `docs/README.md`.
- Documentation was checked against `web/src/app/route-config.tsx` and RT-S12-002 final E2E route sequence:
  `/research/add` → `/research/articles` → `/research/results` → `/rules/review` → `/rules/backtests` → `/rules/results` → `/authors` → `/strategies` → `/daily/pre-market` → `/daily/after-close`.

### Documents delivered

- `docs/stage-12-user-docs/README.md`: formal documentation entry for ordinary users, administrators, and deployers.
- `docs/stage-12-user-docs/Quick-Start.md`: ordinary-user quick start for article import through daily plan/review.
- `docs/stage-12-user-docs/User-Manual.md`: complete ordinary-user manual for formal navigation and product pages.
- `docs/stage-12-user-docs/First-Time-Initialization.md`: administrator first-time initialization guide.
- `docs/stage-12-user-docs/Daily-Pre-Market-Guide.md`: ordinary-user daily pre-market guide.
- `docs/stage-12-user-docs/Daily-After-Close-Guide.md`: ordinary-user post-close review guide.
- `docs/stage-12-user-docs/Data-Failure-Handling.md`: ordinary-user missing/partial/unavailable/degraded/invalid/conflict handling guide.
- `docs/stage-12-user-docs/Admin-Operations-Guide.md`: administrator operations guide for diagnostics, migration, backup, recovery, scheduling, permissions, audit, and failure handling.
- `docs/stage-12-user-docs/Deployment-Runbook.md`: deployer/admin deployment and runtime runbook.
- `docs/README.md`: formal docs index updated.

### Review and bounded fix loop

- Loop 1:
  - Finding: existing formal `docs/` lacked a Stage 12 current user/admin/deployment handoff; prior user/deployment docs under `bak/` and `Deprecated/` were old-route materials.
  - Fix: added the new formal docs listed above and kept old materials untouched as historical documents.
  - Rerun: terminology grep, safety grep, link validation, route/source review.
- Loop 2:
  - Finding: formal docs index needed to expose the new Stage 12 handoff without creating a second TaskList, route source, schema source, governance source, or architecture source.
  - Fix: updated `docs/README.md` and kept `docs/stage-12-user-docs/README.md` as a documentation entry only.
  - Rerun: terminology grep, safety grep, markdown link validation, route-config test, deployment command verification.

### Verification

- `git diff --check`: pass.
- Formal docs terminology grep for `Job|Workflow|Pipeline|Artifact|Provider|Schema|config_path|prompt_run_id|run_id`: no matches in the delivered docs and updated docs index.
- Formal docs safety grep for required sensitive/local-path terms: no matches in the delivered docs and updated docs index.
- Markdown link validation for delivered docs and updated docs index: pass, `markdown links ok`.
- `python -m scripts.web_local env-check`: pass; output was redacted. It reported only `DASHSCOPE_API_KEY` set in the current shell and did not print sensitive values.
- `python -m cli.main db-check --config config/app.template.yaml`: pass after approved elevated rerun; sandboxed run was blocked by socket permissions.
- `python -m alembic -c src/db/migrations/alembic.ini current`: command reachable after approved elevated rerun; current DB reported `2026_06_14_0006`.
- `python -m alembic -c src/db/migrations/alembic.ini heads`: pass; migration head is `2026_06_20_0001`.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm test -- src/app/route-config.test.tsx`: pass, `12 passed`.

### Unrun or partial verification

- Full browser E2E was not rerun because RT-S12-003 is documentation-only and must not start new E2E data generation; RT-S12-002 final E2E evidence is reused as route/product-path source.
- Web build/typecheck were not rerun because no frontend source changed; route-config test was rerun because the docs describe final routes.
- Backend full test suite was not rerun because no backend source changed.
- Current local database is not at migration head (`current=2026_06_14_0006`, `head=2026_06_20_0001`); this is recorded as a deployment/environment residual risk, not as a documentation content blocker.

### Decision

`RT_S12_003_USER_DOCS_ACCEPTED`

Next allowed item is `Stage 12 Gate`, only after explicit user authorization.

## 2026-06-30 RT-S12-003 Documentation Folder Consolidation

### Status

`RT_S12_003_USER_DOCS_ACCEPTED` remains unchanged.

### Scope

- Moved RT-S12-003 user/admin/deployment documents into `docs/stage-12-user-docs/`.
- Updated `docs/README.md`, `docs/Refactor-Implementation-Log.md`, and this Stage 12 log to reference the consolidated folder.
- No content contract, route, UI, API, database, runtime, Browser E2E, live provider, broad backfill, or LLM work was started.

### Verification

- Markdown link validation rerun after the move.
- Terminology and safety greps rerun against the consolidated folder.
- `git diff --check` rerun.

## 2026-06-29 RT-S12-002 Browser E2E Acceptance

### Status

`RT_S12_002_BROWSER_E2E_ACCEPTED`

### Scope

- Browser E2E used formal UI routes and formal UI/API endpoints.
- Reference-chain records remained setup/comparison evidence only and were not counted as final pass evidence.
- No `RT-S12-003`, user documentation generation, Stage 12 Gate, broad live provider refresh, article recrawl, broad market backfill, or LLM execution was started.
- Detailed evidence log: [RT-S12-002 Browser E2E Acceptance](rt-s12-002-browser-e2e.md).

### Final E2E evidence

- Run id: `rt-s12-002-e2e-1782743876308`
- ArticleRevision: `b64a3c51-bf32-562c-8a86-849eac28ad72`
- Prompt/schema version: `article_analysis_v1` / `article_analysis_v1`
- RuleVersion: `8d15ae78-4abb-40ef-9a6e-184bb7289d0c`
- BacktestRun: `f6a90723-3d8c-472b-b057-cc58238974b8`
- BacktestResult: `3fd98591-c9b4-4959-b1e5-598f9db979d7`
- DatasetSnapshot: `b534d59d-851a-4a78-a32d-af6e71a4e71f`
- MarketSnapshots: `88aa0f65-0fb8-41fb-aee8-cb8bbdb33a6f`, `9646ace9-a755-485d-89f4-4900602bde30`
- MarketStates: `a8c2d82f-8db9-41ad-aec7-4c79f42c701f`, `f9084b48-020a-4493-84a0-f2994e7dbccf`
- RuleApplicabilityProfile stable id: `d4e78900-7326-42a1-b28e-1f83583ee358`
- RuleApplicabilityProfile row id: `54f553dd-9f79-4fdd-9067-128e3fa67671`
- AuthorProfileVersion IDs: method `878294da-85b8-46b1-ada7-a66287468526`, rule `99b44c67-77f5-40b4-99c9-5fa17b88dad8`, validated `04327d22-1c64-4604-9477-8ef9786b9162`
- StrategyVersion: `b0ef4ad1-3753-4115-966a-4e816a591f42`
- Strategy validation state: `passed`
- Current published strategy pointer: `b0ef4ad1-3753-4115-966a-4e816a591f42`
- DailyRuleSelection: `65e08166-a346-4b3e-bed7-96cfe156c078`
- DailyStrategyInstance: `539023df-cfba-484f-9fe7-be7a8723e5ef`
- TradingDayPlan: `66b87fa8-f3a8-454f-8e06-c1dbd6b71ee2`
- PostMarketReview: `afc638fa-fb22-4d11-96df-38ebe5949aac`
- OptimizationProposal IDs: `2b675c91-3014-471b-97e5-24609e0d0b38`, `a005dd39-78fe-4dac-bec2-947b2c3ad19c`, `1420a163-7625-4066-977f-14c2998cdd0a`

### Bounded fixes completed

- Added a formal Playwright E2E test for the Stage 12 product journey.
- Exposed formal RuleApplicability publish API through `/api/ui/v1/rules/backtests/applicability-profiles/{profile_id}/publish`.
- Made formal RuleApplicability draft generation idempotent for the same run/result evidence and compatible with the existing unique stable-id contract.
- Exposed RuleApplicability lifecycle state in API evidence.
- Corrected E2E strategy evidence binding to stable `applicability_profile_id` and formal plural backtest evidence fields.
- Enforced a single current formal strategy pointer during strategy publish so pre-market readiness reads one source of truth.
- Installed Playwright Chromium runtime for this authorized Browser E2E task; runtime cache files were not committed.

### Verification

- `python -m scripts.web_local env-check`: pass.
- `python -m cli.main db-check --config config/app.template.yaml`: pass.
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, current/head `2026_06_20_0001`.
- Focused backend/API/service tests: pass during the review/fix loop.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm typecheck`: pass.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm test -- src/app/route-config.test.tsx`: pass, `12 passed`.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm e2e`: pass, `1 passed`.
- `git diff --check`: pass.
- Changed-files secret scan: pass.

### Decision

`RT_S12_002_BROWSER_E2E_ACCEPTED`

Next allowed item is `RT-S12-003 用户文档`, only after explicit user authorization. Stage 12 Gate remains not started.

## 2026-06-29 RT-S12-002 Reference Chain Completion Repair

### Status

`READY_FOR_RT_S12_002_IMPLEMENTATION`

### Scope

- Bounded reference-chain repair only.
- No final `RT-S12-002` Browser E2E Acceptance was started.
- No `RT-S12-003` user documentation, Stage 12 Gate, broad live provider refresh, article recrawl, LLM run, or broad market backfill was started.
- Reference-chain records are pre-E2E smoke/contract evidence only. Browser E2E must still generate or lifecycle-transition a separate final E2E chain and record new object IDs or new audit/lifecycle transitions.

### Repairs completed

- `StrategyCenterService` validation now reads real `BacktestResult.coverage_json` nested sample coverage and result execution state instead of requiring flat fields that current formal backtest results do not write.
- Level-1 validation reports `out_of_sample_state=not_required` when market-state coverage is explicitly not required, instead of treating it as unavailable.
- `BacktestRunRepository.find_dataset_snapshot` now rejects future dataset snapshots for a requested backtest end date, preventing point-in-time leakage.
- Pre-market readiness now accepts global level-1 applicability profiles without market snapshot bindings while still requiring snapshot matches for snapshot-bound profiles.
- Post-close actual availability checks now normalize naive database timestamps as Asia/Shanghai timestamps before comparing with cutoff times.

### Strategy validation and publish evidence

- Strategy: `15416124-5087-4cbc-998b-ca107423c74b`
- StrategyVersion: `6bbaf1a0-0b97-4254-a9b2-b7d696260849`
- `current_published_version_id`: `6bbaf1a0-0b97-4254-a9b2-b7d696260849`
- Validation state: `passed`
- `out_of_sample_state`: `not_required`
- `sample_coverage.state`: `sufficient`
- `sample_count`: `40`
- Evidence source:
  - BacktestRun `ec58660b-7a34-46e3-8744-b2cec0436655`
  - BacktestResult `46f17a5c-5895-427f-8b6b-19d309aeafac`
  - result nested coverage sample count `40`, sample state `ready`, level-1 market-state coverage `not_required`
- Audit/lifecycle evidence:
  - existing `created_draft`
  - prior `validated`
  - new `submitted_for_review`
  - new `validated`
  - new `published`

### Reference chain evidence

- New pre-market dataset-bound repair evidence:
  - BacktestRun `cd19b7bc-ff03-47ae-8183-79bd36258a51`
  - BacktestResult `8571385f-1a3a-40d5-82fb-3cd7c205aa55`
  - RuleApplicabilityProfile stable id `e49756c0-21c1-4558-a57f-aabd7c91f94d`
  - profile row id `ea020370-e641-41ea-9791-69688a72a38e`
  - DatasetSnapshot `680a9e4a-8cb4-4131-8ef0-785031cb670b`
- DailyRuleSelection: `8db45d9a-d944-4686-a1ab-d2564552ba85`
- DailyStrategyInstance: `9a8858ec-70c1-4348-bc41-b969dd131d40`
- TradingDayPlan: `ce6dd260-c916-4151-bb33-4361837b19fa`
- PostMarketReview: `4249b5b2-6e9a-4c93-88c8-d76c4fa47429`
- OptimizationProposal records:
  - RuleOptimizationProposal `0d82c843-0130-435d-af0e-9b507c228de8`
  - AuthorProfileRevisionProposal `f328e549-8be8-4ab1-b07b-fb287872a806`
  - StrategyRevisionProposal `0cad8dc4-a2b6-4961-9e8e-2d356df67fca`

### Review loop

- Loop 1 found the validation contract mismatch between nested formal `BacktestResult.coverage_json` and strategy validation's flat-field reader; fixed the contract and added focused unit coverage.
- Loop 2 found dataset snapshot selection could choose a future snapshot; fixed the repository lookup and added a point-in-time regression test.
- Loop 3 found daily readiness rejected valid level-1 global applicability profiles; fixed the readiness matcher and added a regression test.
- Loop 4 found broader daily/post-close tests exposed naive/aware datetime mismatches; fixed timestamp normalization and reran the affected suite.

### Verification

- `python -m scripts.web_local env-check`: pass, redacted output only.
- `python -m cli.main db-check --config config/app.template.yaml`: pass.
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, current/head `2026_06_20_0001`.
- Focused backend aggregate: `73 passed`.
- `web` typecheck with Node 18: pass.
- `web` route-config test: `12 passed`.
- `git diff --check`: pass.
- Changed-files secret scan: pass, no matches.

### Residuals

- Browser E2E Acceptance remains not started and must not reuse these records as final pass evidence.
- PostMarketReview and optimization proposals were generated truthfully from partial/invalid post-close evidence; evidence states were not faked to ready.
- An earlier attempted dataset-bound repair created a non-final backtest/applicability set against a future-selected dataset before the point-in-time repository fix. It is not counted as daily readiness evidence.

### Decision

`READY_FOR_RT_S12_002_IMPLEMENTATION`

## 2026-06-24 RT-S12-002 Readiness Repair — 5.5 Review / Bounded Repair

### Status

`READINESS_REPAIR_ACCEPTED_WITH_RESIDUAL_BLOCKERS`

### Scope

- Review only; no RT-S12-002 browser E2E acceptance started.
- No RT-S12-003 user documentation started.
- No Stage 12 Gate started.
- No data/evidence repair, live crawl, live market backfill, live LLM extraction, or formal business-state mutation executed.

### Entry verification

- Stage 11 Gate: `ACCEPTED`.
- Stage 12 Bootstrap: `READY`.
- `RT-S12-001`: `ACCEPTED`.
- `RT-S12-002`: implementation not started; readiness/preflight only.
- `RT-S12-003`: not started.
- Stage 12 Gate: not started.
- Prior RT-S12-002 Preflight: `BLOCKED`.
- Readiness Repair claim: `PARTIAL_READY`.
- Review-start HEAD: `e2625af RT-S12-002 Readiness Repair`; repair commit is present.
- Review-start working tree: clean.

### Findings and bounded repairs

- Found one tooling/documentation consistency defect: `web/package.json` contained `@playwright/test` but lacked the documented `e2e`, `e2e:headed`, and `e2e:install` scripts.
- Bounded repair:
  - added the three Playwright package scripts to `web/package.json`
  - corrected `docs/refactor-implementation-logs/rt-s12-002-preflight.md` so remaining browser work is Chromium install only when the later browser E2E task is explicitly authorized
  - replaced new env-check test fixture values with clearly fake/example values to keep changed-files secret scan classification clean
- No unrelated files were modified.

### Verification

- `python -m pytest tests/unit/scripts/test_web_local.py -q`: `4 passed`.
- `python -m scripts.web_local env-check`: pass; printed only set/unset/source with sensitive values redacted.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm typecheck`: pass.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm test -- src/app/route-config.test.tsx`: `12 passed`.
- `cd web && PATH=${NODE18_BIN}:$PATH pnpm exec playwright --version`: `Version 1.61.1`.
- `git diff --check`: pass.
- Changed-files secret scan:
  - hits are variable names, redacted labels, dependency names/integrities, fake/example test fixtures, or pre-existing local helper parameter names
  - no committed local config file and no real secret value found

### Residual blockers

- Canonical downstream evidence chain remains missing.
- OHLCV still covers only one trade date.
- `DatasetSnapshot` remains `partial`.
- `MarketSnapshot` and `MarketRegime` evidence remain missing.
- Legacy rule/backtest rows must still not be counted as final RT-S12-002 evidence.

### Decision

`READINESS_REPAIR_ACCEPTED_WITH_RESIDUAL_BLOCKERS`

## 2026-06-24 RT-S12-002 Readiness Repair — Tooling / Runtime Baseline / Data Recheck

### Status

`PARTIAL_READY`

### Scope

- Bounded readiness repair only; no RT-S12-002 browser E2E acceptance started.
- No RT-S12-003 user documentation started.
- No Stage 12 Gate started.
- No formal business-state mutation, live crawl, live LLM generation, or broad market-data backfill executed.

### Repairs completed

- Tooling / browser baseline:
  - added `@playwright/test` to `web/package.json`
  - added `web/playwright.config.ts`
  - added `pnpm e2e` / `pnpm e2e:headed` / `pnpm e2e:install`
  - verified `pnpm exec playwright --version` -> `1.61.1`
- Local runtime baseline:
  - `scripts/web_local.py` now prefers the configured local Node 18 bin directory when available
  - `scripts/web_local.py` now uses `config/app.template.yaml` for local migrate/worker helpers
  - added `python -m scripts.web_local env-check` to parse `.env` safely without shell-sourcing and to print only redacted values
- Working-tree classification:
  - only bounded readiness-repair files changed in this session
  - no unrelated repo files were modified

### Selected future E2E article subset

- `be0d68bd-8fc3-445c-8510-8b01a43185d6` — `量化风格下的轮动行情该如何实战思考，上周总结以及下周应对思路看这里！`
- `fb673d83-bfb7-4a88-a804-c60ad2f8d8a2` — `教你短线模式之一字首开！淘县九年义务教育！`
- `8856f8f8-2441-492a-9292-981f0b3e1672` — `教你恒宝股份短线逻辑全拆解！`
- `84558067-1ba1-4248-9700-fd4225be8593` — `南方路机，短线逻辑全拆解！`
- `fc461ca7-ff28-4c81-ba58-e4bc69ec8461` — `教你什么是短线跨年龙模式~淘县九年义务教育！`

All five already have one current `article_analysis_v1` prompt run and one candidate each; none yet has current formal reviewed downstream evidence.

### Remaining blockers after repair

- Canonical downstream evidence remains missing:
  - `rule_versions` are still legacy-only / unresolved
  - `backtest_runs` / `backtest_results` / `rule_applicability_profiles` / `author_profile_versions` / `strategy_versions` / `daily_rule_selections` / `post_market_reviews` / `optimization_proposals` are still `0`
- Deterministic market data remains insufficient:
  - `ohlcv_bars` still cover only one trade date (`2026-04-20`)
  - the only `dataset_snapshot` is still `partial`
  - `market_snapshots` / `market_regimes` are still `0`
- No truthful local seed files were available to repair those blockers offline:
  - `data/kaipan/raw` and `data/market_universe/snapshots` contain directory scaffolding but no usable local snapshot payloads
- Because this bounded task did not run live provider fetches or fresh LLM generation, the formal data/evidence blockers could not be truthfully cleared

### Decision

`PARTIAL_READY`

- Fixed blockers:
  - browser E2E tooling missing from web workspace
  - default shell Node too old for `pnpm`
  - current `.env` cannot be safely shell-sourced
- Remaining blockers:
  - minimal canonical rule/backtest/applicability/profile/strategy/daily/post-close/proposal evidence chain still absent
  - OHLCV / DatasetSnapshot / MarketSnapshot / MarketRegime readiness still insufficient for truthful snapshot-bound RT-S12-002 evidence

## 2026-06-24 RT-S12-002 Preflight — Tooling / Config / Data / Formal Route Readiness

### Status

`BLOCKED`

### Scope

- Preflight only; no RT-S12-002 implementation started.
- No production code changes.
- No browser E2E.
- No live crawl, live backfill, live LLM run, or formal business-state mutation.

### Result summary

- Config baseline used: `config/app.template.yaml`
- Database-first decision: reuse existing `blog_articles` / `article_revisions`; do not recrawl or bulk-regenerate corpus
- Tooling readiness:
  - backend imports available
  - local DB reachable
  - default shell Node is too old for `pnpm`
  - `pnpm typecheck` passes with Node 18 path
  - `pnpm test` runs with Node 18 path but current suite has failures
  - `@playwright/test` is missing from `web/package.json`
- Redacted secret readiness:
  - `DATABASE_URL` / `ADMIN_API_KEY` / `DASHSCOPE_API_KEY` / `TGB_COOKIE` /
    `KAIPAN_TOKEN` / `KAIPAN_USER_ID`: set
  - `.env` cannot be safely shell-sourced because the cookie value contains raw
    semicolons
- Canonical data readiness:
  - articles/revisions present
  - only `12` current `article_analysis_v1` prompt runs
  - `rule_versions` are legacy-only / unresolved
  - no canonical backtest/applicability/profile/strategy/daily/post-close/proposal chain
  - OHLCV only has `84` rows for one trade date
  - one `dataset_snapshot` exists but lifecycle is `partial`
  - `market_snapshots` / `market_regimes`: `0`
- Formal route readiness:
  - required formal routes exist in `web/src/app/route-config.tsx`
  - frozen ordinary-user path does not require retired routes
- Missing items:
  - browser E2E tooling
  - minimal canonical rule/backtest/profile/strategy/daily evidence chain
  - deterministic OHLCV window and snapshot/state evidence

### Detailed record

- Detailed report: `docs/refactor-implementation-logs/rt-s12-002-preflight.md`

### Next allowed action

- Fix preflight blockers first.
- Do not start RT-S12-002 implementation until the blocker list is addressed and
  the user authorizes implementation.

## 2026-06-25 RT-S12-002 BacktestRun Schema Compatibility Repair — No-Data Device

### Status

`BACKTESTRUN_SCHEMA_REPAIR_ACCEPTED_WITH_RESIDUALS`

### Entry Verification

- Stage 11 Gate：`ACCEPTED`，from Stage 11 and main implementation logs.
- Stage 12 Bootstrap：`READY`，from `docs/refactor-implementation-plans/stage-12-implementation-plan.md` and this Stage 12 log.
- `RT-S12-001`：`ACCEPTED`.
- `RT-S12-002` browser E2E：not started in this repair.
- `RT-S12-003` user documentation：not started.
- Stage 12 Gate：not started.
- Working tree before repair：clean at `f5c038b` before pulling later upstream preflight/readiness commits.
- This repair was rebased over upstream `RT-S12-002 Minimal Canonical Evidence Repair`; the current preflight record is `docs/refactor-implementation-logs/rt-s12-002-preflight.md`.

### Scope

- This was a narrow code/schema compatibility repair only.
- No articles, OHLCV, DatasetSnapshot, MarketSnapshot, MarketRegime, RuleVersion, BacktestRun, BacktestResult, RuleApplicabilityProfile, author profile, strategy, daily plan, or optimization-proposal business evidence was imported, seeded, recreated, or counted as current RT-S12-002 evidence.
- Minimal Canonical Evidence Repair Resume was not run.
- Browser E2E, live provider refresh, LLM, live crawl, market backfill, RT-S12-003 docs, and Stage 12 Gate were not started.

### Root Cause

- ORM mapped `BacktestRun.status` through `SAEnum(BacktestRunStatus, name="backtest_run_status")`.
- Committed migration `2026_06_18_0010_stage6_backtest_run_foundation.py` creates `backtest_runs.status` as `sa.String(length=32)`.
- On a database that follows the committed migration-backed schema, the ORM enum mapping can require missing PostgreSQL enum type `backtest_run_status`.
- Creating that enum manually would be an unapproved schema change, so the migration-backed `String(32)` column remains the source of truth.

### Implementation

- Updated `src/models/stage2_canonical.py` so `BacktestRun.status` is mapped as `String(32)`.
- Kept `BacktestRunStatus` as a Python `StrEnum` / service-layer allowed-value constant.
- Confirmed existing service code writes literal allowed status strings such as `dependency_checked`, `completed_valid`, and `completed_invalid`; no lifecycle behavior was broadened.
- Added a focused SQLAlchemy metadata test proving `BacktestRun.status` is `String(32)`, is not `SAEnum`, and no longer carries the `backtest_run_status` enum type name.

### Verification

- Red test before fix:
  - `../.venv/bin/python -m pytest tests/unit/models/test_stage2_canonical_models.py::test_backtest_run_status_matches_migration_backed_string_schema -q`
  - result: failed because `BacktestRun.status` was `Enum(..., name='backtest_run_status')`.
- Focused metadata test after fix:
  - `../.venv/bin/python -m pytest tests/unit/models/test_stage2_canonical_models.py::test_backtest_run_status_matches_migration_backed_string_schema -q`
  - result: `1 passed`.
- Requested service tests:
  - `../.venv/bin/python -m pytest tests/unit/services/test_backtest_application_service.py tests/unit/services/test_rule_applicability_service.py -q`
  - result: `22 passed`.
- Broader touched model metadata tests:
  - `../.venv/bin/python -m pytest tests/unit/models/test_stage2_canonical_models.py -q`
  - result: `5 passed`.
- Optional local env check:
  - `../.venv/bin/python -m scripts.web_local env-check`
  - result: skipped/unavailable because this checkout's `scripts.web_local` has no `env-check` command.
- DB-dependent checks:
  - `../.venv/bin/python -m cli.main db-check --config config/app.template.yaml`: skipped because `DATABASE_URL` / local DB environment was not available on this no-data device.
  - `../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini current`: skipped because `DATABASE_URL` / local DB environment was not available on this no-data device.
- `git diff --check`: pass.
- Changed-files secret scan on `src/models/stage2_canonical.py` and `tests/unit/models/test_stage2_canonical_models.py`: no matches.

### Residuals / Next Task

- Local DB/evidence checks were not run on this no-data device.
- Minimal Canonical Evidence Repair remains represented by the upstream Stage 12 records; this schema repair did not add, modify, or count business evidence.
- `RT-S12-002` browser E2E remains not started.

### Final Decision

`BACKTESTRUN_SCHEMA_REPAIR_ACCEPTED_WITH_RESIDUALS`

## 2026-06-23 RT-S12-001 Blocker Repair — Ordinary-user terminology cleanup

### Status

`ACCEPTED`

### Entry Verification

- Prior 5.5 review state: `RT-S12-001 BLOCKED` only by ordinary-user-adjacent internal terminology/link exposure outside the route registry.
- Route-level retirement candidates: verified as redirect-only / hidden from normal product navigation in `web/src/app/route-config.tsx` and route tests.
- `RT-S12-002`、`RT-S12-003`、final E2E、user documentation、Stage 12 Gate: not started.
- Working tree before blocker repair already contained 5.4/5.5 route-review changes; no unrelated files were reverted.

### Bounded Repair Scope

- Fixed shared ordinary-user-adjacent recovery actions:
  - `web/src/lib/error-recovery.ts`
  - `web/src/lib/error-recovery.test.ts`
- Fixed dashboard/status ordinary-user-adjacent wording and retired links:
  - `web/src/components/dashboard/dashboard-alert-strip.tsx`
  - `web/src/components/dashboard/dashboard-recent-artifacts.tsx`
  - `web/src/components/dashboard/dashboard-recent-jobs.tsx`
  - `web/src/components/dashboard/dashboard-status-summary.tsx`
  - `web/src/components/status/recent-artifacts-panel.tsx`
  - `web/src/components/status/recent-jobs-panel.tsx`
- Fixed System Management diagnostic display labels without renaming API/backend fields:
  - `web/src/pages/system/index.tsx`
  - `web/src/pages/system/index.test.tsx`
- No backend API field, database field, schema, governance lifecycle, evidence object, E2E, user documentation, or Stage Gate work was changed.

### Terminology / Link Scan Classification

Required command:

```bash
rg -n "Job|Workflow|Pipeline|Artifact|Provider|Schema|config_path|prompt_run_id|run_id|/jobs|/artifacts|/workflows" web/src docs -g '!**/*.test.*'
```

Post-repair final scan captured `5044` hits in a temporary local evidence file that is not a formal documentation source.

| Hit group | Representative files | Classification | Action |
| --- | --- | --- | --- |
| Dashboard/recovery ordinary-user wording and `/jobs`/`/artifacts` links | `web/src/lib/error-recovery.ts`, `web/src/components/dashboard/*`, `web/src/components/status/*` | fixed ordinary-user-visible issue | replaced with `运行记录` / `运行产出` and formal targets `/system/runs`, `/system/data`, `/system/configuration`, `/rules/*`, `/daily/*` |
| System Management run/cost diagnostics | `web/src/pages/system/index.tsx` | admin diagnostic allowed | kept technical IDs under System Management, relabeled visible fields as `运行编号` / `结构版本`; no ordinary workflow input required |
| Route registry retired paths | `web/src/app/route-config.tsx` | redirect-only compatibility registry | allowed; all retirement candidates redirect to formal targets and are hidden from normal navigation |
| Formal daily/backtest/strategy implementation fields | `web/src/pages/daily/index.tsx`, `web/src/features/backtest/formal-backtest-*.tsx`, `web/src/pages/strategies/StrategyOverviewPage.tsx` | internal implementation only | allowed; visible copy uses business Chinese such as `运行编号` / `回测记录` and does not expose `run_id` as required user input |
| Unmounted legacy compatibility source | `web/src/pages/jobs/*`, `web/src/pages/artifacts/*`, `web/src/features/workflows/*`, `web/src/features/market-workspace/*`, `web/src/features/strategy-workspace/*`, legacy backtest pages | internal/legacy source only after route retirement | allowed for RT-S12-001 because route-config no longer mounts them as normal product entries; residual cleanup can occur only under later authorized work |
| API clients and TS types | `web/src/lib/api/*`, `web/src/types/*` | internal implementation only | allowed; backend/API fields were not renamed in this bounded repair |
| Tests / fixtures | excluded by required scan; inspected separately where affected | test fixture only | affected assertions updated; legacy route tests remain evidence for redirect behavior |
| Historical docs and archived docs | `docs/bak/**`, `docs/Deprecated/**`, stage plans/logs, migration/current-state audits | historical documentation note | allowed; not normal user documentation and not updated as RT-S12-003 docs work |

No remaining hit is classified as `remaining blocker`.

### Verification

- `PATH="${NODE18_BIN}:$PATH" pnpm vitest run src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx src/lib/error-recovery.test.ts src/components/dashboard/dashboard-recent-jobs.test.tsx src/components/dashboard/dashboard-status-summary.test.tsx src/pages/system/index.test.tsx`
  - result: `9` files passed, `89` tests passed.
- Broader exploratory frontend run additionally included daily/strategy pages; it had one unrelated date-sensitive failure in `src/pages/daily/index.test.tsx` expecting `2026-06-22` while the session date is `2026-06-23`, plus stale expectations repaired in this blocker scope. The accepted verification set above excludes that unrelated date assertion.
- `PATH="${NODE18_BIN}:$PATH" pnpm typecheck`
  - result: pass.
- `PATH="${NODE18_BIN}:$PATH" pnpm eslint src/lib/error-recovery.ts src/lib/error-recovery.test.ts src/components/dashboard/dashboard-recent-jobs.tsx src/components/dashboard/dashboard-recent-artifacts.tsx src/components/dashboard/dashboard-status-summary.tsx src/components/dashboard/dashboard-alert-strip.tsx src/components/status/recent-jobs-panel.tsx src/components/status/recent-artifacts-panel.tsx src/pages/system/index.tsx src/pages/system/index.test.tsx`
  - result: pass.
- `git diff --check`
  - result: pass.
- Required terminology scan:
  - result: completed; `5044` hits classified above; no remaining ordinary-user-visible blocker.
- Backend/API tests:
  - not run; this blocker repair changed only frontend wording/links, route-adjacent shared recovery text, System Management display labels, tests, and logs. No backend route, API client contract, database schema, or evidence access logic changed.

### Residual Risks

- Legacy source files still contain developer terms and retired links, but the 5.5 route registry no longer exposes them as normal workflow entries. They are classified as unmounted legacy compatibility source, not active ordinary-user product flow.
- System Management diagnostics still display technical IDs for operators/admins, with Chinese labels and no requirement for ordinary users to supply those IDs.
- Browser E2E and user documentation remain future Stage 12 tasks and were not started here.

### Final Decision

`RT-S12-001 ACCEPTED`

## 2026-06-23 RT-S12-001 5.5 Review / Bounded Repair

### Review Status

`BLOCKED`

### Entry Verification

- Stage 11 Gate：`ACCEPTED`，from `docs/refactor-implementation-logs/stage-11.md`.
- Stage 12 Bootstrap：`READY`，from this log and `docs/refactor-implementation-plans/stage-12-implementation-plan.md`.
- 5.4 implementation state：`READY_FOR_5.5_REVIEW`，from this log and `docs/Refactor-Implementation-Log.md`.
- `RT-S12-002`、`RT-S12-003`、final E2E、user documentation、Stage 12 Gate：not started.
- Branch：`main`.
- Review-start HEAD：`5c578e76ef9afedf06cc84654ada4b7150ac63a6`.
- Review-start dirty files：5.4 implementation files only:
  `docs/Refactor-Implementation-Log.md`,
  `docs/refactor-implementation-logs/stage-12.md`,
  `web/src/app/route-config.tsx`,
  `web/src/app/route-config.test.tsx`,
  `web/src/components/layout/section-nav.test.tsx`.
- Subagents：0 selected. Parent review only; route inventory and scans were local, mechanical, and did not justify coordination overhead.

### Reviewed 5.4 Scope

- `web/src/app/route-config.tsx` converted legacy main entries to hidden redirects and removed no-longer-used legacy page imports.
- `web/src/app/route-config.test.tsx` asserted legacy metadata and redirect behavior.
- `web/src/components/layout/section-nav.test.tsx` updated the System Management label expectation.
- Stage 12 and main implementation logs recorded the 5.4 handoff.
- No backend, database, schema, prompt, governance lifecycle, evidence object, E2E, or user-doc work was started.

### 5.5 Bounded Repair

- `web/src/app/route-config.tsx`
  - changed the remaining mutable or developer-facing legacy detail candidates from mounted legacy pages to redirects:
    `/jobs/:jobId`, `/profiles/:profileId`, `/profiles/:profileId/edit`,
    `/profiles/:profileId/snapshots/:snapshotId`, `/workflows/:workflowId/run`,
    `/backtest/regime`, `/rule-pool/:ruleId`, `/artifacts/:artifactId`,
    `/market/snapshots`, `/market/datasets`.
  - removed the corresponding legacy page imports from the route registry.
- `web/src/app/route-config.test.tsx`
  - updated metadata expectations and now requires every retired route candidate to redirect to a formal product or System Management target.
- `web/src/app/router-auth.test.tsx`
  - updated dynamic legacy deep-link behavior: `/jobs/job-123` now redirects to `/system/runs`.

### Full Retirement Inventory

| Legacy route | Handling after 5.5 repair | Formal target | Ordinary-user exposure | Evidence / rollback preservation |
| --- | --- | --- | --- | --- |
| `/workflows` | redirected | `/system/runs` | no normal entry | system run trace page preserves run evidence |
| `/workflows/:workflowId/run` | redirected | `/system/runs` | no normal entry | system run trace page preserves legacy runtime evidence |
| `/workflows/pre-market` | redirected | `/daily/pre-market` | no normal entry | formal daily pre-market page |
| `/workflows/pre-market/run` | redirected | `/daily/pre-market` | no normal entry | formal daily pre-market page |
| `/workflows/after-close` | redirected | `/daily/after-close` | no normal entry | formal daily after-close page |
| `/workflows/after-close/run` | redirected | `/daily/after-close` | no normal entry | formal daily after-close page |
| `/jobs` | redirected | `/system/runs` | no normal entry | system run trace page |
| `/jobs/:jobId` | redirected | `/system/runs` | no normal entry | system run trace page; direct detail resolver remains future hardening |
| `/artifacts` | redirected | `/system/runs` | no normal entry | system run trace / artifact evidence remains queryable through diagnostics |
| `/artifacts/:artifactId` | redirected | `/system/runs` | no normal entry | system run trace / artifact evidence remains queryable through diagnostics |
| `/market` | redirected | `/system/data` | no normal entry | formal data and scheduling page |
| `/market/snapshots` | redirected | `/system/data` | no normal entry | formal data diagnostics preserve snapshot evidence |
| `/market/datasets` | redirected | `/system/data` | no normal entry | formal data diagnostics preserve dataset evidence |
| `/market/kaipan` | redirected | `/system/data` | no normal entry | formal data page |
| `/market/ohlcv` | redirected | `/system/data` | no normal entry | formal data page |
| `/backtest` | redirected | `/rules/backtests` | no normal entry | formal backtest workbench |
| `/backtest/regime` | redirected | `/rules/results` | no normal entry | formal market-state result page |
| `/backtest/candidates` | redirected | `/strategies/candidates` | no normal entry | formal strategy candidate page |
| `/strategies/pre-market` | redirected | `/daily/pre-market` | no normal entry | formal daily pre-market page |
| `/strategies/after-close` | redirected | `/daily/after-close` | no normal entry | formal daily after-close page |
| `/dashboard` | redirected | `/` | no normal entry | formal home page |
| `/articles` | redirected | `/research/articles` | no normal entry | formal article library |
| `/articles/run` | redirected | `/research/add` | no normal entry | formal article import page |
| `/articles/list` | redirected | `/research/articles` | no normal entry | formal article library |
| `/articles/quality` | redirected | `/research/results` | no normal entry | formal extraction results page |
| `/articles/results` | redirected | `/research/results` | no normal entry | formal extraction results page |
| `/rule-pool` | redirected | `/rules/review` | no normal entry | formal rule review page |
| `/rule-pool/:ruleId` | redirected | `/rules/library` | no normal entry | formal rule library |
| `/persona` | redirected | `/authors` | no normal entry | formal author profile page |
| `/profiles` | redirected | `/system/configuration` | no normal entry | formal configuration page |
| `/profiles/import` | redirected | `/system/configuration` | no normal entry | formal configuration page |
| `/profiles/:profileId` | redirected | `/system/configuration` | no normal entry | formal configuration diagnostics |
| `/profiles/:profileId/edit` | redirected | `/system/configuration` | no normal entry | prevents legacy edit page from remaining live |
| `/profiles/:profileId/snapshots/:snapshotId` | redirected | `/system/configuration` | no normal entry | formal configuration diagnostics |
| `/alerts` | redirected | `/system/runs` | no normal entry | formal system run / alert diagnostics |
| `/admin` | redirected | `/system/status` | no normal entry | formal system status |
| `/admin/audit` | redirected | `/system/audit` | no normal entry | formal audit page |
| `/system/restore` | redirected | `/system/backup` | no normal entry | formal backup/recovery page |
| `/settings` | redirected | `/system/configuration` | no normal entry | formal configuration page |

### Retained Compatibility Register

After 5.5 bounded repair, no RT-S12-001 retirement-candidate route remains as a mounted read-only compatibility page in `web/src/app/route-config.tsx`; all candidates are redirect-only. Canonical long-term routes `/login`, `/`, `/strategies`, `/system/*`, and `*` are not retirement candidates.

### Reference Scan Classification

- Required broad route scan:
  `rg -n "/workflows|/jobs|/artifacts|/market|/backtest|/strategies/pre-market|/strategies/after-close|/dashboard|/articles|/rule-pool|/persona|/profiles|/alerts|/admin|/settings|/system/restore" web docs`
  - Active `route-config` hits are expected redirect definitions and route tests.
  - Active `web/src/lib/api/*` hits are internal API-client implementation, not route registry or navigation.
  - Active legacy component/page hits remain in source but are no longer imported by `route-config`; direct legacy route mounts were removed.
  - `docs/Refactor-Migration-Matrix.md`, Stage plans/logs, and current implementation logs are historical / contract evidence.
  - `docs/bak/**` and `docs/Deprecated/**` contain archived historical notes; not normal user documentation.
- Required internal terminology scan:
  `rg -n "Job|Workflow|Pipeline|Artifact|Provider|Schema|config_path|prompt_run_id|run_id" web/src docs -g '!**/*.test.*'`
  - Admin/system diagnostics allowed: `web/src/pages/system/index.tsx`, system management workspace, audit/run trace references.
  - Internal implementation only: API clients, TS types, component names, unmounted legacy pages/components.
  - Historical documentation note: TaskList, migration matrix, stage plans/logs, current-state audit.
  - `must fix / blocker`: active formal or ordinary-user-adjacent components still contain visible `Job` / `/jobs` / `Artifact` wording and links outside the route registry, including examples in `web/src/pages/daily/index.tsx`, `web/src/features/strategy-workspace/*`, `web/src/features/backtest/*`, `web/src/features/market-workspace/*`, dashboard/status artifact/job panels, and shared error recovery actions. Some may be unmounted by current formal routes, but this review did not prove all are unreachable from ordinary user flows.

### Verification

- `pnpm vitest run src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx`
  - first attempt failed because the default shell used Node `v14.4.0`.
  - rerun with Node 18 path: `5` files passed, `70` tests passed.
- `pnpm typecheck`
  - pass.
- `pnpm exec eslint src/app/route-config.tsx src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.ts src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx`
  - pass.
- `git diff --check`
  - pass.
- Backend/API tests:
  - not run; bounded repairs only changed frontend route exposure, route tests, and logs. No API client, backend route, database, System Management service, or evidence access logic was changed in 5.5.

### Automatic Repair Loop Summary

- Finding 1: retained `/jobs/:jobId` metadata lacked formal target / retirement condition in route config.
  - repair: redirected to `/system/runs`.
- Finding 2: `/profiles/:profileId/edit` mounted a mutable edit page, violating read-only/redirect-only compatibility criteria.
  - repair: redirected profile detail/edit/snapshot compatibility routes to `/system/configuration`.
- Finding 3: other retained evidence detail routes mounted legacy pages that could expose developer-facing workflow controls or terms.
  - repair: redirected job/artifact/workflow/backtest/rule/market detail candidates to formal targets.
- Finding 4: ordinary-user visible internal terminology remains outside route registry.
  - result: not fully repaired in this bounded pass; needs additional ordinary-user exposure cleanup or a 5.5 scoping decision.

### Residual Risks / Blockers

- `BLOCKER`: the required internal terminology scan still finds active non-test frontend source with visible `Job`, `/jobs`, `Artifact`, `run_id`, and related wording outside `route-config`. Some hits are admin diagnostics or unmounted legacy components, but this review did not prove all remaining hits are inaccessible to ordinary users.
- `BLOCKER`: because of those unclassified/active ordinary-user-adjacent hits, RT-S12-001 cannot yet satisfy the hard forbidden condition that `Job / Workflow / Pipeline / Artifact / Provider / Schema / config_path / prompt_run_id / run_id` are not exposed as ordinary-user workflow concepts or required inputs.
- Non-blocking note: route-level old-entry retirement itself now passes focused tests; no retired route candidate remains mounted as a legacy page.

### 5.5 Review Decision

`RT-S12-001 BLOCKED`

Exact blocker: complete ordinary-user exposure cleanup/classification is still required for internal terminology hits outside the route registry before the task can be accepted. Do not start `RT-S12-002`, `RT-S12-003`, final E2E, user documentation, or Stage 12 Gate.

## 2026-06-23 RT-S12-001 旧入口退役

### Status

`READY_FOR_5.5_REVIEW`

### Scope

- 只修改 `web/src/app/route-config.tsx`、相关路由/导航测试和正式实施日志；
- 只处理 legacy route/page entry、navigation exposure、redirect/hide decisions、
  related unused imports、route tests、navigation tests 和 retirement evidence log；
- 不修改数据库 schema、formal records、Prompt evidence、migration reports、
  backtest evidence、strategy/rule/profile audit history、daily plans、
  optimization proposals、governance lifecycle 或 backend runtime behavior；
- 不启动 `RT-S12-002`、`RT-S12-003`、browser E2E、Stage 12 Gate 或用户文档。

### Entry Verification

- Stage 11 Gate：`ACCEPTED`
- Stage 12 Bootstrap：`READY`
- `RT-S12-001` 是 Stage 12 下一且必须单独执行的 Task：verified
- Stage 12 implementation 在本 Session 前未开始：verified from
  `docs/refactor-implementation-logs/stage-12.md` and
  `docs/Refactor-Implementation-Log.md`
- working tree before edits：clean
- no parallel Stage 12 task / E2E / docs work started：verified

### Implementation

- `web/src/app/route-config.tsx`
  - 将确认已被 formal route 覆盖的 legacy 主入口改为 direct redirect，避免普通用户
    再进入旧工作台：
    - `/jobs` -> `/system/runs`
    - `/profiles` -> `/system/configuration`
    - `/profiles/import` -> `/system/configuration`
    - `/workflows` -> `/system/runs`
    - `/articles/run` -> `/research/add`
    - `/articles/list` -> `/research/articles`
    - `/articles/quality` -> `/research/results`
    - `/articles/results` -> `/research/results`
    - `/alerts` -> `/system/runs`
    - `/backtest` -> `/rules/backtests`
    - `/backtest/candidates` -> `/strategies/candidates`
    - `/rule-pool` -> `/rules/review`
    - `/artifacts` -> `/system/runs`
    - `/market` -> `/system/data`
    - `/market/kaipan` -> `/system/data`
    - `/market/ohlcv` -> `/system/data`
    - `/persona` -> `/authors`
    - `/strategies/pre-market` -> `/daily/pre-market`
    - `/strategies/after-close` -> `/daily/after-close`
  - 保留 evidence/deep-link sensitive compatibility routes 为 hidden read-only /
    compatibility-only surface，不暴露在 primary navigation：
    - `/jobs/:jobId`
    - `/artifacts/:artifactId`
    - `/market/snapshots`
    - `/market/datasets`
    - `/profiles/:profileId`
    - `/profiles/:profileId/edit`
    - `/profiles/:profileId/snapshots/:snapshotId`
    - `/workflows/:workflowId/run`
    - `/backtest/regime`
    - `/rule-pool/:ruleId`
  - 删除 redirect 后已不再使用的 legacy page imports；未删除 route registry，
    继续保持 `route-config.tsx` 为唯一 formal source-of-truth。
- `web/src/app/route-config.test.tsx`
  - 先以 failing test 固化 RT-S12-001 退役目标；
  - 更新 expected legacy metadata；
  - 新增断言：retired legacy main entries 必须 redirect，detail evidence routes
    继续 compatibility-only。
- `web/src/components/layout/section-nav.test.tsx`
  - 修复 stale 文案断言：`数据管理` -> `数据与调度`，使当前系统管理 section nav
    与正式路由标签一致。

### Retirement Inventory And Retained Compatibility Register

| Legacy route | Handling | Formal target | Owner | Evidence / rollback reason | Remaining retirement condition | Ordinary user visible | Admin/operator diagnostic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/dashboard` | redirected | `/` | Stage 1 product shell | none | stable long-term redirect | no | n/a |
| `/jobs` | redirected | `/system/runs` | Stage 11 system runs | list evidence already exposed in formal System Management | observe old deep-link traffic only | no | yes |
| `/jobs/:jobId` | read-only retained | `/system/runs` | Stage 11 system runs | job timeline, artifacts, logs, config snapshot deep links still live here | formal run detail resolver by business object or system route | no | yes |
| `/profiles` | redirected | `/system/configuration` | Stage 11 system configuration | none | observe old deep-link traffic only | no | yes |
| `/profiles/import` | redirected | `/system/configuration` | Stage 11 system configuration | none | observe old deep-link traffic only | no | yes |
| `/profiles/:profileId` | read-only retained | `/system/configuration` | Stage 11 system configuration | profile id deep links and configuration evidence remain reachable | formal configuration detail route / resolver | no | yes |
| `/profiles/:profileId/edit` | read-only retained | `/system/configuration` | Stage 11 system configuration | historical edit/review deep links still resolve here | formal configuration edit/detail route / resolver | no | yes |
| `/profiles/:profileId/snapshots/:snapshotId` | read-only retained | `/system/configuration` | Stage 11 system configuration | snapshot evidence deep links still resolve here | formal configuration snapshot route / resolver | no | yes |
| `/workflows` | redirected | `/system/runs` | Stage 11 system runs | list evidence already exposed in formal runs page | observe old deep-link traffic only | no | yes |
| `/workflows/pre-market` | redirected | `/daily/pre-market` | Stage 9 daily pre-market | none | stable redirect observation | no | n/a |
| `/workflows/pre-market/run` | redirected | `/daily/pre-market` | Stage 9 daily pre-market | none | stable redirect observation | no | n/a |
| `/workflows/after-close` | redirected | `/daily/after-close` | Stage 10 daily after-close | none | stable redirect observation | no | n/a |
| `/workflows/after-close/run` | redirected | `/daily/after-close` | Stage 10 daily after-close | none | stable redirect observation | no | n/a |
| `/workflows/:workflowId/run` | read-only retained | `/system/runs` | Stage 11 system runs | workflow-run deep links may still be needed to inspect legacy runtime evidence | formal legacy workflow resolver or confirmed no traffic | no | yes |
| `/articles` | redirected | `/research/articles` | Stage 3 research | none | stable long-term redirect | no | n/a |
| `/articles/run` | redirected | `/research/add` | Stage 3 research | formal import flow now covers user goal | observe old deep-link traffic only | no | n/a |
| `/articles/list` | redirected | `/research/articles` | Stage 3 research | formal article list now covers user goal | observe old deep-link traffic only | no | n/a |
| `/articles/quality` | redirected | `/research/results` | Stage 3 research | formal result/status view now covers user goal | observe old deep-link traffic only | no | n/a |
| `/articles/results` | redirected | `/research/results` | Stage 4 research | formal extraction result view now covers user goal | observe old deep-link traffic only | no | n/a |
| `/alerts` | redirected | `/system/runs` | Stage 11 system runs | alert list/repair actions already exposed in System Management and homepage | observe old deep-link traffic only | no | yes |
| `/backtest` | redirected | `/rules/backtests` | Stage 6 formal backtests | formal backtest workbench covers user workflow | observe old deep-link traffic only | no | n/a |
| `/backtest/regime` | read-only retained | `/rules/results` | Stage 6 formal backtests | market-state result evidence may still require legacy report deep link | formal result detail parity or confirmed unused | no | yes |
| `/backtest/candidates` | redirected | `/strategies/candidates` | Stage 8 strategy center | formal candidate route covers user goal | observe old deep-link traffic only | no | n/a |
| `/rule-pool` | redirected | `/rules/review` | Stage 4 rule review | formal review workbench covers user goal | observe old deep-link traffic only | no | n/a |
| `/rule-pool/:ruleId` | read-only retained | `/rules/library` | Stage 4 rule review | historical rule id mapping evidence may still resolve here | formal rule-detail legacy id resolver | no | yes |
| `/artifacts` | redirected | `/system/runs` | Stage 11 system runs | artifact list is no longer a formal user workflow | observe old deep-link traffic only | no | yes |
| `/artifacts/:artifactId` | read-only retained | `/system/runs` | Stage 11 system runs | artifact preview/download deep links still provide provenance access | formal artifact detail resolver by business object | no | yes |
| `/market` | redirected | `/system/data` | Stage 5 system data | formal data workspace covers ordinary-user repair path | observe old deep-link traffic only | no | yes |
| `/market/snapshots` | read-only retained | `/system/data` | Stage 5 system data | snapshot browser still carries admin/detail evidence | formal snapshot detail route or confirmed unused | no | yes |
| `/market/datasets` | read-only retained | `/system/data` | Stage 5 system data | dataset version browser still carries admin/detail evidence | formal dataset detail route or confirmed unused | no | yes |
| `/market/kaipan` | redirected | `/system/data` | Stage 5 system data | formal data workspace covers repair actions | observe old deep-link traffic only | no | yes |
| `/market/ohlcv` | redirected | `/system/data` | Stage 5 system data | formal data workspace covers repair actions | observe old deep-link traffic only | no | yes |
| `/persona` | redirected | `/authors` | Stage 7 author profiles | formal author-profile flow covers user goal | observe old deep-link traffic only | no | n/a |
| `/strategies/pre-market` | redirected | `/daily/pre-market` | Stage 9 daily pre-market | formal daily plan flow covers user goal | observe old deep-link traffic only | no | n/a |
| `/strategies/after-close` | redirected | `/daily/after-close` | Stage 10 daily after-close | formal post-market flow covers user goal | observe old deep-link traffic only | no | n/a |
| `/admin` | redirected | `/system/status` | Stage 11 system management | none | stable redirect observation | no | yes |
| `/admin/audit` | redirected | `/system/audit` | Stage 11 system management | none | stable redirect observation | no | yes |
| `/system/restore` | redirected | `/system/backup` | Stage 11 system management | none | stable redirect observation | no | yes |
| `/settings` | redirected | `/system/configuration` | Stage 11 system management | none | stable redirect observation | no | yes |

### Verification

- route / navigation / visibility tests
  - `pnpm vitest run src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx`
  - result: `5` files passed, `60` tests passed
- focused red/green proof
  - first `pnpm vitest run src/app/route-config.test.tsx` failed with 3 expected
    failures because legacy main entries were still `notice` instead of `redirect`
  - after `route-config.tsx` changes the same suite passed: `12` tests passed
- frontend typecheck
  - `pnpm typecheck`
  - result: pass
- targeted lint
  - `pnpm exec eslint src/app/route-config.tsx src/app/route-config.test.tsx src/app/router-auth.test.tsx src/app/navigation.ts src/app/navigation.test.ts src/components/layout/sidebar.test.tsx src/components/layout/section-nav.test.tsx`
  - result: pass
- safety
  - `git diff --check`
  - result: pass

### Reference Scan Results

- `rg -n "/workflows|/jobs|/artifacts|/market|/backtest|/strategies/pre-market|/strategies/after-close|/dashboard|/articles|/rule-pool|/persona|/profiles|/alerts|/admin|/settings|/system/restore" web/src docs --glob '!**/docs/bak/**' --glob '!**/docs/Deprecated/**'`
  - hits in `web/src/app/route-config.tsx`: expected formal route registry and compatibility definitions
  - hits in navigation/route tests: expected verification fixtures
  - hits in `docs/Refactor-Migration-Matrix.md`, current logs, and stage plans/logs:
    expected historical / retirement documentation
  - no new second route registry discovered
- legacy main-entry imports removed from `route-config.tsx` only after redirect conversion;
  retained detail pages continue to have explicit references from the single route registry

### Grep / Internal Terminology Classification

- `rg -n "Job|Workflow|Pipeline|Artifact|Provider|Schema|config_path|prompt_run_id|run_id" web/src docs -g '!**/*.test.*' --glob '!**/docs/bak/**' --glob '!**/docs/Deprecated/**'`
  - `web/src/app/route-config.tsx`: internal code only; legacy metadata and compatibility mapping
  - `docs/Trade-Refactor-TaskList.md`, `docs/Refactor-Migration-Matrix.md`,
    `docs/Refactor-Implementation-Log.md`, stage plans/logs: documentation historical note /
    contract language; allowed
  - `web/src/features/*`, `web/src/lib/api/*`, `web/src/components/artifacts/*`,
    `web/src/components/status/*`: internal code only or admin diagnostic allowed
  - no finding requiring RT-S12-001 code changes was found in primary navigation,
    section navigation, or `route-config` user-facing labels after this task

### Bounded Repairs

- Updated `web/src/components/layout/section-nav.test.tsx` to assert the current
  formal label `数据与调度`; the old `数据管理` expectation was stale and caused one
  focused verification failure.

### Residual Risks

- Compatibility detail routes still exist for job, artifact, workflow-run,
  snapshot, dataset, profile snapshot/edit and legacy rule/backtest detail evidence.
  This is intentional because formal resolver parity has not yet been proven.
- Reference scans still show many historical mentions inside migration matrix,
  stage plans, and implementation logs. These are retirement evidence, not active
  user workflow docs.
- No browser E2E or user documentation work was started in this Task; both remain
  later Stage 12 scope.

### Implementation Decision

`READY_FOR_5.5_REVIEW`

## 2026-06-23 Stage 12 Bootstrap

### Status

`READY`

### Scope

- 只执行 Stage 12 Bootstrap / contract freezing；
- 创建 Stage 12 implementation plan 和 Stage 12 log；
- 更新主实施日志的当前状态、索引、残余风险和下一步；
- 不实现生产代码；
- 不退役 legacy routes；
- 不修改 frontend / backend / database runtime behavior；
- 不启动 `RT-S12-001`、`RT-S12-002` 或 `RT-S12-003`。

### Required Reading Completed

- `AGENTS.md`
- `trade-strategy-ai/AGENTS.md`
- `docs/AI-Conversation-Templates.md`
- `docs/AI-Conversation-Project-Constraints-1.md`
- `docs/AI-Conversation-Project-Constraints-2.md`
- `docs/AI-Conversation-Task-Matrix.md`
- `docs/Trade-Refactor-TaskList.md`
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
- `docs/PROMPT_REVIEW_AND_MIGRATION.md`
- `docs/AUTHOR_PROFILE_PROMPT_FLOW.md`
- `docs/refactor-implementation-logs/stage-11.md`
- `docs/Refactor-Implementation-Log.md`
- Stage 0-11 implementation plans/logs were scanned for retirement,
  compatibility, final-delivery, residual-risk, Gate, and E2E evidence needed
  for Stage 12 readiness.
- `web/src/app/route-config.tsx` was read to verify current route metadata and
  retirement candidates.

### Entry Verification

- Stage 11 Gate：`ACCEPTED`
- `RT-S11-001 系统管理入口`：`ACCEPTED`
- `RT-S11-002 自动化和恢复`：`ACCEPTED`
- `RT-S11-003 可观测性和运行追踪`：`ACCEPTED`
- `RT-S11-004 成本与增量控制`：`ACCEPTED`
- `RT-S11-005 数据时间语义`：`ACCEPTED`
- `RT-S11-006 灰度迁移和回滚`：`ACCEPTED`
- `RT-S11-007 用户友好错误`：`ACCEPTED`
- Stage 12 before Bootstrap：not started
- working tree before Bootstrap edits：clean
- Branch：`main`
- Baseline commit：`6d15a217694569008cb39ad194871c119de66a58`

### Frozen Contracts

- Stage 12 must not create a second formal source-of-truth.
- Stage 12 must not remove evidence required for traceability, rollback, audits,
  prompt history, data provenance, or migration recovery.
- Legacy route retirement must happen only when the new formal entry is
  verified.
- Ordinary users must not see developer-tool main entries.
- User-facing docs must not require understanding internal developer terms.
- Missing, partial, unavailable, degraded, invalid, and conflict states remain
  truthful.
- Accepted governance paths for rules, profiles, strategies, daily plans, and
  optimization proposals must be preserved.
- Deletion versus hiding criteria, rollback/recovery expectations, E2E
  acceptance path, required documentation deliverables, task order, per-task
  acceptance criteria, residual-risk classification, and verification strategy
  are frozen in
  `docs/refactor-implementation-plans/stage-12-implementation-plan.md`.

### Frozen Task Order

1. `RT-S12-001 旧入口退役`
2. `RT-S12-002 端到端验收`
3. `RT-S12-003 用户文档`

Combination rules:

- `RT-S12-001` must be single and separate.
- `RT-S12-002` + `RT-S12-003` may be combined only after `RT-S12-001` is
  accepted, and only if E2E evidence and documentation updates are kept clearly
  separated.
- Bootstrap is not combined with implementation.

### Residual Risks Inherited From Stage 11

- Legacy compatibility pages still contain internal terms and legacy
  implementation details；blocking for `RT-S12-001` until each page is deleted,
  redirected, hidden, or explicitly retained read-only with reason.
- Stage 2 migration report files and historical PromptRun evidence may be absent
  in some environments；non-blocking only if Stage 12 preserves evidence paths
  and continues truthful `partial` / `unavailable` presentation.
- `DatasetSnapshot` still lacks independent persisted `captured_at` / `slot`
  columns；non-blocking unless Stage 12 attempts to change data-time schema.
- Browser E2E and full all-repo lint were not run in Stage 11；blocking for final
  Stage 12 Gate unless replaced by documented scoped evidence and accepted
  residual risk.
- Stage 10 OpenAPI response-schema assertions partial；Stage 12 Gate must include
  full or targeted contract review.
- `/strategies/after-close` compatibility route remains；blocking for
  `RT-S12-001` unless explicitly retained read-only with reason.

### Bootstrap Outputs

- Created `docs/refactor-implementation-plans/stage-12-implementation-plan.md`.
- Created `docs/refactor-implementation-logs/stage-12.md`.
- Updated `docs/Refactor-Implementation-Log.md`.

### Verification

- Documentation-only diff review：pass；changed files are limited to Stage 12
  plan/log and the main implementation log.
- No production code changed：pass；diff/status review shows only docs files.
- Stage 11 Gate and accepted tasks verified from Stage 11 log：pass.
- Stage 12 not previously started verified from main log, Stage 11 log, and
  absence of Stage 12 plan/log before edits：pass.
- `git diff --check`：pass.

### Bootstrap Decision

`Stage 12 Bootstrap READY`

Next allowed action：wait for explicit user authorization for
`RT-S12-001 旧入口退役` only. Do not start `RT-S12-002`、`RT-S12-003` or final
E2E/documentation work automatically.

## RT-S12-002 Minimal Canonical Evidence Repair 5.5

Date: 2026-06-24

Status: `[!] 阻塞`

Readiness decision: `STILL_BLOCKED`

Entry verification:

- Stage 11 Gate: `ACCEPTED`
- Stage 12 Bootstrap: `READY`
- RT-S12-001: `ACCEPTED`
- RT-S12-002 implementation: not started
- RT-S12-003: not started
- Stage 12 Gate: not started
- latest readiness repair review: `READINESS_REPAIR_ACCEPTED_WITH_RESIDUAL_BLOCKERS`
- previous preflight status: `PARTIAL_READY`

Repair scope:

- reused the selected five existing DB articles; no article corpus recrawl
- no final RT-S12-002 browser E2E
- no RT-S12-003 user documentation
- no Stage 12 Gate
- no LLM generation
- no Kaipan refresh
- bounded AkShare/OHLCV refresh only for `002104.SZ` and `603280.SH`

Records repaired:

- OHLCV:
  - `002104.SZ`: 20 daily rows, `2024-05-06` to `2024-05-31`
  - `603280.SH`: 20 daily rows, `2024-05-06` to `2024-05-31`
- DatasetSnapshot:
  - `680a9e4a-8cb4-4131-8ef0-785031cb670b`, ready, fingerprint `9f56b30c66ca0ca11f53fe0452dd4e31e31ef4826cece9cd071561c2839f7538`
  - `b534d59d-851a-4a78-a32d-af6e71a4e71f`, ready, fingerprint `62bc2a46401cb6ffdf0f734443618079d0fc211c3bafded9e8393de19171d64c`
- MarketSnapshot / MarketRegime:
  - pre-market MarketSnapshot `88aa0f65-0fb8-41fb-aee8-cb8bbdb33a6f`, snapshot id `rt-s12-002:2024-05-31:09-25:selected-symbols`, quality `partial`
  - pre-market MarketRegime `a8c2d82f-8db9-41ad-aec7-4c79f42c701f`, regime id `rt-s12-002:2024-05-31:09-25:selected_symbol_resilient`, quality `partial`
  - post-close MarketSnapshot `9646ace9-a755-485d-89f4-4900602bde30`, snapshot id `rt-s12-002:2024-05-31:17-30:selected-symbols`, quality `partial`
  - post-close MarketRegime `f9084b48-020a-4493-84a0-f2994e7dbccf`, regime id `rt-s12-002:2024-05-31:17-30:selected_symbol_resilient`, quality `partial`
- RuleVersion:
  - `8d15ae78-4abb-40ef-9a6e-184bb7289d0c`
  - source candidate `af289b09-d9f1-44e1-8ce3-dfd87c84322d`
  - lifecycle `in_review`
  - not published

Blocker:

- `BacktestRun` insert fails because PostgreSQL type `backtest_run_status` is absent.
- Alembic reports current/head `2026_06_20_0001`, but the committed migration creates `backtest_runs.status` as `String` while the current ORM maps it to enum `backtest_run_status`.
- Creating that type manually would be a schema change without an applicable committed migration, so the repair stopped instead of fabricating or bypassing canonical evidence.

Not generated:

- `BacktestRun`
- `BacktestResult`
- `RuleApplicabilityProfile`
- `AuthorProfileVersion`
- `StrategyVersion` / published `Strategy`
- `DailyRuleSelection`
- `DailyStrategyInstance`
- `TradingDayPlan`
- `PostMarketReview`
- `OptimizationProposal`

Verification:

- `python -m scripts.web_local env-check`: pass
- `python -m cli.main db-check --config config/app.template.yaml`: pass
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, current/head `2026_06_20_0001`
- `python -m pytest tests/unit/services/test_backtest_application_service.py tests/unit/services/test_rule_applicability_service.py -q`: pass, `22 passed`
- `PATH="${NODE18_BIN}:$PATH" pnpm typecheck`: pass
- `PATH="${NODE18_BIN}:$PATH" pnpm test -- src/app/route-config.test.tsx`: pass, `12 passed`
- `git diff --check`: pass

Next required repair:

- add and apply a committed migration or adjust ORM/schema contract so `BacktestRun.status` can be inserted truthfully.
- after that, rerun the bounded canonical chain from BacktestRun through OptimizationProposal.
- do not start final browser E2E, RT-S12-003, or Stage 12 Gate until this evidence blocker is resolved.

## 2026-06-25 — RT-S12-002 minimal canonical evidence repair resume

Status: `[!] 阻塞`

Readiness decision: `STILL_BLOCKED`

Entry verification:

- `git pull`: already up to date; latest HEAD `85ea013 fix(backtest): align run status schema`
- BacktestRun schema repair decision: `BACKTESTRUN_SCHEMA_REPAIR_ACCEPTED_WITH_RESIDUALS`
- Stage 11 Gate: `ACCEPTED`
- Stage 12 Bootstrap: `READY`
- RT-S12-001: `ACCEPTED`
- RT-S12-002 final browser E2E: not started
- RT-S12-003: not started
- Stage 12 Gate: not started

Baseline evidence reused:

- selected article subset count `5`
- executable article `84558067-1ba1-4248-9700-fd4225be8593`
- executable candidate `af289b09-d9f1-44e1-8ce3-dfd87c84322d`
- candidate fingerprint `32db69f061d899626664245410ce67879746788effbe3a0bd83bfa4e72d704b8`
- OHLCV `002104.SZ` and `603280.SH`: 20 rows each, `2024-05-06` to `2024-05-31`
- DatasetSnapshots `680a9e4a-8cb4-4131-8ef0-785031cb670b` and `b534d59d-851a-4a78-a32d-af6e71a4e71f`: ready
- pre/post MarketSnapshots and MarketRegimes present with quality `partial`

Generated or advanced evidence:

- BacktestRun `ec58660b-7a34-46e3-8744-b2cec0436655`
- BacktestResult `46f17a5c-5895-427f-8b6b-19d309aeafac`
- RuleApplicabilityProfile `012a2a09-ea6a-4e3c-97e6-41a164e01eab` / stable id `33a32c99-31df-4e97-9995-7eb31866812d`, published
- canonical author `4166623f-1689-42c2-bd90-c32dc7804391`
- RuleVersion `8d15ae78-4abb-40ef-9a6e-184bb7289d0c`, published / display state `可用`
- AuthorProfileVersions:
  - method `03167004-d590-463d-837b-07b6ef22e19f`, published, partial
  - rule `b685bc3d-8ef7-4639-8aa7-32e03fb7c0eb`, published, partial
  - validated `5eda537a-e772-4df3-8986-4d646ebf3e23`, published, unresolved / insufficient evidence
- Strategy draft:
  - strategy `15416124-5087-4cbc-998b-ca107423c74b`
  - version `6bbaf1a0-0b97-4254-a9b2-b7d696260849`
  - validation `insufficient_coverage`

Blocker:

- `StrategyCenterService.validate_version` returned `insufficient_coverage`.
- Dataset, market snapshots, backtest, and applicability were bound, but `out_of_sample_state` is `unavailable` and sample coverage is `unknown`.
- Because the strategy did not pass validation, it was not submitted or published.
- DailyRuleSelection, DailyStrategyInstance, TradingDayPlan, PostMarketReview, and OptimizationProposal were not generated.

LLM / provider actions:

- No LLM call.
- No article recrawl.
- No Kaipan refresh.
- No broad OHLCV backfill.
- No final browser E2E.

Code compatibility repairs:

- explicit audit timestamps for rule applicability, author profile, and strategy audit repositories
- `RuleApplicabilityService` serialization fix for review/publish
- audited `publish_formal_profile` transition for downstream consumers

Verification:

- `python -m scripts.web_local env-check`: pass
- `python -m cli.main db-check --config config/app.template.yaml`: pass
- `python -m alembic -c src/db/migrations/alembic.ini current`: pass, current/head `2026_06_20_0001`
- focused backend tests: pass, `4 passed`
- `web` typecheck with Node 18: pass
- `web` route-config test: pass, `12 passed`
- `git diff --check`: pass
- changed-files secret scan: pass

Next allowed action:

- Repair the bounded strategy validation coverage evidence so the strategy can truthfully publish, then resume from Strategy publish through daily/post-close/proposal.
- Do not start final browser E2E, RT-S12-003, or Stage 12 Gate before that chain exists.
