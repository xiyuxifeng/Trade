# 🚀 AI 交易策略反推与 Agent 系统开发计划（更新版）

## 项目概述
构建一个完整的 AI 系统：你会提供多个交易员的文章与交易记录，每个交易员最终对应一个独立 TraderAgent，并由 DataAgent 提供可扩展数据能力、ManagerAgent 负责定时编排、汇总日报、盘后考核与复盘反馈，形成可解释的持续改进闭环。

约束与决策（与实现强相关）：
- 不自动下单：先做建议/报告/复盘闭环
- 无 GPU：使用第三方大语言模型 API
- 运行形态：先交互式验证，再沉淀为长期运行服务（共用同一套核心逻辑）
- 调度与阈值：盘前/盘后时间、收益阈值等必须通过 config 配置

---

## 📊 开发阶段总览

| 阶段 | 目标 | 工作量 | 预期周期 |
|------|------|--------|----------|
| Phase 0 | 运行闭环 MVP（盘前建议 + 盘后考核复盘） | 中 | 3-7 天 |
| Phase 0.5 | Persona Router MVP（可执行规则画像 + 多风格路由） | 中 | 3-7 天 |
| Phase 1 | 数据采集与存储（增量抓取/导入/新鲜度） | 重 | 2-3 周 |
| Phase 2 | 多 TraderAgent 画像与建议生成（结构化 TradeIdea） | 重 | 1.5-2.5 周 |
| Phase 3 | Manager 考核与复盘反馈（阈值触发 + 记忆写回） | 中 | 1-2 周 |
| Phase 4 | 策略反推：认知与行为建模（增强 Trader 画像来源） | 重 | 2-3 周 |
| Phase 5 | 对齐/DSL/回测与优化（增强验证能力） | 重 | 3-4 周 |

**说明**：Phase 0-3 优先交付“日常运行闭环”，Phase 4-5 将原有“策略反推与验证”能力逐步接回。

---

## 0️⃣ Phase 0：运行闭环 MVP（3-7 天）
**目标**：在真实约束下尽快跑通闭环，建立可配置、可复用的核心骨架。

### 0.1 配置与契约（必须先行）
- 配置文件（建议 YAML）包含：
  - `timezone`
  - `schedule.enable`
  - `schedule.pre_market_time`（盘前）
  - `schedule.after_close_time`（盘后）
  - `evaluation.min_expected_return`（收益不达标阈值）
  - `evaluation.loss_trigger`（亏损即触发复盘）
  - `traders[]`（每个交易员的 article_sources / trade_log_sources / trader_id 等）
  - `llm.provider` / `llm.model` / 超时重试限流
- 关键数据契约（Pydantic Schema）：
  - DataRequest/DataResponse
  - TradeIdea
  - EvaluationRequest/EvaluationResult

### 0.2 最小可运行编排
ManagerAgent：
  - 手动触发 `run_pre_market()` 生成日报，自动生成每日分析报告并支持HTML展示
  - 手动触发 `run_after_close()` 生成考核与复盘任务，报告可通过HTML模板渲染，便于后续Web/静态浏览
- DataAgent：
  - 先实现最小数据能力（例如行情 OHLCV + 常用指标），能力不足返回 `capability_missing`
- TraderAgent（至少 1 个样本）：
  - 盘前请求数据并输出结构化 TradeIdea

### 0.3 验收标准（Phase 0）
- 同一天重复运行不重复入库（幂等键）
- 未配置 schedule 时不自动定时（仅允许手动）
- 生成一份盘前日报 + 一份盘后考核报告（可落库）

---

## 0️⃣.5 Phase 0.5：Persona Router MVP（3-7 天）

目标：在不依赖完整爬虫/LLM 抽取/DSL 的情况下，把“多风格 persona + 市场态势路由 + 收益最大化”能力接入日常闭环，并可回放/可解释。

交付：

- 定义 `strategy_rules/preconditions` 的标准 JSON schema + claim_key 字典（用于后续抽取与聚合）
- StyleCluster 数据结构与 clusters 文件格式（可先用样例文件跑通）
- MarketState（市场态势）对象与路由评分函数（无回测时用代理收益项 E）
- 盘前 TradeIdea 标注 style 选择结果（cluster_id/label/score/reasons），并输出路由决策 JSON

验收：

- persona.enable=true 时，盘前日报可看到风格簇列；输出 persona_route_YYYY-MM-DD.json
- Top-1/Top-2 选择有可解释理由，便于后续人工调参

相关规格：doc/PersonaRouterSpec.md

---

## Claude Code/Openclaw 薄壳集成路径（规划）

原则：核心逻辑仍是独立应用；宿主只负责交互、触发、展示。

- 提供稳定 JSON 命令接口（例如 run_pre_market/run_after_close/persona_init_sample）
- 宿主通过该接口触发任务并拉取结果，不直接承载业务状态

---

## 🥇 Phase 1：数据层（2-3 周）
**目标**：建立完整的数据采集和存储基础

### 1.1 架构设计
- **数据库选型**：PostgreSQL（结构化）+ DuckDB（分析）+ Parquet（存储）
- **表结构设计**：
  - `blog_articles` - 博客文章表
  - `trade_logs` - 交易记录表
  - `market_data` - 市场数据表
  - `article_metadata` - 文章元数据表
- **API接口设计**：RESTful API 用于数据查询

### 1.2 爬虫系统
- 博客内容爬虫（支持动态加载）
- 交易记录抽取（HTML/PDF解析）
- 市场数据接口集成（股票 K线、指数、板块）

补充（面向新需求的必须项）：
- 文章增量更新机制：按交易员来源配置抓取，基于 `content_hash`/URL 去重
- 数据新鲜度策略：缓存、补齐与回补（由 DataAgent skills 实现）

### 1.3 数据处理管道
- 数据清洗（缺失值处理、异常检测）
- 数据验证（格式检查、业务规则验证）
- 数据索引优化

### 1.4 存储与访问层
- 数据库连接池管理
- 缓存策略（Redis）
- 数据查询接口

---

## 🥈 Phase 2：认知与行为建模（2-3 周）
**目标**：完成 TraderAgent 画像与建议生成所需的“交易员理解层”，并与日常闭环打通

> 注：原 Knowledge/Behavior/Alignment 能力仍然保留，但 Phase 2 优先服务于“TraderAgent 画像/记忆/建议输出”，可先用轻量画像再逐步增强。

### 2.0 TraderAgent（新增核心）
- 交易员画像：从文章与交易记录抽取偏好（周期/题材/纪律/止损等）
- 记忆机制：存储成功/失败案例与复盘结论，供后续生成检索
- 盘前建议生成：输出 TradeIdea（买入价/目标价/止盈止损/仓位/失效条件/理由）

### 2.1 Knowledge Agent（文章理解）
- 概念提取（主动性/被动性策略）
- 买卖规则识别（条件、动作、参数）
- 市场前置条件识别（大盘、板块、风格）
- **输出**：策略 DSL 结构化表示

### 2.2 Behavior Agent（行为分析）
- 交易行为标签化（追涨/抄底/震荡/趋势）
- 特征提取（报酬率、夏普比、最大回撤、胜率）
- 行为聚类（K-means/DBSCAN）
- 模式识别（常见交易模式库）

### 2.3 数据验证检查点
- ✓ 博客文章完整性抽取（>90%）
- ✓ 交易记录准确性验证（时间序列一致）
- ✓ 特征计算正确性（N次抽样验证）

---

## 🥉 Phase 3：策略对齐（⭐ 核心，2 周）
**目标（更新）**：ManagerAgent 在盘后对 Trader 当日建议进行考核评分，并对不达标/亏损触发复盘；同时保留原“文章策略 vs 行为”的对齐能力作为后续增强。

### 3.0 ManagerAgent（新增核心）
- 盘前汇总日报：收集各 TraderAgent TradeIdea，去重/冲突合并/风险提示
- 盘后考核：拉取最新市场数据，对当日建议进行收益与纪律评分
- 复盘触发：低于 `evaluation.min_expected_return` 或触发 `evaluation.loss_trigger` → 生成复盘任务
- 复盘写回：将 Trader 复盘结论写回记忆，用于后续生成

### 3.1 对齐分析框架
- **规则匹配评分** `rule_match_score()`
  - 逐条交易记录与规则匹配
  - 计算规则覆盖率和准确率

- **行为适配度评分** `behavior_fit_score()`
  - 交易特征与文章描述的拟合度
  - 使用余弦相似度/KL散度

- **冲突检测** `conflict_detection()`
  - 发现文章与行为矛盾之处
  - 分类冲突类型（时序冲突、参数冲突、逻辑冲突）

- **综合可信度评分** `confidence_scoring()`
  - 综合三个维度生成最终评分（0-100）
  - 生成对齐报告

### 3.2 输出产物
- 对齐报告（文本 + 可视化）
- 策略可信度评分
- 冲突分析清单
- 优化建议

---

## 🏅 Phase 4：策略执行系统（1.5 周）
**目标（更新）**：将策略执行能力作为增强模块逐步接入，优先支持“建议的可验证性与可解释性”，而非实时高频信号。

### 4.1 Strategy Agent（决策引擎）
- 特征计算引擎（实时计算技术指标）
- 规则评估引擎（快速匹配交易规则）
- 信号合成（多规则加权组合）
- 信号输出（BUY/SELL/HOLD）

### 4.2 Risk Agent（风险控制）
- 头寸管理（动态头寸计算）
- 止损设置（基于波动率/回撤）
- 风险敞口控制（单股集中度、行业敞口）
- 组合风险评估

### 4.3 规则引擎实现
- DSL 解析器（文章规则→可执行代码）
- 参数管理系统
- 规则版本控制

---

## 🚀 Phase 5：验证与优化（1.5 周）
**目标（更新）**：在闭环稳定后引入回测与优化，以更系统的方式验证 Trader 画像/规则的有效性。

### 5.1 Backtest Agent（回测系统）
- 历史数据回测框架
- 交易执行模拟（滑点、手续费、成本）
- 绩效指标计算（收益率、夏普比、最大回撤、卡玛比）
- 生成回测报告（HTML 可视化）

### 5.2 参数优化
- 网格搜索 / 贝叶斯优化
- 超参数调优（MA周期、阈值等）
- 过度拟合风险评估
- 参数稳定性分析

### 5.3 多 Agent 协调
- 任务调度器（DAG 执行）
- 消息队列框架（Kafka/RabbitMQ 可选）
- 日志与监控系统

---

## 🛠️ 技术栈

### 数据层
- PostgreSQL / DuckDB / Parquet
- Python pandas / polars
- SQLAlchemy ORM

### 爬虫 & 数据处理
- Playwright / Selenium（动态爬虫）
- BeautifulSoup / lxml（HTML 解析）
- Apache Airflow（数据管道编排）

### AI & 分析
- LLM API（文章理解）
- scikit-learn（特征工程、聚类）
- statsmodels（统计分析）

### 策略引擎
- ANTLR / lark（DSL 解析）
- 自研规则引擎
- backtesting.py / VectorBT（回测框架）

### 部署 & 运维
- 本地直跑（Python venv + 本机 PostgreSQL）
- Docker / Docker Compose（可选）
- FastAPI（Web 服务）
- Prometheus + Grafana（监控）

---

## 📚 关键接口与数据流

### 核心数据流向
```
Blog & Trade Data
  → Data Agent → DB
  → Knowledge Agent → Strategy DSL
  → Behavior Agent → Behavior Profile
  → Alignment Agent → Confidence Score
  → Strategy Agent + Risk Agent → Signal
  → Backtest Agent → Performance Report
```

### 关键 Agent 接口

| Agent | 输入 | 处理 | 输出 |
|-------|------|------|------|
| Data | 博客URL、交易文件 | 爬取 + 清洗 | 结构化数据 |
| Knowledge | 文章文本 | NLP理解 | 规则DSL |
| Behavior | 交易数据 | 特征提取 | 行为标签 |
| Alignment | DSL + 行为 | 对齐分析 | 可信度评分 |
| Strategy | 规则 + 行情 | 规则评估 | BUY/SELL/HOLD |
| Risk | 信号 + 持仓 | 风控检查 | 最终决策 |
| Backtest | 历史数据 | 回测模拟 | 绩效指标 |

---

## ✅ 验证检查点

### Phase 1
- [ ] DBSchema 通过 code review
- [ ] 爬虫能成功采集100+条博客和交易记录
- [ ] 数据清洗后的缺失率 <5%

### Phase 2
- [ ] Knowledge Agent 规则提取准确率 >80%
- [ ] Behavior Agent 特征计算与手工验证一致
- [ ] 样本数据通过业务逻辑检查

### Phase 3
- [ ] Alignment 评分与 domain expert feedback 相关性 >0.7
- [ ] 冲突检测能识别已知矛盾场景
- [ ] 生成的报告清晰可读

### Phase 4
- [ ] Strategy Agent 信号生成延时 <100ms
- [ ] Risk Agent 能成功阻止 >95% 的风险交易
- [ ] DSL 规则覆盖 >90% 的历史交易

### Phase 5
- [ ] 回测结果与现实数据的偏差符合预期
- [ ] 参数优化后的策略 Sharpe > 1.0
- [ ] 多 Agent 系统能稳定运行 >24h

---

## 🎯 交付物

1. **Phase 1**: 数据库 Schema，爬虫脚本，数据集样本
2. **Phase 2**: Knowledge Agent 模块，Behavior Agent 模块，样本分析报告
3. **Phase 3**: Alignment Agent 模块，对齐报告示例，可信度评分模型
4. **Phase 4**: Strategy Agent 模块，Risk Agent 模块，信号示例
5. **Phase 5**: Backtest Agent 模块，回测报告示例，系统集成文档

---

## 📝 风险与缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 爬虫失效 / 网站改版 | Phase 1 延期 | 提前建立备选数据源 |
| LLM 理解精度不足 | Phase 2 延期 | 结合规则模板 + prompt 优化 |
| 策略对齐困难 | Phase 3 延期 | 多维度对齐指标组合 |
| 数据质量问题 | 全局延期 | 前期加强数据验证 |
| 交易延迟 / 滑点 | Phase 4 风险 | 充分的压力测试 |

---

## 🔄 推进节奏建议

- **Week 1-3**: Phase 1 完成
- **Week 3-5**: Phase 2 完成
- **Week 5-7**: Phase 3 完成
- **Week 7-9**: Phase 4 完成
- **Week 9-11**: Phase 5 完成 + 系统分级验证
