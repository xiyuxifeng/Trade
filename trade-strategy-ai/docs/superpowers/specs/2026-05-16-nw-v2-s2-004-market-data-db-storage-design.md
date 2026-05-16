# NW-V2-S2-004 Market Data DB Storage Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将市场数据从“文件为主的事实源”收敛为“数据库为主的查询源”，同时保留文件导出/调试/归档作为兼容层，并为后续 Web 查询与外部系统接入提供稳定的主数据模型。

**Architecture:** 采用现有 SQLAlchemy async + migration + repository 体系，新增一组统一的 market data 表，使用关系型列承载高频查询维度，使用 `payload_json` 承载 section 的扩展明细。`snapshot-build` 负责把结构化 Market Snapshot 写入数据库，Artifact 只保留 `snapshot_id` / `dataset_id` / `storage_ref` 等安全引用，不暴露服务器绝对路径。

**Tech Stack:** SQLAlchemy async、Alembic migration、现有 `JobService` / `JobRunner` / `ArtifactService` / `MarketSnapshotService`、JSONB、Repository 模式、现有 Web API 体系。

---

## 背景

当前 `NW-V2-S2-003` 已经把 `snapshot-build` 的 Market Snapshot 做成结构化产物，但主查询源仍以文件和 Job artifact 为主。  
`NW-V2-S2-004` 的目标不是新增 CLI 命令，也不是再造一套查询入口，而是把市场数据正式落到数据库中，形成可查询、可回溯、可扩展的 Web 后端事实源。

本任务只负责：
- 建表
- 建 Repository
- 建写入与查询链路
- 约束 Artifact 元数据
- 兼容旧文件导出

本任务不负责：
- `NW-V2-S2-005` 对外查询 API
- `UI-V2-010` / `UI-V2-011` 页面实现
- 新 CLI 产品入口
- 完整回测或 rule selection

---

## 总体原则

1. **单一 canonical。** 数据库是主查询源，文件是兼容导出层。
2. **可查询字段做列。** 高频查询维度必须落列并建索引。
3. **扩展字段进 JSON。** 仅把不稳定或 section 特有扩展字段放进 `payload_json`。
4. **不引入第二套 DB 事实源。** 统一沿用现有 SQLAlchemy async + Alembic + Repository 风格。
5. **不强化 CLI。** 任何迁移或导入仅作为内部兼容层，不进入产品化入口。
6. **Artifact 不暴露绝对路径。** 对外只保留安全引用和可追溯标识。

---

## 目标表结构

### 1. `market_snapshots`

市场快照主表，一条记录表示某个 `trade_date + market + profile_id + data_version` 下的一次结构化 snapshot。

建议字段：
- `id`：主键
- `snapshot_id`：业务唯一 ID
- `trade_date`
- `market`
- `profile_id`
- `data_version`
- `slot`
- `quality_status`
- `section_count`
- `available_section_count`
- `partial_section_count`
- `missing_section_count`
- `storage_ref`
- `summary_artifact_ref`
- `quality_artifact_ref`
- `created_at`
- `updated_at`

建议索引：
- `unique(snapshot_id)`
- `index(trade_date, market)`
- `index(profile_id, trade_date)`
- `index(quality_status, trade_date)`

用途：
- 按 `snapshot_id` 查询快照主记录
- 按 `trade_date` / `market` 列表查询
- 回溯 Job / Artifact / UI 展示入口

---

### 2. `market_snapshot_sections`

section 摘要表，一条记录对应一个 snapshot 中的一个 section。

建议字段：
- `id`
- `snapshot_id`
- `section_id`
- `provider`
- `source_time`
- `record_count`
- `missing_reason`
- `quality_status`
- `section_version`
- `storage_ref`
- `created_at`
- `updated_at`

建议索引：
- `unique(snapshot_id, section_id)`
- `index(snapshot_id, quality_status)`
- `index(section_id, quality_status)`

用途：
- 展示 section 质量与缺失原因
- snapshot 详情页按 section 展开
- 为后续市场 snapshot browser 提供摘要数据

---

### 3. `market_snapshot_items`

可查询明细表，一条记录对应一个 section 内的一个 item。

建议字段：
- `id`
- `snapshot_id`
- `section_id`
- `dataset_id`
- `symbol`，可空
- `item_key`
- `item_type`
- `source_time`
- `quality_status`
- `payload_json`
- `created_at`
- `updated_at`

建议索引：
- `index(snapshot_id, section_id)`
- `index(snapshot_id, symbol)`
- `index(dataset_id)`
- `index(section_id, quality_status)`

用途：
- 按 snapshot / section 查询明细
- 按 `symbol` 查询相关数据
- 支撑后续浏览器展示样本和局部详情

`payload_json` 定位：
- 存放该 item 的结构化扩展明细
- 允许保留 section 特有字段和 provider 规范化后的补充字段
- 不承载 `snapshot_id` / `trade_date` / `market` / `section_id` / `quality_status` 这类主查询字段

---

### 4. `market_datasets`

统一数据集事实源，用于将 snapshot、section、item 和外部接入统一到一个稳定引用上。

建议字段：
- `id`
- `dataset_id`
- `dataset_type`
- `trade_date`
- `market`
- `source`
- `storage_ref`
- `snapshot_id`
- `profile_id`
- `quality_status`
- `created_at`
- `updated_at`

建议索引：
- `unique(dataset_id)`
- `index(trade_date, market)`
- `index(snapshot_id)`
- `index(dataset_type, trade_date)`

用途：
- 统一 dataset 事实源
- 为后续 `snapshot_id -> dataset_id` 映射提供稳定承接点
- 为外部系统接入预留长期 ID

---

### 5. `market_data_quality_reports`

质量报告表，用于存储快照质量评估结果和 section 汇总。

建议字段：
- `id`
- `snapshot_id`
- `overall_status`
- `warning_count`
- `error_count`
- `section_summary_json`
- `report_json`
- `storage_ref`
- `created_at`
- `updated_at`

建议索引：
- `unique(snapshot_id)`
- `index(overall_status, created_at)`

用途：
- Job Detail 和 Artifact Center 回溯质量情况
- 展示缺失 section、warning、error
- 作为后续 UI 的统一质量来源

---

## 数据写入链路

### 写入顺序

1. `snapshot-build` 生成结构化 Market Snapshot。
2. `MarketDataStorageService` 或等价服务将 snapshot 拆解为主表、section 表、item 表和质量报告。
3. Repository 层负责 upsert / insert。
4. Artifact 元数据只写安全引用，不写绝对路径。
5. 文件导出保留为兼容层，用于调试、备份和下载。

### 写入约束

- 不能把 provider 原始响应直接当主表事实源。
- 不能把文件路径写入对外可见字段。
- 不能让写库逻辑散落在 Router 或 Web 页面里。
- 不能为 DB 存储新增产品级 CLI 命令。

---

## 数据查询链路

### 必须支持的 Repository 查询

- `by snapshot_id`
- `by trade_date`
- `by symbol`
- `by section`
- `by dataset_id`

### 查询策略

- 主查询字段走列和索引。
- `payload_json` 只作为补充载荷和扩展字段。
- 需要高频过滤的字段必须落列。
- 复杂诊断可以再看 JSONB，但不能依赖 JSON 作为主查询入口。

---

## Repository 分层

### `MarketSnapshotRepository`
- 负责 snapshot 主记录写入、查询、upsert。

### `MarketSnapshotSectionRepository`
- 负责 section 级摘要写入、查询、upsert。

### `MarketSnapshotItemRepository`
- 负责 item 明细写入、查询、分页。

### `MarketDatasetRepository`
- 负责 dataset 统一引用和外部接入事实源。

### `MarketDataQualityRepository`
- 负责质量报告写入与查询。

要求：
- 不直接在业务层拼 SQL。
- 不引入第二套 ORM / session 方案。
- Repository 之间保持单一职责。

---

## 兼容层与退役边界

保留：
- 文件导出
- artifact 下载
- 旧 debug 读取路径

明确退役：
- 文件作为主查询源
- 新 CLI 产品入口
- 对外暴露绝对路径

退役计划必须在实现完成后同步写入 TaskList 或文档。

---

## 验收标准

1. `snapshot-build` 可以把 Market Snapshot 写入 DB。
2. 可以通过 Repository 按 `trade_date` 查询 snapshot。
3. 可以通过 Repository 按 `snapshot_id` 查询 sections 和 items。
4. Artifact Center 可以通过 artifact metadata 回溯到 `snapshot_id`。
5. 文件导出仍可作为 artifact download 使用。
6. Web / API 不依赖服务器绝对路径。
7. 测试覆盖 DB 写入、查询、空数据、重复写入、质量报告。

---

## UI 关联任务

- `UI-V2-010 Market Snapshot Browser`
- `UI-V2-011 Market Dataset Viewer`
- `UI-V2-007 Artifact Center`

---

## 实现顺序建议

1. 先建 `market_snapshots`
2. 再建 `market_snapshot_sections`
3. 再建 `market_snapshot_items`
4. 再建 `market_datasets`
5. 最后建 `market_data_quality_reports`
6. 再补 Repository 和写入服务
7. 最后补测试和文档收口

