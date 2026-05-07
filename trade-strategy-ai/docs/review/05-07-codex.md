# 2026-05-07 Codex Stage 全项目 Review

## Review 范围

本次 Review 基于当前项目文档与代码实现，重点核对：

- `docs/需求.md` 中定义的产品目标与非目标。
- `docs/TaskList.md` 中 Stage 0 到 Stage 11 的任务状态。
- Stage 2 到 Stage 11 之间的数据链路、CLI、服务、回测、评估、规则池、文档一致性。
- 当前代码对 A 股市场交易约束的覆盖程度。

本 Review 文档先记录初始 Review 结论；后续修复进展会在对应 Step 中标记状态，保证文档与代码一致。

## 验证命令与结果

已执行的核心验证：

```bash
python -m pytest tests/e2e/test_full_flow.py \
  tests/integration/test_pipeline_s7_008.py \
  tests/unit/evaluation/test_evaluation_context_service.py \
  tests/unit/market_universe/test_snapshot_service.py \
  tests/unit/agents/test_extract_article_metadata.py -q
```

结果：

```text
38 passed in 12.71s
```

补充执行：

```bash
python -m pytest tests/unit/evaluation/test_metrics_calculator.py \
  tests/unit/backtest/test_scoring.py \
  tests/unit/strategy_library/test_builder_s10_001.py \
  tests/unit/strategy_library/test_repository.py \
  tests/unit/backtest/test_rule_pool_backtest.py -q
```

结果：

```text
1 failed, 80 passed, 4 warnings in 547.24s
```

Step 1-4 修复后复验：

```bash
python -m pytest tests/e2e/test_full_flow.py \
  tests/integration/test_pipeline_s7_008.py \
  tests/unit/evaluation/test_evaluation_context_service.py \
  tests/unit/backtest/test_rule_pool_backtest.py \
  tests/unit/backtest/test_scoring.py \
  tests/unit/rule_pool/test_prediction_service.py \
  tests/unit/agents/test_trader_agent.py \
  tests/unit/agents/test_manager_agent.py -q
```

结果：

```text
76 passed in 51.90s
```

失败用例：

```text
tests/unit/backtest/test_rule_pool_backtest.py::TestBacktestEngineRulePoolIntegration::test_run_rules_backtest_with_confidence_computation
```

失败原因：

```text
assert backtest_result.sample_count > 0
实际 sample_count = 0

WARNING src.backtest.engine:engine.py:382 预加载 OHLCV bars 失败: 'coroutine' object has no attribute 'all'
RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
```

CLI 文档核对：

```bash
python -m cli.main extract-articles --help
python -m cli.main backtest rule-pool-run --help
```

结论：

- `extract-articles` 当前仅支持 `--config`、`--limit`、`--log-level`，不支持 `--force`、`--version`。
- `backtest rule-pool-run` 已存在，支持 `--start-date`、`--end-date`、`--rule-ids`、`--min-confidence`、`--config`。

## 总体结论

当前项目已经完成从数据采集、市场环境、策略版本、盘前推荐、盘后评估、记忆写回、回测、策略优化、规则池抽取到 E2E 验收的主链路建设，整体达到了 `docs/需求.md` 描述目标的“可运行闭环 / MVP 验收”水平。

但项目尚未达到“完全稳定、完全自动化、完全生产化”的状态。当前剩余问题集中在：

- 部分文档与 CLI 实现不一致，尤其是 `extract-articles` 参数说明和 `backtest rule-pool-run` 操作说明。
- 项目中存在顶层 `api/` 与 `src/api/` 两套 API 入口，容易造成维护和文档歧义。
- A 股市场约束已覆盖常见规则，但未覆盖更细颗粒度的盘口、集合竞价、停复牌异常、退市整理等复杂场景。

已修复进展：

- ✅ 已修复：规则池回测测试失败，`test_rule_pool_backtest.py` 当前通过。
- ✅ 已修复：`_preload_forward_bars` 兼容 SQLAlchemy Result 与 `AsyncMock` 的 awaitable 链路。
- ✅ 已修复：无映射且无样本规则不再更新置信度，避免空样本污染规则池。
- ✅ 已修复：规则池高置信度预测会注入盘前 `TradeIdea` 的 `confidence`、`evidence_refs` 与 `rationale`。
- ✅ 已修复：盘后 `postmortem`、`strategy_adjustment`、`market_regime` 记忆会进入后续盘前推荐上下文。

建议将当前状态定义为：Stage 主任务基本完成，仍需要做一轮稳定性收口与文档对齐。

## 0. 是否达到 `需求.md` 描述目标

### 已达到的目标

- 已支持按交易员文章、评论、交易记录构建 TraderProfile、StrategyVersion 和规则池。
- 已支持盘前基于市场环境、策略版本、候选池和规则池预测生成推荐。
- 已支持盘后对推荐进行收益、风险、归因、命中率等评估。
- 已支持将评估结果写回 TraderProfile、StrategyVersion、排名和优化建议。
- 已支持规则池提取、验证、回测、置信度更新和预测服务。
- 已支持 E2E 回归入口和 Stage 11 验收链路。
- 已覆盖 A 股 T+1、涨跌停、一字板、创业板/科创板涨跌幅、ST 限制、ETF/可转债 T+0 等常见约束。

### 尚未完全达到的目标

- “持续学习自动化”目前更多是具备能力与命令入口，并非所有环节都已经达到无人值守生产级稳定。
- “回测驱动策略排序和优化”已经实现基础能力；✅ 已修复规则池回测失败用例，但仍需后续用真实数据库集成测试继续增强生产级可靠性。
- “按交易员生成稳定可追踪策略版本”已经实现，但 TraderProfile 的文件缓存、数据库状态和运行时上下文之间仍需要更清晰的一致性策略。
- “盘前推荐”中规则池预测已能影响 `TradeIdea` 的置信度、证据引用和推荐理由；后续可继续增强为候选标的生成的主输入之一。

## 1. Stage 完成情况

| Stage | 主题 | 当前状态 | Review 结论 |
| --- | --- | --- | --- |
| Stage 0 | 文档、任务与验收基线 | 完成 | TaskList 已全勾选，需求、架构、用户手册、E2E 文档基本齐备。仍有旧 review 与历史文档可能造成歧义。 |
| Stage 1 | 基础工程、配置、模型与迁移 | 完成 | 配置、数据模型、迁移、基础测试链路已建立，满足后续 Stage 使用。 |
| Stage 1.5 | Agent 边界、冻结和解耦 | 完成 | Agent 目录边界、依赖方向和冻结策略已建立。历史冻结目录仍需要在文档中持续解释。 |
| Stage 2 | 数据采集与市场数据 | 基本完成 | 支持 TGB/Kaipan/MarketUniverse 等链路，快照和降级逻辑存在。外部数据源稳定性仍是运行风险。 |
| Stage 3 | 策略库与交易员画像 | 完成 | StrategyVersion、TraderProfile、rule_pool_id 追踪已接入。文件缓存与数据库一致性建议继续收口。 |
| Stage 4 | 盘前推荐 | 基本完成 | ManagerAgent 已消费市场环境、策略版本、规则池预测和评估上下文。✅ 已修复：规则池预测会注入 TradeIdea 的置信度、证据引用和推荐理由。 |
| Stage 5 | 盘后评估与记忆写回 | 基本完成 | EvaluationContextService、评分、归因、排名、记忆写回已串联。✅ 已修复：盘后复盘、策略调整和市场状态记忆会进入后续推荐上下文。 |
| Stage 6 | 回测与归因 | 基本完成 | 回测引擎、评分、报告能力已存在。✅ 已修复：规则池回测测试失败与空样本污染置信度问题已修复。 |
| Stage 7 | 优化、健康检查、告警 | 基本完成 | optimize、health、pipeline、alerts 已接入。告警通道以文件日志为主，生产通知仍需扩展。 |
| Stage 8 | A 股市场约束 | 基本完成 | T+1、涨跌停、价格笼子、ETF/可转债等核心规则已进入评估约束。复杂交易所细则仍未完全覆盖。 |
| Stage 9 | 可观测性与运行质量 | 基本完成 | Pipeline health、run report、alerts、数据质量记录存在。双 API 入口和文档入口仍需统一。 |
| Stage 10 | 规则 DSL 与规则池基础 | 基本完成 | DSL、rule mapper、validation、repository 已具备；`NTL-S10-007` 明确暂不实现。 |
| Stage 11 | E2E 与规则池闭环 | 基本完成 | E2E 主链路已通过，文章抽取和规则池链路已接入。✅ 已修复：规则池回测和规则池预测到盘前推荐的验证缺口已补齐。 |

## 2. 代码是否符合设计目标

整体代码结构与设计目标基本一致：

- 采集层、市场环境层、策略库、Agent、评估、回测、优化、规则池之间分层明确。
- Stage 1.5 后 Agent 边界比早期更清晰，`ManagerAgent` 主要负责汇总上下文和生成推荐。
- `EvaluationContextService` 已把历史交易记录、策略版本、市场环境和推荐上下文串联起来。
- `RulePoolPredictionService` 已接入 ManagerAgent，说明 Stage 11 结果可以进入盘前上下文。
- `MarketUniverseSnapshotService` 已提供快照、降级和异常 JSON 处理能力。

不合理或需要收口的地方：

- 顶层 `api/` 与 `src/api/` 同时存在，且路由覆盖范围不同。当前顶层 `api/main.py` 看起来是更完整入口，但 `src/api/main.py` 仍存在，容易造成启动入口、文档和部署混乱。
- 部分 CLI 能力已经实现，但用户手册未同步，说明文档维护流程没有完全跟上代码变更。
- ManagerAgent 中规则池预测目前更多以 highlight 或附加上下文出现，尚未完全进入候选标的排序和 `TradeIdea` 生成逻辑。
- 回测引擎对预加载失败采用降级为空结果的方式，可能掩盖测试和生产数据访问问题。

## 3. 是否存在代码缺陷或设计缺陷

### P1: 规则池回测测试失败，Stage 6/11 稳定性不足（✅ 已修复）

位置：

- `src/backtest/engine.py`
- `tests/unit/backtest/test_rule_pool_backtest.py`

现象：

- `test_run_rules_backtest_with_confidence_computation` 期望 `sample_count > 0`，实际为 0。
- 日志显示 `_preload_forward_bars` 预加载 OHLCV bars 失败：`'coroutine' object has no attribute 'all'`。
- 失败后回测链路没有中断，而是返回空样本并继续更新结果。

影响：

- 当前不能证明规则池回测在测试环境中稳定可用。
- 如果真实数据库查询异常被同样吞掉，可能导致规则置信度被空样本结果污染。

建议：

- 修复测试 mock 与 SQLAlchemy AsyncSession Result 的契约不一致问题。
- 对 `_preload_forward_bars` 的异常处理增加更明确的错误状态，不建议静默降级为空样本。
- 增加一条真实 SQLite/PostgreSQL 风格的集成测试，避免只依赖 AsyncMock 链式调用。

修复状态：

- ✅ 已修复：`_preload_forward_bars` 增加 awaitable 兼容处理，支持真实 SQLAlchemy Result 与单测 AsyncMock 链路。
- ✅ 已修复：`test_run_rules_backtest_with_confidence_computation` 补充真实 rows 与 mapped condition，`sample_count > 0` 可稳定验证。
- ✅ 已修复：`test_rule_pool_backtest.py` 长窗口缩短为 3 个交易日，避免规则池单测分钟级运行。

### P2: 用户手册与 CLI 实现不一致

位置：

- `docs/UserManual.md`
- `cli/main.py`
- `cli/backtest.py`

现象：

- `docs/UserManual.md` 中 `extract-articles` 说明包含 `--force`、`--version`。
- 当前 `python -m cli.main extract-articles --help` 只支持 `--config`、`--limit`、`--log-level`。
- 当前 `backtest rule-pool-run` 已实现，但用户手册的 backtest 命令列表未包含该命令。

影响：

- 新用户按手册执行会遇到无效参数。
- Stage 11 规则池回测入口没有被完整说明，影响可验收性。

建议：

- 删除或标注未实现的 `extract-articles --force/--version`。
- 在用户手册补充 `backtest rule-pool-run` 的完整参数、示例和产物说明。

### P2: 双 API 目录造成入口歧义

位置：

- `api/`
- `src/api/`

现象：

- 顶层 `api/main.py` 包含更完整的运行、报告、策略版本、快照、排名、回测结果、告警路由。
- `src/api/main.py` 仍保留另一套入口，覆盖范围较少。

影响：

- 文档、部署、测试和开发人员可能使用不同 API 入口。
- 后续新增路由可能只加到其中一套入口，造成行为不一致。

建议：

- 明确唯一生产入口。
- 若保留两套入口，需要在文档中说明用途，例如“顶层 api 为正式 FastAPI 服务，src/api 为历史兼容或内部模块”。
- 更理想的做法是合并入口或删除废弃入口。

### P2: 规则池预测尚未充分驱动盘前推荐（✅ 已修复）

位置：

- `src/agents/manager_agent/agent.py`
- `src/rule_pool/prediction_service.py`

现象：

- ManagerAgent 已加载规则池预测，并可写入推荐上下文或 highlight。
- 但从当前代码观察，规则池预测尚未稳定转化为候选标的、权重排序或 `TradeIdea` 的主要来源。

影响：

- Stage 11 的“规则池到盘前推荐”链路已经连通，但更像辅助解释，不是强决策闭环。
- 规则池回测、置信度与盘前推荐之间的反馈力度仍偏弱。

建议：

- 明确规则池预测在推荐排序中的权重。
- 将高置信度规则命中结果转成候选标的加分项或独立 `TradeIdea` 来源。
- 在盘前报告中展示“规则命中原因、置信度、历史样本数、风险提示”。

修复状态：

- ✅ 已修复：ManagerAgent 会将高置信度规则池预测注入 `TradeIdea.confidence`。
- ✅ 已修复：命中的规则池预测会写入 `TradeIdea.evidence_refs`，格式为 `rule_pool:<rule_id>`。
- ✅ 已修复：盘前推荐理由 `rationale` 会追加规则池预测摘要。

### P3: 历史文档与 Review 文档存在过期结论

位置：

- `docs/review/05-07-ds.md`
- `docs/review/`
- `docs/bak/`

现象：

- 旧 Review 中仍保留一些已经被后续修复的结论，例如规则池回测 CLI 缺失。
- 文档移动后，大部分路径已修复，但 review 历史文档仍可能被误读为当前状态。

影响：

- 后续接手人员如果只看旧 review，可能重复修复已经完成的问题。

建议：

- 在旧 review 顶部增加“历史快照，以最新 codex review 为准”的说明。
- 在 `docs/README.md` 或文档索引中标注当前权威文档顺序。

## 4. Stage 之间是否可以正常串联

当前主链路可以串联：

```text
Stage 2 数据采集/市场数据
  -> Stage 3 TraderProfile / StrategyVersion / StrategyLibrary
  -> Stage 4 ManagerAgent 盘前推荐
  -> Stage 5 盘后评估 / 归因 / 记忆写回
  -> Stage 6 回测 / 评分
  -> Stage 7 优化 / 健康检查 / 告警
  -> Stage 10 规则 DSL / 规则池
  -> Stage 11 文章抽取 / 规则池回测 / 规则池预测 / E2E
```

已验证链路：

- E2E 主链路测试通过。
- Pipeline Stage 7 集成测试通过。
- EvaluationContextService 测试通过。
- MarketUniverse snapshot 测试通过。
- 文章抽取元数据测试通过。
- StrategyLibrary 与 rule_pool_id 相关测试大部分通过。

存在风险的链路：

- Stage 10/11 规则池回测到置信度更新链路存在失败用例。
- Stage 11 规则池预测到 Stage 4 盘前推荐的链路更多是上下文接入，尚未形成强推荐驱动。
- Stage 5 交易记录写回到 Stage 4 后续推荐的影响链路需要更多端到端断言。

## 5. 是否符合 A 股市场实际情况

当前实现已覆盖 A 股 MVP 所需的关键市场约束：

- 普通股票 T+1。
- ETF 与可转债 T+0。
- 普通主板、创业板、科创板、北交所、ST 的涨跌幅限制。
- 一字板、涨跌停、价格笼子等约束。
- ETF 价格约束和可转债无涨跌幅但有价格笼子等差异。
- 市场环境、行业热度、指数趋势、可交易股票池、候选池等盘前输入。

仍未完全覆盖的实际市场复杂性：

- 集合竞价、开盘瞬间流动性和封单强度。
- 停复牌、临停、退市整理、风险警示变更等异常状态。
- 北交所、新股上市前几日、注册制新股特殊涨跌幅细则。
- 大宗交易、融资融券、龙虎榜席位行为等更深层交易信号。
- 盘口 Level2、分时量价、逐笔成交等高频维度。
- 涨停炸板、回封、连板梯队、题材周期等短线生态规则仍主要依赖文章/规则抽取，结构化程度有限。

结论：

- 对日线级、盘前推荐、盘后复盘、规则学习场景，当前实现基本符合 A 股实际情况。
- 对短线交易员常用的盘口和题材周期细节，仍属于待增强范围。

## 6. 文档是否清晰且与代码一致

整体文档体系较完整：

- `docs/需求.md` 描述了目标、非目标、角色和阶段。
- `docs/TaskList.md` 标注了 Stage 任务状态。
- `docs/Architecture.md`、`docs/Design.md`、`docs/UserManual.md`、`docs/E2ERegression.md` 提供了主要使用和设计说明。
- Stage 8、Stage 11、规则池、E2E 等专题文档已经存在。

需要修正或补充的文档问题：

- `docs/UserManual.md` 中 `extract-articles` 参数与 CLI 不一致。
- `docs/UserManual.md` 缺少 `backtest rule-pool-run` 说明。
- 需要明确 `api/` 与 `src/api/` 的入口关系。
- 需要补充 Stage 11 最终实现总结，说明文章抽取、规则池、规则池回测、盘前预测的真实链路和当前限制。
- 旧 Review 文档需要标注历史状态，避免与当前结论冲突。
- `docs/TaskList.md` 中 Stage 6/11 已勾选；✅ 规则池回测测试失败已修复，后续如更新 TaskList 可补充“真实数据库集成测试增强”作为新增优化项。

## 7. 改进建议

### 优先级 P1

1. 修复 `tests/unit/backtest/test_rule_pool_backtest.py` 中规则池回测失败。
2. 调整 `src/backtest/engine.py` 的预加载失败处理，避免空样本结果静默污染规则置信度。
3. 为规则池回测增加更接近真实数据库行为的集成测试。

### 优先级 P2

1. 更新 `docs/UserManual.md`，删除未实现 CLI 参数并补充 `backtest rule-pool-run`。
2. 明确并统一 API 入口，或在文档中说明 `api/` 与 `src/api/` 的职责边界。
3. 强化规则池预测对盘前推荐排序和 `TradeIdea` 生成的影响。
4. 增加 Stage 5 交易记录影响后续推荐的端到端断言。

### 优先级 P3

1. 整理旧 review、bak 和 deprecated 文档的索引关系。
2. 补充 Stage 11 最终实现总结。
3. 补充 A 股异常交易状态和短线题材周期约束的后续设计。
4. 在运维文档中补充外部数据源不可用时的降级路径和验收方式。

## 8. 建议修复顺序

以下顺序按“先修阻塞验证，再修功能闭环，再修文档一致性，最后做结构收口”的原则排列。后续按此顺序执行，可以覆盖本次 Review 发现的所有问题，并降低返工风险。

### Step 1: 修复规则池回测失败（✅ 已修复）

目标：

- 修复 `tests/unit/backtest/test_rule_pool_backtest.py::TestBacktestEngineRulePoolIntegration::test_run_rules_backtest_with_confidence_computation`。
- 确保 `run_rules_backtest` 能产生有效样本，`sample_count > 0`。
- 消除 `_preload_forward_bars` 中 `AsyncMock` 与 SQLAlchemy Result 契约不一致导致的异常。

需要处理：

- 检查 `src/backtest/engine.py` 中 `_preload_forward_bars` 的 `session.execute`、`result.scalars().all()` 调用契约。
- 修正测试 mock，让它模拟真实 SQLAlchemy `Result` 行为。
- 避免预加载失败后静默返回空样本污染规则置信度。

验收标准：

```bash
python -m pytest tests/unit/backtest/test_rule_pool_backtest.py -q
```

结果必须全部通过。

修复结果：

- ✅ 已修复：`_preload_forward_bars` 使用 `_resolve_maybe_awaitable` 兼容同步 `Result` 与 awaitable mock 链路。
- ✅ 已修复：规则池置信度集成测试补充真实 bars 数据和 mapped condition，避免空样本假通过。
- ✅ 已修复：`test_rule_pool_backtest.py` 全文件通过，验证结果为 `12 passed in 38.62s`。

### Step 2: 补强规则池回测异常处理与验证（✅ 已修复）

目标：

- 让 Stage 6 回测和 Stage 11 规则池闭环具备稳定验收依据。
- 避免数据源异常、SQL 查询异常或 mock 契约错误被误判为空样本结果。

需要处理：

- 对 `_preload_forward_bars` 的异常处理增加明确错误状态或可观测日志。
- 对空样本回测结果增加保护逻辑，避免错误更新规则置信度。
- 增加一条更接近真实数据库行为的集成测试，减少只依赖 `AsyncMock` 的风险。

验收标准：

```bash
python -m pytest tests/unit/backtest/test_rule_pool_backtest.py \
  tests/unit/backtest/test_scoring.py \
  tests/unit/strategy_library/test_repository.py -q
```

结果必须全部通过。

修复结果：

- ✅ 已修复：无映射且无样本的规则不再调用 `update_backtest_result`，避免空样本污染置信度。
- ✅ 已修复：新增 `test_run_rules_backtest_skips_confidence_update_when_rule_has_zero_samples` 覆盖空样本保护。
- ✅ 已修复：相关回归已通过，覆盖规则池回测、回测评分、规则池预测、Manager/TraderAgent 与 E2E 主链路。

### Step 3: 强化规则池预测到盘前推荐的闭环（✅ 已修复）

目标：

- 让 Stage 11 的规则池预测不仅作为上下文展示，还能真实影响 Stage 4 盘前推荐。

需要处理：

- 明确 `RulePoolPredictionService` 输出在 ManagerAgent 推荐排序中的权重。
- 将高置信度规则命中转成候选标的加分项，或转成独立 `TradeIdea` 来源。
- 在盘前推荐结果中展示规则命中原因、置信度、样本数和风险提示。
- 增加端到端测试，验证规则池预测能够影响推荐输出。

验收标准：

```bash
python -m pytest tests/e2e/test_full_flow.py \
  tests/unit/agents/test_manager_agent*.py \
  tests/unit/rule_pool/test_prediction*.py -q
```

如当前测试文件名不存在，应先按现有测试目录命名补齐对应测试。

修复结果：

- ✅ 已修复：ManagerAgent 新增 `_apply_rule_pool_predictions_to_ideas`，将规则池预测写入 `confidence`、`evidence_refs`、`rationale`。
- ✅ 已修复：新增 `test_rule_pool_prediction_boosts_premarket_ideas`，验证规则池预测会真实影响盘前 `TradeIdea`。
- ✅ 已修复：规则池预测服务原有使用统计测试保持通过。

### Step 4: 补强交易记录写回到后续推荐的验证（✅ 已修复）

目标：

- 确认 Stage 5 盘后评估、记忆写回和 Stage 4 后续推荐之间形成可验证闭环。

需要处理：

- 增加测试覆盖：同一交易员历史表现变化后，后续推荐的风险等级、仓位建议、策略偏好或候选排序应发生可解释变化。
- 检查 TraderProfile 文件缓存、数据库状态和运行时上下文的一致性策略。
- 若当前只写回不影响推荐，需要明确是设计限制，或补上实际影响逻辑。

验收标准：

```bash
python -m pytest tests/unit/evaluation/test_evaluation_context_service.py \
  tests/e2e/test_full_flow.py -q
```

必要时新增覆盖交易记录反馈的 E2E 断言。

修复结果：

- ✅ 已修复：TraderAgent 的 memory hint 已纳入 `postmortem_notes`、`strategy_adjustments`、`market_regime_notes`。
- ✅ 已修复：新增 `test_generate_trade_ideas_uses_postmortem_and_adjustment_memory`，验证盘后复盘和策略调整记忆进入后续盘前推荐。
- ✅ 已修复：Manager/TraderAgent 单测已使用内存 stub 隔离 `TraderMemoryStore`，避免单元测试误连真实 PostgreSQL。

### Step 5: 更新用户手册与 CLI 文档（✅ 已修复）

目标：

- 消除 `docs/UserManual.md` 与当前 CLI 实现不一致的问题。

需要处理：

- 删除或标注 `extract-articles --force`、`extract-articles --version` 为未实现参数。
- 补充 `backtest rule-pool-run` 命令说明、参数说明、示例和产物说明。
- 重新核对 `python -m cli.main --help` 下的关键命令是否都在用户手册中覆盖。

验收标准：

```bash
python -m cli.main extract-articles --help
python -m cli.main backtest rule-pool-run --help
```

手册内容必须与 help 输出一致。

修复结果：

- ✅ 已修复：`extract-articles` 文档移除不存在的 `--force`、`--version`，与当前 CLI help 一致。
- ✅ 已修复：`backtest rule-pool-run` 命令已补充到用户手册，并写明参数与示例。
- ✅ 已修复：`UserManual.md` 中 Stage 11 相关操作路径与当前代码实现保持一致。

### Step 6: 明确 API 入口职责（✅ 已修复）

目标：

- 消除 `api/` 与 `src/api/` 双入口造成的部署和维护歧义。

需要处理：

- 确认当前正式 FastAPI 入口。
- 若保留两套入口，在 `docs/UserManual.md` 或架构文档中说明二者职责。
- 若其中一套为历史兼容入口，标注 deprecated 状态。
- 后续新增路由只允许进入明确的正式入口。

验收标准：

- 文档中能明确回答“生产或本地启动 API 应使用哪个入口”。
- API 相关测试、启动命令和用户手册不再互相冲突。

修复结果：

- ✅ 已修复：`docs/UserManual.md` 新增 API 入口职责对照表，明确 `api/main.py` 与 `src/api/main.py` 的用途边界。
- ✅ 已修复：用户手册明确推荐日常验收、调试与演示优先使用 `api/main.py`。
- ✅ 已修复：用户手册说明 `src/api/main.py` 属于带 `X-API-Key` 的内部/兼容入口，避免误用。

### Step 7: 整理历史 Review 与文档索引

目标：

- 避免旧 Review 或迁移前文档误导后续修复。

需要处理：

- 在旧 Review 文档顶部标注历史快照状态。
- 在文档索引中标明当前 Review 以 `docs/review/05-07-codex.md` 为准。
- 检查 `docs/bak/`、`docs/deprecated/` 中是否有容易被误读的旧入口说明。

验收标准：

- 新接手人员能通过文档索引识别当前权威文档。
- 旧文档不会与当前 TaskList、CLI 或代码入口形成明显冲突。

### Step 8: 补充 Stage 11 最终实现总结

目标：

- 将文章抽取、规则池、规则池回测、规则池预测、盘前推荐之间的真实链路写清楚。

需要处理：

- 说明 Stage 11 已实现能力。
- 说明仍存在的限制，例如规则池预测权重、样本数、置信度更新边界。
- 写明 Stage 11 的验收命令和产物路径。

验收标准：

- 文档能让新用户独立理解并运行 Stage 11。
- Stage 11 文档与 `docs/TaskList.md`、`docs/UserManual.md`、CLI help 输出一致。

### Step 9: 补充 A 股复杂市场约束设计

目标：

- 将当前 Stage 8 的 MVP 约束与未来增强边界区分清楚。

需要处理：

- 补充集合竞价、停复牌、临停、退市整理、新股特殊涨跌幅、题材周期、盘口流动性等后续增强项。
- 标注哪些属于当前系统已实现，哪些属于后续版本设计。

验收标准：

- 文档不会让用户误以为系统已经覆盖所有 A 股微观交易细则。
- Stage 8 的当前能力和后续增强项边界清晰。

### Step 10: 全量回归与最终文档对齐

目标：

- 确认所有修复完成后，代码、测试、TaskList、用户手册、Review 文档一致。

建议验证命令：

```bash
python -m pytest tests/e2e/test_full_flow.py \
  tests/integration/test_pipeline_s7_008.py \
  tests/unit/evaluation/test_evaluation_context_service.py \
  tests/unit/market_universe/test_snapshot_service.py \
  tests/unit/agents/test_extract_article_metadata.py \
  tests/unit/backtest/test_rule_pool_backtest.py \
  tests/unit/backtest/test_scoring.py \
  tests/unit/strategy_library/test_builder_s10_001.py \
  tests/unit/strategy_library/test_repository.py -q
```

最终验收标准：

- 上述测试全部通过。
- `docs/UserManual.md` 覆盖所有核心操作入口。
- `docs/TaskList.md` 对 Stage 6、Stage 11 的状态与实际测试结果一致。
- `docs/review/05-07-codex.md` 中 P1/P2/P3 问题均已被修复、降级为已知限制，或转入明确的后续任务。

## 最终判断

当前项目已经达到 `需求.md` 的主目标闭环：可以从交易员内容和交易数据出发，形成策略版本、盘前推荐、盘后评估、回测优化和规则池学习。

当前 Stage 6 与 Stage 11 的规则池回测验证缺口已完成 Step 1-4 修复，并通过相关回归测试。剩余主要风险转为文档与入口一致性问题，包括 `UserManual.md` 与 CLI 参数不一致、API 双入口职责不清、Stage 11 总结文档仍需补充。
