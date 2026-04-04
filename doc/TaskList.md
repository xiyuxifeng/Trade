# 📋 开发任务列表（Task List）

## Phase 0：运行闭环 MVP（3-7 天）

> 目标：先跑通“盘前建议 + 盘后考核复盘”的日常闭环（可手动、可配置定时），再逐步完善爬虫与策略反推能力。


### Config & Contracts（配置与数据契约）
- [x] P0-101 定义配置文件规范（建议 YAML）：timezone、schedule.*、evaluation.*、traders[]、llm.*
- [x] P0-102 实现配置加载与优先级（文件 < 环境变量 < DB覆盖(可选) < 手动触发参数）
- [x] P0-103 定义并实现 Pydantic 契约：DataRequest/DataResponse、TradeIdea、EvaluationRequest/EvaluationResult、DailyReport
- [x] P0-104 定义幂等键与重复运行策略（同日重复运行不重复入库）


### Orchestration（编排与调度）
- [x] P0-105 实现 ManagerAgent 最小编排：run_pre_market / run_after_close（先 CLI 手动触发）
- [x] P0-106 实现轻量 scheduler（建议 APScheduler）：按 schedule.* 定时触发 Manager
- [x] P0-107 实现 DataAgent 最小能力（例如：行情 OHLCV + 常用指标）；缺能力返回 capability_missing
- [x] P0-108 实现 1 个 TraderAgent 样本：请求数据 -> 输出结构化 TradeIdea -> 上报 Manager
- [x] P0-109 实现 Task 机制：capability_missing 自动生成 agent_tasks 待办


### Reporting（报告最小闭环）
 - [x] P0-110 生成盘前日报（DailyReport）
 - [x] P0-111 生成盘后考核报告（EvaluationResult 汇总）
 - [x] P0-112 输出每日分析报告（HTML）：DailyReport / EvaluationResult 渲染为静态 HTML 文件
 - [x] P0-113 增加日报/考核 HTML 模板：`src/reporting/templates/daily_report.html`、`src/reporting/templates/evaluation.html`
 - [x] P0-114 CLI 增加报告导出参数（可选）：运行盘前/盘后时同时生成 HTML 版本报告
 - [x] P0-V01 Phase 0 验收：手动触发可完成“盘前日报 + 盘后考核”，未配置 schedule 不自动跑

---

## Phase 0.5：Persona Router MVP（3-7 天）

> 目标：在不依赖完整爬虫/LLM 抽取/DSL 的情况下，把“多风格 persona + 市场态势路由 + 收益最大化”接入盘前闭环，并输出可解释/可回放的决策。

### Persona Schema（规则契约与字段标准化）
- [x] P0-115 定义 `strategy_rules/preconditions` JSON schema（字段标准化）
- [x] P0-116 定义 claim_key 字典（v0）并写入文档

### StyleCluster & Router（多风格与路由）
- [x] P0-117 定义 StyleCluster/MarketState 数据结构（可回放）
- [x] P0-118 实现收益最大化路由（Hard Filter + Scoring Router + Top-2 备选）
- [x] P0-119 CLI 增加 `persona-init-sample`（无爬虫时生成样例 clusters 文件）

### MarketState（指数/ETF 日线 → regime/vol）
- [x] P0-123 从本地指数/ETF 日线 CSV 生成 MarketState（regime/vol 规则化分类）
- [x] P0-124 CLI 增加 `market-state-build`（输出 MarketState JSON）
- [x] P0-125 ManagerAgent 在缺省 market_state_path 时可从 benchmark CSV 自动构建 MarketState
- [x] P0-126 AkShare 日线拉取工具类（可复用），并支持 `market-state-build --from-akshare`

### Run Loop Integration（闭环接入）
- [x] P0-120 盘前 TradeIdea 标注风格选择结果（cluster_id/label/score/reasons）
- [x] P0-121 输出路由决策 JSON（persona_route_YYYY-MM-DD.json）
- [x] P0-122 日报 HTML 增加“风格簇”列

### Phase 0.5 Verification（验收）
- [x] P0.5-V01 persona.enable=true 时，盘前日报包含风格簇列且可生成 persona_route 文件
- [x] P0.5-V02 Top-1/Top-2 选择理由可解释、可人工调参

备注：已在本机完成一次 CLI 端到端运行验证（见 data/processed 输出）。

---

## Phase 1：数据层（2-3 周）

### Data Architecture (数据架构)
- [ ] P0-001 设计 PostgreSQL Schema：blog_articles, trade_logs, market_data, article_metadata
- [ ] P0-002 设计数据库索引策略（时间序列、股票代码、关键字段）
- [ ] P0-003 制定数据验证规则和异常检测策略
- [ ] P0-004 选型并配置 DuckDB / Parquet 存储方案

### Blog Crawler (博客爬虫)
- [x] P1-001 分析目标博客网站结构和动态加载机制
- [x] P1-002 开发静态 HTML 爬虫模块（BeautifulSoup）
- [ ] P1-003 开发动态页面爬虫模块（Playwright）
- [ ] P1-004 实现博客内容提取器（标题、正文、发布时间、标签）
- [ ] P1-005 集成 Nginx + Proxy 池实现反爬虫防护
- [ ] P1-006 建立爬虫错误重试和日志机制

补充（面向增量更新的必须项）：
- [x] P1-006A 建立“按交易员来源配置”的增量抓取机制（支持同站点多作者，last_seen + content_hash/URL 去重）
- [ ] P1-006B 建立文章更新触发：新文章入库后触发 Trader 画像/记忆刷新（可异步）
- [x] P1-006C 为淘股吧实现手工 Cookie 认证抓取（配置形态：`crawl.auth.tgb.cn.cookie`）
- [x] P1-006C1 将抓取配置拆分为 `crawl.auth`（站点认证）与 `crawl.sources`（作者来源）
- [x] P1-006D 为淘股吧实现评论抓取与清洗：去表情、标记无效评论、区分作者/读者
- [ ] P1-006E 为淘股吧实现楼中楼评论拍平存储，同时保留 `parent_comment_id/root_comment_id/reply_to_user`
- [ ] P1-006F 增加首版轻量反爬策略：限频、随机抖动、最大页数/文章数/评论页数、403/429 退避
- [x] P1-006G 自动登录预留：定义认证接口，后续支持 Playwright 登录与 Cookie 自动续期
- [x] P1-006H 抓取命令增加 Cookie 配置使用说明，并记录到项目文档
- [x] P1-006I 抽象站点抓取器接口，首版实现 `TgbCrawler`，兼容未来多站点扩展

### Trade Log Parser (交易记录解析)
- [ ] P1-007 定义交易记录 Schema（时间、标的、方向、价格、仓位）
- [ ] P1-008 开发 HTML/Table 交易记录解析器
- [ ] P1-009 开发 PDF 交易记录解析器
- [ ] P1-010 实现交易数据验证（重复、冲突、缺失）
- [ ] P1-011 建立交易数据导入流程（CSV/Excel 支持）

补充（多交易员绑定）：
- [ ] P1-011A 增加 trader_id/account_id 绑定策略（导入时能归属到 TraderAgent）

### Market Data Integration (市场数据接入)
- [ ] P1-012 集成股票 K线数据源（TuShare / AKShare）
- [ ] P1-013 实现数据本地缓存和更新策略
- [ ] P1-014 集成指数和板块数据
- [ ] P1-015 建立数据质量检查（OHLCV 合理性）

### Database & Storage (数据库与存储)
- [ ] P1-016 配置 PostgreSQL 连接池（SQLAlchemy）
- [ ] P1-017 实现 ORM 模型和数据访问层
- [ ] P1-018 建立数据导入脚本和初始化流程
- [ ] P1-019 配置数据备份和恢复机制
- [ ] P1-020 优化数据库查询性能（Query Plan）
- [ ] P1-021 建立数据版本控制和审计日志

### Data Pipeline & Validation (数据管道与验证)
- [ ] P1-022 设计 Airflow DAG 或 Luigi 数据流程
- [ ] P1-023 实现数据异常检测（离群值、缺失）
- [ ] P1-024 实现数据去重和去噪
- [ ] P1-025 编写数据质量测试（单元测试）
- [ ] P1-026 建立数据监控 Dashboard（数据新鲜度、完整性）

### API Layer (API 接口层)
- [ ] P1-027 设计数据查询 API（FastAPI）
- [ ] P1-028 实现博客数据查询接口
- [ ] P1-029 实现交易数据查询接口
- [ ] P1-030 实现市场数据查询接口
- [ ] P1-031 实现数据导出接口（CSV/JSON/Parquet）

补充（运行闭环接口）：
- [ ] P1-032 实现手动触发接口（可选）：/run/pre_market、/run/after_close
- [ ] P1-033 实现报告查询接口（可选）：日报/考核报告/复盘报告

补充（宿主薄壳接口，规划）：
- [x] P1-034 定义宿主 JSON 命令契约（run_pre_market/run_after_close/persona_init_sample）
- [ ] P1-035 提供薄壳入口（可选）：FastAPI /host/command → 调用内部 handler
- [ ] P1-036 提供结果查询与下载（可选）：报告/路由决策 JSON

### Phase 1 Verification (验收检查)
- [ ] P1-V01 单元测试覆盖率 >80%
- [ ] P1-V02 爬虫成功率 >95%，数据缺失率 <5%
- [ ] P1-V03 数据库性能测试通过（1000+ QPS）
- [ ] P1-V04 数据 24h 更新能工作无异常
- [ ] P1-V05 文档完成度 100%

---

## Phase 2：认知与行为建模（2-3 周）

> 更新：Phase 2 优先服务于 TraderAgent 画像与建议生成；原 Knowledge/Behavior 任务仍保留，但可以分批落地。

### TraderAgent（交易员画像与建议生成，新增核心）
- [ ] P2-101 定义 traders 配置结构（trader_id、display_name、article_sources、trade_log_sources）
- [ ] P2-102 实现 Trader 画像（文章 + 交易记录 → 风格/纪律/偏好标签）
- [ ] P2-103 实现 Trader 记忆存储结构（成功/失败案例、复盘结论，可检索）
- [ ] P2-104 实现盘前 TradeIdea 生成（结构化输出 + 校验）
- [ ] P2-105 实现复盘任务处理：接收 EvaluationRequest，输出复盘结论并写回记忆

### ManagerAgent（日常汇总与编排，新增核心）
- [ ] P2-106 实现 TradeIdea 收集与去重/冲突处理
- [ ] P2-107 生成盘前汇总日报（DailyReport）
- [ ] P2-108 盘后触发评估：拉取最新行情并计算建议收益（含 MFE/MAE 口径定义）
- [ ] P2-109 阈值触发复盘：evaluation.* 配置化

### Knowledge Agent - 文章理解 (NLP & 策略提取)
- [ ] P2-001 定义策略 DSL 格式（YAML/JSON 模式）
- [ ] P2-002 创建策略概念库（主动性、被动性、量态）
- [ ] P2-003 开发概念抽取模块（LLM + Prompt）
- [ ] P2-004 开发买卖规则抽取模块（条件、动作、参数）
- [ ] P2-005 开发市场前置条件抽取（大盘、板块、风格、流动性）
- [ ] P2-006 实现 DSL 生成器（规则 → 可执行代码）
- [ ] P2-007 建立策略 DSL 验证和标准化流程

### Behavior Agent - 行为分析 (特征工程)
- [ ] P2-008 定义交易行为分类体系（追涨、抄底、震荡、趋势）
- [ ] P2-009 开发行为标签化模块（规则 or ML）
- [ ] P2-010 计算交易特征集（收益率、夏普比、最大回撤、胜率、期望值）
- [ ] P2-011 实现特征归一化和标准化
- [ ] P2-012 开发行为聚类模块（K-means/DBSCAN）
- [ ] P2-013 建立常见交易模式库（头肩顶、双顶、复合形态）
- [ ] P2-014 实现模式匹配和识别

### Feature Extraction & Preprocessing (特征工程)
- [ ] P2-015 编写特征计算脚本（Pandas/Polars）
- [ ] P2-016 实现技术指标计算库（MA, MACD, RSI, Bollinger）
- [ ] P2-017 实现基本面特征计算（PE, PB, 涨速）
- [ ] P2-018 实现时间序列特征（趋势、波动性、自相关）
- [ ] P2-019 编写缺失值处理和异常检测脚本

### Data Validation for Phase 2 (验证检查)
- [ ] P2-020 手工验证 Knowledge Agent 输出（>20 个样本）
- [ ] P2-021 手工验证 Behavior Agent 输出（>20 个样本）
- [ ] P2-022 特征计算准确性抽样验证
- [ ] P2-023 行为标签和实际交易一致性检查

### Phase 2 Verification
- [ ] P2-V01 Knowledge Agent 规则提取准确率 >80%
- [ ] P2-V02 Behavior Agent 标签准确率 >75%
- [ ] P2-V03 特征计算速度 <50ms/笔
- [ ] P2-V04 样本数据通过 domain expert 评审
- [ ] P2-V05 模块文档完成度 100%

---

## Phase 3：策略对齐（⭐ 核心，2 周）

> 更新：Phase 3 分两条线并行：
> 1）面向日常系统的“建议考核与复盘闭环”
> 2）面向策略反推的“文章策略 vs 行为”对齐（原计划保留）

### Daily Evaluation（建议考核与复盘闭环，新增核心）
- [ ] P3-101 定义建议考核指标口径（收益率、触发止损/止盈、最大不利波动等）
- [ ] P3-102 实现盘后建议评分与汇总报告（EvaluationResult + 总结）
- [ ] P3-103 实现不达标/亏损的复盘任务生成与追踪
- [ ] P3-104 将复盘结论写回 Trader 记忆，并在下一次生成中显式引用
- [ ] P3-V01 验收：连续运行 5-20 天回放数据能稳定产生“日报 + 考核 + 复盘”

### Alignment Analysis Framework (对齐分析框架)
- [ ] P3-001 定义规则匹配评分算法 `rule_match_score()`
- [ ] P3-002 定义行为适配度评分算法 `behavior_fit_score()`
- [ ] P3-003 定义冲突检测算法 `conflict_detection()`
- [ ] P3-004 定义综合可信度评分算法 `confidence_scoring()`

### Rule Matching & Scoring (规则匹配)
- [ ] P3-005 实现规则漏配检测（历史交易未被规则覆盖）
- [ ] P3-006 计算规则覆盖率（% 历史交易被匹配）
- [ ] P3-007 计算规则准确度（规则触发中真实交易 %）
- [ ] P3-008 实现规则冲突检测（互相排斥的规则）

### Behavior Fit Analysis (行为适配度)
- [ ] P3-009 计算特征向量相似度（余弦、欧几里得）
- [ ] P3-010 计算概率分布拟合度（KL 散度、Wasserstein）
- [ ] P3-011 实现时间序列相似度（DTW，点互相关）
- [ ] P3-012 计算胜率、期望值等统计量的匹配度

### Conflict Detection (冲突检测)
- [ ] P3-013 识别时序冲突（规则要求 vs 实际时间顺序）
- [ ] P3-014 识别参数冲突（参数设置不一致）
- [ ] P3-015 识别逻辑冲突（相互矛盾的规则）
- [ ] P3-016 分类冲突严重程度（Critical / Major / Minor）

### Confidence Scoring & Reporting (可信度评分)
- [ ] P3-017 实现多维度综合评分（加权组合）
- [ ] P3-018 生成对齐报告（文本格式）
- [ ] P3-019 生成可视化报告（图表）
- [ ] P3-020 生成冲突清单和优化建议
- [ ] P3-021 实现评分结果缓存和版本管理

### Alignment Agent 集成 (Agent 模块)
- [ ] P3-022 实现 Alignment Agent 主控逻辑
- [ ] P3-023 集成 Rule Matching / Behavior Fit / Conflict Detection
- [ ] P3-024 实现评分输出的持久化存储
- [ ] P3-025 实现增量对齐（新数据来时增量计算）

### Validation & Verification (验证)
- [ ] P3-026 与 domain expert 对齐评分结果对标（相关性 >0.7）
- [ ] P3-027 编写对齐分析的单元和集成测试
- [ ] P3-028 性能测试（>100 笔/秒 对齐评分能力）
- [ ] P3-029 生成样本对齐报告取得 stakeholder 确认

### Phase 3 Verification
- [ ] P3-V01 对齐评分与 expert feedback 相关性 >0.7
- [ ] P3-V02 冲突检测准确率 >85%
- [ ] P3-V03 性能达到 100+ 笔/秒
- [ ] P3-V04 报告清晰易读，被业务方接受
- [ ] P3-V05 模块文档完成度 100%

---

## Phase 4：策略执行系统（1.5 周）

### Strategy Agent - 决策引擎 (信号生成)
- [ ] P4-001 实现特征计算引擎（实时）
- [ ] P4-002 实现规则评估引擎（快速匹配）
- [ ] P4-003 实现多规则信号合成（加权/投票）
- [ ] P4-004 实现信号输出格式（BUY / SELL / HOLD）
- [ ] P4-005 实现信号版本控制和追踪

### Risk Agent - 风险控制 (风控)
- [ ] P4-006 实现头寸管理模块（动态头寸计算）
- [ ] P4-007 实现止损设置（基于波动率/回撤）
- [ ] P4-008 实现止盈策略
- [ ] P4-009 实现单股集中度检查
- [ ] P4-010 实现行业敞口控制
- [ ] P4-011 实现总体风险敞口评估
- [ ] P4-012 实现风险超限告警

### DSL Parser & Execution (DSL 解析和执行)
- [ ] P4-013 选型 DSL 框架（ANTLR / Lark）
- [ ] P4-014 设计 DSL 语法规则
- [ ] P4-015 实现 DSL Parser
- [ ] P4-016 实现 DSL Compiler（→ Python/Java）
- [ ] P4-017 实现 DSL 执行引擎

### Parameter Management (参数管理)
- [ ] P4-018 设计参数存储结构
- [ ] P4-019 实现参数版本控制
- [ ] P4-020 实现参数动态更新机制
- [ ] P4-021 实现参数约束验证

### Strategy Agent Integration (Agent 集成)
- [ ] P4-022 集成 Strategy Agent 主控逻辑
- [ ] P4-023 集成 Risk Agent 主控逻辑
- [ ] P4-024 实现两个 Agent 的通信接口
- [ ] P4-025 实现信号输出的持久化存储

### Testing & Validation (测试验证)
- [ ] P4-026 编写 Strategy Agent 单元测试
- [ ] P4-027 编写 Risk Agent 单元测试
- [ ] P4-028 压力测试（高频信号输入）
- [ ] P4-029 手工验证信号生成的合理性

### Phase 4 Verification
- [ ] P4-V01 信号生成延迟 <100ms
- [ ] P4-V02 风控能阻止 >95% 风险交易
- [ ] P4-V03 规则覆盖 >90% 历史交易
- [ ] P4-V04 系统稳定运行 4+ 小时无异常
- [ ] P4-V05 模块文档完成度 100%

---

## Phase 5：验证与优化（1.5 周）

### Backtest Agent - 回测系统 (验证策略)
- [ ] P5-001 选型回测框架（backtesting.py / VectorBT）
- [ ] P5-002 实现历史数据回测逻辑
- [ ] P5-003 实现交易执行模拟（滑点、手续费、成本）
- [ ] P5-004 实现绩效指标计算（收益率、夏普比、最大回撤、卡玛比、信息比）
- [ ] P5-005 实现风险指标计算（波动率、下行波动率、VaR）
- [ ] P5-006 实现回测报告生成（HTML 可视化）
- [ ] P5-007 实现回测结果的持久化存储

### Parameter Optimization (参数优化)
- [ ] P5-008 实现网格搜索优化器
- [ ] P5-009 实现贝叶斯优化器（可选）
- [ ] P5-010 实现参数扫描和对比
- [ ] P5-011 实现过度拟合风险评估（Walk Forward）
- [ ] P5-012 实现参数稳定性分析

### Multi-Agent Coordination (多 Agent 协调)
- [ ] P5-013 设计任务调度器（DAG 执行）
- [ ] P5-014 实现消息队列框架（可选：Kafka/RabbitMQ）
- [ ] P5-015 实现 Agent 间的通信接口
- [ ] P5-016 实现错误重试和容错机制

### Monitoring & Logging (监控与日志)
- [ ] P5-017 实现集中式日志系统
- [ ] P5-018 配置 Prometheus + Grafana 监控
- [ ] P5-019 实现关键指标告警
- [ ] P5-020 实现系统健康检查

### Integration & Testing (集成与测试)
- [ ] P5-021 全链路集成测试
- [ ] P5-022 压力测试（24h 无间断运行）
- [ ] P5-023 故障恢复测试
- [ ] P5-024 安全测试（输入验证、权限）

### Documentation & Deployment (文档与部署)
- [ ] P5-025 编写系统设计文档
- [ ] P5-026 编写 API 文档
- [ ] P5-027 编写部署和运维文档
- [ ] P5-028 编写故障排查指南
- [ ] P5-029 准备 Docker 镜像
- [ ] P5-030 准备部署 Kubernetes manifests

### Phase 5 Verification
- [ ] P5-V01 回测结果与现实数据偏差符合预期
- [ ] P5-V02 参数优化后策略 Sharpe >1.0
- [ ] P5-V03 系统 24h 稳定运行无异常
- [ ] P5-V04 性能达到要求（延迟、吞吐量）
- [ ] P5-V05 文档完成度 100%，交付物齐全

---

## 🚨 高优先级任务（需要首先着手）

- [ ] **P0-001 ~ P0-004**: 数据库架构设计（建议 Week 1.0）
- [ ] **P1-001 ~ P1-006**: 爬虫开发（建议 Week 1.0-1.5）
- [ ] **P2-001 ~ P2-006**: 策略 DSL 定义（建议 Week 1.5）
- [ ] **P3-001 ~ P3-004**: 对齐分析框架设计（建议 Week 2.0）

---

## 📊 任务优先级与依赖关系

### 优先级说明
- **P0**: Critical - 阻塞其他任务
- **P1**: High - Phase 内核心功能
- **P2**: Medium - Phase 内支持功能
- **P3**: Low - 优化和增强

### 并行任务
以下任务可以并行开展（不相互阻塞）：
- P1-001 ~ P1-006（爬虫）与 P1-007 ~ P1-011（交易解析）
- P2-001 ~ P2-007（Knowledge Agent）与 P2-008 ~ P2-014（Behavior Agent）

---

## 📅 建议推进时间表

| 周 | Phase | 完成里程碑 |
|----|-------|----------|
| 1 | P1 | 数据库 schema + 爬虫基础 |
| 2-3 | P1 | 爬虫完成 + 数据管道 |
| 3-4 | P2 | Knowledge Agent + Behavior Agent |
| 5-6 | P3 | Alignment Agent 完成 |
| 7-8 | P4 | Strategy & Risk Agent 完成 |
| 9-10 | P5 | Backtest Agent + Parameter Optimization |
| 11 | P5+ | 集成、测试、部署 |

---

## 🎯 定义完成标准（DoD - Definition of Done）

每个任务完成时需要满足：
- [ ] 代码已提交到 Git
- [ ] 单元测试覆盖率 >80%
- [ ] 代码 review 已通过
- [ ] 文档已更新
- [ ] 集成测试通过
