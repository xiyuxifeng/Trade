# Preview.md：交付前完整流程演示与验收方案

> 目标：在当前设备上清理开发临时数据，准备一套可控时间范围的数据，向用户完整展示 Web 系统从数据准备到策略、盘前、盘后、回测、产物查看和运维排错的闭环。
>
> 原则：演示环境必须可重复、可回滚、数据范围足够小、结果足够完整，不在用户面前暴露开发脏数据、临时 Job、旧产物和不稳定配置。

---

## 1. 演示目标

本次 Preview 要向用户证明以下能力已经可以交付：

1. 系统可以从干净环境启动。
2. Web 可以登录、查看 Dashboard、系统健康、告警、任务与产物。
3. Profile 可以作为统一运行上下文使用。
4. 文章数据可以抓取、清洗、校验、入库、生成结构化结果。
5. 市场数据可以准备，包括 OHLCV、快照、Kaipan 如需展示。
6. 策略版本可以构建，并经过人工 Release 后用于正式流程。
7. 盘前可以生成当日关注、市场环境、策略要点。
8. 盘后可以生成表现考核、归因和复盘材料。
9. 回测可以基于历史快照和 OHLCV 生成指标、报告和交易明细。
10. 任务中心、产物中心、备份恢复、审计与排错链路可用。

---

## 2. 数据时间范围应该怎么限制

### 2.1 推荐范围

建议演示数据范围限制为：

```text
最近 20 个交易日到最近 60 个交易日之间。
推荐默认：最近 30 个交易日。
```

如果按自然日填写，可以使用：

```text
最近 45 个自然日，覆盖约 30 个交易日。
```

### 2.2 为什么不建议抓太长

不建议演示时抓取半年或一年数据，原因是：

1. 抓取耗时不可控，现场演示容易等待过久。
2. 外部数据源可能限流或返回不稳定。
3. 数据越多，失败点越多，排错时间越长。
4. 演示目标是证明闭环，不是做长期历史研究。
5. 旧数据混入后，用户难以判断哪些结果是本次演示产生的。

### 2.3 为什么不建议抓太短

不建议只抓 1～3 天，原因是：

1. 回测指标没有意义。
2. 盘前/盘后缺少上下文。
3. 快照质量检查可能无法充分展示。
4. 规则适用性、Regime、策略效果无法展示趋势。

### 2.4 推荐演示日期选择

优先选择已经收盘、数据完整的历史区间，例如：

```text
end_date = 最近一个完整交易日
start_date = end_date 往前 45 个自然日
```

如果当天还未收盘，不要把今天作为盘后演示日期。建议使用上一个完整交易日作为演示日。

### 2.5 推荐数据规模

| 数据类型 | 推荐限制 | 说明 |
|---|---:|---|
| 文章 | 30～80 篇 | 足够展示抓取、清洗、规则提取，不至于过慢 |
| 股票标的 | 10～30 个 | 足够展示候选池、OHLCV、回测，不建议全市场 |
| OHLCV | 最近 30 个交易日 | 日常演示足够 |
| 快照 | 1 个演示日 + 可选 5～10 个历史日 | 盘前/盘后需要演示日；回测如依赖快照，可补历史快照 |
| 回测 | 20～30 个交易日 | 能展示胜率、收益、skipped、CSV 明细 |
| Kaipan | 1 个演示日或最近 5 个交易日 | 如果该模块不是核心演示，可作为附加展示 |

---

## 3. 清理当前设备旧数据与临时数据

### 3.1 清理前先备份

即使目标是清理，也必须先保留一份当前状态，避免误删后无法恢复。

#### Web 方式

1. 登录 Web。
2. 打开 **系统管理** → **数据备份与恢复**（`/system/backup`）。
3. 提交 `backup-data`。
4. 勾选 `include_processed`。
5. 等待 Job 完成。
6. 在产物中心或备份目录确认备份存在。

#### CLI 方式

如果 Web 还未启动，可以先复制关键目录：

```bash
cd trade-strategy-ai
mkdir -p data/backups/manual-preview-$(date +%Y%m%d-%H%M%S)
cp -R data data/backups/manual-preview-$(date +%Y%m%d-%H%M%S)/data-copy
cp -R config data/backups/manual-preview-$(date +%Y%m%d-%H%M%S)/config-copy
```

注意：如果数据量较大，建议只备份数据库导出、artifacts、processed、profiles 相关文件，不要重复嵌套复制整个 `data/backups`。

---

### 3.2 推荐清理策略

清理不建议直接删除整个项目目录。建议分层处理：

| 层级 | 是否清理 | 说明 |
|---|---:|---|
| 数据库 Job 记录 | 是 | 清掉开发期间 pending/running/failed/succeeded 旧任务 |
| Artifacts | 是 | 清掉旧报告、旧 JSON、旧 CSV，避免用户混淆 |
| Processed 中间数据 | 是 | 清掉旧文章处理结果、旧快照中间结果 |
| Market Cache | 视情况 | 如果想完全干净，清；如果外部数据源慢，可保留已验证缓存 |
| Profiles | 一般不删 | 推荐保留交付 Profile；如旧 Profile 混乱，可归档后重新导入 |
| Config | 不删 | `config/app.yaml` 是部署基础 |
| Backups | 不删 | 至少保留清理前备份 |
| 日志 | 可归档后清理 | 演示前保留新日志更利于排错 |

---

### 3.3 停止服务

清理前先停止 API 和 Worker，避免清理过程中有 Job 写入。

#### 本机模式

```bash
cd trade-strategy-ai
python -m scripts.web_local stop
```

#### Docker Compose

```bash
cd trade-strategy-ai
docker compose stop api worker web
```

如需清理数据库，可以暂时保留 `db` 运行。

---

### 3.4 清理产物与中间文件

建议执行前先确认当前路径是 `trade-strategy-ai` 项目根目录：

```bash
pwd
ls config web data
```

推荐清理命令：

```bash
cd trade-strategy-ai

# 归档旧日志
mkdir -p logs/archive-preview-$(date +%Y%m%d-%H%M%S)
find logs -maxdepth 1 -type f -name "*.log" -exec mv {} logs/archive-preview-$(date +%Y%m%d-%H%M%S)/ \;

# 清理旧产物和中间处理结果
rm -rf data/artifacts/*
rm -rf data/processed/*

# 可选：清理临时缓存。若外部数据源不稳定，可以先不清。
rm -rf data/tmp/* 2>/dev/null || true
rm -rf data/cache/* 2>/dev/null || true
```

不要删除：

```text
config/
data/backups/
web/dist/  # 除非准备重新 build
```

---

### 3.5 清理数据库旧 Job 与业务数据

数据库清理需要谨慎。推荐优先使用系统已有的备份/恢复或维护入口。如果必须手工清理，先确认表结构。

```bash
cd trade-strategy-ai
python -m cli.main db-check --config config/app.yaml
```

然后通过 Web 的系统管理或维护功能清理旧 Job、旧产物索引、旧审计测试数据。

如果当前系统没有提供“一键清理演示数据”的正式入口，建议不要直接在生产数据库执行 `TRUNCATE`。可以采用更安全的方式：

1. 创建新的 Preview 专用数据库，例如 `trade_strategy_ai_preview`。
2. 指向新的 `DATABASE_URL`。
3. 重新执行 `db-migrate`。
4. 重新创建管理员。
5. 重新导入 Profile。

这是最适合交付演示的方式。

#### 推荐：使用 Preview 专用数据库

```bash
createdb -O trade trade_strategy_ai_preview
export DATABASE_URL="postgresql+asyncpg://trade:<password>@localhost:5432/trade_strategy_ai_preview"
python -m cli.main db-migrate --config config/app.yaml
python -m cli.main seed-admin --username preview-admin --password <strong-password>
```

这样可以完全避免开发旧数据污染演示。

### 3.6 数据表清理清单

> 说明：
> - 下面表格按“演示用途”来判断是否保留，不是按“是否有数据”简单二分。
> - 如果文章链路采用“只增量抓取”，则 `raw_articles`、`blog_articles`、`article_metadata`、`crawl_state` 应保留为演示基线，不做整表删除。
> - `stock_info` 和 `ohlcv_bars` 建议收缩为演示所需的最小子集，而不是保留全市场历史。

| 表名 | 数据用途 | 保留 / 删除 | 原因 |
|---|---|---|---|
| `alembic_version` | 记录数据库迁移版本 | 保留 | 这是数据库底座表，删除会破坏迁移状态判断。 |
| `users` | 系统用户与管理员账号 | 保留 | 演示登录、权限、审计都依赖用户表。 |
| `config_profiles` | Profile 正式事实源 | 保留单条演示 Profile | 需要保留 `preview-demo` 或等价演示配置；多余旧 Profile 建议清理或归档。 |
| `raw_articles` | 原始文章抓取结果 | 保留演示基线，删除脏数据 | 如果文章只做增量抓取，这张表应保留一批最近可演示数据；仅删除明显脏数据、测试数据和重复数据。 |
| `blog_articles` | 清洗后的文章主表 | 保留演示基线，删除脏数据 | 与 `raw_articles` 同步保留，作为文章流程展示底座。 |
| `article_metadata` | 文章结构化结果与 LLM 提取结果 | 保留演示基线，删除脏数据 | 文章处理、规则提取、质量展示都依赖这张表。 |
| `crawl_state` | 增量抓取游标 | 保留并按演示起点重置 | 这是增量抓取的关键控制表；不保留会导致重复抓取或跳过目标区间。 |
| `stock_info` | 股票基础信息 | 收缩到演示标的子集 | 当前全市场数据过大，演示时只需 10～30 个标的和必要基准数据。 |
| `ohlcv_bars` | 日线行情数据 | 收缩到演示区间子集 | 只保留演示标的最近约 30 个交易日的数据，避免全市场历史干扰演示。 |
| `jobs` | 历史任务记录 | 删除旧开发 Job | 演示时应只保留本次新产生的任务，旧 Job 会污染任务中心和排错路径。 |
| `job_audit_events` | Job 审计轨迹 | 删除旧开发审计 | 旧审计记录会暴露开发历史和失败堆栈，影响演示清爽度。 |
| `data_audit_events` | 数据变更审计 | 删除旧开发审计 | 旧审计记录不属于演示基线，应清理。 |
| `user_sessions` | 登录会话 | 删除旧会话 | 演示前应重新登录，避免旧会话干扰权限和身份展示。 |
| `ranking_entries` | 排名结果与历史评估 | 删除旧测试结果 | 当前只有少量开发残留记录，不适合作为正式演示数据。 |
| `market_snapshots` | 市场快照主表 | 视演示需要保留最小集合 | 若要展示盘前、盘后或回测，应保留演示日及必要历史快照；其余可清理。 |
| `market_snapshot_sections` | 快照分段内容 | 视 `market_snapshots` 保留策略同步处理 | 依赖快照主表存在，不应单独保留无主记录数据。 |
| `market_snapshot_items` | 快照明细项 | 视 `market_snapshots` 保留策略同步处理 | 依赖快照主表存在，建议与主快照一起裁剪。 |
| `market_data_quality_reports` | 快照质量报告 | 视 `market_snapshots` 保留策略同步处理 | 只保留演示快照对应的质量报告即可。 |
| `market_datasets` | 市场数据集元信息 | 视演示需要保留最小集合 | 如果演示包含数据集查看，应保留本次演示数据集；历史数据集建议清理。 |
| `market_regimes` | 市场状态记录 | 视演示需要保留最小集合 | 如果要演示市场状态分析，只保留演示区间的记录。 |
| `market_regime_features` | 市场状态特征 | 视演示需要保留最小集合 | 与 `market_regimes` 配套，按演示区间裁剪。 |
| `rule_applicability_profiles` | 规则适用性画像 | 视演示需要保留最小集合 | 如果要展示规则适用性，应保留演示期样本；否则可清理历史残留。 |
| `signals` | 信号结果 | 视演示需要保留最小集合 | 若要展示策略/文章到信号的链路，可保留演示期数据；否则清理旧残留。 |
| `workflow_runs` | 工作流运行记录 | 删除旧开发记录 | 演示时只应保留本次运行记录，避免混入历史测试。 |
| `workflow_run_steps` | 工作流步骤记录 | 删除旧开发记录 | 同上，防止任务中心展示大量旧步骤。 |
| `alert_history` | 告警历史 | 删除旧开发记录 | 旧告警会干扰健康检查与排错展示。 |
| `evidence_packs` | 证据包 | 视演示需要保留最小集合 | 若演示要展示证据链，可保留本次演示生成的证据包；历史残留建议清理。 |
| `hot_topics_snapshots` | 热点主题快照 | 视演示需要保留最小集合 | 如果演示包含热点主题分析，只保留最近演示窗口的数据。 |
| `strong_symbols_snapshots` | 强势标的快照 | 视演示需要保留最小集合 | 如果演示会展示强势标的分析，只保留演示期快照。 |
| `topic_constituents_snapshots` | 主题成分快照 | 视演示需要保留最小集合 | 与热点主题链路配套，按演示窗口裁剪。 |
| `trade_logs` | 交易日志 | 删除旧测试记录 | 当前库里无有效演示依赖，旧记录会增加噪音。 |
| `trade_sample` | 交易样本 | 删除旧测试记录 | 不是当前演示主链路所必需。 |
| `trader_memory` | 交易员记忆 | 视 Persona 演示需要保留最小集合 | 如果要演示画像/个性化，可以保留演示期样本；否则清理旧残留。 |
| `trader_strategy_versions` | 策略版本记录 | 视策略演示需要保留最小集合 | 若要演示策略版本、draft/release，保留演示版本即可；旧测试版本建议删除。 |
| `rule_pool` | 规则池 | 视规则池演示需要保留最小集合 | 若本次不演示规则池能力，可清理旧测试数据。 |
| `article_classification` | 文章分类结果 | 视文章演示需要保留最小集合 | 如果文章链路要展示分类结果，可保留演示窗口数据；否则清理旧残留。 |

#### 建议执行顺序

1. 先清理 `jobs`、`job_audit_events`、`data_audit_events`、`user_sessions`、`ranking_entries`。
2. 再确认 `config_profiles` 只保留一个演示 Profile。
3. 文章链路如果采用增量抓取，则先保留基线，再删除脏数据和测试数据。
4. 行情链路只保留演示标的和最近约 30 个交易日。
5. 其余按本次演示是否要展示对应页面决定是否保留最小集合。

#### 可执行清理顺序

> 说明：
> - 下面顺序是“按风险从低到高”排列，适合先清开发痕迹，再收缩业务基线。
> - 文章链路如果采用只增量抓取，不要整表删除文章三表，而是保留基线后再删脏数据、测试数据和重复数据。
> - 如果当前环境并不打算做逐表裁剪，优先切到 Preview 专用数据库再重建基线。

1. 清理开发痕迹表：
   - `jobs`
   - `job_audit_events`
   - `data_audit_events`
   - `user_sessions`
   - `ranking_entries`
2. 处理演示 Profile：
   - `config_profiles` 只保留一个演示 Profile
   - 如果当前只有 `default`，建议替换或重建为 `preview-demo`
3. 处理文章增量基线：
   - 保留 `raw_articles`、`blog_articles`、`article_metadata`、`crawl_state`
   - 删除明显脏数据、测试数据、重复数据
   - 按你希望的增量起点重置 `crawl_state`
4. 收缩行情基线：
   - `stock_info` 只保留演示标的和必要 benchmark
   - `ohlcv_bars` 只保留演示标的最近约 30 个交易日
5. 按演示页面决定是否保留最小集合：
   - `market_snapshots`
   - `market_snapshot_sections`
   - `market_snapshot_items`
   - `market_data_quality_reports`
   - `market_datasets`
   - `market_regimes`
   - `market_regime_features`
   - `rule_applicability_profiles`
   - `signals`
   - `evidence_packs`
   - `hot_topics_snapshots`
   - `strong_symbols_snapshots`
   - `topic_constituents_snapshots`
   - `trader_memory`
   - `trader_strategy_versions`
   - `rule_pool`
   - `article_classification`

#### 绝对不要删

> 这些表属于数据库底座或当前演示必须保留的核心入口，删除会直接破坏系统启动、登录、迁移判断或演示 Profile。

| 表名 | 原因 |
|---|---|
| `alembic_version` | 迁移版本控制表，删除后无法正确判断数据库迁移状态。 |
| `users` | 登录和权限基础表，演示必须保留至少一个管理员账号。 |
| `config_profiles` | Profile 正式事实源，演示需要 `preview-demo` 或等价配置。 |

> 如果你要重新构建演示环境，优先“替换成新的单条演示 Profile”，不要把这张表整体清空后还保留旧的多套配置入口。

---

## 4. Preview 数据准备方案

### 4.1 推荐演示 Profile

准备一个专门的 Profile：

```text
profile_name = preview-demo
```

要求：

1. 只包含演示要用的交易员、标的、策略偏好。
2. 标的数量限制在 10～30 个。
3. 默认 benchmark 使用 `000300.SH` 或系统当前默认指数。
4. 关闭不稳定或非核心 Provider。
5. 明确文章来源和最大抓取数量。

### 4.2 推荐参数

```text
文章 max_articles = 50
OHLCV symbols = 10～30 个核心标的
OHLCV mode = incremental 或 full
OHLCV start_date = end_date 往前 45 个自然日
OHLCV end_date = 最近一个完整交易日
snapshot date = 最近一个完整交易日
backtest date_from = end_date 往前 30 个交易日
backtest date_to = 最近一个完整交易日
```

### 4.3 演示标的选择

优先选择数据源稳定、流动性高、用户容易理解的标的。示例：

```text
000001.SZ, 000333.SZ, 000651.SZ, 600000.SH, 600036.SH,
600519.SH, 601318.SH, 601398.SH, 300750.SZ, 002415.SZ
```

实际以项目支持的市场和代码格式为准。

---

## 5. 完整演示操作流程

### 5.1 启动系统

#### 本机模式

```bash
cd trade-strategy-ai
export LOG_LEVEL=WARNING
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local start
```

访问：

```text
http://localhost:8000
```

#### Docker Compose

```bash
cd trade-strategy-ai
docker compose build
docker compose up -d db
docker compose run --rm api python -m cli.main db-migrate --config config/app.yaml
docker compose up -d api worker web
```

访问：

```text
http://localhost:3000
```

---

### 5.2 健康检查

打开：

```text
/dashboard
/system/health
/jobs
/artifacts
```

验收点：

- Dashboard 无严重错误。
- API、DB、Worker 正常。
- Jobs 页面可加载。
- Artifacts 页面为空或仅有本次新产物。
- Worker 能领取任务，不出现长期 pending。

命令行辅助检查：

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/ui/v1/system/status
```

---

### 5.3 登录与 Profile

操作：

1. 使用 preview admin 登录。
2. 打开 `/profiles`。
3. 导入 `config/app.yaml` 或交付模板 `config/app.template.yaml` 为 `preview-demo`。
4. 确认状态为 `validated`。
5. 进入 Profile 详情，确认关键 sections 存在。

验收点：

- 登录成功。
- Profile 可导入。
- Profile 状态为 `validated`。
- 后续业务页面可以选择该 Profile。

---

### 5.4 文章流程

打开：

```text
/articles/run
```

推荐演示顺序：

1. 选择 Profile：`preview-demo`。
2. 执行 `crawl`，限制 `max_articles=50`。
3. 执行 `clean`。
4. 执行 `validate`。
5. 执行 `store`。
6. 执行 `process`。
7. 到 `/jobs` 查看每一步状态。
8. 到 `/articles/list` 查看文章。
9. 到 `/articles/quality` 查看数据质量。
10. 到 `/artifacts` 查看文章相关产物。

可简化演示：

如果页面支持一键 pipeline-run，可以使用全量 pipeline-run；如果当前实现已经改为 step job，则按 step 展示更清晰。

验收点：

- 每个 step Job 可以创建。
- Job 状态从 `pending` → `running` → `succeeded`。
- 失败时可以看到明确错误。
- 文章列表有数据。
- 数据质量页面能显示摘要。
- 产物中心出现本次文章产物。

---

### 5.5 市场数据流程

#### OHLCV

打开：

```text
/market/ohlcv
```

操作：

1. 选择 Profile：`preview-demo`。
2. 填写 symbols，建议 10～30 个。
3. 选择 `full` 或 `incremental`。
4. 如果是 full，填写 start_date / end_date。
5. 提交 `ohlcv-crawl`。
6. 到 `/jobs` 等待完成。
7. 到 `/market/datasets` 查看数据。

验收点：

- 数据能按标的和日期写入。
- 重复抓取不会产生明显重复脏数据。
- 数据集页面能看到本次范围。

#### Snapshot

打开：

```text
/market/snapshots
```

或盘前页面中的快照构建入口。

操作：

1. 选择 Profile。
2. 设置 date 为最近一个完整交易日。
3. slot 使用默认 `17-30`。
4. snapshot_type 使用 `all`。
5. 提交 `snapshot-build`。
6. 查看 snapshot-json、summary、quality 产物。

验收点：

- 快照构建成功。
- 快照质量报告可查看。
- 快照 ID 可用于策略构建。

#### Kaipan，可选

如果用户关心 Kaipan：

1. 打开 `/market/kaipan`。
2. 先执行 `kaipan-fetch`。
3. 再执行 `kaipan-normalize`。
4. 演示调度启动/停止入口，但不建议现场长时间等待调度触发。

验收点：

- 抓取和归一化 Job 可执行。
- 调度入口状态清楚。
- 用户理解 Kaipan 与 OHLCV 是两个不同数据链路。

---

### 5.6 策略版本流程

打开：

```text
/strategies/versions
```

操作：

1. 选择 Profile。
2. 选择 trader_id。
3. strategy_date 使用最近一个完整交易日。
4. 如页面支持，选择 snapshot_id。
5. 提交 `strategy-build`。
6. Job 成功后查看生成的策略版本。
7. 确认版本状态为 `draft`。
8. 打开版本详情，检查推荐、规则、证据链。
9. 人工执行 `Release`。
10. 确认版本状态变为 `released`。

验收点：

- `strategy-build` 只生成草稿版本。
- 用户可以理解 draft 不能直接作为正式版本。
- Release 后变为 released。
- released 版本可供盘前和回测使用。

---

### 5.7 盘前流程

打开：

```text
/strategies/pre-market
```

操作：

1. 选择 Profile。
2. Strategy date 选择最近一个完整交易日或演示日。
3. Benchmark 使用默认或 `000300.SH`。
4. 确认当日快照存在。
5. 提交 `run-pre-market`。
6. 查看 Job 状态。
7. 查看 result-json 或 HTML 报告。

验收点：

- 盘前 Job 成功。
- 报告包含关注标的、市场状态、策略要点。
- 页面可以跳转到任务详情和产物详情。

---

### 5.8 盘后流程

打开：

```text
/strategies/after-close
```

操作：

1. 选择 Profile。
2. as_of_date 选择同一个完整交易日。
3. 勾选 export_html。
4. 提交 `run-after-close`。
5. 查看 Job 状态和报告。

验收点：

- 盘后 Job 成功。
- 报告包含 evaluations、failure_categories、ranking_features、postmortem_notes。
- 用户能看到表现考核和归因结果。

---

### 5.9 回测流程

打开：

```text
/backtest
```

操作：

1. 选择 Profile。
2. 选择 trader_id。
3. date_from 使用演示区间开始日期。
4. date_to 使用最近一个完整交易日。
5. strategy_version_id 选择 released 版本。
6. symbols 可留空或填演示标的。
7. benchmark_symbol 使用默认。
8. 保持 use_snapshot_only=true。
9. 提交 `backtest-run`。
10. 查看指标、Markdown 报告、CSV 明细。
11. 可选执行 `backtest-validate-rules`。
12. 可选执行 `backtest-reproducibility-check`。

验收点：

- 回测 Job 成功。
- 结果包含 total_days、total_trades、valid_trades、skipped_trades、win_rate、avg_return_pct、fingerprint。
- 产物包含 result-json、report-markdown、records-csv。
- skipped 如果较多，需要能解释原因，例如缺数据、无信号、无快照。

---

### 5.10 任务、产物、告警、审计展示

#### 任务中心

打开 `/jobs`：

- 按 status 筛选。
- 按 job_type 筛选。
- 打开任务详情。
- 展示参数、日志、结果、关联产物。
- 如存在失败任务，演示 retry 或错误定位。

#### 产物中心

打开 `/artifacts`：

- 展示 result-json。
- 预览 report-markdown。
- 下载 records-csv。
- 展示 snapshot-quality-json。

#### 告警中心

打开 `/alerts`：

- 查看告警配置状态。
- 如果 Webhook 已配置，发送测试告警。
- 展示确认/解决告警。

#### 审计

打开 `/system/audit`：

- 展示高风险操作记录。
- 包括 Release、restore、db-migrate、权限拒绝等。

验收点：

- 用户能从业务结果追溯到 Job。
- 能从 Job 追溯到产物。
- 能从失败定位到日志。
- 高风险操作有审计记录。

---

## 6. 验收操作流程

### 6.1 演示前验收

| 检查项 | 通过标准 |
|---|---|
| 当前环境已备份 | `/system/backup` 或手工备份完成 |
| 开发旧数据已隔离 | Jobs、Artifacts、Processed 不展示旧数据 |
| API 正常 | `/health` 返回正常 |
| Worker 正常 | 测试 Job 能从 pending 进入 running |
| Profile 可用 | `preview-demo` 为 validated |
| 前端可访问 | Dashboard、Jobs、Artifacts、Profiles 可打开 |
| 数据源可用 | 小范围 OHLCV 或文章抓取成功 |

### 6.2 业务流程验收

| 流程 | 操作 | 通过标准 |
|---|---|---|
| 登录 | 使用 preview admin 登录 | 成功进入 Dashboard |
| Profile | 导入/查看 Profile | 状态 validated |
| 文章 | crawl/clean/validate/store/process | Job succeeded，文章列表有数据 |
| OHLCV | 抓取演示标的 | 数据集可查看 |
| Snapshot | 构建演示日快照 | 质量报告可查看 |
| Strategy | strategy-build | 生成 draft |
| Release | 人工发布策略版本 | 状态 released |
| Pre-market | run-pre-market | 报告可查看 |
| After-close | run-after-close | 复盘结果可查看 |
| Backtest | backtest-run | 指标和报告可查看 |
| Artifacts | 查看和下载产物 | JSON/Markdown/CSV 可访问 |
| Jobs | 查看任务详情 | 参数、日志、产物链路完整 |

### 6.3 交付验收口径

本次 Preview 可以判定为通过的最低标准：

```text
1. 系统在干净演示数据下启动成功。
2. 至少一个 Profile validated。
3. 文章流程至少完成一次。
4. OHLCV 至少完成一批标的数据抓取。
5. 至少生成一个 snapshot。
6. 至少生成一个 draft 策略版本，并成功 Release。
7. 盘前和盘后各成功运行一次。
8. 回测成功运行一次，并生成报告和 CSV。
9. 任务中心和产物中心能完整追踪结果。
10. 失败或异常有明确排错路径。
```

---

## 7. 推荐现场演示脚本

### 7.1 开场说明

```text
这次演示使用 preview-demo Profile，数据范围限制在最近约 30 个交易日，目的是展示系统完整闭环，而不是追求最大数据量。
```

### 7.2 演示顺序

```text
1. Dashboard：系统健康和最近任务
2. Profiles：preview-demo 配置
3. Articles：文章抓取与处理结果
4. Market：OHLCV 与 Snapshot
5. Strategies：策略构建、draft、Release
6. Pre-market：盘前报告
7. After-close：盘后复盘
8. Backtest：历史回测结果
9. Jobs：任务追踪和日志
10. Artifacts：报告和文件下载
11. System：备份、审计、健康检查
```

### 7.3 现场避免事项

不要现场做这些事：

1. 不要抓全市场。
2. 不要抓一年以上历史数据。
3. 不要在用户面前临时改核心配置。
4. 不要现场清空数据库。
5. 不要现场执行 restore-data，除非已经提前演练。
6. 不要展示开发旧 Job、失败堆栈、脏产物。
7. 不要使用默认弱密码或个人账号。

---

## 8. 如果某一步失败怎么处理

| 失败点 | 处理方式 |
|---|---|
| 登录失败 | 检查 API Key / 用户密码，重新创建 preview admin |
| Profile validation 失败 | 回到导入源（`config/app.yaml` 或 `config/app.template.yaml`），检查必填 section 和路径 |
| Job pending | 检查 Worker 是否启动、DB 是否可连 |
| 文章抓取失败 | 降低 max_articles，检查来源配置和网络 |
| OHLCV 失败 | 缩小 symbols，缩短日期范围，检查 Provider |
| Snapshot 失败 | 确认 OHLCV 数据已存在，检查 benchmark_symbol |
| strategy-build 失败 | 确认 Profile、文章结构化数据、快照存在 |
| 无 released 版本 | 到策略版本详情执行 Release |
| 盘前失败 | 检查 released 策略版本和当日快照 |
| 盘后失败 | 检查演示日是否已有行情数据和盘前结果 |
| 回测 skipped 多 | 检查 OHLCV、快照覆盖区间和 symbols |

---

## 9. 建议新增的 Preview 专用脚本

为了以后交付更稳定，建议后续增加一个只在演示环境使用的脚本：

```text
scripts/preview_reset.py
```

功能建议：

1. 检查当前环境是否为 preview/dev，禁止在 production 运行。
2. 自动创建备份。
3. 清理 Job、Artifacts、Processed、旧演示数据。
4. 保留或重新导入 preview-demo Profile。
5. 输出下一步操作清单。

建议命令：

```bash
python -m scripts.preview_reset --profile preview-demo --keep-backups --confirm PREVIEW
```

在没有这个脚本前，不建议把手工 SQL 清理作为正式流程交给用户。

---

## 10. 最终建议

本次交付前 Preview 推荐使用：

```text
演示范围：最近 45 个自然日 / 约 30 个交易日
文章数量：50 篇以内
标的数量：10～30 个
快照：至少演示日 1 个，回测需要时补历史快照
回测：20～30 个交易日
数据库：优先使用 Preview 专用数据库，不直接污染开发库或生产库
```

这样既能完整展示系统能力，又能把现场风险控制在可接受范围内。
