# New-Web-TaskList

> `trade-strategy-ai` Demo → 可交付版本的 Web/API/Worker First 重构执行规格书。
>
> 本文档适合人类 Review，也适合 Codex / Claude Code / AI Agent 按 Task ID 分阶段实现。当前 Web UI 只是 V1 的临时验收入口，不作为最终 UI 形态限制；长期稳定资产是 API、Service、Runtime Contract、Job/Workflow/Step、Config Snapshot 和 Artifact 模型。

---


## 0.1 与 `New-Web-UI-TaskList.md` 的强制执行关系

`New-Web-UI-TaskList.md` 不是独立孤立执行的前端计划，而是本主 TaskList 的 UI 子计划。执行任何 V1 / V2 / V3 阶段任务时，必须同步检查 UI TaskList 中对应的 `UI-V*` 任务。

执行规则：

```text
主 TaskList 定义：后端能力、Runtime Contract、Job/Workflow/Step、Config/Profile、Artifact、业务切片。
UI TaskList 定义：页面、组件、API Client、表单、状态、交互、用户验收。
两者必须按版本一起执行。
```

版本映射：

| 主计划版本 | 必须同步执行的 UI 范围 | 说明 |
| --- | --- | --- |
| V1 | `New-Web-UI-TaskList.md` 的 `UI-V1-*` | 支撑 article_pipeline 和运行底座验收 |
| V2 | `New-Web-UI-TaskList.md` 的 `UI-V2-*` | 正式 Profile、Dashboard、Market/Strategy 工作台 |
| V3 | `New-Web-UI-TaskList.md` 的 `UI-V3-*` | Backtest、Rule Pool、Admin Ops、权限审计、最终体验 |

AI Agent 执行主任务时必须在任务结果中说明：

```text
1. 是否存在对应 UI 任务；
2. 对应 UI Task ID 是什么；
3. 当前任务是否已提供 UI 所需 API / Contract；
4. 如果 UI 任务暂时不能执行，Blocking 原因是什么。
```

典型示例：

```text
执行 NW-V1-S3-003 article_pipeline API 时，必须同步检查：
- UI-V1-002 API Client
- UI-V1-007 Schema-driven Workflow Run Form
- UI-V1-010 Article Pipeline Page
- UI-V1-005 Job Detail Page
- UI-V1-008 Artifact Panel
- UI-V1-009 Config Snapshot Readonly Panel
```

## 0. 项目阶段定位

当前项目仍属于 Demo 阶段，已经具备部分 Job Center、Workflow UI 定义、UI Job API、Web 页面和文档基础，但还没有达到真实用户可交付版本。

本 TaskList 的目标不是继续给 Demo 补页面，而是把系统重构成可维护、可追踪、可验收的产品架构。

### 当前可复用基础

现有代码应优先复用并收敛，不允许重复建设第二套事实源：

- `src/services/job_registry.py`：已有 `JobDefinition`、权限、风险、参数 schema、并发、确认、runnable 等定义。
- `src/services/workflow_service.py`：已有 `WorkflowDefinition`、`WorkflowStep` 和 UI Workflow 展示结构，但目前更偏 UI 定义，不是真正的可执行 Step 编排。
- `src/services/job_service.py`：已有 Job 创建、状态更新、取消、重试、日志、产物目录、审计事件等基础能力。
- `api/routers/ui/jobs.py`：已有 Job 定义查询、创建、校验、列表、详情、日志、取消 API。
- `web/src/`：已有临时 Web 页面、导航、API Client 和 Job/Artifact 展示基础。
- `docs/WebOnly-Refactor-New-TaskList.md`：已有 Web-only 终态思路，但 V1 P0 范围过大，需要拆成 AI 可执行切片。

---

## 1. 最终重构交付目标

最终交付版本需要达到以下目标：

1. 普通用户通过 Web 完成核心业务操作，包括文章处理、市场数据、策略运行、回测优化、规则池审核、任务查看和产物查看。
2. 管理员通过 Web/API 完成配置管理、数据健康检查、备份恢复、权限管理、运行日志查看和基础告警查看。
3. 所有超过 3 秒、写库、写文件、调用外部服务、需要追踪进度的操作都通过 Job Center / Worker 执行。
4. 每个 Job 都记录输入快照、配置快照、执行上下文、Step Timeline、日志、错误、产物、创建人、重试次数、取消状态。
5. Workflow 不再只是 UI 展示定义，而是具备可执行、可追踪、可恢复的 Step Contract。
6. Artifact 不只是文件路径，而是具备类型、来源、权限、摘要、解释、下载和缺失处理的元数据。
7. Config 不再只是 `config_path`，而是逐步迁移为 Profile + Snapshot 模型；V1 允许兼容 `config_path`，但每次运行必须生成 Config Snapshot。
8. CLI 不再是正式产品入口，只保留开发调试薄入口，例如 `dev run-step`、`dev run-workflow`、`dev list-workflows`。
9. Web UI 当前可以是临时验收入口，但必须通过稳定 API 与 Service 交互，不允许写死业务规则。
10. 用户文档、API 文档、部署文档、运维文档、验收清单必须和实际功能一致。
11. 每个 P0 / V1.x P0 能力必须有自动化测试或明确人工验收路径。

---

## 2. V1 范围与优先级策略

### 2.1 V1 交付范围

V1 不是一次性完成所有业务模块，而是完成可交付产品骨架，并交付一条完整业务闭环。

V1 必须交付：

- 统一 Runtime Contract。
- Config Snapshot 最小可交付能力。
- Artifact Metadata 最小可交付能力。
- Job / Workflow / Step 执行底座。
- Job Center 状态、日志、错误、产物、取消、重试、Step Timeline。
- article_pipeline / 文章处理纵向切片。
- Web 临时入口，可触发、查看、解释和下载结果。
- 最小权限、设置、文档和 E2E 验收。
- CLI 降级方案和兼容入口标记。

V1 不强制完整交付：

- 完整市场数据链路。
- 完整策略运行链路。
- 完整回测优化链路。
- 完整规则池审核。
- 高级告警中心。
- 多租户复杂权限。
- 最终版 Web UI 设计系统。
- 高级 Profile 管理 UI。

这些进入 V1.1 / V1.2 / V1.3 / V1.4。

### 2.2 优先级定义

- `V1-P0`：V1 可交付版本阻断项。
- `V1-P1`：V1 建议完成；缺失会降低体验或运维效率，但不阻断 V1。
- `V1.x-P0`：后续业务切片的阻断项，不阻断 V1，但阻断对应版本。
- `P2`：长期优化，不阻断 V1 或 V1.x。

---

## 3. AI Implementation Rules

后续任务可能由 AI Agent 执行，所有实现必须遵守：

1. 每次只处理一个 Task ID。
2. 修改前必须阅读该 Task 的输入文件和相关现有实现。
3. 不允许实现 Task 未要求的功能。
4. 不允许为了通过测试删除或弱化测试。
5. 不允许绕过 `JobDefinition`、`WorkflowDefinition`、`JobService` 另起第二套长期事实源。
6. 不允许在 Web Router 中写业务逻辑。
7. 不允许在 Web UI 中写死后端业务规则。
8. 不允许把任意 shell 命令包装成 Web 功能。
9. 不允许把 `subprocess`、本地文件路径拼接、Provider 调用细节散落到 Router。
10. 不允许静默吞掉异常；错误必须结构化并能被用户理解。
11. 每个 P0 任务必须包含测试或明确人工验收。
12. 每个用户可见行为必须更新文档或验收说明。
13. 如果发现任务描述与现有代码冲突，停止扩大实现范围，并记录 Blocking。
14. 如果新增兼容层，必须写清楚删除条件。
15. 如果新增文件，必须说明它属于长期模块还是临时兼容模块。

---

## 4. 目标架构

```text
Web UI / CLI Dev
        ↓
API Router
        ↓
Application Service
        ↓
Runtime Contract
        ↓
JobService / WorkflowService / StepRegistry
        ↓
Worker / Runner
        ↓
Domain Service
        ↓
ArtifactService / ConfigSnapshotService / DB
```

### 4.1 Web UI

只负责展示、表单输入、用户操作和基础验收。不负责业务规则、配置合并、文件路径拼接、Provider 调用。

### 4.2 API Router

只负责认证、授权、请求/响应 schema、调用 Application Service、HTTP error mapping。不直接执行 Job、Workflow、Step 或 Provider。

### 4.3 Application Service

负责把用户意图转换为 Job / Workflow Run；负责加载 Profile 或 `config_path`、生成 Config Snapshot、校验参数、创建 Job、绑定执行上下文。

### 4.4 JobService

负责 Job 生命周期、状态、审计、日志、取消、重试、产物绑定、Job 文件目录。现有 `JobService` 是必须复用和增强的核心事实源。

### 4.5 WorkflowService

负责 Workflow 定义、Workflow Run、Step Timeline 和 Workflow 到 Job 的映射。V1 阶段允许通过兼容桥复用现有 `WorkflowDefinition`。

### 4.6 Step

负责一个可执行业务动作。每个 Step 必须有输入、输出、错误结构、Artifact 定义、权限和风险等级。

### 4.7 Domain Service

承载具体业务能力，例如文章处理、市场数据、策略、回测、规则池。

### 4.8 ArtifactService

负责产物元数据、下载、安全路径、摘要、解释说明、缺失和权限错误。

### 4.9 ConfigSnapshotService

负责运行时配置快照、脱敏、hash、来源追踪和校验结果。

---

## 5. Web UI 过渡策略

当前 Web UI 是 V1 的临时验收入口，不是最终产品 UI 形态。

V1 Web UI 必须做到：

- 能触发 V1 核心 Workflow。
- 能展示 Job 状态、Step Timeline、日志、错误、产物。
- 能查看脱敏 Config Snapshot。
- 能完成 V1 人工验收。

V1 Web UI 不追求：

- 完整设计系统。
- 高级交互体验。
- 复杂图表。
- 多主题。
- 一次性重构全部前端架构。
- 一次性做完所有业务页面。

前端必须依赖稳定 API；业务规则、权限、默认值、参数 schema 必须以后端事实源为准。

---

## 6. Compatibility Rules

1. `config_path` 在 V1 保留，但所有运行必须生成 Config Snapshot。
2. 旧 CLI 在 V1 保留，但正式用户文档不再把它作为主入口。
3. 旧 Workflow UI Definition 在 V1 可通过兼容桥使用，但新增 Workflow 必须按 Runtime Contract 注册。
4. 兼容桥不是永久事实源；每个兼容层必须有退出条件。
5. 当对应业务切片完成后，旧入口不得再作为正式入口出现在用户文档中。
6. 新旧 schema 不允许长期并行无边界存在；必须在迁移矩阵中标记：`keep`、`bridge`、`deprecated`、`remove-later`。

---

## 7. Task Template

所有新增任务必须使用以下模板。

```markdown
#### [ ] TASK-ID Priority 任务名称

任务目标：

背景说明：

当前相关文件：
- 

允许修改：
- 

禁止修改：
- 

输入：
- 

输出：
- 

实现步骤：
1. 
2. 
3. 

兼容要求：
- 

测试要求：
- 

验收标准：
- 

失败/阻塞判断：
- 

完成后必须更新：
- 

AI 执行提示：
- 本任务只允许实现上述范围。
- 如果发现需要扩大范围，停止实现，并在任务结果中记录 Blocking。
```

---

# Stage 0：现状冻结、迁移矩阵与 AI 约束（V1-P0）

## Stage 目标

冻结当前 Demo 实现，建立旧入口到新产品架构的迁移矩阵，定义 V1 可交付边界和 AI 开发约束。

## 阶段交付物

- `docs/WebOnly-Current-State-Audit.md`
- `docs/WebOnly-Migration-Matrix.md`
- `docs/WebOnly-V1-Acceptance.md`
- `docs/WebOnly-AI-Development-Constraints.md`

---

#### [ ] NWT-S0-001 V1-P0 完成当前实现审计

任务目标：

基于代码记录当前 Demo 的真实实现状态，明确可复用模块、不可复用模块、重复事实源和高风险路径。

当前相关文件：

- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/job_service.py`
- `api/routers/ui/jobs.py`
- `web/src/`
- `tests/`
- `docs/WebOnly-Refactor-New-TaskList.md`

允许修改：

- `docs/WebOnly-Current-State-Audit.md`

禁止修改：

- 不修改业务代码。
- 不修改测试。
- 不新增架构代码。

输出：

- 当前 Job 类型、风险、参数 schema、runnable 状态。
- 当前 Workflow 定义和 UI 展示能力。
- 当前 Job 状态、日志、错误、产物、取消、重试能力。
- 当前 Web 页面覆盖。
- 当前测试覆盖。
- 当前重复逻辑和高风险路径。

验收标准：

- 已明确 `JobDefinition`、`WorkflowDefinition`、`JobService` 是否作为后续事实源复用。
- 已明确 Workflow 当前偏 UI 定义、缺少可执行 Step Contract。
- 已明确 Web UI 当前只是临时入口。
- 审计结论基于文件和代码，不写未经验证的判断。

AI 执行提示：

- 本任务只做审计文档，不实现代码。

---

#### [ ] NWT-S0-002 V1-P0 建立旧入口迁移矩阵

任务目标：

建立旧 CLI、旧脚本、现有 Web/API/Job 到新 Web/API/Worker 架构的完整映射。

当前相关文件：

- `cli/`
- `api/routers/ui/`
- `src/services/`
- `docs/UserManual.md`
- `docs/WebUserManual.md`
- `docs/Web-UserManual-Coverage.md`

允许修改：

- `docs/WebOnly-Migration-Matrix.md`

禁止修改：

- 不实现任何迁移代码。
- 不删除旧 CLI。

矩阵字段：

```text
旧入口
当前 Service
当前 API
当前 Job Type
当前 Workflow
目标 Application Service
目标 Step
目标 Workflow
目标 Job Type
Web 页面
配置依赖
产物类型
权限
风险等级
迁移策略 keep/bridge/deprecated/remove-later
目标版本 V1/V1.1/V1.2/V1.3/Future
验收方式
备注
```

验收标准：

- 所有旧 CLI 命令、现有 UI Job、现有 Workflow 都有迁移策略。
- 每个保留能力至少映射到 Service、Step、Workflow、Job、Web 页面中的一项。
- 不迁移能力明确标记原因。
- 没有未解释的未知功能。

---

#### [ ] NWT-S0-003 V1-P0 定义 V1 可交付验收清单

任务目标：

定义 V1 可交付版本的最低验收口径，避免 AI 实现只完成底层框架但业务不可用。

允许修改：

- `docs/WebOnly-V1-Acceptance.md`

禁止修改：

- 不实现业务代码。

V1 验收必须包含：

- article_pipeline 主流程验收。
- Job Center 状态、日志、错误、产物、取消、重试验收。
- Step Timeline 验收。
- Config Snapshot 脱敏验收。
- Artifact 下载与解释验收。
- 权限不足、空数据、失败、重试场景验收。
- Web 临时页面人工验收路径。
- 自动化回归命令。

验收标准：

- 每个验收项能映射到 Stage 1~4 的任务。
- 不把 V1.1/V1.2/Future 功能列为 V1 阻断项。

---

#### [ ] NWT-S0-004 V1-P0 建立 AI 开发约束文档

任务目标：

建立 AI Agent 实施规则和 Review Checklist，防止后续任务发散或绕过架构。

允许修改：

- `docs/WebOnly-AI-Development-Constraints.md`

禁止修改：

- 不实现业务代码。

文档必须包含：

- Router 允许/禁止事项。
- Web UI 允许/禁止事项。
- JobService 允许/禁止事项。
- Workflow/Step 责任边界。
- Config Snapshot 脱敏规则。
- Artifact 安全路径规则。
- AI 单任务执行规则。
- PR Review Checklist。

验收标准：

- 后续 PR 可直接按该文档判断是否违反架构。
- 明确禁止新增第二套 Job/Workflow/Config/Artifact 事实源。

---

# Stage 1：统一 Runtime Contract 与兼容桥（V1-P0）

## Stage 目标

建立长期稳定的运行契约，但不推翻现有 `JobDefinition`、`WorkflowDefinition`、`JobService`。通过兼容桥把 Demo 基础收敛到产品架构。

## 阶段交付物

- `src/services/runtime_contracts.py`
- `src/services/config_snapshot_service.py`
- `src/services/artifact_contracts.py`
- `src/services/artifact_service.py`
- `src/services/runtime_registry_bridge.py`
- `src/services/pipeline_application_service.py`
- 对应测试

---

#### [ ] NWT-S1-001 V1-P0 设计并落地 Runtime Contract

任务目标：

定义所有 Job / Workflow / Step 共用的运行数据结构。

当前相关文件：

- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/job_service.py`

允许修改：

- `src/services/runtime_contracts.py`
- `tests/services/test_runtime_contracts.py`

禁止修改：

- 不修改现有 Job 创建流程。
- 不修改现有 WorkflowService 行为。
- 不读取配置文件、数据库或环境变量。

契约必须包含：

- `UserContext`
- `RunContext`
- `StepInput`
- `StepResult`
- `StepError`
- `ArtifactRef`
- `ConfigSnapshotRef`
- `RuntimeStatus`

实现要求：

- 使用稳定字段命名。
- 支持 JSON 序列化/反序列化。
- 错误结构能表达 user_error、system_error、external_dependency_error、permission_error、cancelled、timeout。
- ArtifactRef 能表达 file、json、csv、html_report、table、chart_data、external_link。

测试要求：

- 序列化测试。
- 反序列化测试。
- 错误类型测试。
- ArtifactRef 类型测试。

验收标准：

- Contract 不依赖 CLI、FastAPI、React、数据库 ORM。
- Contract 可以被后续 StepRegistry、WorkflowRunner、ArtifactService 复用。

---

#### [ ] NWT-S1-002 V1-P0 实现 Config Snapshot 最小可交付能力

任务目标：

让每个 Job 都能记录本次运行实际使用的配置快照，并保护敏感信息。

当前相关文件：

- `src/services/config_service.py`
- `src/services/job_service.py`
- `src/services/job_registry.py`

允许修改：

- `src/services/config_snapshot_service.py`
- `src/services/config_profile_service.py`
- `tests/services/test_config_snapshot_service.py`
- 必要时小范围增强 `src/services/job_service.py`

禁止修改：

- 不删除现有 `config_path` 参数。
- 不要求第一版完整 Profile UI。
- 不在 Router 中读取配置文件。
- 不在 API、日志、Artifact 中暴露 token、cookie、secret、password 原文。

实现要求：

1. 支持从 `config_path` 读取配置。
2. 支持生成脱敏 snapshot。
3. 支持计算稳定 `config_hash`。
4. 支持记录 `config_source`、`config_version`、`masked_snapshot`、`validation_errors`。
5. 支持将 snapshot 元数据关联到 Job。
6. 配置缺失或非法时返回结构化用户错误。

测试要求：

- 普通配置 snapshot。
- 敏感字段脱敏。
- 缺失 config_path。
- hash 稳定性。

验收标准：

- 创建 pipeline 类 Job 后能看到 config snapshot 元数据。
- API 返回不包含敏感原文。
- 现有依赖 `config_path` 的 Job 仍可创建。

---

#### [ ] NWT-S1-003 V1-P0 建立 Artifact Contract 与 ArtifactService

任务目标：

把产物从普通文件路径升级为可解释、可下载、可权限控制的元数据。

当前相关文件：

- `src/services/job_service.py`
- `api/routers/ui/jobs.py`
- Web Job Detail / Artifact 页面

允许修改：

- `src/services/artifact_contracts.py`
- `src/services/artifact_service.py`
- `tests/services/test_artifact_service.py`
- 必要时小范围增强 `JobService.bind_artifact`

禁止修改：

- 不暴露服务器绝对路径给前端。
- 不让 Router 直接拼接本地文件路径。
- 不破坏现有 `job.artifacts` 兼容结构。

实现要求：

- Artifact 元数据包含：artifact_id、job_id、workflow_id、step_id、kind、display_name、safe_path、size、created_at、summary、description、downloadable、visibility、metadata。
- 支持 file、json、csv、html_report、log、table、chart_data、data_snapshot。
- 支持缺失文件、权限不足、过期产物的结构化错误。
- 支持从旧 `job.artifacts` 兼容转换。

测试要求：

- 绑定产物。
- 读取产物元数据。
- 缺失文件。
- 绝对路径不暴露。

验收标准：

- Job 详情页后续可以按 Step 展示产物。
- Artifact API 后续可以基于 ArtifactService 实现。

---

#### [ ] NWT-S1-004 V1-P0 建立 Job/Workflow 兼容桥

任务目标：

把现有 `JobDefinition` 和 `WorkflowDefinition` 桥接到 Runtime Contract，避免重复定义任务和工作流。

当前相关文件：

- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/runtime_contracts.py`

允许修改：

- `src/services/runtime_registry_bridge.py`
- `tests/services/test_runtime_registry_bridge.py`

禁止修改：

- 不新增第二套长期 Job Registry。
- 不新增 `WebJobDefinition`。
- 不修改现有 JobDefinition 字段语义。

实现要求：

- 将现有 JobDefinition 转换为 Runtime Job Contract。
- 将现有 WorkflowDefinition 转换为 Runtime Workflow Contract。
- 保留风险、权限、参数 schema、确认要求、runnable、UI action 信息。
- 输出新旧字段映射。
- 无法映射字段必须返回 warning，不静默丢失。

测试要求：

- 所有现有 job type 可桥接。
- 所有现有 workflow 可桥接。
- 重复 job type 检测。
- 不可映射字段 warning。

验收标准：

- 新增 Job 或 Workflow 的登记入口仍然只有一个。
- 后续 StepRegistry / WorkflowRunner 可以读取桥接结果。

---

#### [ ] NWT-S1-005 V1-P0 建立 PipelineApplicationService 骨架

任务目标：

建立 Web/API/CLI Dev 共用的应用服务层，避免 Router、CLI、Web 各自拼参数和业务逻辑。

当前相关文件：

- `api/routers/ui/jobs.py`
- `src/services/job_service.py`
- `src/services/workflow_service.py`
- `src/services/config_snapshot_service.py`

允许修改：

- `src/services/pipeline_application_service.py`
- `tests/services/test_pipeline_application_service.py`

禁止修改：

- 不把业务处理逻辑写进 Application Service。
- 不直接调用 Provider。
- 不直接执行 pipeline。

实现要求：

- 提供 `submit_workflow()`。
- 提供 `submit_job()`。
- 负责参数校验、Config Snapshot、RunContext 创建、Job 创建。
- 调用现有 JobService / WorkflowService。
- 为 Router 和 CLI Dev 提供统一入口。

测试要求：

- submit_job 创建 Job。
- submit_workflow 创建 Job 或 Workflow Run。
- config snapshot 被关联。
- 参数非法返回结构化错误。

验收标准：

- 后续 Router 可以变薄，只调用 Application Service。
- CLI Dev 可以调用同一套 Application Service。

---

# Stage 2：Job / Workflow / Step 执行底座（V1-P0）

## Stage 目标

让 Job Center 成为统一长任务入口，让 Workflow 具备可执行 Step Timeline，让用户能追踪、取消、重试和理解失败原因。

---

#### [ ] NWT-S2-001 V1-P0 实现 Step Registry 最小版本

任务目标：

建立统一 Step 登记入口，让业务动作可以被 Workflow 编排、测试和展示。

允许修改：

- `src/services/step_registry.py`
- `tests/services/test_step_registry.py`

禁止修改：

- 不立即迁移所有旧 pipeline 内部 step。
- 不在 StepRegistry 中写具体业务逻辑。

实现要求：

- Step 定义包含 name、version、title、description、input_schema、output_schema、risk、permission、handler。
- 支持注册、按名称获取、列出、输入校验。
- 重复注册失败。
- 支持从 Runtime Registry Bridge 生成只读 Step 描述。

验收标准：

- 可注册 article_pipeline 需要的最小 Step。
- Step 定义可被 Workflow Runner 和 Web 展示读取。

---

#### [ ] NWT-S2-002 V1-P0 实现 Step Timeline Model

任务目标：

为每个 Job / Workflow 记录用户可理解的 Step 执行时间线。

允许修改：

- `src/models/` 中新增必要模型或使用 JSON 存储。
- `src/services/job_service.py`
- `src/services/workflow_timeline_service.py`
- `tests/services/test_workflow_timeline_service.py`

禁止修改：

- 不破坏现有 JobStatus。
- 不要求一次性做复杂 DAG。

实现要求：

- 支持 step pending、running、success、failed、skipped、cancelled。
- 记录 step_id、title、started_at、finished_at、duration、error、artifacts、summary。
- 支持追加 timeline event。
- 支持按 job_id 查询 timeline。

验收标准：

- Job 详情 API 后续能展示 Step Timeline。
- 单 Job 包装型 workflow 也可以生成 timeline。

---

#### [ ] NWT-S2-003 V1-P0 实现 Workflow Runner 最小版本

任务目标：

把 Workflow 从纯 UI 映射升级为可执行编排，但 V1 不强制替换所有内部 pipeline step。

允许修改：

- `src/services/workflow_runner.py`
- `src/services/workflow_service.py` 小范围增强
- `tests/services/test_workflow_runner.py`

禁止修改：

- 不大规模重写现有业务 pipeline。
- 不删除现有 `run_workflow()` 行为，除非提供兼容层。
- 不强制把所有内部 pipeline step 拆成独立 Step。

实现要求：

- 支持执行单 Job 包装型 workflow。
- 支持执行多 Step 顺序 workflow。
- 支持向 Step Timeline 写入状态。
- 支持 StepResult / StepError。
- 支持失败即停止。
- 支持取消检查。

验收标准：

- article_pipeline 可以先以单 Job + 用户可见 Step Timeline 方式接入。
- 后续可逐步拆成多 Step。

---

#### [ ] NWT-S2-004 V1-P0 收敛 Job Logs / Errors / Artifacts API

任务目标：

让 Job 详情相关 API 统一通过 Service 获取日志、错误和产物，避免 Router 直接读文件路径。

当前相关文件：

- `api/routers/ui/jobs.py`
- `src/services/job_service.py`
- `src/services/artifact_service.py`

允许修改：

- `src/services/job_service.py`
- `api/routers/ui/jobs.py`
- `tests/api/test_ui_jobs.py`

禁止修改：

- 不在 Router 中拼文件路径。
- 不暴露服务器绝对路径。

实现要求：

- `JobService.get_job_logs(job_id)`。
- `JobService.get_job_artifacts(job_id)` 或调用 ArtifactService。
- `JobService.get_job_detail(job_id)` 聚合 job、timeline、config snapshot、artifacts。
- Router 只调用 Service。

验收标准：

- 旧 `/jobs/{job_id}/logs` 行为兼容。
- 新 Job detail 可供 Web 直接使用。

---

#### [ ] NWT-S2-005 V1-P0 明确取消、重试、恢复规则

任务目标：

统一 Job / Workflow / Step 的取消、重试、恢复语义，避免各业务自行处理。

允许修改：

- `docs/WebOnly-Job-Lifecycle.md`
- `src/services/job_service.py` 小范围增强
- `tests/services/test_job_lifecycle.py`

禁止修改：

- 不引入复杂分布式调度。
- 不改变现有 JobStatus 枚举语义，除非有 migration。

实现要求：

- 定义 pending、running、success、failed、cancelled、scheduled 的转移规则。
- 定义 retry_count、max_retries、backoff、timeout 行为。
- 定义 Workflow Step 失败后的 Job 状态。
- 定义取消 running job 的行为。

验收标准：

- 文档和测试一致。
- Web 可以向用户解释失败、取消、重试状态。

---

# Stage 3：article_pipeline 纵向切片（V1-P0）

## Stage 目标

完成第一条真实可交付业务闭环。它不是 Demo 页面，而是后续所有业务切片的模板。

---

#### [ ] NWT-S3-001 V1-P0 定义 article_pipeline 的 PipelineSpec

任务目标：

明确文章处理链路的输入、输出、Workflow、Step、Job、Config、Artifact 和验收口径。

允许修改：

- `docs/ArticlePipeline-Spec.md`
- 必要时新增 `src/services/pipeline_specs.py`

禁止修改：

- 不实现业务代码。

Spec 必须包含：

- 用户目标。
- 输入参数。
- 配置依赖。
- Step 列表。
- Job Type 映射。
- Artifact 输出。
- 错误场景。
- 空数据场景。
- 重复运行场景。
- Web 页面需求。
- API 需求。
- 验收标准。

验收标准：

- article_pipeline 后续任务都能引用该 Spec。

---

#### [ ] NWT-S3-002 V1-P0 映射现有 crawl / pipeline-run / pipeline-step

任务目标：

把现有文章处理相关 job 映射到新的 article_pipeline，不重复实现已有能力。

当前相关文件：

- `src/services/job_registry.py`
- 现有 pipeline/crawl 相关 service
- `docs/WebOnly-Migration-Matrix.md`

允许修改：

- `docs/ArticlePipeline-Migration.md`
- 必要时更新 `docs/WebOnly-Migration-Matrix.md`

禁止修改：

- 不实现业务代码。
- 不删除旧 job type。

验收标准：

- 明确 `crawl`、`pipeline-run`、`pipeline-step` 在 V1 中的角色。
- 明确哪些作为正式入口，哪些作为兼容入口。

---

#### [ ] NWT-S3-003 V1-P0 实现 article_pipeline Workflow

任务目标：

让 Web/API 可以通过统一 Application Service 提交文章处理 Workflow。

允许修改：

- `src/services/workflow_service.py`
- `src/services/workflow_runner.py`
- `src/services/pipeline_application_service.py`
- `tests/services/test_article_pipeline_workflow.py`

禁止修改：

- 不把文章业务逻辑写进 Router。
- 不新增平行 Job 类型事实源。

实现要求：

- 支持通过 workflow_id 提交 article_pipeline。
- 使用现有 JobDefinition / JobService。
- 生成 RunContext。
- 生成 Config Snapshot。
- 写入 Step Timeline。
- 绑定 Artifact。

验收标准：

- API 能创建 article_pipeline Job / Workflow Run。
- Job 详情能看到 workflow、params、config snapshot、timeline。

---

#### [ ] NWT-S3-004 V1-P0 接入文章处理 Artifact Metadata

任务目标：

让文章处理结果不是只落文件，而是能被用户理解、查看和下载。

允许修改：

- 文章处理相关 service
- `src/services/artifact_service.py`
- `tests/services/test_article_pipeline_artifacts.py`

禁止修改：

- 不暴露绝对路径。
- 不把 Artifact 展示逻辑写进业务 service。

Artifact 至少包含：

- 原始文章/导入摘要。
- 清洗结果摘要。
- 入库结果摘要。
- 抽取结果 JSON。
- 错误报告。
- 可下载报告或 JSON。

验收标准：

- Job 成功后有可解释 Artifact。
- Job 失败后有错误 Artifact 或结构化错误。

---

#### [ ] NWT-S3-005 V1-P0 实现 article_pipeline API

任务目标：

提供稳定 API 供临时 Web UI 调用。

允许修改：

- `api/routers/ui/`
- `api/schemas/` 如有
- `tests/api/`

禁止修改：

- Router 不直接执行 pipeline。
- Router 不读取 config 文件。
- Router 不拼 Artifact 路径。

API 能力：

- 提交 article_pipeline。
- 查询 workflow/job detail。
- 查询 step timeline。
- 查询 artifact metadata。
- 下载 artifact。
- 取消 job。
- 重试 job。

验收标准：

- API schema 清晰。
- 错误响应结构化。
- 权限不足有明确错误。

---

#### [ ] NWT-S3-006 V1-P0 实现 article_pipeline 临时 Web 页面

任务目标：

提供 V1 人工验收可用的临时 Web 入口。

允许修改：

- `web/src/`

禁止修改：

- 不在前端写死业务规则。
- 不在前端拼接本地文件路径。
- 不追求最终 UI 设计系统。

页面能力：

- 创建 article_pipeline 任务。
- 查看 Job 状态。
- 查看 Step Timeline。
- 查看日志摘要。
- 查看错误说明。
- 查看 Config Snapshot 脱敏信息。
- 查看和下载 Artifact。
- 取消/重试任务。

验收标准：

- 可完成 V1 人工验收。
- 页面从 API 获取 schema 和状态。

---

#### [ ] NWT-S3-007 V1-P0 完成 article_pipeline 错误、空数据、重复执行处理

任务目标：

让文章处理链路具备真实用户可理解的异常处理能力。

允许修改：

- article_pipeline 相关 service
- `src/services/workflow_runner.py`
- `src/services/job_service.py`
- tests

禁止修改：

- 不静默吞异常。
- 不只返回 traceback。

必须处理：

- 配置缺失。
- Provider 失败。
- 没有新文章。
- 清洗失败。
- 入库失败。
- 抽取失败。
- 重复提交。
- 用户取消。

验收标准：

- 每种失败能在 Job detail 中看到用户可理解错误。
- 技术细节保留在日志中。

---

# Stage 4：V1 产品化收口（V1-P0 / V1-P1）

## Stage 目标

把 V1 article_pipeline 和运行底座收口成可交付版本。

---

#### [ ] NWT-S4-001 V1-P0 完成最小权限闭环

任务目标：

让 Web/API 对 viewer、operator、admin 有基础权限控制。

允许修改：

- `api/dependencies.py`
- `api/routers/ui/`
- tests

禁止修改：

- 不做复杂多租户。
- 不把权限判断写在前端作为唯一保护。

验收标准：

- viewer 可查看。
- operator 可创建/取消普通任务。
- admin 可执行高风险任务。
- 权限不足返回结构化错误。

---

#### [ ] NWT-S4-002 V1-P0 完成 Job Detail 产品化展示

任务目标：

统一展示 Job 基础信息、参数、配置快照、Step Timeline、日志、错误、Artifact。

允许修改：

- `web/src/`
- 相关 API client

禁止修改：

- 不在前端重新计算业务状态。

验收标准：

- 普通用户能理解任务做了什么、现在到哪一步、结果是什么、失败怎么办。

---

#### [ ] NWT-S4-003 V1-P0 完成 V1 E2E 与人工验收文档

任务目标：

提供可重复的本地验收路径。

允许修改：

- `tests/e2e/`
- `docs/WebOnly-V1-Acceptance.md`
- `docs/V1-Manual-Test-Guide.md`

验收标准：

- 有一条命令或脚本可执行 V1 回归。
- 有人工验收步骤。
- 失败时能定位到 Job 日志和 Artifact。

---

#### [ ] NWT-S4-004 V1-P0 更新用户文档、API 文档、部署文档

任务目标：

让文档与 V1 实际能力一致。

允许修改：

- `docs/WebUserManual.md`
- `docs/APIReference.md`
- `docs/Deployment.md` 或新增部署文档
- `docs/Operations.md` 或新增运维文档

禁止修改：

- 不描述尚未实现的 V1.1/V1.2 功能为已可用。

验收标准：

- 用户能按文档完成 article_pipeline。
- 管理员能按文档查看失败原因和产物。

---

#### [ ] NWT-S4-005 V1-P1 完成设置页最小展示

任务目标：

展示配置项说明、来源、脱敏值、风险提示。

允许修改：

- `api/routers/ui/settings.py`
- `web/src/`
- `src/services/config_snapshot_service.py`

禁止修改：

- 不做完整 Profile 编辑器。
- 不展示 secret 原文。

验收标准：

- 用户能知道当前任务使用了哪些配置来源。

---

# Stage 5：CLI 降级与兼容清理（V1-P1）

## Stage 目标

让 CLI 不再和 Web/API 分叉。CLI 保留为开发调试入口，正式业务入口收敛到 Web/API/Worker。

---

#### [ ] NWT-S5-001 V1-P1 梳理 CLI 命令并标记正式/开发/废弃

允许修改：

- `docs/CLI-Migration.md`
- `docs/WebOnly-Migration-Matrix.md`

禁止修改：

- 不直接删除命令。

验收标准：

- 每个 CLI 命令有 keep/dev/deprecated/remove-later 状态。

---

#### [ ] NWT-S5-002 V1-P1 让 dev CLI 调用 Application Service

允许修改：

- `cli/`
- `src/services/pipeline_application_service.py`
- tests

禁止修改：

- CLI 不再自己拼业务流程。
- CLI 不绕过 JobService。

验收标准：

- `dev run-workflow` 与 Web 提交走同一套 Application Service。

---

# Stage 6：市场数据纵向切片（V1.1-P0）

## Stage 目标

按 V1 模板迁移市场数据链路，不阻断 V1。

范围：

- `kaipan-fetch`
- `kaipan-normalize`
- `kaipan-run`
- `ohlcv-crawl`
- `market-state-build`
- `snapshot-build`

任务模板：

1. 定义 MarketData PipelineSpec。
2. 映射旧入口和 Job Type。
3. 接入 Workflow / Step Timeline。
4. 接入 Config Snapshot。
5. 接入 Artifact Metadata。
6. 提供 API。
7. 提供临时 Web 页面。
8. 处理失败、空数据、重复执行。
9. 增加测试和文档。

验收标准：

- 用户能通过 Web/API 完成市场数据链路。
- 每个任务可追踪、可解释、可下载产物。

---

# Stage 7：策略运行纵向切片（V1.2-P0）

范围：

- `strategy-build`
- `run-pre-market`
- `run-after-close`
- 证据包
- 排名
- 记忆更新

交付要求同 Stage 6。

---

# Stage 8：回测优化与规则池纵向切片（V1.3-P0）

范围：

- `backtest-run`
- `backtest-validate-rules`
- `backtest-reproducibility-check`
- `rule-pool-backtest`
- `optimize-create-candidate`

交付要求同 Stage 6。

---

# Stage 9：管理员运维、恢复与告警（V1.4-P0 / P1）

范围：

- 配置管理增强。
- 备份恢复。
- 数据健康检查。
- 用户与权限增强。
- 运行日志查看。
- 基础告警查看。

V1.4-P0：

- 管理员可查看关键健康状态。
- 管理员可查看失败任务和错误聚合。
- 管理员可执行备份/恢复前检查。

P1：

- 完整告警中心。
- 高级配置 Profile UI。
- 多用户权限增强。

---

# Stage 10：Future 优化（P2）

- 分布式 Worker。
- 定时调度中心。
- 高级可观测性 Dashboard。
- 高级图表和报告系统。
- 多 Profile 版本对比。
- 多租户权限。
- Web UI 设计系统重做。
- 外部 API 集成。

---

## 8. Review Checklist

每个 PR 必须检查：

- 是否只实现了对应 Task ID？
- 是否绕过了 JobService / WorkflowService / Runtime Contract？
- 是否新增了重复事实源？
- Router 是否包含业务逻辑？
- Web 是否写死业务规则？
- 是否暴露本地绝对路径？
- 是否泄露 secret？
- 是否有测试或人工验收？
- 是否更新文档？
- 是否影响旧 CLI / API？是否记录到迁移矩阵？
- 是否有兼容层删除条件？

---

## 9. V1 Release Acceptance Checklist

V1 发布前必须全部满足：

- Stage 0 完成。
- Stage 1 完成。
- Stage 2 完成。
- Stage 3 完成。
- Stage 4 中所有 V1-P0 完成。
- article_pipeline 可通过 Web/API 完整运行。
- Job Detail 可展示状态、参数、配置快照、Step Timeline、日志、错误、Artifact。
- 配置敏感字段不泄露。
- Artifact 不暴露服务器绝对路径。
- 权限不足有明确错误。
- 空数据、失败、取消、重试至少各有一个验收用例。
- 用户文档、API 文档、部署文档、运维文档已更新。
- CLI 正式入口降级策略已记录。



---

## 附录：主任务与 UI 任务快速映射

| 主任务阶段 | 同步 UI 任务 |
| --- | --- |
| `NW-V1-S0-*` 现状冻结与验收边界 | `UI-V1-001`, `UI-V1-011` |
| `NW-V1-S1-*` Runtime / Config Snapshot / Artifact | `UI-V1-005`, `UI-V1-008`, `UI-V1-009` |
| `NW-V1-S2-*` Step Timeline / Workflow Runner | `UI-V1-004`, `UI-V1-005`, `UI-V1-006`, `UI-V1-007` |
| `NW-V1-S3-*` article_pipeline | `UI-V1-002`, `UI-V1-007`, `UI-V1-010` |
| `NW-V1-S4-*` V1 E2E / 文档 | `UI-V1-011` |
| `NW-V2-S1-*` Profile 迁移 | `UI-V2-002`, `UI-V2-003` |
| `NW-V2-S2-*` Market Data | `UI-V2-005`, `UI-V2-007`, `UI-V2-008` |
| `NW-V2-S3-*` Strategy | `UI-V2-006`, `UI-V2-007`, `UI-V2-008` |
| `NW-V2-S4-*` CLI 降级 | Web 必须覆盖正式入口，无单独 CLI UI 任务 |
| `NW-V3-S1-*` Backtest / Rule Pool / Optimize | `UI-V3-001`, `UI-V3-002`, `UI-V3-003` |
| `NW-V3-S2-*` Admin Ops / 权限 / 审计 | `UI-V3-004`, `UI-V3-005`, `UI-V3-006`, `UI-V3-007` |
| `NW-V3-S3-*` 最终发布验收 | `UI-V3-008`, `UI-V3-009` |

执行结论：`New-Web-UI-TaskList.md` 必须和本文件一起执行，不建议单独执行。
