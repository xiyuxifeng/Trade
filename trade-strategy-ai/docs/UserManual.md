
# Trade Strategy AI 操作手册

> 适用版本：仓库当前 `pyproject.toml` 中的 `trade-strategy-ai==0.1.0`（以代码为准）。
> 
> 本手册面向“第一次接触项目的人”，目标是：**按步骤照做即可跑通**抓取 → 处理 → 盘前日报 → 盘后考核 → 回测/优化 的主链路。
> 本文档的 CLI 章节按当前 `cli/main.py` 已注册命令整理，包含配置、数据处理、盘前盘后、快照、回测、优化、规则池和调度等全部常用操作入口。

---

## 目录

- [0. 安装与配置](#0-安装与配置)
- [1. 主要功能与典型用法](#1-主要功能与典型用法)
- [2. CLI 命令与参数说明](#2-cli-命令与参数说明)
- [3. 如何运行当前项目（CLI / API / 调度）](#3-如何运行当前项目cli--api--调度)
- [4. 数据依赖与获取方式](#4-数据依赖与获取方式)
- [5. 可配置参数清单（含含义）](#5-可配置参数清单含含义)
- [6. 结果与中间文件在哪里看](#6-结果与中间文件在哪里看)
- [7. 如何进行调优/优化](#7-如何进行调优优化)
  - [7.1 文章→规则完整链路](#71-文章规则完整链路端到端)
  - [7.2 trader 策略回测与规则验真](#72-trader-策略回测与规则验真)
  - [7.3 风控账户快照](#73-风控账户快照)
  - [7.4 trader 筛选与策略建议](#74-trader-筛选与策略建议optimize)
  - [7.5 规则池管理命令速查](#75-规则池管理命令速查rule-pool)
- [8. 常见问题与日志排障](#8-常见问题与日志排障)
- [9. 其他重要信息](#9-其他重要信息)

---

## 0. 安装与配置

### 0.1 运行前你需要准备什么

- Python：`>=3.11`（见 `pyproject.toml`）
- 数据库：PostgreSQL（强烈推荐用于 pipeline / 策略版本 / ranking / 告警等）
- 可选：
	- Playwright 浏览器运行时（仅当抓取需要 `render_js=true` 时才必须）
	- Docker（仅用于快速起 PostgreSQL/Redis，项目本身不强制 Docker）

### 0.2 创建 Python 虚拟环境并安装依赖

在 workspace 根目录（`trade-strategy-ai` 的上一层）创建虚拟环境：

```bash
# 在 workspace 根目录执行
python -m venv .venv
source .venv/bin/activate

# 进入项目目录，可编辑安装
cd trade-strategy-ai
pip install -e ".[dev]"
```

说明：项目采用可编辑安装（`-e`），便于本地开发和直接运行 `python -m ...`。

如果你在 `crawl.sources[]` 中启用了 `render_js: true`（需要 Playwright 动态渲染），还需要安装浏览器运行时：

```bash
python -m playwright install chromium
```

### 0.3 启动 PostgreSQL（两种方式二选一）

#### 方式 A：本机安装（macOS Homebrew 示例）

```bash
brew install postgresql@15
brew services start postgresql@15
```

创建用户与数据库（示例：用户名/密码均为 `trade`）：

```bash
psql postgres -c "CREATE ROLE trade WITH LOGIN PASSWORD 'trade';"
createdb -O trade trade_strategy_ai
```

然后配置数据库连接串（推荐写到 `.env` 或导出环境变量）：

```bash
export DATABASE_URL='postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai'
```

#### 方式 B：Docker Compose 启动数据库

仓库提供了 `docker-compose.yml`（默认端口 5432）：

```bash
docker compose -f docker-compose.yml up -d db
```

你可以通过环境变量覆盖数据库名/用户/密码（可选）：

```bash
export POSTGRES_DB=trade_strategy_ai
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
```

> 注意：如果你用 compose 的默认用户密码，请相应设置 `DATABASE_URL`。

### 0.4 配置文件与环境变量（强烈建议先读这一节）

项目主配置文件为：`config/app.yaml`，配置加载由 `src/common/config.py:load_app_config()` 完成。

#### 配置优先级（高 → 低）

1. 少量 CLI 参数（个别命令提供覆盖项）
2. 环境变量（推荐）
3. `config/app.yaml`
4. 代码默认值（兜底）

#### 环境变量展开

YAML 支持环境变量展开：例如在 `config/app.yaml` 中写 `"${TGB_COOKIE}"`，运行时会替换为当前环境变量值。

#### 常用环境变量

- `DATABASE_URL`：数据库连接串（SQLAlchemy async URL）
- `TGB_COOKIE`：淘股吧爬虫 Cookie（用于文章抓取）
- 大模型 API Key：取决于你选用的 `config.llm.provider`（例如阿里云 DashScope 兼容 OpenAI 接口，通常用 `DASHSCOPE_API_KEY` 注入，然后在 YAML 里引用）

可选：你也可以在项目根目录创建一个 `.env` 文件来统一管理本地环境变量（避免每次手工 export）：

```env
DATABASE_URL=postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai
TGB_COOKIE=你的cookie
DASHSCOPE_API_KEY=你的key
```

注意：

- `config/app.yaml` 中的 `"${TGB_COOKIE}"` 这类写法，是从**进程环境变量**读取的；项目不会自动把 `.env` 文件内容导出为环境变量。
- `.env` 对数据库连接串通常仍然有效，是因为部分代码会通过 `config/settings.py`（Pydantic Settings）读取 `.env`；但这不等价于“YAML 也会自动读取 `.env`”。

如果你希望在当前终端会话中让 `.env` 的变量真正成为环境变量（供 YAML 展开使用），可以执行：

```bash
set -a
source .env
set +a
```

#### 生成一份“默认模板配置”（可选）

如果你希望从模板生成新的配置文件（不会自动覆盖已有文件）：

```bash
python -m cli.main init-config --dest config/app.yaml
```

### 0.5 初始化数据库（迁移）

先做连通性检查：

```bash
python -m cli.main db-check --config config/app.yaml
```

再执行迁移：

```bash
python -m cli.main db-migrate --config config/app.yaml
```

---

## 1. 主要功能与典型用法

本项目主链路可以按两条“最常用”的路径理解：

1. **数据资产链路**：文章抓取与处理 Pipeline（写库 + 导出 DuckDB）
2. **盘前/盘后闭环**：盘前日报（生成 TradeIdea/Signal）→ 盘后考核（评估、evidence pack、ranking）

另外还提供：市场候选池快照（Kaipan）、OHLCV 入库、回测与优化工具。

### 1.1 文章抓取与处理 Pipeline（crawl → clean → validate → store → process → export）

一键执行全流程（推荐先从小规模跑通）：

```bash
python -m cli.main pipeline-run --config config/app.yaml --max-articles 10
```

常见变体：

- 强制重跑清洗/校验产物：

```bash
python -m cli.main pipeline-run --config config/app.yaml --force
```

- 只跑单步（调试/补跑）：

```bash
python -m cli.main pipeline-step crawl --config config/app.yaml
python -m cli.main pipeline-step clean --config config/app.yaml
python -m cli.main pipeline-step store --config config/app.yaml
```

> 提示：`pipeline-run` 与 `pipeline-step` 会自动在 `data/processed/` 下发现前置中间文件。

### 1.2 盘前日报（run-pre-market）

生成当日盘前日报（写入 `config.storage.output_dir` 目录）：

```bash
python -m cli.main run-pre-market --config config/app.yaml --export-html
```

可指定日期：

```bash
python -m cli.main run-pre-market --config config/app.yaml --as-of 2026-05-06 --export-html
```

说明（与代码一致）：

- 日报 JSON 文件名：`daily_report_YYYY-MM-DD.json`
- 可选 HTML：`daily_report_YYYY-MM-DD.html`
- 若启用了 persona router 且 clusters 文件存在，会额外输出：`persona_route_YYYY-MM-DD.json`

### 1.3 盘后考核（run-after-close）

基于盘前日报进行评估并写入考核结果：

```bash
python -m cli.main run-after-close --config config/app.yaml --export-html
```

说明：

- 考核 JSON：`evaluation_YYYY-MM-DD.json`
- 可选 HTML：`evaluation_YYYY-MM-DD.html`
- 盘后会为每条交易想法生成 EvidencePack（用于追溯、归因、ranking）：见“产物位置”章节。

### 1.4 市场候选池快照（snapshot build）

候选池快照是 Stage 4 盘前链路的重要输入之一，默认落盘到：

- `data/market_universe/snapshots/{YYYY-MM-DD}/{slot}.json`

构建命令：

```bash
python -m cli.main snapshot build --date 2026-04-29 --type all
```

可仅构建某一种：

```bash
python -m cli.main snapshot build --date 2026-04-29 --type hot_topics --force
```

说明：

- 目前快照构建器会尝试使用 Kaipan provider；若 Kaipan 配置缺失/不可用，会跳过并打印 warning。

### 1.5 OHLCV 行情入库（ohlcv crawl）

抓取日线 OHLCV 并写入数据库表（`ohlcv_bars`）：

```bash
python -m cli.main ohlcv crawl --mode incremental
```

全量模式示例：

```bash
python -m cli.main ohlcv crawl --mode full --from 2026-01-01 --to 2026-04-28 --limit 100
```

### 1.6 策略版本（strategy build / list）

构建某交易员某天的策略版本（draft）：

```bash
python -m cli.main strategy build --trader trader_a --date 2026-04-29
```

列出策略版本（从数据库读取）：

```bash
python -m cli.main strategy list --status all
python -m cli.main strategy list --trader trader_a --status released
```

### 1.7 备份与恢复（backup-data / restore-data）

备份数据库表 +（可选）处理产物：

```bash
python -m cli.main backup-data --config config/app.yaml
```

恢复（**破坏性操作**，必须显式 `--force`）：

```bash
python -m cli.main restore-data --config config/app.yaml --source /path/to/backup --force
```

### 1.8 数据监控 Dashboard（可选）

项目内置了一个“数据监控/质量巡检”工具（Click CLI），用于汇总：

- 数据新鲜度（文章/交易/行情）
- 数据质量/异常
- 告警摘要（若触发 critical，会以非 0 退出码退出，便于 crontab/CI 监控）

运行方式：

```bash
# 仅输出到终端
python -m src.pipeline.dashboard --mode cli

# 生成静态 HTML
python -m src.pipeline.dashboard --mode html

# 两种都输出
python -m src.pipeline.dashboard --mode both
```

默认 HTML 输出：`data/processed/dashboard/dashboard.html`。

---

## 2. CLI 命令与参数说明

### 2.1 总入口

项目 CLI 主入口为：

```bash
python -m cli.main <command> [options]
```

你可以用 Typer 自带帮助查看所有命令：

```bash
python -m cli.main --help
python -m cli.main <command> --help
```

下面列出“当前代码中已注册”的主要命令与关键参数（按功能分组）。

### 2.2 配置/数据库

- `init-config`
	- `--dest`：输出路径（默认 `config/app.yaml`）
	- `--force`：覆盖已存在文件

- `db-check`
	- `--config`：从 YAML 读取 `database.url` 并同步到 `DATABASE_URL`
	- `--database-url`：临时覆盖数据库连接串

- `db-migrate`
	- `--config`：同上
	- `--project-root`：项目根目录（默认 `.`）
	- `--revision`：目标版本（默认 `head`）

- `init-project`
	- 说明：一次性执行迁移 + 本地 seed（用于快速初始化开发环境）
	- `--config`：配置文件路径
	- `--log-level`：日志级别（默认 `INFO`）

- `seed-data`
	- 说明：将本地 crawl JSONL / 交易记录等样例数据导入数据库（用于开发/演示）
	- `--config`：配置文件路径
	- `--log-level`：日志级别（默认 `INFO`）

- `backup-data`
	- 说明：备份数据库表与（可选）处理产物到一个目录
	- `--dest`：备份目录（可选）
	- `--include-processed`：是否包含 `data/processed`
	- `--log-level`：日志级别（默认 `INFO`）

- `restore-data`
	- 说明：从备份目录恢复（破坏性操作，必须 `--force`）
	- `--source`：备份目录
	- `--include-processed`：是否恢复 `data/processed`
	- `--force`：确认执行
	- `--log-level`：日志级别（默认 `INFO`）

- `scheduler-start`
	- 说明：启动盘前/盘后定时任务（依赖 `schedule.enable=true`）
	- `--config`：配置文件路径
	- `--log-level`：日志级别（默认 `INFO`）

### 2.3 抓取与数据处理 Pipeline

- `crawl`
	- `--config`：配置文件路径（默认 `config/app.yaml`）
	- `--max-articles`：每个作者最多抓取文章数
	- `--log-level`：日志级别（默认 `INFO`）

- `import-trade-logs`
	- `--config`：配置文件路径
	- `--csv-path`：交易记录文件路径（支持 `.csv/.xlsx/.html/.pdf`）
	- `--source`：交易来源标识（默认 `csv_import`）
	- `--trader-account-map`：JSON 字符串，`trader_id -> account_id` 映射（可选）
	- `--dry-run`：仅解析校验，不写入数据库
	- `--log-level`：日志级别（默认 `INFO`）

- `pipeline-run`
	- `--config`：配置文件
	- `--max-articles`：限制数量（crawl/clean/validate/store 生效）
	- `--force`：强制重跑 clean/validate（并触发更多覆盖行为）
	- `--skip-crawl`：跳过 crawl
	- `--from-step`：从指定步骤开始（建议仅使用：crawl/clean/validate/store/process/export）
	- `--use-db`：crawl 阶段写入 `raw_articles` 表，替代写 `articles.jsonl`
	- `--new-version`：process 阶段的版本号（如 `v2/v3`；常用于你升级 prompts 后希望重跑抽取/处理）
	- `--log-level`：日志级别（默认 `INFO`）

说明：当前 `pipeline-run` 运行的图节点为 `crawl/clean/validate/store/process/export`。`stock_info_update/cleanup` 虽然在 `pipeline-step` 中可用，但不属于 `pipeline-run` 的图节点。

- `pipeline-step <step>`
	- `<step>` 可选：`crawl` / `clean` / `validate` / `store` / `stock_info_update` / `process` / `export` / `cleanup`
	- 通用参数：`--config`、`--max-articles`、`--force`、`--use-db`、`--new-version`、`--log-level`

- `migrate-crawl-state`
	- 将 `data/processed/crawl/.../state.json` 迁移到数据库 `crawl_state` 表
	- `--config`：配置文件路径
	- `--log-level`：日志级别（默认 `INFO`）

- `extract-articles`
	- `--config`：配置文件路径
	- `--limit`：最多抽取多少篇（默认 20）；`--force` 强制重跑（清空断点）；`--version` 提取版本号（默认 v1，升级 prompts 后应使用 v2/v3）
	- `--log-level`：日志级别（默认 `INFO`）
	- 说明：未配置 LLM 时会使用启发式降级抽取，并写入 `article_metadata.raw_llm_output.mode=fallback_heuristic`

- `clusters-build`
	- `--config`：配置文件路径
	- `--dest`：clusters 输出路径（默认 `data/processed/persona/clusters.real.json`）
	- `--max-articles`：最多用多少篇文章
	- `--log-level`：日志级别（默认 `INFO`）

- `e2e-regression`（可选）
	- 说明：端到端回归链路（crawl→pipeline→extract→clusters→pre_market+HTML→after_close+HTML）
	- `--config` / `--max-articles` / `--extract-limit` / `--clusters-dest` / `--log-level`

### 2.4 盘前/盘后/信号

- `run-pre-market`
	- `--as-of`：日期 `YYYY-MM-DD`（默认今天）
	- `--force`：覆盖缓存输出
	- `--export-html`：同时导出 HTML
	- `--log-level`：日志级别（默认 `INFO`）

- `run-after-close`
	- 同上

- `list-signals`
	- `--config`：配置文件路径
	- `--symbol`：按标的过滤
	- `--since`：起始日期过滤
	- `--limit`：返回数量
	- `--log-level`：日志级别（默认 `INFO`）

- `persona-init-sample`
	- 说明：生成样例 clusters 文件（用于在真实聚类前跑通 persona router）
	- `--config`：配置文件路径
	- `--dest`：输出路径（可选）
	- `--log-level`：日志级别（默认 `INFO`）

- `market-state-build`
	- 说明：从基准指数/ETF 日线构建 MarketState JSON
	- `--config`：配置文件路径
	- `--as-of`：日期（默认今天）
	- `--from-akshare`：当未配置 CSV 时尝试从 AkShare 拉取
	- `--cache-csv`：从 AkShare 拉取后是否缓存为 CSV
	- `--dest`：输出路径（默认 `data/processed/persona/market_state.json`）
	- `--log-level`：日志级别（默认 `INFO`）

### 2.5 快照/策略版本/OHLCV

- `snapshot build`
	- `--date`：交易日
	- `--slot`：时段（默认 `17-30`）
	- `--type`：`all` / `hot_topics` / `topic_constituents` / `strong_symbols`
	- `--force`：覆盖已有快照
	- `--config`：配置文件路径

- `strategy build`
	- `--trader`：交易员 ID
	- `--date`：策略日期
	- `--force`：强制重建
	- `--config`：配置文件路径

- `strategy list`
	- `--trader`：可选
	- `--status`：`all` / `released` / `draft` / `candidate`
	- `--limit`：默认 50
	- `--config`：配置文件路径

- `ohlcv crawl`
	- `--mode`：`full` / `incremental`
	- `--symbols-file`：每行一个代码
	- `--from` / `--to`：日期区间
	- `--limit`：标的数量上限
	- `--config`：配置文件路径（用于读取 `akshare.*` 限速参数）

### 2.6 回测（backtest 子命令）

入口：

```bash
python -m cli.main backtest <subcommand> [options]
```

- `backtest run`
	- `--trader`、`--from`、`--to`
	- `--mode`：`full` / `replay` / `rule_validation`
	- `--format`：`markdown` / `json`
	- `--output`：输出文件路径（可选，不提供则打印到 stdout）
	- `--config`：应用配置（用于初始化快照 loader 等依赖）

- `backtest report`
	- `--result-file`：回测结果 JSON
	- `--format`、`--output`

- `backtest validate-rules`
	- 基于快照对高频规则做命中验证
	- `--output`：输出报告（Markdown）
	- `--config`：应用配置文件路径（用于初始化快照/策略加载依赖）

- `backtest reproducibility-check`
	- 相同请求跑两次，对比序列化结果是否一致（可复现性检查）
	- `--config`：应用配置文件路径（可选）

### 2.7 优化（optimize 子命令）

入口：

```bash
python -m cli.main optimize <subcommand> [options]
```

- `optimize filter`：基于 BacktestResult JSON 做活跃 trader 筛选
- `optimize advise`：基于 RuleValidationResult JSON 给出策略调整建议
- `optimize create-candidate`：根据“正式版本 + 调整建议”生成候选版本（文件链路默认；`--db` 走 DB 链路）

> 注意：`optimize create-candidate` 支持 `--output` 输出候选版本 JSON；`--db` 模式要求提供 `--trader` 与 `--date`。

### 2.8 规则池管理（rule-pool）

**查看规则详情：**

```bash
# 查看单条规则完整信息（基本属性、提取层、回测结果、审核状态等）
python -m cli.main rule-pool show --rule-id <RULE_ID>
```

**列出规则（支持过滤）：**

```bash
# 列出所有规则
python -m cli.main rule-pool list --limit 100

# 按审核状态过滤
python -m cli.main rule-pool list --status pending

# 按规则类型过滤
python -m cli.main rule-pool list --rule-type entry

# 只显示有映射条件的规则（可参与回测）
python -m cli.main rule-pool list --skip-no-mapped
```

**审核规则：**

```bash
# 单条审核（approve / reject / pending）
python -m cli.main rule-pool review --rule-id <RULE_ID> --decision approve

# 强制覆盖已有审核结果
python -m cli.main rule-pool review --rule-id <RULE_ID> --decision reject --force

# 批量审核：将 pending 规则批量 approve
python -m cli.main rule-pool review-batch --decision approve --status pending --limit 50
```

**自动审核机制：**

规则在文章提取入库时自动触发审核，无需人工干预：
- `initial_confidence >= 0.7` 且规则有可映射条件 → **自动通过** (auto_review)
- `initial_confidence < 0.2` → **自动拒绝**
- `0.2 <= initial_confidence < 0.7` → 保持 **pending**，等待人工审核

人工审核通过 CLI `review` 命令执行，`--force` 可覆盖自动审核结果。

### 2.9 KaipanScheduler（独立 CLI，非 `cli.main`）

Kaipan 的抓取/转换调度器入口是：

```bash
python -m src.providers.kaipan_scheduler <command> [options]
```

命令包括：`fetch` / `normalize` / `status` / `run`，详见 `docs/bak/kaipan_CLI.md`。

### 2.10 数据监控 Dashboard（独立 CLI，非 `cli.main`）

```bash
python -m src.pipeline.dashboard --mode cli
python -m src.pipeline.dashboard --mode html
python -m src.pipeline.dashboard --mode both
```

---

## 3. 如何运行当前项目（CLI / API / 调度）

### 3.1 最推荐：仅用 CLI 跑通主链路（最少步骤）

1）配置环境变量（示例）：

```bash
export DATABASE_URL='postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai'
export TGB_COOKIE='(你的淘股吧 Cookie)'
```

2）数据库迁移：

```bash
python -m cli.main db-migrate --config config/app.yaml
```

3）跑数据 pipeline（抓取文章 → 清洗 → 入库）：

```bash
python -m cli.main pipeline-run --config config/app.yaml --max-articles 10
```

4）抓取 OHLCV 行情 + 构建候选池快照（盘前/盘后依赖）：

```bash
python -m cli.main ohlcv crawl --mode full --from 2026-01-01 --to 2026-04-30 --limit 50
python -m cli.main snapshot build --date 2026-04-29 --type all
```

5）文章提取 → 规则入库（Stage 11 链路）：

```bash
python -m cli.main extract-articles --config config/app.yaml --limit 50
```

6）生成盘前/盘后：

```bash
python -m cli.main run-pre-market --config config/app.yaml --export-html
python -m cli.main run-after-close --config config/app.yaml --export-html
```

### 3.2 运行 API 服务（FastAPI）

仓库目前存在两套 FastAPI 应用入口：

1) `api/main.py`（推荐，路由在 `api/routers/*`）
2) `src/api/main.py`（历史/备用入口，带 `X-API-Key` 鉴权依赖 `src/api/dependencies.py:verify_api_key`）

#### 方式 A（推荐）：启动 `api/main.py`

API 入口在 `api/main.py`，用 uvicorn 启动：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

常用地址：

- Swagger UI：`http://localhost:8000/docs`
- 健康检查：`GET http://localhost:8000/health`
- 手动触发：
	- `POST /run/pre_market`
	- `POST /run/after_close`
- 报告查询：`/reports/*`
- 策略版本/快照/ranking/回测结果/告警历史：见根路径 `GET /` 返回的 `endpoints` 字段。

备注：该入口当前未在 `api/routers/*` 路由上强制 `X-API-Key` 校验。

#### 方式 B（可选）：启动 `src/api/main.py`（带 X-API-Key）

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

当 `config/app.yaml` 中 `api.auth.enabled=true` 且配置了 `api.auth.api_keys` 时，该入口的部分端点会要求在 Header 中携带 `X-API-Key`。

### 3.3 启动调度（两套调度器）

#### 3.3.1 盘前/盘后调度器（APScheduler，来自 `cli.main scheduler-start`）

当你在 `config/app.yaml` 中设置了：

- `schedule.enable: true`
- `schedule.pre_market_time: "HH:MM"`
- `schedule.after_close_time: "HH:MM"`

即可启动：

```bash
python -m cli.main scheduler-start --config config/app.yaml
```

#### 3.3.2 Kaipan 数据抓取调度器（来自 `src.providers.kaipan_scheduler run`）

```bash
python -m src.providers.kaipan_scheduler run
```

说明：该调度器会用 AkShare 的交易日历判断是否交易日，非交易日会自动退出。

---

## 4. 数据依赖与获取方式

### 4.1 交易员文章与评论（淘股吧 tgb.cn）

- 用途：为文章抽取（`article_metadata`）、策略规则沉淀、交易员画像提供原始素材。
- 获取方式：爬虫抓取（需要 Cookie）

关键配置：

- `crawl.auth.tgb.cn.cookie`：建议写 `"${TGB_COOKIE}"`，然后通过环境变量注入。
- `crawl.sources[]`：配置作者（`author_id`、`author_name`、`list_url`）。

抓取命令：

```bash
python -m cli.main crawl --config config/app.yaml --max-articles 50
```

### 4.2 市场候选池快照（Kaipan 私有接口）

- 用途：生成 `hot_topics / topic_constituents / strong_symbols`，供 Stage 4 盘前链路消费。
- 获取方式（两种方式二选一）：
	- 方式 A（推荐用于“数据资产化/可回放”）：先用调度器抓取 raw 并 normalize，再构建 MarketUniverse 快照。
	- 方式 B（更省步骤）：直接运行 `snapshot build`，它会通过 Kaipan provider 在线拉取并落盘快照。

示例：

```bash
# 方式 A：先抓取/归一化，再构建快照
python -m src.providers.kaipan_scheduler fetch --date 2026-04-22 --slot 17-30
python -m cli.main snapshot build --date 2026-04-22 --slot 17-30 --type all

# 方式 B：直接构建快照（会在线拉取并保存）
python -m cli.main snapshot build --date 2026-04-22 --slot 17-30 --type all
```

Kaipan 可选鉴权参数（如有）：

- `kaipan.token`
- `kaipan.user_id`

### 4.3 行情数据（OHLCV 日线）

- 用途：盘后评估（计算 return/mfe/mae）、回测、市场状态识别等。
- 获取方式：`python -m cli.main ohlcv crawl ...` 入库到 `ohlcv_bars` 表。
- 数据源：默认使用东方财富（`stock_zh_a_hist`），失败后自动 fallback 到新浪源（`stock_zh_a_daily`），仅 A 股生效。
- 限速配置：`config/app.yaml` 中的 `akshare.min_request_interval_seconds` 等参数控制请求节奏，避免触发数据源反爬。

### 4.4 交易记录（Trade Logs）

支持从 CSV/Excel/HTML/PDF 导入（写库）：

```bash
python -m cli.main import-trade-logs --config config/app.yaml --csv-path /path/to/trades.csv
```

参数说明：

- `--csv-path`：虽然叫 csv-path，但实际支持 `.csv/.xlsx/.html/.pdf`（代码按后缀分流）
- `--dry-run`：只解析校验，不写库
- `--trader-account-map`：JSON 字符串，`trader_id -> account_id` 映射（可选）

### 4.5 LLM（可选，但强烈建议用于更好抽取）

文章抽取会在 LLM 不可用时自动降级为启发式抽取（不会直接阻塞），但质量通常会更低。

相关配置位于：

- `llm.provider`
- `llm.model`（支持字符串或数组）
- `llm.url`
- `llm.api_key`（建议使用环境变量注入）

---

## 5. 可配置参数清单（含含义）

本节以 `config/app.yaml` + `src/common/config.py` 的 `AppConfig` 为准，列出最常用配置项。

### 5.1 database

- `database.url`：数据库连接串（async SQLAlchemy URL）。为空时会回退到环境变量 `DATABASE_URL`（或 Settings 默认值）。
- `database.echo`：SQLAlchemy echo。
- `database.pool_size / max_overflow / pool_timeout / pool_recycle`：连接池参数。

### 5.2 schedule

- `schedule.enable`：是否启用 `cli.main scheduler-start` 调度。
- `schedule.pre_market_time`：盘前触发时间（`HH:MM`）。
- `schedule.after_close_time`：盘后触发时间（`HH:MM`）。

### 5.3 evaluation

- `evaluation.min_expected_return`：盘后判定“达标”的收益率阈值（例如 `0.01` 表示 1%）。
- `evaluation.loss_trigger`：是否亏损即触发复盘/任务。
- `evaluation.trade_constraint.*`：A 股交易约束（T+1、涨跌停幅度、板块类型推断等）。

### 5.4 data

- `data.providers`：数据提供者列表（Phase 0 常用 `mock`）。
- `data.mock_prices`：mock last_price（盘后评估/盘前建议的降级数据）。
- `data.market_data_cache_dir`：缓存日线 CSV 的目录（用于 market-state 等）。
- `data.market_universe_snapshot_dir`：候选池快照目录（主要用于回测链路初始化 SnapshotService 的 base_dir；当前 Stage 4 盘前链路使用 `SnapshotService()` 默认目录 `data/market_universe/snapshots`）。

### 5.5 crawl

- `crawl.auth.<site>.cookie`：站点 cookie。
- `crawl.sources[]`：抓取源配置。
	- `author_id / author_name / list_url`：作者与列表页。
	- `enabled`：是否启用。
	- `render_js`：是否启用 Playwright 动态渲染（启用则需要安装 Playwright 浏览器）。
- `crawl.throttling.*`：抓取节流与退避重试。

### 5.6 storage

- `storage.output_dir`：盘前/盘后/信号/evidence/ranking 等产物的统一落盘目录（默认 `data/processed/phase0`）。

### 5.7 persona

- `persona.enable`：是否启用 persona style routing。
- `persona.clusters_path`：clusters 文件路径（可用 `persona-init-sample` 或 `clusters-build` 生成）。
- `persona.top_k`：输出 top-k。
- `persona.market_state_*`：市场状态输入来源（JSON 或 benchmark 日线 CSV/缓存）。

### 5.8 stage4

- `stage4.enable`：是否启用 Stage 4 盘前主链路（策略版本 + 候选池快照）。
- `stage4.market_universe_slot`：盘前读取快照的 slot（默认 `09-25`）。
- `stage4.allow_phase0_fallback`：当策略版本/快照不可用时，是否允许降级到 Phase 0（watchlist + last_price）。

### 5.9 api

- `api.host / api.port`：API 服务监听配置。
- `api.timeout_seconds`：`/run/*` 触发接口的超时（0 表示不限制）。
- `api.auth.enabled / api.auth.api_keys`：`X-API-Key` 鉴权配置。
	- 对 `src/api/main.py` 入口生效（使用 `src/api/dependencies.py:verify_api_key`）。
	- 对 `api/main.py`（`api/routers/*`）入口当前不强制生效（后续可扩展为统一鉴权）。

### 5.10 kaipan

- `kaipan.data_dir`：Kaipan 数据根目录（raw/snapshots）。
- `kaipan.schema_dir`：Kaipan schema 目录。
- `kaipan.token / kaipan.user_id`：可选鉴权。
- `kaipan.fetch_schedule.*`：Kaipan scheduler 的抓取时间。
- `kaipan.*retries*`：重试与反爬节流。

### 5.11 akshare

- `akshare.min_request_interval_seconds`：最小请求间隔（秒），避免连续请求触发东方财富反爬（默认 `1.0`）。
- `akshare.max_retries`：请求失败后的重试次数（默认 `2`）。
- `akshare.retry_backoff_seconds`：重试退避时间序列（秒），按序使用，超出索引则取最后一个值（默认 `[1.0, 3.0]`）。
- `akshare.fallback_enabled`：东方财富源失败后，是否自动降级到新浪源（仅 A 股 stock 类型生效，默认 `true`）。

说明：这些参数影响 `ohlcv crawl` 等 AkShare 数据抓取命令的请求节奏。如果抓取时频繁出现 `RemoteDisconnected` 或连接中断，系统会在东方财富源重试失败后自动尝试新浪源（fallback），无需手动干预。如需关闭 fallback，可将 `fallback_enabled` 设为 `false`。

### 5.11 alerting / dashboard（可选）

- `alerting.*`：告警推送相关配置（FastAPI `/alerts/*` 主要用于查询历史与状态；实际推送由告警模块读取此配置）。
	- `alerting.enabled`：是否启用
	- `alerting.channel`：`dingtalk` / `feishu` / `wecom` / `generic`
	- `alerting.*.webhook_url/secret`：对应平台机器人 Webhook
	- `alerting.min_level`：最低告警等级（如 `WARNING`）

- `dashboard.*`：数据监控 Dashboard 的阈值与输出目录（当前 `AppConfig` 未显式声明该字段，因此 Dashboard CLI 使用代码内默认阈值；未来如扩展配置 schema 后可生效）。

---

## 6. 结果与中间文件在哪里看

### 6.1 日志

统一日志默认写入：

- `logs/app.log`（RotatingFileHandler，默认 10MB 轮转，保留 5 份）

CLI 大多数命令还会把 INFO 级别打印到控制台。

### 6.2 数据 Pipeline 中间产物（文件模式）

| 阶段 | 典型路径 | 说明 |
|---|---|---|
| crawl | `data/processed/crawl/{source}/{author_id}/articles.jsonl` | 原始抓取 JSONL（文件模式） |
| crawl state | `data/processed/crawl/{source}/{author_id}/state.json` | 增量抓取状态（文件模式） |
| clean | `data/processed/pipeline/clean/*.articles.cleaned.jsonl` | 清洗后 JSONL |
| validate | `data/processed/pipeline/validate/*.validated.jsonl` | 校验后 JSONL |
| process pending | `data/processed/pipeline/pending_tasks.jsonl` | 待处理任务（抽取后写入） |
| export | `data/processed/duckdb/trade_strategy_ai.duckdb` | DuckDB 导出文件 |

> 若使用 `--use-db`：crawl/raw 会写入数据库 `raw_articles`，增量状态写 `crawl_state` 表。

### 6.2.1 规则池相关数据（数据库表）

`extract-articles` 命令执行后，结果写入以下数据库表（详见 `docs/bak/db-struct.md`）：

| 表 | 内容 |
|---|---|
| `article_classification` | 文章类型分类结果（rule/record/mixed/concept/noise） |
| `article_metadata` | 文章元数据（概念、标的、规则、前置条件、情绪） |
| `rule_pool` | 提取的规则（含置信度、审核状态、回测结果） |
| `trade_sample` | 从 record/mixed 文章提取的交易记录样本 |

查看方式：
```bash
python -m cli.main rule-pool list --limit 50
python -m cli.main rule-pool show --rule-id <RULE_ID>
```

### 6.3 盘前/盘后产物（统一在 `storage.output_dir`）

默认输出目录：`data/processed/phase0`（可配置）。

| 产物 | 文件/目录 | 说明 |
|---|---|---|
| 盘前日报 | `daily_report_YYYY-MM-DD.json` | 盘前生成 |
| 盘前日报 HTML | `daily_report_YYYY-MM-DD.html` | `--export-html` 生成 |
| 盘后考核 | `evaluation_YYYY-MM-DD.json` | 盘后生成 |
| 盘后考核 HTML | `evaluation_YYYY-MM-DD.html` | `--export-html` 生成 |
| persona route | `persona_route_YYYY-MM-DD.json` | persona.enable 且 clusters 存在时生成 |
| signals | `signals/idea_{idea_id}.json` | 信号版本（含上下文） |
| evidence packs | `evidence_packs/{pack_id}.json` | 证据包（用于追溯/归因/ranking） |
| evidence index | `evidence_packs/evidence_pack_index.json` | idea_id → pack_id 索引 |
| ranking 文件 | `rankings/YYYY-MM-DD.json` | 盘后生成的 ranking 输出 |
| agent tasks | `agent_tasks.jsonl` | 编排过程中的结构化任务日志 |

### 6.4 市场候选池快照

- `data/market_universe/snapshots/{YYYY-MM-DD}/{slot}.json`

该目录也被 API `/snapshots/*` 路由用于查询/下载。

### 6.5 Kaipan 数据资产

Kaipan 的三层目录结构（raw 与 snapshots）：

```text
data/kaipan/
	raw/
		{dataset}/{YYYY-MM-DD}_{slot}/{api_name}.json
	snapshots/
		{dataset}/{YYYY-MM-DD}_{slot}/{dataset}.json
```

### 6.6 数据监控 Dashboard 产物（可选）

- HTML 默认输出：`data/processed/dashboard/dashboard.html`
- 异常报告目录（Dashboard 读取/写入相关明细）：`data/processed/pipeline/anomaly/`

---

## 7. 如何进行调优/优化

本项目的“调优”主要包括三类：

1. **数据与抽取质量调优**（提升规则/前置条件的结构化质量）
2. **回测/验真**（验证规则是否可程序化、是否有效）
3. **生成候选策略版本**（不直接覆盖 released，先生成 candidate）

### 7.1 文章→规则完整链路（端到端）

从文章到可用于预测的规则，完整链路分为 4 步。每步都是自动化的，但可以人工干预。

#### Step 1: 文章提取（自动分类 + 提取 + 入库 + 审核）

```bash
python -m cli.main extract-articles --config config/app.yaml --limit 50
```

这一条命令内部自动完成：
1. **文章分类**：LLM 将文章分为 rule/record/mixed/concept/noise 五类 → 写入 `article_classification` 表
2. **元数据提取**：LLM 提取概念、标的、交易规则、前置条件、情绪分数
3. **分层落库**（按文章类型分流）：
   - `rule` → 提取 standalone rules → 写入 `rule_pool` 表 → `standalone_rule_ids`
   - `record` → 提取 trade samples → 写入 `trade_sample` 表 + 反推 derived rules → `derived_rule_ids`
   - `mixed` → 同时提取规则 + 交易样本
   - `concept`/`noise` → 跳过
4. **自动审核**（入库后立即执行）：
   - `confidence >= 0.7` 且规则有可映射条件 → **自动 APPROVED**
   - `confidence < 0.2` → **自动 REJECTED**
   - 中间 → 保持 **PENDING**（等待人工审核）

产物与日志：
- 错误日志（JSONL）：`data/processed/llm_extraction_errors.jsonl`
- 断点文件（JSONL）：`data/processed/pipeline/llm_checkpoint.jsonl`

#### Step 2: 查看与人工审核

```bash
# 查看待审核的规则
python -m cli.main rule-pool list --status pending --limit 50

# 查看单条规则完整详情（提取层、回测结果、审核状态）
python -m cli.main rule-pool show --rule-id <RULE_ID>

# 单条审核
python -m cli.main rule-pool review --rule-id <RULE_ID> --decision approve

# 批量审核
python -m cli.main rule-pool review-batch --decision approve --status pending --limit 50

# 只看已审核通过且有映射条件的规则（可直接回测）
python -m cli.main rule-pool list --status approved --skip-no-mapped
```

#### Step 3: 规则回测（自动调度 + 结果查看）

规则回测由调度器自动执行（每周日凌晨），使用真实 OHLCV/指标数据评估每条规则的命中率和 T+1 收益。

回测结果自动写回 `rule_pool` 表（`backtest_result`/`backtest_hits`/`validated_confidence` 字段），可通过 `rule-pool show` 查看。

```bash
# 查看规则的回测结果
python -m cli.main rule-pool show --rule-id <RULE_ID>
# 输出中查看 "回测结果" 和 "置信度" 段落：
#   validated_confidence ← 回测后的多指标综合置信度
#   hit_rate / avg_return / sharpe_ratio / max_drawdown
```

#### Step 4: 预测与归因（高置信度规则参与）

- `validated_confidence >= 0.8`（A 级）→ 自动进入盘前预测池
- 盘后归因记录预测命中/失效 → 更新 `backtest_hits`/`backtest_misses` → 触发置信度重算

### 7.2 trader 策略回测与规则验真

trader 层面的回测（基于 `strategy_version.rules_snapshot`，不同于 rule_pool）：

```bash
python -m cli.main backtest run --trader trader_a --from 2026-04-01 --to 2026-04-20 --format json --output data/processed/backtest/trader_a_2026-04-01_2026-04-20.json
```

规则验真：

```bash
python -m cli.main backtest validate-rules --trader trader_a --from 2026-04-01 --to 2026-04-20 --output data/processed/backtest/trader_a_validate_rules.md
```

#### A 股交易约束

回测引擎内置 A 股规则校验，自动根据股票代码推断板块类型和涨跌停幅度：

| 板块 | 代码前缀 | 涨跌幅限制 |
|---|---|---|
| 上海主板 | 600/601/603/605 | ±10% |
| 深圳主板 | 000/001/002/003 | ±10% |
| 科创板 | 688 | ±20% |
| 创业板 | 300/301 | ±20% |
| 北交所 | 8/4 开头 | ±30%（预留） |
| ST 股票 | 含 ST | ±5%（沪市 2026-07-06 起调整为 ±10%） |

额外约束：
- **T+1**：买入当日不能卖出
- **新股前 5 日**：无涨跌幅限制
- **价格笼子**：申报价格不超过基准价的 102%/98%（北交所 105%/95%）
- **一字板识别**：区分真实停牌与涨跌停锁死，回测评分中分别记录
- **停牌跳过**：volume==0 且价格无波动 → 不参与 MFE/MAE 计算

回测评分输出中包含 `halted_dates`（停牌日）和 `limit_locked_dates`（一字板日），便于事后审查。

### 7.3 风控账户快照

`ManagerAgent` 在评估交易信号时，优先从 `trade_logs` 表构建真实账户快照。

前置步骤：导入交易记录。

```bash
python -m cli.main import-trade-logs --config config/app.yaml --csv-path /path/to/trades.csv
```

导入后，`evaluate_signal()` 内部自动：
- 按 `account_id` 聚合历史交易，计算当前持仓、平均成本、浮动盈亏
- 从 `ohlcv_bars` 获取最新收盘价估算持仓市值
- 无交易记录或查询失败时 fallback 到模拟账户（初始资金 100,000）

### 7.4 trader 筛选与策略建议（optimize）

活跃 trader 筛选：

```bash
python -m cli.main optimize filter --file data/processed/backtest/*.json --min-trades 10 --min-win-rate 0.40
```

基于规则验真结果生成策略调整建议（需要 RuleValidationResult JSON 作为输入）：

```bash
python -m cli.main optimize advise --file /path/to/rule_validation.json --output data/processed/optimize/advise.json
```

生成候选版本（文件链路）：

> 提示：文件链路需要你准备一份“正式版本 JSON”（`--parent`）。项目目前没有单独的 CLI 直接导出 released_version.json；通常更推荐使用下面的 DB 链路。

```bash
python -m cli.main optimize create-candidate \
	--parent data/processed/strategy/released_version.json \
	--adjustments data/processed/optimize/advise.json \
	--output data/processed/strategy/candidate_version.json
```

生成候选版本（DB 链路，推荐）：

```bash
python -m cli.main optimize create-candidate --db --trader trader_a --date 2026-04-29 --adjustments data/processed/optimize/advise.json
```

### 7.5 规则池管理命令速查（rule-pool）

```bash
# 查看详情
python -m cli.main rule-pool show --rule-id <RULE_ID>

# 列出规则（支持 --status/--rule-type/--skip-no-mapped 过滤）
python -m cli.main rule-pool list --status approved --skip-no-mapped --limit 50

# 单条审核 (approve/reject/pending)
python -m cli.main rule-pool review --rule-id <RULE_ID> --decision approve

# 批量审核
python -m cli.main rule-pool review-batch --decision approve --status pending --limit 50

# 强制覆盖自动审核结果
python -m cli.main rule-pool review --rule-id <RULE_ID> --decision reject --force
```

---

## 8. 常见问题与日志排障

### 8.1 数据库连接失败

现象：`db-check` 报错，或 pipeline/store/strategy/ranking 相关命令报连接错误。

处理步骤：

1）确认数据库进程在运行（本机或 Docker）。

2）确认 `DATABASE_URL` 正确：

```bash
echo "$DATABASE_URL"
```

3）运行连通性校验：

```bash
python -m cli.main db-check --config config/app.yaml
```

### 8.2 爬虫 403 / 429 / 未登录态

现象：抓取时出现 `HTTP 403/429` 或提示登录/验证页面。

原因与处理：

- Cookie 失效或未注入：更新 Cookie，并确保 `crawl.auth.tgb.cn.cookie` 读取到了它（推荐 YAML 写 `"${TGB_COOKIE}"`）。
- 被限流：调大 `crawl.throttling.min_interval_seconds/max_interval_seconds`，并观察退避策略是否生效。

### 8.3 `extract-articles` 提示 prompts 缺失

现象：`prompts dir not found`。

处理：确保项目根目录下存在 `prompts/`（仓库已包含），并从项目根目录运行命令（或确保 `--config` 在正确的相对路径）。

### 8.4 盘后评估缺少盘前日报

现象：`run-after-close` 报错 `Daily report not found`。

处理：先运行盘前：

```bash
python -m cli.main run-pre-market --config config/app.yaml
```

### 8.5 Stage 4 快照缺失导致盘前候选池为空

现象：日志里出现 `failed to load market universe snapshot`，盘前建议退化。

处理：确保对应日期与 slot 的快照已生成：

```bash
python -m cli.main snapshot build --date 2026-04-29 --slot 09-25 --type all
```

或者在 `config` 中允许降级（默认允许）：`stage4.allow_phase0_fallback=true`。

### 8.6 OHLCV 抓取频繁失败（RemoteDisconnected）

现象：`ohlcv crawl` 日志中大量 `RemoteDisconnected` / `Connection aborted` 警告。

原因：AKShare 底层访问东方财富接口，短时间内高频请求被限流。

处理：

1）确认 fallback 已启用：默认 `akshare.fallback_enabled: true`，东方财富重试失败后会自动降级到新浪源，日志中会看到 `新浪源 fallback 成功` 提示。

2）增大请求间隔：修改 `config/app.yaml` 中 `akshare.min_request_interval_seconds`（如从 `0.5` 改为 `1.0` 或更大）。

3）增大重试退避：调整 `akshare.retry_backoff_seconds`（如改为 `[2.0, 5.0]`）。

4）减少单次抓取量：使用 `--limit` 减少标的数量，分批执行。

5）如果 fallback 后仍全部失败，可能是网络问题，检查网络连接后重试。

### 8.7 日志如何定位

1）优先看 `logs/app.log`。

2）提高 CLI 输出日志等级（很多命令有 `--log-level`）：

```bash
python -m cli.main pipeline-run --config config/app.yaml --log-level DEBUG
```

---

## 9. 其他重要信息

### 9.1 安全与密钥

- 不要把 Cookie/API Key 明文提交到仓库。
- 推荐做法：
	- 在 `config/app.yaml` 用 `"${ENV_VAR}"` 占位
	- 在本地 `.env` 或 shell 环境变量中注入真实值

### 9.2 目录与相对路径

很多命令默认使用相对路径（例如 `config/app.yaml`、`data/...`）。建议：

- 在 `trade-strategy-ai/` 项目根目录执行命令
- 或者为 `--config` 提供绝对路径，并理解输出目录相对 base_dir 的解析规则

### 9.3 测试与冒烟验证

项目提供了 `Makefile` 的 smoke gate：

```bash
make smoke
```

也可以直接运行 pytest：

```bash
pytest -q
```
