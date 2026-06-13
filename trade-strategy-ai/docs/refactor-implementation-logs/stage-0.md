# Stage 0 实施记录

## Stage 摘要

- Stage：`Stage 0 现状审计与迁移矩阵`
- 状态：`[x] 已完成`
- Task：`RT-S0-001`、`RT-S0-002`
- 最终结论：代码现状审计和迁移矩阵已通过严格 Review，可作为后续 Stage 的事实基线。

## RT-S0-001 现状审计

- 状态：`[x] 已完成`
- 修改范围：新增现状审计文档；未修改核心业务代码、数据库和 Prompt。
- 关键决定：
  - 以当前注册关系、ORM、迁移和 Prompt 加载点为事实，不沿用历史审计结论。
  - 将 JobService、市场数据模型、回测 snapshot-only 原则和运行审计列为可复用基础。
  - 将前端多入口、API 重复端点、Prompt 双链、画像多模型和策略按日建模列为主要重构风险。
  - 主 TaskList 与较早方案冲突时，按主 TaskList 只执行审计，不提前实施导航改造。
- 数据库迁移：无。
- 验证摘要：
  - Alembic 单一 head：`2026_06_03_0001`。
  - FastAPI 注册 163 个路由。
  - 注册 33 个 JobDefinition、2 个 WorkflowDefinition、4 个 Runtime Bridge PipelineSpec；另有 1 个未注册的 `market_data` PipelineSpec。
  - 源码声明 40 张 ORM 表；迁移环境和运行时导入范围不完全一致。
- 未完成项：实际部署数据库的数据量、质量和遗留表核对进入 Stage 2。

## RT-S0-002 迁移矩阵

- 状态：`[x] 已完成`
- 修改范围：新增迁移矩阵文档；未修改核心业务代码、数据库和 Prompt。
- 关键决定：
  - 所有旧前端入口必须映射到业务新入口或系统管理。
  - Jobs、Workflows、Artifacts 只保留为运行底座或高级详情，不再作为普通用户主导航。
  - 迁移矩阵按主 TaskList Stage 指定兼容截止点，Stage 12 统一完成旧入口退役。
  - 兼容层必须有退役条件，禁止形成第二套正式事实源。
- 数据库迁移：无；Stage 2 负责正式数据迁移对象和验证。
- 验证摘要：迁移矩阵覆盖现有能力、前端入口、API、Schema、Prompt、数据和执行定义。

## Stage 0 严格 Review

- 状态：`[x] 已完成`
- Review 关键结论：
  - `docs/bak` 不作为事实依据。
  - 区分实际注册入口、源码未注册 legacy 和迁移遗留对象。
  - 前端路由口径修正为 49 条。
  - Prompt 文件口径修正为 19 个，并补充 1 个硬编码分类 Prompt。
  - 数据库口径为源码声明 40 张 ORM 表；迁移环境未导入全部 ORM。
  - 调度实现包含 CLI、Pipeline、文章、规则回测、OHLCV、Kaipan 六类。
- 验证摘要：
  - FastAPI 163 条路由均可归属到注册模块。
  - 49 条前端路径均有目标入口，通配 404 已纳入矩阵。
  - 33 个 Job、2 个 Workflow、4 个已注册 Pipeline 和 1 个孤立 Pipeline 均已列入矩阵。
  - 19 个 Prompt 文件和 1 个硬编码 Prompt 均已纳入审计。
- 残余风险：
  - Alembic migration env 未导入全部 ORM，Stage 2 迁移前必须修复 autogenerate 范围。
  - 调度器多为进程内状态，统一前可能重复启动或状态漂移。
  - 未注册 legacy 模块删除前必须执行引用和部署检查。
  - 回测禁止实时 Provider 需要 Stage 6 运行验证。
- 最终验收：Stage 0 通过，可以进入 Stage 1。