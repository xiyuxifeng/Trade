# Project-Wide Next Phase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前已打通的 `crawl -> store -> extract -> clusters -> pre-market -> report` 闭环固化成稳定回归门禁，并继续推进剩余 Phase 1 / Phase 2 主线功能；LLM 抽取 V2 优化延后到整个项目完成后再做。

**Architecture:** 以 `e2e-regression` 作为第一优先级 smoke gate，确保数据绑定、抽取、聚类、路由和报告产物都能稳定生成。随后按“数据接入 -> 认知建模 -> 报告/接口”三条线推进，保持每个阶段都能独立运行、独立验证，避免再出现只能手工跑通但无法回归的状态。

**Tech Stack:** Python 3.11+, pytest/pytest-asyncio, SQLAlchemy async, PostgreSQL, DuckDB, Typer CLI, Pydantic, Jinja2 HTML reports

---

## 文件变更概览

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `trade-strategy-ai/tests/e2e/test_full_flow.py` | Create/Modify | 固化 `e2e-regression` 产物检查与核心路径 smoke test |
| `trade-strategy-ai/tests/unit/common/test_config.py` | Modify | 锁定 `crawl.sources.trader_id` 绑定，防止 clusters 路由回退为空 |
| `trade-strategy-ai/config/app.yaml` | Modify | 当前项目配置默认绑定 `crawl.sources.trader_id` |
| `trade-strategy-ai/cli/main.py` | Modify | 保持 `init-config` 模板与主配置一致 |
| `trade-strategy-ai/src/persona/cluster_builder.py` | Modify | 继续强化 trader 绑定与聚类可解释性 |
| `trade-strategy-ai/src/agents/manager_agent/agent.py` | Modify | 继续强化日报/考核/路由产物的稳定性 |
| `trade-strategy-ai/src/pipeline/tasks/*` | Modify | 继续补齐 pipeline 的失败回归与输入一致性 |

---

## Task 1: 把全链路回归固定成可重复的 smoke gate

**Files:**
- Create: `trade-strategy-ai/tests/e2e/test_full_flow.py`
- Modify: `trade-strategy-ai/cli/main.py`
- Modify: `trade-strategy-ai/tests/unit/common/test_config.py`

- [ ] **Step 1: 写全链路 smoke test**

让测试直接验证官方回归链路的关键产物，而不是只断言某个单点函数。

```python
def test_e2e_regression_produces_report_and_persona_route():
    ...
    assert report_path.exists()
    assert route_path.exists()
    assert daily_report["ideas"]
    assert len(route["decisions"]) > 0
```

- [ ] **Step 2: 运行失败测试并确认能抓到真实问题**

Run: `pytest tests/e2e/test_full_flow.py -q`
Expected: 先失败，原因应来自缺少 smoke test 断言或产物不完整，而不是语法错误。

- [ ] **Step 3: 固化 CLI 入口的一致性**

确保 `e2e-regression`、`run-pre-market`、`clusters-build` 的默认路径与 `config/app.yaml`、`init-config` 模板保持一致，避免“命令能跑但模板生成出来的配置跑不通”。

- [ ] **Step 4: 重新运行 smoke test**

Run: `pytest tests/e2e/test_full_flow.py -q`
Expected: 通过，并能在测试输出里看到 `DailyReport` 与 persona 产物被生成。

- [ ] **Step 5: 运行官方回归命令**

Run: `../.venv/bin/python -m cli.main e2e-regression --max-articles 1 --extract-limit 1`
Expected: `E2E OK. DailyReport ideas=...`，且 `persona_route` 里 `decisions > 0`。

---

## Task 2: 完成 Phase 1 剩余数据输入主线

**Files:**
- Modify: `trade-strategy-ai/src/agents/data_agent/sites/tgb.py`
- Modify: `trade-strategy-ai/src/agents/data_agent/skills/crawl_blog.py`
- Modify: `trade-strategy-ai/src/pipeline/tasks/crawl_task.py`
- Modify: `trade-strategy-ai/src/pipeline/tasks/validate_task.py`
- Test: `trade-strategy-ai/tests/unit/agents/test_crawl_blog.py`

- [ ] **Step 1: 给动态页面抓取补回归测试**

聚焦 Playwright 入口和动态页 fallback，先锁住“能抓到内容”而不是扩展站点能力。

```python
def test_dynamic_crawler_falls_back_when_static_html_is_missing():
    ...
```

- [ ] **Step 2: 运行 crawler 单测并修补**

Run: `pytest tests/unit/agents/test_crawl_blog.py -q`
Expected: crawler 的静态 / 动态分支都能覆盖到，不依赖线上站点才能验证核心行为。

- [ ] **Step 3: 补交易记录解析入口**

把交易记录的 HTML / PDF / CSV 导入边界先钉住，避免 Phase 2 画像阶段数据源继续悬空。

- [ ] **Step 4: 验证 pipeline 输入输出一致性**

Run: `pytest tests/unit/pipeline -q`
Expected: crawl -> clean -> validate -> store 的 JSONL 输出格式保持一致。

---

## Task 3: 完成 Phase 1 的存储、接口和运维缺口

**Files:**
- Modify: `trade-strategy-ai/src/pipeline/tasks/export_task.py`
- Modify: `trade-strategy-ai/src/db/migrations/*`
- Modify: `trade-strategy-ai/src/host/handler.py`
- Modify: `trade-strategy-ai/cli/main.py`
- Test: `trade-strategy-ai/tests/unit/pipeline/test_export_task.py`
- Test: `trade-strategy-ai/tests/integration/test_api.py`

- [ ] **Step 1: 把导出、备份、恢复和审计的边界固定下来**

优先补数据层可靠性，避免后续画像和策略层不断被底层数据问题打断。

- [ ] **Step 2: 给薄壳 API / host command 补回归**

确保 `/host/command`、`run_pre_market`、`run_after_close` 这些入口在未来仍然只是薄壳，不引入第二套逻辑。

- [ ] **Step 3: 运行存储与接口测试**

Run: `pytest tests/unit/pipeline/test_export_task.py tests/integration/test_api.py -q`
Expected: 导出、查询和 host 入口都通过，不再依赖手工 CLI。

---

## Task 4: 推进 Phase 2 核心认知建模

**Files:**
- Modify: `trade-strategy-ai/src/agents/trader_agent/agent.py`
- Modify: `trade-strategy-ai/src/agents/manager_agent/agent.py`
- Modify: `trade-strategy-ai/src/persona/cluster_builder.py`
- Modify: `trade-strategy-ai/src/persona/router.py`
- Test: `trade-strategy-ai/tests/unit/persona/test_router.py`

- [ ] **Step 1: 完成 Trader 画像与记忆存储的最小闭环**

先把文章/交易记录映射到 trader，再让画像能持续积累，而不是一次性脚本式生成。

- [ ] **Step 2: 让 ManagerAgent 的日报 / 考核 / 复盘形成稳定链路**

确保 `run_pre_market`、`run_after_close` 和 HTML 报告能在连续多天回放时稳定工作。

- [ ] **Step 3: 为 persona route / clusters 增加更可解释的产物**

保持当前可回放 JSON 结构不变，只提升输出的稳定性和可解释性，不提前做 V2 的质量优化。

- [ ] **Step 4: 运行 persona / manager 相关测试**

Run: `pytest tests/unit/persona/test_router.py tests/integration/test_agent_coordination.py -q`
Expected: 路由和编排逻辑继续保持可回归。

---

## Task 5: 全项目收口策略

**Files:**
- Modify: `doc/TaskList.md`
- Modify: `daily-report/2026-04-06.md`
- Modify: `daily-sessions/2026-04-06.md`

- [ ] **Step 1: 更新 TaskList 的优先级顺序**

把当前最关键的工作顺序调整为：
1. smoke gate / 回归门禁
2. Phase 1 剩余数据输入与接口
3. Phase 2 核心画像与日报
4. `P2-LLM` 的 V2 优化延后

- [ ] **Step 2: 更新日报里的下一步计划**

把今日结果、已修复问题和下一步路线写清楚，避免后续会话再次从“抽取质量优化”切回。

- [ ] **Step 3: 保持 V2 延后**

`P2-LLM-001/002/003/004` 继续保留在项目完成后的优化阶段，不在下一阶段抢占主线资源。

---

## Phase Gate

- `Task 1` 完成后，才允许把 `e2e-regression` 当作稳定 smoke gate。
- `Task 2` 和 `Task 3` 完成后，Phase 1 才能视为“工程上可继续扩展”。
- `Task 4` 完成后，才进入 Phase 2 的正式画像/记忆/复盘主线。
- `V2` 抽取优化继续后置，等整个项目主线稳定后再启。
