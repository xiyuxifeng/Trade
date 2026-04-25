# TaskList

> 本文件是 `trade-strategy-ai` 的唯一执行入口。
> 目标不是“记录想法”，而是确保任何人在没有历史上下文时，也能继续把项目推进到可交付状态。
> 旧 `docs/TaskList.md`、旧 `docs/Proposed-Plan/TaskList.md`、以及其他历史计划文档只保留参考价值，不再作为执行入口。

---

## 1. 文档用途

本清单同时承担 4 个作用：

1. 定义项目最终交付目标。
2. 定义当前代码与目标的差距。
3. 定义从当前状态到最终交付的唯一任务路径。
4. 定义每个任务的输入、输出、前置依赖、验收标准与并行边界。

---

## 2. 使用说明

### 2.1 无上下文接手规则

新的执行者在没有历史上下文时，必须按以下顺序接手：

1. 阅读 [Project.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/Project.md:1)，理解当前项目结构。
2. 阅读 [Plan.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/Plan.md:1)，理解当前阶段目标。
3. 阅读 [需求.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/需求.md:1)，理解最终交付要求。
4. 阅读本文件，确认当前 Stage、未完成任务、依赖关系和验收标准。
5. 只从“未完成且前置依赖已满足”的任务开始执行。

### 2.2 任务状态规则

- `[ ]` 未开始
- `[-]` 进行中
- `[x]` 已完成
- `[!]` 阻塞

### 2.3 任务完成规则

一个任务只有同时满足以下条件，才能标记为完成：

1. 目标已经实现。
2. 输出物已经落地到明确路径。
3. 验收标准已经满足。
4. 相关测试、样例验证或手工验证已经完成。
5. 文档或配置更新已补齐。

### 2.4 任务字段说明

每个任务都使用相同字段：

- `目标`：这项任务要解决什么问题。
- `输入`：开始执行前必须已经具备的内容。
- `输出`：任务完成后必须新增或修改的产物。
- `修改范围`：需要改动的文件或模块。
- `前置依赖`：必须先完成的任务。
- `可并行`：哪些任务可以和它同时做。
- `验收标准`：做到什么程度才算完成。
- `完成情况`: 记录完成的内容和结果。
- `备注`: 可选，其他需要注意的事项和说明。

### 2.5 执行原则

- 所有任务优先保证“可落盘、可回放、可验证”。
- 私有接口必须先经 `provider + snapshot` 隔离，不直接绑死主流程。
- 不继续扩展旧 `watchlist + last_price` 路径。
- 不把复杂逻辑继续堆进 `ManagerAgent`。
- 能做成 module/service 的，不强行做成独立 Agent。

---

## 3. 最终交付目标

项目完成后，必须达到以下交付状态：

1. 能持续抓取和保存市场快照、文章抽取结果、策略版本、盘前建议、盘后评估。
2. 能按 `trader_id` 生成独立策略版本，并基于快照与画像生成盘前建议。
3. 能在盘后做统一评分、归因、记忆写回和 ranking。
4. 能用同一套快照和评分口径做离线回测与规则验真。
5. 能基于盘后结果和回测结果产生候选优化版本，而不是直接覆盖正式版本。
6. 有稳定的 CLI/API/任务编排入口，可以重复运行关键链路。
7. 文档、目录、任务清单收敛为单一主线，没有互相冲突的历史入口。

---

## 4. 当前代码现状与主要缺口

### 4.1 已有基础

- 配置加载、CLI、API、APScheduler、最小盘前/盘后闭环已经存在。
- 文章抓取、清洗、抽取、增量处理 pipeline 已存在。
- `blog_articles`、`article_metadata`、`market_data`、`trade_logs`、`raw_articles`、`crawl_state` 已落库。
- `TraderProfile`、`TraderMemory`、`StrategyAgent`、`RiskAgent`、`SignalVersioning` 已有最小骨架。
- AKShare 个股、指数、行业板块、概念板块日线同步能力已存在。

### 4.2 关键缺口

- `DataAgent` 仍然只支持 `last_price`。
- `TraderAgent` 仍然是 `watchlist + last_price` 模板。
- `ManagerAgent` 仍然是最小编排，缺少策略版本、候选池、Evidence Pack、ranking。
- 缺 `market_universe`、`strategy_library`、`evaluation`、`backtest` 等主线模块。
- 缺稳定的数据快照资产，无法支持回测与学习闭环。
- `TraderProfile`、`TraderMemory`、`SignalVersioning` 的结构都还不够支撑完整闭环。

### 4.3 唯一主线

本项目后续唯一主线是：

`数据快照 -> provider -> 市场候选池 -> per-trader 策略版本 -> 盘前决策 -> 盘后评估/归因 -> 回测验真 -> 自主优化`

---

## 5. 优先级定义

- `P0`：阻塞主链路，不完成就不能继续推进。
- `P1`：主链路核心能力，应在前置完成后立即推进。
- `P2`：增强与扩展能力，应在主链路稳定后推进。

---

## 6. 最终可交付标准

只有当以下标准全部满足，项目才视为“可交付”：

### 6.1 数据资产

- 存在稳定的 `raw / normalized / snapshots` 三层数据目录。
- 至少能稳定保存 `hot_topics / topic_constituents / strong_symbols / ohlcv_1d` 的每日快照。
- 每份快照都能追溯抓取时间、请求参数、来源 provider、版本信息。

### 6.2 盘前链路

- 能按交易日为每个 trader 生成策略版本。
- 能基于候选池、画像、记忆、策略版本输出结构化 `TradeIdea`。
- 输出可以追溯到快照、策略版本和证据引用。

### 6.3 盘后链路

- 能对盘前建议进行统一评分。
- 能生成 Evidence Pack、失败归因和 ranking。
- 能把 postmortem 与策略调整建议写回记忆层。

### 6.4 回测与规则验真

- 能在离线模式下按 trader / 日期区间重放策略版本与市场快照。
- 能对高频 LLM 规则做程序化命中验证。
- 回测与线上评分使用统一 scoring 口径。

### 6.5 运行与文档

- 关键链路存在 CLI 入口，至少包括：抓快照、构建策略版本、盘前执行、盘后评估、回测。
- 关键链路具备最小测试、样例或可重复手工验证方法。
- `Project.md / Plan.md / 需求.md / TaskList.md` 与代码现状一致。

---

## 7. 执行顺序总览

1. Stage 0：统一文档与数据底座
2. Stage 1：配置、契约、模型与迁移
3. Stage 1.5：Agent 边界收敛
4. Stage 2：Provider 与市场候选池
5. Stage 3：按 trader 的策略版本库
6. Stage 4：盘前主链路升级
7. Stage 5：盘后评估与学习闭环
8. Stage 6：离线回测与规则验真
9. Stage 7：自主优化与可观测性

---

## 8. Stage 0：统一主线与数据底座（P0）

### Stage 目标

- 文档入口唯一化。
- 私有接口数据先资产化，不直接绑定主流程。
- 为后续 provider 和快照体系打底。

### 阶段交付物

- 收敛后的主文档。
- `kaipan` 抓取目录规范。
- 原始、标准化、快照三层样例数据。
- `kaipan_provider.py` 最小可扩展草案。

### 任务清单

- [x] `NTL-S0-001` `P0`
  目标：将 `docs/TaskList.md` 设为唯一主清单。
  输入：旧任务文档。
  输出：新主清单入口说明。
  修改范围：`docs/TaskList.md`、旧 TaskList 文档顶部说明。
  前置依赖：无。
  可并行：`NTL-S0-002` ~ `NTL-S0-006`。
  验收标准：旧任务文档不再作为执行入口。

- [x] `NTL-S0-002` `P0`
  目标：收敛 `Project.md` 为项目结构说明。
  输入：当前仓库真实目录。
  输出：与当前目录对齐的 `Project.md`。
  修改范围：`docs/Project.md`。
  前置依赖：无。
  可并行：`NTL-S0-001`、`NTL-S0-003`、`NTL-S0-005`。
  验收标准：文档不再混入失效结构或伪存在目录。

- [x] `NTL-S0-003` `P0`
  目标：把 `kaipan` 私有接口纳入规划入口，但不直接绑主流程。
  输入：`kaipan.md` 接口说明。
  输出：接口映射文档与 provider 规划说明。
  修改范围：`docs/Kaipan-Interface-Mapping.md`、规划文档。
  前置依赖：无。
  可并行：`NTL-S0-001`、`NTL-S0-002`。
  验收标准：高价值接口与主线任务已有映射关系。

- [x] `NTL-S0-004` `P1`
  目标：废除旧任务文档的执行入口地位。
  输入：旧 `TaskList` 文档。
  输出：历史参考标记。
  修改范围：旧 `docs/TaskList.md`、旧 `docs/Proposed-Plan/TaskList.md`。
  前置依赖：`NTL-S0-001`。
  可并行：`NTL-S0-005`。
  验收标准：任何人不会把旧文档误当主清单。

- [x] `NTL-S0-005` `P0`
  目标：收敛最终保留文档并归档无效文档。
  输入：当前 `docs/` 目录。
  输出：保留 `Project.md / Plan.md / 需求.md / TaskList.md / Kaipan-Interface-Mapping.md`，其余按 `bak` 或 `Deprecated` 归档。
  修改范围：`docs/`。
  前置依赖：无。
  可并行：`NTL-S0-001` ~ `NTL-S0-004`。
  验收标准：当前入口文档唯一且历史文档归档位置明确。

- [x] `NTL-S0-006` `P0`
  目标：把 Agent 保留/降级/冻结边界写入文档。
  输入：现有 `src/agents/` 结构与目标架构。
  输出：文档中的 Agent 边界说明。
  修改范围：`docs/Project.md`、`docs/需求.md`、`docs/Plan.md`。
  前置依赖：无。
  可并行：`NTL-S0-002`、`NTL-S0-005`。
  验收标准：后续不再以“每种能力都建一个 Agent”为默认方向。

- [x] `NTL-S0-007` `P0`
  目标：定义 `kaipan` 数据目录规范。
  输入：现有 `data/` 目录和 `kaipan.md`。
  输出：`raw / snapshots` 目录结构说明与样例路径约定。
  修改范围：`data/` 目录规范文档。
  前置依赖：`NTL-S0-003`。
  可并行：`NTL-S0-008`、`NTL-S0-010`。
  验收标准：至少明确到日期、接口、快照类型三级路径命名规则。
  完成情况：已创建 `data/kaipan/raw/` 和 `data/kaipan/snapshots/` 目录骨架，commit `8ff96e7`。

- [x] `NTL-S0-008` `P0`
  目标：确定首批 13 个高价值接口并实现原始 JSON 保存。
  输入：`kaipan.md` 接口列表。
  输出：首批接口名单和原始响应保存逻辑。
  修改范围：`src/providers/kaipan_provider.py`、样例数据目录。
  前置依赖：`NTL-S0-007`。
  可并行：`NTL-S0-009`、`NTL-S0-010`。
  验收标准：13 个接口可以保存原始 JSON 到 `raw` 层。
  完成情况：13 个接口全部实现（commit `6ede745` → `3090ce8`），支持多域名（apphis/applhb/apphwshhq）、POST/GET 方法、meta 嵌入、文件名含 api_name + 关键参数。

- [x] `NTL-S0-009` `P0`
  目标：定义并输出标准化快照 JSON。
  输入：原始 JSON 响应。
  输出：`hot_topics`、`topic_constituents`、`strong_symbols`、`market_context` 的标准化快照文件。
  修改范围：`src/providers/kaipan_normalizer.py`、`src/providers/kaipan_schema/`、`data/snapshots`。
  前置依赖：`NTL-S0-007`、`NTL-S0-008`。
  可并行：`NTL-S0-010`。
  验收标准：四类标准化快照字段结构稳定，且样例可读取。
  完成情况：Normalizer 实现完成（commit `5004e41` → `1946cf5`），4 个 YAML schema 文件，11/11 测试 PASS。

- [x] `NTL-S0-010` `P0`
  目标：为每次抓取记录元信息。
  输入：抓取请求与响应。
  输出：包含请求参数、抓取时间、接口版本、鉴权来源的元信息记录。
  修改范围：`src/providers/kaipan_provider.py`。
  前置依赖：`NTL-S0-007`。
  可并行：`NTL-S0-008`、`NTL-S0-009`。
  验收标准：任意一份 raw/snapshot 数据都能追溯来源。
  完成情况：`_save_raw()` 方法内嵌 meta（dataset、trade_date、slot、fetched_at、source、request），与 NTL-S0-008 合并实现（commit `3090ce8`）。

- [x] `NTL-S0-011` `P1`
  目标：验证接口字段稳定性与分页规则。
  输入：首批 8 个接口抓取能力。
  输出：最近 20 到 60 个交易日的样本数据和字段稳定性结论。
  修改范围：抓取脚本、验证脚本、记录文档。
  前置依赖：`NTL-S0-008`、`NTL-S0-009`、`NTL-S0-010`。
  可并行：`NTL-S0-014`。
  验收标准：能明确哪些字段稳定、哪些字段存在缺失或分页差异。
  完成情况：最近 30 个交易日、13 个接口批量抓取验证完成；`RealRankingInfo`、`GetFengKListBest`、`GetInterviewsByDateStock`、`GetZhangTingTianTi` 的历史/今日差异已在 normalizer 里归一化；测试 `22 passed`。

- [x] `NTL-S0-012` `P0`
  目标：建立 `src/providers/kaipan_provider.py` 草案。
  输入：接口映射设计。
  输出：Provider 草案文件。
  修改范围：`src/providers/kaipan_provider.py`。
  前置依赖：`NTL-S0-003`。
  可并行：`NTL-S0-007`。
  验收标准：已定义 provider 边界，不直接侵入 Agent 主流程。

- [x] `NTL-S0-013` `P0`
  目标：建立 `src/providers` 包结构。
  输入：provider 规划。
  输出：`src/providers/__init__.py` 等基础结构。
  修改范围：`src/providers/`。
  前置依赖：无。
  可并行：`NTL-S0-012`。
  验收标准：provider 目录可以作为后续 Stage 的基础模块。

- [x] `NTL-S0-014` `P1`
  目标：为 `kaipan` 抓取器补最小验证。
  输入：raw/snapshot 三层样例数据。
  输出：最小测试、样例断言或离线验证脚本。
  修改范围：`tests/providers/test_kaipan_pipeline.py`。
  前置依赖：`NTL-S0-009`、`NTL-S0-010`。
  可并行：`NTL-S0-011`。
  验收标准：抓取器至少有一条可重复验证路径。
  完成情况：11 个离线验证测试全部 PASS（commit `52ebfdf`）。

### Stage 0 完成标准

- 文档入口已收敛。
- `kaipan` 数据可以稳定落到三层目录。
- 数据来源与元信息可追溯。

---

## 9. Stage 1：配置、契约、模型与迁移（P0）

### Stage 目标

- 为新链路补齐配置、schema、模型、migration。
- 保证新旧链路可共存，避免后续返工。

### 阶段交付物

- 新配置项。
- 新合同与 schema。
- 新表结构与 migration。
- 最小模型测试。

### 任务清单

- [x] `NTL-S1-001` `P0`
  目标：扩展配置 schema，支持 provider、snapshot、kaipan。
  输入：现有 `src/common/config.py`。
  输出：新增配置字段与默认值。
  修改范围：`src/common/config.py`。
  前置依赖：Stage 0 完成。
  可并行：`NTL-S1-002`。
  验收标准：配置层能表达 provider、快照与抓取参数。
  完成情况：已补充 `KaipanConfig`，并保留 `token/user_id`、fetch schedule、default headers、重试参数等可配置项。

- [x] `NTL-S1-002` `P0`
  目标：更新 CLI 默认 YAML 模板。
  输入：新配置 schema。
  输出：默认 YAML 模板中的新配置段。
  修改范围：`cli/main.py`、模板文件。
  前置依赖：`NTL-S1-001`。
  可并行：无。
  验收标准：新配置可以通过 CLI 初始化或展示。
  完成情况：`init-config` 默认模板已加入 `kaipan` 段，并在生成时归一化制表符为可解析 YAML。

- [x] `NTL-S1-003` `P0`
  目标：扩展 `DataRequest/DataResponse` 相关契约。
  输入：现有 `src/schemas/contracts.py`。
  输出：支持 `hot_topics`、`topic_constituents`、`strong_symbols`、`ohlcv_1d`、`indicators`。
  修改范围：`src/schemas/contracts.py`。
  前置依赖：Stage 0 完成。
  可并行：`NTL-S1-004`、`NTL-S1-005`。
  验收标准：新字段可被 DataAgent 消费和返回。

- [x] `NTL-S1-004` `P0`
  目标：扩展 `TradeIdea`。
  输入：现有交易建议 schema。
  输出：新增 `strategy_version_id`、`source_topic_ids`、`evidence_refs`、`decision_mode`。
  修改范围：`src/schemas/contracts.py` 或相关 schema 文件。
  前置依赖：Stage 0 完成。
  可并行：`NTL-S1-003`、`NTL-S1-005`。
  验收标准：盘前建议结构足以支撑追溯。

- [x] `NTL-S1-005` `P0`
  目标：扩展盘后评估契约。
  输入：现有 `EvaluationResult` 与 review task schema。
  输出：Evidence Pack、失败分类、ranking features 相关字段。
  修改范围：`src/schemas/contracts.py`、`src/schemas/review_task.py`。
  前置依赖：Stage 0 完成。
  可并行：`NTL-S1-003`、`NTL-S1-004`。
  验收标准：盘后评估 schema 足以支持后续归因和 ranking。

- [x] `NTL-S1-006` `P0`
  目标：新增 `trader_strategy_version` 模型。
  输入：策略版本设计。
  输出：模型定义。
  修改范围：`src/models/`。
  前置依赖：`NTL-S1-001`。
  可并行：`NTL-S1-007`、`NTL-S1-008`、`NTL-S1-009`。
  验收标准：模型字段能追溯 trader、版本状态、证据来源。

- [x] `NTL-S1-007` `P0`
  目标：新增 `hot_topics_snapshot` 模型。
  输入：快照 schema 设计。
  输出：模型定义。
  修改范围：`src/models/`。
  前置依赖：`NTL-S1-001`、`NTL-S1-003`。
  可并行：`NTL-S1-006`、`NTL-S1-008`、`NTL-S1-009`。
  验收标准：模型能承载每日热点快照。

- [x] `NTL-S1-008` `P0`
  目标：新增 `topic_constituents_snapshot` 模型。
  输入：快照 schema 设计。
  输出：模型定义。
  修改范围：`src/models/`。
  前置依赖：`NTL-S1-001`、`NTL-S1-003`。
  可并行：`NTL-S1-006`、`NTL-S1-007`、`NTL-S1-009`。
  验收标准：模型能承载题材成分快照。

- [x] `NTL-S1-009` `P0`
  目标：新增 `strong_symbols_snapshot` 模型。
  输入：快照 schema 设计。
  输出：模型定义。
  修改范围：`src/models/`。
  前置依赖：`NTL-S1-001`、`NTL-S1-003`。
  可并行：`NTL-S1-006`、`NTL-S1-007`、`NTL-S1-008`。
  验收标准：模型能承载强势池快照。

- [x] `NTL-S1-010` `P1`
  目标：扩展 `signal` 模型追踪字段。
  输入：现有 `src/models/signal.py`。
  输出：新增 trader、version、topic、evaluation 追踪字段。
  修改范围：`src/models/signal.py`。
  前置依赖：`NTL-S1-004`、`NTL-S1-005`、`NTL-S1-006`。
  可并行：`NTL-S1-011`。
  验收标准：signal 能串联盘前与盘后上下文。

- [x] `NTL-S1-011` `P0`
  目标：新增 migration。
  输入：所有新增模型。
  输出：Alembic 迁移文件。
  修改范围：`src/db/migrations/`。
  前置依赖：`NTL-S1-006` ~ `NTL-S1-010`。
  可并行：`NTL-S1-013`。
  验收标准：数据库可创建新增表和字段。

- [x] `NTL-S1-012` `P0`
  目标：重构配置代码，避免继续只服务旧最小闭环。
  输入：扩展后的配置 schema。
  输出：配置读取逻辑对新旧链路兼容。
  修改范围：`src/common/config.py` 及相关配置消费方。
  前置依赖：`NTL-S1-001`。
  可并行：`NTL-S1-003`、`NTL-S1-004`、`NTL-S1-005`。
  验收标准：现有链路仍可运行，新字段可被正确消费。
  完成情况：`load_app_config` / `KaipanConfig` / CLI 默认模板 / 现有消费方已对齐，新旧链路可以共存。

- [x] `NTL-S1-013` `P1`
  目标：为新增模型与 migration 补最小测试。
  输入：新增模型与迁移。
  输出：模型测试、迁移测试或最小验证脚本。
  修改范围：`tests/`。
  前置依赖：`NTL-S1-011`。
  可并行：无。
  验收标准：模型与 migration 至少有一条自动化验证路径。
  完成情况：已补模型注册测试、模型字段测试与 migration 内容测试，覆盖新模型、`signals` 扩列和 `Base.metadata` 注册。

### Stage 1 完成标准

- 新配置、新契约、新模型和 migration 已落地。
- 新旧链路可以共存。
- Stage 2 以后不需要再回头补基础结构。
 现已完成。

---

## 10. Stage 1.5：Agent 边界收敛与模块化改造（P0）

### Stage 目标

- 明确哪些长期保留为 Agent。
- 明确哪些能力应下沉为 module/service。
- 冻结旧主线，避免继续发散。

### 阶段交付物

- 文档中的角色边界。
- 代码目录中的保留/冻结说明。
- 为后续重构提供稳定边界。

### 任务清单

- [x] `NTL-S15-001` `P0`
  目标：明确 `ManagerAgent` 长期保留，但只负责编排。
  输入：现有 Manager 逻辑。
  输出：文档与代码中的职责说明。
  修改范围：文档、`src/agents/manager_agent/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S15-002` ~ `NTL-S15-005`。
  验收标准：Manager 不再被当作逻辑堆积点。
  完成情况：已在 `src/agents/manager_agent/agent.py` 头部和类 docstring 中明确边界：编排角色、委托分工、禁止继续堆叠业务逻辑。

- [x] `NTL-S15-002` `P0`
  目标：明确 `DataAgent` 长期保留为 capability router。
  输入：现有 DataAgent。
  输出：职责说明。
  修改范围：文档、`src/agents/data_agent/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S15-001`、`NTL-S15-003`。
  验收标准：DataAgent 的长期目标清晰且后续实现不偏航。
  完成情况：已在 `src/agents/data_agent/agent.py` 类 docstring 中明确边界：capability router、skill 注册机制、Phase 0 与后续演进路径。

- [x] `NTL-S15-003` `P0`
  目标：明确 `TraderAgent` 长期保留为 per-trader 执行器。
  输入：现有 TraderAgent。
  输出：职责说明。
  修改范围：文档、`src/agents/trader_agent/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S15-001`、`NTL-S15-002`。
  验收标准：TraderAgent 不再只是模板拼装器。
  完成情况：已在 `src/agents/trader_agent/agent.py` 头部和类 docstring 中明确边界：per-trader 执行器、委托分工、Stage 4 升级路径。

- [x] `NTL-S15-004` `P1`
  目标：明确 `StrategyAgent` 保留为规则评估层。
  输入：现有 StrategyAgent。
  输出：职责说明。
  修改范围：文档、`src/agents/strategy_agent/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S15-005`。
  验收标准：StrategyAgent 与 TraderAgent、RiskAgent 边界清晰。
  完成情况：已在 `src/agents/strategy_agent/agent.py` 类 docstring 中明确边界：规则评估层、接收特征和规则列表、输出 RawSignal、Stage 3/4 演进方向。

- [x] `NTL-S15-005` `P1`
  目标：明确 `RiskAgent` 保留为风险过滤层。
  输入：现有 RiskAgent。
  输出：职责说明。
  修改范围：文档、`src/agents/risk_agent/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S15-004`。
  验收标准：RiskAgent 不承担策略构建或数据抓取职责。
  完成情况：已在 `src/agents/risk_agent/agent.py` 类 docstring 中明确边界：风险过滤层、接收 RawSignal 和账户快照、输出可能被拒绝的 Signal、异常默认拒绝。

- [x] `NTL-S15-006` `P0`
  目标：把 `KnowledgeAgent` 主线职责降级为 module/service。
  输入：现有 KnowledgeAgent 目录与能力。
  输出：迁移计划与历史目录说明。
  修改范围：文档、`src/agents/knowledge_agent/`、后续模块目录。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S15-007`、`NTL-S15-008`。
  验收标准：后续知识抽取不再以独立 Agent 作为主线。
  完成情况：已在 `src/agents/knowledge_agent/__init__.py` 添加冻结说明；后续若有知识抽取需求在 strategy_library / evaluation 模块中实现。

- [x] `NTL-S15-007` `P0`
  目标：把 `BehaviorAgent` 主线职责降级为 module/service。
  输入：现有 BehaviorAgent 目录与能力。
  输出：迁移计划与历史目录说明。
  修改范围：文档、`src/agents/behavior_agent/`、后续模块目录。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S15-006`、`NTL-S15-008`。
  验收标准：行为分析能力进入 `trader_profile / evaluation / backtest` 主线。
  完成情况：已在 `src/agents/behavior_agent/__init__.py` 添加冻结说明；后续若有行为分析需求在 trader_profile / evaluation / backtest 模块中实现。

- [x] `NTL-S15-008` `P0`
  目标：把 `BacktestAgent` 主线职责降级到 `src/backtest`。
  输入：现有 BacktestAgent 目录与能力。
  输出：迁移计划与历史目录说明。
  修改范围：文档、`src/agents/backtest_agent/`、后续 `src/backtest/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S15-006`、`NTL-S15-007`。
  验收标准：回测主线不再继续扩展旧 Agent 空壳。
  完成情况：已在 `src/agents/backtest_agent/__init__.py` 添加冻结说明；后续回测开发统一进入 src/backtest/ 模块。

- [x] `NTL-S15-009` `P0`
  目标：冻结旧 `AlignmentAgent` 主线。
  输入：现有 AlignmentAgent 目录。
  输出：冻结说明与目录状态标记。
  修改范围：文档、`src/agents/alignment_agent/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S15-010`。
  验收标准：不会再把旧 Alignment 路径当当前核心交付路径。
  完成情况：已在 `src/agents/alignment_agent/__init__.py` 和 `agent.py` 头部添加冻结说明；后续若需对齐分析在 Stage 5 evaluation 中规划。

- [x] `NTL-S15-010` `P1`
  目标：在代码与文档中同步保留/冻结/历史参考状态。
  输入：前面 9 个任务的边界定义。
  输出：统一说明。
  修改范围：`src/agents/`、文档。
  前置依赖：`NTL-S15-001` ~ `NTL-S15-009`。
  可并行：无。
  验收标准：新执行者看到目录即可理解当前主线与历史边界。
  完成情况：已在 `docs/Project.md` 中更新 Agent 状态总览表，添加状态说明（保留为长期 Agent / 已冻结主线），关联各 Agent 到对应 NTL-S15-00X 任务编号。

### Stage 1.5 完成标准

- Agent 边界清晰。
- 旧多 Agent 发散路径被收敛。
- Stage 2 以后可以围绕稳定角色继续开发。

---

## 11. Stage 2：Provider 抽象与市场候选池（P0）

### Stage 目标

- 建立 provider 抽象。
- 生成每日热点、成分、强势池快照。
- 把 `DataAgent` 升级为 capability router。

### 阶段交付物

- `src/providers/` 基础抽象与实现。
- `src/market_universe/` 模块。
- 支持新 fields 的 DataAgent。
- 快照接入 pipeline。

### 任务清单

- [x] `NTL-S2-001` `P0`
  目标：新增 provider 抽象基类。
  输入：Stage 1 契约与配置。
  输出：`src/providers/base.py`。
  修改范围：`src/providers/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S2-002` ~ `NTL-S2-005`。
  验收标准：provider 接口支持统一请求、标准化输出与错误处理。
  完成情况：已新增 `src/providers/base.py`，提供统一的 `ProviderBase`、`ProviderResult`、`ProviderError` 与 `ProviderStatus`。

- [x] `NTL-S2-002` `P0`
  目标：新增热点 provider。
  输入：provider 基类、快照 schema。
  输出：`src/providers/hot_topics_provider.py`。
  修改范围：`src/providers/`。
  前置依赖：`NTL-S2-001`。
  可并行：`NTL-S2-003`、`NTL-S2-004`、`NTL-S2-005`。
  验收标准：能输出统一的热点结构。
  完成情况：已新增 `src/providers/hot_topics_provider.py`，可汇总板块强度、行业排名与概念风口为统一 topics 列表。

- [x] `NTL-S2-003` `P0`
  目标：新增题材成分 provider。
  输入：provider 基类、快照 schema。
  输出：`src/providers/topic_constituents_provider.py`。
  修改范围：`src/providers/`。
  前置依赖：`NTL-S2-001`。
  可并行：`NTL-S2-002`、`NTL-S2-004`、`NTL-S2-005`。
  验收标准：能输出统一的题材成分结构。
  完成情况：已新增 `src/providers/topic_constituents_provider.py`，可汇总题材、龙头、涨停原因和龙虎榜相关成分信息。

- [x] `NTL-S2-004` `P0`
  目标：新增基础行情 provider。
  输入：provider 基类、行情 schema。
  输出：`src/providers/market_data_provider.py`。
  修改范围：`src/providers/`。
  前置依赖：`NTL-S2-001`。
  可并行：`NTL-S2-002`、`NTL-S2-003`、`NTL-S2-005`。
  验收标准：能输出统一的 `ohlcv_1d` 或基础行情结构。
  完成情况：已新增 `src/providers/market_data_provider.py`，可从 `fetch_ohlcv_1d`、`MarketDataSyncService` 或 cache 读取日线行情，并归一为 `ohlcv_1d` bars 结构。

- [x] `NTL-S2-005` `P0`
  目标：新增 AKShare provider。
  输入：现有 AKShare 能力。
  输出：`src/providers/akshare_provider.py`。
  修改范围：`src/providers/`。
  前置依赖：`NTL-S2-001`。
  可并行：`NTL-S2-002`、`NTL-S2-003`、`NTL-S2-004`。
  验收标准：AKShare 能以 provider 形式输出标准数据。
  完成情况：已新增 `src/providers/akshare_provider.py`，可直接输出 `ohlcv_1d` 标准结构，也可作为 `MarketDataProvider` 的 backend 复用。

- [x] `NTL-S2-006` `P0`
  目标：把 `kaipan_provider.py` 从草案推进为可调用实现。
  输入：Stage 0 的数据资产层和 provider 基类。
  输出：可调用的 `kaipan` provider。
  修改范围：`src/providers/kaipan_provider.py`。
  前置依赖：`NTL-S2-001`、Stage 0 完成。
  可并行：`NTL-S2-007`。
  验收标准：至少能输出热点、成分、强势池三类标准结构。
  完成情况：已将 `KaipanProvider` 升级为 `ProviderBase`，补齐 `hot_topics`、`topic_constituents`、`strong_symbols` 三类 capability，以及对应的标准化输出与公开 wrapper 方法。

- [x] `NTL-S2-007` `P1`
  目标：新增 fallback provider。
  输入：多个 provider 实现。
  输出：`src/providers/fallback_provider.py`。
  修改范围：`src/providers/`。
  前置依赖：`NTL-S2-002` ~ `NTL-S2-006`。
  可并行：无。
  验收标准：主链路 provider 异常时可按顺序降级。
  完成情况：已新增 `src/providers/fallback_provider.py`，FallbackProvider 继承 ProviderBase，维护 `capability -> 有序 provider 列表` 映射；支持三种降级场景（单个成功候选链成功返回、部分成功返回 partial、所有失败返回 partial 与完整错误列表）；17 tests PASS；已注册到 providers 包。

- [x] `NTL-S2-008` `P0`
  目标：建立市场候选池 schema。
  输入：快照定义。
  输出：`src/market_universe/schemas.py`。
  修改范围：`src/market_universe/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S2-009` ~ `NTL-S2-012`。
  验收标准：候选池的热点、成分、强势股结构统一。
  完成情况：已新增 `src/market_universe/schemas.py`，定义 `HotTopic`、`TopicConstituent`、`StrongSymbol` 三个原子 dataclass，以及 `HotTopicsPayload`、`TopicConstituentsPayload`、`StrongSymbolsPayload`、`MarketUniverse` 四个聚合结构；9 tests PASS；与 provider normalize 输出结构完全对齐。

- [x] `NTL-S2-009` `P0`
  目标：建立热点快照构建器。
  输入：热点 provider 输出。
  输出：`src/market_universe/hot_topics_builder.py`。
  修改范围：`src/market_universe/`。
  前置依赖：`NTL-S2-002`、`NTL-S2-008`。
  可并行：`NTL-S2-010`、`NTL-S2-011`。
  验收标准：每日热点快照可稳定生成。
  完成情况：已新增 `src/market_universe/hot_topics_builder.py`，HotTopicsBuilder 将 provider 输出转换为 HotTopicsPayload；支持 HotTopic 实例化、去重、score 降序排列；8 tests PASS；已注册到 market_universe 包。

- [x] `NTL-S2-010` `P0`
  目标：建立题材成分解析器。
  输入：题材成分 provider 输出。
  输出：`src/market_universe/constituents_resolver.py`。
  修改范围：`src/market_universe/`。
  前置依赖：`NTL-S2-003`、`NTL-S2-008`。
  可并行：`NTL-S2-009`、`NTL-S2-011`。
  验收标准：热点与个股之间的成分关系可稳定解析。
  完成情况：已新增 `src/market_universe/constituents_resolver.py`，ConstituentsResolver 将 provider 输出转换为 TopicConstituentsPayload；按 kind 组合 topic_id/symbol 做去重；6 tests PASS；已注册到 market_universe 包。

- [x] `NTL-S2-011` `P0`
  目标：建立强势池选择器。
  输入：强势股 provider 输出与基础行情。
  输出：`src/market_universe/strong_symbols_selector.py`。
  修改范围：`src/market_universe/`。
  前置依赖：`NTL-S2-004`、`NTL-S2-006`、`NTL-S2-008`。
  可并行：`NTL-S2-009`、`NTL-S2-010`。
  验收标准：能生成每日强势标的列表。
  完成情况：已新增 `src/market_universe/strong_symbols_selector.py`，StrongSymbolsSelector 将 provider 输出转换为 StrongSymbolsPayload；支持三种 kind（strong_fengkou/interval_stats_stock/morning_bidding_list）；6 tests PASS；已注册到 market_universe 包。

- [x] `NTL-S2-012` `P0`
  目标：建立候选池快照服务。
  输入：热点、成分、强势池构建器。
  输出：`src/market_universe/snapshot_service.py`。
  修改范围：`src/market_universe/`。
  前置依赖：`NTL-S2-009`、`NTL-S2-010`、`NTL-S2-011`。
  可并行：`NTL-S2-020` ~ `NTL-S2-022`。
  验收标准：可统一写入和读取候选池快照。
  完成情况：已新增 `src/market_universe/snapshot_service.py`，SnapshotService 实现 save/load/list_snapshots/delete；使用文件系统后端（data/market_universe/snapshots/）；8 tests PASS；已注册到 market_universe 包。

- [x] `NTL-S2-013` `P0`
  目标：新增热点拉取 skill。
  输入：新 DataRequest fields、provider、候选池服务。
  输出：`fetch_hot_topics.py`。
  修改范围：`src/agents/data_agent/skills/`。
  前置依赖：`NTL-S2-002`、`NTL-S2-012`。
  可并行：`NTL-S2-014`、`NTL-S2-015`。
  验收标准：DataAgent 可以按请求返回热点。
  完成情况：已新增 `src/agents/data_agent/skills/fetch_hot_topics.py`，skill 支持 `hot_topics` 字段，使用 HotTopicsBuilder 构建 payload；5 tests PASS。

- [x] `NTL-S2-014` `P0`
  目标：新增题材成分拉取 skill。
  输入：新 DataRequest fields、provider、候选池服务。
  输出：`fetch_topic_constituents.py`。
  修改范围：`src/agents/data_agent/skills/`。
  前置依赖：`NTL-S2-003`、`NTL-S2-012`。
  可并行：`NTL-S2-013`、`NTL-S2-015`。
  验收标准：DataAgent 可以按请求返回题材成分。
  完成情况：已新增 `src/agents/data_agent/skills/fetch_topic_constituents.py`，skill 支持 `topic_constituents` 字段，使用 ConstituentsResolver 构建 payload；5 tests PASS。

- [x] `NTL-S2-015` `P0`
  目标：新增强势池拉取 skill。
  输入：新 DataRequest fields、provider、候选池服务。
  输出：`fetch_strong_symbols.py`。
  修改范围：`src/agents/data_agent/skills/`。
  前置依赖：`NTL-S2-011`、`NTL-S2-012`。
  可并行：`NTL-S2-013`、`NTL-S2-014`。
  验收标准：DataAgent 可以按请求返回强势池。
  完成情况：已新增 `src/agents/data_agent/skills/fetch_strong_symbols.py`，skill 支持 `strong_symbols` 字段，使用 StrongSymbolsSelector 构建 payload；5 tests PASS。

- [x] `NTL-S2-016` `P1`
  目标：新增 `ohlcv_1d` 拉取 skill。
  输入：行情 provider。
  输出：`fetch_ohlcv.py`。
  修改范围：`src/agents/data_agent/skills/`。
  前置依赖：`NTL-S2-004`。
  可并行：`NTL-S2-017`。
  验收标准：DataAgent 可以按请求返回日线行情。
  完成情况：已新增 `src/agents/data_agent/skills/fetch_ohlcv.py`，skill 支持 `ohlcv_1d` 字段；6 tests PASS。

- [x] `NTL-S2-017` `P1` ✅ 2026-04-23 完成（下午会话补充路由）
  目标：新增指标拉取 skill。
  输入：指标计算或 provider 输出。
  输出：`src/agents/data_agent/skills/fetch_indicators.py`（基于 PatternFeatureEngine 计算 RSI/MACD/Bollinger/ATR 等指标）；DataAgent 已注册 indicators 路由。
  修改范围：`src/agents/data_agent/skills/`、`src/agents/data_agent/agent.py`。
  前置依赖：`NTL-S2-016` 或现有指标能力可复用。
  可并行：无。
  验收标准：DataAgent 可以按请求返回指标。
  完成情况：fetch_indicators skill 已注册；下午会话补充了 DataAgent.handle 中 fetch_indicators 的 elif 路由分支，路由链路已贯通。

- [x] `NTL-S2-018` `P0`
  目标：把 `DataAgent` 改造成 capability router。
  输入：新增 skills、扩展后的契约。
  输出：按 fields 路由能力的 DataAgent。
  修改范围：`src/agents/data_agent/agent.py`。
  前置依赖：`NTL-S2-013`、`NTL-S2-014`、`NTL-S2-015`、`NTL-S1-003`。
  可并行：`NTL-S2-019`、`NTL-S2-024`。
  验收标准：DataAgent 不再只支持 `last_price`。
  完成情况：DataAgent 已注册全部 5 个 skills（fetch_market/fetch_hot_topics/fetch_topic_constituents/fetch_strong_symbols/fetch_ohlcv）；按 dataset 路由到对应 skill；兼容无 dataset 时的 last_price fallback；6 tests PASS。

- [x] `NTL-S2-019` `P1`
  目标：收敛 `fetch_market.py` 为基础行情 skill。
  输入：新 DataAgent 路由设计。
  输出：基础行情能力与新 skills 边界清晰。
  修改范围：`src/agents/data_agent/skills/fetch_market.py`。
  前置依赖：`NTL-S2-018`。
  可并行：`NTL-S2-024`。
  验收标准：`fetch_market.py` 不再承担过宽职责。
  完成情况：已更新 `fetch_market.py` docstring，明确职责边界（仅 last_price）、数据来源优先级、Phase 0 兼容定位。

- [x] `NTL-S2-020` `P0`
  目标：把热点快照接入 pipeline。
  输入：热点构建器与快照服务。
  输出：热点快照 handler。
  修改范围：`src/pipeline/` 或现有任务处理模块。
  前置依赖：`NTL-S2-012`。
  可并行：`NTL-S2-021`、`NTL-S2-022`。
  验收标准：可通过任务系统生成热点快照。
  完成情况：已新增 `src/pipeline/tasks/snapshot_tasks.py`，handle_hot_topics_snapshot 实现；从 KaipanProvider 获取数据，经 HotTopicsBuilder 构建，SnapshotService 保存；已注册到 process_tasks.py。

- [x] `NTL-S2-021` `P0`
  目标：把题材成分快照接入 pipeline。
  输入：成分解析器与快照服务。
  输出：成分快照 handler。
  修改范围：`src/pipeline/` 或现有任务处理模块。
  前置依赖：`NTL-S2-012`。
  可并行：`NTL-S2-020`、`NTL-S2-022`。
  验收标准：可通过任务系统生成题材成分快照。
  完成情况：已新增 `src/pipeline/tasks/snapshot_tasks.py`，handle_topic_constituents_snapshot 实现；从 KaipanProvider 获取数据，经 ConstituentsResolver 构建，SnapshotService 保存；已注册到 process_tasks.py。

- [x] `NTL-S2-022` `P0`
  目标：把强势池快照接入 pipeline。
  输入：强势池选择器与快照服务。
  输出：强势池快照 handler。
  修改范围：`src/pipeline/` 或现有任务处理模块。
  前置依赖：`NTL-S2-012`。
  可并行：`NTL-S2-020`、`NTL-S2-021`。
  验收标准：可通过任务系统生成强势池快照。
  完成情况：已新增 `src/pipeline/tasks/snapshot_tasks.py`，handle_strong_symbols_snapshot 实现；从 KaipanProvider 获取数据，经 StrongSymbolsSelector 构建，SnapshotService 保存；已注册到 process_tasks.py。

- [x] `NTL-S2-023` `P0`
  目标：移除 DataAgent 仅支持 `last_price` 的硬限制。
  输入：新路由实现。
  输出：字段支持清单与兼容逻辑。
  修改范围：`src/agents/data_agent/agent.py`、skills 注册。
  前置依赖：`NTL-S2-018`。
  可并行：`NTL-S2-024`。
  验收标准：请求新 fields 时不再直接失败。
  完成情况：DataAgent 已支持 5 种 dataset 路由；无 dataset 时的 fallback 只对 last_price 生效，其他字段返回 capability_missing；字段支持清单在 _all_supported_fields 中定义。

- [x] `NTL-S2-024` `P1`
  目标：定义 `capability_missing` 的降级策略。
  输入：新 DataAgent 路由体系。
  输出：缺能力时的统一返回和待办生成逻辑。
  修改范围：`src/agents/data_agent/agent.py`、Manager 接口约定、文档。
  前置依赖：`NTL-S2-018`。
  可并行：`NTL-S2-019`、`NTL-S2-023`。
  验收标准：缺失能力时行为可预期、可记录、可追踪。
  完成情况：已在 DataAgent docstring 中明确降级策略（capability_missing/error/partial/ok 四种状态）；ManagerAgent 已为 capability_missing 创建 AgentTask(type="capability_missing")。

### Stage 2 完成标准

- 每日能生成 `hot_topics / topic_constituents / strong_symbols` 快照。
- `DataAgent` 已能按新 fields 返回标准化 payload。
- 盘前链路具备从静态 watchlist 迁移出去的前提。

---

## 12. Stage 3：按 trader 版本化策略库（P1）

### Stage 目标

- 每个 trader 每日生成独立策略版本。
- 策略版本能追溯到文章、画像、证据和质量门禁。

### 阶段交付物

- `src/strategy_library/` 模块。
- 扩展后的 `TraderProfile`。
- 策略版本构建任务。

### 任务清单

- [x] `NTL-S3-001` `P1` ✅ 2026-04-23
  目标：建立策略库 schema。
  输入：策略版本模型与契约。
  输出：`src/strategy_library/schemas.py`（StrategyVersionStatus, StrategyIdea, StrategyRecommendation, StrategyVersion）。
  修改范围：`src/strategy_library/`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S3-002`、`NTL-S3-003`。
  验收标准：策略版本的输入输出结构清晰。

- [x] `NTL-S3-002` `P1` ✅ 2026-04-23
  目标：建立策略库 repository。
  输入：策略版本模型。
  输出：`src/strategy_library/repository.py`（StrategyLibraryRepository，支持异步查询和保存）。
  修改范围：`src/strategy_library/`。
  前置依赖：`NTL-S3-001`。
  可并行：`NTL-S3-003`。
  验收标准：能按 trader、日期、状态读取策略版本。

- [x] `NTL-S3-003` `P1` ✅ 2026-04-23
  目标：建立策略版本构建器。
  输入：TraderProfile、文章证据、策略规则。
  输出：`src/strategy_library/builder.py`（StrategyVersionBuilder，支持 build_draft / build_released）。
  修改范围：`src/strategy_library/`。
  前置依赖：`NTL-S3-001`、`NTL-S3-005`、`NTL-S3-006`、`NTL-S3-007`。
  可并行：`NTL-S3-004`。
  验收标准：可构建 `draft/released` 等版本状态。

- [x] `NTL-S3-004` `P1` ✅ 2026-04-23
  目标：建立策略库 service。
  输入：schema、repository、builder。
  输出：`src/strategy_library/service.py`（StrategyLibraryService，整合 repository + builder）。
  修改范围：`src/strategy_library/`。
  前置依赖：`NTL-S3-002`、`NTL-S3-003`。
  可并行：`NTL-S3-008`。
  验收标准：主流程可读取某 trader 当前发布版本。

- [x] `NTL-S3-005` `P1` ✅ 2026-04-23
  目标：增强文章元数据抽取。
  输入：现有 `extract_article_metadata` 逻辑。
  输出：质量门禁（_quality_gate）、证据字段（source_url/published_at）、可聚合字段（sentiment_score/clamped, confidence_score/clamped）。
  修改范围：`src/agents/data_agent/skills/extract_article_metadata.py`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S3-006`、`NTL-S3-007`。
  验收标准：文章元数据可支撑策略版本构建而不是仅作展示。

- [x] `NTL-S3-006` `P1` ✅ 2026-04-23
  目标：扩展 `TraderProfile` schema。
  输入：现有画像结构。
  输出：StrategyPreference、RiskStyle、ThemeStat、PositionBias 等扩展字段（schema_version 升级为 v2）。
  修改范围：`src/trader_profile/schemas.py`。
  前置依赖：Stage 1 完成。
  可并行：`NTL-S3-005`、`NTL-S3-007`。
  验收标准：画像结构可以作为策略版本输入。

- [x] `NTL-S3-007` `P1` ✅ 2026-04-23
  目标：扩展 `TraderProfile` service。
  输入：增强后的画像 schema 与文章元数据。
  输出：可直接被策略版本构建器消费的画像结果（含策略偏好、风险风格、主题偏好、仓位倾向）。
  修改范围：`src/trader_profile/service.py`。
  前置依赖：`NTL-S3-005`、`NTL-S3-006`。
  可并行：无。
  验收标准：同一 trader 的画像结果稳定、可重复。

- [x] `NTL-S3-008` `P1` ✅ 2026-04-23
  目标：把策略版本构建接入任务系统。
  输入：策略库 service。
  输出：`src/pipeline/tasks/strategy_version_tasks.py`（handle_build_trader_strategy_version handler，已注册到 process_tasks.py）。
  修改范围：`process_tasks.py`、`src/pipeline/tasks/`。
  前置依赖：`NTL-S3-004`。
  可并行：`NTL-S3-009`。
  验收标准：可按 trader 和交易日生成策略版本。

- [x] `NTL-S3-009` `P1` ✅ 2026-04-23
  目标：把轻量 `TraderProfile` 升级为版本构建输入。
  输入：现有 TraderProfile 使用路径。
  输出：builder.py 增强（position_bias 调整决策、risk_style 控制止损、max_positions 限制数量、theme_preference 过滤排序；ArticleEvidence 新增 entry_price 字段）。
  修改范围：`src/strategy_library/builder.py`。
  前置依赖：`NTL-S3-006`、`NTL-S3-007`。
  可并行：`NTL-S3-008`。
  验收标准：画像结果不再只是 prompt 辅助信息。

- [x] `NTL-S3-010` `P1` ✅ 2026-04-23
  目标：保证同一 trader 同日只产出一个 released 版本。
  输入：策略库 service。
  输出：`release_version()` 新增已有版本检查，抛出 ValueError 防止重复发布。
  修改范围：`src/strategy_library/service.py`。
  前置依赖：`NTL-S3-004`。
  可并行：`NTL-S3-011`。
  验收标准：不会出现同 trader 同日多个 released 版本。

- [x] `NTL-S3-011` `P1` ✅ 2026-04-23
  目标：保证不同 trader 版本严格隔离。
  输入：策略库 service。
  输出：version_id 含 trader_id，repository 查询严格按 trader_id 过滤。
  修改范围：`src/strategy_library/`。
  前置依赖：`NTL-S3-004`。
  可并行：`NTL-S3-010`。
  验收标准：不同 trader 的版本不会互相污染。

### Stage 3 完成标准

- 每个 trader 每日有独立 `released` 策略版本。
- 版本可追溯到文章证据与质量门禁结果。

---

## 13. Stage 4：盘前主链路升级（P1）

### Stage 目标

- 盘前建议不再依赖旧 `watchlist + last_price` 逻辑。
- 盘前建议必须基于快照、策略版本、画像和记忆。

### 阶段交付物

- 升级后的 TraderAgent、StrategyAgent、ManagerAgent。
- 完整上下文 signal 追踪。
- 最小盘前回归测试。

### 任务清单

- [x] `NTL-S4-001` `P1` ✅ 2026-04-24
  目标：重构 `TraderAgent` 输入。
  输入：策略版本、强势池、画像、记忆。
  输出：可消费新输入的 `TraderAgent`。
  修改范围：`src/agents/trader_agent/agent.py`。
  前置依赖：Stage 2、Stage 3 完成。
  可并行：`NTL-S4-003`、`NTL-S4-004`。
  验收标准：TraderAgent 不再以 watchlist 为核心输入。
  完成情况：新增 strategy_version + market_universe 参数；新增 _candidates_from_strategy/_strong_symbol_hint 方法；Phase 0 降级路径完整保留；5 tests PASS。

- [x] `NTL-S4-002` `P1` ✅ 2026-04-24
  目标：支持 `buy / sell / hold` 三类决策。
  输入：新 TraderAgent。
  输出：完整决策类型。
  修改范围：`src/agents/trader_agent/agent.py`、相关 schema。
  前置依赖：`NTL-S4-001`。
  可并行：无。
  验收标准：盘前输出不再只有单一建议路径。
  完成情况：移除 _candidates_from_strategy 对 sell 的过滤；buy/hold/sell 三类决策全输出；TradeIdea.side 正确传递；测试断言更新（HOLD → BUY）。

- [x] `NTL-S4-003` `P1` ✅ 2026-04-24
  目标：扩展 `StrategyAgent` 支持版本化规则快照。
  输入：策略版本库。
  输出：版本化规则评估逻辑。
  修改范围：`src/agents/strategy_agent/agent.py`。
  前置依赖：Stage 3 完成。
  可并行：`NTL-S4-001`、`NTL-S4-004`。
  验收标准：StrategyAgent 评估基于策略版本而不是静态模板。
  完成情况：StrategyVersion 新增 rules_snapshot 字段；generate_raw_signal 新增 strategy_version 参数；规则来源判断逻辑实现；39 tests PASS。

- [x] `NTL-S4-004` `P1` ✅ 2026-04-24
  目标：扩展信号类型上下文。
  输入：现有 `src/strategy/types.py`。
  输出：新增版本、快照、主题来源字段。
  修改范围：`src/strategy/types.py`。
  前置依赖：Stage 3 完成。
  可并行：`NTL-S4-001`、`NTL-S4-003`。
  验收标准：信号上下文足以支撑追溯。
  完成情况：SignalContext 新增 strategy_version_id/market_universe_snapshot/topic_source_ids 字段；Signal 新增 strategy_version_id 字段；8 tests PASS。

- [x] `NTL-S4-005` `P1` ✅ 2026-04-24
  目标：扩展 `signal_version` 持久化完整上下文。
  输入：扩展后的 signal 类型。
  输出：完整 signal 版本持久化能力。
  修改范围：`src/strategy/signal_version.py`。
  前置依赖：`NTL-S4-004`。
  可并行：`NTL-S4-006`。
  验收标准：能重放某次盘前建议的完整上下文。
  完成情况：_signal_to_dict/_dict_to_signal 新增 strategy_version_id；_context_to_dict/_dict_to_context 新增 strategy_version_id/market_universe_snapshot/topic_source_ids；57 tests PASS。

- [x] `NTL-S4-006` `P1` ✅ 2026-04-25
  目标：重构 `ManagerAgent` 接入策略版本与候选池快照。
  输入：新 DataAgent、策略库、候选池快照。
  输出：升级后的 ManagerAgent。
  修改范围：`src/agents/manager_agent/agent.py`。
  前置依赖：`NTL-S4-001`、`NTL-S4-003`、Stage 2、Stage 3 完成。
  可并行：`NTL-S4-007`。
  验收标准：Manager 能编排新版盘前链路。
  完成情况：新增 StrategyLibraryService + SnapshotService 依赖；run_pre_market 重构（market_universe 共享加载、strategy_version per-trader 加载）；_record_ideas_as_signals 更新（side 映射、SignalContext 扩展）；Phase 0 降级完整保留；SignalContext 包含 market_universe_snapshot + topic_source_ids；5 manager tests PASS，合计 57 tests PASS。

- [x] `NTL-S4-007` `P1` ✅ 2026-04-24
  目标：引入定向深挖 DataRequest 规划。
  输入：Manager 编排逻辑。
  输出：按需要发起二次取数的规划逻辑。
  修改范围：`src/agents/manager_agent/agent.py`。
  前置依赖：`NTL-S4-006`。
  可并行：`NTL-S4-008`。
  验收标准：盘前取数不再只是固定模板。
  完成情况：新增 _plan_data_requests 方法，从 rules_snapshot 条件中提取字段并映射到 dataset；run_pre_market 集成定向深挖逻辑，当 strategy_version 存在且有 rules_snapshot 时自动发起 indicators/ohlcv_1d 等额外取数；57 tests PASS。

- [x] `NTL-S4-008` `P1` ✅ 2026-04-24
  目标：盘前输出增加策略版本和证据追踪字段。
  输入：扩展后的 `TradeIdea`。
  输出：完整结构化输出。
  修改范围：`src/agents/manager_agent/agent.py`、输出 schema。
  前置依赖：`NTL-S4-006`、`NTL-S1-004`。
  可并行：无。
  验收标准：盘前建议可直接追溯版本与证据。
  完成情况：TradeIdea 新增 source_recommendation_idx 字段（来源 recommendation 索引）；DailyReport 新增 strategy_version_ids 字段（报告级版本追溯）；run_pre_market 收集 used_strategy_version_ids 并传入 DailyReport；57 tests PASS。

- [x] `NTL-S4-009` `P1` ✅ 2026-04-24
  目标：下线旧 `watchlist + last_price` 主路径地位。
  输入：新版盘前链路。
  输出：旧路径降级为兼容或 fallback。
  修改范围：`TraderAgent`、`ManagerAgent`、相关配置。
  前置依赖：`NTL-S4-006`、`NTL-S4-008`。
  可并行：`NTL-S4-010`。
  验收标准：主路径已经切换到快照 + 版本方案。
  完成情况：新增 Stage4Config（enable=True, market_universe_slot, allow_phase0_fallback）；run_pre_market 受 stage4.enable 控制，allow_phase0_fallback=False 时跳过 trader 而非降级；57 tests PASS。

- [x] `NTL-S4-010` `P1` ✅ 2026-04-24
  目标：拆分 `ManagerAgent` 中膨胀的编排逻辑。
  输入：现有与新版 Manager 实现。
  输出：service 层或辅助模块。
  修改范围：`src/agents/manager_agent/` 及相关 service。
  前置依赖：`NTL-S4-006`。
  可并行：`NTL-S4-009`。
  验收标准：Manager 只保留编排，不继续承担过多业务逻辑。
  完成情况：新增 `src/agents/manager_agent/premarket_service.py`（PreMarketService）；将 per-trader 编排逻辑（策略版本加载/定向深挖/信号评估/missing symbols）提取到 `PreMarketService.run_for_trader`；`run_pre_market` 简化为循环调用 service；57 tests PASS。

- [x] `NTL-S4-011` `P1` ✅ 2026-04-24
  目标：补盘前链路回归测试。
  输入：新版盘前主链路。
  输出：回归测试或稳定的集成验证。
  修改范围：`tests/`。
  前置依赖：`NTL-S4-008`、`NTL-S4-009`。
  可并行：无。
  验收标准：至少一条完整盘前流程可重复验证。
  完成情况：新增 5 个回归测试（test_stage4_path_with_strategy_version / test_phase0_fallback_when_no_strategy_version / test_allow_phase0_false_skips_trader / test_daily_report_includes_strategy_version_ids / test_trade_idea_side_reflects_strategy_decision）；覆盖 Stage 4 路径、Phase 0 降级、allow_phase0_fallback=False 跳过逻辑、DailyReport.strategy_version_ids 追溯、TradeIdea.side 决策传递；10/10 manager tests PASS。

### Stage 4 完成标准

- 单 trader 与多 trader 盘前建议都能基于快照和版本生成。
- 输出可完整追溯到快照、策略版本和证据。

---

## 14. Stage 5：盘后评估、学习闭环与 ranking（P1）

### Stage 目标

- 盘后从“简单收益率汇总”升级为评分、归因、记忆写回和 ranking。

### 阶段交付物

- `src/evaluation/` 模块。
- 扩展后的 `TraderMemory`。
- 盘后 Evidence Pack、归因与 ranking。

### 任务清单

- [x] `NTL-S5-001` `P1`
  目标：建立 Evidence Pack 结构。
  输入：盘前输出、行情快照、信号上下文。
  输出：`src/evaluation/evidence_pack.py` + `src/models/converters.py` + `src/models/evidence_pack.py`。
  修改范围：`src/evaluation/` + `src/models/`。
  前置依赖：Stage 4 完成。
  可并行：`NTL-S5-002`、`NTL-S5-003`。
  验收标准：任一建议都能生成证据包。
  **完成内容**：EvidencePack dataclass（trade_idea / signal_context / market_data / strategy_version_snapshot）+ converters.py 显式转换层 + EvidencePackRecord ORM 模型。

- [x] `NTL-S5-002` `P1` ✅ 2026-04-25
  目标：建立失败归因分类。
  输入：盘后评估需求。
  输出：`src/evaluation/failure_taxonomy.py`。
  修改范围：`src/evaluation/`。
  前置依赖：Stage 4 完成。
  可并行：`NTL-S5-001`、`NTL-S5-003`。
  验收标准：失败原因分类结构稳定且可扩展。
  完成情况：新增 `failure_taxonomy.py`（FailureRootCause/FailureStage/FailureRuleType/FailureAttribution/parse_failure_categories）；10 tests PASS；多维度标签体系设计文档已提交。

- [x] `NTL-S5-003` `P1` ✅ 2026-04-25
  目标：建立盘后复盘 service。
  输入：Evidence Pack、失败归因、行情数据。
  输出：`src/evaluation/postmortem_service.py`。
  修改范围：`src/evaluation/`。
  前置依赖：`NTL-S5-001`、`NTL-S5-002`。
  可并行：`NTL-S5-004`。
  验收标准：能生成结构化 postmortem 结果。
  完成情况：新增 `postmortem_service.py`（ValidationDecision/LLMValidationResult/PostmortemResult/PostmortemService/LLMValidator protocol）；自动归因 + LLM 校验混合模式；25 tests PASS；设计文档已提交。

- [x] `NTL-S5-004` `P1`
  目标：建立 ranking service。
  输入：盘后评分数据。
  输出：`src/evaluation/ranking_service.py` + `ranking_repository.py` + `RankingEntryRecord` ORM。
  修改范围：`src/evaluation/` + `src/models/`。
  前置依赖：`NTL-S5-001`、`NTL-S5-002`。
  可并行：`NTL-S5-003`。
  验收标准：能按 trader、策略版本、标的等维度输出 ranking。
  完成情况：新增 `RankingEntry` dataclass + `RankingService`（add_entry/generate_ranking/update_entry）+ `RankingRepository`（upsert/update_rank/query）+ `RankingEntryRecord` ORM；多级排序（return_pct + 赔率）；nested/flat 双视图输出；is_latest 版本淘汰；41 tests PASS。

- [x] `NTL-S5-005` `P1`
  目标：扩展 `TraderMemory` schema。
  输入：当前记忆结构。
  输出：新增 `postmortem`、`strategy_adjustment`、`market_regime_note`。
  修改范围：`src/trader_memory/schemas.py`。
  前置依赖：Stage 4 完成。
  可并行：`NTL-S5-006`、`NTL-S5-007`。
  验收标准：记忆结构足以存储盘后结果。
  完成情况：TraderMemoryType 新增 3 种类型（postmortem/strategy_adjustment/market_regime_note）；TraderMemoryItem 新增 idea_id/strategy_version_id/ranking_entry_id/postmortem_data/strategy_adjustment_data/market_regime_data 字段；TraderMemorySummary 新增 postmortem_notes/strategy_adjustments/market_regime_notes 字段；summarize_context 更新支持聚合 new types；22 tests PASS。

- [x] `NTL-S5-006` `P1`
  目标：扩展 `TraderMemory` service 检索能力。
  输入：扩展后的记忆 schema。
  输出：支持按版本、主题、标的检索。
  修改范围：`src/trader_memory/schemas.py`、`src/trader_memory/service.py`、`src/db/migrations/`。
  前置依赖：`NTL-S5-005`。
  可并行：`NTL-S5-007`。
  验收标准：下次盘前能按上下文取回相关记忆。
  完成情况：TraderMemoryItem 新增 topic_source/raw_topic_ids 字段（dict[str, list[str]]）；TraderMemoryFilter 新增 tags/strategy_version_id 字段；_apply_filter 实现 tags 任一命中 + strategy_version_id 精确匹配；新增 topic_mapping Alembic migration；27 tests PASS；NTL-S5-006 前置集成：DailyReport.market_universe_snapshot、source_topic_ids 使用 "topic_name|kind" 编码格式（直接来自 topic_constituents，不依赖 hot_topics 查表）、_build_topic_tags 解析编码生成 canonical tag；5 commits 完成。

- [x] `NTL-S5-007` `P1` ✅ 2026-04-25
  目标：扩展 review task 结构。
  输入：盘后归因需求。
  输出：支持结构化失败归因的 review task。
  修改范围：`src/schemas/review_task.py` 或相关文件。
  前置依赖：`NTL-S1-005`、Stage 4 完成。
  可并行：`NTL-S5-006`。
  验收标准：盘后复盘任务输入结构完整。
  完成情况：`ReviewTaskDetails.failure_category` 从 `str` 升级为 `FailureAttribution | None`，与 `PostmortemResult.failure_attribution` 类型对齐；测试更新。

- [x] `NTL-S5-008` `P1` ✅ 2026-04-25
  目标：把 postmortem 接入任务系统。
  输入：postmortem service。
  输出：`run_postmortem_analysis` 任务。
  修改范围：任务处理模块。
  前置依赖：`NTL-S5-003`、`NTL-S5-007`。
  可并行：无。
  验收标准：盘后复盘可通过任务系统运行。
  完成情况：新增 `src/pipeline/tasks/postmortem_tasks.py`（handle_postmortem_analysis）；run_after_close 末尾为未通过评估的 idea 创建 postmortem_analysis 任务；process_tasks.py 注册 handler；自动归因结果以 TraderMemoryType.postmortem 写回 TraderMemoryStore；4 tests PASS。

- [x] `NTL-S5-009` `P1` ✅ 2026-04-25
  目标：让 Manager 生成 Evidence Pack。
  输入：Evidence Pack 模块和盘前输出上下文。
  输出：盘后流程中生成 Evidence Pack。
  修改范围：`src/agents/manager_agent/agent.py` 或 service。
  前置依赖：`NTL-S5-001`、`NTL-S4-006`。
  可并行：`NTL-S5-010`、`NTL-S5-011`。
  验收标准：每条盘前建议都能生成对应证据包。
  完成情况：
  - 新增 StrategyLibraryRepository.get_by_version_id + StrategyLibraryService.get_version
  - manager_agent 新增 5 个辅助方法（_generate_evidence_pack / _save_evidence_pack / _load_signal_context / _fetch_full_market_data / _load_strategy_version_snapshot）
  - run_after_close 中调用 EvidencePack 生成并持久化到 JSON；postmortem_tasks 从 JSON 加载
  - EvidencePack.market_data 统一为 MarketDataSnapshot 结构化 schema，避免下游多处分支判断
  - _save_evidence_pack 新增 evidence_pack_index.json 索引（idea_id -> pack_id），postmortem_tasks 查找从 O(n) 降为 O(1)
  - 95 tests PASS。

- [x] `NTL-S5-010` `P1`
  目标：升级盘后评分口径。
  输入：新评估 schema、行情数据。
  输出：支持 `MFE / MAE / 规则命中 / 前置条件违背`。
  修改范围：Manager 盘后逻辑、evaluation 模块。
  前置依赖：`NTL-S5-001`、`NTL-S5-002`、`NTL-S1-005`。
  可并行：`NTL-S5-009`、`NTL-S5-011`。
  验收标准：盘后评估不再只依赖当前价格。
  完成情况：
  - 新增 `metrics_calculator.py`（compute_mfe_mae_return + rules_hit 提取）
  - `postmortem_service.py` 集成计算并增强归因逻辑（亏损 + rules_hit 非空 → RULE_PRECONDITION_FAILED）
  - A股交易规则约束：新增 TradeConstraint 配置类，支持 T+1（entry_date 当日不检查止盈止损）和涨跌停限制（主板 10%/创业板 20%/科创板 20%/ST 5%），根据股票代码自动推断板块类型
  - 停牌/无成交识别：新增 _is_bar_halted()，支持显式 is_halted 标志和 volume==0+价格无波动双重规则；volume 字段缺失时不默认视为 0，避免正常数据被误判为停牌
  - 返回结果扩展为 7 元组：新增 halted_dates（停牌日期列表）和 eval_date（评估截止日），exit_date 语义修正为"实际出场日"（None 表示未出场）
  - 109 tests PASS。

- [x] `NTL-S5-011` `P1` ✅ 2026-04-25
  目标：在盘后生成 ranking。
  输入：ranking service、盘后评分结果。
  输出：盘后 ranking 结果。
  修改范围：Manager 盘后逻辑、evaluation 模块。
  前置依赖：`NTL-S5-004`、`NTL-S5-010`。
  可并行：`NTL-S5-009`。
  验收标准：可以按 trader、策略版本等输出 ranking。
  完成情况：handle_postmortem_analysis 中在完成复盘后调用 RankingService.add_entry；ranking_task 在 postmortem_analysis 之后执行；ranking 结果通过 RankingRepository 持久化。

- [x] `NTL-S5-012` `P1` ✅ 2026-04-25
  目标：差评触发 LLM 归因并写回记忆。
  输入：postmortem 结果、记忆 service。
  输出：自动写回差评复盘结论。
  修改范围：Manager 盘后逻辑、`src/trader_memory/`。
  前置依赖：`NTL-S5-003`、`NTL-S5-006`、`NTL-S5-010`。
  可并行：无。
  验收标准：差评案例会形成可复用记忆。
  完成情况：
  - TraderMemoryItem 新增 `extra` 字段（存储 auto_original）；TraderMemoryStore 新增 `update()` 方法（load+modify+save 模式）
  - PostmortemService 新增 `llm_attribution()` 方法：调用 LLMClient.complete_json(*, system_prompt, user_prompt)，支持降级为 auto
  - prompts/llm_attribution.md：提取 LLM 归因 prompt 模板（标准字段：{symbol}/{side}/{entry}/{target_price}/{stop_loss_price}/{bars}/{auto_reason}/{auto_confidence}，兼容旧占位符 {target}/{stop_loss}）
  - handle_postmortem_analysis：查找已有的 failure_case 条目，存在则原地更新（update），不存在才 append
  - run_after_close：从 signal_context 提取 trigger_rules + confidence 作为 auto_attribution 传入 postmortem_task details
  - 修复 PostgreSQL constraint name 长度超限（68 chars → 19 chars "uq_tsv_trader_dt_ver"）
  - 105 tests PASS

- [x] `NTL-S5-013` `P1` ✅ 2026-04-26
  目标：替换当前仅基于 `current_price` 的简化评估逻辑。
  输入：新评分与归因逻辑。
  输出：旧盘后简化逻辑降级或退出主路径。
  修改范围：`src/agents/manager_agent/agent.py`、相关 service。
  前置依赖：`NTL-S5-010`。
  可并行：`NTL-S5-014`。
  验收标准：主路径盘后评估已使用新评分口径。
  完成情况：
  - IdeaEvaluation.status 扩展为 Literal["ok", "partial", "fallback", "not_evaluated"]
  - current_price 字段标注废弃（语义变为 exit_price）
  - run_after_close 评估循环重构：先生成 EvidencePack 获取 bars，再计算 mfe/mae/return_pct
  - 状态判断：完整 bars → ok；bars < 2 → partial；无 bars + 有 current_price → fallback；无 entry_price → not_evaluated
  - 143 core module tests PASS，2 pre-existing failures (UniqueViolationError on ranking_entries)
  - 2026-04-26 复核：补齐 `partial_data` / `fallback_reason` 结构化字段、partial/fallback 日志、`postmortem_notes` 输出与写回。

- [x] `NTL-S5-014` `P1`
  目标：验证记忆写回可被下次消费。
  输入：盘前与盘后记忆写回逻辑。
  输出：验证用例或集成测试。
  修改范围：`tests/`、`src/trader_memory/`。
  前置依赖：`NTL-S5-012`。
  可并行：无。
  验收标准：下一次盘前能读取前一次的 postmortem 结果。
  完成情况：Memory write → read 完整链路验证通过。`handle_postmortem_analysis` → `summarize_context` → `_memory_hint()` → idea rationale。`by_type["success_case/failure_case"]` 正确影响 confidence。110 tests PASS（manager_agent/evaluation/trader_memory）。asyncpg event loop 警告为测试 infrastructure 问题，不影响逻辑。

### Stage 5 完成标准

- 盘后不再只是简单收益率汇总。
- 已具备评分、ranking、归因、记忆写回能力。

**Stage 5 总结文档**：[2026-04-26-Stage5-Summary-Design.md](../superpowers/specs/2026-04-26-Stage5-Summary-Design.md)

---

## 15. Stage 6：开发期离线回测与规则验真（P1）

### Stage 目标

- 建立开发期离线回测能力。
- 对 LLM 规则做程序化验真和筛选。

### 阶段交付物

- `src/backtest/` 模块。
- 回测 CLI。
- 规则验真白名单和报告。

### 任务清单

- [ ] `NTL-S6-001` `P1`
  目标：建立回测 schema。
  输入：快照、策略版本、评分口径。
  输出：`src/backtest/schemas.py`。
  修改范围：`src/backtest/`。
  前置依赖：Stage 2、Stage 3 完成。
  可并行：`NTL-S6-002`、`NTL-S6-003`。
  验收标准：回测输入输出结构清晰。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 1）

- [ ] `NTL-S6-002` `P1`
  目标：建立回测执行器。
  输入：回测 schema。
  输出：`src/backtest/execution.py`。
  修改范围：`src/backtest/`。
  前置依赖：`NTL-S6-001`。
  可并行：`NTL-S6-003`。
  验收标准：可按策略版本和快照执行回放。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 2）

- [ ] `NTL-S6-003` `P1`
  目标：建立回测评分模块。
  输入：线上评分口径。
  输出：`src/backtest/scoring.py`。
  修改范围：`src/backtest/`。
  前置依赖：Stage 5 评分设计或兼容口径。
  可并行：`NTL-S6-002`。
  验收标准：回测评分口径与线上一致。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 3）

- [ ] `NTL-S6-004` `P1`
  目标：建立回测引擎。
  输入：执行器和评分模块。
  输出：`src/backtest/engine.py`。
  修改范围：`src/backtest/`。
  前置依赖：`NTL-S6-002`、`NTL-S6-003`。
  可并行：`NTL-S6-005`。
  验收标准：能按 trader / 日期区间完整回测。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 4）

- [ ] `NTL-S6-005` `P1`
  目标：建立回测报告模块。
  输入：回测结果。
  输出：`src/backtest/reporting.py`。
  修改范围：`src/backtest/`。
  前置依赖：`NTL-S6-004`。
  可并行：`NTL-S6-008`。
  验收标准：回测结果有可读报告输出。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 5）

- [ ] `NTL-S6-006` `P1`
  目标：让回测读取快照和策略版本，而不是实时取数。
  输入：快照服务和策略库。
  输出：离线回放读取逻辑。
  修改范围：`src/backtest/`、快照读取逻辑。
  前置依赖：`NTL-S6-004`、Stage 2、Stage 3 完成。
  可并行：`NTL-S6-007`。
  验收标准：相同输入可重复回放。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 6）

- [ ] `NTL-S6-007` `P1`
  目标：回测与线上共用 scoring 口径。
  输入：线上评分逻辑与回测评分模块。
  输出：统一 scoring 组件或共享接口。
  修改范围：`src/evaluation/`、`src/backtest/`。
  前置依赖：`NTL-S6-003`、Stage 5 完成。
  可并行：`NTL-S6-006`。
  验收标准：同一案例线上线下评分结果差异可解释。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 7）

- [ ] `NTL-S6-008` `P1`
  目标：增加回测 CLI 入口。
  输入：回测引擎。
  输出：按 trader / 区间回测命令。
  修改范围：`cli/`。
  前置依赖：`NTL-S6-004`、`NTL-S6-005`。
  可并行：无。
  验收标准：可直接从命令行运行回测。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 8）

- [ ] `NTL-S6-009` `P1`
  目标：建立 LLM 规则白名单。
  输入：现有规则抽取结果。
  输出：规则 -> 所需字段 / 可程序化程度映射。
  修改范围：规则文档、配置或数据文件。
  前置依赖：Stage 3 或现有规则抽取能力可用。
  可并行：`NTL-S6-010`。
  验收标准：可区分能直接验真的规则与不能直接验真的规则。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 9）

- [ ] `NTL-S6-010` `P1`
  目标：对高频规则做命中验证。
  输入：规则白名单与历史快照。
  输出：10 到 20 条高频规则的命中验证结果。
  修改范围：回测或规则验证模块。
  前置依赖：`NTL-S6-009`、`NTL-S6-006`。
  可并行：`NTL-S6-011`。
  验收标准：至少一批规则完成命中验证。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 10）

- [ ] `NTL-S6-011` `P1`
  目标：输出规则覆盖率、命中率、后验收益分布。
  输入：规则验证结果。
  输出：验证报告。
  修改范围：回测报告或单独报告模块。
  前置依赖：`NTL-S6-010`。
  可并行：无。
  验收标准：能据此筛掉明显无效规则。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 11）

- [ ] `NTL-S6-012` `P1`
  目标：停止继续扩展旧 `backtest_agent` 路线。
  输入：新 backtest 模块。
  输出：旧目录说明与主路径切换。
  修改范围：文档、旧 agent 目录说明。
  前置依赖：`NTL-S6-004`。
  可并行：`NTL-S6-013`。
  验收标准：后续回测开发统一进入 `src/backtest/`。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 12）

- [ ] `NTL-S6-013` `P1`
  目标：验证回测结果可复现。
  输入：相同快照、相同策略版本、相同 scoring 口径。
  输出：复现验证结果。
  修改范围：测试、验证脚本。
  前置依赖：`NTL-S6-006`、`NTL-S6-007`。
  可并行：无。
  验收标准：同一输入重复运行结果一致或差异可解释。
  实施计划：[2026-04-25-stage6-implementation-plan.md](../superpowers/plans/2026-04-25-stage6-implementation-plan.md)（对应 Task 13）

### Stage 6 完成标准

- 能按日期区间复现某 trader 当日可见信息。
- 能对高频规则做命中验证并筛掉明显无效规则。

---

## 16. Stage 7：自主优化与运行可观测性（P2）

### Stage 目标

- 在不破坏正式版本的前提下，建立候选优化闭环。
- 增强 API、CLI、告警与测试。

### 阶段交付物

- 自主优化策略建议。
- API/CLI 扩展。
- 数据新鲜度与快照缺失告警。
- 更完整的回归测试。

### 任务清单

- [ ] `NTL-S7-001` `P2`
  目标：基于 ranking 与回测筛选活跃 trader。
  输入：Stage 5 ranking、Stage 6 回测结果。
  输出：活跃 trader 筛选逻辑。
  修改范围：优化模块或 service。
  前置依赖：Stage 5、Stage 6 完成。
  可并行：`NTL-S7-002`。
  验收标准：能识别值得继续优化的 trader。

- [ ] `NTL-S7-002` `P2`
  目标：基于 postmortem 结果输出策略调整建议。
  输入：盘后归因和回测结果。
  输出：策略调整建议。
  修改范围：优化模块、evaluation 或 strategy_library。
  前置依赖：Stage 5、Stage 6 完成。
  可并行：`NTL-S7-001`。
  验收标准：调整建议有明确输入依据。

- [ ] `NTL-S7-003` `P2`
  目标：把策略调整建议写入候选版本而不是覆盖 released 版本。
  输入：策略调整建议与策略版本库。
  输出：候选版本生成机制。
  修改范围：`src/strategy_library/`。
  前置依赖：`NTL-S7-002`。
  可并行：`NTL-S7-004`。
  验收标准：正式版本不会被自动优化结果直接覆盖。

- [ ] `NTL-S7-004` `P2`
  目标：建立滚动评估窗口。
  输入：ranking、回测结果和调整建议。
  输出：滚动评估逻辑。
  修改范围：优化模块。
  前置依赖：`NTL-S7-001`、`NTL-S7-002`。
  可并行：`NTL-S7-003`。
  验收标准：不会因为单日噪声直接触发过拟合调整。

- [ ] `NTL-S7-005` `P2`
  目标：扩展 API 查询能力。
  输入：策略版本、快照、ranking、回测结果。
  输出：API 查询接口。
  修改范围：`api/`、`src/api/`。
  前置依赖：Stage 5、Stage 6 完成。
  可并行：`NTL-S7-006`、`NTL-S7-007`。
  验收标准：可通过 API 查询核心资产和结果。

- [ ] `NTL-S7-006` `P2`
  目标：扩展 CLI。
  输入：快照、策略库、回测与评估能力。
  输出：构建快照、构建策略版本、执行回测等命令。
  修改范围：`cli/`。
  前置依赖：Stage 5、Stage 6 完成。
  可并行：`NTL-S7-005`、`NTL-S7-007`。
  验收标准：关键链路都能通过 CLI 触发。

- [ ] `NTL-S7-007` `P2`
  目标：增加数据新鲜度、快照缺失、provider 失败告警。
  输入：运行日志与快照状态。
  输出：告警逻辑。
  修改范围：`src/alerting/`、任务系统或监控配置。
  前置依赖：Stage 2、Stage 5 完成。
  可并行：`NTL-S7-005`、`NTL-S7-006`。
  验收标准：关键数据问题能被及时发现。

- [ ] `NTL-S7-008` `P2`
  目标：增加关键链路集成测试与回归测试。
  输入：盘前、盘后、回测主链路。
  输出：关键链路测试集合。
  修改范围：`tests/`。
  前置依赖：Stage 4、Stage 5、Stage 6 完成。
  可并行：无。
  验收标准：关键链路至少具备一组稳定回归用例。

### Stage 7 完成标准

- 已形成“正式版本 + 候选优化版本”的双轨机制。
- 关键链路可观察、可告警、可查询、可回归。

---

### Stage 8. 实际市场约束

- [ ] 增加实际市场约束

1. 主板（沪市、深市）涨停板定义 普通股票‌：‌±10‌%，科创板股票‌：‌±20%‌，创业板股票‌：‌±20%定义
2. 一字涨停板无法买入成交， 除非盘中开板，如果买入的话可以按涨停价格计算
3. 一字跌停板无法卖出成交， 除非盘中开板，如果卖出的话可以按跌停价格计算
4. 如果以开盘价格买入和卖出 需要按照这个规则计算成交价: A股市场沪深主板、科创板、创业板的限价申报价格不得高于基准价格的 102% 且不得低于 98%，北交所则为 105% 和 95%

---

## 17. 并行执行规则

### 17.1 明确可并行的任务包

- Stage 1 完成后：
  - `NTL-S2-002` ~ `NTL-S2-006`
  - `NTL-S2-008` ~ `NTL-S2-011`
  - `NTL-S3-001` ~ `NTL-S3-004`
- Stage 4 完成后：
  - `NTL-S5-001` ~ `NTL-S5-004`
  - `NTL-S6-001` ~ `NTL-S6-005`
- 文档与样例验证：
  - `NTL-S0-011` 与 `NTL-S0-014`
  - `NTL-S1-013`
  - `NTL-S4-011`
  - `NTL-S5-014`
  - `NTL-S6-013`

### 17.2 不建议并行的任务

- 同时重写 `ManagerAgent` 与 `TraderAgent` 主流程。
- 同时改配置层、契约层和 migration 但不先锁定 schema。
- 在 Stage 2 未完成时直接做 Stage 4 主链路切换。
- 在 Stage 5 未统一 scoring 前先做大量回测结果对比。

---

## 18. 当前推荐执行顺序

### 18.1 最近必须先做的任务

1. `NTL-S0-007` ~ `NTL-S0-010`
2. `NTL-S0-014`
3. `NTL-S1-001` ~ `NTL-S1-013`
4. `NTL-S15-001` ~ `NTL-S15-010`
5. `NTL-S2-001` ~ `NTL-S2-024`

### 18.2 当前不要做的事

- 不要先做 UI。
- 不要先做分钟级高频回测。
- 不要先让私有接口直接接管现有盘前链路。
- 不要继续增强旧 `watchlist + last_price` 主路径。
- 不要继续在旧 `AlignmentAgent` 路线投入主线开发。

---

## 19. 与旧任务文档的关系

- 旧 `docs/TaskList.md` 中已完成的基础能力，默认视为本清单的“已有可复用基础”。
- 旧多 Agent 草图、旧 Alignment 主线、宿主薄壳、图片处理等任务，不再作为当前主线。
- 旧 `Proposed-Plan` 中与策略版本、候选池、ranking、backtest 相关的有效内容，已吸收到本清单。

---

## 20. 维护规则

后续更新本清单时，必须遵守：

1. 不新增没有输入、输出、验收标准的任务。
2. 不新增只描述“方向”但没有明确产物的任务。
3. 不把多个独立交付混在一个任务里。
4. 如果代码实现与目标不符，优先补“代码对齐改造项”。
5. 如果某 Stage 的完成标准还没满足，不得把后续 Stage 标为主线已完成。
