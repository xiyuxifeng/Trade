# JobService Implementation Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Web Job Center 提供数据库驱动的 Job 生命周期管理能力，覆盖创建、查询、状态流转、幂等、日志路径、产物引用以及 Worker 协议所需的心跳和重试元数据。

**Architecture:** JobService 只负责 Job 的业务管理，不负责实际执行任务。Job 完整日志落文件系统，数据库只存状态、摘要、结果、错误、产物引用与恢复所需元数据。服务层通过 SQLAlchemy async session 读写 `jobs` 表，并以 `ServiceResult` 向 CLI / Web API 返回结构化结果。

**Tech Stack:** Python 3.13, SQLAlchemy async, Pydantic `ServiceResult`, pytest / pytest-asyncio, PostgreSQL / SQLite 测试库。

---

## 1. 设计边界

- `WEB-S2-002` 只实现 JobService，不实现 Worker。
- 任务执行、心跳、锁超时恢复属于 `WEB-S2-003` / `WEB-S2-005`。
- 完整日志不入库，只在 `Job` 记录中保存日志路径、错误摘要和结果摘要。
- Job 的唯一来源是数据库表 `jobs`，文件系统只作为附属存储。
- `retry_backoff_seconds` 记录失败或 stale 后再次领取前的退避秒数。

## 2. JobService 职责

- 创建 Job。
- 按 `job_id` 查询 Job。
- 列出 Job，支持分页和过滤。
- 更新 Job 状态：`pending / running / success / failed / cancelled`。
- 记录执行开始、结束、失败和取消时间。
- 支持幂等键去重创建。
- 记录 Job 发起人 `created_by`。
- 绑定日志路径、结果 JSON 和产物引用。
- 原子领取、心跳刷新和退避重试标记。
- 标记超时与恢复 stale Job。
- 记录取消请求时间 `cancel_requested_at`。

## 3. 数据流

1. 调用方传入 `job_type`、`params`、`idempotency_key` 等字段。
2. JobService 先检查幂等键是否已存在。
3. 若不存在，写入 `jobs` 表并返回结构化结果。
4. Job 状态变化时，JobService 更新数据库中的状态、时间戳和错误/结果摘要。
5. 日志与产物写入文件系统后，通过路径或引用写入 Job 记录。
6. Worker 通过 `claim_job()` 领取任务，通过 `heartbeat_job()` 刷新运行中任务心跳，通过 `recover_stale_jobs()` 处理超时恢复。

## 4. 文件边界

- `src/services/job_service.py`
  - JobService 核心实现。
  - 只依赖 `src.models.job.Job`、`session_scope` 和 `ServiceResult`。
- `tests/unit/services/test_job_service.py`
  - 覆盖创建、查询、状态流转、幂等、日志、产物、超时与恢复。
- `src/services/__init__.py`
  - 导出 `JobService`。
- `docs/Web-TaskList.md`
  - 在实现完成并验证后更新 `WEB-S2-002` 状态。

## 5. 验收标准

- 能创建 Job 并返回 `job_id`。
- 幂等键重复时不创建新 Job。
- 能查询 Job 列表和详情。
- 能启动、完成、失败、取消 Job。
- 能追加日志路径和绑定产物引用。
- 能记录错误摘要和结果摘要。
- 能标记超时 Job，并提供恢复所需元数据。
- 能记录 `created_by` 和 `cancel_requested_at`。
- 对应测试全部通过。
