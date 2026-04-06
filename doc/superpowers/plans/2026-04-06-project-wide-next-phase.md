# Project-Wide Next Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按“运行闭环主线 -> 数据输入主线 -> 服务化主线”的顺序，推进下一阶段 8 项核心功能，把当前 `crawl -> store -> extract -> clusters -> pre-market -> evaluation` 的最小闭环升级为可持续演进的 Trader 画像、记忆、建议、复盘系统。

**Architecture:** 先在现有 `ManagerAgent + TraderAgent + persona/metadata/pipeline` 基础上补齐 `TraderProfile`、`TraderMemory`、复盘任务与写回链路，让系统先拥有真实的“建议生成 + 盘后反馈 + 自反馈”能力。随后只补支撑闭环所必需的数据输入能力（交易记录、市场数据、动态抓取），最后再通过 FastAPI / host 薄壳把已稳定的能力对外暴露，避免过早把未成熟逻辑服务化。

**Tech Stack:** Python 3.11+, pytest/pytest-asyncio, SQLAlchemy async, PostgreSQL, DuckDB, Typer CLI, Pydantic, Jinja2 HTML reports

---

## Priorities

1. 运行闭环主线：Trader 画像、记忆、建议生成、盘后复盘写回
2. 数据输入主线：动态抓取、交易记录解析、市场数据接入
3. 服务化主线：查询 API、触发接口、host 薄壳

---

## Next 8 Tasks

### Task 1: 建立 TraderProfile 最小画像层

**目标：** 把现有 `article_metadata`、`clusters.real.json`、`crawl.sources.trader_id` 绑定结果，沉淀为可持续读取的 trader 画像，而不是每次运行时临时拼接。

**Files:**
- Create: `trade-strategy-ai/src/trader_profile/service.py`
- Create: `trade-strategy-ai/src/trader_profile/schemas.py`
- Modify: `trade-strategy-ai/src/persona/cluster_builder.py`
- Modify: `trade-strategy-ai/src/agents/data_agent/skills/extract_article_metadata.py`
- Test: `trade-strategy-ai/tests/unit/trader_profile/test_service.py`

- [ ] 定义 `TraderProfile` 字段：风格标签、题材偏好、常见标的、纪律偏好、证据来源、更新时间。
- [ ] 实现从 `article_metadata + cluster` 生成轻量画像的聚合服务。
- [ ] 为画像聚合增加单元测试，覆盖空数据、单 trader、多 trader 三种场景。
- [ ] 验证画像文件或表结构能够被 `TraderAgent` 直接读取。

### Task 2: 建立 TraderMemory 最小记忆层

**目标：** 先落地“成功案例 / 失败案例 / 复盘结论”三类记忆，解决当前系统没有历史反馈可复用的问题。

**Files:**
- Create: `trade-strategy-ai/src/trader_memory/service.py`
- Create: `trade-strategy-ai/src/trader_memory/schemas.py`
- Modify: `trade-strategy-ai/src/agents/manager_agent/agent.py`
- Test: `trade-strategy-ai/tests/unit/trader_memory/test_service.py`

- [ ] 定义 `TraderMemoryItem` 与索引键（`trader_id + memory_type + as_of_date`）。
- [ ] 实现 append / list_recent / search_by_symbol 的最小接口。
- [ ] 约束 JSONL 或数据库存储格式，先选一种最小可用方案，不同时维护两套。
- [ ] 为记忆写入与读取补单元测试。

### Task 3: 重构 TraderAgent 建议生成逻辑

**目标：** 把当前基于 watchlist 和固定比例的建议生成，升级为“画像 + 记忆 + 市场数据”的结构化建议生成。

**Files:**
- Modify: `trade-strategy-ai/src/agents/trader_agent/agent.py`
- Modify: `trade-strategy-ai/src/schemas/contracts.py`
- Test: `trade-strategy-ai/tests/unit/agents/test_trader_agent.py`

- [ ] 给 `TraderAgent` 注入 `TraderProfile` 和 `TraderMemory` 读取能力。
- [ ] 让建议理由引用画像与历史记忆证据，而不是只拼默认文案。
- [ ] 保持当前 `TradeIdea` 契约兼容，不提前扩大字段面。
- [ ] 补齐 trader agent 单测，覆盖有画像/无画像、有记忆/无记忆两类退化路径。

### Task 4: 强化 ManagerAgent 的盘前汇总与冲突处理

**目标：** 避免多个 Trader 建议简单拼接，补齐盘前去重、冲突提示和统一风险摘要。

**Files:**
- Modify: `trade-strategy-ai/src/agents/manager_agent/agent.py`
- Modify: `trade-strategy-ai/src/reporting/html_reports.py`
- Test: `trade-strategy-ai/tests/unit/agents/test_manager_agent.py`

- [ ] 定义同 symbol 多建议的冲突合并规则。
- [ ] 在 `DailyReport` 里增加冲突说明和风险摘要来源。
- [ ] 保持 HTML 报告渲染兼容已有产物。
- [ ] 为 pre-market 汇总新增回归测试。

### Task 5: 扩展盘后考核为复盘任务生成

**目标：** 当前 `run_after_close()` 已能做收益评估，但还没有真正把“不达标/亏损”转成可消费复盘任务。

**Files:**
- Modify: `trade-strategy-ai/src/agents/manager_agent/agent.py`
- Modify: `trade-strategy-ai/src/schemas/contracts.py`
- Test: `trade-strategy-ai/tests/unit/agents/test_manager_agent.py`

- [ ] 把低收益/亏损评估结果写成标准复盘任务对象。
- [ ] 明确触发阈值与复盘原因字段，避免后续写回时丢上下文。
- [ ] 保持 `EvaluationResult` 对已有 HTML 输出兼容。
- [ ] 补齐盘后复盘任务生成测试。

### Task 6: 实现复盘任务消费与记忆写回

**目标：** 把复盘任务真正消费掉并写回 `TraderMemory`，形成闭环。

**Files:**
- Create: `trade-strategy-ai/src/review_tasks/service.py`
- Modify: `trade-strategy-ai/src/pipeline/tasks/process_tasks.py`
- Modify: `trade-strategy-ai/src/trader_memory/service.py`
- Test: `trade-strategy-ai/tests/unit/pipeline/test_process_tasks.py`

- [ ] 为复盘任务定义处理入口，与现有 `pending_tasks` 机制对齐。
- [ ] 处理成功后把复盘结论写回 `TraderMemory`。
- [ ] 失败时沿用现有 failed/dead task 机制，不单开第二套重试系统。
- [ ] 补齐 process task 回归测试。

### Task 7: 补齐支撑闭环的最小数据输入能力

**目标：** 不追求一口气做完所有数据层，而是优先补齐支撑画像/复盘的输入缺口。

**Files:**
- Modify: `trade-strategy-ai/src/agents/data_agent/skills/crawl_dynamic.py`
- Create: `trade-strategy-ai/src/agents/data_agent/skills/import_trade_logs.py`
- Modify: `trade-strategy-ai/src/agents/data_agent/skills/fetch_market.py`
- Modify: `trade-strategy-ai/src/pipeline/dag.py`
- Test: `trade-strategy-ai/tests/unit/agents/test_crawl_blog.py`
- Test: `trade-strategy-ai/tests/unit/agents/test_data_agent.py`

- [ ] 实现 Playwright 动态抓取最小入口，只覆盖当前目标站点必需场景。
- [ ] 增加交易记录 CSV/HTML 导入入口，先支持最小字段集。
- [ ] 把市场数据接入扩展到能支撑盘后考核与画像统计。
- [ ] 为新增数据输入能力补回归测试。

### Task 8: 服务化暴露稳定能力

**目标：** 在闭环与数据输入稳定后，再提供查询与触发接口，避免过早服务化。

**Files:**
- Create: `trade-strategy-ai/api/main.py`
- Create: `trade-strategy-ai/api/routers/report.py`
- Create: `trade-strategy-ai/api/routers/run.py`
- Modify: `trade-strategy-ai/src/host/handler.py`
- Test: `trade-strategy-ai/tests/integration/test_api.py`

- [ ] 提供最小查询接口：日报、考核报告、persona route。
- [ ] 提供最小触发接口：`run_pre_market`、`run_after_close`。
- [ ] 保持 host handler 与 API 共用同一套核心调用，不复制业务逻辑。
- [ ] 补齐 API 集成测试。

---

## Verification

- `make smoke`
- `pytest -q`
- `python -m cli.main e2e-regression --config config/app.yaml --max-articles 1 --extract-limit 1`
- 画像、记忆、复盘三个新增模块都至少有对应单测

## Phase Gate

- Task 1-3 完成后，系统才具备最小“画像驱动建议”能力。
- Task 4-6 完成后，系统才具备真正的“盘后复盘写回”闭环。
- Task 7 完成后，画像与复盘所依赖的数据输入主线才算基本可用。
- Task 8 最后执行，避免把未成熟逻辑提前服务化。
