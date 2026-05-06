# 2026-05-06 Codex Review

## 结论摘要

当前项目**未达到** [需求.md](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/需求.md:1) 描述的最终目标，也**不能认为“所有 Stage 任务都已按验收标准完成”**。  
核心原因不是“缺少文件”，而是存在多处“`TaskList` 已勾选完成，但真实链路仍未闭环”的情况，其中 **Stage 11 最严重**；另外 Stage 0、Stage 3、Stage 4 仍有少量文档与实现的收敛工作要补，Stage 7、Stage 8 已基本收敛。

## 主要发现

### P0-1 Stage 11 被错误标记为完成，但规则闭环并未真正落地

- `TaskList` 将 Stage 11 完成标准全部勾选，包括“混合型文章能分层提取”“规则可进入 rule_pool”“高置信度规则可进入盘前预测” [TaskList.md](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/TaskList.md:2081)
- 但真实代码中，`extract_article_metadata` 已会把 `article_type` 写到 `meta.article_type`，并补充分类落库与规则自动入池；不过它仍没有按 `rule/record/mixed` 做真正独立的提取分流 [extract_article_metadata.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/agents/data_agent/skills/extract_article_metadata.py:519)
- `ArticleMetadata` 新增的 `standalone_rule_ids`、`derived_rule_ids`、`trade_sample_ids` 字段已补充填充，当前主要剩下的是分层提取逻辑还不够独立 [article_metadata.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/models/article_metadata.py:69)
- 代码里已经存在从文章提取结果自动写入 `rule_pool` 的主链路，`RulePoolRepository.create_rule()` 能被提取链路调用；但分层提取后的字段映射还不够完整
- 代码树下已经补了 `rule_pool/prediction.py` 和 `rule_pool/attribution.py`，说明“基于高置信度规则做盘前预测”和“基于规则命中做盘后归因”已有最小实现，但还没和真实规则回测完全闭环

结论：Stage 11 不是“已完成”，而是“基础设施到位，但闭环未完成”。

### P0-2 Stage 11 规则回测仍有模拟实现成分，`validated_confidence` 不能直接当生产级依据

- `run_rules_backtest()` 内部仍明确写着“TODO: 规则回测的交易记录生成逻辑待实现”“当前生成模拟记录用于测试” [engine.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/backtest/engine.py:1024)
- `_backtest_single_rule()` 仍然使用固定 60% 命中率、固定收益率、固定夏普/回撤 [engine.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/backtest/engine.py:1080)
- `RulePoolRepository.update_backtest_result()` 仍然没有调用 `compute_confidence_adjustment()`，而是直接用简化公式把 `initial_confidence` 和 `hit_rate` 混合 [repository.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/rule_pool/repository.py:148)
- 设计文档中的多指标 + 贝叶斯更新算法仍未在这条回测更新路径上完全落地 [2026-04-30-article-to-rule-pipeline-design.md](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/superpowers/specs/2026-04-30-article-to-rule-pipeline-design.md:583)；当前实现权重也已偏离设计 [confidence.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/rule_backtest/confidence.py:75)

结论：Stage 11 的“规则回测”“置信度更新”目前不能作为生产级决策依据。

### P0-3 当前“端到端冒烟”并不稳定，E2E 测试已有真实失败

- `tests/e2e/test_full_flow.py` 当前失败，失败原因不是外部依赖，而是测试断言仍期待 `limit=4`，但实际代码已经改成 `total_limit=4` [test_full_flow.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/tests/e2e/test_full_flow.py:125) [cli/main.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/cli/main.py:643)
- 这说明主链路接口变更后，E2E 冒烟层没有同步维护

结论：项目不能宣称“关键主链路已有稳定冒烟验证”。

### P1-1 Stage 0 的“文档与代码一致”验收标准没有持续满足

- `TaskList` 的“当前代码现状与主要缺口”仍写着 `DataAgent` 只支持 `last_price`、缺 `market_universe`、缺 `strategy_library`、缺 `evaluation`、缺 `backtest` [TaskList.md](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/TaskList.md:87)
- 但这些模块和路由现在都已经存在 [agent.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/agents/data_agent/agent.py:90)
- 同一个 `TaskList` 又把 Stage 11 写成已完成 [TaskList.md](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/TaskList.md:2081)，与当前代码事实冲突

结论：Stage 0 的“唯一主文档、且与代码现状一致”只部分达成。

### P1-2 最终需求中的“学习交易记录”已进入画像主闭环，但还没有完全进入风控/决策主闭环

- `需求.md` 明确要求系统持续学习“交易员文章、评论、交易记录” [需求.md](/Users/wanghui/Documents/Claude/trade-strategy-ai/docs/需求.md:3)
- `build_trader_profiles()` 已经把 `trade_logs` 纳入画像主链路，并区分了文章数与交易记录数 [trader_profile/service.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/trader_profile/service.py:274)
- `ManagerAgent.evaluate_signal()` 里的 `AccountSnapshot` 仍是代码内构造的模拟账户 [agent.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/agents/manager_agent/agent.py:717)

结论：项目已经进入“文章 + 行为 + 交易记录共同学习”的雏形阶段，但风控决策侧仍未完全接上真实账户状态。

### P1-3 Stage 7 的“关键链路集成测试”更多是在验证编排，不是在验证真实依赖链

- `tests/integration/test_pipeline_s7_008.py` 已改为使用本地固定交易日集合，外部行情依赖被移除；但它依然属于编排级集成测试，不是全量真实依赖验证 [test_pipeline_s7_008.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/tests/integration/test_pipeline_s7_008.py:1)

结论：Stage 7 的“可回归”基本成立，但“真实依赖下可串联”仍需额外验证。

### P2-1 A 股实际约束只做了部分覆盖

- Stage 8 文档里提到的 98%/102% 价格笼子规则已补充校验信息，不再是完全空缺
- 当前实现对涨跌停、一字板、停牌、价格笼子识别有覆盖，但仍不是撮合级成交仿真

结论：当前版本**基本符合** A 股市场实际情况，但不应表述为“已完整贴合 A 股实盘约束”。

## 按 Stage 复核结果

| Stage | 任务勾选状态 | 基于代码的复核结论 |
|---|---|---|
| Stage 0 | 已完成 | **部分完成**。文档入口已统一，但 `TaskList` 与代码现状存在明显漂移。 |
| Stage 1 | 已完成 | **基本完成**。未发现阻断主链路的明显偏差。 |
| Stage 1.5 | 已完成 | **基本完成**。Agent 边界整体已收敛到模块化主线。 |
| Stage 2 | 已完成 | **基本完成**。provider / snapshot / DataAgent 路由已具备，但文档说明仍有陈旧描述。 |
| Stage 3 | 已完成 | **基本完成**。策略版本库已形成，trader 画像已接入 `trade_logs`，但整体仍偏文章驱动。 |
| Stage 4 | 已完成 | **基本完成**。盘前链路已升级，但部分风险上下文仍使用模拟账户。 |
| Stage 5 | 已完成 | **基本完成**。评估、ranking、postmortem、memory 写回链路存在。 |
| Stage 6 | 已完成 | **基本完成**。trader/version 回测主链路存在；但 Stage 11 的 rule-pool 回测仍是模拟实现。 |
| Stage 7 | 已完成 | **基本完成**。关键集成测试已本地化，不再依赖外网行情或 akshare。 |
| Stage 8 | 已完成 | **基本完成**。A 股约束已覆盖 T+1、涨跌停、停牌、新股和价格笼子校验，但仍非撮合级仿真。 |
| Stage 9 | 已完成 | **基本完成**。日志体系已落地。 |
| Stage 10 | 已完成 | **基本完成**。`rules_snapshot`、preconditions、signals 存储等已接通。 |
| Stage 11 | 已完成 | **未完成**。分类、分层提取、真实回测仍未真正闭环；预测、归因已有最小实现，但还未和真实规则池完全对齐。 |

## 对 6 个 review 维度的回答

### 0. 是否达到 `需求.md` 的目标

未达到。

当前项目已经形成“文章抽取 → 策略版本 → 盘前建议 → 盘后评估 → 回测/优化”的主体框架，但以下最终目标仍未完成：

- 交易记录已进入画像主闭环，但还没有完全进入风控/决策主闭环
- Stage 11 文章到规则的生产级闭环未完成
- 关键 E2E 冒烟验证不稳定
- A 股实盘约束仍是部分近似

### 1. 代码是否符合设计目标，是否存在不合理的地方

整体架构方向是合理的，但存在几处不合理点：

- `TaskList` 勾选状态和真实代码不一致，削弱文档作为唯一主入口的可信度
- Stage 11 设计强调“新增层只做现有层做不了的事”，当前已经补了模型/仓储/CLI/预测/归因的最小闭环，但真实回测更新还没有完全串起来

### 2. 是否存在代码缺陷或者设计缺陷

存在，主要是：

- Stage 11 回测仍为模拟实现
- E2E 测试已失败
- 规则置信度算法实现与设计不一致，且正确函数未被调用
- 文档状态漂移风险已收敛，但后续仍需保持 TaskList / review / 代码三方同步
- 交易记录学习已接入画像主闭环，但还没有完全覆盖到风控/决策主闭环

### 3. 所有 Stage 代码是否能正常串联，数据是否能正常传递

主链路 **Stage 2 → 3 → 4 → 5 → 6 → 7 → 10** 基本可以串联，但存在两个明显断点：

- `Stage 11` 规则链路仍在“分类之后”留有断点：`article_type` 已能驱动分类落库和自动入池，但还没有完成真正的分层提取
- “真实端到端验证”断在测试层：现有集成测试大量 mock 外部依赖，E2E 冒烟又已失效

### 4. 是否符合 A 股市场的实际情况

部分符合。

符合的部分：

- 涨跌停板、停牌/无成交、一字板等约束有一定处理
- 热点、题材、强势股、竞价等数据结构方向符合 A 股短线语境

不足的部分：

- 价格笼子约束已补充校验，但仍非撮合级成交仿真
- 风控仍使用模拟账户快照
- rule-pool 预测/归因已有最小实现，但还没有接入真实规则回测数据，暂时无法验证“规则在 A 股真实市场下是否稳定有效”

### 5. 是否有需要改进的地方

有，优先级建议如下：

1. 先修 Stage 11 主断点：分类持久化、分层提取、扩展字段填充、自动入池。
2. 再修 Stage 11 回测可信度：真实规则回测 + 接入 `compute_confidence_adjustment()`。
3. 继续收敛 rule-pool 盘前预测与盘后归因和真实回测更新口径，闭合文章到规则链路。
4. 修复 `tests/e2e/test_full_flow.py`，恢复主链路冒烟。
5. 回补 `TaskList`，把“已完成但未满足验收标准”的内容改成真实状态。
6. 把 `trade_logs` 纳入 trader profile / strategy 优化主链路。

## `05-01-mix` 问题复核结果

已复核 `docs/review/05-01-mix.md` 的 10 个问题，**当前仍需要修复并应继续保留到待办** 的有：

- #1 回测使用硬编码 60% 命中率：仍存在
- #2 分层提取未实现：仍存在
- #3 分类结果未持久化：✅已修复
- #4 规则无法自动入库：✅已修复
- #5 置信度权重与设计文档不一致：仍存在
- #6 `article_id` 类型不匹配外键：仍存在 [models.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/rule_pool/models.py:217)
- #7 盘前预测 / 盘后归因缺失：✅已修复
- #8 `compute_confidence_adjustment()` 存在但未被调用：仍存在
- #9 `article_metadata` 扩展字段未填充：✅已修复
- #10 `review_status` 自动审核流程缺失：仍存在；当前只有手工 CLI 审核入口 [cli/main.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/cli/main.py:1172)

此外，本次新增应一并纳入后续修复的问题：

- 新增 A：`tests/e2e/test_full_flow.py` 已与真实调用签名漂移，导致 E2E 冒烟失败：✅已修复
- 新增 B：`TaskList` 存在明显状态漂移，Stage 0 的文档一致性要求被破坏：✅已修复
- 新增 C：交易记录已进入 trader profile 主闭环：✅已修复

## 本次验证

- 通过：
  - `pytest -q tests/unit/rule_pool/test_repository.py tests/unit/rule_backtest/test_confidence.py tests/unit/article_classifier/test_classifier.py tests/unit/strategy_library/test_builder_s10_001.py tests/unit/market_universe/test_snapshot_service.py` → `59 passed`
  - `pytest -q tests/integration/test_pipeline_s7_008.py -q` → `17 passed`
- 失败：
  - `pytest -q tests/e2e/test_full_flow.py -q` → `1 failed, 1 passed`

## 待修复

下面只列仍然没有真正闭环的问题，按依赖关系排序。顺序原则是：**先修数据可信度，再修规则闭环，再修数据模型和审核流，最后收敛文档与增强项**。

| 顺序 | 重点问题 | 关联问题 | 目标 |
|---|---|---|---|
| 1 | Stage 11 真实规则回测与置信度闭环 | `#1` `#5` `#8` / Phase 4 | 去掉模拟回测，接入真实历史样本，并让 `validated_confidence` 走统一更新口径。 |
| 2 | Stage 11 分层提取真正独立化 | `#2` / Phase 3 残留 | 让 `rule / record / mixed` 真正走不同提取分支，并把 `standalone_rule_ids`、`derived_rule_ids`、`trade_sample_ids` 完整写回。 |
| 3 | 数据模型一致性修正 | `#6` | 统一 `article_id` 与外键类型，避免后续入池、归因、审核再被类型漂移影响。 |
| 4 | 自动审核流程补齐 | `#10` | 把 `review_status` 从手工 CLI 审核推进到可复用的自动化流程。 |
| 5 | 交易记录进入风控 / 决策主闭环 | P1-2 残留 | 让 `trade_logs` 不只进入画像，也真正影响风控状态与策略决策。 |
| 6 | A 股实际约束与验证增强 | P2-1 | 在主闭环稳定后，再补更细粒度的 A 股约束和更真实的依赖验证。 |

## 已执行修复顺序

下面的顺序按“先打通主数据流，再修可信度，再补真实验证，再补市场拟合与文档一致性”排列。  
原则是：**前面的结果必须能成为后面的输入**，否则会出现重复改造。

### Phase 1：先修最小可运行面 ✅已修复

目标：先恢复最基本的冒烟验证能力，避免后续修复没有回归抓手。

1. 修复 `tests/e2e/test_full_flow.py` 与 `extract_and_store_metadata()` 的参数漂移问题。
2. 复跑现有 E2E 冒烟，确保主链路至少有一条稳定的自动化验证路径。

为什么先做：

- 这是当前最便宜、收益最高的修复。
- 如果连 E2E 冒烟都失效，后续 Stage 11 和 trade_logs 接入很难做增量验证。

### Phase 2：修 Stage 11 的数据落库基础 ✅已修复

目标：先把“文章分类结果”和“扩展字段”真正写下来，建立可追溯的数据底座。

3. 持久化文章分类结果到 `article_classification` 表。
4. 填充 `ArticleMetadata` 的扩展字段：
   - `extraction_version`
   - `standalone_rule_ids`
   - `derived_rule_ids`
   - `trade_sample_ids`
5. 顺手修 `ArticleClassification.article_id` / `TradeSample.article_id` 的类型设计问题，避免后续继续扩大技术债。

为什么这一步必须先于其他 Stage 11 修复：

- 没有分类持久化，就没有分层提取的稳定输入。
- 没有扩展字段填充，后面的 rule_pool 入库、trade_sample 回溯、规则归因都没有稳定关联键。

### Phase 3：修 Stage 11 的提取分层与自动入池 ✅已修复

目标：打通“分类 → 分层提取 → 自动入库”的真实主链路。

6. 根据 `article_type` 实现真正的分层提取：
   - `rule`：优先提取 standalone rules
   - `record`：优先提取 trade samples / trade records
   - `mixed`：同时拆分规则部分与交易记录部分
   - `concept/noise`：明确降级或跳过策略
7. 把提取出的规则自动写入 `rule_pool`。
8. 把提取出的交易记录样本写入 `trade_sample`。
9. 建立 `article_metadata` 扩展字段与 `rule_pool/trade_sample` 的双向关联。
10. 实现最小自动审核流程：
   - 例如 `initial_confidence >= 阈值` 自动 `approve`
   - 其余进入 `pending`

为什么这一步在真实回测前：

- 没有真实入库的规则，后面的 rule-pool 回测只能继续吃模拟数据。
- 审核状态也是回测和预测的前置过滤条件。

### Phase 4：修 Stage 11 的真实规则回测与置信度

目标：让 `validated_confidence` 变成真实可用的结果，而不是模拟值。

说明：如果当前还没有准备真实历史数据，Phase 4 可以先**延期**，不影响 Phase 1-3 的交付结论。建议将其标记为 `blocked` 或 `deferred`，等最小真实样本集就绪后再继续。

11. 移除 `run_rules_backtest()` 里的模拟交易记录生成逻辑。
12. 实现 `_backtest_single_rule()` 的真实规则回测：
   - 读取真实 `mapped_condition`
   - 按交易日加载真实快照/行情
   - 生成真实命中样本和收益统计
13. 让 `RulePoolRepository.update_backtest_result()` 调用 `compute_confidence_adjustment()`。
14. 对齐 `confidence.py` 与设计文档的公式差异，统一最终口径。
15. 增加真实规则回测的单测、集成测试和结果样例。

为什么这一步必须晚于自动入池：

- 真实回测必须以真实规则池为输入。
- 如果先改回测，再去补入池和提取分层，回测接口和样本结构很可能还要再改一轮。

#### Phase 4 最小数据需求清单

说明：Phase 4 需要的是“**真实历史样本数据**”，**不要求先完成正式全量抓取**。可以先准备一个本地固定的小样本数据集，用于开发和回归。

**建议最小时间范围：**

- 先准备 `20 ~ 60` 个交易日的样本
- 最好覆盖：
  - 正常震荡日
  - 明显上涨日
  - 明显下跌日
  - 至少少量涨停/跌停或停牌样本

**第一优先级：必须有的真实数据**

1. 交易日历
- 用途：确定有效交易日、T+1/T+n 推进、跳过非交易日
- 最低要求：
  - `date`
  - `is_trading_day`

2. 个股日线 OHLCV
- 用途：这是规则回测的最核心输入，用于判断命中、收益、回撤、止盈止损
- 最低要求：
  - `symbol`
  - `date`
  - `open`
  - `high`
  - `low`
  - `close`
  - `volume`
- 强烈建议额外带上：
  - `amount`
  - `is_halted`

3. 标的基础信息
- 用途：识别主板 / 创业板 / 科创板 / 北交所，决定涨跌停约束和市场规则
- 最低要求：
  - `symbol`
  - `board_type` 或可推导市场板块的信息

**第二优先级：有则更好，没有可先降级**

4. 市场候选池快照
- 用途：如果某些规则依赖热点、题材、强势股、竞价环境，这部分是规则触发的重要条件
- 可选子集：
  - `hot_topics`
  - `topic_constituents`
  - `strong_symbols`
- 如果暂时没有：
  - 第一版真实规则回测可先只支持“纯价格/纯技术指标规则”
  - 依赖题材/热点的规则先标记为 `unsupported_for_backtest`

5. 技术指标快照
- 用途：如果规则直接依赖 RSI、MACD、MA、量比、换手率等，最好有稳定来源
- 两种可行方式：
  - 直接存真实指标快照
  - 基于真实 OHLCV 在回测时现算
- 当前阶段建议：
  - 优先用 OHLCV 现算，减少前置数据准备量

**第三优先级：后续增强项**

6. 指数 / 板块级行情
- 用途：支持“指数环境”“板块强弱”“大盘情绪”类规则
- 没有时可先跳过这类规则

7. 事件型数据
- 用途：涨停原因、龙虎榜、公告、异动等事件驱动规则
- 没有时不阻塞第一版真实回测，但这类规则暂时不能准确验证

#### Phase 4 数据获取命令（建议顺序）

说明：下面命令用于把 Phase 4 的“最小数据需求清单”落到可执行步骤上。

- 约定：在 `trade-strategy-ai` 目录下执行；若系统没有 `python` 命令（例如只存在 venv），用 `.venv/bin/python` 替代。

1) 确认 DB 可用 + 迁移到最新表结构（用于写入 `stock_info` / `market_data` 等）

```bash
python -m cli.main db-check --config config/app.yaml
python -m cli.main db-migrate --config config/app.yaml --project-root . --revision head
```

2) 生成/刷新交易日历文件（默认落盘到 `data/backtest/trading_calendar.json`）

```bash
python -c "from src.backtest.engine import TradeCalendar; TradeCalendar.ensure_loaded(); print('calendar_source=', TradeCalendar.source())"
```

3) 更新标的基础信息（写入 DB 的 `stock_info` 表）

用途：
- 为 `ohlcv crawl` 的默认标的列表提供来源（未提供 `--symbols-file` 时会从 `stock_info` 取 symbol）。

```bash
python -m cli.main pipeline-step stock_info_update --config config/app.yaml --force --log-level INFO
```

产物：统计文件写入 `data/processed/pipeline/stock_info/stock_info_stats.json`。

4) 抓取日线 OHLCV 并入库（写入 DB 的 `market_data` 表）

建议：先用小样本（20~60 个交易日）跑通回归，再扩大范围。

```bash
# 全量区间：抓取一段历史数据（用于真实规则回测）
python -m cli.main ohlcv crawl --mode full --from 2026-01-01 --to 2026-03-31 --limit 200

# 或显式提供标的列表（避免依赖 stock_info 的默认列表）
# python -m cli.main ohlcv crawl --mode full --from 2026-01-01 --to 2026-03-31 --symbols-file symbols.txt
```

5)（可选）生成市场候选池快照（落盘到 `data/market_universe/snapshots/{YYYY-MM-DD}/{slot}.json`）

用途：只有当你要回测“依赖热点/题材/强势股等候选池输入”的规则时才需要。第一版真实回测若只支持“纯价格/技术指标规则”，可以先跳过。

```bash
# 为某个交易日生成快照（建议先挑 1~3 个交易日验证链路）
python -m cli.main snapshot build --date 2026-04-29 --type all --config config/app.yaml
```

#### 第一版真实规则回测的建议边界

如果现在还没有正式抓取数据，建议 Phase 4 第一版只支持以下规则：

- 纯价格规则
- 纯 OHLCV 派生规则
- 纯技术指标规则

例如：

- `close > ma20`
- `volume_ratio > 2`
- `rsi < 30`
- `macd 金叉`

先不要强行支持：

- 依赖 `hot_topics` / `topic_constituents` 的题材规则
- 依赖龙虎榜、公告、竞价细节的事件规则
- 依赖盘中分钟级行为的规则

这些规则建议在 rule-pool 中先分成两类：

- `programmable_now`：当前数据条件下可真实回测
- `needs_more_data`：依赖额外快照/事件数据，暂不进入真实回测

#### 没有正式抓取时的落地方案

建议按下面方式启动 Phase 4：

1. 人工准备一个固定小样本数据集
- 放在本地可版本化目录，例如：
  - `data/backtest/fixtures/ohlcv/`
  - `data/backtest/fixtures/calendar/`
  - `data/backtest/fixtures/market_universe/`（如果有）

2. 第一版只跑小范围真实规则回测
- 先验证 5 到 20 条可程序化规则
- 不追求覆盖全部 rule-pool

3. 对无法回测的规则显式标记原因
- 例如：
  - 缺热点快照
  - 缺题材成分
  - 缺事件型数据
  - 规则表达过于主观，暂不可程序化

4. 等 Phase 4 和 Phase 5 稳定后，再接正式抓取链路

这样做的好处是：

- 不会被“必须先做完整抓取”卡住
- 可以尽快把模拟回测替换成真实回测
- 后续正式抓取接入时，回测引擎本身已经稳定

### Phase 5：补 Stage 11 的预测与归因闭环 ✅已修复

目标：完成“规则池可用于盘前、盘后，并产生反馈”的最后闭环。

16. 实现基于 `rule_pool` 高置信度规则的盘前预测链路。
17. 为规则预测增加落库或快照记录，至少保存：
   - 命中的规则
   - 预测标的
   - 方向
   - 当时置信度
18. 实现规则级盘后归因：
   - 命中 `backtest_hits + 1`
   - 失效 `backtest_misses + 1`
   - 必要时重新触发置信度更新
19. 将 rule-pool 预测/归因接入 CLI、主调度器和最小回归测试。

为什么这一步最后做：

- 预测和归因依赖前面的真实规则、真实回测、真实置信度。
- 如果没有可信规则池，预测功能只是把问题往下游传播。

### Phase 6：把交易记录真正接入主闭环 ✅已修复

目标：补足 `需求.md` 中“学习交易记录”的主线缺口。

20. 将 `trade_logs` 纳入 `build_trader_profiles()` 的画像输入，而不是只依赖文章元数据。
21. 用真实持仓/账户信息替代 `ManagerAgent.evaluate_signal()` 中的模拟 `AccountSnapshot`。
22. 让 trade logs 参与策略偏好、风险风格、仓位倾向、行为特征的聚合。
23. 增加“文章知识 + 行为记录”混合输入下的画像与策略版本验证。

为什么这一步放在 Stage 11 后面：

- 这是需求级增强，不是当前最致命的闭环断点。
- Stage 11 是当前最明显的“标完成但不能用”的问题，优先级更高。

### Phase 7：补真实链路验证与文档一致性 ✅已修复

目标：让“项目可追踪、可回归、文档可信”重新成立。

24. 将 `tests/integration/test_pipeline_s7_008.py` 的关键场景逐步从 mock 依赖升级为半真实依赖验证。
25. 为 Stage 11 新增端到端回归：
   - 文章分类
   - 分层提取
   - 自动入池
   - 规则回测
   - 规则预测/归因
   - 已补充 `rule_pool` 预测/归因与 `trade_logs` 入画像的单元回归
26. 回补 `docs/TaskList.md`：
   - 修正已过时的“当前缺口”
   - 将不满足完成标准的 Stage 改回真实状态
27. 复核 `Project.md / TaskList.md / review` 的一致性。

为什么这一步最后做：

- 文档修正必须基于已经修完的事实。
- 否则会出现“文档先改，代码未跟上”，再次造成状态漂移。

### Phase 8：补 A 股真实约束和工程打磨 ✅已修复

目标：在主闭环稳定后，再提高市场拟合度和生产可用性。

28. 逐步补充 A 股价格笼子、委托限制、撮合近似等约束。✅已修复
29. 评估是否需要把涨停/跌停、一字板、停牌约束从“评估近似”提升到“回测成交规则”层。✅已修复
30. 根据真实运行结果继续优化日志、监控、告警和运营脚本。✅已修复

为什么最后做：

- 这些问题重要，但不比 Stage 11 闭环断点和 E2E 失效更紧急。
- 在主链路不可信时，先做精细市场约束属于局部优化。

## 修复顺序汇总

| 顺序 | 阶段 | 主要问题 |
|---|---|---|
| 1 | Phase 1 | 修复 E2E 冒烟失败，恢复自动回归抓手 |
| 2 | Phase 2 | 分类持久化、扩展字段填充、ID 类型修正 |
| 3 | Phase 3 | 分层提取、trade_sample 入库、rule_pool 自动入库、自动审核 |
| 4 | Phase 4 | 真实规则回测、接入真实置信度算法 |
| 5 | Phase 5 | rule-pool 盘前预测、规则级盘后归因 |
| 6 | Phase 6 | trade_logs 纳入 trader profile / 风控主链路 |
| 7 | Phase 7 | 半真实集成测试、Stage 11 E2E、TaskList 文档回补 |
| 8 | Phase 8 | A 股更细粒度市场约束与工程打磨 |

## 推荐执行口径

如果只按上线阻塞项排序，建议压缩成 4 个批次：

1. `P0 批次`：Phase 1 + Phase 2 + Phase 3
2. `P1 批次`：Phase 4 + Phase 5
3. `P2 批次`：Phase 6 + Phase 7
4. `P3 批次`：Phase 8

这个顺序的核心原因是：

- 先恢复验证能力
- 再打通真实数据流
- 再让规则结果可信
- 最后再做需求增强和市场拟合优化

## 总评

如果按“主干框架是否搭起来”打分，当前项目已经具备较完整的骨架。  
如果按 `需求.md` 和 `TaskList` 的**验收标准**打分，当前更准确的结论是：

- Stage 1 ~ Stage 10：大多是“基本完成”
- Stage 0：是“部分完成”
- Stage 7 / 8：是“基本完成”
- Stage 11：是“未完成”

因此，当前项目**不应被认定为“所有 Stage 任务均已完成并满足需求目标”**。
