# 📁 AI 交易策略反推与 Agent 系统 — 项目结构

## 项目名称：`trade-strategy-ai`

本项目将同时支持两种运行形态（共享同一套核心应用层，避免逻辑分叉）：
- 交互式模式：通过 CLI/脚本手动触发盘前/盘后任务，便于快速迭代
- 长期运行模式：作为独立程序运行（FastAPI + scheduler/worker），按配置定时自动跑批

---

## 一、项目目录结构

```
trade-strategy-ai/
├── README.md                          # 项目说明
├── pyproject.toml                     # Python 项目配置（依赖、构建）
├── Makefile                           # 常用命令快捷方式
├── docker-compose.yml                 # 本地开发环境编排
├── Dockerfile                         # 生产镜像构建
├── .env.example                       # 环境变量模板
├── .gitignore
│
├── config/                            # 全局配置
│   ├── __init__.py
│   ├── settings.py                    # 应用配置（Pydantic Settings）
│   ├── database.py                    # 数据库连接配置
│   ├── redis.py                       # Redis 缓存配置
│   └── logging.py                     # 日志配置
│
├── doc/                               # 项目文档（需求/计划/任务）
│   ├── 需求.md
│   ├── Plan.md
│   ├── Project.md
│   └── TaskList.md
│
├── src/                               # 核心源码
│   ├── __init__.py
│   │
│   ├── common/                        # 公共模块
│   │   ├── __init__.py
│   │   ├── exceptions.py              # 自定义异常
│   │   ├── constants.py               # 全局常量
│   │   ├── types.py                   # 类型定义
│   │   ├── utils.py                   # 通用工具函数
│   │   └── logger.py                  # 日志工具
│   │
│   ├── models/                        # 数据模型（ORM）
│   │   ├── __init__.py
│   │   ├── base.py                    # SQLAlchemy Base
│   │   ├── blog_article.py            # 博客文章模型
│   │   ├── trade_log.py               # 交易记录模型
│   │   ├── market_data.py             # 市场数据模型
│   │   ├── article_metadata.py        # 文章元数据模型
│   │   ├── strategy_dsl.py            # 策略 DSL 模型
│   │   ├── alignment_result.py        # 对齐结果模型
│   │   └── signal.py                  # 交易信号模型
│   │
│   ├── schemas/                       # Pydantic Schema（API 数据校验）
│   │   ├── __init__.py
│   │   ├── blog.py                    # 博客相关 Schema
│   │   ├── trade.py                   # 交易相关 Schema
│   │   ├── market.py                  # 市场数据 Schema
│   │   ├── strategy.py                # 策略 DSL Schema
│   │   ├── alignment.py               # 对齐结果 Schema
│   │   └── signal.py                  # 信号输出 Schema
│   │
│   ├── db/                            # 数据库访问层
│   │   ├── __init__.py
│   │   ├── session.py                 # 数据库会话管理
│   │   ├── repositories/              # Repository 模式
│   │   │   ├── __init__.py
│   │   │   ├── blog_repo.py           # 博客数据访问
│   │   │   ├── trade_repo.py          # 交易数据访问
│   │   │   ├── market_repo.py         # 市场数据访问
│   │   │   ├── strategy_repo.py       # 策略 DSL 访问
│   │   │   └── signal_repo.py         # 信号数据访问
│   │   └── migrations/                # Alembic 数据库迁移
│   │       ├── env.py
│   │       ├── alembic.ini
│   │       └── versions/              # 迁移版本文件
│   │
│   ├── agents/                        # 🤖 Agent 核心模块
│   │   ├── __init__.py
│   │   ├── base.py                    # Agent 基类
│   │   ├── registry.py                # Agent 注册与发现
│   │   ├── coordinator.py             # 多 Agent 调度协调器
│   │   │
│   │   ├── manager_agent/              # 🧾 Manager Agent（编排/汇总/考核/复盘）
│   │   │   ├── __init__.py
│   │   │   └── agent.py
│   │   │
│   │   ├── trader_agent/               # 👤 Trader Agent（每交易员独立画像/记忆/建议）
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   └── templates/              # 交易员提示词模板/策略偏好模板（可选）
│   │   │
│   │   ├── data_agent/                # 📦 Data Agent（数据采集）
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Data Agent 主控
│   │   │   └── skills/
│   │   │       ├── __init__.py
│   │   │       ├── crawl_blog.py      # 博客爬虫
│   │   │       ├── crawl_dynamic.py   # 动态页面爬虫（Playwright）
│   │   │       ├── parse_html.py      # HTML 解析
│   │   │       ├── extract_trade.py   # 交易记录提取
│   │   │       ├── fetch_market.py    # 市场数据获取
│   │   │       └── store_db.py        # 数据入库
│   │   │
│   │   ├── knowledge_agent/           # 📚 Knowledge Agent（文章理解）
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Knowledge Agent 主控
│   │   │   └── skills/
│   │   │       ├── __init__.py
│   │   │       ├── extract_concepts.py    # 概念提取
│   │   │       ├── extract_rules.py       # 买卖规则提取
│   │   │       ├── extract_preconditions.py # 前置条件提取
│   │   │       └── build_strategy_dsl.py  # DSL 构建
│   │   │
│   │   ├── behavior_agent/            # 📈 Behavior Agent（行为分析）
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Behavior Agent 主控
│   │   │   └── skills/
│   │   │       ├── __init__.py
│   │   │       ├── label_behavior.py      # 行为标签化
│   │   │       ├── feature_extraction.py  # 特征提取
│   │   │       ├── pattern_mining.py      # 模式挖掘
│   │   │       └── clustering.py          # 行为聚类
│   │   │
│   │   ├── alignment_agent/           # ⭐ Alignment Agent（核心对齐）
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Alignment Agent 主控
│   │   │   └── skills/
│   │   │       ├── __init__.py
│   │   │       ├── rule_match_score.py    # 规则匹配评分
│   │   │       ├── behavior_fit_score.py  # 行为适配度评分
│   │   │       ├── conflict_detection.py  # 冲突检测
│   │   │       └── confidence_scoring.py  # 综合可信度评分
│   │   │
│   │   ├── strategy_agent/            # 🎯 Strategy Agent（决策引擎）
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Strategy Agent 主控
│   │   │   └── skills/
│   │   │       ├── __init__.py
│   │   │       ├── compute_features.py    # 特征计算
│   │   │       ├── evaluate_rules.py      # 规则评估
│   │   │       ├── combine_scores.py      # 信号合成
│   │   │       └── generate_signal.py     # 信号生成
│   │   │
│   │   ├── risk_agent/                # 🛡️ Risk Agent（风控）
│   │   │   ├── __init__.py
│   │   │   ├── agent.py               # Risk Agent 主控
│   │   │   └── skills/
│   │   │       ├── __init__.py
│   │   │       ├── position_sizing.py     # 头寸管理
│   │   │       ├── stop_loss.py           # 止损策略
│   │   │       └── drawdown_control.py    # 回撤控制
│   │   │
│   │   └── backtest_agent/            # 🧪 Backtest Agent（回测）
│   │       ├── __init__.py
│   │       ├── agent.py               # Backtest Agent 主控
│   │       └── skills/
│   │           ├── __init__.py
│   │           ├── run_backtest.py        # 运行回测
│   │           ├── evaluate_metrics.py    # 绩效评估
│   │           └── parameter_search.py    # 参数优化
│   │
│   ├── dsl/                           # DSL 策略语言引擎
│   │   ├── __init__.py
│   │   ├── grammar.py                 # DSL 语法定义（Lark）
│   │   ├── parser.py                  # DSL 解析器
│   │   ├── compiler.py                # DSL → Python 编译器
│   │   ├── executor.py                # DSL 执行引擎
│   │   ├── validator.py               # DSL 验证器
│   │   └── templates/                 # 策略模板
│   │       ├── base_strategy.yaml
│   │       └── example_strategy.yaml
│   │
│   ├── features/                      # 特征工程模块
│   │   ├── __init__.py
│   │   ├── technical.py               # 技术指标（MA, MACD, RSI, Bollinger）
│   │   ├── fundamental.py             # 基本面指标（PE, PB）
│   │   ├── timeseries.py              # 时间序列特征
│   │   ├── trade_stats.py             # 交易统计特征（胜率、夏普比）
│   │   └── normalizer.py              # 特征归一化/标准化
│   │
│   ├── pipeline/                      # 数据管道
│   │   ├── __init__.py
│   │   ├── dag.py                     # DAG 任务定义
│   │   ├── tasks/                     # 管道任务
│   │   │   ├── __init__.py
│   │   │   ├── crawl_task.py          # 爬虫任务
│   │   │   ├── clean_task.py          # 数据清洗任务
│   │   │   ├── validate_task.py       # 数据验证任务
│   │   │   ├── feature_task.py        # 特征计算任务
│   │   │   └── export_task.py         # 数据导出任务
│   │   └── scheduler.py              # 任务调度器
│   │
│   └── reporting/                     # 报告生成模块
│       ├── __init__.py
│       ├── alignment_report.py        # 对齐报告生成
│       ├── backtest_report.py         # 回测报告生成
│       ├── visualizer.py              # 图表可视化
│       └── templates/                 # 报告 HTML 模板
│           ├── alignment.html
│           └── backtest.html
│
├── api/                               # FastAPI Web 服务
│   ├── __init__.py
│   ├── main.py                        # FastAPI 应用入口
│   ├── deps.py                        # 依赖注入
│   ├── middleware.py                  # 中间件（CORS、日志、限流）
│   └── routers/                       # API 路由
│       ├── __init__.py
│       ├── blog.py                    # 博客数据 API
│       ├── trade.py                   # 交易数据 API
│       ├── market.py                  # 市场数据 API
│       ├── strategy.py                # 策略管理 API
│       ├── alignment.py               # 对齐分析 API
│       ├── signal.py                  # 信号查询 API
│       ├── backtest.py                # 回测 API
│       └── health.py                  # 健康检查 API
│
├── cli/                               # 命令行工具
│   ├── __init__.py
│   ├── main.py                        # CLI 入口（Typer/Click）
│   ├── crawl.py                       # 爬虫命令
│   ├── analyze.py                     # 分析命令
│   ├── backtest.py                    # 回测命令
│   └── migrate.py                     # 数据迁移命令
│
├── tests/                             # 测试
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   ├── factories.py                   # 测试数据工厂
│   │
│   ├── unit/                          # 单元测试
│   │   ├── __init__.py
│   │   ├── agents/
│   │   │   ├── test_data_agent.py
│   │   │   ├── test_knowledge_agent.py
│   │   │   ├── test_behavior_agent.py
│   │   │   ├── test_alignment_agent.py
│   │   │   ├── test_strategy_agent.py
│   │   │   ├── test_risk_agent.py
│   │   │   └── test_backtest_agent.py
│   │   ├── dsl/
│   │   │   ├── test_parser.py
│   │   │   ├── test_compiler.py
│   │   │   └── test_executor.py
│   │   ├── features/
│   │   │   ├── test_technical.py
│   │   │   └── test_trade_stats.py
│   │   └── models/
│   │       └── test_models.py
│   │
│   ├── integration/                   # 集成测试
│   │   ├── __init__.py
│   │   ├── test_pipeline.py
│   │   ├── test_agent_coordination.py
│   │   ├── test_api.py
│   │   └── test_db.py
│   │
│   └── e2e/                           # 端到端测试
│       ├── __init__.py
│       └── test_full_flow.py
│
├── scripts/                           # 运维脚本
│   ├── init_db.py                     # 数据库初始化
│   ├── seed_data.py                   # 种子数据导入
│   ├── export_data.py                 # 数据导出
│   └── benchmark.py                   # 性能基准测试
│
├── data/                              # 本地数据（.gitignore）
│   ├── raw/                           # 原始数据
│   ├── processed/                     # 处理后数据
│   ├── parquet/                       # Parquet 存储
│   └── samples/                       # 样本数据（可提交）
│       ├── sample_blog.json
│       ├── sample_trades.csv

│
├── docs/                              # 项目文档
│   ├── architecture.md                # 架构设计文档
│   ├── api.md                         # API 文档
│   ├── dsl-spec.md                    # DSL 语法规范
│   ├── deployment.md                  # 部署指南
│   ├── troubleshooting.md             # 故障排查
│   └── diagrams/                      # 架构图
│       ├── system-overview.mmd        # Mermaid 系统架构图
│       ├── data-flow.mmd              # 数据流图
│       └── agent-interaction.mmd      # Agent 交互图
│
├── deploy/                            # 部署配置
│   ├── docker/
│   │   ├── Dockerfile.api             # API 服务镜像
│   │   ├── Dockerfile.worker          # Worker 镜像
│   │   └── nginx.conf                 # Nginx 配置
│   ├── k8s/                           # Kubernetes 部署
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── configmap.yaml
│   └── monitoring/                    # 监控配置
│       ├── prometheus.yml
│       ├── grafana/
│       │   └── dashboards/
│       └── alertmanager.yml
│
└── prompts/                           # LLM Prompt 模板
    ├── concept_extraction.md          # 概念提取 Prompt
    ├── rule_extraction.md             # 规则提取 Prompt
    ├── precondition_extraction.md     # 前置条件提取 Prompt
    └── dsl_generation.md              # DSL 生成 Prompt
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

**Agent 列表与职责：**

| Agent | 目录 | 职责 | 关键 Skills |
|-------|------|------|------------|
| Data Agent | `data_agent/` | 数据采集（爬虫、市场数据、入库） | `crawl_blog`, `fetch_market`, `store_db` |
| Knowledge Agent | `knowledge_agent/` | 文章理解 → 策略 DSL | `extract_concepts`, `extract_rules`, `build_strategy_dsl` |
| Behavior Agent | `behavior_agent/` | 交易行为分析 | `label_behavior`, `feature_extraction`, `clustering` |
| Alignment Agent | `alignment_agent/` | ⭐ 策略对齐 + 可信度评分 | `rule_match_score`, `conflict_detection`, `confidence_scoring` |
| Strategy Agent | `strategy_agent/` | 决策信号生成 | `compute_features`, `evaluate_rules`, `generate_signal` |
| Risk Agent | `risk_agent/` | 风险控制 | `position_sizing`, `stop_loss`, `drawdown_control` |
| Backtest Agent | `backtest_agent/` | 策略回测验证 | `run_backtest`, `evaluate_metrics`, `parameter_search` |

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
| **容器** | Docker + Docker Compose | 本地开发/部署 |
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

### 6.2 Docker Compose 服务

```yaml
services:
  api:           # FastAPI 服务         → :8000
  postgres:      # PostgreSQL 数据库    → :5432
  redis:         # Redis 缓存           → :6379
  worker:        # 后台 Agent Worker
  prometheus:    # 监控                  → :9090
  grafana:       # 仪表盘               → :3000
```

### 6.3 环境变量

```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/trade_ai
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
LOG_LEVEL=INFO
CRAWL_PROXY=http://proxy:port
MARKET_DATA_TOKEN=xxx
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

# 3. 启动基础设施
docker compose up -d postgres redis

# 4. 初始化数据库
python scripts/init_db.py

# 5. 运行 API
uvicorn api.main:app --reload

# 6. 运行测试
pytest tests/ -v --cov=src
```
