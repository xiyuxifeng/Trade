# Trade Strategy AI 重构实施状态

本文件只保存当前状态、Task 索引、阻塞项、下一步和 Stage 日志链接。

详细历史记录位于：

```text
trade-strategy-ai/docs/refactor-implementation-logs/
```

日志管理规则见：

- [重构实施日志管理规则](refactor-implementation-logs/README.md)

## 当前状态

- 当前 Stage：`Stage 5 基础数据、数据调度与数据质量`
- Stage 状态：`[-] 进行中`
- 当前 Task：`RT-S5-002 Kaipan 数据体系` 已完成。
- 计划：[Stage 5 实施计划](refactor-implementation-plans/stage-5-implementation-plan.md)
- 详细日志：[Stage 5](refactor-implementation-logs/stage-5.md)
- 下一步：可开始 `RT-S5-003 调度和系统管理`；不得自动开始，需用户明确授权。

## 当前阻塞项

- 当前无 Stage 5 Bootstrap blocker。
- Stage 2 Gate 最终 `ACCEPTED`。
- Stage 3 Bootstrap 已复核 canonical writer effective true、legacy writer rejection 和 no dual-write；当前无 Bootstrap blocker。
- RT-S3-001 已接受；Stage 3 canonical Prompt registry、Pydantic Schema、Prompt runtime foundation 和 canonical PromptRun/ArticleStructure/RuleCandidate 写入已建立。
- RT-S3-002 provenance repair 已接受；human-review/RuleVersion/canonical-writer 工作保留，summary 与 ArticleStructure provenance 已补齐。
- RT-S3-003 已接受；固定 12 篇 regression set、bulk gate 和可恢复 dry-run batch 已建立。
- RT-S3-004 已接受；legacy Prompt 已删除，历史读取兼容、fixed-set compatibility comparison、rollback 与 deletion gate 证据已补齐。
- Stage 3 Gate 最终 `ACCEPTED`；Stage 4 Bootstrap may begin。
- Stage 4 Bootstrap 已完成；Stage 4 范围冻结为 `RT-S4-001`、`RT-S4-002`、`RT-S4-003`。
- Stage 4 执行顺序冻结为：`RT-S4-002` -> `RT-S4-003` -> `RT-S4-001` -> Stage 4 Gate。
- Stage 4 Gate 最终 `ACCEPTED`；Stage 5 Bootstrap may begin after explicit user instruction.
- 2026-06-17 已完成 Stage 4 Pre-Stage-5 cleanup review；异步数据库清理 warning、批量审核原子性、正式变更入口授权和低风险批量合同一致性均已复验并修复/核实。
- 2026-06-17 已完成 Stage 5 Bootstrap；Stage 5 计划、数据/时间/快照合同、兼容/退役边界和执行顺序已冻结。
- 2026-06-17 `RT-S5-001` 已接受；OHLCV/DatasetSnapshot canonical contract 已落地。
- 2026-06-17 `RT-S5-002` 已接受；Kaipan/MarketSnapshot canonical slot、provenance、freeze 与 market-state coverage boundary 已落地。

## Task 状态

| Task | 当前状态 | 实施结论 | 详细记录 |
| --- | --- | --- | --- |
| RT-S0-001 | `[x]` | 现状审计已接受 | [Stage 0](refactor-implementation-logs/stage-0.md) |
| RT-S0-002 | `[x]` | 迁移矩阵已接受 | [Stage 0](refactor-implementation-logs/stage-0.md) |
| RT-S1-001 | `[x]` | 导航和路由实现、回归和用户 UI 检查已接受 | [Stage 1](refactor-implementation-logs/stage-1.md) |
| RT-S1-002 | `[x]` | 统一页面体验、真实能力接入和用户 UI 检查已接受 | [Stage 1](refactor-implementation-logs/stage-1.md) |
| RT-S1-003 | `[x]` | 首页实现、聚焦回归和用户 UI 检查已接受 | [Stage 1](refactor-implementation-logs/stage-1.md) |
| RT-S2-001 | `[x]` | canonical domain contracts、typed refs、lifecycle validator、legacy mapping 与 compatibility adapters 已接受；未改 DB/运行行为 | [Stage 2](refactor-implementation-logs/stage-2.md) |
| RT-S2-002 | `[x]` | Gate 重开后补齐 reused-table frozen fields/FKs、MarketState typed FKs、linear repair migrations；metadata、实际 PostgreSQL、rollback/re-upgrade 与 existing-data preservation 通过 | [Stage 2](refactor-implementation-logs/stage-2.md) |
| RT-S2-003 | `[x]` | Gate 重开后 feature flag 已控制 runtime writer routing；canonical application-service boundary、legacy write rejection、no-dual-write 与 migration isolation tests 通过 | [Stage 2](refactor-implementation-logs/stage-2.md) |
| RT-S3-001 | `[x]` | versioned Prompt registry、Pydantic Schema、single-call/one-repair runtime、cache/idempotency 和 canonical persistence foundation 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S3-002 | `[x]` | human-review/RuleVersion contracts 保留；summary/ArticleStructure provenance repair 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S3-003 | `[x]` | 12 篇 fixed regression set、semantic assertions、gate、recoverable dry-run batch、CLI/readiness evidence 已接受 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S3-004 | `[x]` | legacy Prompt migration / retirement 已接受；Stage 3 Gate 可开始 | [Stage 3](refactor-implementation-logs/stage-3.md) |
| RT-S4-002 | `[x]` | canonical fingerprint/family/runtime、duplicate/variant/conflict detection、source-link provenance、fixed-set gate enforcement、focused API/schema/migration/tests 已接受 | [Stage 4](refactor-implementation-logs/stage-4.md) |
| RT-S4-003 | `[x]` | canonical 规则生命周期、单一路径 transition/audit、idempotency/stale-write 保护、legacy rule_pool 拒写和 focused API/tests 已接受 | [Stage 4](refactor-implementation-logs/stage-4.md) |
| RT-S4-001 | `[x]` | deterministic automatic review、canonical human-review service/router/workbench、batch approve/reject、审计与 fixed-set gate 已接受 | [Stage 4](refactor-implementation-logs/stage-4.md) |
| Stage 5 Bootstrap | `[x]` | Stage 5 范围、数据时间语义、DatasetSnapshot/MarketSnapshot 合同、兼容/退役边界、执行顺序和 RT-S5-001 next prompt 已冻结；未实施生产代码 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| RT-S5-001 | `[x]` | OHLCV canonical identity/time/provenance、calendar-aware gap repair、indicator invalidation boundary、canonical `dataset_snapshots` runtime path 与 immutable snapshot freeze 已接受 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| RT-S5-002 | `[x]` | Kaipan canonical slot/time/provenance、truthful coverage/availability、immutable MarketSnapshot freeze、market-state recompute boundary、compatibility read surfaces 与 migration/test evidence 已接受 | [Stage 5](refactor-implementation-logs/stage-5.md) |
| RT-S5-003 | `[ ]` | 调度和系统管理；数据合同稳定后后置单独执行 | [Stage 5](refactor-implementation-logs/stage-5.md) |

## Stage 状态

| Stage | 状态 | 结论 | 详细记录 |
| --- | --- | --- | --- |
| Stage 0 | `[x]` | 已完成并接受 | [stage-0.md](refactor-implementation-logs/stage-0.md) |
| Stage 1 | `[x]` | 功能、契约、自动验证和用户 UI 检查已接受 | [stage-1.md](refactor-implementation-logs/stage-1.md) |
| Stage 2 | `[x]` | Gate escalation 后 preserve contract；Schema convergence、single-writer runtime routing、migration/recovery 与 compatibility re-review 全部接受 | [stage-2.md](refactor-implementation-logs/stage-2.md) |
| Stage 3 | `[x]` | Gate 最终 `ACCEPTED`；RT-S3-001～RT-S3-004 均保持 accepted，Prompt/article pipeline、fixed regression、recoverable batch、legacy Prompt retirement 和 historical-read compatibility 已验证 | [stage-3.md](refactor-implementation-logs/stage-3.md) |
| Stage 4 | `[x]` | Gate 最终 `ACCEPTED`；RT-S4-001、RT-S4-002、RT-S4-003 均保持 accepted，规则治理、去重/规则族、生命周期、审核工作台、迁移和 legacy 拒写已验证 | [stage-4.md](refactor-implementation-logs/stage-4.md) |
| Stage 5 | `[-]` | Bootstrap accepted；RT-S5-001 and RT-S5-002 accepted；RT-S5-003 pending | [stage-5.md](refactor-implementation-logs/stage-5.md) |

## Stage 1 已接受证据摘要

- 前端全量：`90/90` 个文件、`283/283` 个测试通过。
- TypeScript、ESLint、Vite 生产构建通过。
- 后端受影响套件：`25 passed`；存在 2 条既有异步连接清理 warning。
- 系统状态定向：`4 passed`。
- app factory、唯一入口和 OpenAPI：`5 passed`。
- Web 静态/API 路由优先级：`3 passed`。
- Web E2E：`1 passed`。
- `git diff --check` 通过。
- `/dashboard` 生产引用仅保留在集中兼容配置。
- 未新增数据库迁移、Prompt 或 Stage 2 领域对象。
- 用户已完成 Stage 1 UI 检查并确认可接受。

以上摘要不表示仓库后端全量测试已通过。仓库级后端全量测试曾中止，相关 Stage 1 失败已通过定向套件修复和复验。

## 当前残余风险

- React Router v7 future flag warning 尚未治理，记录为非阻塞技术债。
- 2026-06-16 及更早日志中记录的 async cleanup warning 已在 2026-06-17 Pre-Stage-5 cleanup review 中修复；相关历史条目仅保留为当时 Gate 证据，不再代表当前状态。
- 视觉一致性、非关键响应式细节和文案润色进入 UI backlog，不阻塞 Stage 2。
- Stage 3 legacy article extraction 仍存在，但在 canonical writer enabled 时不能形成正式 Stage 3 formal writer。
- 旧 revision summary 仅在 `ArticleRevision.source_payload` 含 frozen summary 时可展示；否则 API 需 truthful unavailable，不得回退到当前 `BlogArticle.summary`。
- Stage 3 Gate dry-run batch 在 sandbox 内因本地 PostgreSQL socket 权限失败；已按权限流程在外部执行同一命令并通过。该 sandbox 限制不影响 Stage 3 runtime contract。
- Stage 3 Gate 发现 postmortem future-stage Prompt 可被旧 pipeline opt-in 触达；已在 Stage 3 hard-disable future-stage LLM Prompt invocation，保留 deterministic fallback 和 historical read compatibility。
- 后续操作必须保持 canonical writer effective true，不得以关闭 feature flag 恢复 legacy writer。
- Stage 4 Gate 已验证 legacy `rule_pool` / `strategy_studio` / job / CLI review paths 不能绕过 canonical governance；旧 review 写入口保持 compatibility-only 拒写。
- Stage 4 Gate 已修正受影响规则审核页面的普通用户技术词暴露；内部组件/import 名称中仍可能存在 legacy `Regime` 等代码命名，但不作为 Stage 4 普通用户显示文本。
- RT-S4-003 已将 canonical 规则生命周期收口为单一路径：`候选 -> 待审核 -> 已批准 -> 待回测 -> 验证中 -> 可用/限定使用 -> 已停用`。`FormalLifecycleState.approved` 在当前 Stage 仍无可证明用户态映射时返回 truthful unavailable/compatibility-only，不伪造“可用”。
- legacy `rule_pool` / `strategy_studio` UI 与 CLI 写路径已在 RT-S4-003 显式拒绝 formal lifecycle 写入；RT-S4-001 已新增 `/rules/review` 正式审核工作台和 canonical `/api/ui/v1/rule-review` 写路径。
- RT-S4-001 automatic review 使用五状态：`auto_pass`、`recommend_pass`、`manual_review`、`not_backtestable`、`recommend_reject`。其中低风险批量通过只允许 `auto_pass/recommend_pass`，会全批预检后把可回测的新规则推进到 `待回测`；精确重复规则复用既有 RuleVersion 且不重复进入回测；批量驳回只允许 `recommend_reject/not_backtestable`；全部 formal mutation 继续受 fixed-set gate 约束。
- `AI-Conversation-Project-Constraints.md` 单文件不存在；当前权威约束以 `AI-Conversation-Project-Constraints-1.md` 和 `AI-Conversation-Project-Constraints-2.md` 为准。
- Stage 5 Bootstrap 冻结：`DatasetSnapshot` formal source is `dataset_snapshots`；`market_datasets` is compatibility read-only under canonical writer routing；`MarketSnapshot` formal source is `market_snapshots` and child tables；missing data must remain truthful and must not become false/zero/success.
- Stage 5 Bootstrap 冻结：`RT-S5-001` -> `RT-S5-002` -> `RT-S5-003` -> Stage 5 Gate；`RT-S5-003` must not start until data contracts stabilize；Stage 6 backtest execution remains out of scope.

## 2026-06-17 Stage 5 Bootstrap

- Task ID：`Stage 5 Bootstrap`
- 状态：`[x] 已完成`
- 修改范围：`docs/refactor-implementation-plans/stage-5-implementation-plan.md`、`docs/refactor-implementation-logs/stage-5.md`、`docs/Refactor-Implementation-Log.md`
- 关键决定：
  - Stage 5 task order 冻结为 `RT-S5-001` -> `RT-S5-002` -> `RT-S5-003` -> Gate。
  - `RT-S5-001` 与 `RT-S5-002` 可以在同一 Parent session 中分 acceptance batch 执行；`RT-S5-003` 后置且单独执行。
  - Stage 5 time contract 区分 `trade_date`、event/source/captured/ingested/available time，并要求 `Asia/Shanghai` 调度语义和无未来数据泄漏。
  - `DatasetSnapshot` formal source 为 `dataset_snapshots`；`market_datasets` 仅 compatibility read-only。
  - `MarketSnapshot` formal source 为 `market_snapshots` 及 child tables。
  - OHLCV missing numeric data 不得继续默认为 0；必须进入 validation/quality/rejection path。
  - 正式用户表面必须使用业务中文；调度和作业系统保留为内部执行基础设施。
- 数据库迁移：Bootstrap 未新增迁移；计划识别 RT-S5-001/002 需要新增 OHLCV provenance/time/quality、canonical DatasetSnapshot runtime path、coverage/repair、Kaipan provenance/coverage 和 snapshot immutability 相关迁移。
- 兼容处理：保留 legacy `/market*`、`/api/ui/v1/kaipan/*`、`/api/ui/v1/market/ohlcv/*`、legacy snapshot routes、`market_universe` files、`market_datasets` view、technical Job/Workflow/Pipeline/Artifact routes 为 compatibility-only until retirement evidence.
- 已运行测试：未运行测试；Bootstrap 为 analysis and planning only。
- 测试结果：不适用。
- 未完成项：`RT-S5-001`、`RT-S5-002`、`RT-S5-003` 均未开始。
- 已知风险：
  - OHLCV 当前实现仍存在 missing numeric -> zero 风险，需 RT-S5-001 修复。
  - DatasetSnapshot runtime 仍混用 `MarketDataset` compatibility read path，需 RT-S5-001 收敛。
  - 调度/系统管理入口仍分散，需 RT-S5-003 在数据合同稳定后收口。
  - Web compatibility body copy 仍有技术词暴露，需 RT-S5-003 修复。
- 验收结论：Bootstrap `READY`；`RT-S5-001` 可在用户明确授权后开始；不得自动开始。

## 2026-06-17 RT-S5-001 OHLCV 数据体系

- Task ID：`RT-S5-001`
- 状态：`[x] 已完成`
- 修改范围：`src/models/ohlcv_bar.py`、`src/market_data/ohlcv_service.py`、`src/models/stage2_canonical.py`、`src/db/repositories/dataset_snapshot_repository.py`、`src/db/repositories/__init__.py`、`src/services/dataset_snapshot_service.py`、`src/services/market_service.py`、`src/services/market_snapshot_query_service.py`、`cli/ohlcv.py`、`src/pipeline/tasks/ohlcv_crawl_task.py`、`src/db/migrations/versions/2026_06_17_0008_stage5_ohlcv_contract.py`、相关 unit/api/frontend tests、Stage 5 docs/logs。
- 关键决定：
  - OHLCV canonical identity 固定为 `symbol + exchange + asset_type + frequency + adjustment_policy + trade_date`；股票/指数/ETF 不得共用同一 formal identity。
  - `trade_date` 使用 `Asia/Shanghai` 交易日语义；`event_time` 固定为当日 15:00 CST 对应 UTC，`available_at` 固定为当日 17:00 CST 对应 UTC；`source_time` 缺失时保留缺失并记录 `provider_time_unavailable`。
  - 缺失或非法 OHLCV 数值显式拒绝；不得默认成 `0`、`false`、`ready` 或 success。
  - provider duplicate rows 按 canonical payload fingerprint 去重；同一 identity 冲突 payload 直接报错，不伪造“成功写入”。
  - 历史回灌、增量更新与 repair 均保持 idempotent；仅在 canonical payload 真正变化时更新行并触发后续指标缓存失效边界。
  - 指标边界采取 truthful invalidation：当某 symbol 的 OHLCV 从某交易日起被修复后，删除该交易日及之后的 `indicators` 缓存，留待后续正式读取按 canonical OHLCV 重算；不在 RT-S5-001 内扩展到 Stage 6 回测执行。
  - `DatasetSnapshot` formal runtime path 已切到 `dataset_snapshots` repository/service；formal key 为 `content_fingerprint`，`logical_dataset_id`/`dataset_id` 仅作 compatibility mapping。
  - frozen `DatasetSnapshot` 不做原地修改；同内容 rerun 复用既有 snapshot，不同内容生成新 fingerprint/new snapshot。
- 数据库迁移：新增 `src/db/migrations/versions/2026_06_17_0008_stage5_ohlcv_contract.py`，补齐 OHLCV provenance/time/identity 字段，回填 legacy 数据，替换唯一约束，并在 downgrade 会导致 canonical identity 塌缩时显式拒绝降级。
- 兼容处理：
  - `market_datasets` 保持 compatibility-only；用户可见 dataset 浏览仍走原有 `/market/datasets` 页面，但后端读取已切换到 canonical `dataset_snapshots` repository。
  - 现有 OHLCV 抓取、CLI、pipeline task 和 Web 工作台继续保留入口，只增加 canonical snapshot freeze 和 truthful dataset metadata。
- 已运行测试：
  - `../.venv/bin/python -m pytest tests/unit/cli/test_ohlcv.py tests/unit/pipeline/test_ohlcv_crawl_task.py tests/unit/models/test_ohlcv_bar.py tests/unit/market_data/test_ohlcv_service.py tests/unit/db/repositories/test_dataset_snapshot_repository.py tests/unit/services/test_market_snapshot_query_service.py tests/unit/services/test_dataset_snapshot_service.py tests/unit/services/test_snapshot_market_service.py tests/unit/db/test_migrations.py tests/api/routers/test_market_ui.py -q`
  - `pnpm test -- src/pages/market/datasets/index.test.tsx src/pages/market/index.test.tsx src/lib/api/market.test.ts`
  - `pnpm typecheck`
  - `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - `../.venv/bin/python -m compileall src api cli`
  - `git diff --check`
- 测试结果：
  - Focused backend/API/database/CLI/job/migration suite：`51 passed`
  - Frontend targeted suite：`10 passed`
  - TypeScript：passed
  - Stage 3 fixed-set regression：`passed`
  - `compileall`：passed
  - `git diff --check`：passed
- 未完成项：
  - `RT-S5-002` Kaipan 数据体系未开始。
  - `RT-S5-003` 调度与系统管理正式收口未开始。
- 已知风险：
  - 本次 migration 证据以迁移定义测试、upgrade/downgrade 守卫逻辑和 existing-data backfill 代码审查为主，未在本 session 内额外跑独立 PostgreSQL 真实 upgrade/downgrade/re-upgrade 回放。
  - Stage 6 当前仍从 DB 读取 OHLCV 并按需计算指标；本任务只交付其所需 canonical data contract，不包含 Stage 6 runtime 切换或 backtest 执行。
  - 当前 Web 仍保留技术型 market workspace/调度页面；普通用户正式“数据与调度”入口收口属于 `RT-S5-003`。
- 验收结论：`RT-S5-001 ACCEPTED`。OHLCV canonical identity/time/provenance、calendar-aware repair、truthful availability、indicator invalidation boundary、immutable DatasetSnapshot freeze、canonical dataset runtime path 与受影响回归验证均满足当前 Stage 5 冻结合同；`RT-S5-002` 可在新 acceptance batch 中开始，但不得自动开始。

## 2026-06-17 RT-S5-002 Kaipan 数据体系

- Task ID：`RT-S5-002`
- 状态：`[x] 已完成`
- 修改范围：`src/models/market_snapshot.py`、`src/models/market_data_snapshot.py`、`src/models/market_data_snapshot_section.py`、`src/services/market_snapshot_builders.py`、`src/services/market_snapshot_service.py`、`src/services/market_data_storage_service.py`、`src/db/repositories/market_snapshot_repository.py`、`src/db/repositories/market_snapshot_section_repository.py`、`src/services/market_regime_service.py`、`src/models/__init__.py`、`src/db/migrations/versions/2026_06_17_0009_stage5_kaipan_contract.py`、相关 unit/api/frontend tests、Stage 5 docs/logs。
- 关键决定：
  - Kaipan canonical slot 固定为 `09-25`（盘前）和 `17-30`（盘后）；两者形成不同 formal snapshot identity，不得合并或互相覆写。
  - `MarketSnapshot` formal source 继续为 `market_snapshots` 及 child tables；formal identity 改为 `content_fingerprint` + immutable `snapshot_id`，允许同一 `trade_date/slot` 在内容变化时形成新 frozen version。
  - `MarketSnapshotSection` 与 snapshot 主记录显式记录 `source_time`、`captured_at`、`ingested_at`、`available_at`、`trade_date`、`slot`、`source_dataset`、`raw_payload_fingerprint`、`normalization_version`；缺失/历史 unavailable 不伪造时间。
  - canonical payload 会移除 `fetched_at` 这类 rerun 易变字段，保证 normalization/freeze fingerprint deterministic；同内容 rerun 复用同一 frozen snapshot identity。
  - 历史 Kaipan 不可得时保持 `unavailable/missing/partial` truthful semantics，不合成历史盘前/盘后内容，不把缺失 Kaipan 转成 `false`、`0`、`ready` 或 satisfied rule condition。
  - `market_datasets` compatibility write 继续拒绝；legacy/file snapshot paths 保留 compatibility-only，formal runtime source 不回退。
  - market-state recompute 继续绑定 canonical snapshot + OHLCV/indicator coverage；当 snapshot coverage 不足时，feature/regime 构建维持 truthful `partial`/warning，而不是伪造 ready。
- 数据库迁移：新增 `src/db/migrations/versions/2026_06_17_0009_stage5_kaipan_contract.py`，补齐 `market_snapshots`/`market_snapshot_sections` 的 slot/provenance/freeze 字段，移除会阻塞 versioned snapshot 的 `(market, trade_date, slot, data_version)` 唯一约束，并在 downgrade 会塌缩 frozen version 时显式拒绝。
- 兼容处理：
  - `market_datasets` 继续 compatibility read-only；相关 repository tests 已切到拒写预期。
  - file-based snapshot 路径仍保留给 compatibility loader/UI，但 formal snapshot freeze 语义由 DB canonical records 承担。
  - 现有 `/api/ui/v1/kaipan/*`、market workspace、snapshot browser 和 legacy snapshot routes 保持入口，只修复为 truthful slot/coverage/readiness 表达。
- 已运行测试：
  - `../.venv/bin/python -m pytest tests/unit/models/test_market_snapshot.py tests/unit/providers/test_kaipan_provider.py tests/unit/providers/test_kaipan_normalizer.py tests/providers/test_kaipan_scheduler.py tests/providers/test_kaipan_pipeline.py tests/unit/services/test_market_snapshot_builders.py tests/unit/services/test_market_snapshot_registry.py tests/unit/services/test_market_snapshot_service.py tests/unit/services/test_market_data_storage_service.py tests/unit/services/test_market_snapshot_query_service.py tests/unit/services/test_market_regime_feature_service.py tests/unit/services/test_market_regime_service.py tests/unit/services/test_snapshot_market_service.py tests/unit/services/test_kaipan_dashboard_service.py tests/api/routers/ui/test_kaipan.py tests/api/routers/test_ui_snapshots.py tests/api/routers/test_market_ui.py tests/unit/db/repositories/test_market_data_repositories.py tests/unit/db/test_migrations.py -q`
  - `pnpm vitest run src/features/market-workspace/market-workspace-shell.test.tsx src/pages/market/snapshots/index.test.tsx src/pages/market/index.test.tsx`
  - `pnpm typecheck`
  - `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - `../.venv/bin/python -m compileall src api cli`
  - `git diff --check`
- 测试结果：
  - Focused backend/API/provider/database/migration/market-state suite：`119 passed`
  - Frontend targeted suite：`14 passed`
  - TypeScript：passed
  - Stage 3 fixed-set regression：`{"status":"passed","article_count":12,"processed_count":12,"validation_failures":[]}`
  - `compileall`：passed
  - `git diff --check`：passed
- 未完成项：
  - `RT-S5-003` 调度与系统管理正式收口未开始。
  - Stage 6 backtest execution / rule applicability 仍未开始。
- 已知风险：
  - 本次 migration 证据仍以 migration-definition tests、downgrade guard、sqlite runtime path 与 code review 为主；未在本 session 内额外执行独立 PostgreSQL upgrade/downgrade/re-upgrade operational replay。
  - raw Kaipan 历史可用性仍受 provider/credential/network 限制；本批 acceptance 以 deterministic fixtures/fake providers 验证合同，不代表外部 provider 对所有历史日期都可 operational 成功。
  - formal normal-user 数据与调度入口收口仍属于 `RT-S5-003`；当前 Web 仍保留 admin/compatibility technical surfaces。
- 验收结论：`RT-S5-002 ACCEPTED`。Kaipan canonical slot/time/provenance、truthful historical availability、idempotent freeze/retry/rerun、immutable versioned `MarketSnapshot`、market-state truthful degradation、compatibility-only legacy paths 与受影响回归验证满足当前 Stage 5 冻结合同；`RT-S5-003` 可在新 acceptance batch 中开始，但不得自动开始。

## 2026-06-17 Stage 4 Pre-Stage-5 Cleanup Review

- Task ID：`Stage 4 Pre-Stage-5 Cleanup Review`
- 状态：`[x] 已完成`
- 修改范围：`config/database.py`、`api/app.py`、`src/services/rule_review_service.py`、`src/services/rule_lifecycle_service.py`、`api/routers/ui/rule_pool.py`、`api/routers/ui/strategy_studio.py`、相关 Stage 4 API/integration tests、Stage 4 日志。
- 关键决定：
  - 缓存 async engine 必须在应用 shutdown 时显式 `dispose`，不能把 asyncpg 连接清理留给解释器/事件循环收尾。
  - `approve_low_risk` / `reject_invalid` 必须在单个事务单元内执行，且批内每项在写入时重新校验资格，不能只依赖批前预检。
  - `/api/ui/v1/rule-review`、`/api/ui/v1/rule-lifecycle` 以及兼容 `rule-pool` / `strategy-studio` 正式变更入口均要求 `operator+`。
  - 低风险批量合同保持为：新规则进入 `待回测`；精确重复复用既有 `RuleVersion` 且不重复进入回测；不伪造验证/可用/发布语义。
- 数据库迁移：无新增迁移。
- 兼容处理：保留 legacy `rule-pool` / `strategy-studio` 写入口为 compatibility-only，同时新增 operator 授权拦截，拒绝在拒写逻辑之前触达服务。
- 已运行测试：
  - `../.venv/bin/python -m pytest tests/integration/test_stage4_rule_governance.py tests/integration/test_stage4_rule_lifecycle.py tests/integration/test_stage4_rule_review.py tests/api/routers/test_rule_lifecycle.py tests/api/routers/test_rule_review.py tests/api/routers/test_rule_pool.py tests/api/routers/ui/test_strategy_studio.py tests/unit/services/test_rule_governance_service.py tests/unit/db/test_stage4_rule_governance_migration.py tests/unit/cli/test_rule_pool_cli.py tests/api/test_api_app_factory.py tests/api/test_ui_openapi_contract.py -q`
  - `../.venv/bin/python -m pytest tests/unit/services/test_stage2_writer_routing.py tests/regression/stage3 tests/unit/stage3 tests/integration/test_stage3_single_article.py tests/integration/test_stage3_batch.py tests/integration/test_stage3_legacy_compatibility.py tests/api/routers/ui/test_article_metadata.py tests/unit/services/test_optimize_rule_pool_service.py -q`
  - `../.venv/bin/python -m cli.main stage3-regression run --fixed-set`
  - `PYTHONASYNCIODEBUG=1 PYTHONTRACEMALLOC=1 ../.venv/bin/python -W error::RuntimeWarning -m pytest tests/api/test_ui_openapi_contract.py tests/api/test_api_app_factory.py::test_app_lifespan_disposes_cached_engine_on_shutdown -q` repeated 3 times
  - `pnpm test -- src/pages/rules/review.test.tsx src/pages/rule-pool/index.test.tsx`
  - `pnpm typecheck`
  - `../.venv/bin/python -m compileall src api cli`
  - `git diff --check`
- 测试结果：
  - Stage 4 focused governance/API/CLI/migration/auth suite：`41 passed`
  - Affected Stage 3/4 regression suite：`43 passed`
  - Stage 3 fixed-set gate：`passed`
  - RuntimeWarning diagnostic repeat：`3/3` runs passed with no `Connection._cancel` warning
  - Frontend targeted tests：`5 passed`
  - TypeScript、compileall、`git diff --check`：passed
- 未完成项：无。
- 已知风险：
  - 当前结论基于本地可访问 PostgreSQL/asyncpg 与 targeted regression evidence；仓库全量后端测试未在本次 bounded review 中重跑。
  - React Query 测试仍输出既有 query-data warning，不属于本次 Stage 4 formal contract。
- 验收结论：Stage 4 `ACCEPTED` 保持不变；Pre-Stage-5 cleanup review 结论为 verified and fixed；Stage 5 Bootstrap 仍需用户明确授权后方可开始。

## 日志读取规则

新 Session 或恢复任务时：

1. 先读本文件。
2. 读取 Stage 5 计划和详细日志。
3. 再读当前 Task Card、上游 handoff、当前 `git status` 和完整 diff。
4. 不默认读取已完成 Stage 详细日志；仅在 single-writer 证据失效或合同冲突时回读 Stage 2。

同一 Stage 延续时，只读取本文件变化、当前 Stage 日志新增条目和当前 Task 直接相关证据。
