# trade-strategy-ai Web 用户手册（Admin）

> 适用范围：以 **admin** 身份使用 Web 管理后台的交付用户。
>
> 目标：说明系统能做什么、各页面如何使用、从零完成盘前/盘后日常流程与回测流程，以及各参数含义与预期结果。

---

## 1. 系统简介

**trade-strategy-ai** 是一套面向「多交易员文章 + 交易记录」的多 Agent 交易研究与复盘系统。Web 工作台是正式产品入口，用于：

- 抓取与处理交易员文章
- 准备市场数据与候选池快照
- 构建策略版本、执行盘前准备与盘后复盘
- 离线回测与规则验真
- 审核规则池、管理配置 Profile
- 查看任务进度、产物与系统健康

**核心工作方式**：在页面上提交 **Job（任务）** → Worker 后台执行 → 在 **任务中心** 查看状态 → 在 **产物中心** 下载/预览结果。

---

## 2. 登录与权限

### 2.1 登录

1. 浏览器访问 Web 地址（部署后通常为 `http://<host>:3000` 或本机 `http://localhost:8000`）。
2. 进入 **登录页**，输入管理员 **API Key**（由运维在首次部署时创建）。
3. 登录成功后，侧边栏显示全部可用入口。

### 2.2 角色说明

| 角色 | 能力 |
|------|------|
| **viewer** | 查看仪表盘、任务、产物、回测结果等 |
| **operator** | 在 viewer 基础上，可提交大部分业务 Job（盘前、盘后、回测、快照等） |
| **admin** | 全部权限，含系统管理、备份恢复、Kaipan、用户管理等 |

本手册按 **admin** 编写；admin 可执行所有页面上的操作。

### 2.3 侧边栏导航

| 分组 | 页面 | 路径 | 作用 |
|------|------|------|------|
| 正式入口 | 仪表盘 | `/dashboard` | 系统健康、告警、最近任务/产物摘要 |
| 正式入口 | 任务 | `/jobs` | 长时间运行任务列表与详情 |
| 业务工作台 | 文章 | `/articles` | 文章抓取与处理 |
| 业务工作台 | 市场数据 | `/market` | OHLCV、快照、Kaipan 等市场数据 |
| 业务工作台 | 策略 | `/strategies` | 策略版本、盘前、盘后 |
| 业务工作台 | 回测 | `/backtest` | 离线回测与规则验真 |
| 业务工作台 | 规则池 | `/rule-pool` | 规则审核与适用性画像 |
| 业务工作台 | 产物 | `/artifacts` | 日志、报告、JSON 等输出 |
| 配置与管理 | 配置管理 | `/profiles` | Profile 配置 CRUD 与快照 |
| 配置与管理 | 系统管理 | `/system` | 健康检查、用户、备份、审计（仅 admin） |

---

## 3. 首次使用：环境就绪检查

在执行业务流程前，确认以下项已完成（部署细节见 [`web-deployment-operation.md`](web-deployment-operation.md)）：

| 检查项 | 如何确认 |
|--------|----------|
| API 与 Worker 已启动 | `/dashboard` 系统健康为正常；或访问 `/system/health` |
| 数据库已迁移 | `/system/db-migrate` 无待执行迁移（或部署时已执行） |
| 管理员账号可用 | 能正常登录 Web |
| Profile 已导入 | `/profiles` 中存在 `validated` 状态的 Profile |
| Worker 在运行 | 提交 Job 后状态会从 `pending` 变为 `running` |

---

## 4. 配置管理（Profile）

Profile 是策略、盘前、盘后、回测、文章等业务的 **统一运行上下文**。优先使用 `profile_id`，而不是直接写配置文件路径。

### 4.1 导入 Profile

1. 进入 **配置管理** → **导入**（`/profiles/import`）。
2. 填写 `config_path`（通常为 `config/app.yaml`）及 Profile 名称。
3. 提交后系统生成 Profile 及配置快照。
4. 在 Profile 列表确认 `validation_status` 为 **validated**。

### 4.2 Profile 详情与编辑

- **详情页**（`/profiles/:profileId`）：查看 sections、关联 Job、历史快照。
- **编辑页**（`/profiles/:profileId/edit`）：修改配置段；admin 可归档 Profile。
- **快照页**：每次导入/保存会生成快照，供策略构建时引用。

### 4.3 策略相关 Profile Sections

策略构建依赖以下配置段（在 Profile 中维护）：

| Section | 含义 |
|---------|------|
| `top_symbols` | 重点关注的标的 |
| `style_cluster_ids` | 风格聚类 ID |
| `concept_tags` | 概念标签 |
| `strategy_preference` | 策略偏好 |
| `risk_style` | 风险风格 |
| `theme_preference` | 主题偏好 |
| `position_bias` | 仓位倾向 |

---

## 5. 页面功能说明

### 5.1 仪表盘（`/dashboard`）

**作用**：运维总览，不执行业务 Job。

- 系统健康、数据库状态、失败/成功任务数
- 产物数量、告警摘要
- 最近任务与最近产物（可跳转详情）
- 快速入口：任务中心、配置管理、市场数据、策略工作台、系统审计、产物中心

**建议使用场景**：每天开始工作前扫一眼，确认无大量失败任务或告警。

---

### 5.2 任务中心（`/jobs`）

**作用**：所有长时间运行任务的统一入口。

| 功能 | 说明 |
|------|------|
| 列表筛选 | 按 `status`、`job_type`、`created_by` 过滤 |
| 自动刷新 | 运行中任务约每 5 秒刷新 |
| 任务详情 | 参数、结果 payload、日志、关联产物 |
| 重试 | 部分 Job 支持失败后重试 |

**排错路径**：任何页面提交 Job 后 → 进入 `/jobs/:jobId` → 查看日志与错误 → 跳转关联产物。

---

### 5.3 产物中心（`/artifacts`）

**作用**：查看、预览、下载 Job 产生的文件。

常见产物类型：

| kind | 说明 |
|------|------|
| `result-json` | 结构化结果摘要（盘前/盘后/回测等） |
| `report-markdown` | Markdown 报告 |
| `html` | HTML 可视化报告 |
| `records-csv` | 回测交易明细 |
| `snapshot-json` | 市场快照 |
| `snapshot-summary-json` | 快照摘要 |
| `snapshot-quality-json` | 快照质量报告 |
| `validation-report-markdown` | 规则验真报告 |

---

### 5.4 文章工作台（`/articles`）

**作用**：从交易员站点抓取文章 → 清洗 → 结构化入库。

| 子页面 | 路径 | 作用 |
|--------|------|------|
| 工作台首页 | `/articles` | 六个子入口导航 |
| 抓取与处理 | `/articles/run` | 提交完整 `pipeline-run` |
| 文章列表 | `/articles/list` | 按作者/来源/交易员/日期浏览 |
| 数据质量 | `/articles/quality` | 摘要、标签、去重、新鲜度 |
| 最近任务 | `/articles/jobs` | 文章相关 Job |
| 处理结果 | `/articles/results` | 最近结构化输出 |
| 高级维护 | `/articles/maintenance` | 重跑、失败重试、清理 |

**`pipeline-run` 主要参数**：

| 参数 | 含义 |
|------|------|
| `config_path` | 配置文件路径（Profile 驱动时自动映射） |
| `max_articles` | 最多处理文章数（默认 10） |
| `force` | 强制执行，忽略缓存 |
| `skip_crawl` | 跳过抓取，仅处理已有数据 |
| `from_step` | 从指定步骤恢复 |
| `use_db` | 是否使用数据库 |
| `new_version` | 生成新版本 |
| `retry_failed` | 重试失败项 |

**预期结果**：`result-json` 摘要；可选 HTML 报告；文章可在列表页浏览。

---

### 5.5 市场数据（`/market`）

**作用**：准备盘前/策略构建所需的市场数据。

| 子页面 | 路径 | 作用 |
|--------|------|------|
| 总览 | `/market` | 快照/数据集统计、失败 Job、快捷入口 |
| 市场快照 | `/market/snapshots` | 快照列表、质量、派生特征 |
| 市场数据集 | `/market/datasets` | 数据集分页浏览 |
| Kaipan 数据 | `/market/kaipan` | Kaipan 抓取/归一化/调度（admin） |
| OHLCV 行情 | `/market/ohlcv` | 日线 OHLCV 抓取 |

**市场 Job 类型与参数**：

#### OHLCV 抓取（`ohlcv-crawl`）

| 参数 | 必填 | 含义 |
|------|------|------|
| `profile_id` | 二选一 | Profile ID（优先） |
| `config_path` | 二选一 | 配置文件路径 |
| `symbols` | 是 | 标的列表 |
| `mode` | 否 | `incremental`（增量，默认）/ 全量 |
| `start_date` / `end_date` | 否 | 抓取日期区间 |
| `limit` | 否 | 最多抓取标的数 |

#### 市场状态构建（`market-state-build`）

| 参数 | 必填 | 含义 |
|------|------|------|
| `config_path` | 是 | 配置文件路径 |
| `benchmark_symbol` | 是 | 基准指数代码（如 `000300.SH`） |
| `as_of` | 否 | 基准日期 |
| `from_akshare` | 否 | 是否从 AkShare 构建 |
| `cache_csv` | 否 | 是否缓存 CSV |

#### 快照构建（`snapshot-build`）

| 参数 | 必填 | 含义 |
|------|------|------|
| `profile_id` | 二选一 | Profile ID |
| `config_path` | 二选一 | 配置文件路径 |
| `date` | 二选一 | 单日快照日期 |
| `start_date` + `end_date` | 二选一 | 区间快照 |
| `benchmark_symbol` | 否 | 基准指数 |
| `slot` | 否 | 时间槽（默认 `17-30`） |
| `snapshot_type` | 否 | `all` / `hot_topics` 等 |
| `force` | 否 | 强制重建 |
| `offline` | 否 | 离线模式 |

#### Kaipan（admin）

| Job | 作用 |
|-----|------|
| `kaipan-fetch` | 抓取 Kaipan 原始数据 |
| `kaipan-normalize` | 归一化为统一格式 |
| `kaipan-run` | 一键运行或启动调度器 |

---

### 5.6 策略工作台（`/strategies`）

**作用**：策略版本构建、盘前准备、盘后复盘的全流程中心。

| 子页面 | 路径 | 作用 |
|--------|------|------|
| 工作台首页 | `/strategies` | 摘要、流程入口、最近 Job |
| 盘前准备 | `/strategies/pre-market` | 快照构建 + 盘前运行 |
| 盘后复盘 | `/strategies/after-close` | 盘后考核与归因 |
| 策略版本 | `/strategies/versions` | 构建与查看策略版本 |
| 候选版本 | `/strategies/candidates` | 候选版本生成与审核 |
| 规则选择 | `/strategies/regime-selection` | Regime-aware 规则选择视图 |
| 运行历史 | `/strategies/history` | 策略相关 Job 历史 |

**策略 Pipeline 逻辑顺序**：

```text
strategy-build → run-pre-market → run-after-close
```

日常使用时 **不必每天重建策略版本**；仅在 Profile、规则、快照或 Regime 发生变化时才需要重新 `strategy-build`。

---

### 5.7 回测工作台（`/backtest`）

**作用**：对历史数据进行离线回测，评估策略表现。

| 子页面 | 路径 | 作用 |
|--------|------|------|
| 回测中心 | `/backtest` | 提交回测、查看结果 |
| Regime 回测 | `/backtest/regime` | Regime-aware 回测报告 |

**回测 Pipeline**：

```text
backtest-run →（可选）backtest-validate-rules / backtest-reproducibility-check
```

---

### 5.8 规则池（`/rule-pool`）

**作用**：审核从文章/策略中提取的交易规则。

- **列表**：按 `status`（默认 pending）、`rule_type`、`mapping_status` 等筛选
- **详情**（`/rule-pool/:ruleId`）：
  - 查看规则内容与证据
  - 生成/审核适用性画像（Rule Applicability Profile）
  - 提交 **规则池回测**（`rule-pool-backtest`，admin，需二次确认）

**规则池回测参数**：

| 参数 | 含义 |
|------|------|
| `rule_id` | 规则 ID |
| `start_date` / `end_date` | 回测区间 |
| `min_confidence` | 最低置信度 |
| `market_regime_version` | 市场状态版本 |

---

### 5.9 系统管理（`/system`，admin only）

| 子页面 | 路径 | 作用 |
|--------|------|------|
| Hub | `/system` | 运维入口汇总 |
| 权限与审计 | `/system/audit` | 高风险操作、权限拒绝记录 |
| 用户管理 | `/system/users` | 增删用户、改角色、改密 |
| 系统健康 | `/system/health` | API、DB、Worker、存储状态 |
| 数据库迁移 | `/system/db-migrate` | 触发 `db-migrate`（高风险） |
| 数据备份与恢复 | `/system/backup` | 项目级备份/恢复 |

---

## 6. 从零开始：盘前 + 盘后完整流程

以下是从全新环境到获得当日盘前/盘后结果的 **推荐操作顺序**。

### 流程总览

```mermaid
flowchart TD
    A[首次部署与环境就绪] --> B[导入 Profile]
    B --> C[文章 pipeline-run]
    C --> D[OHLCV 抓取]
    D --> E[快照构建 snapshot-build]
    E --> F{规则/Regime 有变化?}
    F -->|是| G[策略构建 strategy-build]
    F -->|否| H[盘前 run-pre-market]
    G --> H
    H --> I[盘后 run-after-close]
    I --> J[查看产物与报告]
```

---

### Step 0：首次环境就绪

1. 完成部署（见运维手册）。
2. 执行数据库迁移、创建 admin 用户。
3. 确认 Worker 在运行。

---

### Step 1：导入 Profile

1. 打开 **配置管理** → **导入**。
2. 从 `config/app.yaml` 导入 Profile。
3. 确认 validation 状态为 `validated`。
4. 记录 `profile_id`（后续步骤会用到）。

---

### Step 2：准备文章数据（首次或需要更新时）

1. 打开 **文章** → **抓取与处理**（`/articles/run`）。
2. 选择 Profile，填写参数：
   - `max_articles`：根据需要设置（如 50）
   - 首次运行：`force=false`，`skip_crawl=false`
3. 提交 `pipeline-run` Job。
4. 在 **任务中心** 等待完成。
5. 在 **文章列表** 确认文章已入库；在 **数据质量** 检查摘要。

**预期结果**：文章结构化数据入库，供后续策略与规则提取使用。

---

### Step 3：准备市场数据

1. 打开 **市场数据** → **OHLCV 行情**（`/market/ohlcv`）。
2. 选择 Profile，填写：
   - `symbols`：关注标的列表（如 `600519.SH,000001.SZ`）
   - `mode`：`incremental`
   - 日期区间：按需设置
3. 提交 `ohlcv-crawl` Job，等待完成。

4. （可选）打开 **市场数据** 总览或盘前页，提交 **快照构建**：
   - `profile_id`：你的 Profile
   - `date`：策略日期（如今日）
   - `slot`：`17-30`（默认）
   - `snapshot_type`：`all`

**预期结果**：
- OHLCV 日线数据就绪
- `snapshot-json`、`snapshot-summary-json`、`snapshot-quality-json` 产物

5. 在 **市场快照** 页确认快照质量可接受。

---

### Step 4：构建策略版本（规则/Regime/快照变化时）

> 若已有对应日期的策略版本，可跳过此步。

1. 打开 **策略** → **规则选择**（`/strategies/regime-selection`），查看 Regime 规则选择结果。
2. 打开 **策略版本**（`/strategies/versions`）。
3. 填写参数并提交 **`strategy-build`**：

| 参数 | 必填 | 含义 |
|------|------|------|
| `profile_id` | 推荐 | Profile ID |
| `trader_id` | 是 | 交易员 ID（如 `trader_a`） |
| `strategy_date` | 是 | 策略日期 |
| `snapshot_id` | 否 | 快照 ID；留空则用 Profile 最新快照 |
| `market_regime_version` | 否 | 市场状态版本（默认 `market-regime-v3`） |
| `source_feature_version` | 否 | Regime 特征版本（默认 `market-regime-features-v3`） |
| `applicability_profile_version` | 否 | 规则适用性画像版本 |
| `selected_by` | 否 | 选择来源（默认 `web`） |
| `force` | 否 | 强制重建 |

4. 等待 Job 完成，记录生成的 **策略版本 ID**。

**预期结果**：
- `result-json`：策略版本摘要
- 可选 `regime-selection-json`、HTML 报告

---

### Step 5：盘前准备

1. 打开 **策略** → **盘前准备**（`/strategies/pre-market`）。
2. 选择 Profile、**Strategy date**（策略日期）、Benchmark（可留空，使用 Profile 默认）。
3. 若当日快照尚未构建，先提交 **快照构建**（参数见 Step 3）。
4. 提交 **`run-pre-market`**：

| 参数 | 含义 |
|------|------|
| `profile_id` | Profile ID |
| `as_of_date` | 执行日期（= 策略日期） |
| `benchmark_symbol` | 基准指数（可选，如 `000300.SH`） |
| `force` | 强制执行 |
| `export_html` | 是否导出 HTML 报告 |

5. 在任务详情等待完成。

**预期结果**：
- `result-json`：盘前日报摘要（关注列表、市场状态、策略要点等）
- 可选 HTML 报告
- 策略首页显示最新 `run-pre-market` Job 链接

**你能得到什么**：一份面向当日的盘前准备报告，明确今日关注标的、市场环境与策略执行要点。

---

### Step 6：盘后复盘

> 通常在当日收盘后执行。

1. 打开 **策略** → **盘后复盘**（`/strategies/after-close`）。
2. 选择 Profile、**执行日期**（`as_of_date`）。
3. 可选勾选 `force`、`export_html`。
4. 提交 **`run-after-close`** Job。
5. 等待完成，在页面查看结果摘要。

**预期结果**（`result-json` 含）：

| 字段 | 含义 |
|------|------|
| `evaluations` | 各标的收益与考核状态 |
| `evidence_pack_refs` | 证据包引用 |
| `failure_categories` | 失败分类 |
| `ranking_features` | 排名特征 |
| `postmortem_notes` | 复盘笔记 |

页面还会展示：信号归因、今日表现、最近盘后 Job 列表。

**你能得到什么**：当日交易表现的结构化考核结果、归因分析与复盘材料，可用于反馈与策略优化。

---

### 日常重复流程（环境已就绪）

第二个交易日及以后，通常只需：

```text
1. （按需）ohlcv-crawl 增量更新
2. snapshot-build（当日快照）
3. （仅 Regime/规则变化时）strategy-build
4. run-pre-market
5. run-after-close
```

---

## 7. 从零开始：回测完整流程

### 7.1 前置条件

| 条件 | 说明 |
|------|------|
| Profile 已导入 | 含 trader、strategy、market 等配置 |
| 策略版本已存在 | 在 `/strategies/versions` 构建或已有历史版本 |
| 快照数据可用 | 回测 **固定使用快照数据**（`use_snapshot_only=true`） |
| OHLCV 已抓取 | 覆盖回测日期区间 |

### 7.2 操作步骤

1. 打开 **回测**（`/backtest`）。
2. 填写回测表单（见参数表）。
3. 点击 **「运行回测」** 提交 `backtest-run` Job。
4. 自动跳转或手动进入 **任务详情**，等待完成。
5. 在 **最近结果** 列表选择 `result_id`，查看摘要指标。
6. 预览或下载 Markdown 报告、CSV 明细。
7. （可选）点击 **「验证规则」** 提交 `backtest-validate-rules`。
8. （可选，admin）**「可复现性检查」** 提交 `backtest-reproducibility-check`，比对 fingerprint。

### 7.3 回测参数详解

| 参数 | 必填 | 默认值 | 含义 |
|------|------|--------|------|
| `profile_id` | 推荐 | — | 运行上下文；驱动 config_path |
| `trader_id` | 是 | — | 交易员 ID |
| `date_from` | 是 | 近 30 天 | 回测开始日期 |
| `date_to` | 是 | 今日 | 回测结束日期 |
| `strategy_version_id` | 强烈建议 | — | 绑定的策略版本 |
| `symbols` | 否 | 全部 | 标的列表，逗号/空格分隔；空=全部 |
| `benchmark_symbol` | 否 | `000300.SH` | 基准指数（沪深300） |
| `mode` | 否 | `full` | 见下表 |
| `use_snapshot_only` | 固定 | `true` | 仅使用快照数据（UI 不可改） |
| `scoring_profile` | 否 | `stage5` | 评分配置口径 |
| `config_path` | 否 | 自动 | 通常由 Profile 自动填充 |

**`mode` 取值**：

| 值 | 含义 |
|----|------|
| `full` | 全量回测 |
| `replay` | 重放模式 |
| `rule_validation` | 规则验真（`backtest-validate-rules` 默认） |

### 7.4 回测结果解读

Job 完成后，在结果列表和详情页可看到：

| 指标 | 含义 |
|------|------|
| `total_days` | 回测覆盖交易日数 |
| `total_trades` | 总交易笔数 |
| `valid_trades` | 有效交易笔数 |
| `skipped_trades` | 跳过笔数（缺数据等） |
| `win_rate` | 胜率 |
| `avg_return_pct` | 平均收益率 |
| `fingerprint` | 结果指纹，用于可复现性比对 |

**产物**：

| kind | 用途 |
|------|------|
| `result-json` | 结构化摘要，含 fingerprint |
| `report-markdown` | 人类可读报告，可下载 |
| `records-csv` | 逐笔交易明细 |
| `validation-report-markdown` | 规则验真报告 |

**Regime 回测**：打开 `/backtest/regime` 查看按市场状态分段的回测报告。

**你能得到什么**：在指定日期区间内，某策略版本的历史表现评估，包括胜率、收益、交易明细，以及（可选）规则验真与可复现性验证。

---

## 8. 候选版本与策略优化

1. 打开 **策略** → **候选版本**（`/strategies/candidates`）。
2. 提交 **`optimize-create-candidate`** 生成候选版本。
3. 在列表中审核，提交 **`candidate-review`**（高风险，需二次确认）：
   - `candidate_version_id`：候选版本 ID
   - `decision`：审核决定
   - `reviewed_by`：审核人

---

## 9. 统一排错指南

无论哪个页面出问题，按以下顺序排查：

```text
1. /dashboard 或 /system/health — 系统是否正常
2. /jobs — 找到失败 Job，查看日志
3. /artifacts — 查看是否有部分产物
4. /profiles — 确认 Profile 与快照有效
5. /system/audit — 查看是否有权限拒绝或高风险操作记录
```

**常见问题**：

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| Job 一直 pending | Worker 未启动 | 启动 Worker，见运维手册 |
| 权限拒绝 | 角色不足 | 确认使用 admin 账号 |
| 回测 skipped 多 | 快照/OHLCV 缺数据 | 补抓数据后重跑 |
| 盘前/盘后失败 | Profile 或快照无效 | 检查 Profile validation 与 snapshot-build |
| 页面空白/401 | API Key 失效 | 重新登录 |

---

## 10. Admin 专属操作速查

| 操作 | 入口 | Job 类型 |
|------|------|----------|
| 用户管理 | `/system/users` | — |
| 数据库迁移 | `/system/db-migrate` | `db-migrate` |
| 项目备份 | `/system/backup` | `backup-data` |
| 项目恢复 | `/system/backup` | `restore-data` |
| Kaipan 抓取 | `/market/kaipan` | `kaipan-*` |
| 回测可复现性 | `/backtest` | `backtest-reproducibility-check` |
| 规则池回测 | `/rule-pool/:ruleId` | `rule-pool-backtest` |
| Profile 归档 | `/profiles/:id/edit` | — |

---

## 11. Job 类型速查表

| job_type | 页面入口 | 用途 |
|----------|----------|------|
| `pipeline-run` | 文章 | 文章完整处理链路 |
| `ohlcv-crawl` | 市场数据 | OHLCV 抓取 |
| `market-state-build` | 市场数据 | 市场状态 |
| `snapshot-build` | 市场数据 / 盘前 | 候选池快照 |
| `strategy-build` | 策略版本 | 构建策略版本 |
| `run-pre-market` | 盘前 | 盘前日报 |
| `run-after-close` | 盘后 | 盘后考核 |
| `backtest-run` | 回测 | 离线回测 |
| `backtest-validate-rules` | 回测 | 规则验真 |
| `backtest-reproducibility-check` | 回测 | 可复现性（admin） |
| `rule-pool-backtest` | 规则池 | 单规则回测（admin） |
| `backup-data` | 系统管理 | 项目备份 |
| `restore-data` | 系统管理 | 项目恢复 |
| `db-migrate` | 系统管理 | 数据库迁移 |

---

## 12. 附录：典型工作日时间线

| 时间 | 操作 | 页面 |
|------|------|------|
| 开盘前 | 检查仪表盘、增量 OHLCV、构建快照 | `/dashboard`, `/market/ohlcv` |
| 开盘前 | 盘前运行 | `/strategies/pre-market` |
| 盘中 | 查看盘前报告产物 | `/artifacts` |
| 收盘后 | 盘后运行 | `/strategies/after-close` |
| 收盘后 | 查看考核结果、归因 | `/strategies/after-close`, `/artifacts` |
| 周末/按需 | 回测、规则池审核 | `/backtest`, `/rule-pool` |

---

*文档版本：与当前 Web 正式入口（V2 IA）对齐。部署与运维见 [`web-deployment-operation.md`](web-deployment-operation.md)。*
