# trade-strategy-ai Web 用户手册（Admin）

> 适用范围：以 **admin** 身份使用 Web 管理后台的交付用户。  
> 目标：说明系统能做什么、各页面如何使用、从零完成盘前/盘后日常流程与回测流程，以及各参数含义与预期结果。

---

## 1. 系统简介

**trade-strategy-ai** 是一套面向「多交易员文章 + 交易记录」的多 Agent 交易研究与复盘系统。Web 工作台是正式产品入口，用于：

- 抓取与处理交易员文章
- 准备市场数据与候选池快照
- 查看 Persona 样例聚类与行为规则
- 构建策略版本、执行盘前准备与盘后复盘
- 离线回测与规则验真
- 审核规则池、管理配置 Profile
- 查看任务进度、产物、告警与系统健康

**核心工作方式**：在页面上提交 **Job（任务）** → Worker 后台执行 → 在 **任务中心** 查看状态 → 在 **产物中心** 下载/预览结果。

---

## 2. 登录与权限

### 2.1 登录

1. 浏览器访问 Web 地址：
   - Docker Compose：通常为 `http://<host>:3000`
   - 本机 API 托管前端：通常为 `http://localhost:8000`
   - 反向代理部署：通常为 `https://<your-domain>`
2. 进入 **登录页**，按部署方提供的认证方式登录。
3. 当前交付口径按 **API Key 鉴权** 描述：管理员 API Key 由运维创建或发放。
4. 如果部署环境启用了 username/password 登录，请以部署方提供的登录页提示为准；登录成功后侧边栏显示全部可用入口。

> 注意：`seed-admin --username --password` 用于创建管理员身份；API Key 的生成/发放方式以当前部署实现为准。交付时运维必须明确告诉用户“登录页填写 API Key”还是“填写用户名和密码”。

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
| 正式入口 | 告警中心 | `/alerts` | 告警历史、确认/解决、测试告警 |
| 正式入口 | 任务 | `/jobs` | 长时间运行任务列表与详情 |
| 业务工作台 | 文章 | `/articles` | 文章抓取与处理 |
| 业务工作台 | 市场数据 | `/market` | OHLCV、快照、Kaipan 等市场数据 |
| 业务工作台 | Persona | `/persona` | 交易风格画像、样例聚类、行为规则只读预览 |
| 业务工作台 | 策略 | `/strategies` | 策略版本、盘前、盘后 |
| 业务工作台 | 回测 | `/backtest` | 离线回测与规则验真 |
| 业务工作台 | 规则池 | `/rule-pool` | 规则审核与适用性画像 |
| 业务工作台 | 产物 | `/artifacts` | 日志、报告、JSON 等输出 |
| 配置与管理 | 配置管理 | `/profiles` | Profile 配置 CRUD 与快照 |
| 配置与管理 | 系统管理 | `/system` | 健康检查、用户、备份、审计（仅 admin） |

---

## 3. 首次使用：最小成功路径

在执行业务流程前，先完成一次最小成功验证：

```text
登录 Web → 检查 /dashboard → 导入 Profile → 提交一个测试 Job → 在 /jobs 看到 running/succeeded → 在 /artifacts 看到产物
```

| 检查项 | 如何确认 |
|--------|----------|
| API 与 Worker 已启动 | `/dashboard` 系统健康为正常；或访问 `/system/health` |
| 数据库已迁移 | `/system/db-migrate` 无待执行迁移（或部署时已执行） |
| 管理员账号/API Key 可用 | 能正常登录 Web |
| Profile 已导入 | `/profiles` 中存在 `validated` 状态的 Profile |
| Worker 在运行 | 提交 Job 后状态会从 `pending` 变为 `running` |

---

## 4. 配置管理（Profile）

Profile 是策略、盘前、盘后、回测、文章等业务的 **统一运行上下文**。Web 日常操作优先使用 `profile_id`，不要求用户直接填写配置文件路径。

### 4.1 导入 Profile

1. 进入 **配置管理** → **导入**（`/profiles/import`）。
2. 选择或填写初始配置来源，例如部署内置的 `config/app.yaml`。
3. 提交后系统生成 Profile 及配置快照。
4. 在 Profile 列表确认 `validation_status` 为 **validated**。

> 说明：Web 用户只需要选择 Profile；页面会自动绑定当前 Profile，不要求手动填写 `config_path`。`config_path` 仅保留给 CLI / 历史兼容。

### 4.2 Profile 详情与编辑

- **详情页**（`/profiles/:profileId`）：查看 sections、关联 Job、历史快照。
- **编辑页**（`/profiles/:profileId/edit`）：修改配置段；admin 可归档 Profile。
- **快照页**：每次导入/保存会生成快照，供策略构建时引用。

---

## 5. 页面功能说明

### 5.1 仪表盘（`/dashboard`）

**作用**：运维总览，不执行业务 Job。

- 系统健康、数据库状态、失败/成功任务数
- 产物数量、告警摘要
- 最近任务与最近产物（可跳转详情）
- 快速入口：告警中心、任务中心、配置管理、市场数据、Persona、策略工作台、系统审计、产物中心

### 5.2 告警中心（`/alerts`）

**作用**：集中查看告警状态、历史记录，并对已触发的告警做确认/解决/测试。

| 功能 | 说明 |
|------|------|
| 状态摘要 | 显示 `alerting.enabled`、当前通道、Webhook 是否配置 |
| 告警历史 | 查看最近告警，支持按状态、级别、标签筛选 |
| 告警处理 | 对告警执行确认、解决 |
| 配置验证 | 发送测试告警，验证 Webhook 是否可用 |

### 5.3 任务中心（`/jobs`）

**作用**：所有长时间运行任务的统一入口。

| 功能 | 说明 |
|------|------|
| 列表筛选 | 按 `status`、`job_type`、`created_by` 过滤 |
| 自动刷新 | 运行中任务约每 5 秒刷新 |
| 任务详情 | 参数、结果 payload、日志、关联产物 |
| 任务控制 | 支持 `pause / resume / cancel / retry`，仅对对应 Job 能力开放 |

排错路径：任何页面提交 Job 后 → 进入 `/jobs/:jobId` → 查看日志与错误 → 跳转关联产物。

### 5.4 产物中心（`/artifacts`）

**作用**：查看、预览、下载 Job 产生的文件。

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

### 5.5 文章工作台（`/articles`）

**作用**：从交易员站点抓取文章 → 清洗 → 结构化入库。

| 子页面 | 路径 | 作用 |
|--------|------|------|
| 工作台首页 | `/articles` | 子入口导航 |
| 抓取与处理 | `/articles/run` | 选择 step，生成对应 Job |
| 文章列表 | `/articles/list` | 按作者/来源/交易员/日期浏览 |
| 数据质量 | `/articles/quality` | 摘要、标签、去重、新鲜度 |
| 最近任务 | `/articles/jobs` | 文章相关 Job |
| 处理结果 | `/articles/results` | 最近结构化输出 |
| 高级维护 | `/articles/maintenance` | 重跑、失败重试、清理 |

> 版本口径：`/articles/results` 可查看同一篇文章的多个 `article_metadata` 候选版本，并设置当前生效版本；后续策略生成和回测只使用当前生效版本。`/articles/maintenance` 的 `new_version` 表示候选 metadata 版本，不是回测版本号。

常用 step：`crawl`、`clean`、`validate`、`store`、`process`。日常操作先选择 Profile，再选择 step，然后按页面表单提交。

> 说明：`use_db` 和 `config_path` 属于系统内部兼容参数，Web 日常操作不需要填写，页面会自动处理。

**`article_metadata` 版本怎么操作**：

1. 打开 **处理结果**（`/articles/results`）。
2. 找到目标文章，查看当前版本、推荐版本和评分原因。
3. 如果自动推荐不合适，切换为更适合该文章的候选版本并保存。
4. 保存后，后续 **策略版本** 和 **回测** 只会读取当前生效版本。
5. 如需重新生成候选版本，去 **高级维护**（`/articles/maintenance`）执行 `process`，`new_version` 只是候选 metadata 版本号。

### 5.6 市场数据（`/market`）

**作用**：准备盘前/策略构建所需的市场数据。

| 子页面 | 路径 | 作用 |
|--------|------|------|
| 总览 | `/market` | 快照/数据集统计、失败 Job、快捷入口 |
| 市场快照 | `/market/snapshots` | 快照列表、质量、派生特征 |
| 市场数据集 | `/market/datasets` | 数据集分页浏览 |
| Kaipan 数据 | `/market/kaipan` | Kaipan 抓取/归一化/调度（admin） |
| OHLCV 行情 | `/market/ohlcv` | 日线 OHLCV 抓取 |

#### OHLCV 行情

1. 选择 Profile。
2. 选择抓取模式：`incremental` 用于日常增量，`full` 用于历史回补。
3. 填写 `symbols`、日期区间等。
4. 提交 `ohlcv-crawl`，到任务中心查看进度。

Web 页面优先使用 `profile_id`，默认自动绑定当前 Profile。`config_path` 仅保留给 CLI / debug / 历史兼容，不建议交付用户手动填写。

#### Kaipan 数据

| Job | 作用 | 说明 |
|-----|------|------|
| `kaipan-fetch` | 抓取 Kaipan 原始数据 | 从数据源获取原始记录 |
| `kaipan-normalize` | 归一化为统一格式 | 将原始数据转成系统可用结构 |
| `kaipan-run` | 一键运行或启动/停止调度 | 用于调度控制，不等同于历史全量重跑 |

#### 快照构建（`snapshot-build`）

快照是盘前、策略版本、回测的重要输入。常用参数：Profile、日期或日期区间、基准指数、slot、snapshot_type、force、offline。

#### 自动更新与调度边界

- OHLCV 支持手动增量抓取；如部署启用了每日自动更新，由系统调度在盘后执行。
- Kaipan 支持手动抓取、归一化、一键运行/调度。
- 调度时间建议统一在系统管理/调度监控或部署配置中维护；市场数据页面主要作为业务操作入口。
- 盘前/盘后任务是否自动补齐缺失市场数据，以当前部署实现为准；交付时应由运维明确说明。如果未启用自动补齐，请先手动执行 `ohlcv-crawl` 与 `snapshot-build`。

### 5.7 Persona 工作台（`/persona`）

**作用**：查看 Persona 相关的两类能力。

| 标签 | 作用 | 说明 |
|------|------|------|
| 样例聚类 | 生成样例聚类文件 | 用于验证风格路由和 MarketState 的输入链路 |
| 行为规则（只读） | 查看单笔交易行为标签规则 | 用于解释一笔交易为什么命中某个标签，不支持在线编辑 |

**使用说明**：

1. 打开 `/persona`。
2. 默认进入 **样例聚类** 标签，可点击生成样例聚类文件。
3. 切换到 **行为规则（只读）** 标签，查看规则分类、优先级、条件和信号。
4. 规则页只用于解释和排查，不承担编辑或保存职责。

**预期结果**：

- 能快速理解 `sample clusters` 和 `behavior_rules.yaml` 的区别
- 能看到每条规则的分类、条件、信号和优先级
- 能确认该页面只是只读预览，不会修改正式配置

#### Legacy / Compatibility：`market-state-build`

`market-state-build` 属于旧 Persona/MarketState 兼容任务，不是当前 Web 日常主流程的必选步骤。普通交付用户不需要手动执行；如历史数据迁移、兼容验证或开发排障需要，可由运维/开发按 CLI 或高级入口执行。

---

## 6. 从零开始：盘前 + 盘后完整流程

```text
1. 登录并确认系统健康
2. 导入并选择 validated Profile
3. 准备文章数据：crawl / clean / validate / store / process
4. 准备 OHLCV 行情
5. 构建 snapshot-build 快照
6. 如 Profile、规则、快照或 Regime 有变化，执行 strategy-build
7. 审核并 Release 策略版本
8. 开盘前执行 run-pre-market
9. 收盘后执行 run-after-close
10. 在 jobs / artifacts 查看结果和报告
```

### 策略版本状态

`strategy-build` 完成后通常先生成 **draft 草稿版本**，它不是盘前/回测自动消费的正式版本。

| 状态 | 含义 | 是否可直接用于盘前/回测 |
|------|------|------------------------|
| `draft` | 已构建完成，等待人工审核 | 否 |
| `released` | 已人工确认并发布 | 是 |

请先在策略版本页面检查 draft 的推荐、规则快照和证据链，确认无误后执行 Release。没有可用 `released` 版本时，盘前和回测主流程可能报错。

**策略版本页面的操作顺序**：

1. 打开 `/strategies/versions`，选择 trader、策略日期和 Profile。
2. 生成或筛选出目标策略版本后，查看版本详情。
3. 在版本详情里检查 **来源文章 metadata 版本**，确认每篇来源文章的当前版本、推荐版本和评分原因。
4. 如果某篇文章的来源版本不合适，先回到 `/articles/results` 切换该文章的当前生效版本，再重新生成策略版本。
5. 确认 draft 无误后再执行 Release。

### 日常重复流程

第二个交易日及以后，通常只需：

```text
1. （按需或自动）ohlcv-crawl 增量更新
2. snapshot-build 当日快照
3. （仅 Regime/Profile/规则/快照变化时）strategy-build + Release
4. run-pre-market
5. run-after-close
```

---

## 7. 从零开始：回测完整流程

### 前置条件

| 条件 | 说明 |
|------|------|
| Profile 已导入 | 含 trader、strategy、market 等配置 |
| 策略版本已发布 | 在 `/strategies/versions` 中存在 `released` 版本 |
| 快照数据可用 | 回测固定使用快照数据（`use_snapshot_only=true`） |
| OHLCV 已抓取 | 覆盖回测日期区间 |

### 操作步骤

1. 打开 **回测**（`/backtest`）。
2. 选择 Profile、`trader_id`、`date_from`、`date_to` 和 `strategy_version_id`。
3. 如需限定标的，填写 `symbols`；如需指定基准，填写 `benchmark_symbol`。
4. 保持 `use_snapshot_only=true`。
5. 提交 `backtest-run`。
6. 查看摘要指标、Markdown 报告、CSV 明细。
7. 可选执行 `backtest-validate-rules` 或 `backtest-reproducibility-check`。
8. 提交前先检查页面里的 **策略版本来源** 卡片，确认该策略版本引用的来源文章 metadata 版本和评分原因符合预期。

Web 中由系统自动绑定当前 Profile，不向用户暴露 `config_path`。

---

## 8. 统一排错指南

```text
1. /dashboard 或 /system/health — 系统是否正常
2. /alerts — 是否有告警
3. /jobs — 找到失败 Job，查看日志
4. /artifacts — 查看是否有部分产物
5. /profiles — 确认 Profile 与快照有效
6. /system/audit — 查看权限拒绝或高风险操作记录
```

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| Job 一直 pending | Worker 未启动 | 启动 Worker，见运维手册 |
| 权限拒绝 | 角色不足 | 确认使用 admin/operator 账号 |
| 回测 skipped 多 | 快照/OHLCV 缺数据 | 补抓数据后重跑 |
| 盘前/盘后失败 | Profile、快照或 released 策略版本无效 | 检查 Profile validation、snapshot-build、策略版本 Release |
| 页面空白/401 | API Key 或登录状态失效 | 重新登录 |

---

## 9. Job 类型速查表

| job_type | 页面入口 | 用途 |
|----------|----------|------|
| `pipeline-run` / article step jobs | 文章 | 文章处理链路 |
| `ohlcv-crawl` | 市场数据 | OHLCV 抓取 |
| `snapshot-build` | 市场数据 / 盘前 | 候选池快照 |
| `strategy-build` | 策略版本 | 构建策略草稿版本 |
| `run-pre-market` | 盘前 | 盘前日报 |
| `run-after-close` | 盘后 | 盘后考核 |
| `backtest-run` | 回测 | 离线回测 |
| `backtest-validate-rules` | 回测 | 规则验真 |
| `backtest-reproducibility-check` | 回测 | 可复现性（admin） |
| `rule-pool-backtest` | 规则池 | 单规则回测（admin） |
| `backup-data` | 系统管理 | 项目备份 |
| `restore-data` | 系统管理 | 项目恢复 |
| `db-migrate` | 系统管理 | 数据库迁移 |
| `kaipan-fetch` / `kaipan-normalize` / `kaipan-run` | 市场数据 | Kaipan 数据处理与调度 |
| `market-state-build` | Legacy/Compatibility | 旧 MarketState 兼容任务，非日常主流程 |

---

*文档版本：修订交付版。重点收敛 Profile、明确策略 Release、调度边界与 legacy market-state-build。*
