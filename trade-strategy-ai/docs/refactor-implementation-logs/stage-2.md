# Stage 2 实施记录

## Stage 摘要

- Stage：`Stage 2 领域模型、数据库和版本契约`
- 当前状态：`[ ] 未开始`
- 入口条件：Stage 1 已接受，权威日志允许进入 Stage 2。
- 出口条件：领域、ORM、数据库、API/DTO、迁移和 compatibility 合同一致；旧数据迁移可追溯、可重跑、可恢复；无第二套正式事实源。
- 实施计划：`refactor-implementation-plans/stage-2-implementation-plan.md`
- 下一 Task：`RT-S2-001 定义核心领域对象`

## Bootstrap 记录

### 状态

- Bootstrap 与合同冻结：已完成。
- Stage 实现：未开始。
- `RT-S2-001`：`[ ]`。
- `RT-S2-002`：`[ ]`，等待 `RT-S2-001` 接受。
- `RT-S2-003`：`[ ]`，等待 `RT-S2-002` 接受。

### 委派

- 使用 Parent 单控制器。
- 只读 delegation 判定：无收益，选择 `0` 个 Explorer。
- 实现 delegation：Bootstrap 禁止实现，选择 `0` 个 Executor。
- 未委派领域、Schema、迁移顺序、rollback 或事实源决定。

### Git 与基线

- 分支：`main`。
- 基线：`90ad17ef2265e4e48d0f135dd121e94323872577`。
- `HEAD == origin/main`。
- Bootstrap 开始时工作树与暂存区无差异。
- 未发现需要保护的未提交用户改动。

### Stage 1 入口核验

- 主实施日志与 Stage 1 日志均记录 Stage 1 `[x]`。
- Stage 1 完成导航、统一页面、首页和兼容入口验收。
- Stage 1 明确未实施 Stage 2 对象、迁移或 Prompt。
- Stage 2 允许开始。

### 数据库与实际数据核验

- PostgreSQL：`trade_strategy_ai.public`。
- Alembic head：`2026_06_03_0001`，实际数据库同一版本。
- 实际表：43。
- 关键数据：
  - `raw_articles=131`
  - `blog_articles=131`
  - `article_metadata=262`，每篇 `v1/v2`
  - `article_metadata_selections=7`
  - `rule_pool=14`
  - `ohlcv_bars=84`
  - `backtest_result_runs=0`
  - `market_snapshots=0`
  - `market_regimes=0`
  - `rule_applicability_profiles=0`
  - `trader_strategy_versions=0`
  - `trader_memory=0`
- 131 条 raw article 均可按 `source_url` 对应 blog article，但 `is_processed=false`，迁移时必须标歧义。
- 14 条 RulePool 均有来源文章和内嵌回测；7 approved、7 pending，全部 unmapped。
- 84 条 OHLCV 覆盖 84 个 symbol，但只有 `2026-04-20` 一个交易日，不能解释为完整 DatasetSnapshot。

### Alembic/ORM 冲突

- `alembic check` 失败。
- metadata 未完整注册多个现存表，包括 RulePool 相关表和 AlertHistory。
- 存在 JSON/JSONB、索引、constraint、trade_logs 字段漂移。
- ORM 中一个策略唯一约束名超过 PostgreSQL 限制，实际 migration 使用短名。
- 结论：`RT-S2-002` 必须先完成 metadata alignment，任何 autogenerate drop 都必须人工解释。

### 重复事实源

- Article：RawArticle/BlogArticle。
- ArticleStructure/Prompt：ArticleMetadata 混合承担。
- Rule：ArticleMetadata、RulePool、Persona、Strategy snapshot。
- Backtest：RulePool JSON、BacktestResultRun、Job/Artifact/文件。
- MarketSnapshot：同名 dataclass 与 ORM。
- MarketState：Persona Pydantic、MarketRegime tables、文件。
- Author profile：TraderProfilesFile、Persona clusters、TraderMemory。
- StrategyVersion：ORM、dataclass、CLI/JSON 和日级语义。
- Pre/post market：报告文件、Markdown、Job result、Artifact。

### 冻结决定

- 数据库是正式业务对象主事实源。
- 文件只作导入、导出、缓存、归档、附件和 compatibility provenance。
- 19 个核心对象的 ID、版本、生命周期、关系、事实源、复用/新增/转换决定见 Stage 2 实施计划。
- 新对象 UUID 使用 `uuid4()`；已有稳定 UUID 保留；legacy 字符串 ID 通过 mapping 表保存。
- 正式版本、runtime instance、Proposal 分离。
- Proposal 接受只能创建 draft，不能覆盖 published 对象。
- PromptRun 保存 prompt/schema/model/input/raw output/validation/token/cost。
- Stage 2 不执行 Prompt、画像、策略、盘前盘后业务行为。

## Task 记录

### RT-S2-001 定义核心领域对象

- 状态：`[x] 已接受`
- 依赖：Bootstrap 合同冻结完成。
- 委派：`0` 个 subagent；领域、事实源、生命周期、对象关系和 compatibility 边界均由 Parent 直接实现。
- 仓库事实复核：
  - Task Card 所用 Bootstrap 基线 `90ad17e` 已被仅文档提交 `16f81d9 Stage 2 Bootstrap` 替代；对比 `90ad17e..HEAD` 仅改动 `docs/refactor-implementation-plans/stage-2-implementation-plan.md`、`docs/refactor-implementation-logs/stage-2.md`、`docs/Refactor-Implementation-Log.md`。
  - 执行开始时 `git status --short` 为空；未发现需保护的未提交用户改动。
  - 当前仓库仍不存在 `src/domain/`，且 `src/schemas/market.py`、`src/schemas/strategy.py`、`src/schemas/trade.py` 为空文件；适合作为 canonical contract 与 compatibility import 边界。
- 实现范围：
  - 新增 `src/domain/` canonical contract 包：枚举、typed references、value objects、19 个核心对象 DTO、lifecycle validator、legacy mapping contract、显式 compatibility adapters。
  - 新增 `tests/unit/domain/` 和 `tests/unit/schemas/test_domain_adapters.py`，覆盖 frozen lifecycle、typed IDs、same-name MarketSnapshot convergence、MarketState/StrategyVersion adapter convergence、legacy mapping 显式歧义保留、JSON Schema `$defs` 完整性。
  - 在 `api/schemas/article_metadata.py`、`api/schemas/market.py` 增加只读 DTO adapter 函数；在 `src/schemas/market.py`、`src/schemas/strategy.py`、`src/schemas/trade.py` 增加 canonical compatibility import/export。
- Frozen-contract 核验：
  - 未修改数据库表、列、索引、FK、约束、enum、migration 或 persisted data。
  - formal version 生命周期固定为 `draft -> in_review -> approved -> published -> archived`，并保留 `rejected` / `superseded` 终态语义。
  - runtime instance、formal version、Proposal 使用不同状态枚举；`accepted Proposal -> draft only` 由 validator 显式拒绝非 draft 目标。
  - Rule/Strategy/Profile 资产 ID 与版本 ID 分离；typed references 对 `rule_id/rule_version_id`、`strategy_id/strategy_version_id`、`author_profile_id/author_profile_version_id` 强制区分。
  - ArticleStructure、RuleCandidate、MarketSnapshot、MarketState、StrategyVersion 的 legacy 定义通过显式 adapter 汇聚到 canonical DTO；未引入第二套 formal schema 或 writer。
  - 缺失、歧义和 legacy-only 信息保持显式 `QualityStatus.partial|ambiguous|legacy_only|unresolved`，未被降格为 false/0/empty/verified。
- 验证：
  - `../.venv/bin/python -m pytest tests/unit/domain tests/unit/schemas -q` → `12 passed`
  - `../.venv/bin/python -m pytest tests/unit/models/test_models.py tests/unit/models/test_stage1_models.py tests/api/test_ui_openapi_contract.py -q` → `12 passed`
  - `../.venv/bin/python -m mypy src/domain api/schemas` → `exit 1`；仓库启用 `[tool.mypy] strict = true`，但该命令会递归分析 `src/domain api/schemas` 的依赖链并命中 95 个文件中的 466 个既有错误，包含 `src/persona/param_types.py`、`src/models/market_snapshot.py`、`api/schemas/common.py`、多处缺失 stubs 与历史严格类型问题；因此本仓库当前 mypy 配置对本 Task 不可作为通过门禁，未报告为 passed。
  - 替代静态检查：`../.venv/bin/python -m compileall src/domain api/schemas` → 通过。
  - `git diff --check` → 通过。
- Parent Review 结论：
  - 本 Task 输出满足 Task Card 第 11 节：canonical enum/DTO、typed refs、lifecycle validator、audit/provenance/quality/source value objects、legacy mapping contracts、无 DB 写入 compatibility adapters、contract/import/convergence/JSON Schema tests 均已落地。
  - 未发现需要触发 `ESCALATION_REQUIRED` 的新 frozen-contract 冲突。
  - `RT-S2-001` 接受；`RT-S2-002` 允许开始，但仍受其自身 Task Card 与 Stage 2 metadata drift 门禁约束。

### RT-S2-002 重构数据库

- 状态：`[x] 已接受`
- 委派：`0` 个 subagent；Schema、metadata、Alembic、compatibility、rollback/recovery 与 acceptance 决定均由 Parent 直接完成。
- 入口与保护：
  - 当前分支 `main`，本任务实现前 `HEAD=e654b89738fc62c4e6681c13ed353d6f01bf7f97`。
  - 继续执行前已复核当前完整 diff、现有 Alembic 链、真实 PostgreSQL 表结构、代表性数据量和 legacy writer/read 路径。
  - 本次开始时无未提交用户改动需要保护；未回退任何用户改动。
- 本 Task 实现：
  - 完成权威 metadata 收敛：
    - 注册 `alert_history`、`rule_pool`、`trade_sample`、`article_classification`、`market_data`、`topic_mapping` 等既有表；
    - 对齐 `trader_strategy_versions` 短约束名 `uq_tsv_trader_dt_ver`；
    - 修正多处 legacy `json/jsonb`、索引、约束和 `trade_logs` 类型/字段漂移；
    - `env.py` 引入 compatibility view 过滤，避免 autogenerate 把兼容视图误判为正式表漂移。
  - 完成 Stage 2 canonical ORM 与 repository/compatibility foundation：
    - 新增 `src/models/stage2_canonical.py`，落地 support tables、PromptRun、migration observability、canonical rule/profile/strategy/daily-plan tables；
    - 新增 `src/domain/stage2_repositories.py` canonical repository protocols；
    - 新增 `src/db/repositories/stage2_compatibility.py` legacy read adapters；
    - compatibility views 对应的 legacy ORM 已标记为 compatibility-only，不参与正式 metadata drift gate。
  - 完成线性 Alembic migration chain：
    - `2026_06_14_0002_stage2_metadata_alignment`
    - `2026_06_14_0003_stage2_domain_schema`
    - `2026_06_14_0004_stage2_compatibility_views`
    - 单一 head 保持为 `2026_06_14_0004`。
  - 完成 metadata alignment 与 non-destructive Schema 变更：
    - `alert_history.tags/status/aggregated_count` 收紧为 `NOT NULL`；
    - `trade_logs` additively 补齐 `source/market/position_side/order_type/currency/strategy_tag/rationale`、`account_id/side/fee` 非空和 `uq_trade_logs_external_id`；
    - 空 legacy 表 `market_datasets`、`strategy_regime_selections`、`regime_rule_selections` 按冻结方案重构为 `dataset_snapshots`、`daily_rule_selections`、`daily_rule_selection_items`，并保留旧表名 compatibility views；
    - 未迁移、未回填、未重解释任何现有业务数据。
  - 完成 backup/recovery foundation：
    - `backup_project_state` / `restore_project_state` 现在跳过 compatibility views，避免旧视图重复打包；
    - 新增单测证明 canonical 新表进入 manifest，而 compatibility views 不进入。
- 冻结合同核验：
  - 未改动已接受的 19 个 canonical object 定义、稳定 ID 规则、formal version / runtime instance / Proposal 边界、fact-source/provenance/quality/audit 语义或单一 writer 所有权。
  - 未新建第二套正式 Schema、事实源或 Alembic head。
  - 未执行 RT-S2-003、未做业务数据 backfill、未删除 legacy 表。
  - `api/schemas/market.py` 的改动仅为修正既有 response schema 缩进错误，以通过本 Task 明确要求的 API focused checks；未扩展 Stage 边界。
- 隔离 PostgreSQL 验证：
  - 因本机 `trade` 角色无 `CREATE DATABASE` 权限，使用临时独立 PostgreSQL cluster（`/private/tmp/rt_s2_002_pgdata` + unix socket）完成隔离验证。
  - 空库验证：
    - `base -> head` 升级通过；
    - `head -> 2026_06_03_0001` downgrade 通过；
    - `2026_06_03_0001 -> head` re-upgrade 通过。
  - 代表性 existing-data fixture 验证：
    - 在 `2026_06_03_0001` base 插入 `blog_articles=1`、`trade_logs=1`、`alert_history=1` legacy rows；
    - 升级到 head 后计数保持 `1/1/1`，未删除；
    - 校验 `trade_logs` 原业务字段仍可读，新增字段只填默认兼容值：`source=legacy`、`market=CN`、`position_side=long`、`currency=CNY`；
    - `alert_history` fixture 行在 `status=sent`、`aggregated_count=1` 下保持不变。
  - 结构检查通过：
    - `dataset_snapshots`、`daily_rule_selections` 实体表存在且约束/索引/FK 命名受控；
    - `market_datasets` compatibility view 存在并可读。
- 已运行测试与检查：
  - `../.venv/bin/python -m pytest tests/unit/db/test_migrations.py tests/unit/db/test_stage1_migration.py tests/unit/models tests/unit/backup -q` → `51 passed in 3.24s`
  - `../.venv/bin/python -m pytest tests/api/routers/test_articles.py tests/api/routers/ui/test_article_metadata.py tests/api/routers/test_rule_pool.py tests/api/routers/test_strategy_versions.py tests/api/routers/test_backtest_results.py tests/api/routers/test_market_ui.py -q` → `20 passed in 6.35s`
  - `../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini heads` → `2026_06_14_0004 (head)`
  - `../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini upgrade head` → 通过；再次执行 `upgrade head` 也为 no-op，通过 safe-rerun 验证
  - `../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini check` → `No new upgrade operations detected.`
  - `git diff --check` → 通过。
- Parent Review 结论：
  - `RT-S2-002` completion conditions 已满足：
    - 单一 Alembic head；
    - metadata convergence；
    - 无 unexplained autogenerate drop；
    - old API read compatibility focused checks 通过；
    - 无业务数据 backfill/deletion/reinterpretation；
    - isolated PostgreSQL rollback / re-upgrade / existing-data preservation 证据完备；
    - backup manifest 覆盖 canonical 新表并排除 compatibility views。
  - `RT-S2-002` 接受。
  - `RT-S2-003` 现在允许开始，但本 Session 未开始执行。

### RT-S2-003 数据迁移

- 状态：`[ ] 未开始`
- 阻塞：等待 `RT-S2-002` 目标 Schema、migration chain、rollback/recovery 接受。

## Stage Gate

- 尚未运行。
- Stage 3 不允许开始。

## 残余风险与后续依赖

- Stage 2 当前状态更新为 `[-] 进行中`：`RT-S2-001` 已接受，Stage 尚未完成。
- Alembic metadata drift 是 `RT-S2-002` 必须解决的高风险前置项。
- legacy 文件和报告的实际迁移数量需在 `RT-S2-003` preflight 中完整盘点。
- 当前数据库多数后续对象为空，但不能省略升级、回滚、幂等和 compatibility 验证。
