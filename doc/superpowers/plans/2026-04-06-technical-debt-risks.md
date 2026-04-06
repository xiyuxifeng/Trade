# 技术债务与风险记录

> 创建时间：2026-04-06
> 记录目的：追踪实现过程中发现的设计问题和风险，供后续迭代参考。

---

## T1: DuckDB JSON 字段存储为 TEXT，应用层需 parse

**严重程度**：低（可工作）
**影响范围**：`export_task` 导出到 DuckDB 的所有 JSON 字段（`extracted_concepts`, `trading_symbols`, `strategy_rules`, `preconditions`, `comment_insights`, `raw_llm_output`）

**现状**：
- DuckDB 原生支持 JSON 类型，但当前 export_task 将 JSON 字段直接存储为 TEXT
- 查询时需要 `json_extract(col, '$.key')` 或 `json(col)` 手动解析

**后续处理**：
- 在 `export_task.py` 中将 TEXT 列改为 DuckDB JSON 类型
- 验证查询语句兼容性和性能差异
- 涉及文件：`src/pipeline/tasks/export_task.py`

**相关任务**：P1-026B（待追加到 TaskList）

---

## T2: export_task 当前从 SQLite 读取（本地调试），生产需确认 PostgreSQL 连接

**严重程度**：中（影响生产部署）
**影响范围**：`export_task` 数据源切换

**现状**：
- `export_task.py` 目前硬编码读取 `data/trade_strategy_ai.db`（SQLite）
- 尚未验证 PostgreSQL 连接和增量查询逻辑

**后续处理**：
- 确认 PostgreSQL 连接字符串（`DATABASE_URL`）
- 实现 `get_source_db_engine()` 函数，根据配置选择 SQLite 或 PostgreSQL
- 增量查询逻辑：`id > max_id` 在 PostgreSQL 下验证
- 涉及文件：`src/pipeline/tasks/export_task.py`

**相关任务**：P1-026C（待追加到 TaskList）

---

## T3: run_process_tasks config 传入方式使用 global 模式，非最佳实践但可工作

**严重程度**：低（技术债务）
**影响范围**：`src/pipeline/tasks/process_tasks.py`

**现状**：
- `run_process_tasks()` 内部调用 `get_app_config()` 获取全局配置
- 未通过参数显式注入 config，测试时需要 mock 或环境变量

**后续处理**：
- 重构为 `run_process_tasks(config: AppConfig, ...)` 参数传入模式
- 保持向后兼容：默认 `config=None` 时使用 `get_app_config()`
- 涉及文件：`src/pipeline/tasks/process_tasks.py`, `src/pipeline/dag.py`

**相关任务**：P1-026D（待追加到 TaskList）

---

## T4: pending_tasks 处理器处理完成后清空 pending_tasks.jsonl，failed_tasks 持久化

**严重程度**：低（设计权衡）
**影响范围**：`process_tasks.py` 任务持久化策略

**现状**：
- 成功处理的任务从 `pending_tasks.jsonl` 中移除
- 失败任务写入 `failed_tasks.jsonl`（持久化，不会自动重试）
- 处理器运行后 `pending_tasks.jsonl` 为空，即使有失败也不会保留

**问题**：
- `failed_tasks.jsonl` 中的任务不会自动重试（需要人工介入或单独工具处理）
- 如果 `failed_tasks.jsonl` 累积，需要定期清理机制

**后续处理**：
- 方案 A（推荐）：在 `failed_tasks.jsonl` 中增加 `retry_after` 字段，达到时间条件后自动移回 `pending_tasks.jsonl`
- 方案 B：提供 CLI 命令手动将 `failed_tasks` 移回 `pending_tasks`
- 方案 C：定期清理 `failed_tasks.jsonl`（如保留 7 天后删除）
- 涉及文件：`src/pipeline/tasks/process_tasks.py`

**相关任务**：P1-026E（待追加到 TaskList）

---

## 追加到 TaskList 的任务汇总

| 任务 ID | 描述 | 优先级 | 所属阶段 |
|---------|------|--------|----------|
| P1-026B | DuckDB JSON 字段改为原生 JSON 类型 | P2 | Phase 1 |
| P1-026C | export_task 支持 PostgreSQL 数据源 | P1 | Phase 1 |
| P1-026D | run_process_tasks 改为显式 config 参数注入 | P3 | Phase 1 |
| P1-026E | failed_tasks.jsonl 增加自动重试或定期清理机制 | P2 | Phase 1 |
