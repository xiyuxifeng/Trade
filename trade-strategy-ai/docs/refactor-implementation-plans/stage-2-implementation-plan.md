# Stage 2 领域模型、数据库和版本契约实施计划

> **执行要求：** `RT-S2-001`、`RT-S2-002`、`RT-S2-003` 是三个独立 M3 Task，必须依次执行。每个 Task 使用独立 Parent Session 或明确的同 Stage 延续会话；不得合并实现。可选 mini 只能执行已冻结、边界明确的只读调查或机械工作，最终 Review 与接受由 Parent 完成。

**Stage 目标：** 建立核心领域对象、稳定 ID、正式版本、数据库 Schema、兼容边界和可恢复数据迁移合同，使数据库成为正式业务事实源，并为 Stage 3 提供唯一、可追溯的领域基础。

**基线：** `main`，commit `90ad17e`，与 `origin/main` 一致；Bootstrap 开始时工作树和暂存区均无差异。

**风险：** Stage 2 全部为 M3。领域关系、正式事实源、Schema、迁移顺序、回滚和数据解释错误都可能形成第二套正式系统或破坏历史数据。

**执行顺序：**

```text
RT-S2-001 冻结并实现领域契约
→ Parent Review 接受领域合同
→ RT-S2-002 实现目标 Schema 和兼容基础
→ Parent Review 接受 Schema 与 Alembic 链
→ RT-S2-003 执行可重跑数据迁移
→ Parent Review
→ gpt-5.5 Stage 2 Gate
```

---

## 1. Bootstrap 与委派决定

- 本次 Bootstrap 使用 Parent 单控制器，选择 `0` 个 subagent。
- 不创建 Explorer。ORM、Alembic、API、DTO、前端类型、Service、Job、Workflow 和文件入口已经可由明确路径与全仓搜索定位；只读委派的上下文转移成本高于收益。
- 不创建 Executor。Bootstrap 禁止实现 Stage 2，且领域、Schema、迁移顺序、回滚和事实源决定不可委派。
- 后续 Task 默认仍为 Parent 主导：
  - `RT-S2-001`：默认 `0` 个 subagent；核心合同不得委派。
  - `RT-S2-002`：合同接受后可使用最多 `1` 个 Executor 完成机械 ORM/Alembic 工作，但仅允许一个 writer 修改共享 ORM 和 migration chain。
  - `RT-S2-003`：合同接受后可使用最多 `1` 个 Executor 编写迁移工具和测试；迁移解释、冲突裁决和接受仍由 Parent 完成。

## 2. 已核验入口条件

### 2.1 Stage 1

- `Refactor-Implementation-Log.md` 和 `refactor-implementation-logs/stage-1.md` 均记录 Stage 1 为 `[x]`。
- Stage 1 已接受七个业务导航、统一页面状态、首页真实聚合和兼容路由边界。
- Stage 1 明确未创建 Stage 2 对象、迁移或 Prompt 变更。
- 权威日志明确允许进入 Stage 2。

### 2.2 Git 与工作区

- 当前分支：`main`。
- `HEAD`：`90ad17ef2265e4e48d0f135dd121e94323872577`。
- `origin/main`：同一 commit。
- `git status --porcelain=v2`、工作区 diff、暂存区 diff 均为空。
- Bootstrap 开始时没有未提交的用户自有改动。本计划产生的文档差异属于本次 Bootstrap。

### 2.3 数据库与 Alembic

- 实际数据库：PostgreSQL `trade_strategy_ai`，schema `public`。
- Alembic 脚本只有一个 head：`2026_06_03_0001`。
- 实际 `alembic_version`：`2026_06_03_0001`。
- 历史在 `2026_05_17_0001` 分叉为 workflow 与 market-regime 两支，并已通过 `2026_05_19_0001` 合并。
- 实际数据库有 43 张表。
- `alembic check` 失败，不能把“位于 head”解释为“ORM 与数据库一致”：
  - metadata 未纳入 `alert_history`、`rule_pool`、`trade_sample`、`article_classification`、`topic_mapping`、`market_data` 等现存表；
  - 多处 JSON/JSONB、索引、约束和 `trade_logs` 字段漂移；
  - ORM 约束名 `uq_trader_strategy_versions_trader_id_strategy_date_version_name` 超过 PostgreSQL 63 字符限制；
  - 现有 migration 中实际约束名为较短的 `uq_tsv_trader_dt_ver`。
- `RT-S2-002` 必须先修复 metadata 注册和漂移门禁，再生成 Stage 2 migration；禁止基于当前 autogenerate 输出直接执行删除。

### 2.4 实际数据

| 对象 | 实际数量/事实 |
| --- | --- |
| `raw_articles` | 131；全部 `is_processed=false` |
| `blog_articles` | 131；与 `raw_articles.source_url` 131/131 对应 |
| `article_metadata` | 262；每篇文章恰有 `v1`、`v2` 两条 |
| `article_metadata_selections` | 7；全部为 `auto` |
| `rule_pool` | 14；7 `approved`、7 `pending`，全部 `unmapped` |
| RulePool 内嵌回测 | 14/14 均有 `backtest_result` |
| RulePool 来源引用 | 14/14 非空；未发现引用不到 `blog_articles.id` 的值 |
| `ohlcv_bars` | 84 行、84 个 symbol，全部日期为 `2026-04-20` |
| `backtest_result_runs` | 0 |
| `market_datasets` / `market_snapshots` / `market_regimes` | 0 |
| `rule_applicability_profiles` | 0 |
| `trader_strategy_versions` / `trader_memory` | 0 |
| `strategy_regime_selections` / `signals` | 0 |
| Jobs | 7；`kaipan-fetch` 4、`process` 3 |

数据结论：

- 当前可迁移的主要正式数据是文章、两版文章提取结果、7 条选择记录、14 条规则及内嵌回测摘要、少量 OHLCV 和运行记录。
- 多数后续领域表为空，可以重命名或重构，但仍必须通过 migration 保留对象和引用，不得依赖“当前为空”绕过升级/回滚测试。
- `raw_articles.is_processed=false` 与已存在 131 条 `blog_articles` 冲突，必须标记迁移质量问题，不能据此重复导入或解释为未处理。

## 3. 当前重复事实源与冲突

1. 文章：`raw_articles` 与 `blog_articles` 各持有完整正文；前者是导入原始记录，后者应成为 canonical Article。
2. 文章结构：`article_metadata` 同时承载 Prompt 调用、结构化文章、候选规则和原始输出；`ArticleMetadataSelection` 以 schema version 选择整条结果。
3. 规则：`article_metadata.strategy_rules[]`、`rule_pool`、Persona `ArticleStrategyRule`、策略 `rules_snapshot` 并行。
4. 回测：`rule_pool.backtest_result`、`BacktestResultRun`、Job result、Artifact/文件和 CLI JSON 并行。
5. MarketSnapshot：`src/models/market_snapshot.py` 是 dataclass；`src/models/market_data_snapshot.py` 是同名 ORM。
6. MarketState：Persona `MarketState`、`MarketRegimeFeature`、`MarketRegimeRecord` 和文件 `market_state.json` 并行。
7. 作者画像：`TraderProfilesFile`、Persona clusters、`TraderMemory` 与文章/规则统计并行，且旧实现会从有限文章和交易日志推断风险风格。
8. StrategyVersion：`TraderStrategyVersion` ORM、`strategy_library.schemas.StrategyVersion`、文件/CLI candidate/released JSON 和日级 `strategy_date` 语义并行。
9. 每日选择：`StrategyRegimeSelection` 的名称和字段接近 DailyRuleSelection，但没有正式 FK。
10. Signal：已有 `signals.signal_id` 稳定 UUID，但没有 TradingDayPlan FK，`strategy_version_id` 也是未约束字符串。
11. 盘前盘后：报告 API、daily report/session Markdown、Job result 和 Artifact 仍可作为唯一读取入口。
12. Writer：文章抽取、RulePool repository、策略 repository、market storage、Job runner、CLI 和文件服务存在多个领域写入口。

## 4. 统一 ID、版本、审计和质量合同

### 4.1 ID

- 新 canonical 实体主键统一使用 PostgreSQL UUID，应用层使用 `uuid4()`；数据库不得从文件路径生成主键。
- 已有稳定 UUID 保留：
  - `blog_articles.id` 作为 `Article.article_id`；
  - `market_snapshots.id` 保留内部主键，`snapshot_id` 保留现有业务键；
  - `signals.signal_id` 作为 canonical Signal ID，旧整数 `signals.id` 仅为兼容 surrogate。
- 已有字符串 ID 通过 `legacy_id_mappings` 保存，不直接重新解释成 UUID。
- 新资产使用“稳定资产 ID + 不可变版本 ID”：
  - `rule_id` + `rule_version_id`；
  - `author_profile_id` + `author_profile_version_id`；
  - `strategy_id` + `strategy_version_id`；
  - `market_state_definition_id` + `definition_version`；
  - `dataset_snapshot_id` 本身不可变。
- 版本序号是同一资产内单调递增整数；对外引用版本 UUID，不使用文件名、日期或可变 label 作为正式 FK。

### 4.2 通用生命周期

正式版本对象允许以下状态：

```text
draft
→ in_review
→ approved
→ published
→ archived
```

终止或替代：

```text
draft/in_review → rejected
published → superseded → archived
```

约束：

- `approved` 表示审核通过但尚未成为正式读取版本。
- `published` 是正式可引用版本。
- 每个资产最多一个当前 `published` 版本；发布新版本时旧版本转 `superseded`，不得覆盖原 payload。
- `rejected` 不可恢复为同一版本；修订必须创建新版本。
- Runtime instance 不使用正式资产生命周期；Proposal 被接受后只能创建 draft，不能直接覆盖 published 资产。

### 4.3 审计

所有正式版本、runtime instance、Proposal 和人工选择至少保存：

```text
created_at
created_by
updated_at
updated_by
source_type
source_ref
quality_status
```

所有状态变更写入 `lifecycle_events`：

```text
event_id
object_type
object_id
from_state
to_state
actor_type
actor_id
reason_code
reason_text
before_json
after_json
occurred_at
correlation_id
```

禁止只更新 `reviewed_by/reviewed_at` 而丢失历史。

### 4.4 来源与质量

`fact_source` 枚举冻结为：

```text
explicit_article
llm_inference
program_observation
backtest_observation
human_approval
legacy_import
```

`quality_status` 冻结为：

```text
verified
complete
partial
ambiguous
unresolved
rejected
legacy_only
```

质量状态不得替代生命周期状态。缺失、歧义和无法映射必须保存原因与原始值。

## 5. 核心领域对象冻结

| 对象 | 稳定 ID / 业务键 | 版本与生命周期 | 正式事实源 | Stage 2 处理 |
| --- | --- | --- | --- | --- |
| Article | `blog_articles.id`; natural key `(source, source_article_id)`，缺失时 `source_url` | 内容修订由 `content_hash` 和 `article_revisions` 追踪；Article 本体不走发布生命周期 | `blog_articles` | 保留表，ORM/DTO 改名为 Article；`raw_articles` 仅导入来源 |
| ArticleStructure | `article_structure_id`; unique `(article_id, prompt_run_id)` | draft/in_review/approved/rejected/superseded | `article_structures` | 新表；从 `article_metadata` 迁移 |
| RuleCandidate | `rule_candidate_id`; candidate fingerprint 非正式 ID | extracted/auto_review/manual_review/approved/rejected/superseded | `rule_candidates` | 新表；LLM 输出只能生成 candidate |
| RuleVersion | `rule_id` + `rule_version_id`; unique `(rule_id, version_no)` | 通用正式版本生命周期 | `rule_versions` | 新表；只有人工批准 candidate 可创建 |
| RuleFamily | `rule_family_id`; unique canonical fingerprint | draft/in_review/approved/published/archived | `rule_families` + memberships | 新表；规则版本与参数变体通过 membership 关联 |
| DatasetSnapshot | `dataset_snapshot_id`; unique `content_fingerprint` | immutable；ready/partial/invalid/archived | `dataset_snapshots` | 物理重命名空表 `market_datasets`；旧表名仅保留只读兼容视图；OHLCV/Kaipan 通过 manifest 引用 |
| MarketSnapshot | `market_snapshots.id` UUID；`snapshot_id` 是外部业务键；unique `(market, trade_date, slot, data_version)` | immutable；building/ready/partial/invalid/archived | `market_snapshots` | 保留并补时间语义、manifest 与审计；正式 FK 一律引用 UUID `id` |
| MarketState | `market_state_id`; unique `(market_snapshot_id, definition_version)`；`regime_id` 是旧业务键 | immutable observation；valid/partial/invalid/superseded | 物理表 `market_regimes` | 不新建 `market_states` 表；公开 ORM/DTO 使用 `MarketStateRecord`/MarketState；旧 `regime_*` API 只读兼容 |
| RuleApplicabilityProfile | `applicability_profile_id`; unique `(rule_version_id, dataset_snapshot_id, market_state_definition_version)` | draft/in_review/approved/published/archived/superseded/rejected | `rule_applicability_profiles` | 复用表并补正式 FK、dataset 和结果状态 |
| AuthorMethodProfile | 共享 `author_profile_id` + version ID；kind=`method` | 通用正式版本生命周期 | `author_profile_versions` | 新共享表的 typed view |
| AuthorRuleProfile | 同上；kind=`rule` | 通用正式版本生命周期 | `author_profile_versions` | 新共享表的 typed view |
| AuthorValidatedProfile | 同上；kind=`validated` | 通用正式版本生命周期 | `author_profile_versions` | 新共享表的 typed view |
| StrategyVersion | `strategy_id` + `strategy_version_id`; unique `(strategy_id, version_no)` | 通用正式版本生命周期 | `strategy_versions` | 新 canonical 表；旧 TraderStrategyVersion compatibility-only |
| DailyRuleSelection | `daily_rule_selection_id`; unique `(strategy_version_id, trade_date, market_state_id, revision_no)` | generated/approved/rejected/superseded/cancelled | `daily_rule_selections` + `daily_rule_selection_items` | 物理重命名当前空表及 item 表；旧表名仅保留只读兼容视图 |
| DailyStrategyInstance | `daily_strategy_instance_id`; unique `(strategy_version_id, trade_date, revision_no)` | generated/approved/superseded/cancelled | `daily_strategy_instances` | 新表 |
| TradingDayPlan | `trading_day_plan_id`; unique `(daily_strategy_instance_id, revision_no)` | draft/in_review/approved/rejected/superseded/cancelled | `trading_day_plans` | 新表 |
| Signal | `signal_id`; natural key optional `(plan_id, symbol, signal_kind, sequence_no)` | proposed/approved/rejected/cancelled/expired/executed | `signals` | 复用，补 plan/rule-version FK 和时间字段 |
| PostMarketReview | `post_market_review_id`; unique `(trading_day_plan_id, revision_no)` | draft/in_review/approved/archived | `post_market_reviews` | 新表 |
| OptimizationProposal | `optimization_proposal_id`; unique `(review_id, proposal_type, target_asset_id, revision_no)` | draft/in_review/accepted/rejected/archived/superseded | `optimization_proposals` | 新表；三类 proposal 共表，以 type 区分 |

### 5.1 关键关系

```text
Article
├─ ArticleRevision
├─ PromptRun
└─ ArticleStructure
   └─ RuleCandidate
      └─ human approval → RuleVersion

RuleFamily
└─ RuleFamilyMembership → RuleVersion

DatasetSnapshot
├─ BacktestRun
└─ RuleApplicabilityProfile

MarketSnapshot
└─ MarketState

Author
└─ AuthorProfileVersion(kind=method|rule|validated)

StrategyVersion
├─ StrategyRuleMembership → RuleVersion
└─ optional published AuthorProfileVersion refs

StrategyVersion + MarketState + RuleApplicabilityProfile
→ DailyRuleSelection
→ DailyStrategyInstance
→ TradingDayPlan
→ Signal
→ PostMarketReview
→ OptimizationProposal
```

### 5.2 Stage 边界

Stage 2 包含：

- 对象、ID、版本、生命周期、ORM、Schema、FK、索引、迁移和 compatibility repository；
- Prompt 结果的存储合同；
- 历史数据转换和报告；
- 旧路径到新 ID 的映射。

Stage 2 不包含：

- Stage 3 的新 Prompt 调用、100+ 篇重处理或规则抽取行为；
- Stage 4 的规则审核 UI、规则发布业务；
- Stage 5 的数据抓取和 DatasetSnapshot 构建行为；
- Stage 6 的 point-in-time 回测执行和适用性计算；
- Stage 7 的作者画像生成；
- Stage 8 的策略创建/发布 UI；
- Stage 9/10 的每日盘前盘后业务生成；
- 删除旧 API、旧页面、旧文件或旧表。

## 6. 目标 Schema 冻结

### 6.1 支撑表

#### `authors`

```text
author_id uuid PK
source varchar(50) not null
source_author_key varchar(128) not null
display_name varchar(100)
created_at timestamptz not null
updated_at timestamptz not null
unique(source, source_author_key)
```

#### `article_revisions`

```text
article_revision_id uuid PK
article_id uuid FK blog_articles
revision_no int not null
content_hash varchar(64) not null
content_text text not null
content_html text
source_payload jsonb not null
captured_at timestamptz not null
quality_status quality_status not null
unique(article_id, revision_no)
unique(article_id, content_hash)
```

#### `prompt_runs`

```text
prompt_run_id uuid PK
run_id varchar(64)
article_id uuid FK blog_articles null
prompt_name varchar(128) not null
prompt_version varchar(64) not null
schema_name varchar(128) not null
schema_version varchar(64) not null
provider varchar(50)
model varchar(128) not null
input_object_type varchar(64) not null
input_object_id varchar(128)
input_version_id varchar(128)
input_hash varchar(64) not null
request_json jsonb not null
raw_output jsonb
raw_output_text text
validation_state prompt_validation_state not null
validation_errors jsonb not null
retry_count int not null default 0
token_usage jsonb not null
cost_amount numeric(18,8)
cost_currency varchar(8)
started_at timestamptz
completed_at timestamptz
created_at timestamptz not null
unique(prompt_name, prompt_version, schema_version, model, input_hash, retry_count)
```

`prompt_validation_state`：

```text
pending
valid
invalid_json
invalid_schema
invalid_evidence
repaired
failed
```

#### `legacy_id_mappings`

```text
mapping_id uuid PK
legacy_system varchar(64) not null
legacy_object_type varchar(64) not null
legacy_id varchar(512) not null
canonical_object_type varchar(64) not null
canonical_id uuid
canonical_version_id uuid
mapping_status quality_status not null
mapping_reason text
source_snapshot jsonb not null
created_at timestamptz not null
unique(legacy_system, legacy_object_type, legacy_id)
```

#### `lifecycle_events`

字段按 4.3 冻结；索引 `(object_type, object_id, occurred_at)`、`correlation_id`。

#### 迁移观测表

```text
migration_runs
migration_run_items
migration_conflicts
migration_quality_reports
```

必须保存 migration name/version、source fingerprint、started/completed time、status、pre/post counts、rejected/conflict counts、report JSON 和恢复点。

### 6.2 文章与规则

#### `article_structures`

```text
article_structure_id uuid PK
article_id uuid FK blog_articles not null
article_revision_id uuid FK article_revisions
prompt_run_id uuid FK prompt_runs not null
schema_version varchar(64) not null
payload jsonb not null
evidence_json jsonb not null
missing_fields jsonb not null
inference_fields jsonb not null
lifecycle_state formal_lifecycle not null
quality_status quality_status not null
approved_by varchar(64)
approved_at timestamptz
supersedes_id uuid FK article_structures
created_at/created_by/updated_at/updated_by
unique(article_id, prompt_run_id)
```

#### `rule_candidates`

```text
rule_candidate_id uuid PK
article_structure_id uuid FK article_structures not null
source_article_id uuid FK blog_articles not null
candidate_index int not null
candidate_fingerprint varchar(64) not null
rule_type varchar(64) not null
canonical_payload jsonb not null
evidence_json jsonb not null
explicit_fields jsonb not null
inferred_fields jsonb not null
missing_fields jsonb not null
data_dependencies jsonb not null
backtestability_status varchar(32) not null
review_state candidate_review_state not null
quality_status quality_status not null
created_at/created_by/updated_at/updated_by
unique(article_structure_id, candidate_index)
```

#### `rules`、`rule_versions`

```text
rules:
  rule_id uuid PK
  business_key varchar(128) unique not null
  current_published_version_id uuid null
  created_at/created_by/updated_at/updated_by

rule_versions:
  rule_version_id uuid PK
  rule_id uuid FK rules not null
  version_no int not null
  source_candidate_id uuid FK rule_candidates
  canonical_fingerprint varchar(64) not null
  schema_version varchar(64) not null
  lifecycle_state formal_lifecycle not null
  title varchar(256) not null
  description text
  rule_type varchar(64) not null
  instrument_scope jsonb not null
  condition_json jsonb not null
  action_json jsonb not null
  parameter_json jsonb not null
  data_dependencies jsonb not null
  evidence_json jsonb not null
  quality_status quality_status not null
  parent_version_id uuid FK rule_versions
  published_at/published_by/superseded_at
  created_at/created_by/updated_at/updated_by
  unique(rule_id, version_no)
  unique(rule_id, canonical_fingerprint)
```

#### `rule_families`、`rule_family_memberships`

```text
rule_families:
  rule_family_id uuid PK
  family_key varchar(128) unique
  canonical_fingerprint varchar(64) unique
  name varchar(256)
  lifecycle_state formal_lifecycle
  quality_status quality_status
  audit fields

rule_family_memberships:
  membership_id uuid PK
  rule_family_id uuid FK
  rule_version_id uuid FK
  member_role varchar(32)
  parameter_distance jsonb
  approved_by/approved_at
  unique(rule_family_id, rule_version_id)
```

### 6.3 数据、市场状态与回测引用

- 物理重命名空表 `market_datasets` 为 `dataset_snapshots`，并创建只读兼容视图 `market_datasets`：
  - 新增 `dataset_snapshot_id uuid PK`、`content_fingerprint`、`date_from/date_to`、`symbol_manifest`、`ohlcv_manifest`、`kaipan_manifest`、`benchmark_symbol`、`market_state_definition_version`、`available_at`、`frozen_at`、`quality_report_id`；
  - 删除文件路径作为业务键；`storage_ref` 只保留附件位置；
  - immutable，任何内容变化创建新 snapshot。
- `market_snapshots` 保留：
  - 新增 `captured_at`、`available_at`、`effective_at`、`content_fingerprint`、`manifest_json`；
  - unique `(market, trade_date, slot, data_version)`。
- 物理表 `market_regimes` 保留，不创建第二张 `market_states` 表：
  - 新增 `market_state_id uuid PK`，`regime_id` 保留为 nullable unique 旧业务键并写入 `legacy_id_mappings`；
  - ORM 唯一公开正式类为 `MarketStateRecord`，API/DTO 统一使用 MarketState；旧 `MarketRegime*` 只读适配；
  - `market_snapshot_id` 必须是 FK `market_snapshots.id`，并保存 `definition_version`、`feature_version`、`available_at`；
  - unique `(market_snapshot_id, definition_version)`，禁止新旧对象双写。
- 物理重命名空表 `strategy_regime_selections` 为 `daily_rule_selections`，空表 `regime_rule_selections` 为 `daily_rule_selection_items`；旧表名仅保留只读兼容视图。
- `backtest_result_runs` Stage 2 保留兼容表并补 FK：
  - `dataset_snapshot_id`、`rule_version_id`、`strategy_version_id`、`market_state_definition_version`；
  - 原 `storage_ref/artifact_ref` 为附件，不是结果身份；
  - Stage 6 再完成执行语义。
- `rule_applicability_profiles` 补 `rule_version_id`、`dataset_snapshot_id`、`market_state_definition_version`、`lifecycle_state`、`result_status`；`insufficient_sample` 是结果状态，不是零值。

### 6.4 作者画像

#### `author_profile_versions`

```text
author_profile_version_id uuid PK
author_profile_id uuid not null
author_id uuid FK authors not null
profile_kind author_profile_kind not null
version_no int not null
schema_version varchar(64) not null
lifecycle_state formal_lifecycle not null
as_of_from date
as_of_to date
payload jsonb not null
evidence_json jsonb not null
source_article_ids jsonb not null
source_rule_version_ids jsonb not null
source_backtest_run_ids jsonb not null
source_daily_review_ids jsonb not null
prompt_run_id uuid FK prompt_runs
parent_version_id uuid FK author_profile_versions
quality_status quality_status not null
published_at/published_by
created_at/created_by/updated_at/updated_by
unique(author_profile_id, profile_kind, version_no)
```

- `AuthorMethodProfile`、`AuthorRuleProfile`、`AuthorValidatedProfile` 是三个严格 DTO/领域类型，共用该表，不建立三套生命周期和审计实现。
- `profile_kind`：`method`、`rule`、`validated`。
- 旧 `TraderProfile` 只可迁移为 draft/legacy_only，不能因旧推断直接 published。

### 6.5 策略、每日实例、计划与复盘

#### `strategies`、`strategy_versions`、`strategy_rule_memberships`

```text
strategies:
  strategy_id uuid PK
  owner_type varchar(32)
  owner_id uuid
  business_key varchar(128) unique
  current_published_version_id uuid
  audit fields

strategy_versions:
  strategy_version_id uuid PK
  strategy_id uuid FK
  version_no int
  schema_version varchar(64)
  lifecycle_state formal_lifecycle
  parent_version_id uuid FK strategy_versions
  risk_policy_json jsonb
  selection_policy_json jsonb
  universe_json jsonb
  author_method_profile_version_id uuid null
  author_rule_profile_version_id uuid null
  author_validated_profile_version_id uuid null
  evidence_json jsonb
  quality_status quality_status
  published_at/published_by
  audit fields
  unique(strategy_id, version_no)

strategy_rule_memberships:
  membership_id uuid PK
  strategy_version_id uuid FK
  rule_version_id uuid FK
  base_weight numeric
  status varchar(32)
  configuration_json jsonb
  unique(strategy_version_id, rule_version_id)
```

#### 每日对象

```text
daily_rule_selections:
  daily_rule_selection_id uuid PK
  strategy_version_id uuid FK
  market_state_id uuid FK
  trade_date date
  revision_no int
  selected_rules_json/reduced_rules_json/blocked_rules_json
  quality_status
  lifecycle state
  source_run_id
  audit fields

daily_strategy_instances:
  daily_strategy_instance_id uuid PK
  strategy_version_id uuid FK
  daily_rule_selection_id uuid FK
  market_snapshot_id uuid FK market_snapshots.id
  trade_date date
  revision_no int
  risk_multiplier/position_limit/candidate_pool_snapshot_id
  payload jsonb
  lifecycle state
  audit fields

trading_day_plans:
  trading_day_plan_id uuid PK
  daily_strategy_instance_id uuid FK
  trade_date date
  revision_no int
  lifecycle state
  payload jsonb
  approved_by/approved_at/rejection_reason
  source_run_id
  audit fields
```

`signals`：

- 保留 `signal_id`；
- 增加 `trading_day_plan_id` FK、`daily_strategy_instance_id` FK、`rule_version_ids` UUID array/association、`signal_state`、`generated_at`、`available_at`、`expires_at`；
- 旧 `strategy_version_id` 字符串迁移为 canonical FK 后只保留 compatibility view。

#### `post_market_reviews`、`optimization_proposals`

```text
post_market_reviews:
  post_market_review_id uuid PK
  trading_day_plan_id uuid FK
  revision_no int
  market_snapshot_id FK
  market_state_id FK
  signal_results_json
  attribution_json
  evidence_json
  lifecycle state
  quality_status
  prompt_run_id optional
  audit fields

optimization_proposals:
  optimization_proposal_id uuid PK
  post_market_review_id uuid FK
  proposal_type proposal_type
  target_asset_type varchar(32)
  target_asset_id uuid
  base_version_id uuid
  proposed_changes jsonb
  evidence_json jsonb
  confidence numeric
  lifecycle state
  accepted_draft_version_id uuid
  audit fields
```

`proposal_type`：

```text
rule_optimization
author_profile_revision
strategy_revision
```

## 7. ORM、API、DTO 和前端边界

- ORM 是数据库映射，不承载 UI 文案或隐式业务转换。
- 领域 DTO 放在唯一 canonical 模块；Prompt Schema、运行时 DTO 和 API DTO 必须引用或转换自该模块，不复制字段定义。
- Stage 2 只建立 canonical DTO 和 compatibility adapter，不在旧 API 上直接暴露未实现的后续行为。
- 旧 API 在 Stage 2 继续可读：
  - `/api/ui/v1/article-metadata/*`
  - `/api/ui/v1/rule-pool/*`
  - `/strategy_versions/*`
  - `/backtest_results/*`
  - market snapshot/regime APIs
- 旧 API 写入规则：
  - Bootstrap 后到 `RT-S2-002` 完成前保持旧写路径；
  - `RT-S2-002` 完成后旧 writer 只能写 legacy 表或通过 canonical application service 双记录 mapping，不能双写两个正式事实源；
  - `RT-S2-003` cutover 后 canonical repository 是唯一正式 writer，旧端点使用 adapter 转发；
  - compatibility API 的响应必须包含 canonical ID/version（可为 null + quality reason），不得用文件路径作为 ID。
- 前端类型在 Stage 2 不做产品页面重写；仅在 API compatibility 需要时增加 canonical reference 字段。

## 8. Writer 所有权

| 领域 | 唯一正式 writer |
| --- | --- |
| Article/Revision | Article application service |
| PromptRun/ArticleStructure/RuleCandidate | Article analysis application service（Stage 3 接入） |
| RuleVersion/RuleFamily | Rule governance application service（Stage 4 接入） |
| DatasetSnapshot/MarketSnapshot/MarketState | Market data application service |
| BacktestRun/Applicability | Backtest application service（Stage 6 接入） |
| Author profiles | Author profile application service（Stage 7 接入） |
| StrategyVersion | Strategy application service（Stage 8 接入） |
| Daily objects | Daily trading application service（Stage 9/10 接入） |
| Migration tables/mappings | Stage 2 migration runner only |

Repository、CLI、Job、Workflow 和 API Router 不得绕过 application service 创建正式版本。

## 9. Migration chain、rollout、rollback 与恢复

### 9.1 Alembic 策略

- 从唯一 head `2026_06_03_0001` 建立线性 Stage 2 migration。
- `RT-S2-002` 预计至少拆分为：

```text
2026_06_xx_0001_stage2_metadata_alignment
2026_06_xx_0002_stage2_domain_schema
2026_06_xx_0003_stage2_compatibility_views
```

- 不创建新 branch head。
- metadata alignment 只使 Alembic 正确认识现有表，不得把“removed table”作为删除指令。
- 所有 constraint/index 名显式控制在 PostgreSQL 63 字符内。

### 9.2 Rollout

```text
1. 备份 + preflight report
2. metadata alignment
3. additive tables/columns/enums
4. compatibility views/adapters
5. deploy read-old/write-old compatibility
6. RT-S2-003 backfill in bounded batches
7. compare counts, hashes, rejected/conflicts
8. canonical read shadow comparison
9. canonical writer cutover
10. legacy tables read-only
```

Stage 2 不删除 legacy 表和文件。

### 9.3 Rollback

- Schema migration 在无 canonical 写入前必须支持 Alembic downgrade。
- 一旦 canonical writer cutover：
  - 不通过 destructive downgrade 删除新数据；
  - 先停止 writer，导出 canonical delta，恢复 legacy writer，按 mapping 反向同步可表达字段；
  - 无法反向表达的字段保存在 recovery export 和 quality report。
- 每次 migration run 记录恢复点、批次 cursor 和 source fingerprint。

### 9.4 故障检测与恢复

检测：

- migration status 非 completed；
- pre/post count 不满足规则；
- mapping duplicate；
- FK orphan；
- canonical hash 与 source snapshot 不一致；
- 同一 source fingerprint 产生不同 canonical ID；
- rejected/conflict 数超过阈值；
- compatibility read 与 canonical read 不一致。

恢复：

- 事务内批次失败自动 rollback；
- 事务外批次使用 idempotency key 和 upsert，不覆盖人工修订；
- 从最后 completed cursor 重跑；
- 冲突写 `migration_conflicts`，不自动选择；
- rejected 写 `migration_run_items` 并保存原始 payload、错误代码和可重试标志。

## 10. RT-S2-003 迁移覆盖

| Legacy 数据 | 目标 | 规则 |
| --- | --- | --- |
| `raw_articles` + `blog_articles` | Article + ArticleRevision + mapping | 131/131 URL 对应；Article 使用现有 blog UUID；raw 记录保留 provenance；`is_processed=false` 标 `ambiguous` |
| `article_metadata` v1/v2 | PromptRun + ArticleStructure + RuleCandidate | 每条原始输出保存；没有 prompt version 时标 `legacy_unknown`；不自动批准 |
| `article_metadata_selections` | ArticleStructure approval/selection event | 7 条 auto selection 迁移为 compatibility selection，不升级为 human approval |
| `rule_pool` | RuleCandidate/RuleVersion/RuleFamily mapping | approved 也不能无条件 published；人工来源可证实才 approved，否则 draft/legacy_only |
| `rule_pool.backtest_result` | BacktestRun compatibility observation | 保存原 JSON、指标和 quality；无 DatasetSnapshot 时 `unresolved` |
| `backtest_result_runs`/文件 | BacktestRun | 当前 DB 为 0；扫描兼容文件和 Job result，不能仅按 DB 0 宣告无数据 |
| `TraderProfilesFile`/Persona clusters | Author profile drafts | 不将推断写成事实；来源证据缺失时 `legacy_only` |
| `trader_memory` | review evidence/proposal legacy mapping | 当前 DB 为 0；文件/历史产物仍扫描 |
| `trader_strategy_versions` + candidate JSON | StrategyVersion drafts/mapping | 当前 DB 为 0；日级 recommendation 不解释成稳定正式策略 |
| `market_datasets`/OHLCV | DatasetSnapshot manifest | 当前 market dataset 0；84 OHLCV 明确为 partial，不生成“完整数据集” |
| Kaipan 文件/market snapshots | MarketSnapshot mapping | 扫描 Job 与 raw 文件；缺 snapshot manifest 时 `partial` |
| daily reports/sessions、report JSON、Job artifacts | TradingDayPlan/PostMarketReview compatibility records | Markdown/JSON 保留原文和日期；无法区分盘前/盘后时 `ambiguous` |

每类迁移必须输出：

```text
source_count
eligible_count
migrated_count
skipped_idempotent_count
rejected_count
conflict_count
target_count_before
target_count_after
quality_status_counts
orphan_count
hash_mismatch_count
```

## 11. Task Card：RT-S2-001 定义核心领域对象

**目标：** 在不修改数据库和业务行为的前提下，实现并验证本计划冻结的 canonical 领域 DTO、枚举、关系、ID、版本、生命周期、来源、质量和 compatibility mapping 合同。

**风险：** M3，核心领域与正式事实源。

**依赖：** Stage 1 已接受；本 Bootstrap 计划已批准。无下游 Task 可并行。

**已核验事实：**

- 现有对象散落于 ORM、Pydantic、dataclass、API schema 和前端类型。
- 同名 `MarketSnapshot`、多种 `MarketState`、两套 StrategyVersion 是明确冲突。
- 现有生命周期枚举互不一致，缺完整状态历史。

**适用约束：**

- Domain contract constraints。
- AGENTS 单一事实源、版本、审核、Proposal 和事实分类要求。

**冻结合同：**

- 本文第 4、5、7、8 节全部内容。
- 不得改变 ID、版本、生命周期、正式事实源或对象关系。

**允许路径：**

```text
trade-strategy-ai/src/domain/**
trade-strategy-ai/src/schemas/**（仅 compatibility import/adapter）
trade-strategy-ai/src/models/**（仅类型引用或命名冲突准备，不改表）
trade-strategy-ai/api/schemas/**（仅 DTO adapter）
trade-strategy-ai/web/src/types/**（仅生成/映射边界，必要时）
trade-strategy-ai/tests/unit/domain/**
trade-strategy-ai/tests/unit/schemas/**
trade-strategy-ai/tests/api/test_ui_openapi_contract.py
trade-strategy-ai/docs/refactor-implementation-logs/stage-2.md
trade-strategy-ai/docs/Refactor-Implementation-Log.md
```

**禁止路径：**

```text
trade-strategy-ai/src/db/migrations/**
trade-strategy-ai/prompts/**
trade-strategy-ai/data/**
trade-strategy-ai/daily-report/**
trade-strategy-ai/daily-sessions/**
Stage 3+ 页面、Service 和运行行为
```

**精确输出：**

- canonical domain enum 与 DTO 模块；
- 每个核心对象的 typed reference；
- lifecycle transition validator；
- provenance/quality/audit/value objects；
- legacy-to-canonical mapping contracts；
- 无数据库写入的 compatibility adapter；
- 合同测试和 import/convergence 测试。

**focused tests：**

```bash
cd trade-strategy-ai
../.venv/bin/python -m pytest tests/unit/domain tests/unit/schemas -q
../.venv/bin/python -m pytest tests/unit/models/test_models.py tests/unit/models/test_stage1_models.py tests/api/test_ui_openapi_contract.py -q
../.venv/bin/python -m mypy src/domain api/schemas
cd ..
git diff --check
```

若仓库没有可用 mypy 配置，记录未运行原因并以 import compile + Pydantic schema tests 替代，不得虚报。

**API/合同验证：**

- 同一 enum/字段只定义一次；
- 旧 API DTO 通过显式 adapter 转换；
- JSON Schema snapshot 无循环引用和未定义类型；
- formal version、runtime instance、proposal 不可互换。

**完成条件：**

- 所有 19 个核心对象都有唯一职责、ID、关系、生命周期和事实源；
- tests 通过；
- Parent Review 未发现第二套 Schema；
- Stage 日志更新。

**停止条件：**

- 需要改动数据库；
- 现有对象无法在冻结关系中无损表示；
- 需要改变本计划 ID/版本/状态；
- API compatibility 需要双写；
- 发现未识别的正式 writer。

**gpt-5.5 升级条件：**

- 任一停止条件；
- 对 Article/Rule/Profile/Strategy/MarketState 的事实源有新冲突；
- 需要增加或删除核心对象；
- 生命周期无法满足人工审核或 proposal 边界。

## 12. Task Card：RT-S2-002 重构数据库

**目标：** 基于已接受的 RT-S2-001 合同，建立目标 ORM、表、FK、索引、唯一约束、枚举、PromptRun 存储、migration observability 与 compatibility 基础；不迁移业务数据。

**风险：** M3，Schema 和 migration chain。

**依赖：** `RT-S2-001 [x]` 且 Parent 接受；禁止提前开始。

**已核验事实：**

- DB 位于单一 head，但 `alembic check` 失败；
- metadata 注册不完整；
- 现有表大多无正式 FK；
- Stage 2 目标中部分表可复用，部分必须新增。

**适用约束：**

- Database migration constraints。
- 若实现发现领域关系仍未解决，同时应用 Domain contract constraints 并立即升级。

**冻结合同：**

- 本文第 4～9 节；
- PromptRun 字段；
- 单一 writer 和 compatibility 规则；
- migration chain 线性策略。

**允许路径：**

```text
trade-strategy-ai/src/models/**
trade-strategy-ai/src/db/migrations/**
trade-strategy-ai/src/db/repositories/**
trade-strategy-ai/src/domain/**
trade-strategy-ai/src/services/*compat*
trade-strategy-ai/tests/unit/db/**
trade-strategy-ai/tests/unit/models/**
trade-strategy-ai/tests/integration/test_db.py
trade-strategy-ai/tests/unit/backup/**
trade-strategy-ai/docs/refactor-implementation-logs/stage-2.md
trade-strategy-ai/docs/Refactor-Implementation-Log.md
```

**禁止路径：**

```text
trade-strategy-ai/prompts/**
trade-strategy-ai/web/src/pages/**
trade-strategy-ai/data/**
任何批量数据 backfill
删除 legacy 表/列/文件
Stage 3+ 行为
```

**精确输出：**

- metadata import convergence；
- 不产生 destructive autogenerate 的 baseline；
- 目标 ORM 和迁移；
- canonical repository 接口与旧 repository adapter；
- migration/quality/mapping/lifecycle 表；
- backup manifest 覆盖新表；
- upgrade/downgrade 或 safe-rerun 测试。

**migration 顺序：**

1. 修复 metadata 注册、命名和 ORM/DB 漂移识别；
2. 建立 enums 和支撑表；
3. 建立文章/规则/画像/策略/每日对象表；
4. 对可复用表做 additive 改造或安全 rename；
5. 建 compatibility views/adapters；
6. 不 backfill 正式业务数据。

**focused tests：**

```bash
cd trade-strategy-ai
../.venv/bin/python -m pytest tests/unit/db/test_migrations.py tests/unit/db/test_stage1_migration.py tests/unit/models tests/unit/backup -q
../.venv/bin/python -m pytest tests/api/routers/test_articles.py tests/api/routers/ui/test_article_metadata.py tests/api/routers/test_rule_pool.py tests/api/routers/test_strategy_versions.py tests/api/routers/test_backtest_results.py tests/api/routers/test_market_ui.py -q
../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini heads
../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini upgrade head
../.venv/bin/python -m alembic -c src/db/migrations/alembic.ini check
cd ..
git diff --check
```

在隔离临时 PostgreSQL 上额外验证：

```text
base → head upgrade
head → Stage 2 base downgrade（若安全）
Stage 2 base → head re-upgrade
existing-data fixture upgrade
constraint/index/FK inspection
```

**完成条件：**

- 单一 Alembic head；
- `alembic check` 不再报告未注册表或意外删除；
- 目标 Schema 与 RT-S2-001 合同一致；
- 旧 API read compatibility 通过；
- migration 未迁移/删除业务数据；
- rollback 或明确 safe-rerun 通过。

**停止条件：**

- 需要修改冻结领域关系；
- 需要数据解释才能完成 DDL；
- 现有 head 无法线性升级；
- downgrade 会静默丢失 canonical 写入；
- autogenerate 仍提出未解释的 drop；
- 多个 writer 必须同时修改 shared ORM/migration。

**gpt-5.5 升级条件：**

- 任一停止条件；
- 需要新 branch head；
- 需要物理 rename 与 compatibility view 之间重新决策；
- 发现生产数据使用未建模 FK/自然键；
- migration 无法在维护窗口内事务化或分批恢复。

## 13. Task Card：RT-S2-003 数据迁移

**目标：** 使用 RT-S2-002 已接受 Schema，将全部列明 legacy 数据以幂等、可观察、可恢复方式迁入 canonical 对象，保留 provenance、原始值和 old-to-new ID。

**风险：** M3，数据转换与 cutover。

**依赖：** `RT-S2-002 [x]`、目标 Schema 和 migration chain 已由 Parent 接受；禁止提前开始。

**已核验事实：**

- 当前主要非空数据和数量见第 2.4 节；
- DB 之外仍有 JSON/JSONL、Job result、Markdown daily reports/sessions 和 compatibility files；
- legacy 状态不能直接等同新正式生命周期。

**适用约束：**

- Database migration constraints。
- 对仍影响来源、版本、状态的转换同时应用 Domain contract constraints。

**冻结合同：**

- 本文第 4、5、8、9、10 节；
- 不允许重新解释 legacy approved/released；
- 所有 ambiguity 必须显式 quality status。

**允许路径：**

```text
trade-strategy-ai/scripts/migrate_stage2_*.py
trade-strategy-ai/src/migrations/**
trade-strategy-ai/src/db/repositories/**
trade-strategy-ai/tests/unit/scripts/**
trade-strategy-ai/tests/integration/**
trade-strategy-ai/tests/fixtures/**
trade-strategy-ai/docs/refactor-implementation-logs/stage-2.md
trade-strategy-ai/docs/Refactor-Implementation-Log.md
```

**禁止路径：**

```text
trade-strategy-ai/prompts/**
trade-strategy-ai/web/src/pages/**
直接编辑或删除 trade-strategy-ai/data 下 legacy 文件
删除 legacy 表/列
Stage 3 批量 Prompt 重处理
任何无法生成 migration report 的临时脚本
```

**精确输出：**

- preflight inventory；
- dry-run；
- 分领域迁移器；
- migration run/item/conflict/quality report；
- old-to-new mapping；
- read shadow comparison；
- writer cutover 开关；
- recovery export；
- idempotency、failure injection 和 resume tests。

**focused tests：**

```bash
cd trade-strategy-ai
../.venv/bin/python -m pytest tests/unit/scripts/test_stage2_migration.py tests/integration/test_stage2_data_migration.py -q
../.venv/bin/python scripts/migrate_stage2_data.py --dry-run --report-dir <temp-dir>
../.venv/bin/python scripts/migrate_stage2_data.py --apply --batch-size 50 --report-dir <temp-dir>
../.venv/bin/python scripts/migrate_stage2_data.py --apply --batch-size 50 --report-dir <temp-dir>
../.venv/bin/python scripts/migrate_stage2_data.py --verify --report-dir <temp-dir>
../.venv/bin/python -m pytest tests/api/routers/test_articles.py tests/api/routers/ui/test_article_metadata.py tests/api/routers/test_rule_pool.py tests/api/routers/test_strategy_versions.py tests/api/routers/test_backtest_results.py tests/api/routers/test_market_ui.py -q
cd ..
git diff --check
```

`<temp-dir>` 是执行时临时目录，不写入正式文档或业务引用。

**专项验证：**

- pre/post counts 与第 10 节字段齐全；
- 第二次 apply 只产生 `skipped_idempotent`，不新增重复对象；
- 注入中途失败后可从 cursor 恢复；
- mapping 无重复、FK 无 orphan；
- 旧 API 与 canonical shadow read 关键字段一致；
- 文件路径只出现在 provenance/storage ref，不作为 canonical ID；
- rejected/conflict/quality report 可定位原始记录。

**完成条件：**

- 所有迁移类别有明确 migrated/empty/rejected/conflict 结论；
- 当前实际 131 文章、262 metadata、7 selection、14 rule、84 OHLCV 等完成对账；
- legacy 数据继续可读；
- canonical writer cutover 有验证证据；
- 未删除 legacy 数据；
- Parent Review 接受。

**停止条件：**

- preflight count 与 Bootstrap 差异无法解释；
- 同一 legacy ID 映射到多个 canonical ID；
- 需要覆盖人工修改；
- 需要把推断提升为事实；
- 无法区分稳定策略与日级实例；
- 失败后不能恢复；
- 需要修改 Schema 或领域关系。

**gpt-5.5 升级条件：**

- 任一停止条件；
- rejected/conflict 超出预设阈值；
- compatibility read 与 canonical read 存在业务语义差异；
- writer cutover 会造成双写或停机风险；
- 发现新的文件正式事实源或未列明历史数据库。

## 14. Stage 2 Gate 与 Stage 3 入口证据

Stage 3 只有在 gpt-5.5 Parent 逐项确认后才允许开始：

1. `RT-S2-001`、`RT-S2-002`、`RT-S2-003` 分别 `[x]`，没有合并实现。
2. domain、ORM、数据库、API adapter 和前端 reference 字段一致。
3. 19 个核心对象各有唯一正式事实源。
4. 稳定 ID、版本关系、生命周期和审计事件通过测试。
5. 单一 Alembic head，metadata 完整，`alembic check` 无未解释漂移。
6. upgrade、downgrade 或 safe-rerun、故障恢复通过。
7. migration report 覆盖所有非空 legacy 数据和文件来源。
8. 无静默丢失、覆盖或事实重解释。
9. 文件路径不再是正式业务 ID。
10. PromptRun 可以保存 prompt/schema/model/input/raw output/validation/token/cost 元数据。
11. 旧 API 和文件仍可 compatibility read，旧 writer 已受控。
12. 未引入 Stage 3 Prompt 调用、批量重处理或后续 Stage 业务行为。

## 15. 当前风险与阻塞

### 非阻塞但必须在 RT-S2-002 解决

- Alembic metadata 与实际数据库漂移，`alembic check` 当前失败。
- ORM constraint name 与实际 migration name 不一致且超长。
- JSON 与 JSONB 历史类型混用。
- 现有 FK 缺失，多个关系只保存字符串/JSON。
- `raw_articles.is_processed=false` 与已清洗文章并存。

### 阻塞条件

- Bootstrap 本身无阻塞，Stage 2 可以开始。
- `RT-S2-002` 被 `RT-S2-001` 接受阻塞。
- `RT-S2-003` 被 `RT-S2-002` Schema、migration chain 和 rollback 接受阻塞。
- Stage 3 被完整 Stage 2 Gate 阻塞。

## 16. 下一可执行 Task

```text
RT-S2-001 定义核心领域对象
```

执行时只实现 Task Card 第 11 节，不修改数据库，不开始 `RT-S2-002` 或 Stage 3。
