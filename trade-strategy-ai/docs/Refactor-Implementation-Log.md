# Trade Strategy AI 重构实施状态

本文件是重构工作的**当前状态总入口**，只保存当前状态、下一步、硬约束、仍有效风险、Task/Stage 索引和详细日志链接。

详细历史、测试输出、迁移证据、修复记录和 Task 级实施细节请查看：

- [重构实施日志目录](refactor-implementation-logs/README.md)
- [Stage 0 日志](refactor-implementation-logs/stage-0.md)
- [Stage 1 日志](refactor-implementation-logs/stage-1.md)
- [Stage 2 日志](refactor-implementation-logs/stage-2.md)
- [Stage 3 日志](refactor-implementation-logs/stage-3.md)
- [Stage 4 日志](refactor-implementation-logs/stage-4.md)
- [Stage 5 日志](refactor-implementation-logs/stage-5.md)
- [Stage 6 日志](refactor-implementation-logs/stage-6.md)
- [Stage 7 日志](refactor-implementation-logs/stage-7.md)
- [Stage 8 日志](refactor-implementation-logs/stage-8.md)
- [Stage 9 日志](refactor-implementation-logs/stage-9.md)
- [Stage 10 日志](refactor-implementation-logs/stage-10.md)
- [Stage 11 日志](refactor-implementation-logs/stage-11.md)
- [Stage 12 日志](refactor-implementation-logs/stage-12.md)
- [RT-S12-002 reference-chain boundary](refactor-implementation-logs/rt-s12-002-reference-chain-boundary.md)
- [RT-S12-002 Browser E2E Acceptance](refactor-implementation-logs/rt-s12-002-browser-e2e.md)

## 当前状态

- 当前 Stage：`Stage 12 旧入口退役与最终交付`
- Stage 状态：`[-] RT-S12-001 ACCEPTED；RT-S12-002 RT_S12_002_BROWSER_E2E_ACCEPTED；RT-S12-003 RT_S12_003_USER_DOCS_ACCEPTED；Stage 12 Gate 未开始`
- 当前已接受 Task：`RT-S7-004 画像版本与时间分段`、`RT-S7-001 作者方法画像`、`RT-S7-002 作者规则画像`、`RT-S7-003 作者验证画像`、`RT-S8-001 策略草稿与发布`、`RT-S8-002 策略验证和回滚`、`RT-S8-003 策略优化建议`、`RT-S9-001 自动前置检查`、`RT-S9-002 每日规则选择`、`RT-S9-003 每日策略实例和盘前计划`、`RT-S10-001 信号结果评估`、`RT-S10-002 结构化归因`、`RT-S10-003 优化建议`、`RT-S10-004 盘后用户页面`、`RT-S11-001 系统管理入口`、`RT-S11-002 自动化和恢复`、`RT-S11-003 可观测性和运行追踪`、`RT-S11-004 成本与增量控制`、`RT-S11-005 数据时间语义`、`RT-S11-006 灰度迁移和回滚`、`RT-S11-007 用户友好错误`、`RT-S12-003 用户文档`
- 当前已接受 Stage Bootstrap：`Stage 8 Bootstrap`、`Stage 9 Bootstrap`、`Stage 10 Bootstrap`、`Stage 11 Bootstrap`、`Stage 12 Bootstrap`
- 当前阻塞 Task：无。`RT-S12-002` Browser E2E 已通过正式 UI/API 路径生成 separate final E2E chain；reference-chain records 未计为 final pass evidence。`RT-S12-003` 用户文档已接受。Stage 12 Gate 仍未开始。
- 当前边界：[RT-S12-002 reference-chain boundary](refactor-implementation-logs/rt-s12-002-reference-chain-boundary.md) 已冻结：repair/reference chain 只能作为 pre-E2E smoke/contract evidence，Browser E2E Acceptance 必须通过正式入口生成或 lifecycle-transition 一套 separate final E2E chain，并记录新对象 ID 或新 audit/lifecycle transition。
- 当前计划：[Stage 12 实施计划](refactor-implementation-plans/stage-12-implementation-plan.md)
- 详细日志：[Stage 12](refactor-implementation-logs/stage-12.md)
- 下一步：等待用户明确授权后启动 `Stage 12 Gate`；不得自动启动 Stage 12 Gate。

## 最近实施记录

- Task ID: `RT-S12-003 用户文档`
- 状态: `已完成（RT_S12_003_USER_DOCS_ACCEPTED）`
- 修改范围: `docs/stage-12-user-docs/README.md`、`docs/stage-12-user-docs/Quick-Start.md`、`docs/stage-12-user-docs/User-Manual.md`、`docs/stage-12-user-docs/First-Time-Initialization.md`、`docs/stage-12-user-docs/Daily-Pre-Market-Guide.md`、`docs/stage-12-user-docs/Daily-After-Close-Guide.md`、`docs/stage-12-user-docs/Data-Failure-Handling.md`、`docs/stage-12-user-docs/Admin-Operations-Guide.md`、`docs/stage-12-user-docs/Deployment-Runbook.md`、`docs/README.md`、Stage 12 implementation logs
- 关键设计决定: 以 `web/src/app/route-config.tsx` 和 RT-S12-002 final E2E route sequence 为文档事实依据；普通用户文档仅描述正式业务入口和中文操作；管理员/部署者文档单独标记技术诊断、迁移、备份、恢复、权限、观测和部署运行；部署手册只描述当前系统如何部署运行，不建立新的架构事实源。
- 数据库迁移: 无
- 兼容处理: 旧 `bak/` / `Deprecated/` 文档保留为历史材料；新增正式文档放在 `docs/`，不要求普通用户进入 retired/developer-facing routes。
- 已运行测试: `git diff --check`、formal docs terminology grep、formal docs safety grep、markdown link validation、`python -m scripts.web_local env-check`、`python -m cli.main db-check --config config/app.template.yaml`、`python -m alembic -c src/db/migrations/alembic.ini current`、`python -m alembic -c src/db/migrations/alembic.ini heads`、`web` route-config test
- 测试结果: docs terminology grep no matches；docs safety grep no matches；markdown links ok；env-check redacted output only；DB check `DB OK: 1` after elevated rerun；Alembic current `2026_06_14_0006` and head `2026_06_20_0001` recorded as environment residual; route-config `12 passed`; `git diff --check` passed
- 未完成项: Stage 12 Gate 未开始；full browser E2E 未重跑，沿用 RT-S12-002 final E2E evidence 作为文档路径依据。
- 已知风险: 当前本地数据库不在 migration head，部署者需按 `docs/stage-12-user-docs/Deployment-Runbook.md` 在目标环境执行迁移并确认 head；本任务未改变数据库或运行时。
- 验收结论: `RT_S12_003_USER_DOCS_ACCEPTED`

- Task ID: `RT-S12-002 Browser E2E Acceptance`
- 状态: `已完成（RT_S12_002_BROWSER_E2E_ACCEPTED）`
- 修改范围: `web/tests/e2e/stage12-browser-acceptance.spec.ts`、`web/playwright.config.ts`、`api/routers/ui/formal_backtests.py`、`src/services/backtest_application_service.py`、`src/services/rule_applicability_service.py`、`src/db/repositories/rule_applicability_repository.py`、`src/models/rule_applicability.py`、`src/db/repositories/strategy_repo.py`、focused tests、Stage 12 implementation logs
- 关键设计决定: 通过正式 UI routes 和正式 UI/API endpoints 生成 separate final E2E chain；不把 reference-chain records 计为 final pass evidence；RuleApplicability publish 接入现有 formal service；同一 formal run/result evidence 幂等复用；新 evidence 使用新的 stable applicability id；策略发布维护全局唯一 current formal strategy pointer。
- 数据库迁移: 无
- 兼容处理: 未改变 frozen schema/data-source contract；Playwright Chromium runtime 仅为授权 E2E 安装到本地缓存，未提交；failed attempts 产生的非最终 rows 不计入验收证据。
- 已运行测试: `python -m scripts.web_local env-check`、`python -m cli.main db-check --config config/app.template.yaml`、`python -m alembic -c src/db/migrations/alembic.ini current`、focused backend/API/service tests、`web` typecheck、`web` route-config test、`web` Playwright E2E、`git diff --check`、changed-files secret scan
- 测试结果: Browser E2E `1 passed`；route-config `12 passed`；focused backend/API/service tests passed；DB current/head `2026_06_20_0001`；changed-files secret scan no secret values found
- 已完成项: final E2E ArticleRevision、Prompt/Schema evidence、RuleVersion、BacktestRun/BacktestResult、DatasetSnapshot、MarketSnapshot/MarketState、RuleApplicabilityProfile、AuthorProfileVersions、StrategyVersion publish/current pointer、DailyRuleSelection、DailyStrategyInstance、TradingDayPlan、PostMarketReview 和三类 OptimizationProposal IDs recorded in `rt-s12-002-browser-e2e.md`.
- 未完成项: `RT-S12-003 用户文档` 未开始；Stage 12 Gate 未开始。
- 已知风险: post-close/proposal evidence reflects partial available actuals truthfully; several failed E2E attempts created non-final formal rows and are not counted as final evidence.
- 验收结论: `RT_S12_002_BROWSER_E2E_ACCEPTED`

- Task ID: `RT-S12-002 Reference Chain Completion Repair`
- 状态: `进行中（READY_FOR_RT_S12_002_IMPLEMENTATION；Browser E2E 未开始）`
- 修改范围: `src/services/strategy_center_service.py`、`src/db/repositories/backtest_run_repository.py`、`src/services/pre_market_readiness_service.py`、`src/services/post_close_actuals_service.py`、focused backend tests、Stage 12 implementation logs
- 关键设计决定: 修复 service/repository contract mismatch，读取真实 nested backtest coverage；level-1 market-state coverage 明确使用 `not_required`；禁止未来 dataset snapshot 被选入 backtest；reference chain 只作为 pre-E2E smoke/contract evidence。
- 数据库迁移: 无
- 兼容处理: 未创建 PostgreSQL enum，未变更 frozen validation/publication/schema/data-source contract；保留 reference-chain / final-E2E-chain 分离边界。
- 已运行测试: `python -m scripts.web_local env-check`、`python -m cli.main db-check --config config/app.template.yaml`、`python -m alembic -c src/db/migrations/alembic.ini current`、focused backend aggregate、`web` typecheck、`web` route-config test、`git diff --check`、changed-files secret scan
- 测试结果: backend focused aggregate `73 passed`；route-config `12 passed`；typecheck/pass；DB current/head `2026_06_20_0001`；secret scan no matches
- 已完成项: Strategy validation `passed`；reference StrategyVersion published；reference DailyRuleSelection、DailyStrategyInstance、TradingDayPlan、PostMarketReview、RuleOptimizationProposal、AuthorProfileRevisionProposal 和 StrategyRevisionProposal created.
- 未完成项: Browser E2E Acceptance 未开始；RT-S12-003、用户文档和 Stage 12 Gate 未开始。
- 已知风险: repair/reference records 不能作为 Browser E2E final pass evidence；Browser E2E 必须生成或 lifecycle-transition separate final E2E chain。
- 验收结论: `READY_FOR_RT_S12_002_IMPLEMENTATION`

- Task ID: `RT-S12-002 Reference Chain Boundary Documentation Repair`
- 状态: `已完成（BOUNDARY_DOCUMENTED）`
- 修改范围: `docs/refactor-implementation-logs/rt-s12-002-reference-chain-boundary.md`、`docs/refactor-implementation-logs/README.md`、`docs/Refactor-Implementation-Log.md`
- 关键设计决定: 采用 Strategy B：Repair 生成 reference chain；Browser E2E 必须通过正式入口生成或 transition separate final E2E chain。
- 数据库迁移: 无
- 兼容处理: 无 production code 或 business evidence 变更；仅补齐后续 Prompt / Review 应读取的边界入口。
- 未完成项: Reference Chain Completion Repair 仍需修复 Strategy validation `insufficient_coverage`，并完成 reference Strategy / Daily / PostClose / Proposal 链路。
- 已知风险: 若后续 Browser E2E 误用 reference-chain records 作为 final pass evidence，将无法证明用户链路真实走通；后续 Prompt 必须读取 boundary 文档并记录 E2E 新对象 ID / 新 lifecycle transition。
- 验收结论: `BOUNDARY_DOCUMENTED`

- Task ID: `RT-S12-002 Minimal Canonical Evidence Repair Resume`
- 状态: `阻塞（STILL_BLOCKED）`
- 修改范围: `docs/refactor-implementation-logs/rt-s12-002-preflight.md`、`docs/refactor-implementation-logs/stage-12.md`、`docs/Refactor-Implementation-Log.md`、bounded service/repository compatibility fixes
- 关键设计决定: 原始数据设备上复用 selected article/OHLCV/DatasetSnapshot/MarketSnapshot/MarketRegime baseline，从 BacktestRun 继续推进 reference evidence；未启动 Browser E2E、RT-S12-003 或 Stage Gate。
- 数据库迁移: 无
- 兼容处理: 修复 audit writer explicit timestamps、RuleApplicability publish transition 和 session serialization 问题。
- 已运行测试: `python -m scripts.web_local env-check`、`python -m cli.main db-check --config config/app.template.yaml`、`python -m alembic -c src/db/migrations/alembic.ini current`、targeted backend tests `4 passed`、web `pnpm typecheck`、route-config test `12 passed`、`git diff --check`、changed-files secret scan
- 测试结果: 通过；Alembic current/head `2026_06_20_0001`
- 已完成项: reference BacktestRun、BacktestResult、RuleApplicabilityProfile、published RuleVersion、partial AuthorProfileVersion、Strategy draft。
- 未完成项: Strategy validation `insufficient_coverage` 阻塞 reference Strategy publish；daily/post-close/proposal reference chain 未生成。
- 验收结论: `STILL_BLOCKED`

- Task ID: `RT-S12-002 BacktestRun Schema Compatibility Repair`
- 状态: `已完成（BACKTESTRUN_SCHEMA_REPAIR_ACCEPTED_WITH_RESIDUALS）`
- 修改范围: `src/models/stage2_canonical.py`、`tests/unit/models/test_stage2_canonical_models.py`、`docs/refactor-implementation-logs/stage-12.md`、`docs/Refactor-Implementation-Log.md`
- 关键设计决定: 以已提交 migration-backed schema 为事实源，将 `BacktestRun.status` ORM mapping 从 PostgreSQL enum 改为 `String(32)`；保留 `BacktestRunStatus` 作为 Python/service-layer allowed-value constant
- 数据库迁移: 无；未创建 PostgreSQL enum `backtest_run_status`；未新增 migration
- 兼容处理: 服务层继续写入字符串状态值；读取侧已有 enum-or-string normalizer，不要求 ORM 返回 enum object
- 已运行测试: `pytest tests/unit/models/test_stage2_canonical_models.py::test_backtest_run_status_matches_migration_backed_string_schema tests/unit/services/test_backtest_application_service.py tests/unit/services/test_rule_applicability_service.py -q`、`pytest tests/unit/models/test_stage2_canonical_models.py -q`、`git diff --check`、changed-files secret scan
- 测试结果: focused metadata + requested service tests `23 passed`；model metadata tests `5 passed`；`git diff --check` passed；secret scan no matches
- 未完成项: DB-dependent checks skipped on no-data device；schema repair did not run or alter Minimal Canonical Evidence Repair business evidence
- 已知风险: `RT-S12-002` final acceptance still requires separate canonical evidence repair and browser E2E; legacy rows cannot be counted as final evidence
- 验收结论: ORM no longer requires missing PostgreSQL enum type `backtest_run_status`; no articles/OHLCV/snapshots/business evidence were recreated

- Task ID: `RT-S12-002 Readiness Repair 5.5 Review`
- 状态: `已完成（READINESS_REPAIR_ACCEPTED_WITH_RESIDUAL_BLOCKERS）`
- 修改范围: `web/package.json`、`tests/unit/scripts/test_web_local.py`、`docs/refactor-implementation-logs/rt-s12-002-preflight.md`、`docs/refactor-implementation-logs/stage-12.md`、`docs/Refactor-Implementation-Log.md`
- 关键设计决定: 仅审查并修复 5.4 readiness repair 范围内缺口；不启动 RT-S12-002 browser E2E、RT-S12-003、Stage 12 Gate 或数据/evidence repair
- 数据库迁移: 无
- 兼容处理: 补齐已记录但实际缺失的 Playwright package scripts；Chromium 安装仍 deferred 到后续显式授权的 browser E2E task
- 已运行测试: `python -m pytest tests/unit/scripts/test_web_local.py -q`、`python -m scripts.web_local env-check`、`pnpm typecheck`（Node 18 PATH）、`pnpm test -- src/app/route-config.test.tsx`（Node 18 PATH）、`pnpm exec playwright --version`（Node 18 PATH）、`git diff --check`、changed-files secret scan
- 测试结果: helper 单测 `4 passed`；env-check 仅输出脱敏 set/source；frontend typecheck 通过；route-config test `12 passed`；Playwright version `1.61.1`；`git diff --check` 通过；secret scan 未发现真实 secret
- 未完成项: minimal canonical rule/backtest/applicability/profile/strategy/daily/post-close/proposal chain；sufficient OHLCV / DatasetSnapshot / MarketSnapshot / MarketRegime evidence
- 已知风险: `RT-S12-002` final acceptance 仍需单独 Minimal Canonical Evidence Repair；legacy rows 不能计入最终证据
- 验收结论: `READINESS_REPAIR_ACCEPTED_WITH_RESIDUAL_BLOCKERS`

- Task ID: `RT-S12-002 Readiness Repair`
- 状态: `已完成（PARTIAL_READY）`
- 修改范围: `scripts/web_local.py`、`tests/unit/scripts/test_web_local.py`、`web/package.json`、`web/pnpm-lock.yaml`、`web/playwright.config.ts`、`docs/refactor-implementation-logs/stage-12.md`、`docs/refactor-implementation-logs/rt-s12-002-preflight.md`、`docs/Refactor-Implementation-Log.md`
- 关键设计决定: 仅修复 preflight tooling/runtime blocker；不伪造 canonical downstream evidence；把 5 篇已有 current `article_analysis_v1` 文章冻结为未来 RT-S12-002 子集
- 数据库迁移: 无
- 兼容处理: `scripts/web_local.py` 优先注入本机 Node 18 PATH，改用 `config/app.template.yaml` 作为本地 migrate/worker helper 默认 config，并新增 `env-check` 安全读取 `.env`
- 已运行测试: `python -m pytest tests/unit/scripts/test_web_local.py -q`、`python -m scripts.web_local env-check`、`pnpm typecheck`（Node 18 PATH） 、`pnpm test -- src/app/route-config.test.tsx`（Node 18 PATH）、`pnpm exec playwright --version`（Node 18 PATH）、read-only DB checks、`git diff --check`
- 测试结果: helper 单测 `4 passed`；frontend typecheck 通过；frontend relevant test `12 passed`；Playwright version `1.61.1`；`git diff --check` 通过；preflight 状态提升为 `PARTIAL_READY`
- 未完成项: minimal canonical rule/backtest/applicability/profile/strategy/daily/post-close/proposal chain；sufficient OHLCV / DatasetSnapshot / MarketSnapshot / MarketRegime evidence
- 已知风险: 本地没有可用离线 Kaipan / market-universe seed payload；若不执行最小 live provider / fresh LLM repair，则正式数据 blocker 仍然存在
- 验收结论: bounded readiness repair 已修复 tooling/runtime blocker，但 RT-S12-002 实现前仍需补足真实 canonical data/evidence；详见 `docs/refactor-implementation-logs/rt-s12-002-preflight.md`

- Task ID: `RT-S12-002 Preflight`
- 状态: `阻塞`
- 修改范围: `docs/refactor-implementation-logs/rt-s12-002-preflight.md`、`docs/refactor-implementation-logs/stage-12.md`、`docs/Refactor-Implementation-Log.md`
- 关键设计决定: 以 `config/app.template.yaml` 为唯一 config baseline；database-first 复用现有文章；legacy LLM/backtest 结果只计为 historical evidence，不计为最终 E2E pass evidence
- 数据库迁移: 无
- 兼容处理: 无生产代码改动；仅记录 `config/app.yaml` hard-coded local tooling mismatch
- 已运行测试: `python --version`、backend import check、Node/Pnpm version check、`pnpm typecheck`、`pnpm test`、read-only DB connectivity / counts / provenance / route scans
- 测试结果: `pnpm typecheck` 通过；`pnpm test` 可运行但存在失败；DB 可连且 `alembic_version` 与 migration head 一致；preflight 结论为 `BLOCKED`
- 未完成项: browser E2E tooling、minimal canonical rule/backtest/profile/strategy/daily evidence chain、sufficient OHLCV/DatasetSnapshot/MarketSnapshot/MarketRegime evidence
- 已知风险: `.env` 当前不能安全 shell source；default Node 版本过低；当前 DB 几乎没有 Stage 6–10 canonical evidence
- 验收结论: `RT-S12-002` 实现前置条件未满足，详见 `docs/refactor-implementation-logs/rt-s12-002-preflight.md`

## 当前硬约束

- 后续 Task 不得自动开始；每个 Stage / Task / Gate 都需要用户明确授权。
- legacy internal tooling / Job / Workflow / Pipeline / Artifact / file JSON / `config_path` / live Provider / mutable latest records 不得成为后续 Stage 的 formal data input。
- Stage 6 formal backtest 和 rule applicability 只能消费 canonical DatasetSnapshot、MarketSnapshot、BacktestRun、BacktestResult、RuleApplicabilityProfile 及其 immutable IDs/fingerprints/versions/provenance/availability timestamps。
- Stage 7 正式作者画像分为：`AuthorMethodProfile`、`AuthorRuleProfile`、`AuthorValidatedProfile`。
- Stage 7 三类作者画像必须共享版本、生命周期、审核、审计、证据指纹、画像指纹、supersession 和时间分段规则。
- 正式作者验证画像只能消费 formal `RuleApplicabilityProfile`、formal `BacktestRun`、formal `BacktestResult` 和 Stage 6 level/市场状态/sample evidence。
- 新证据只能生成草稿/修订，不得自动覆盖已发布画像。
- Formal Stage 8 strategy source-of-truth is canonical `StrategyVersion` in `strategy_versions`, scoped by canonical `Strategy` in `strategies`; `TraderStrategyVersion` is compatibility-only.
- Formal Stage 8 strategy contents must include rule pool, rule base weights, author profile versions, risk policy, position constraints, target universe, market-state selection policy, degradation policy and evidence bindings.
- `StrategyVersion` is not regenerated daily.
- `DailyStrategyInstance` is runtime-only and cannot become a formal strategy.
- `StrategyRevisionProposal` is proposal-only and cannot directly modify a published/current strategy.
- Only one current strategy per strategy scope unless a later explicit contract changes the scope rule.
- Rollback must create/audit a version transition and cannot silently mutate history.
- Stage 9 Bootstrap 已冻结：`DailyRuleSelection` 是每日规则选择输出，不是正式策略；`DailyStrategyInstance` 是运行时对象，不是 `StrategyVersion`；`TradingDayPlan` 是用户可见每日计划。
- Stage 9 current formal strategy must be read from canonical `Strategy.current_published_version_id` and its `StrategyVersion` / `StrategyRuleMembership` records.
- Stage 9 formal inputs must be canonical `DatasetSnapshot`、`MarketSnapshot`、`BacktestRun`、`BacktestResult`、`RuleApplicabilityProfile`、`AuthorProfileVersion` and validated data-quality state.
- Stage 9 formal flow must not consume legacy Job / Workflow / Pipeline / Artifact / file JSON / `config_path` / live Provider / mutable latest records / legacy strategy service / legacy backtest service / `strategy-studio` / `optimize` / compatibility views.
- Stage 9 must not modify `StrategyVersion`、published/current strategy pointers、author profiles、rule versions、rule applicability profiles or proposal status.
- Stage 10 Bootstrap 已冻结：`PostMarketReview` 是每日运行证据，不是正式策略；信号结果评估和结构化归因必须 program-fact-first；LLM 只能 bounded validation/explanation。
- Stage 10 proposal 必须分离 `RuleOptimizationProposal`、`AuthorProfileRevisionProposal`、`StrategyRevisionProposal`，不得合成泛化 AI suggestion。
- Stage 10 单日结果不得直接覆盖 `RuleVersion`、`RuleApplicabilityProfile`、`AuthorProfileVersion`、`StrategyVersion`、`Strategy.current_published_version_id`、`DailyRuleSelection`、`DailyStrategyInstance` 或 `TradingDayPlan` source traceability。
- Stage 10 formal flow must not consume legacy Job / Workflow / Pipeline / Artifact / file JSON / `config_path` / live Provider / mutable latest records / legacy post-market reports / `/daily/overview` compatibility job cards.
- `RT-S10-001` contract escalation 已冻结 `Decision 1`：formal canonical post-close actual snapshot source is required and sufficient for signal outcome metrics；approved imported actuals are optional supplement for execution-specific fields only。
- `RT-S10-001` 恢复时优先采用 `post_close_symbol_ohlcv_actuals` canonical `MarketSnapshot` section/item contract，绑定 `DatasetSnapshot.dataset_snapshot_id`、`DatasetSnapshot.content_fingerprint`、row fingerprint、quality/availability state、`frozen_at` / `available_at` 和 per-signal actual rows。
- `RT-S10-002` 已冻结并接受：`PostMarketReview.attribution_json` 必须从 RT-S10-001 已落库 program facts deterministic 生成；formal attribution state 与 six-category classification 分离；LLM gate 仅记录 eligibility，未调用 runtime 时不得写 `prompt_run_id`。
- `RT-S10-003` 已冻结并接受：Stage 10 proposal lane 必须保持 `rule_optimization`、`author_profile_revision`、`strategy_revision` 分离；rule/profile 仅允许 review / continue observing / reject；strategy accept 仅允许 draft-only，且不得修改 `Strategy.current_published_version_id`。
- 不得把 raw `OHLCVBar` mutable latest rows、legacy report payload、raw `trade_logs`、file JSON 或临时 source 当作 formal post-close actuals source。
- Approved imported actuals 不得作为 unexecuted signal close/MFE/MAE/return 的唯一来源，除非另行扩展为覆盖所有 signaled symbols 的 immutable OHLCV actuals contract。
- Stage 11 Bootstrap 已冻结：低频管理能力集中到 System Management，普通用户日常业务页面保持简单。
- Stage 11 System Management groups：Profile 配置、数据源、数据与调度、任务运行、失败与告警、数据库与备份、权限与审计。
- Stage 11 business pages stay outside System Management：`/research`、`/rules`、`/authors`、`/strategies`、`/daily`、`/daily/pre-market`、`/daily/after-close`。
- Stage 11 不得把 legacy Job / Workflow / Pipeline / Artifact 记录变成 formal business input；`config_path` 不得作为 Web formal input 回归。
- Stage 11 missing data must remain unavailable / partial / conflict / invalid / degraded，不得变成 success / false / 0。
- Stage 11 automation 不得静默 publish、overwrite、approve 或 execute user-impacting decisions；用户影响动作必须 notify-only 或 admin approval，除非后续 Task 明确冻结更窄 contract。
- Stage 11 不得通过系统管理绕过已接受的 rule/profile/strategy governance paths，不得直接修改 formal strategy/rule/profile/current pointers。
- Stage 11 不得退役 legacy routes，除非后续 Task 被明确授权；Stage 12 不得从 Stage 11 session 自动开始。
- `AI-Conversation-Project-Constraints.md` 单文件不存在；当前权威约束以 `AI-Conversation-Project-Constraints-1.md` 和 `AI-Conversation-Project-Constraints-2.md` 为准。
- Stage 12 Bootstrap 已冻结：Stage 12 不得创建第二 formal source-of-truth，不得移除 traceability / rollback / audit / prompt history / data provenance / migration recovery 所需证据。
- Stage 12 legacy route retirement 必须先验证对应 new formal entry；普通用户不得看到 developer-tool main entries。
- Stage 12 deletion vs hiding：只有 formal replacement、历史证据访问、引用扫描、测试和 rollback/recovery 条件全部满足时才删除；否则只能隐藏、redirect 或保留 read-only compatibility，并在 Stage 12 log 记录剩余退役条件。
- Stage 12 E2E 必须走通正式路径：文章导入 → 提取规则 → 审核规则 → 回测 → 生成规则适用性 → 生成作者画像 → 发布策略 → 生成盘前计划 → 完成盘后复盘 → 生成优化建议。
- Stage 12 RT-S12-002 采用 reference-chain / final-E2E-chain 分离边界：repair/reference chain 不得直接计为 Browser E2E final pass evidence；Browser E2E 必须通过正式入口生成或 lifecycle-transition separate final E2E chain，并记录新对象 ID 或新 audit/lifecycle transition。
- Stage 12 用户文档必须面向普通用户，不要求理解 Job / Workflow / Pipeline / Artifact / Provider / Schema / config_path / prompt_run_id / run_id。

## 当前残余风险

- Stage 8 Gate 最终 `ACCEPTED`；`RT-S8-001/002/003` 已接受，策略中心 Stage 已完成。
- Stage 9 Gate 最终 `ACCEPTED`；`RT-S9-001/002/003` 已接受。
- Stage 10 Gate 已于 2026-06-22 最终 `ACCEPTED`；Stage 11 Gate 已于 2026-06-23 最终 `ACCEPTED`。
- Stage 12 Bootstrap 已于 2026-06-23 `READY`；`RT-S12-001` 已于 2026-06-23 `ACCEPTED`。
- RT-S12-002 reference chain 已完成 pre-E2E smoke/contract evidence；Browser E2E 已生成 separate final E2E chain，reference-chain records 未计为 final pass evidence。
- Browser E2E 已通过正式 UI/API 路径；下一步仍需用户明确授权后进入 `RT-S12-003 用户文档`，不得自动启动 Stage 12 Gate。
- legacy compatibility source / admin diagnostics / historical docs 仍包含 internal terms；普通用户正式入口不得暴露 legacy main entries。
- UI 视觉一致性、非关键响应式细节和文案润色进入 backlog，不阻塞当前 Stage。

## Task 状态索引

| Task | 状态 | 简短结论 | 详细记录 |
| --- | --- | --- | --- |
| RT-S0-001 | `[x]` | 现状审计已接受 | [Stage 0](refactor-implementation-logs/stage-0.md) |
| RT-S0-002 | `[x]` | 迁移矩阵已接受 | [Stage 0](refactor-implementation-logs/stage-0.md) |
| RT-S1-001 | `[x]` | 导航和路由实现已接受 | [Stage 1](refactor-implementation-logs/stage-1.md) |
| RT-S1-002 | `[x]` | 统一页面体验和真实能力接入已接受 | [Stage 1](refactor-implementation-logs/stage-1.md) |
| RT-S1-003 | `[x]` | 首页实现已接受 | [Stage 1](refactor-implementation-logs/stage-1.md) |
| RT-S2-001 | `[x]` | canonical domain contracts 已接受 | [Stage 2](refactor-implementation-logs/stage-2.md) |
| RT-S2-002 | `[x]` | schema convergence 和 migration/recovery 已接受 | [Stage 2](refactor-implementation-logs/stage-2.md) |
| RT-S2-003 | `[x]` | canonical writer routing 与 legacy write rejection 已接受 | [Stage 2](refactor-implementation-logs/stage-2.md) |
| RT-S3-001 | `[x]` | versioned Prompt registry 与 canonical persistence foundation 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S3-002 | `[x]` | provenance repair 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S3-003 | `[x]` | fixed regression set 和 recoverable dry-run batch 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S3-004 | `[x]` | legacy Prompt migration / retirement 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S4-001 | `[x]` | automatic review 与 human-review workbench 已接受 | [Stage 4](refactor-implementation-logs/stage-4.md) |
| RT-S4-002 | `[x]` | fingerprint/family/runtime 与 duplicate/conflict detection 已接受 | [Stage 4](refactor-implementation-logs/stage-4.md) |
| RT-S4-003 | `[x]` | canonical rule lifecycle 已接受 | [Stage 4](refactor-implementation-logs/stage-4.md) |
| Stage 5 Bootstrap | `[x]` | Stage 5 data contracts 和 task order 已冻结 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| RT-S5-001 | `[x]` | OHLCV DatasetSnapshot canonical contract 已接受 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| RT-S5-002 | `[x]` | Kaipan/MarketSnapshot canonical contract 已接受 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| RT-S5-003 | `[x]` | 系统管理数据与调度门面已接受 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| Stage 6 Bootstrap | `[x]` | Stage 6 backtest/applicability contracts 已冻结 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| RT-S6-001 | `[x]` | formal backtest workbench foundation 已接受 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| RT-S6-002 | `[x]` | point-in-time market-state results 已接受 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| RT-S6-003 | `[x]` | RuleApplicabilityProfile 草稿/版本和审核已接受 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| RT-S6-004 | `[x]` | Level 1/2/3 backtest levels 已接受 | [Stage 6](refactor-implementation-logs/stage-6.md) |
| Stage 7 Bootstrap | `[x]` | Stage 7 author profile contracts 和 task order 已冻结 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| RT-S7-004 | `[x]` | 作者画像版本、生命周期、审核审计和时间分段 foundation 已接受 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| RT-S7-001 | `[x]` | 结构化文章批次生成 formal AuthorMethodProfile draft 已接受 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| RT-S7-002 | `[x]` | reviewed RuleVersion / RuleFamily 生成 formal AuthorRuleProfile draft 已接受 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| RT-S7-003 | `[x]` | formal Stage 6 validation evidence 生成 AuthorValidatedProfile draft 已接受 | [Stage 7](refactor-implementation-logs/stage-7.md) |
| Stage 8 Bootstrap | `[x]` | Stage 8 strategy contracts 和 task order 已冻结 | [Stage 8](refactor-implementation-logs/stage-8.md) |
| RT-S8-001 | `[x]` | canonical draft/review/publish foundation、正式策略中心、migration 和 focused verification 已接受 | [Stage 8](refactor-implementation-logs/stage-8.md) |
| RT-S8-002 | `[x]` | canonical validation summary、current-vs-candidate comparison、version diff、audited rollback 和 focused verification 已接受 | [Stage 8](refactor-implementation-logs/stage-8.md) |
| RT-S8-003 | `[x]` | canonical proposal service/API/UI、accept-to-draft traceability 和 focused verification 已接受 | [Stage 8](refactor-implementation-logs/stage-8.md) |
| Stage 9 Bootstrap | `[x]` | Stage 9 pre-market contracts 和 task order 已冻结 | [Stage 9](refactor-implementation-logs/stage-9.md) |
| RT-S9-001 | `[x]` | formal pre-market readiness check、正式 API/UI 和 focused verification 已接受 | [Stage 9](refactor-implementation-logs/stage-9.md) |
| RT-S9-002 | `[x]` | formal daily rule selection、traceability、正式 API/UI 和 focused verification 已接受 | [Stage 9](refactor-implementation-logs/stage-9.md) |
| RT-S9-003 | `[x]` | 每日策略实例和盘前计划、正式计划审核流和 focused verification 已接受 | [Stage 9](refactor-implementation-logs/stage-9.md) |
| Stage 10 Bootstrap | `[x]` | Stage 10 post-market contracts 和 task order 已冻结 | [Stage 10](refactor-implementation-logs/stage-10.md) |
| RT-S10-001 | `[x]` | Option A formal post-close actuals source、signal outcome service/API、bounded repair 和 Parent acceptance review 已接受 | [Stage 10](refactor-implementation-logs/stage-10.md) |
| RT-S10-002 | `[x]` | deterministic structured attribution、LLM gate metadata、focused verification 和 Parent acceptance review 已接受 | [Stage 10](refactor-implementation-logs/stage-10.md) |
| RT-S10-003 | `[x]` | 分离 proposal lane、正式 API、safe review actions 和 focused verification 已接受 | [Stage 10](refactor-implementation-logs/stage-10.md) |
| RT-S10-004 | `[x]` | formal `/daily/after-close` 页面、盘后聚合读取接口、建议动作面板和 focused verification 已接受 | [Stage 10](refactor-implementation-logs/stage-10.md) |
| Stage 11 Bootstrap | `[x]` | Stage 11 system management / automation / observability / time / cost / rollback / error contracts 和 task order 已冻结 | [Stage 11](refactor-implementation-logs/stage-11.md) |
| RT-S11-001 | `[x]` | 正式 `/system` 入口、七类管理分组、兼容映射和可见性验证已接受 | [Stage 11](refactor-implementation-logs/stage-11.md) |
| RT-S11-002 | `[x]` | 有界自动化/恢复、审批 gate、失败证据保留和 traceability 已接受 | [Stage 11](refactor-implementation-logs/stage-11.md) |
| RT-S11-003 | `[x]` | bounded run-trace service/API/UI、daily source_run_id persistence 和 focused verification 已接受 | [Stage 11](refactor-implementation-logs/stage-11.md) |
| RT-S11-004 | `[x]` | 成本与增量控制 contracts、管理员 API/UI 和 focused verification 已接受 | [Stage 11](refactor-implementation-logs/stage-11.md) |
| RT-S11-005 | `[x]` | 盘前/盘后 cutoff enforcement、truthful late-data handling 和系统管理时间字段可见性已接受 | [Stage 11](refactor-implementation-logs/stage-11.md) |
| RT-S11-006 | `[x]` | rollout state、rollback/recovery evidence、batch recovery metadata 和 system UI/API 已接受 | [Stage 11](refactor-implementation-logs/stage-11.md) |
| RT-S11-007 | `[x]` | 用户友好错误、共享错误契约和 Stage 11 focused verification 已接受 | [Stage 11](refactor-implementation-logs/stage-11.md) |
| Stage 12 Bootstrap | `[x]` | Stage 12 retirement/final delivery contracts、task order、acceptance criteria 和 residual risk classification 已冻结 | [Stage 12](refactor-implementation-logs/stage-12.md) |
| RT-S12-001 | `[x]` | old-entry route retirement and ordinary-user terminology blocker repair 已接受 | [Stage 12](refactor-implementation-logs/stage-12.md) |
| RT-S12-002 | `[x]` | Browser E2E Acceptance 已通过正式 UI/API 路径生成 separate final E2E chain；reference chain 未计为 final pass evidence | [Stage 12](refactor-implementation-logs/stage-12.md) / [Browser E2E](refactor-implementation-logs/rt-s12-002-browser-e2e.md) / [Boundary](refactor-implementation-logs/rt-s12-002-reference-chain-boundary.md) |
| RT-S12-003 | `[x]` | 用户文档、管理员文档和部署与运行手册已接受；匹配 Stage 12 final UI / route/navigation 与 RT-S12-002 final E2E 路径 | [Stage 12](refactor-implementation-logs/stage-12.md) |

## Stage 状态索引

| Stage | 状态 | 结论 | 详细记录 |
| --- | --- | --- | --- |
| Stage 0 | `[x]` | 已完成并接受 | [stage-0.md](refactor-implementation-logs/stage-0.md) |
| Stage 1 | `[x]` | 功能、契约、自动验证和用户 UI 检查已接受 | [stage-1.md](refactor-implementation-logs/stage-1.md) |
| Stage 2 | `[x]` | Gate 最终 `ACCEPTED` | [stage-2.md](refactor-implementation-logs/stage-2.md) |
| Stage 3 | `[x]` | Gate 最终 `ACCEPTED` | [stage-3.md](refactor-implementation-logs/stage-3.md) |
| Stage 4 | `[x]` | Gate 最终 `ACCEPTED` | [stage-4.md](refactor-implementation-logs/stage-4.md) |
| Stage 5 | `[x]` | Gate 最终 `ACCEPTED` | [stage-5.md](refactor-implementation-logs/stage-5.md) |
| Stage 6 | `[x]` | Gate 最终 `ACCEPTED` | [stage-6.md](refactor-implementation-logs/stage-6.md) |
| Stage 7 | `[x]` | Gate 最终 `ACCEPTED` | [stage-7.md](refactor-implementation-logs/stage-7.md) |
| Stage 8 | `[x]` | Gate 最终 `ACCEPTED` | [stage-8.md](refactor-implementation-logs/stage-8.md) |
| Stage 9 | `[x]` | Gate 最终 `ACCEPTED` | [stage-9.md](refactor-implementation-logs/stage-9.md) |
| Stage 10 | `[x]` | Gate 最终 `ACCEPTED` | [stage-10.md](refactor-implementation-logs/stage-10.md) |
| Stage 11 | `[x]` | Gate 最终 `ACCEPTED`；RT-S11-001 / 002 / 003 / 004 / 005 / 006 / 007 已接受 | [stage-11.md](refactor-implementation-logs/stage-11.md) |
| Stage 12 | `[-]` | `RT-S12-001` accepted；`RT-S12-002` Browser E2E accepted；`RT-S12-003` user docs accepted；Stage 12 Gate 未开始 | [stage-12.md](refactor-implementation-logs/stage-12.md) / [Browser E2E](refactor-implementation-logs/rt-s12-002-browser-e2e.md) / [Boundary](refactor-implementation-logs/rt-s12-002-reference-chain-boundary.md) |

## 下一步建议

建议下一次先处理：

```text
Stage 12 next authorized work, only after explicit user approval:
`Stage 12 Gate`：仅在用户明确授权后启动。不得自动启动 Stage 12 Gate。
```

执行前应读取：

- [Stage 12 计划](refactor-implementation-plans/stage-12-implementation-plan.md)
- [Stage 12 日志](refactor-implementation-logs/stage-12.md)
- [RT-S12-002 reference-chain boundary](refactor-implementation-logs/rt-s12-002-reference-chain-boundary.md)
- 本文件的“当前硬约束”和“当前残余风险”

不得自动开始任何后续 Stage 12 工作；必须等待用户明确授权后再进入 `RT-S12-003 用户文档`。
