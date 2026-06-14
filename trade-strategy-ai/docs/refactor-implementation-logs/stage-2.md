# Stage 2 实施记录

## Stage 摘要

- Stage：`Stage 2 领域模型、数据库和版本契约`
- 当前状态：`[x] 已完成`
- 入口条件：Stage 1 已接受，权威日志允许进入 Stage 2。
- 出口条件：领域、ORM、数据库、API/DTO、迁移和 compatibility 合同一致；旧数据迁移可追溯、可重跑、可恢复；无第二套正式事实源。
- 实施计划：`refactor-implementation-plans/stage-2-implementation-plan.md`
- 下一 Task：`Stage 3 Bootstrap`

## Bootstrap 记录

### 状态

- Bootstrap 与合同冻结：已完成。
- Stage 实现：进行中，Gate 未执行。
- `RT-S2-001`：`[x]`。
- `RT-S2-002`：`[x]`。
- `RT-S2-003`：`[x]`。

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

- 状态：`[x] 已接受`
- 委派：`0` 个 subagent；迁移解释、legacy/canonical mapping、冲突边界、cutover/recovery、acceptance 决定均由 Parent 直接完成。
- 入口与保护：
  - 当前分支 `main`，执行开始前 `HEAD=27bf920a3f75a6cda726b65a1f9a36e6c21e64d8`。
  - 开始前已复核 `RT-S2-001` / `RT-S2-002` 在当前仓库中均为 accepted。
  - 已核对当前 git status、完整 diff、Alembic head、legacy 数据库事实、legacy 文件源、Jobs 与 reports。
  - 实现开始时工作树无未提交用户改动；未覆盖或回退任何用户内容。
- 预检与库存核验：
  - Alembic head：`2026_06_14_0004`，单一 head，无 Schema 链改动。
  - Bootstrap 数据库计数与预期一致：
    - `raw_articles=131`
    - `blog_articles=131`
    - `article_metadata=262`
    - `article_metadata_selections=7`
    - `rule_pool=14`
    - `ohlcv_bars=84`
    - `backtest_result_runs=0`
    - `market_snapshots=0`
    - `market_regimes=0`
    - `rule_applicability_profiles=0`
    - `trader_strategy_versions=0`
    - `trader_memory=0`
  - 额外 legacy source inventory：
    - `daily-report/*.md=34`，fingerprint `ddec80ea037ded1d63233a40f87342983952ba85105213e230582fa2ff319bcd`
    - `daily-sessions/*.md=36`，fingerprint `199bac92020036efc1a684a4e1505c530cc5cfa6fe987e7454dd124c0df7c5d1`
    - `data/jobs/*/job.log=4`，fingerprint `c0d6bef0ac7f44316ff9ab3021a60a96217d63dc46ad679ad08ab55867505126`
    - `data/**/*.json|jsonl=9`，fingerprint `3384345d0fbcc35d6662a95549877381e2d9d705e28a446dc06d18ff043785f1`
    - `strategy_files=0`
    - `market_files=0`
  - 解释约束核对：
    - `raw_articles.source_url` 与 `blog_articles.source_url` 全量 131/131 对齐。
    - `raw_articles.is_processed=false` 全量存在，按 Task Card 统一标记为 `ambiguous`，未据此重复导入。
    - `article_metadata` 为每篇 `v1/v2` 双记录；未知 prompt/schema 版本统一记为 `legacy_unknown`。
    - `article_metadata_selections` 7 条均为 `auto`，仅保留 compatibility event，不升级为人工批准。
    - `rule_pool` 14 条中 `approved=7`、`pending=7`，legacy approved 未被提升为 canonical published。
    - `ohlcv_bars` 84 条仅覆盖单个交易日 `2026-04-20`，仅生成 1 个 partial `DatasetSnapshot`。
- 本 Task 实现：
  - 新增 `scripts/migrate_stage2_data.py` 稳定 CLI 入口，支持：
    - `--dry-run`
    - `--apply`
    - `--verify`
    - `--resume`
    - `--batch-size`
    - `--report-dir`
    - `--fail-after-items`
  - 新增 `src/migrations/stage2_data_migration.py`：
    - preflight inventory、deterministic source fingerprint、dry-run report、apply/verify/resume runner；
    - bounded batch 迁移 articles、article analysis、selections、rules/backtests、market data；
    - `migration_runs` / `migration_run_items` / `migration_quality_reports` / `legacy_id_mappings` / `migration_conflicts` observability；
    - deterministic legacy-to-canonical mapping、quality status、recovery export、shadow read、cutover switch 状态；
    - repeated apply 幂等保护，同一 `source_fingerprint` 下不生成重复 canonical 对象；
    - injected mid-run failure 可保留 recovery point 并 resume。
  - 新增测试：
    - `tests/unit/scripts/test_stage2_migration.py`
    - `tests/integration/test_stage2_data_migration.py`
  - 未修改 Prompt、前端页面、legacy 数据文件、Schema 或 Alembic 链。
- canonical 迁移结果：
  - Articles：
    - `blog_articles 131 -> article_revisions 131`
    - 保留 blog article UUID 作为 canonical article ID；
    - `raw_articles` 仅保留 provenance/mapping，全部 `ambiguous`，未重复导入。
  - Article analysis：
    - `article_metadata 262 -> prompt_runs 262 + article_structures 262 + rule_candidates 485`
    - raw LLM output 全量保留；
    - prompt/schema 无法证明时记 `legacy_unknown`；
    - 未自动批准任何提取结果。
  - Selections：
    - `article_metadata_selections 7 -> lifecycle_events 7`
    - 全部作为 compatibility event 保留，未变成人工批准。
  - Rules：
    - `rule_pool 14 -> rules 14 + rule_versions 14 + rule_families 14 + rule_family_memberships 14`
    - quality 分布：`legacy_only=7`、`unresolved=7`
    - canonical published 版本数保持 `0`。
  - Backtests：
    - `rule_pool.backtest_result 14 -> backtest_result_runs 14`
    - 全部为 compatibility observation，quality=`unresolved`，未声称可复现。
  - Market data：
    - `ohlcv_bars 84 -> dataset_snapshots 1`
    - 质量标记 `partial=84`，未虚构完整 manifest。
  - Daily objects：
    - `34 + 36 = 70` 条文件均保留为 source inventory；
    - 因 pre-market / post-market 与 stable asset 角色无法证明，全部 `rejected_count=70` + `quality_status_counts.ambiguous=70`；
    - 未错误映射为正式 `TradingDayPlan` 或 `PostMarketReview`。
  - Author profiles / strategies：
    - 当前可用 legacy source 计数均为 `0`，未创建 formal canonical 记录。
- 主库 dry-run / apply / verify 结论：
  - dry-run 报告：`/private/tmp/rt_s2_003_dryrun2/dry_run_report.json`
  - 第一轮 apply 成功后主库 canonical 计数：
    - `article_revisions=131`
    - `prompt_runs=262`
    - `article_structures=262`
    - `rule_candidates=485`
    - `rules=14`
    - `rule_versions=14`
    - `backtest_result_runs=14`
    - `dataset_snapshots=1`
    - `lifecycle_events=7`
    - `legacy_id_mappings=629`
    - `migration_run_items=498`
    - `migration_quality_reports=9`
  - 第二轮相同 fingerprint apply 幂等通过：
    - `migration_runs` 仍为 `1`
    - 各已迁移分类 `migrated_count=0`
    - `skipped_idempotent_count` 分别为：
      - articles `131`
      - article_analysis `262`
      - selections `7`
      - rules `14`
      - backtests `14`
      - market_data `84`
  - verify 报告：`/private/tmp/rt_s2_003_verify/verify_report.json`
- 隔离 PostgreSQL failure/resume 验证：
  - 使用独立 UTF-8 临时 PostgreSQL cluster：
    - data dir `/private/tmp/rt_s2_003_pgdata`
    - socket `/private/tmp/rt_s2_003_pgsocket`
    - port `55433`
  - 临时库先升到接受的 head `2026_06_14_0004`，再导入 legacy source tables。
  - injected failure：
    - 命令 `--apply --batch-size 50 --fail-after-items 160`
    - 结果 `exit 2`
    - `migration_runs.status=failed`
    - `recovery_point_json={"mode":"apply","error":"injected failure after article analysis batch","processed_items":393}`
    - 失败时已保留部分写入：
      - `article_revisions=131`
      - `prompt_runs=262`
      - `migration_run_items=393`
  - resume：
    - 命令 `--resume --batch-size 50`
    - 同一 `migration_run_id=3eac42e0-fe95-544a-b72d-34a71afa9f8b` 完成
    - resume 后计数收敛到目标值：
      - `article_revisions=131`
      - `prompt_runs=262`
      - `article_structures=262`
      - `rule_candidates=485`
      - `rules=14`
      - `rule_versions=14`
      - `backtest_result_runs=14`
      - `dataset_snapshots=1`
      - `migration_run_items=498`
      - `legacy_id_mappings=629`
- 主库一致性与 compatibility 证据：
  - legacy source counts 在迁移前后保持不变：
    - `raw_articles=131`
    - `blog_articles=131`
    - `article_metadata=262`
    - `article_metadata_selections=7`
    - `rule_pool=14`
    - `ohlcv_bars=84`
  - orphan / duplicate 检查：
    - `duplicate_legacy_keys=0`
    - `article_structure_prompt_orphans=0`
    - `article_structure_revision_orphans=0`
    - `rule_version_orphans=0`
    - `family_orphans=0`
    - `membership_rule_orphans=0`
  - compatibility reads：
    - `market_datasets=1`
    - `regime_rule_selections=0`
    - `strategy_regime_selections=0`
    - `lifecycle_events=7`
  - migration observability：
    - `migration_quality_reports=9`
    - `migration_conflicts=0`
  - shadow read：
    - `legacy_blog_articles=131 == canonical_article_revisions=131`
    - `legacy_metadata=262 == prompt_runs=262 == article_structures=262`
    - `legacy_rule_pool=14 == canonical_rule_versions=14`
    - `published_rule_versions=0`
- Writer cutover：
  - cutover switch：`STAGE2_CANONICAL_WRITER_ENABLED`
  - 当前 `enabled=false`
  - `verified=true`，且 recovery export 已生成；本 Task 未开启 dual write，未退役 legacy writer。
- 已运行测试与检查：
  - `../.venv/bin/python -m pytest tests/unit/scripts/test_stage2_migration.py tests/integration/test_stage2_data_migration.py -q` → `6 passed in 3.07s`
  - `../.venv/bin/python scripts/migrate_stage2_data.py --dry-run --report-dir /private/tmp/rt_s2_003_dryrun2` → 通过
  - `../.venv/bin/python scripts/migrate_stage2_data.py --apply --batch-size 50 --report-dir /private/tmp/rt_s2_003_apply1` → 通过
  - `../.venv/bin/python scripts/migrate_stage2_data.py --apply --batch-size 50 --report-dir /private/tmp/rt_s2_003_apply4` → 幂等通过，仅 skipped
  - `../.venv/bin/python scripts/migrate_stage2_data.py --verify --report-dir /private/tmp/rt_s2_003_verify` → 通过
  - `../.venv/bin/python -m pytest tests/api/routers/test_articles.py tests/api/routers/ui/test_article_metadata.py tests/api/routers/test_rule_pool.py tests/api/routers/test_strategy_versions.py tests/api/routers/test_backtest_results.py tests/api/routers/test_market_ui.py -q` → `20 passed in 17.97s`
  - 隔离库 injected failure / resume：
    - `../.venv/bin/python scripts/migrate_stage2_data.py --apply --batch-size 50 --fail-after-items 160 --report-dir /private/tmp/rt_s2_003_temp_fail` → 预期失败，recovery point 已落库
    - `../.venv/bin/python scripts/migrate_stage2_data.py --resume --batch-size 50 --report-dir /private/tmp/rt_s2_003_temp_resume` → 通过
  - `git diff --check` → 通过
- Parent Review 结论：
  - RT-S2-003 completion conditions 满足：
    - 所有列出的 migration category 均有 migrated / empty / rejected 结论；
    - article / metadata / selection / rule / OHLCV / file counts 已核对并解释；
    - apply 幂等；
    - isolated failure injection + resume 通过；
    - legacy-to-canonical mappings deterministic，无重复 legacy assignment；
    - canonical FK 无 orphan；
    - compatibility reads 保持可用；
    - cutover switch 显式存在且 recovery evidence 完整；
    - legacy 数据未删除，未发明 human-approved/published 状态；
    - focused tests、compatibility tests、verify mode、`git diff --check` 均通过。
  - `RT-S2-003` 接受。
  - Stage 2 Gate 本 Task 未执行；如用户明确继续，可开始 Gate，但当前日志不将 Stage 2 标记为完成。

## Stage Gate

### 2026-06-14 gpt-5.5 Gate escalation 与合同决定

- 初始 Gate 结论：`ESCALATION_REQUIRED`。
- 初始 BLOCKER：`STAGE2_CANONICAL_WRITER_ENABLED` 只进入迁移报告，没有控制 runtime writer routing；legacy rule、strategy、market snapshot/state、backtest、applicability、signal writers 仍可形成第二正式写入路径。
- 初始 HIGH：复用表缺失冻结字段/FK，且 `daily_rule_selections.market_state_id`、`post_market_reviews.market_state_id` 未约束到 canonical MarketState；原日志对 Schema convergence 与 writer cutover 的描述过度。
- 合同复核结论：`PRESERVE_CONTRACT_AND_REPAIR`。
- 判定依据：冻结合同已明确规定 `Application service -> canonical repository -> PostgreSQL canonical tables`、每域一个正式 writer、compatibility read-only、migration 非 runtime writer、禁止 dual-write。现有证据证明实现不完整，没有证明合同矛盾、需要双 writer、Schema 无法表达或数据语义必须重解释。
- 委派：`0` 个 subagent。Schema、migration、runtime routing 和日志共享同一 ORM/Alembic 边界，拆分会增加并发冲突和验收风险。

### 内部修复 Task Cards

#### Repair Card A — RT-S2-002 Schema convergence

- 根因：accepted migration/ORM 将复用 legacy 表误判为已经收敛。
- 允许：仅补齐 frozen Stage 2 字段、FK、索引、约束、repository mapping、backup/metadata coverage 和测试；使用线性 additive migration。
- 禁止：改变 stable IDs、生命周期、事实源、数据含义、正式版本关系；引入第二 head 或 Stage 3 行为。
- 最小修复：新增 `2026_06_14_0005` Schema repair 与 `0006` metadata repair，保留 legacy 字段作 compatibility provenance。
- 必测：metadata、实际 PostgreSQL、upgrade/downgrade/re-upgrade、既有数据保留、FK orphan、single head、autogenerate check。

#### Repair Card B — RT-S2-003 canonical writer routing

- 根因：feature flag 未接入 runtime，application service 与 repository 之间没有可执行 writer boundary。
- 允许：应用服务 scope、canonical repository guard、legacy writer rejection/read-only、CLI/agent/service reroute、enforcement tests、truthful migration report。
- 禁止：intentional dual-write、第二正式 repository/fact source、在 migration runner 中承载 runtime 业务写入、跨入 Stage 3。
- 最小修复：公共 writer routing guard；enabled 时 canonical repository 必须处于匹配的 application-service scope，legacy formal writer 一律拒绝；disabled 时保持原 rollout compatibility。
- 必测：enabled positive path、direct repository bypass、legacy write rejection、CLI/agent routing、migration runtime import isolation、no dual-write。

### Writer ownership matrix

| Domain | Canonical application service | Canonical repository/table | Legacy writer locations | 修复后 legacy 行为 | Feature flag | Enforcement evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Rules / RuleVersion | 后续正式 Rule application service；Stage 2 期间无新 formal publish writer | canonical `rules` / `rule_versions` | RulePool repository、prediction、attribution、CLI review | enabled 时拒绝写；read 保留 | disabled 保持 rollout compatibility；enabled 禁止旧写 | legacy rejection tests；CLI review 不再直接调用 repository |
| Strategy / StrategyVersion | 后续正式 Strategy application service；Stage 2 期间无新 formal publish writer | `strategies` / `strategy_versions` | StrategyLibraryRepository、pipeline callers | enabled 时拒绝写；read 保留 | 同上 | repository guard |
| MarketSnapshot | `MarketDataStorageService` | MarketSnapshot/section/item/quality repositories -> `market_snapshots` 及从属表 | `market_datasets` compatibility writer | enabled 时不写 legacy dataset | enabled 只写 canonical aggregate | direct subtable bypass rejection；service scope |
| MarketState | `MarketRegimeService` | MarketRegimeRepository -> `market_regimes` | `market_datasets` compatibility writer | enabled 时不写 legacy dataset | enabled 只写 canonical state | repository guard；service scope |
| BacktestRun | `JobService` | BacktestResultRunRepository -> `backtest_result_runs` | direct repository callers | enabled 时无 service scope即拒绝 | enabled canonical only | repository guard、mapping tests |
| ApplicabilityProfile | `RuleApplicabilityService` | RuleApplicabilityRepository -> `rule_applicability_profiles` | direct repository/ORM flush | enabled 时无 service scope即拒绝 | enabled canonical only | repository guard、service-scoped review/upsert |
| Signal | `SignalService` | SignalRepository -> `signals` | ManagerAgent direct repository | agent 已改经 service；direct repository 拒绝 | enabled canonical only | positive service-scope test、direct bypass test |
| DailyRuleSelection | `RegimeRuleSelectionService` | selection repositories -> canonical/compatibility-backed selection persistence | direct selection repositories | enabled 时必须由 service scope 调用 | enabled canonical boundary | direct bypass rejection、service scope |
| Dataset compatibility | 无正式 runtime writer | canonical `dataset_snapshots` | MarketDatasetRepository | enabled 时 read-only/reject write | disabled compatibility；enabled no second writer | legacy guard、snapshot/state services skip dual-write |
| Migration/backfill | 不适用 | `scripts/migrate_stage2_data.py` / migration module | 无 runtime import | 仅 apply/backfill/verify/resume | 读取同一 flag仅报告真实状态 | runtime import isolation test |

### RT-S2-002 repairs

- `market_snapshots` 补齐 canonical time semantics、content fingerprint、manifest 和 market/date/slot/version uniqueness。
- `market_regimes` 增加 canonical `market_state_id`、typed `market_snapshot_id` FK、definition/feature version、available time；legacy `regime_id`/`snapshot_id` 保留为 compatibility provenance。
- `backtest_result_runs` 将 legacy string strategy ref 显式保留，新增 typed dataset/rule/strategy version FKs 和 MarketState definition version。
- `rule_applicability_profiles` 增加 canonical ID、rule/dataset FKs、definition version、formal lifecycle、result status。
- `signals` 增加 plan/instance/strategy FKs、rule version IDs、signal lifecycle/time semantics；legacy strategy string保留。
- `daily_rule_selections` 与 `post_market_reviews` 增加 canonical MarketState FKs。
- metadata import cycle 被移除；JSON metadata 保持 PostgreSQL JSONB、SQLite tests 可创建。
- 增加 compatibility query aliases，不新增第二写入实现。

### RT-S2-003 repairs

- 新增 `src/common/stage2_writer_routing.py`，动态读取 `STAGE2_CANONICAL_WRITER_ENABLED`，提供 application-service scope 和可观测拒绝。
- canonical repositories 在 enabled 模式拒绝无 scope 的直接写入；legacy RulePool、StrategyLibrary、MarketDataset writers 在 enabled 模式只读。
- MarketSnapshot aggregate、MarketState、BacktestRun、ApplicabilityProfile、Signal、DailyRuleSelection 写入均由 application service 建立 scope。
- ManagerAgent signal persistence 改经 SignalService；CLI rule review 改经 RulePoolService。
- snapshot/state feature paths 在 enabled 模式跳过 legacy dataset write；一次业务操作不存在 canonical + legacy dual-write。
- migration runner 未被 router、CLI、Job、Workflow 或 runtime service import；migration report 使用实际 runtime flag。

### 失效证据与重跑结果

- 原 `0004` Schema convergence 与 migration-report-only writer cutover 证据失效；`RT-S2-002`、`RT-S2-003` 仅为合同符合性修复而重开，frozen contracts 未修改。
- 指定 Stage 2 unit/integration：最终 re-review `80 passed in 5.18s`。
- 指定 API/OpenAPI compatibility：最终 re-review `21 passed in 8.82s`。
- writer enforcement：最终 re-review `8 passed in 4.09s`。
- 相关 service/repository 回归：`18 passed in 3.97s`。
- Alembic：single head/current `2026_06_14_0006`；`alembic check` 无新操作。
- `scripts/migrate_stage2_data.py --verify`：通过；conflict/hash mismatch/orphan 均为 `0`，`backtest_result_runs=14` 保持，ambiguous daily objects 继续显式 rejected。
- 隔离 PostgreSQL：accepted `0004 -> 0006`、`0006 -> 0004`、re-upgrade、第二次 upgrade no-op 均通过；14 条既有 backtest records 保留，rule FK orphan `0`；实际 FK/constraint/index 已检查。
- 原 RT-S2-003 isolated failure/resume 证据仍有效，且本次 migration unit/integration 回归覆盖 injected failure/resume。
- compileall 与 `git diff --check` 通过。
- 仓库全量 pytest 已尝试并在挂起后中断：`151 passed, 1 skipped, 3 failed, 2 errors in 287.40s`。失败为既有非 Stage 2 fake-service signature 不一致（data-health、UI auth）及 agent integration 仍 patch 已不存在的 `SignalVersioning`；本次 ManagerAgent diff 未删除该 symbol，基线中已不存在。未用全量结果替代 Stage 2 指定套件，全部 Stage 2 受影响测试已独立完整运行。

### Final Gate

- Gate 决定：`ACCEPTED`。
- 无剩余 BLOCKER/HIGH 或 contract-sensitive finding。
- RT-S2-001 frozen contracts 未变；ORM、PostgreSQL、repository mapping、API compatibility、migration chain 与 runtime writer boundary 已收敛。
- Stage 2：`[x] 已完成`。
- Stage 3 Bootstrap 可以开始；本 Session 未执行 Stage 3。

## 残余风险与后续依赖

- Stage 2 Gate 已接受，无 Stage 2 实施阻塞。
- 仍保留的业务限制是：daily objects、author profiles、strategies 中未证明的 legacy 文件没有被升级为正式资产，这一保守边界符合合同要求。
