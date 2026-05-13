# trade-strategy-ai

## 系统介绍

trade-strategy-ai 是一个面向“多交易员文章 + 交易记录”的多 Agent 交易研究与复盘系统。

## 项目目标

1. 支持多交易员独立分析与复盘。
2. 通过多智能体协作，实现自动化数据处理、策略分析与报告生成。
3. 强化盘前/盘后总结、考核与反馈闭环。
4. 兼容第三方大模型 API，提升智能分析能力。

## 本地安装（无 Docker）

前置：Python 3.11+。

推荐在 workspace 根目录创建统一虚拟环境：

```bash
cd ..
python -m venv .venv
source .venv/bin/activate

cd trade-strategy-ai
pip install -e ".[dev]"
```

## 配置键（节选）

- `schedule.enable`
- `schedule.pre_market_time`
- `schedule.after_close_time`
- `evaluation.min_expected_return`
- `evaluation.loss_trigger`
- `traders[].watchlist`
- `data.mock_prices`（Phase 0 演示用，后续可接入 akshare/tushare 等）

Phase 0.5（Persona Router MVP，可选）：

- `persona.enable`
- `persona.clusters_path`
- `persona.top_k`

生成样例 clusters 文件：

```bash
python -m cli.main persona-init-sample --config config/app.yaml
```

文档入口：workspace 根目录 `docs/`。

## 数据库与迁移（Phase 1 基础）

准备本地 PostgreSQL（推荐本机安装；Docker 仅作为可选方案）：

- macOS（Homebrew）示例：`brew install postgresql@15 && brew services start postgresql@15`
- 创建数据库与用户（示例：trade/trade）：
	- `psql postgres -c "CREATE ROLE trade WITH LOGIN PASSWORD 'trade';"`
	- `createdb -O trade trade_strategy_ai`

准备环境变量（建议复制一份到 `.env`，不要提交密钥）：

```bash
cp .env.example .env
```

异步连通性校验：

```bash
python -m cli.main db-check --config config/app.yaml
```

执行 Alembic 迁移：

```bash
python -m cli.main db-migrate --config config/app.yaml
```

## Docker / Compose 生产启动

部署拓扑和目录约定见 [docs/WebDeployment.md](docs/WebDeployment.md)。

```bash
docker compose up -d db
docker compose run --rm api python -m cli.main db-migrate --config config/app.yaml
docker compose up -d api worker web
```

常用检查：

```bash
curl http://localhost:8000/health
curl http://localhost:3000/
```

如果需要手动启动 worker：

```bash
python -m cli.main job-worker-start --config config/app.yaml
```

## 本机非 Docker 启动

如果只做单机验证，可以直接用本机 launcher：

```bash
python -m scripts.web_local build
python -m scripts.web_local migrate
python -m scripts.web_local start
```

需要分别启动时：

```bash
python -m scripts.web_local start-api
python -m scripts.web_local start-worker
```

说明：仓库里涉及的 `config/...`、`data/...`、`logs/...` 相对路径，运行时默认按 `trade-strategy-ai` 项目根目录解析，不依赖当前 shell 所在目录。

## 数据 Pipeline（一键链路）

从真实站点抓取 → 清洗 → 校验 → 入库：

```bash
python -m cli.main pipeline-run --config config/app.yaml
```

LLM 抽取 v0（文章抽取已整合到 pipeline-step process 中，未配置 LLM 时会 fallback 并记录 raw_llm_output）：

```bash
python -m cli.main pipeline-step process --config config/app.yaml --new-version v1
```

从真实抽取数据生成 StyleClusters：

```bash
python -m cli.main clusters-build --config config/app.yaml
```

端到端回归（crawl→store→extract→clusters→run-pre-market+HTML）：

```bash
python -m cli.main e2e-regression --config config/app.yaml
```
