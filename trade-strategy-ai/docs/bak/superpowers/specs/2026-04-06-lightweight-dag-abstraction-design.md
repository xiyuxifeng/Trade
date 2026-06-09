# 2026-04-06 轻量 DAG 抽象层设计

## 背景

当前项目已经具备两条可运行主线：

1. 数据主线：`crawl -> clean -> validate -> store -> process -> export`
2. 日常闭环主线：`run_pre_market -> run_after_close`

现有实现已经可以通过 CLI 和内置 scheduler 跑通，但任务之间的依赖关系、重试语义、产物归属和健康状态仍然分散在多个入口里，没有统一的“任务图”描述层。这会带来两个问题：

- 后续要扩展新节点时，执行顺序和依赖关系容易散落到各个函数里
- 任务运行结果缺少统一的图级摘要，不利于排障和后续接入更强的调度系统

本设计的目标不是引入 Airflow，也不是替换现有 scheduler，而是在当前 Python 实现之上增加一层轻量 DAG 抽象，让现有流程可以被统一描述、校验和回放。

## 目标

- 把现有 pipeline 和日常闭环统一抽象成 DAG
- 保持当前 CLI 和 scheduler 的执行方式不变
- 为每个节点定义依赖、重试、产物和失败语义
- 为每次运行生成统一的健康快照，便于追踪和排障
- 为未来接入 Airflow/Luigi 预留结构，但不强制依赖外部框架

## 非目标

- 不引入 Airflow 运行时
- 不引入 Luigi 运行时
- 不重写现有任务实现
- 不把所有命令都改造成 DAG 节点，先覆盖核心主线

## 方案概述

采用“图定义 + 图注册 + 图执行 + 健康快照”的四层结构。

### 1. 图定义

用轻量数据结构描述一个任务节点和一张任务图：

- `PipelineNodeSpec`
  - `name`: 节点名
  - `depends_on`: 前置节点列表
  - `retries`: 重试次数
  - `timeout_seconds`: 超时语义
  - `produces`: 该节点主要产物描述
  - `tags`: 例如 `["data", "pipeline"]`

- `PipelineGraphSpec`
  - `name`: 图名，例如 `data_pipeline`、`daily_cycle`
  - `nodes`: 节点列表
  - `entrypoints`: 允许从哪里开始执行
  - `description`: 图用途说明

### 2. 图注册

新增一个图注册层，把当前系统的两条主线注册进去：

- `data_pipeline`
  - `crawl`
  - `clean`
  - `validate`
  - `store`
  - `process`
  - `export`

- `daily_cycle`
  - `run_pre_market`
  - `run_after_close`

注册层只负责声明，不负责执行。

### 3. 图执行

新增一个 `PipelineRunner`，负责：

- 根据图定义按依赖顺序执行节点
- 复用现有函数：
  - `run_crawl_task`
  - `run_clean_task`
  - `run_validate_task`
  - `store_articles_jsonl_to_db`
  - `run_process_tasks`
  - `run_export_task`
  - `ManagerAgent.run_pre_market`
  - `ManagerAgent.run_after_close`
- 对每个节点记录开始时间、结束时间、耗时、状态、错误信息

执行层仍然走当前 CLI / scheduler，只是把任务顺序与结果记录统一到图模型里。

### 4. 健康快照

新增 `PipelineHealthSnapshot`，用于记录一次运行的整体结果：

- 图名
- 运行时间
- 成功节点
- 失败节点
- 节点耗时
- 节点错误摘要
- 产物路径

健康快照的用途是：

- 让手动运行和定时运行的结果有一致视图
- 方便后续生成 dashboard 或审计报告
- 方便后续迁移到更强的调度系统

## 执行模型

### 数据主线

1. `crawl`
2. `clean`
3. `validate`
4. `store`
5. `process`
6. `export`

执行规则：

- 前置节点失败则后续节点不执行
- `store` 成功后才允许进入 `process`
- `process` 成功后才允许进入 `export`
- 每个节点的结果写入健康快照

### 日常闭环主线

1. `run_pre_market`
2. `run_after_close`

执行规则：

- 可以分别手动触发，也可以由 scheduler 定时触发
- 两个节点之间不强制依赖，但都应写入统一健康快照
- 盘后节点失败时要保留错误摘要，便于第二天排查

## 错误处理

- 节点执行失败时，Runner 记录错误摘要、失败阶段和节点名
- 默认不自动吞错
- 数据主线中断后，后续节点不再执行
- 对外返回结构化结果，包含成功/失败状态，便于 CLI 和测试断言
- 图定义缺失或依赖循环时，在启动阶段直接报错

## 与现有代码的关系

本设计应尽量复用现有实现，不复制业务逻辑。

建议的映射关系：

- `src/pipeline/dag.py`：保留现有 `run_pipeline()`，同时作为数据主线图执行入口
- `src/pipeline/scheduler.py`：保留现有 APScheduler 入口，但内部改为调用图执行层
- `cli/main.py`：继续保留 `scheduler-start`、`e2e-regression` 等入口
- `ManagerAgent`：继续负责盘前/盘后业务逻辑，图层只负责调度包装

## 测试策略

至少覆盖以下场景：

- 数据主线图定义正确，节点依赖顺序正确
- 日常闭环图定义正确，节点可以独立执行
- 节点失败时，Runner 会停止后续依赖节点
- 健康快照会包含每个节点的结果与耗时
- `run_pipeline()` 和 scheduler 的现有行为不回退

测试优先级：

1. 图定义单测
2. Runner 单测
3. 现有 e2e smoke 回归

## 交付物

- 轻量 DAG 抽象层设计文档
- 图定义与注册实现
- 图执行器
- 健康快照结构
- 对现有 pipeline / scheduler 的最小改造

## 里程碑

1. 先完成数据主线图抽象
2. 再把日常闭环纳入同一抽象
3. 最后补健康快照与测试

