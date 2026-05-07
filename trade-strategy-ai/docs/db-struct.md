# 数据库结构文档

本文档描述 trade-strategy-ai 项目的数据库表结构。

---

## 表总览

| 表名 | 说明 | 所属模块 |
|------|------|----------|
| `blog_articles` | 博客文章表 | 文章爬取/存储 |
| `article_metadata` | 文章元数据表（LLM 提取） | 文章处理 |
| `raw_articles` | 原始文章表（爬取阶段） | 文章爬取 |
| `crawl_state` | 增量爬取状态表 | 文章爬取 |
| `ohlcv_bars` | 日线 OHLCV 行情数据 | 行情数据 |
| `indicators` | 技术指标缓存表 | 指标计算 |
| `trade_logs` | 交易日志表 | 交易记录 |
| `signals` | 交易信号表 | 信号生成 |
| `data_audit_events` | 数据审计事件表 | 数据治理 |
| `trader_memory` | 交易员记忆表 | 记忆存储 |
| `stock_info` | 股票基本信息表 | 股票映射 |

---

## 1. blog_articles（博客文章表）

存储从各博客平台爬取的博客文章内容，是系统的核心文章存储表。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | UUID | 否 | 主键 |
| `source` | VARCHAR(50) | 否 | 文章来源平台（如 "雪球"、"东方财富"） |
| `source_article_id` | VARCHAR(128) | 是 | 来源平台文章 ID |
| `source_url` | VARCHAR(1024) | 否 | 文章原始 URL，唯一索引 |
| `title` | VARCHAR(500) | 否 | 文章标题 |
| `author_name` | VARCHAR(100) | 是 | 作者名称 |
| `author_id` | VARCHAR(128) | 是 | 作者 ID |
| `published_at` | DATETIME | 是 | 文章发布时间（含时区） |
| `crawled_at` | DATETIME | 否 | 爬取时间（含时区） |
| `content_text` | TEXT | 否 | 文章纯文本内容 |
| `content_html` | TEXT | 是 | 文章原始 HTML |
| `summary` | TEXT | 是 | 文章摘要 |
| `tags` | JSON | 否 | 文章标签列表 |
| `content_hash` | VARCHAR(64) | 是 | 内容哈希值（用于去重），唯一索引 |
| `view_count` | INTEGER | 否 | 阅读数，默认 0 |
| `like_count` | INTEGER | 否 | 点赞数，默认 0 |
| `bookmark_count` | INTEGER | 否 | 收藏数，默认 0 |
| `comment_count` | INTEGER | 否 | 评论数，默认 0 |
| `comments_payload` | JSON | 否 | 评论详情列表 |
| `raw_payload` | JSON | 否 | 原始爬取数据 |
| `created_at` | DATETIME | 否 | 创建时间（含时区） |
| `updated_at` | DATETIME | 否 | 更新时间（含时区） |

**索引：**
- `ix_blog_articles_source_published_at` - (source, published_at)
- `ix_blog_articles_author_published_at` - (author_id, published_at)
- `ix_blog_articles_crawled_at` - crawled_at
- `ix_blog_articles_content_hash` - content_hash

---

## 2. article_metadata（文章元数据表）

存储 LLM 从博客文章中提取的交易相关元数据，包括交易标的、策略规则、情绪分析等。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | UUID | 否 | 主键 |
| `article_id` | UUID | 否 | 关联的 blog_articles.id，外键，唯一索引 |
| `schema_version` | VARCHAR(20) | 否 | 元数据版本号，默认 "v1" |
| `processed_at` | DATETIME | 是 | LLM 处理时间（含时区） |
| `extracted_concepts` | JSON | 否 | 提取的概念列表 |
| `trading_symbols` | JSON | 否 | 提及的交易标的代码列表 |
| `strategy_rules` | JSON | 否 | 策略规则列表 |
| `preconditions` | JSON | 否 | 前置条件列表 |
| `comment_insights` | JSON | 否 | 评论洞察列表 |
| `raw_llm_output` | JSON | 否 | LLM 原始输出 |
| `sentiment_score` | DECIMAL(4,3) | 是 | 情绪分数，范围 -1~1 |
| `confidence_score` | DECIMAL(4,3) | 是 | 置信度分数，范围 0~1 |
| `created_at` | DATETIME | 否 | 创建时间（含时区） |
| `updated_at` | DATETIME | 否 | 更新时间（含时区） |

**索引：**
- `ix_article_metadata_schema_version` - schema_version
- `ix_article_metadata_processed_at` - processed_at

---

## 3. raw_articles（原始文章表）

爬取阶段直接写入的原始文章，用于支持增量抓取状态管理。后续由 clean 流程转换为 blog_articles。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | UUID | 否 | 主键 |
| `source` | VARCHAR(50) | 否 | 来源平台 |
| `site` | VARCHAR(100) | 否 | 站点名称 |
| `trader_id` | VARCHAR(100) | 是 | 交易员 ID |
| `author_id` | VARCHAR(128) | 否 | 作者 ID |
| `author_name` | VARCHAR(100) | 是 | 作者名称 |
| `source_url` | VARCHAR(1024) | 否 | 文章 URL |
| `source_article_id` | VARCHAR(128) | 是 | 来源平台文章 ID |
| `title` | VARCHAR(500) | 否 | 文章标题 |
| `published_at` | DATETIME | 是 | 发布时间（含时区） |
| `crawled_at` | DATETIME | 否 | 爬取时间（含时区） |
| `content_text` | TEXT | 否 | 纯文本内容 |
| `content_html` | TEXT | 是 | 原始 HTML |
| `content_hash` | VARCHAR(64) | 是 | 内容哈希（去重用） |
| `comment_count` | INTEGER | 否 | 评论数，默认 0 |
| `comments` | JSONB | 否 | 评论列表 |
| `raw_payload` | JSONB | 否 | 原始爬取数据 |
| `is_processed` | BOOLEAN | 否 | 是否已被 clean 流程处理，默认 false |
| `processed_at` | DATETIME | 是 | 处理时间（含时区） |
| `created_at` | DATETIME | 否 | 创建时间（含时区） |
| `updated_at` | DATETIME | 否 | 更新时间（含时区） |

**索引：**
- `ix_raw_articles_source_author` - (source, author_id)
- `ix_raw_articles_crawled_at` - crawled_at
- `ix_raw_articles_content_hash` - content_hash
- `ix_raw_articles_is_processed` - is_processed

---

## 4. crawl_state（增量爬取状态表）

持久化每个 (source, author_id) 的增量爬取状态，替代原有的 state.json 文件。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | INTEGER | 否 | 主键，自增 |
| `source` | VARCHAR(50) | 否 | 来源平台 |
| `author_id` | VARCHAR(128) | 否 | 作者 ID |
| `last_seen_article_url` | TEXT | 是 | 最后见到的文章 URL |
| `last_seen_published_at` | DATETIME | 是 | 最后见到的文章发布时间（含时区） |
| `seen_urls` | TEXT[] | 否 | 已见文章 URL 集合（用于快速去重） |
| `seen_hashes` | TEXT[] | 否 | 已见内容哈希集合（用于内容去重） |
| `last_success_article_count` | INTEGER | 否 | 最后成功抓取的文章数量 |
| `created_at` | DATETIME | 否 | 创建时间（含时区） |
| `updated_at` | DATETIME | 否 | 更新时间（含时区） |

**约束：**
- 唯一约束：`ix_crawl_state_source_author` - (source, author_id)

---

## 5. ohlcv_bars（日线 OHLCV 行情数据表）

存储股票日线 OHLCV 数据，用于回测和规则验真。
数据通过 `cli/ohlcv.py crawl` 从 akshare 抓取。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | UUID | 否 | 主键 |
| `symbol` | VARCHAR(32) | 否 | 标的代码（如 "000001.SZ"） |
| `trade_date` | DATE | 否 | 交易日期 |
| `open` | FLOAT | 否 | 开盘价 |
| `high` | FLOAT | 否 | 最高价 |
| `low` | FLOAT | 否 | 最低价 |
| `close` | FLOAT | 否 | 收盘价 |
| `volume` | FLOAT | 否 | 成交量 |
| `turnover` | FLOAT | 是 | 成交额 |
| `created_at` | DATETIME | 否 | 创建时间（含时区） |
| `updated_at` | DATETIME | 否 | 更新时间（含时区） |

**索引：**
- `ix_ohlcv_symbol` - symbol
- `ix_ohlcv_trade_date` - trade_date

**唯一约束：**
- `uq_ohlcv_symbol_date` - (symbol, trade_date)

---

## 5.1. indicators（技术指标缓存表）

存储从 ohlcv_bars 计算的技术指标。首次回测时按需计算并写入，后续直接读取。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | UUID | 否 | 主键 |
| `symbol` | VARCHAR(32) | 否 | 标的代码 |
| `trade_date` | DATE | 否 | 交易日期 |
| `rsi` | FLOAT | 是 | RSI(14) |
| `macd_histogram` | FLOAT | 是 | MACD 柱状图 |
| `bb_width` | FLOAT | 是 | 布林带宽度 |
| `cci` | FLOAT | 是 | CCI 指标 |
| `ma50` | FLOAT | 是 | 50日均线 |
| `ma200` | FLOAT | 是 | 200日均线 |
| `stoch_k` | FLOAT | 是 | 随机指标 %K |
| `volume_ratio` | FLOAT | 是 | 量比 |
| `price_vs_ma` | FLOAT | 是 | 价格相对均线比率 |
| `atr_ratio` | FLOAT | 是 | ATR 比率 |
| `close_position` | FLOAT | 是 | 收盘在振幅中的位置 |
| `computed_at` | DATETIME | 否 | 计算时间 |

**索引：**
- `ix_indicator_symbol` - symbol
- `ix_indicator_trade_date` - trade_date

**唯一约束：**
- `uq_indicator_symbol_date` - (symbol, trade_date)

> **变更记录：** `market_data` 表已于 2026-05-07 移除，数据迁移至 `ohlcv_bars` + `indicators` 两表分离架构。

---

## 6. trade_logs（交易日志表）

记录实际执行的交易订单，是交易策略验证和复盘的核心数据。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | UUID | 否 | 主键 |
| `source` | VARCHAR(50) | 否 | 交易数据来源 |
| `external_id` | VARCHAR(128) | 是 | 交易所订单 ID，唯一索引 |
| `account_id` | VARCHAR(64) | 否 | 账户 ID |
| `symbol` | VARCHAR(32) | 否 | 标的代码 |
| `market` | VARCHAR(32) | 否 | 市场（默认 "CN"） |
| `side` | VARCHAR(10) | 否 | 交易方向（buy/sell） |
| `position_side` | VARCHAR(10) | 否 | 持仓方向（long/short/flat） |
| `order_type` | VARCHAR(20) | 是 | 订单类型 |
| `executed_at` | DATETIME | 否 | 成交时间（含时区） |
| `quantity` | DECIMAL(20,6) | 否 | 成交数量 |
| `price` | DECIMAL(20,6) | 否 | 成交价格 |
| `amount` | DECIMAL(20,6) | 否 | 成交金额 |
| `fee` | DECIMAL(20,6) | 否 | 手续费，默认 0 |
| `currency` | VARCHAR(8) | 否 | 币种（默认 "CNY"） |
| `strategy_tag` | VARCHAR(128) | 是 | 策略标签 |
| `rationale` | TEXT | 是 | 交易理由 |
| `article_id` | UUID | 是 | 关联的分析文章 ID（blog_articles.id） |
| `raw_payload` | JSONB | 否 | 原始数据 |
| `created_at` | DATETIME | 否 | 创建时间（含时区） |
| `updated_at` | DATETIME | 否 | 更新时间（含时区） |

**索引：**
- `ix_trade_logs_symbol_executed_at` - (symbol, executed_at)
- `ix_trade_logs_account_executed_at` - (account_id, executed_at)
- `ix_trade_logs_article_executed_at` - (article_id, executed_at)

**约束：**
- 唯一约束：`uq_trade_logs_composite_key` - (account_id, symbol, executed_at, quantity, price)

---

## 7. signals（交易信号表）

存储由策略分析生成的交易信号，包含买卖点、止损止盈等信息。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | INTEGER | 否 | 主键，自增 |
| `signal_id` | UUID | 否 | 信号唯一 ID，唯一索引 |
| `symbol` | VARCHAR(20) | 否 | 标的代码 |
| `side` | VARCHAR(10) | 否 | 信号方向（BUY/SELL/HOLD/REJECTED） |
| `confidence` | FLOAT | 是 | 置信度 |
| `triggered_rules` | JSONB | 是 | 触发的规则列表 |
| `synthesis_mode` | VARCHAR(20) | 是 | 合成模式 |
| `entry_price` | JSONB | 是 | 入场价格（JSON 格式） |
| `position_size` | JSONB | 是 | 仓位大小（JSON 格式） |
| `stop_loss` | JSONB | 是 | 止损价格（JSON 格式） |
| `take_profit` | JSONB | 是 | 止盈价格（JSON 格式） |
| `rejected` | BOOLEAN | 否 | 是否被拒绝，默认 False |
| `rejection_reason` | TEXT | 是 | 拒绝原因 |
| `degraded` | BOOLEAN | 否 | 是否降级，默认 False |
| `degradation_reason` | TEXT | 是 | 降级原因 |
| `version` | VARCHAR(10) | 是 | 信号版本 |
| `metadata` | JSONB | 是 | 其他元数据 |
| `created_at` | DATETIME | 否 | 创建时间 |
| `updated_at` | DATETIME | 否 | 更新时间 |

**索引：**
- `idx_signals_symbol` - symbol
- `idx_signals_created_at` - created_at
- `idx_signals_signal_id` - signal_id

---

## 8. data_audit_events（数据审计事件表）

记录关键数据写入操作的批次级审计事件，用于数据治理和溯源。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | UUID | 否 | 主键 |
| `event_type` | VARCHAR(64) | 否 | 事件类型 |
| `actor` | VARCHAR(64) | 否 | 操作者 |
| `entity_type` | VARCHAR(64) | 否 | 实体类型 |
| `entity_id` | VARCHAR(128) | 是 | 实体 ID |
| `dataset_version` | VARCHAR(128) | 是 | 数据集版本 |
| `payload` | JSON | 否 | 事件负载数据 |
| `source` | VARCHAR(64) | 否 | 数据来源 |
| `event_at` | DATETIME | 否 | 事件发生时间（含时区） |
| `created_at` | DATETIME | 否 | 创建时间（含时区） |
| `updated_at` | DATETIME | 否 | 更新时间（含时区） |

**索引：**
- `ix_data_audit_events_created_at` - created_at
- `ix_data_audit_events_event_type_created_at` - (event_type, created_at)

---

## 9. trader_memory（交易员记忆表）

存储交易员的成功/失败案例、复盘笔记、策略调整建议等。

> **变更记录 (NTL-S7-000)：** 原为 JSONL 文件存储（`trader_memory.jsonl`），2026-04-29 迁移至 PostgreSQL 数据库。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | UUID | 否 | 主键 |
| `trader_id` | VARCHAR(64) | 否 | 交易员 ID |
| `memory_type` | VARCHAR(32) | 否 | 记忆类型（success_case/failure_case/review_note/postmortem/strategy_adjustment/market_regime_note） |
| `as_of_date` | DATE | 否 | 关联交易日期 |
| `symbol` | VARCHAR(32) | 是 | 关联股票代码 |
| `title` | VARCHAR(256) | 否 | 记忆标题 |
| `content` | VARCHAR(4096) | 否 | 记忆内容 |
| `source` | VARCHAR(64) | 否 | 来源（默认 "manager"） |
| `source_ref` | VARCHAR(512) | 是 | 来源引用 |
| `tags` | TEXT[] | 是 | 标签列表 |
| `importance` | FLOAT | 否 | 重要性（0~1），默认 0.5 |
| `archived` | BOOLEAN | 否 | 软删除标记，默认 false |
| `archived_at` | TIMESTAMPTZ | 是 | 归档时间 |
| `idea_id` | UUID | 是 | 关联的交易想法 ID |
| `strategy_version_id` | VARCHAR(64) | 是 | 关联的策略版本 ID |
| `ranking_entry_id` | UUID | 是 | 关联的 ranking 条目 ID |
| `topic_source` | VARCHAR(64) | 是 | Topic 来源（如 "kaipan"） |
| `raw_topic_ids` | JSONB | 是 | {provider: [raw_topic_id, ...]} |
| `postmortem_data` | JSONB | 是 | 盘后评估数据 |
| `strategy_adjustment_data` | JSONB | 是 | 策略调整数据 |
| `market_regime_data` | JSONB | 是 | 市场状态数据 |
| `extra` | JSONB | 是 | 附加数据 |
| `created_at` | TIMESTAMPTZ | 否 | 创建时间 |
| `updated_at` | TIMESTAMPTZ | 否 | 更新时间 |

**约束：**
- 唯一约束：`uq_memory_ctx` - (trader_id, memory_type, as_of_date, symbol)

**索引：**
- `ix_memory_trader_id` - trader_id
- `ix_memory_trader_archived` - (trader_id, archived)
- `ix_memory_trade_date` - as_of_date
- `ix_memory_symbol` - symbol
- `ix_memory_type` - memory_type
- `ix_memory_created_at` - created_at

---

## 10. stock_info（股票基本信息表）

存储 A 股股票名称→代码映射表，用于元数据提取时将中文股票名称转换为标准代码格式。

| 字段 | 类型 | 可空 | 说明 |
|------|------|------|------|
| `id` | UUID | 否 | 主键 |
| `symbol` | VARCHAR(32) | 否 | 标准代码（如 "000001.SZ"、"600519.SH"） |
| `code` | VARCHAR(16) | 否 | 股票代码（如 "000001"、"600519"） |
| `market` | VARCHAR(8) | 否 | 交易所（SZ/SH/BJ） |
| `name` | VARCHAR(128) | 否 | 中文名称 |
| `security_type` | VARCHAR(32) | 否 | 证券类型（stock/etf/fund/bond），默认 "stock" |
| `created_at` | DATETIME | 否 | 创建时间（含时区） |
| `updated_at` | DATETIME | 否 | 更新时间（含时区） |

**约束：**
- 唯一约束：`uq_stock_info_symbol` - symbol
- 唯一约束：`uq_stock_info_symbol_market` - (symbol, market)

**索引：**
- `ix_stock_info_name` - name
- `ix_stock_info_code` - code

---

## 表关系图

```
blog_articles ──1:1── article_metadata
    │
    └─────────────── trade_logs (article_id → blog_articles.id, ON DELETE SET NULL)

stock_info ──────── 独立表（用于名称→代码映射）
ohlcv_bars ──────── 独立表（日线行情，回测引擎直读）
indicators ──────── 关联 ohlcv_bars（首次计算缓存，后续直接读取）
trade_logs ──────── 独立表（交易记录）
signals ─────────── 独立表（信号数据）
data_audit_events ─ 独立表（审计日志）
raw_articles ────── 独立表（原始爬取数据）
crawl_state ─────── 独立表（爬取状态）
trader_memory ───── 独立表（交易员记忆，NTL-S7-000 由 JSONL 迁移）
```
