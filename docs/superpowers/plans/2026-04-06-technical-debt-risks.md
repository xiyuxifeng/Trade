# 技术债务与风险记录

> 创建时间：2026-04-06
> 记录目的：追踪实现过程中发现的设计问题和风险，供后续迭代参考。

---

## T1: DuckDB JSON 字段存储/读写一致性

**严重程度**：低（可工作）
**影响范围**：`export_task` 导出到 DuckDB 的所有 JSON 字段（`tags`, `comments_payload`, `raw_payload`, `extracted_concepts`, `trading_symbols`, `strategy_rules`, `preconditions`, `comment_insights`, `raw_llm_output`）

**现状**：
- DuckDB 表结构已使用 JSON 类型列；导出时对 Python dict/list 进行 `json.dumps()` 后写入
- 这在 DuckDB 中通常可用，但读取侧（Python/duckdb 客户端）可能仍以字符串形式返回，需要确认下游消费方式

**后续处理**：
- 明确约定：DuckDB JSON 列写入/读取的类型（字符串 JSON vs 结构化 JSON）
- 为下游 OLAP/导出查询补充示例查询（`json_extract`/`->` 等）
- 涉及文件：`src/pipeline/tasks/export_task.py`（如需调整 serialize/读回）

**相关任务**：P1-026B

---

## T2: export_task 数据源与环境一致性（生产部署确认）

**严重程度**：中（影响生产部署）
**影响范围**：`export_task` 运行时连接的源数据库（SQLite vs PostgreSQL）

**现状**：
- `export_task.py` 通过 `session_scope()` 从“当前应用配置的数据库”读取（不应硬编码数据源）
- 但仍需在目标部署形态下验证：`DATABASE_URL` 生效、连接权限、以及导出查询的性能/一致性

**后续处理**：
- 明确“export 运行环境”的规范（本地/容器/服务）以及 `DATABASE_URL` 的配置位置
- 在 PostgreSQL 下跑一次全量/增量导出回归（包含空增量、少量增量、以及 schema 兼容性）
- 涉及文件：`src/pipeline/tasks/export_task.py`、部署文档（如有）

**相关任务**：P1-026C

---

## T3: process_tasks 的 config 注入仍使用模块级 global（可工作但不利测试/并发）

**严重程度**：低（技术债务）
**影响范围**：`src/pipeline/tasks/process_tasks.py`

**现状**：
- `run_process_tasks(config=...)` 已改为显式参数传入
- 但内部仍将 config 写入模块级 `_config`，供 handler 通过 `_get_config()` 读取（global 模式）

**后续处理**：
 - 将 handler 签名扩展为 `handler(details, *, config)` 或注册时用闭包绑定 config
 - 避免模块级可变全局，便于单测与未来并发 worker
 - 涉及文件：`src/pipeline/tasks/process_tasks.py`, `src/pipeline/dag.py`

**相关任务**：P1-026D

---

## T5: export_task 的“增量水位”基于 UUID4，不可靠

**严重程度**：中（可能导致漏导出/重复导出）
**影响范围**：`src/pipeline/tasks/export_task.py` 的增量导出逻辑

**现状**：
- `blog_articles.id` 使用 `uuid4()` 生成（随机、不可排序）
- 当前“增量导出”用 `id > max_id` 作为过滤条件在语义上不成立（max UUID 不代表最新写入）

**后续处理（推荐）**：
- 改为基于时间戳水位：`created_at` / `crawled_at` / `updated_at`（需明确哪一个代表“新增/更新”）
- 将 watermark 持久化：写入 DuckDB 内的 `export_state` 表，或写入 `data/processed/pipeline/` 下的 state 文件
- 全量导出仍保留 `force_full`

**相关任务**：P1-026H

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
| P1-026B | DuckDB JSON 字段读写约定与查询示例补齐 | P2 | Phase 1 |
| P1-026C | export_task 在 PostgreSQL 环境回归验证（DATABASE_URL/性能/一致性） | P1 | Phase 1 |
| P1-026D | run_process_tasks 改为显式 config 参数注入 | P3 | Phase 1 |
| P1-026E | failed_tasks.jsonl 增加自动重试或定期清理机制 | P2 | Phase 1 |
| P1-026H | 修复 export_task 增量水位（UUID4 → 时间戳 watermark/状态表） | P0 | Phase 1 |
