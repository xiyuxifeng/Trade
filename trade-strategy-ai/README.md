# Trade Strategy AI

`Trade Strategy AI` 是一个面向交易研究与策略反推的多 Agent 系统。项目围绕“文章内容、评论、交易记录、市场数据”构建统一的数据与分析链路，用来支持规则抽取、策略生成、行为分析、风险控制和回测验证。

## 项目目标

- 爬取交易相关文章和评论，形成原始研究语料
- 提取文章中的交易逻辑、前置条件和关键概念
- 接入交易日志与行情数据，建立统一数据底座
- 通过 Agent 协作把主观认知转成可验证、可回测的策略表达

## 当前进展

- 已完成项目基础目录规划
- 已落地 `Data Architecture` 第一轮实现
- 已建立核心 ORM 数据模型、索引策略和验证模块
- 已为后续文章爬取、评论解析、交易导入和行情接入准备好数据结构

## 核心模块

- `src/agents/`
  - 业务 Agent 层，包括 `data_agent`、`knowledge_agent`、`strategy_agent`、`risk_agent`、`backtest_agent`、`alignment_agent`
- `src/models/`
  - SQLAlchemy ORM 模型
- `src/db/`
  - 数据库会话、仓储层、迁移目录
- `src/pipeline/`
  - 数据清洗、校验、特征工程、导出
- `api/`
  - FastAPI 应用入口和路由
- `cli/`
  - 爬取、分析、迁移、回测等命令行入口
- `docs/`
  - 架构设计、API 说明、流程图

## 数据架构

当前 Phase 1 重点围绕 4 张核心表：

- `blog_articles`
  - 文章正文、HTML、作者信息、发布时间、抓取时间、互动指标、评论快照
- `article_metadata`
  - 概念抽取、规则抽取、前置条件、评论洞察、情绪与置信度
- `trade_logs`
  - 账户、标的、方向、成交时间、数量、价格、金额、手续费、关联文章
- `market_data`
  - OHLCV、成交额、复权因子、衍生指标和原始行情 payload

详细设计见 [architecture.md](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/architecture.md)。

## 技术栈

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 Async
- PostgreSQL
- DuckDB
- Redis
- pandas / polars / pyarrow
- Playwright / BeautifulSoup / lxml

## 快速开始

### 1. 安装依赖

```bash
pip install -e .[dev]
```

### 2. 配置环境变量

复制示例配置：

```bash
cp .env.example .env
```

重点变量包括：

- `DATABASE_URL`
- `REDIS_URL`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `MARKET_DATA_TOKEN`

### 3. 初始化数据库

后续数据库初始化脚本准备好后，可执行：

```bash
python scripts/init_db.py
```

### 4. 运行测试

```bash
pytest
```

## 推荐开发顺序

1. 完成数据采集与入库链路
2. 实现文章和评论解析
3. 接入交易数据与市场数据源
4. 完成数据校验、清洗和特征工程
5. 实现策略抽取、对齐分析和回测闭环

## 文档入口

- [架构设计](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/architecture.md)
- [API 文档](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/api.md)
- [数据流图](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/diagrams/data-flow.mmd)

## 当前最值得推进的方向

- 文章爬虫与评论抓取
- 数据入库流水线
- Repository 与 API 查询层
- Alembic 迁移与初始化脚本

## License

暂未指定。
