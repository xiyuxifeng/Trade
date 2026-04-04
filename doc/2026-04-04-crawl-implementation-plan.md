# Crawl Multi-Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为抓取系统增加“同站点多作者、兼容未来多站点”的首版实现，当前落地淘股吧手工 Cookie 增量抓取。

**Architecture:** 在现有配置和 CLI 上增加 `crawl` 配置模型、认证提供者和站点抓取器抽象。抓取主流程只负责遍历 `sources`、调用站点适配器、做去重与落盘；淘股吧解析逻辑独立在站点模块中，后续新站点只需新增适配器实现。

**Tech Stack:** Python 3.11+, Pydantic, Typer, requests/httpx-compatible session patterns, pytest

---

### Task 1: 配置模型与基础单元测试

**Files:**
- Modify: `trade-strategy-ai/src/common/config.py`
- Modify: `trade-strategy-ai/config/app.yaml`
- Modify: `trade-strategy-ai/cli/main.py`
- Test: `trade-strategy-ai/tests/unit/common/test_config.py`

- [ ] Step 1: 先写配置加载失败/成功测试，覆盖 `crawl.auth` 和 `crawl.sources`
- [ ] Step 2: 运行 `pytest trade-strategy-ai/tests/unit/common/test_config.py -v`，确认新字段缺失时失败方式符合预期
- [ ] Step 3: 实现 `crawl` 相关 Pydantic 模型，并更新默认配置模板
- [ ] Step 4: 再次运行 `pytest trade-strategy-ai/tests/unit/common/test_config.py -v`，确认通过

### Task 2: 站点抽象、状态存储与评论清洗

**Files:**
- Create: `trade-strategy-ai/src/agents/data_agent/sites/__init__.py`
- Create: `trade-strategy-ai/src/agents/data_agent/sites/base.py`
- Create: `trade-strategy-ai/src/agents/data_agent/sites/tgb.py`
- Modify: `trade-strategy-ai/src/agents/data_agent/skills/crawl_blog.py`
- Test: `trade-strategy-ai/tests/unit/agents/test_crawl_blog.py`

- [ ] Step 1: 先写失败测试，覆盖评论清洗、作者/读者分类、去重状态判断、站点选择
- [ ] Step 2: 运行 `pytest trade-strategy-ai/tests/unit/agents/test_crawl_blog.py -v`，确认失败点是缺少实现
- [ ] Step 3: 实现最小核心对象与函数：`AuthProvider`、`SiteCrawler`、状态读写、评论清洗、去重判断
- [ ] Step 4: 再次运行 `pytest trade-strategy-ai/tests/unit/agents/test_crawl_blog.py -v`，确认通过

### Task 3: 淘股吧首版适配器与 CLI

**Files:**
- Modify: `trade-strategy-ai/src/agents/data_agent/sites/tgb.py`
- Modify: `trade-strategy-ai/cli/crawl.py`
- Modify: `trade-strategy-ai/cli/main.py`
- Test: `trade-strategy-ai/tests/unit/cli/test_crawl_cli.py`

- [ ] Step 1: 先写 CLI 与适配器接线测试，覆盖多作者遍历和输出目录
- [ ] Step 2: 运行 `pytest trade-strategy-ai/tests/unit/cli/test_crawl_cli.py -v`，确认失败
- [ ] Step 3: 实现 `crawl` CLI 命令、接入配置、遍历 `crawl.sources` 调用 `TgbCrawler`
- [ ] Step 4: 再次运行 `pytest trade-strategy-ai/tests/unit/cli/test_crawl_cli.py -v`，确认通过

### Task 4: 定向验证

**Files:**
- Verify: `trade-strategy-ai/tests/unit/common/test_config.py`
- Verify: `trade-strategy-ai/tests/unit/agents/test_crawl_blog.py`
- Verify: `trade-strategy-ai/tests/unit/cli/test_crawl_cli.py`

- [ ] Step 1: 运行 `pytest trade-strategy-ai/tests/unit/common/test_config.py trade-strategy-ai/tests/unit/agents/test_crawl_blog.py trade-strategy-ai/tests/unit/cli/test_crawl_cli.py -v`
- [ ] Step 2: 如失败，修正最小实现后重跑
- [ ] Step 3: 运行 `git diff --stat` 检查改动范围
