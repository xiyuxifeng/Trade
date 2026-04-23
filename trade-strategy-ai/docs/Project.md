# 📁 AI 交易策略反推与 Agent 系统 — 项目结构

## 项目名称：`trade-strategy-ai`

本项目将同时支持两种运行形态（共享同一套核心应用层，避免逻辑分叉）：
- 交互式模式：通过 CLI/脚本手动触发盘前/盘后任务，便于快速迭代
- 长期运行模式：作为独立程序运行（FastAPI + scheduler/worker），按配置定时自动跑批

当前主线已收敛为：

`数据快照 -> provider -> 市场候选池 -> per-trader 策略版本 -> 盘前决策 -> 盘后评估/归因 -> 回测优化`

说明：

- 本文档的定位是“项目结构说明”，不是任务清单。
- 当前唯一主清单是 `docs/TaskList.md`。
- `Project.md / Plan.md / 需求.md` 是当前有效文档入口；历史方案和旧任务文档已迁移到 `docs/bak` 与 `docs/Deprecated`。

---

## 一、项目目录结构

```
trade-strategy-ai/
├── README.md                          # 项目说明
├── pyproject.toml                     # Python 项目配置
├── Makefile                           # 常用命令入口
├── docker-compose.yml                 # 本地基础设施编排
├── Dockerfile                         # 容器镜像构建
├── .env.example                       # 环境变量模板
├── config/                            # 配置文件与规则配置
├── daily-sessions/                    # 短期会话记录
├── daily-report/                      # 长期日报记录
├── docs/                              # 当前文档入口 + 历史归档
│   ├── Project.md
│   ├── Plan.md
│   ├── 需求.md
│   ├── TaskList.md
│   ├── Kaipan-Interface-Mapping.md
│   ├── bak/
│   ├── Deprecated/
│   └── superpowers/
├── data/                              # 本地数据与样本
│   ├── patterns/
│   ├── processed/
│   ├── samples/
│   └── signals/
├── tools/                             # 外部接口文档与辅助工具
├── prompts/                           # LLM Prompt 模板
├── scripts/                           # 运维与批处理脚本
├── deploy/                            # docker / k8s / monitoring
├── api/                               # FastAPI 入口与路由
├── cli/                               # 命令行入口
├── src/                               # 核心源码
│   ├── agents/                        # 长期 Agent 与历史 Agent 目录
│   ├── providers/                     # 数据源 provider 抽象
│   ├── market_data/                   # 行情同步与缓存
│   ├── trader_profile/                # 交易员画像
│   ├── trader_memory/                 # 交易员记忆
│   ├── strategy/                      # 策略、信号版本、规则执行
│   ├── risk/                          # 风控规则与风险评估
│   ├── persona/                       # 风格画像与路由
│   ├── pipeline/                      # 数据处理管线
│   ├── reporting/                     # 报告生成
│   ├── dsl/                           # DSL 解析与执行
│   ├── indicators/                    # 技术指标
│   ├── features/                      # 特征工程
│   ├── db/                            # 数据访问与迁移
│   ├── models/                        # ORM 模型
│   ├── schemas/                       # Pydantic 契约
│   ├── common/                        # 公共工具与配置封装
│   ├── api/                           # 应用内 API 适配层
│   ├── llm/                           # LLM 调用封装
│   ├── host/                          # 宿主接口层
│   ├── alerting/                      # 告警
│   ├── health/                        # 健康检查
│   ├── audit/                         # 审计日志
│   ├── backup/                        # 备份工具
│   ├── logging/                       # 日志模块
│   ├── shared/                        # 共享基础能力
│   ├── knowledge/                     # 历史知识模块
│   ├── alignment/                     # 历史对齐模块
│   └── agent_net/                     # 历史多 Agent 实验目录
└── tests/                             # 单元 / 集成 / E2E 测试
```

---

  ## 二、关键设计约定（面向新需求）

  ### 1）配置驱动（不写死）
  盘前/盘后时间、收益阈值等关键参数必须来自配置（建议 YAML + 环境变量覆盖），例如：
  - `schedule.enable`
  - `schedule.pre_market_time`
  - `schedule.after_close_time`
  - `evaluation.min_expected_return`

  ### 2）DataAgent 以 skills 扩展能力
  DataAgent 对外提供统一的 DataRequest/DataResponse 接口，内部通过 skills 注册表路由到具体数据能力；当能力缺失时返回 `capability_missing`，由 Manager 记录为待办任务。

  ### 3）日常运行闭环产物
  系统将产生两类核心产物（建议落库）：
  - 盘前：Trader 的 TradeIdea + Manager 的 DailyReport
  - 盘后：EvaluationResult + 触发的复盘报告（写回 Trader 记忆）

  ---

## 三、核心模块说明

### 3.1 Agent 层（`src/agents/`）

所有 Agent 继承自 `base.py` 中的 `BaseAgent`，统一接口：

```python
class BaseAgent:
    """Agent 基类"""

    def __init__(self, name: str, config: AgentConfig):
        self.name = name
        self.config = config
        self.skills: dict[str, Skill] = {}

    async def execute(self, task: Task) -> Result:
        """执行任务的入口方法"""
        ...

    def register_skill(self, skill: Skill):
        """注册技能"""
        ...

    async def call_skill(self, skill_name: str, **kwargs) -> Any:
        """调用指定技能"""
        ...
```

**当前 Agent 列表与职责：**

| Agent | 目录 | 当前定位 | 状态 |
|-------|------|------|------|
| Manager Agent | `manager_agent/` | 主流程编排、盘前输出、盘后评分、复盘触发 | 保留为长期 Agent（NTL-S15-001） |
| Data Agent | `data_agent/` | capability router，统一对外数据契约 | 保留为长期 Agent（NTL-S15-002） |
| Trader Agent | `trader_agent/` | per-trader 决策执行 | 保留为长期 Agent（NTL-S15-003） |
| Strategy Agent | `strategy_agent/` | 规则评估与信号合成 | 保留（边界待定义 NTL-S15-004） |
| Risk Agent | `risk_agent/` | 风险过滤 | 保留（边界待定义 NTL-S15-005） |
| Knowledge Agent | `knowledge_agent/` | 文章理解相关历史目录 | 已冻结主线（NTL-S15-006） |
| Behavior Agent | `behavior_agent/` | 行为分析相关历史目录 | 已冻结主线（NTL-S15-007） |
| Alignment Agent | `alignment_agent/` | 旧对齐分析主线 | 已冻结（NTL-S15-009） |
| Backtest Agent | `backtest_agent/` | 历史回测 Agent 目录 | 已冻结主线（NTL-S15-008） |

**Agent 状态说明：**
- **保留为长期 Agent**：长期保留在 `src/agents/` 中，承担明确职责，不继续堆叠业务逻辑
- **保留（边界待定义）**：保留但具体边界在对应 NTL-S15-00X 任务中定义
- **已冻结主线**：不再作为当前核心交付路径；目录保留为历史参考；代码不再主动扩展

### 3.1.1 当前推荐的主线模块

围绕当前目标，后续长期核心模块应是：

- `src/providers`
- `src/market_universe`
- `src/strategy_library`
- `src/evaluation`
- `src/backtest`
- `src/agents/manager_agent`
- `src/agents/data_agent`
- `src/agents/trader_agent`
- `src/agents/strategy_agent`
- `src/agents/risk_agent`

### 3.2 DSL 引擎（`src/dsl/`）

策略 DSL（Domain Specific Language）用于将自然语言策略描述转换为可执行的交易规则。

**DSL 示例格式（YAML）：**

```yaml
strategy:
  name: "trend_follow_v1"
  version: "1.0"
  preconditions:
    - market_trend: "up"
    - sector_momentum: "> 0"
  rules:
    - id: "buy_rule_1"
      type: "entry"
      condition:
        indicator: "MA5"
        operator: "cross_above"
        reference: "MA20"
      action:
        type: "BUY"
        position: 0.3
    - id: "sell_rule_1"
      type: "exit"
      condition:
        indicator: "price"
        operator: "drop_below"
        reference: "MA20"
      action:
        type: "SELL"
        position: 1.0
  risk:
    max_position: 0.5
    stop_loss: 0.08
    max_drawdown: 0.15
```

**处理流程：**
```
文章文本 → LLM 提取 → YAML DSL → Parser 解析 → Compiler 编译 → Executor 执行
```

### 2.3 特征工程（`src/features/`）

| 模块 | 功能 | 关键指标 |
|------|------|---------|
| `technical.py` | 技术指标 | MA, EMA, MACD, RSI, Bollinger, KDJ, ATR |
| `fundamental.py` | 基本面 | PE, PB, ROE, 涨速 |
| `timeseries.py` | 时间序列 | 趋势强度, 波动率, 自相关, Hurst 指数 |
| `trade_stats.py` | 交易统计 | 胜率, 盈亏比, 夏普比, 最大回撤, 期望值 |
| `normalizer.py` | 特征处理 | Min-Max, Z-Score, 分位数归一化 |

### 2.4 数据管道（`src/pipeline/`）

```
crawl_task → clean_task → validate_task → feature_task → export_task
     ↓            ↓            ↓              ↓             ↓
  原始数据     清洗数据      验证报告      特征矩阵      导出文件
```

### 2.5 API 层（`api/`）

基于 FastAPI 构建 RESTful API：

| 路由模块 | 路径前缀 | 功能 |
|---------|---------|------|
| `blog.py` | `/api/v1/blog` | 博客数据 CRUD |
| `trade.py` | `/api/v1/trade` | 交易记录 CRUD |
| `market.py` | `/api/v1/market` | 市场数据查询 |
| `strategy.py` | `/api/v1/strategy` | 策略 DSL 管理 |
| `alignment.py` | `/api/v1/alignment` | 对齐分析触发与查询 |
| `signal.py` | `/api/v1/signal` | 交易信号查询 |
| `backtest.py` | `/api/v1/backtest` | 回测任务与报告 |
| `health.py` | `/api/v1/health` | 健康检查 |

---

## 三、数据模型设计

### 3.1 数据库 ER 关系

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  blog_articles   │     │   trade_logs      │     │  market_data      │
├─────────────────┤     ├──────────────────┤     ├──────────────────┤
│ id (PK)          │     │ id (PK)           │     │ id (PK)           │
│ title            │     │ stock_code        │     │ stock_code        │
│ content          │     │ direction         │     │ date              │
│ publish_date     │     │ price             │     │ open              │
│ tags             │     │ volume            │     │ high              │
│ source_url       │     │ position          │     │ low               │
│ created_at       │     │ trade_time        │     │ close             │
│ updated_at       │     │ notes             │     │ volume            │
└────────┬────────┘     │ created_at        │     │ amount            │
         │              └──────────────────┘     │ created_at        │
         ↓                                        └──────────────────┘
┌─────────────────┐     ┌──────────────────┐
│ article_metadata │     │  strategy_dsl     │
├─────────────────┤     ├──────────────────┤
│ id (PK)          │     │ id (PK)           │
│ article_id (FK)  │     │ name              │
│ concepts         │     │ version           │
│ rules_json       │     │ dsl_content       │
│ preconditions    │     │ source_article_id │
│ confidence       │     │ confidence_score  │
│ created_at       │     │ is_active         │
└─────────────────┘     │ created_at        │
                         └──────────────────┘
┌─────────────────┐     ┌──────────────────┐
│ alignment_result │     │  trade_signals    │
├─────────────────┤     ├──────────────────┤
│ id (PK)          │     │ id (PK)           │
│ strategy_id (FK) │     │ strategy_id (FK)  │
│ rule_match_score │     │ stock_code        │
│ behavior_fit     │     │ signal_type       │
│ conflict_count   │     │ confidence        │
│ confidence_score │     │ position_size     │
│ report_json      │     │ risk_check_passed │
│ created_at       │     │ generated_at      │
└─────────────────┘     └──────────────────┘
```

### 3.2 核心表说明

| 表名 | 用途 | 数据量级 |
|------|------|---------|
| `blog_articles` | 存储爬取的博客文章 | 千级 |
| `trade_logs` | 存储交易记录 | 万级 |
| `market_data` | 存储股票 K 线数据 | 百万级 |
| `article_metadata` | 文章经 NLP 处理后的元数据 | 千级 |
| `strategy_dsl` | 生成的策略 DSL | 百级 |
| `alignment_result` | 策略对齐结果 | 百级 |
| `trade_signals` | 生成的交易信号 | 万级 |

---

## 四、Agent 交互流程

```
                          ┌─────────────────────────────────┐
                          │        Coordinator               │
                          │   (多 Agent 调度协调器)           │
                          └──────────┬──────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              ↓                      ↓                      ↓
    ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
    │  Data Agent      │   │ Knowledge Agent │   │ Behavior Agent  │
    │  ─────────────   │   │  ─────────────  │   │  ─────────────  │
    │  crawl_blog      │   │  extract_rules  │   │  label_behavior │
    │  fetch_market    │   │  build_dsl      │   │  clustering     │
    │  store_db        │   │                 │   │                 │
    └────────┬────────┘   └────────┬────────┘   └────────┬────────┘
             │                     │                     │
             ↓                     └──────────┬──────────┘
       ┌───────────┐                          ↓
       │    DB     │               ┌─────────────────┐
       └───────────┘               │ Alignment Agent  │
                                   │  ⭐ 核心对齐     │
                                   │  confidence_score│
                                   └────────┬────────┘
                                            ↓
                                 ┌─────────────────┐
                                 │ Strategy Agent   │
                                 │  generate_signal │
                                 └────────┬────────┘
                                          ↓
                                 ┌─────────────────┐
                                 │   Risk Agent     │
                                 │  position_sizing │
                                 │  stop_loss       │
                                 └────────┬────────┘
                                          ↓
                                 ┌─────────────────┐
                                 │  Signal Output   │
                                 │  BUY/SELL/HOLD   │
                                 └─────────────────┘

            (旁路验证)
                                 ┌─────────────────┐
                                 │ Backtest Agent   │
                                 │  run_backtest    │
                                 │  evaluate_metrics│
                                 └─────────────────┘
```

---

## 五、技术栈对照表

| 层级 | 技术选型 | 用途 |
|------|---------|------|
| **语言** | Python 3.11+ | 主开发语言 |
| **Web 框架** | FastAPI | REST API |
| **ORM** | SQLAlchemy 2.0 | 数据库 ORM |
| **数据库** | PostgreSQL 15 | 主数据库 |
| **分析引擎** | DuckDB | OLAP 分析 |
| **列存储** | Parquet (via PyArrow) | 大数据存储 |
| **缓存** | Redis | 热数据缓存 |
| **爬虫** | Playwright + BeautifulSoup | 网页抓取 |
| **LLM** | OpenAI / Claude API | 文章理解 |
| **数据处理** | pandas / polars | 数据清洗 |
| **ML** | scikit-learn | 聚类、特征工程 |
| **统计** | statsmodels | 统计分析 |
| **DSL** | Lark | 语法解析 |
| **回测** | backtesting.py / VectorBT | 策略回测 |
| **任务调度** | Airflow / 自研 DAG | 数据管道 |
| **CLI** | Typer | 命令行工具 |
| **测试** | pytest + pytest-asyncio | 自动化测试 |
| **容器** | Docker + Docker Compose（可选） | 可选的本地/部署形态 |
| **编排** | Kubernetes | 生产部署 |
| **监控** | Prometheus + Grafana | 系统监控 |
| **日志** | structlog | 结构化日志 |

---

## 六、环境配置

### 6.1 开发环境依赖

```toml
# pyproject.toml 核心依赖
[project]
name = "trade-strategy-ai"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    # Web
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    # Database
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "alembic>=1.13",
    "duckdb>=0.10",
    "redis>=5.0",
    # Data
    "pandas>=2.2",
    "polars>=0.20",
    "pyarrow>=15.0",
    # Crawling
    "playwright>=1.42",
    "beautifulsoup4>=4.12",
    "lxml>=5.1",
    # AI/ML
    "openai>=1.12",
    "anthropic>=0.18",
    "scikit-learn>=1.4",
    "statsmodels>=0.14",
    # DSL
    "lark>=1.1",
    # Backtest
    "backtesting>=0.3",
    # Utils
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "typer>=0.9",
    "structlog>=24.1",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",
    "ruff>=0.3",
    "mypy>=1.8",
]
```

### 6.2（可选）Docker Compose 服务

```yaml
services:
  db:            # PostgreSQL 数据库    → :5432
  redis:         # Redis 缓存（可选）   → :6379
```

### 6.3 环境变量

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai
REDIS_URL=redis://localhost:6379/0
LOG_LEVEL=INFO
# TGB_COOKIE=xxx
# LLM_PROVIDER=openai|anthropic|openai_compatible
# LLM_MODEL=gpt-4.1-mini
# LLM_URL=https://api.openai.com/v1
# LLM_API_KEY=xxx
```

---

## 七、开发规范

### 7.1 代码规范
- **格式化**：Ruff（替代 black + isort + flake8）
- **类型检查**：mypy strict mode
- **命名**：snake_case（函数/变量），PascalCase（类）
- **docstring**：Google Style

### 7.2 Git 规范
- **分支策略**：`main` → `develop` → `feature/xxx`
- **Commit 格式**：`feat(agent): add knowledge agent`
  - 类型：`feat` / `fix` / `refactor` / `test` / `docs` / `chore`
- **PR 规则**：至少 1 人 review + CI 通过

### 7.3 测试规范
- 单元测试覆盖率 ≥ 80%
- 集成测试覆盖关键 Agent 交互路径
- 使用 Factory 模式生成测试数据

---

## 八、快速启动

```bash
# 1. 克隆项目
git clone <repo-url> && cd trade-strategy-ai

# 2. 安装依赖
pip install -e ".[dev]"

# 3. 准备本地 PostgreSQL（推荐本机安装；Docker 仅作为可选方案）
# macOS 示例：
#   brew install postgresql@15
#   brew services start postgresql@15
# 创建数据库与用户（示例：trade/trade）：
#   psql postgres -c "CREATE ROLE trade WITH LOGIN PASSWORD 'trade';"
#   createdb -O trade trade_strategy_ai

# 4. 配置数据库连接
cp .env.example .env
# 在 .env 中设置 DATABASE_URL，例如：
#   DATABASE_URL=postgresql+asyncpg://trade:trade@localhost:5432/trade_strategy_ai

# 5. 初始化/迁移数据库
python -m cli.main db-migrate --config config/app.yaml

# 6. 运行 API
uvicorn api.main:app --reload

# 7. 运行测试
pytest tests/ -v --cov=src
```
