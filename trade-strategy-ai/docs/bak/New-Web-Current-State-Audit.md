# New-Web-Current-State-Audit

> 任务：`NW-V1-S0-001 P0 当前实现审计`
>
> 目标：确认当前 Demo 中哪些能力可复用、哪些是临时实现、哪些存在重复事实源。

## 1. 审计范围

本次审计只基于已经核对过的实现与文档事实：

- [src/services/job_registry.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/services/job_registry.py)
- [src/services/workflow_service.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/services/workflow_service.py)
- [src/services/job_service.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/services/job_service.py)
- [api/routers/ui/jobs.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/api/routers/ui/jobs.py)
- [api/routers/ui/workflows.py](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/api/routers/ui/workflows.py)
- [web/src/app/router.tsx](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/app/router.tsx)
- [web/src/routes/overview.tsx](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/routes/overview.tsx)
- [web/src/pages/jobs/index.tsx](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/pages/jobs/index.tsx)
- [web/src/components/layout/placeholder-page.tsx](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/components/layout/placeholder-page.tsx)
- [web/src/pages/strategies/index.tsx](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/pages/strategies/index.tsx)
- [docs/bak/WebOnly-Refactor-New-TaskList.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/bak/WebOnly-Refactor-New-TaskList.md)
- [docs/bak/WebUserManual.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/bak/WebUserManual.md)

说明：

- 任务描述中引用的旧文档名在当前仓库里对应的是 `docs/bak/` 下的版本。
- 本文件不修改业务代码，只记录当前实现状态和风险。

## 2. 当前可复用的 JobDefinition

当前 `job_registry` 里有 **28 个 JobDefinition**，并且它已经承担“任务白名单”的单一事实源角色。

可复用字段如下：

- `job_type`
- `title`
- `service_name`
- `handler_name`
- `permission`
- `risk`
- `can_retry`
- `can_run_concurrently`
- `concurrency_group`
- `requires_confirmation`
- `runnable`
- `param_schema`
- `description`

其中 `param_schema` 已经提供可直接复用的参数能力：

- 字段级描述、默认值、必填、枚举
- 字段类型：`string`、`integer`、`number`、`boolean`、`date`、`path`、`object`、`array`
- 额外字段控制：`allow_additional_fields`
- 参数归一化与校验：`validate(params)`

从实现上看，`JobDefinition.summary()` 可以直接给前端展示，不需要再额外拼一套 Job 元数据。

### 2.1 结论

当前 JobDefinition 已经足够支撑以下用途：

- Job 白名单
- 权限判定
- 风险分级
- 参数表单生成
- 确认弹窗判定
- 并发限制
- 是否可运行的入口判断

### 2.2 现阶段不要再重复建设的内容

- 不要新增第二套 JobDefinition。
- 不要在 UI 里复制一份 job_type/permission/risk 的固定表。
- 不要绕过 `param_schema` 直接在页面写参数事实。

## 3. WorkflowDefinition 与可执行 Step 的差距

当前 `workflow_service` 里有 **13 个 WorkflowDefinition**。它们可以看作“UI 展示型工作流目录”，但还不是完整的可执行 Step 系统。

当前 `WorkflowDefinition` / `WorkflowStep` 已有的内容：

- `workflow_id`
- `title`
- `description`
- `job_type`
- `steps`
- `permissions`
- `step_id`
- `required_job_type`
- `parameters`
- `param_schema`
- `risk`
- `requires_confirmation`

当前实现里，Workflow 的步骤是从 Job 白名单派生的：

- `WorkflowStep.param_schema` 直接来自对应 `JobDefinition.param_schema`
- `WorkflowStep.risk` 直接来自对应 `JobDefinition.risk`
- `WorkflowStep.requires_confirmation` 直接来自对应 `JobDefinition.requires_confirmation`

### 3.1 关键差距

当前 Workflow 还缺少这些“真正可执行”的能力：

- 没有单步执行引擎
- 没有 step-level input/output contract
- 没有 step timeline
- 没有 step 级状态机
- 没有 step 级失败重试语义
- 没有 step 级产物绑定
- 没有 workflow run context
- 没有 workflow 的中间态恢复语义

当前 `WorkflowService.run_workflow()` 的行为是：

1. 取 `workflow_id`
2. 校验确认条件
3. 调用 `validate_job_submission()` 校验参数
4. 直接创建一个对应 `job_type` 的 Job

也就是说，**当前 workflow 本质上还是 Job 的别名入口，不是可执行编排引擎**。

### 3.2 结论

当前 Workflow 定义可复用，但只适合作为：

- 工作流目录
- UI 展示
- 运行入口聚合
- 参数复用来源

如果后续要做真正的 Step 编排，必须补 `Runtime Contract`、`Step Registry`、`Step Timeline` 和 `Workflow Runner MVP`。

## 4. JobService 的可复用能力

当前 `JobService` 已经是比较完整的 Job Center 数据层，能复用的能力包括：

- Job 创建
- Job 查询
- Job 列表
- Job 领取 / start / claim
- Job 完成 / complete
- Job 失败 / fail
- Job 取消 / cancel
- 心跳 / heartbeat
- 产物绑定 / bind_artifact
- 超时处理 / mark_timed_out
- 僵尸任务恢复 / recover_stale_jobs
- 任务计数 / count_jobs
- 可领取任务列表 / list_ready_jobs

### 4.1 已经具备的持久化边界

JobService 目前已经统一落盘：

- `job.log`
- `params.json`
- `result.json`
- `artifacts.json`

并且它把 Job 记录、审计记录和文件目录串了起来。

### 4.2 已经具备的安全处理

审计数据在写入前会经过脱敏：

- `_sanitize_audit_data()` 会调用 `ConfigService().mask_config(...)`
- 这意味着审计负载不会直接暴露配置明文

### 4.3 仍然缺少的统一能力

虽然 JobService 很强，但它还不是最终产品契约层，缺口主要是：

- 没有 Runtime Contract
- 没有 Config Snapshot MVP
- 没有 Artifact Contract MVP
- Job 的产物仍偏“引用文件”语义，不是完整的可解释元数据
- `job_dir` / `log_path` / `params_path` / `result_path` / `artifacts_path` 仍属于内部实现细节，不应该成为长期 Web 事实源

### 4.4 结论

JobService 是当前最可复用的核心服务之一，后续重构应围绕它扩展契约，而不是推翻重写。

## 5. 当前 Web UI 的临时性和缺口

当前 Web UI 不是纯占位页，但也不是最终交付 UI，整体呈现“混合态”：

- 核心页面已经有可用数据流
- 部分页面还是占位壳
- 路由与最终 V1 规划还没有完全对齐

### 5.1 已经具备的可用 UI 能力

`/jobs` 页面已经具备：

- 列表
- 筛选
- 详情抽屉
- 日志查看
- 产物引用查看
- 重新运行
- 取消
- loading / empty / error 状态
- operator 权限提示

`/` 概览页已经具备：

- 系统状态
- 最近任务
- 最近产物
- loading / empty / error 状态

### 5.2 仍然明显临时的 UI

`/strategies` 目前仍是占位页：

- `PlaceholderPage`
- 页面标题直接标注 `Stage 4 placeholder`
- 文案明确写的是“后续阶段连接内容”

这说明当前 UI 不是所有入口都已产品化。

### 5.3 路由和页面的主要缺口

当前路由表里已经有大量入口，但它和 `NW-V1-S0-001` 的临时策略目标并不完全对齐：

- 当前是 `/`，不是任务要求中的 `/dashboard`
- 当前是 `/jobs`，但没有 `jobs/:jobId` 独立页面路由
- 当前是 `/workflows` 和 `/workflows/:workflowId`，但还没有 `/:workflowId/run` 独立运行路由
- 当前包含很多 V2/V3 风格入口，但它们的完整性不一致

### 5.4 结论

当前 UI 可以作为验收入口使用，但还不能当作正式产品终态：

- 路由规划需要收口
- 业务页和占位页混在一起
- 需要进一步把“页面展示”与“业务执行契约”分离

## 6. 重复事实源风险

当前风险不是“有没有数据”，而是“同一份事实会不会被多处复制”。

### 6.1 Job Definition 复制风险

风险点：

- `job_registry.py` 已经是 Job 白名单事实源
- UI 如果再硬编码 job_type / permission / risk，就会和 registry 漂移

后续任务：

- `NW-V1-S1-004` 建立 Job/Workflow Runtime Bridge
- `UI-V1-002` 建立统一 API Client

### 6.2 Workflow 与 Job 的重复描述风险

风险点：

- Workflow 当前是从 Job schema 派生展示定义
- 如果前端再手写一套 workflow 表单 schema，就会和后端 drift

后续任务：

- `NW-V1-S1-001` 设计并落地 Runtime Contract
- `NW-V1-S1-004` 建立 Job/Workflow Runtime Bridge
- `UI-V1-007` Schema-driven Workflow Run Form

### 6.3 Job 结果与文件路径的重复事实源风险

风险点：

- `JobService` 同时维护数据库状态和文件目录
- 如果 UI 以后直接把 `job_dir`、`log_path`、`result_path` 当长期事实源，就会把内部实现暴露出去

后续任务：

- `NW-V1-S1-002` 实现 Config Snapshot MVP
- `NW-V1-S1-003` 实现 Artifact Contract 与 ArtifactService MVP
- `UI-V1-008` Artifact Panel
- `UI-V1-009` Config Snapshot Readonly Panel

### 6.4 页面与文档的重复事实源风险

风险点：

- 页面、手册、任务清单如果各写各的，会出现“页面能看见，但手册没写”或“手册有，但页面没入口”

后续任务：

- `NW-V1-S0-002` 建立迁移矩阵
- `NW-V1-S0-003` 定义 V1 验收清单
- `UI-V1-011` Web UI 基础测试和验收

## 7. 当前高风险点与后续 Task ID

| 高风险点 | 当前状态 | 后续 Task ID |
| --- | --- | --- |
| 仍缺少统一运行契约 | 现有 Job / Workflow / Step 还没有长期共用结构 | `NW-V1-S1-001` |
| Config Snapshot 还不是正式能力 | 当前 Job 只保留参数快照和审计，不是配置快照契约 | `NW-V1-S1-002` |
| Artifact 还没有统一契约 | 当前只是 Job 目录中的产物引用 | `NW-V1-S1-003` |
| Workflow 还不是可执行编排引擎 | 目前只是 Job 白名单的 UI 目录 | `NW-V1-S1-004`、`NW-V1-S2-003` |
| Step Timeline 仍缺失 | 当前 Job 详情只有日志和审计，没有步骤时间线 | `NW-V1-S2-002`、`UI-V1-006` |
| Job Detail 还不是完整契约视图 | 当前详情已可用，但还没有 Step / Snapshot / Artifact 的完整展示边界 | `UI-V1-005` |
| 页面路由还未完全收口 | V1 路由和当前路由混杂 | `UI-V1-001`、`UI-V1-003` |
| 部分页面仍是占位页 | 例如 Strategies 页面仍是 placeholder | `UI-V1-001`、`UI-V1-003` |

## 8. 审计结论

当前项目已经具备可复用的基础事实源：

- `job_registry` 负责 Job 白名单
- `workflow_service` 负责工作流展示定义
- `job_service` 负责 Job Center 生命周期与审计
- UI 已经有可运行的任务中心和概览页

但当前系统还不是最终可交付产品，主要原因是：

- Workflow 还不是可执行 Step 系统
- Config Snapshot / Artifact Contract / Runtime Contract 仍未落地
- UI 仍混有占位页和临时路由
- 重复事实源风险已经出现，尤其是 Job / Workflow / UI 三处同时描述同一类事实

下一步应当按任务编号继续推进：

1. `NW-V1-S0-002` 建立迁移矩阵
2. `NW-V1-S0-003` 定义 V1 验收清单
3. `UI-V1-001` 先把路由规划收口
4. `UI-V1-003` 收敛基础 Layout 与导航
5. `NW-V1-S1-001` 开始 Runtime Contract
6. `NW-V1-S1-004` 建立 Job/Workflow Runtime Bridge
