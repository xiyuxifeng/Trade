# New-Web Data Storage Migration Plan

> 目标：以“3 年回测可复现、可查询、可审计”为硬约束，结合当前数据库结构，明确项目中哪些数据应作为数据库事实源，哪些应继续保留为文件/Artifact，并给出分阶段迁移矩阵。
>
> 适用范围：`trade-strategy-ai` 当前代码、现有 ORM 模型、现有文件落地路径、以及 `New-Web-*` 体系中的市场/策略/回测/运行时数据。

---

## 1. 结论先行

当前项目不是“纯数据库”也不是“纯文件”，而是一个已经形成边界的混合存储系统。

推荐原则很简单：

1. **可查询、可聚合、可回溯的业务事实进数据库。**
2. **原始输入、运行产物、下载件、调试件继续保留文件。**
3. **文件层可以长期保留，但不能再作为唯一业务事实源。**
4. **数据库只保存 `storage_ref` / `artifact_ref` / `summary`，不要保存服务器绝对路径。**
5. **3 年回测优先依赖能做范围查询和版本联动的存储结构，避免为同一份事实长期保留两套可查询副本。**

---

## 2. 现有数据库结构分析

从当前 `src/models/` 和 `src/db/repositories/` 看，项目已经有四类比较明确的数据库事实层。

### 2.1 运行时与审计层

已存在或已规划的表/模型：

- `jobs`
- `job_audit_events`
- `workflow_runs`
- `workflow_run_steps`
- `step_timeline`
- `data_audit_event`
- `security_audit_event`
- `users`
- `user_sessions`

这一层适合放：

- 作业生命周期
- 工作流运行历史
- 审计记录
- 权限和会话信息

### 2.2 配置与身份层

已存在或已规划的表/模型：

- `config_profiles`
- `trader_strategy_versions`
- `trader_memory`
- `signals`

这一层适合放：

- 正式配置画像
- 配置版本
- 策略版本快照
- 交易信号事实
- 运行时可复现的长期事实

### 2.3 内容与抓取层

已存在或已规划的表/模型：

- `raw_articles`
- `blog_articles`
- `article_metadata`
- `crawl_state`
- `stock_info`
- `trade_log`
- `ranking_entry`
- `alignment_result`

这一层适合放：

- 抓取原始数据
- 清洗后内容
- 文章结构化元数据
- 交易、归因、排名等可查询事实

### 2.4 市场与策略层

已存在或已规划的表/模型：

- `ohlcv_bar`
- `indicator`
- `market_snapshots`
- `market_snapshot_sections`
- `market_snapshot_items`
- `market_datasets`
- `market_data_quality_reports`
- `hot_topics_snapshots`
- `topic_constituents_snapshots`
- `strong_symbols_snapshots`
- `market_regimes`
- `market_regime_features`
- `rule_applicability_profiles`
- `trader_strategy_versions`
- `evidence_packs`

这一层适合放：

- 市场快照
- 候选池三快照
- 市场状态特征
- 市场状态记录
- 规则适用性画像
- 策略版本
- 证据包
- 可查询的派生事实

### 2.5 仍以文件形态承载的回测输入与运行产物

当前项目里，下面这些目录/文件仍然是 3 年回测链路中的有效文件层：

- `data/market_universe/snapshots/**`
- `data/config_snapshots/**`
- `data/profile_snapshots/**`
- `data/processed/strategy_regime_selection/**`
- `data/patterns/canonical/**`
- `data/processed/dashboard/dashboard.html`
- `data/processed/pipeline/stock_info/stock_info_stats.json`
- `data/processed/phase0/**`
- `data/processed/kaipan/**`
- `data/jobs/**`
- `data/kaipan/raw/**`
- `data/kaipan/snapshots/**`
- `data/backtest/trading_calendar.json`
- `data/signals/**`（归档/导出用途）

---

## 3. 迁移原则

### 3.1 应迁移到数据库的数据

满足任一条件，就应该把它作为数据库事实源：

- 会被 UI 过滤、列表、搜索、分页
- 会被规则选择、回测、策略推荐复用
- 需要审计或追责
- 需要跨 Job / Workflow / Profile 关联
- 需要按字段做聚合统计
- 需要长期保存并版本化
- 需要支持 3 年回测中的范围查询、版本联动和结果复现

### 3.2 应继续保留文件的数据

满足任一条件，就应该继续保留为文件或 Artifact：

- 原始抓取响应
- 大体积明细输出
- 人工下载件
- 调试回放件
- 报表 Markdown / HTML
- 需要按目录结构做版本归档的运行产物
- 直接作为回测输入的轻量快照文件
- 当前还没有 DB 承接、但仍被回测/运行链路消费的不可逆结果归档

### 3.3 混合存储的标准写法

如果同一份事实既要可查询又要可回放，推荐：

1. 只保留一份**长期 canonical** 存储。
2. 对于回测 / 联动 / 查询类结构化数据，canonical 选数据库。
3. 对于原始证据、报表、下载件，canonical 选文件。
4. 如果必须同时保留两种形态，文件必须只是**导出件 / 证据件**，不能再作为第二套业务事实源。
5. 数据库只保存 `storage_ref` / `artifact_ref`，不保存绝对路径。

---

## 4. 迁移矩阵

### 4.1 已经是数据库事实源的内容

这些数据已经在 DB 里，不需要再迁移，只需要继续收口，避免重新回到文件层。

| 数据域 | 当前模型/表 | 当前状态 | 建议 | 原因 |
| --- | --- | --- | --- | --- |
| Job 生命周期 | `jobs` / `job_audit_events` | DB canonical | 保持 DB | 需要列表、详情、审计、状态流转 |
| Workflow 运行 | `workflow_runs` / `workflow_run_steps` / `step_timeline` | DB canonical | 保持 DB | 需要编排、回放、失败分析 |
| 用户与会话 | `users` / `user_sessions` | DB canonical | 保持 DB | 权限和登录状态必须可控 |
| 运行配置画像 | `config_profiles` | DB canonical | 保持 DB | 取代长期 `config_path` 作为事实源 |
| 文章抓取与清洗 | `raw_articles` / `blog_articles` / `article_metadata` / `crawl_state` | DB canonical | 保持 DB | 文章链路必须可查询和去重 |
| 股票基础信息 | `stock_info` | DB canonical | 保持 DB | 主数据表，跨业务复用 |
| 行情与指标 | `ohlcv_bar` / `indicator` | DB canonical | 保持 DB | 回测、策略、市场分析都依赖 |
| 市场快照 | `market_snapshots` / `market_snapshot_sections` / `market_snapshot_items` / `market_datasets` / `market_data_quality_reports` | DB canonical | 保持 DB | 市场 snapshot 已经是结构化主事实源 |
| 候选池三快照 | `hot_topics_snapshots` / `topic_constituents_snapshots` / `strong_symbols_snapshots` | DB canonical | 保持 DB | 3 年回测需要稳定的候选池底层输入，不应再扫描文件目录 |
| 市场状态特征 | `market_regime_features` | DB canonical | 保持 DB | 供 regime / backtest / UI 查询 |
| 市场状态记录 | `market_regimes` | DB canonical | 保持 DB | 市场状态定义和历史回溯需要 |
| 规则适用性画像 | `rule_applicability_profiles` | DB canonical | 保持 DB | 规则池要可解释、可版本化 |
| 交易信号 | `signals` | DB canonical | 保持 DB | 信号需要做版本、归因和回测联查 |
| 策略版本 | `trader_strategy_versions` | DB canonical | 保持 DB | 3 年回测必须能回放策略版本 |
| 证据包 | `evidence_packs` | DB canonical | 保持 DB | 归因和 ranking 需要长期可查询 |
| 排名/交易/归因 | `ranking_entry` / `trade_log` / `alignment_result` | DB canonical | 保持 DB | 典型查询型业务事实 |

### 4.2 应迁移到数据库的内容

这些数据当前仍有文件事实源，或者文件 + DB 边界不够清晰。建议把“可查询摘要 / 索引 / 运行结果元数据”迁移到 DB。

| 数据域 | 当前文件存储 | 建议 DB 目标 | 建议状态 | 原因 |
| --- | --- | --- | --- | --- |
| 回测结果摘要 | `data/backtest/results/**/result.json`、`report.md`、`records.csv` | `backtest_result_runs` | 已落地摘要表，文件仅保留完整报告 / 导出件 | UI / 规则池 / 画像都按回测摘要查询，文件只适合保留完整报告 |
| 回测规则验真摘要 | `data/backtest/results/**/validate_rules*.json/md` | 同回测结果表或独立验真表 | 应迁移摘要 | 验真结果需要和策略、规则、回测关联查询 |
| Regime-aware rule selection | `data/processed/strategy_regime_selection/**.json` | `strategy_regime_selections` / `regime_rule_selections` | 已落地摘要表，文件仅保留 artifact | 这是高价值业务事实，后续 UI / 审计 / 回放 / 回测都要查 |
| Config snapshot | `data/config_snapshots/*.json` | 新增 `config_snapshots` 或 `config_profile_snapshots` 表 | 当前保留文件，建议未来仅迁移元数据 | 需要版本、hash、来源和回放能力 |
| Profile snapshot | `data/profile_snapshots/*.json` | 目前无对应 DB 表；如果要跨系统查询，建议补 `profile_snapshots` 摘要表 | 当前保留文件 | 这是 job/运行的冻结配置快照，3 年回测复现时有价值，但当前不宜与 `config_profiles` 混写 |
| Signal 归档 | `data/signals/{date}/{signal_id}.json` | `signals` 表（现有）+ 可选归档索引 | 建议以 DB 记录为主，文件只保留归档/导出 | 信号已在 DB 中存在，文件应避免成为第二套事实源 |
| Kaipan 归一化中间态 | `data/kaipan/snapshots/**` | 仅保留为 artifact，不做主查询源 | 不建议迁移完整中间态 | 这是调试产物，体积和重复度都高 |
| EvidencePack 索引 | 旧实现中的 index 文件 | 以 `evidence_packs` 表为准 | 已有 DB，继续收口 | 不再依赖目录扫描做业务查询 |

### 4.3 应继续保留文件的内容

这些数据不建议迁移成数据库主表，原因通常是体积大、偏运行产物、偏原始输入，或者更适合目录化归档。

| 数据域 | 当前文件存储 | 建议保留方式 | 原因 |
| --- | --- | --- | --- |
| Market Snapshot artifact | `data/processed/market_snapshot/{trade_date}/{slot}/snapshot.json` | 保留文件，DB 存摘要和引用 | 完整结构化快照便于回放、排障、离线比对 |
| Market Snapshot summary | `snapshot.summary.json` | 保留文件，DB 存摘要 | 适合人工复核和 Job Detail 展示 |
| Market Snapshot quality report | `snapshot.quality.json` | 保留文件，DB 存质量摘要 | 质量审计需要完整报告 |
| 候选池快照 | `data/market_universe/snapshots/{trade_date}/{slot}.json` | 保留文件，作为 3 年回测直接输入 | 当前 loader 直接读取该目录，且没有对应 DB 表 |
| Config snapshot | `data/config_snapshots/*.json` | 保留文件，DB 仅保留引用和摘要 | 配置冻结件需要可回放、可比对 |
| Profile snapshot | `data/profile_snapshots/*.json` | 保留文件，DB 仅保留引用和摘要 | 运行时 profile 冻结件用于 job 复现 |
| Pattern library | `data/patterns/canonical/*.yaml` | 保留文件 | 这是定义层，不是运行事实层 |
| Dashboard report | `data/processed/dashboard/dashboard.html` | 保留文件 | 人工审阅和交付展示件 |
| Pipeline stats | `data/processed/pipeline/stock_info/stock_info_stats.json` | 保留文件 | 派生统计件，适合文件交付 |
| Phase 0 输出 | `data/processed/phase0/**` | 保留文件 | 当前兼容输出目录，属于运行产物 |
| Kaipan 原始抓取缓存 | `data/kaipan/raw/**` | 保留文件 | 原始证据、接口排查、回放最合适 |
| Kaipan 归一化中间态 | `data/kaipan/snapshots/**` | 保留文件 | 调试/回放/对照用，不适合做主事实源 |
| Kaipan 处理产物 | `data/processed/kaipan/**` | 保留文件 | 批处理/回放/调试产物，偏运行 artifact |
| Job 目录产物 | `data/jobs/{job_id}/**`（如 `job.log`、`params.json`、`result.json`、`artifacts.json`、`config_snapshot.json`、`profile_snapshot.json`） | 保留文件，DB 存索引 | 这是 Job 运行产物，不应只靠 DB 重构完整过程 |
| 回测完整报告 | `report.md`、`records.csv`、`result.json` | 保留文件，DB 存摘要 | 报表和明细文件适合下载和审阅 |
| 交易日历 | `data/backtest/trading_calendar.json` | 保留文件 | 小体积、低频更新、运行时 fallback 合理 |
| 信号归档 | `data/signals/**` | 保留文件归档 | 历史可回放、可压缩、可分目录管理；但查询应优先走 `signals` 表 |
| 证据包 artifact | `evidence_packs/*.json` | 可保留文件，DB 为主查询 | 需要下载和回放，但查询应走 DB |
| 配置模板与 provider schema | `config/*.yaml`、`src/providers/kaipan_schema/*.yaml` | 保留文件 | 这是定义层，不是运行事实层 |

### 4.4 文件 canonical 与 artifact 边界

为了避免“同一份事实保留两套长期可查询副本”，文件层只允许两种角色：

#### 4.4.1 文件 canonical

以下路径仍然可以作为长期 canonical 文件，但它们承担的是**定义层 / 直接输入层**职责，不是业务查询主入口：

- `data/market_universe/snapshots/**`：候选池快照，当前 3 年回测 loader 直接读取
- `data/config_snapshots/**`：配置冻结件，保留 hash、来源和复现能力
- `data/profile_snapshots/**`：运行时 profile 冻结件，用于 job 复现
- `data/patterns/canonical/**`：模式库定义层
- `data/backtest/trading_calendar.json`：运行时 fallback 日历

#### 4.4.2 文件 artifact

以下路径只允许作为 artifact、下载件、调试件或回放件，不再作为业务主查询入口：

- `data/backups/**`
- `data/logs/**`
- `data/params/**`
- `data/processed/alignment/**`
- `data/processed/alignment_cache/**`
- `data/processed/crawl/**`
- `data/processed/market_snapshot/**`
- `data/processed/market_regime_features/**`
- `data/processed/market_regimes/**`
- `data/processed/market_data/**`
- `data/processed/persona/**`
- `data/processed/strategy_regime_selection/**`
- `data/processed/rule_applicability/**`
- `data/processed/dashboard/dashboard.html`
- `data/processed/pipeline/**`
- `data/processed/pipeline/stock_info/stock_info_stats.json`
- `data/processed/phase0/**`
- `data/processed/duckdb/**`
- `data/processed/kaipan/**`
- `data/kaipan/raw/**`
- `data/kaipan/snapshots/**`
- `data/jobs/**`
- `data/signals/**`
- `evidence_packs/*.json`

#### 4.4.3 旧兼容模块

以下代码路径保留为历史兼容实现或回放辅助，但不能再作为新的业务事实层入口：

- `src/strategy/signal_version.py`：仅保留历史兼容与归档读取能力，正式信号写入与查询必须走 DB

#### 4.4.4 统一约束

- 文件 canonical 只用于“直接输入 / 定义 / 复现”，不承担跨系统业务查询。
- artifact 只通过 `storage_ref` / `artifact_ref` 暴露，不暴露服务器绝对路径。
- 对于已经有 DB canonical 的事实，文件层只允许保留 artifact，不允许再成为第二套事实源。

---

## 5. 分阶段迁移计划

### Phase 0: 事实源收口

目标：

- 明确“DB 是主查询源，文件是 artifact”
- 禁止新的业务逻辑继续把文件路径当主事实源

执行项：

- 所有 `storage_ref` 只保存逻辑引用
- 所有 UI / API 查询优先走 DB
- 文件只通过 `artifact` / `download` / `debug` 入口暴露

### Phase 1: 把高频查询结果迁入 DB

优先迁移：

- 回测结果摘要
- 回测验真摘要
- regime-aware rule selection 摘要
- config snapshot 元数据
- persona / market-state 结构化摘要

目标：

- 支持列表、筛选、分页、详情、审计
- 让 UI 和策略服务不再扫描文件目录

### Phase 2: 保留文件作为 artifact

确认保留：

- market snapshot 完整 artifact
- report / csv / html
- raw fetch / normalized cache
- job run payload
- signal archive

目标：

- 保持可回放、可调试、可下载
- 不把 artifact 再次演化成业务主事实源

### Phase 3: 选择性裁剪旧文件事实源

前提：

- DB 主链路稳定
- UI / API / Backtest / Rule Pool 都已切到 DB 查询
- 回放和审计都有替代方案

可裁剪对象：

- 文件主查询入口
- 旧目录扫描逻辑
- 重复索引文件

不建议直接裁剪：

- 原始抓取缓存
- Job 产物目录
- Market Snapshot 完整 artifact

---

## 6. 推荐落地顺序

1. 先把已经 DB 化的主事实源继续收口，不再增加新的文件查询分支。
2. 再补回测结果摘要表和 regime-aware selection 摘要表。
3. 保留完整 artifact 文件，但把 UI 和 API 的默认查询全部切到 DB。
4. 最后再评估哪些文件目录可以降级为纯归档。

---

## 7. 迁移判断标准

一个数据是否应该迁移到数据库，可以直接用下面的判断：

- 如果它要被列表页、筛选、搜索、分页使用，就进 DB。
- 如果它要被审计、归因、规则选择使用，就进 DB。
- 如果它只是完整原始响应、报表、日志或下载件，就留文件。
- 如果它既要可查询又要可回放，就 DB + 文件双轨，但 DB 必须是事实源。

---

## 8. 回测场景下的读取建议

当目标是做较长周期回测，例如连续 3 年数据回测时，**建议以数据库作为主读取层**，文件只保留为原始归档和回放材料。

### 8.1 为什么回测更适合读数据库

1. **范围查询更直接**
   - 回测通常按 `trade_date`、`symbol`、`dataset`、`feature_version`、`regime_version` 取数。
   - 这些天然是数据库的 `WHERE + INDEX` 场景。
   - 文件系统则需要目录遍历、路径拼装和额外缓存。

2. **多源联动更容易**
   - 回测往往要同时使用：
     - `market_snapshots`
     - `market_regime_features`
     - `rule_applicability_profiles`
     - `ohlcv_bar`
     - `trader_strategy_versions`
     - `backtest result`
   - 这些数据在 DB 中更容易统一关联和版本追踪。

3. **性能和稳定性更好**
   - 3 年回测会放大小文件扫描、目录递归、文件命名约定维护等成本。
   - 数据库配合索引、分页和批量查询，更适合长期稳定回测。

4. **复现更清晰**
   - 回测复现需要知道当时用了哪个 `snapshot_id`、`dataset_id`、`feature_version`、`rule_version`。
   - DB 更容易把这些事实连接成一条完整链路。

### 8.2 文件仍然保留什么作用

文件适合保留为：

- 原始抓取缓存
- 标准化快照 artifact
- Job 目录产物
- 回测 Markdown / CSV 报告
- 排障和离线重放材料

这些文件不应该作为 3 年回测的主查询源，而应该作为：

- 证据
- 审计
- 回放
- 下载件

### 8.3 对当前项目的推荐读取链路

如果你要做 3 年回测，推荐主读取链路优先使用：

- `market_snapshots`
- `market_snapshot_sections`
- `market_snapshot_items`
- `hot_topics_snapshots`
- `topic_constituents_snapshots`
- `strong_symbols_snapshots`
- `market_regime_features`
- `market_regimes`
- `rule_applicability_profiles`
- `ohlcv_bar`
- `trader_strategy_versions`
- `signals`
- `evidence_packs` 或回测摘要表

文件层只保留：

- `data/market_universe/snapshots/**`
- `data/config_snapshots/**`
- `data/profile_snapshots/**`
- `data/kaipan/raw/**`
- `data/kaipan/snapshots/**`
- `data/processed/market_snapshot/**`
- `data/processed/strategy_regime_selection/**`
- `data/processed/dashboard/dashboard.html`
- `data/processed/pipeline/stock_info/stock_info_stats.json`
- `data/processed/phase0/**`
- `data/processed/kaipan/**`
- `data/jobs/**`
- `data/patterns/canonical/**`
- `data/signals/**`
- 回测 report / csv / markdown

### 8.4 一句话结论

- **做 3 年回测：数据库优于文件**
- **文件适合做原始归档和回放**
- **最佳实践是 DB 作为查询层，文件作为证据层**

---

## 9. 3 年回测的索引建议

如果目标明确是 3 年回测，索引设计应当围绕两个原则：

1. **先按日期范围过滤，再按标的 / 版本 / 状态联动**
2. **不要为了“保留历史文件”再额外引入一套长期目录扫描索引**

### 9.1 现有表的索引基线

当前模型里的索引方向已经基本正确，适合 3 年回测的主查询：

| 表 | 已有索引 | 适用查询 |
| --- | --- | --- |
| `market_snapshots` | `(trade_date, market)`、`(profile_id, trade_date)`、`(quality_status, trade_date)` | 按日期、画像、质量状态筛快照 |
| `market_snapshot_sections` | `(snapshot_id, quality_status)`、`(section_id, quality_status)` | 按快照/section 做完整性和质量查询 |
| `market_snapshot_items` | `(snapshot_id, section_id)`、`(snapshot_id, symbol)`、`(dataset_id)`、`(section_id, quality_status)` | 按标的、section、dataset 回放明细 |
| `market_datasets` | `(trade_date, market)`、`(snapshot_id)`、`(dataset_type, trade_date)` | 按日期、快照、数据集类型取数 |
| `market_regime_features` | `(trade_date, market)`、`(snapshot_id)`、`(feature_version)` | 回测中按日期和 feature 版本取特征 |
| `market_regimes` | `(trade_date, market)`、`(snapshot_id)`、`(regime_version)` | 回测中按日期和 regime 版本追溯状态 |
| `rule_applicability_profiles` | `(rule_id)`、`(profile_version)`、`(source_backtest_id)`、`(review_status)`、`(created_at)` | 规则适用性画像的审计、回放、筛选 |
| `trader_strategy_versions` | `(trader_id, status)`、`(strategy_date)` | 策略版本回放和按时间筛选 |
| `jobs` | `(status, created_at)`、`(job_type, status)`、`(worker_id)` | 作业追踪、失败排查、任务筛选 |

### 9.2 回测查询的推荐组合

3 年回测的典型查询顺序建议统一为：

1. 先按 `trade_date` / `date_from` / `date_to` 缩小范围
2. 再按 `market` / `symbol` / `dataset_type` / `section_id` 关联
3. 再按 `feature_version` / `regime_version` / `profile_id` / `strategy_version` 过滤
4. 最后才读取 JSONB payload 或 artifact 引用

这样可以把“大范围扫描”限制在索引层，避免回测退化成目录遍历。

### 9.3 如果新增回测摘要表，建议补充的索引

3 年回测下，`backtest_result_runs` 已作为回测摘要 canonical，建议至少建立以下索引：

| 建议索引 | 作用 |
| --- | --- |
| `(trader_id, created_at)` | 按交易员查看最近回测 |
| `(strategy_version_id, created_at)` | 按策略版本回放结果 |
| `(date_from, date_to)` | 按回测区间筛选 |
| `(regime_version, source_feature_version)` | 追踪回测所用市场状态版本 |
| `(benchmark_symbol, created_at)` | 按基准标的对比 |
| `(result_version)` | 兼容结果 schema 演进 |

如果未来需要全文检索，优先对摘要字段做检索，不要把完整 `records.csv` 或原始明细再复制一份到新的文件目录里。

---

## 10. 最终迁移矩阵

这一节给出最终口径。对同一份结构化事实，**长期只保留一个 canonical 存储**。

### 10.1 长期应以数据库为 canonical 的数据

| 数据域 | 最终去向 | 3 年回测角色 | 原因 |
| --- | --- | --- | --- |
| Job 生命周期 / 审计 | DB | 回测任务、失败追踪、重跑 | 需要列表、筛选、状态流转和审计 |
| Workflow 运行 | DB | 任务编排回放 | 需要阶段级回放和失败定位 |
| 用户 / 会话 | DB | 权限和会话控制 | 必须统一管理 |
| 运行配置画像 | DB | 回测参数事实源 | 替代长期 `config_path` 作为事实源 |
| 文章抓取与清洗 | DB | 与市场/策略联动的数据源 | 需要去重、查询和版本化 |
| 股票基础信息 | DB | 回测标的主数据 | 跨模块复用 |
| 行情与指标 | DB | 回测输入主数据 | 3 年回测核心数据层 |
| 市场快照主表 / section / item / dataset / quality | DB | 回测主事实源 | 这是结构化市场事实的主链路 |
| 候选池三快照 | DB | 回测输入主事实 | `hot_topics_snapshots` / `topic_constituents_snapshots` / `strong_symbols_snapshots` |
| 市场状态特征 / 记录 | DB | regime 维度输入 | 回测、策略、UI 都需要联查 |
| 规则适用性画像 | DB | 回测与规则选择联动 | 需要解释性和可审计性 |
| 证据包主记录 | DB | 归因与对比 | 查询和追踪比文件目录更稳定 |
| 排名 / 交易 / 归因 | DB | 策略结果和归因 | 典型查询型事实 |
| 交易信号 | DB | 回测信号复现 | 信号已经有 DB 表，应作为查询主源 |
| 策略版本 | DB | 3 年回测版本回放 | 需要按日期、版本和 trader 复现 |
| 回测结果摘要 | DB | 3 年回测结果索引 | 需要按区间、版本、标的快速筛选 |
| regime-aware rule selection 摘要 | DB | 规则选择结果索引 | 是高频查询和审计对象 |

### 10.2 长期应以文件为 canonical 的数据

| 数据域 | 最终去向 | 3 年回测角色 | 原因 |
| --- | --- | --- | --- |
| 候选池快照 | 文件 | 3 年回测直接输入 | 当前 loader 直接读取 `data/market_universe/snapshots/**`，且没有 DB 表 |
| Config snapshot | 文件 | 回测环境回放 | 这是配置冻结件，适合作为归档和审计证据 |
| Profile snapshot | 文件 | Job 复现 | 冻结运行 profile，便于重放和审计 |
| 配置模板与 provider schema | 文件 | 定义层，不参与回测查询 | 属于静态定义，不是运行事实 |
| 回测完整报告 | 文件 | 下载与审阅 | Markdown / CSV 更适合人工查看 |
| Job 日志 | 文件 | 故障排查 | 日志天然适合文件化 |
| Trading calendar | 文件 | 运行时 fallback | 小体积、低频更新，保留文件最轻量 |
| 归档型 signal 文件 | 文件（归档） | 历史回放 | 只作为归档，不作为主查询层；查询应走 `signals` 表 |
| 证据包导出件 | 文件（导出） | 下载与复核 | 文件用于交付，不作为事实源 |
| Dashboard / pipeline / phase0 / kaipan 中间产物 | 文件 | 运行产物与调试材料 | 这些属于过程件，不应再复制到 DB 形成第二份事实 |

### 10.3 只允许短期保留、后续应裁剪的文件

这些文件不是最终 canonical，只能作为过渡期 artifact：

| 数据域 | 处理建议 | 原因 |
| --- | --- | --- |
| `data/kaipan/snapshots/**` | 迁移后尽量裁剪 | 这是 raw 的标准化中间态，和 DB 事实重复度高 |
| `data/processed/market_snapshot/**/snapshot.json` | 只保留过渡期 artifact | 结构化事实已在 DB，不应长期双份保存 |
| `snapshot.summary.json` / `snapshot.quality.json` | 只保留过渡期 artifact | 这两类信息应优先从 DB 摘要生成 |
| `data/processed/strategy_regime_selection/**` | 只保留过渡期 artifact | 如果未来建立 DB 摘要表，这里只留导出件，不再作为第二套查询源 |
| `result.json` / `records.csv` 的重复副本 | 尽量避免新增 | 回测结果应以 DB 摘要为主，文件只保留一份可下载版本 |

### 10.4 最终落地口径

- **同一份结构化事实，只保留一个长期 canonical。**
- **3 年回测的主读取层必须是数据库。**
- **文件只承担原始证据、导出件、日志和短期 artifact。**
- **凡是可以从 DB 重建的摘要，不要再长期维护第二份文件副本。**
- **如果必须保留文件，文件引用必须是 `storage_ref` / `artifact_ref`，不能再作为业务查询入口。**

---

## 11. 迁移 TaskList

- [x] **DS-MIG-001 统一 3 年回测主事实源到数据库**：把 `market_snapshots`、`market_snapshot_sections`、`market_snapshot_items`、`market_datasets`、`market_data_quality_reports`、`hot_topics_snapshots`、`topic_constituents_snapshots`、`strong_symbols_snapshots`、`market_regimes`、`market_regime_features`、`signals`、`trader_strategy_versions`、`rule_applicability_profiles`、`evidence_packs` 的查询与服务链路收口为 DB 主读源，保证 3 年回测不再依赖文件目录扫描读取业务事实。
- [x] **DS-MIG-002 固化文件 canonical 与 artifact 边界**：按本文件第 4.4 节与第 10.2 / 10.3 节收口文件 canonical 与 artifact 边界，保留 `data/market_universe/snapshots/**`、`data/config_snapshots/**`、`data/profile_snapshots/**`、`data/patterns/canonical/**`、`data/backtest/trading_calendar.json` 作为文件 canonical；保留 `data/backups/**`、`data/logs/**`、`data/params/**`、`data/processed/alignment/**`、`data/processed/alignment_cache/**`、`data/processed/crawl/**`、`data/processed/market_snapshot/**`、`data/processed/market_regime_features/**`、`data/processed/market_regimes/**`、`data/processed/market_data/**`、`data/processed/persona/**`、`data/processed/strategy_regime_selection/**`、`data/processed/rule_applicability/**`、`data/processed/dashboard/dashboard.html`、`data/processed/pipeline/**`、`data/processed/duckdb/**`、`data/processed/phase0/**`、`data/processed/kaipan/**`、`data/kaipan/raw/**`、`data/kaipan/snapshots/**`、`data/jobs/**`、`data/signals/**`、`evidence_packs/*.json` 作为文件/Artifact，统一通过 `storage_ref` / `artifact_ref` 暴露，不再把服务器绝对路径当业务事实。
- [x] **DS-MIG-003 补齐 3 年回测摘要与索引层**：`backtest_result_runs`、`strategy_regime_selections`、`regime_rule_selections` 已落地为 3 年回测摘要与索引层，补齐 `trader_id`、`strategy_version_id`、`date_from`、`date_to`、`regime_version`、`source_feature_version`、`benchmark_symbol` 等查询索引，确保 3 年回测结果可快速筛选、复现和审计。
- [x] **DS-MIG-004 校验 3 年回测端到端链路**：验证回测主链路、Rule Pool、UI、Job 详情和导出能力都已遵循本文件的存储边界，确认没有新的文件主查询分支、没有重复长期副本、没有未收口的临时方案，并同步相关文档与 TaskList。

> 进展记录：
> - `DS-MIG-001` 已完成，3 年回测主事实源已收口到 DB，文件侧业务查询入口已移除。
> - `DS-MIG-002` 已完成，文件 canonical 与 artifact 边界已按第 4.4 节和第 10.2 / 10.3 节完整收口。
> - `/api/ui/v1/signals`、`SignalService.list_signals` 与 CLI 入口已收口为 DB-only，`signals` 表是唯一查询源。
> - `ManagerAgent` 生成的信号已写入 `signals` 表，`EvaluationContextService` 也已从 DB 读取 signal context，不再依赖 `data/signals/**` 作为业务路径。
> - `/backtest_results` 已收口为 DB-only，列表与详情均读取 `jobs` 表，报告下载只读取 `job_dir` 中的 artifact，不再扫描旧回测目录。
> - `RuleApplicabilityService` 已收口为 DB-only，`jobs.result` 是唯一回测输入，不再回退文件目录。
> - `TraderOptionService` 的 `backtest` 来源已改为读取 `jobs` 表中的回测结果，不再扫描回测文件。
> - `backtest_results` 与 `trader_option_service` 的 jobs 读取已补分页，避免 1000 条上限截断 3 年回测数据。
> - `backtest_result_runs` 已作为回测摘要 canonical 落库，`strategy_regime_selections` / `regime_rule_selections` 已作为 regime-aware rule selection 摘要层落库，文件仅保留 artifact。
> - `DS-MIG-004` 已完成，端到端链路验证通过；旧兼容模块 `src/strategy/signal_version.py` 保留为历史归档读取，不再视为新的业务主查询入口。

## 12. 交付前应删除的残留文件与临时数据

这一节只列“交付前应清掉”的残留项，目标是保证交付物干净、没有测试污染、没有临时生成物混入。**不要删除本文件前文明确为 canonical 的内容。**

### 12.1 应优先删除的明确残留

| 文件 / 目录 | 建议 | 原因 |
| --- | --- | --- |
| `data/signals/.DS_Store` | 删除 | 操作系统元数据，不属于业务数据，也不应出现在交付结果中 |
| `data/config_snapshots/113f241d2be08f2124c8dafa131c9d305d1c10dbbd833f12f9195c1a43c18772.json` | 交付前确认后删除 | 当前仓库中仍是未跟踪文件，若不是正式交付所需快照，应清理掉以避免测试/临时生成物混入 |
| `data/config_snapshots/3014d8296caf0bc4584f1f38c9ff449c87fa5fd7e83abbfb9d8325addf2a5843.json` | 交付前确认后删除 | 同上 |
| `data/config_snapshots/488b622ed6df9fdebc8b02059d54a32f19eb79b185d0cc59566b69e6a3a42c17.json` | 交付前确认后删除 | 同上 |
| `data/config_snapshots/dc7685b9ed4503d70d0c2de9de2d0bc399ebacd40a7481e4342aa34751e2d1a7.json` | 交付前确认后删除 | 同上 |

### 12.2 应清理的临时运行产物

| 文件 / 目录 | 建议 | 原因 |
| --- | --- | --- |
| `data/jobs/*/job.log` 中的测试跑批残留 | 按需清理 | 交付前若这些目录只是本地验证产物，应删除或移出交付范围，避免把测试痕迹带给用户 |
| 新生成但未纳入 canonical 的 `data/jobs/*` 目录 | 按需清理 | 仅保留与正式交付相关的 Job 产物，避免临时 Job 目录污染 |
| `data/processed/**` 下的临时调试输出 | 按需清理 | 若仅用于本地测试或排障，不应作为交付数据保留 |
| `data/kaipan/raw/**` 中的临时抓取缓存 | 按需清理 | 仅保留交付需要的证据链，过期或重复抓取应清理 |
| `data/kaipan/snapshots/**` 中的临时归一化中间态 | 按需清理 | 若已确认 DB 为主事实源，这些中间态只保留必要样本，其余应裁剪 |

### 12.3 交付前检查建议

- 只保留 canonical 文件和必要 artifact，不保留测试夹带的临时目录。
- 确认 `data/config_snapshots/` 中每个文件都有明确用途，不要把测试生成的快照当成正式交付数据。
- 清理 `data/signals/.DS_Store`、编辑器缓存、`__pycache__`、`.pytest_cache` 等非业务文件。
- 如果某个 `data/jobs/{job_id}` 仅用于验证迁移流程，交付前应删除或移出交付包。
- 交付前再跑一次 `git status --short`，确保没有未知的未跟踪数据文件混入交付范围。

### 12.4 数据库中的表与数据

如果交付目标是“只保留工程代码”，数据库也必须按同一原则处理。

| 项目 | 处理方式 | 说明 |
| --- | --- | --- |
| 数据库表结构 | 保留 | ORM 模型、migration、建表脚本属于工程代码的一部分 |
| 数据库表数据 | 删除 | 交付时不应包含任何业务数据、测试数据或历史运行结果 |
| 本地数据库文件 | 删除 | `*.db`、`*.sqlite`、`*.sqlite3`、dump 文件、备份文件都不应随代码交付 |
| 启动后重建数据库的能力 | 保留 | 用户拿到交付物后，应通过 migration / init 脚本创建空库，再从抓取开始生成数据 |

结论：**交付时保留的是“能重建数据库的代码”，不是“已经填满数据的数据库”。**

## 13. 代码-only 交付模式下的彻底删除清单

如果这次交付的目标是“**只保留工程代码，不保留任何数据残留**”，则上一节的 canonical/artifact 区分不再作为交付保留依据。此模式下，**`data/` 下的所有内容都应删除**，只保留源码、必要测试代码和构建配置。

### 13.1 必须删除的目录

| 目录 | 删除原因 |
| --- | --- |
| `data/` | 交付目标要求不保留任何数据残留，整个数据目录都应清空 |
| `.pytest_cache/` | 测试缓存，不属于工程代码 |
| `__pycache__/`（所有递归层级） | Python 字节码缓存，不属于工程代码 |
| `.mypy_cache/` | 静态检查缓存，不属于工程代码 |
| `.ruff_cache/` | 代码检查缓存，不属于工程代码 |

### 13.2 必须删除的文件

| 文件 | 删除原因 |
| --- | --- |
| `.DS_Store`（全仓库范围） | macOS 元数据文件，不属于交付内容 |
| `data/backtest/trading_calendar.json` | 属于数据，不属于代码-only 交付 |
| `data/config_snapshots/*.json` | 数据快照，不应随代码交付 |
| `data/profile_snapshots/*.json` | 运行快照，不应随代码交付 |
| `data/market_universe/snapshots/**` | 回测输入数据，不应随代码交付 |
| `data/patterns/canonical/**` | 模式/规则数据，不应随代码交付 |
| `data/kaipan/raw/**` | 原始抓取缓存，不应随代码交付 |
| `data/kaipan/snapshots/**` | 归一化中间态，不应随代码交付 |
| `data/processed/**` | 所有处理产物都属于数据，不应随代码交付 |
| `data/jobs/**` | Job 运行产物，不应随代码交付 |
| `data/logs/**` | 运行日志，不应随代码交付 |
| `data/signals/**` | 信号归档，不应随代码交付 |
| `data/backups/**` | 备份数据，不应随代码交付 |
| `data/params/**` | 参数快照，不应随代码交付 |
| `evidence_packs/*.json`（若存在） | 证据包属于数据，不应随代码交付 |

### 13.3 交付前的判断标准

- 交付包里只应剩下源码、测试代码、构建配置、部署配置和必要说明文档。
- 任何能被当作“输入数据”“运行结果”“审计结果”“回放材料”的内容，都不应留在交付包里。
- 如果某个文件的作用是“以后启动后再抓取/再生成”，它就不是代码，应删除。
- 如果某个目录名里带有 `data`、`snapshot`、`processed`、`job`、`log`、`raw`、`artifact`，默认都应先判定为待清理对象，再决定是否属于代码。
