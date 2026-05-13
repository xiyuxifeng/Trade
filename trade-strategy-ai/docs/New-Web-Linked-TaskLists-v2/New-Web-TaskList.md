# New-Web-TaskList

> `trade-strategy-ai` Demo → 可交付版本的 Web/API/Worker First 主 TaskList。  
> 本文档是最终版主任务清单，负责定义 V1/V2/V3 的交付目标、后端/运行时/业务切片任务，以及与 `New-Web-UI-TaskList.md` 的强绑定执行关系。  
>
> **重要：UI TaskList 不是独立执行文档。UI 任务必须作为 V1/V2/V3 各阶段的前端子任务，与主任务并行推进。**

---

## 0. 执行方式总则

### 0.1 两份文档必须一起执行

本次重构使用两份互相绑定的 TaskList：

1. `New-Web-TaskList.md`
   - 主 TaskList。
   - 覆盖 Runtime Contract、Job/Workflow/Step、Config/Profile、Artifact、业务切片、CLI 降级、部署、验收。
2. `New-Web-UI-TaskList.md`
   - UI 专项 TaskList。
   - 覆盖 Web 路由、Layout、API Client、页面、组件、状态、交互、前端验收。

执行任何主任务前，必须检查该任务的 **UI 关联任务**。  
执行任何 UI 任务前，必须检查对应的 **主任务依赖**。

### 0.2 为什么 UI 不能单独执行

UI 如果最后单独执行，会导致：

- 页面依赖的 API / Contract 不稳定。
- 前端表单 schema 和后端 JobDefinition 分叉。
- Job Detail、Artifact、Config Snapshot 展示口径不一致。
- AI 实现时容易漏掉 loading / empty / error / permission denied 状态。
- Web UI 继续变成临时堆叠，而不是可交付产品入口。

因此，UI 任务必须作为每个版本的验收条件之一。

### 0.3 执行规则

```text
执行 V1 主任务时，必须同步执行 UI-V1。
执行 V2 主任务时，必须同步执行 UI-V2。
执行 V3 主任务时，必须同步执行 UI-V3。
```

示例：

```text
做 article_pipeline：
- 主任务：NW-V1-S3-001 / 002 / 003
- UI 任务：UI-V1-007 / 008 / 009 / 010 / 011

做 Profile 迁移：
- 主任务：NW-V2-S1-001 / 002
- UI 任务：UI-V2-002 / 003

做 Backtest：
- 主任务：NW-V3-S1-001
- UI 任务：UI-V3-001
```

---

## 1. 项目阶段定位

当前项目仍属于 Demo 阶段，但已经具备可复用基础：

- `src/services/job_registry.py`：JobDefinition、权限、风险、参数 schema、并发、确认、runnable。
- `src/services/workflow_service.py`：WorkflowDefinition / WorkflowStep，但目前更偏 UI 展示与 Job 映射。
- `src/services/job_service.py`：Job 生命周期、状态、日志、结果、产物目录、审计、取消、重试。
- `api/routers/ui/jobs.py`：已有 UI Job API。
- 当前 Web UI 是临时入口，不是最终产品 UI 约束。

最终目标：

```text
从 Demo 版本升级为真实用户可使用、可部署、可运维、可复盘、可由 AI Agent 按任务持续实现的完整项目。
```

---

## 2. AI Implementation Rules

所有 AI Agent 实现必须遵守：

1. 每次只实现一个 Task ID，除非任务明确声明可合并。
2. 实现前必须阅读本任务的“当前相关文件”和“UI 关联任务”。
3. 不允许实现任务未要求的功能。
4. 不允许绕过 `JobDefinition`、`WorkflowDefinition`、`JobService`、Runtime Contract 另起事实源。
5. 不允许在 Web Router 中写业务逻辑。
6. 不允许页面组件直接调用裸 `fetch`，必须通过统一 API Client。
7. 不允许在 API、日志、Artifact、UI 中泄露 token、cookie、secret、password。
8. 不允许把服务器绝对路径暴露给 Web UI。
9. P0 任务必须有测试或人工验收。
10. 用户可见行为必须更新文档或验收说明。
11. 如果后端任务需要页面，必须引用 `New-Web-UI-TaskList.md` 的对应 UI Task。
12. 如果 UI 任务缺少 API，不允许伪造完成，应标记 Blocking。
13. 兼容层必须有退出条件。
14. 当前 Web UI 可以重做，但 API / Service / Runtime Contract / Job / Workflow / Artifact / Config Snapshot 必须作为长期稳定边界设计。

---

## 3. 目标架构

```text
Web UI / Dev CLI
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

职责边界：

- Web UI：展示、表单、状态、用户操作；不得写业务逻辑。
- API Router：认证、授权、请求校验、调用 Application Service；不得直接执行 pipeline/provider。
- Application Service：用户意图 → Job/Workflow Run；负责 Profile、ConfigSnapshot、参数校验。
- JobService：Job 生命周期、日志、审计、取消、重试、产物绑定。
- WorkflowService：Workflow 定义、Run、Step Timeline。
- Step：一个可执行的业务动作。
- Domain Service：文章、市场、策略、回测、规则池等业务能力。
- ArtifactService：产物元数据、下载、安全路径、摘要、解释。
- ConfigSnapshotService：运行时配置快照、脱敏、hash、来源追踪。

---

## 4. 版本路线与 UI 绑定

| 版本 | 主交付目标 | 必须同步执行的 UI 任务 |
| --- | --- | --- |
| V1 | 产品化运行底座 + article_pipeline 完整闭环 | UI-V1 全部 P0 |
| V2 | 正式 Profile + 正式 Web 工作台 + Market/Strategy | UI-V2 全部 P0 |
| V3 | Backtest/RulePool/AdminOps/权限审计/最终交付 | UI-V3 全部 P0 |

---

# V1：产品化运行底座 + article_pipeline 完整闭环

## V1 交付目标

V1 目标不是覆盖所有业务模块，而是建立可复用的产品化运行底座，并完成第一条完整业务闭环。

V1 必须交付：

1. Runtime Contract。
2. Config Snapshot MVP。
3. Artifact Metadata MVP。
4. Job/Workflow Runtime Bridge。
5. Step Registry。
6. Step Timeline。
7. Workflow Runner MVP。
8. article_pipeline 纵向切片。
9. Job Center 可追踪：状态、日志、错误、产物、取消、重试。
10. 临时但规范化的 Web 验收 UI。
11. E2E 回归和人工验收文档。
12. CLI 开始降级为 dev 调试入口。

V1 不强制交付：

- 完整市场数据链路。
- 完整策略链路。
- 完整回测链路。
- 完整规则池。
- 高级 Profile Editor。
- 高级告警。
- 多租户权限。
- 最终视觉设计。

---

## Stage V1-S0：现状冻结与交付边界

### [ ] NW-V1-S0-001 P0 当前实现审计

任务目标：确认当前 Demo 中哪些能力可复用、哪些是临时实现、哪些存在重复事实源。

当前相关文件：

- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/job_service.py`
- `api/routers/ui/jobs.py`
- `web/src/`
- `docs/WebOnly-Refactor-New-TaskList.md`
- `docs/WebUserManual.md`

允许修改：

- `docs/New-Web-Current-State-Audit.md`

禁止修改：

- 不修改业务代码。
- 不新增架构代码。
- 不删除旧入口。

实现要求：

1. 列出现有 JobDefinition 的可复用字段。
2. 列出现有 WorkflowDefinition 与可执行 Step 的差距。
3. 列出现有 JobService 的可复用能力。
4. 列出现有 Web UI 的临时性和缺口。
5. 标记所有重复事实源风险。

验收标准：

- 审计结果能指导后续任务。
- 每个高风险点都有后续 Task ID。
- 文档中没有未经验证的判断。

UI 关联任务：

- `UI-V1-001 Web UI 临时策略与路由规划`
- `UI-V1-003 基础 Layout 与导航`

---

### [ ] NW-V1-S0-002 P0 建立迁移矩阵

任务目标：建立旧 CLI、旧脚本、现有 Web/API/Job 到新 Web/API/Worker 架构的完整映射。

输出：

- `docs/New-Web-Migration-Matrix.md`

矩阵字段：

```text
旧入口
当前 Service
当前 API
新 Application Service
新 Step
新 Workflow
新 Job Type
Web 页面
UI Task ID
Config 依赖
Artifact 类型
权限
风险等级
迁移策略
迁移状态
验收方式
备注
```

验收标准：

- 所有旧 CLI 命令、现有 UI Job、现有 Workflow 定义都有迁移策略。
- 每一项用户可见能力必须填写 Web 页面和 UI Task ID。
- 不迁移能力明确标记为 deprecated 或 remove-later。
- 未进入矩阵的能力不得直接实现。

UI 关联任务：

- `UI-V1-001`
- `UI-V1-004 Job List 页面`
- `UI-V1-005 Job Detail 页面`

---

### [ ] NW-V1-S0-003 P0 定义 V1 验收清单

任务目标：定义 V1 可交付版本的验收口径。

输出：

- `docs/New-Web-V1-Acceptance.md`

验收必须覆盖：

- article_pipeline 用户主流程。
- Job Center 可追踪性。
- Step Timeline。
- Artifact 可下载和可解释。
- Config Snapshot 脱敏展示。
- 权限不足场景。
- 失败、重试、取消、空数据场景。
- Web UI 人工验收路径。
- E2E 命令。

验收标准：

- 每个验收项能映射到主 Task ID 和 UI Task ID。
- UI 验收不能只写“页面可用”，必须覆盖 loading/empty/error/permission denied。
- 不把 V2/V3 能力列为 V1 阻断项。

UI 关联任务：

- `UI-V1-011 Web UI 基础测试和验收`

---

## Stage V1-S1：Runtime Contract 与兼容桥

### [ ] NW-V1-S1-001 P0 设计并落地 Runtime Contract

任务目标：定义所有 Step / Workflow / Job Run 共用的长期运行数据结构。

允许修改：

- `src/services/runtime_contracts.py`
- `tests/services/test_runtime_contracts.py`

禁止修改：

- 不读取配置文件。
- 不访问数据库。
- 不依赖 FastAPI、React、CLI。
- 不改现有 JobDefinition。

Contract 必须包含：

- `RunContext`
- `UserContext`
- `StepInput`
- `StepResult`
- `StepError`
- `ArtifactRef`
- `ConfigSnapshotRef`
- `WorkflowRunContext`

验收标准：

- 支持序列化/反序列化。
- StepError 能区分用户错误、系统错误、外部依赖错误、权限错误、取消。
- ArtifactRef 不暴露服务器绝对路径。
- 测试覆盖必填字段、可选字段、错误类型。

UI 关联任务：

- `UI-V1-005 Job Detail 页面`
- `UI-V1-006 Step Timeline Component`
- `UI-V1-008 Artifact Panel`
- `UI-V1-009 Config Snapshot Readonly Panel`

---

### [ ] NW-V1-S1-002 P0 实现 Config Snapshot MVP

任务目标：让每个 Job 都能记录本次运行实际使用的配置快照，并脱敏展示。

允许修改：

- `src/services/config_snapshot_service.py`
- `src/services/config_profile_service.py`
- `src/services/job_service.py`
- `tests/services/test_config_snapshot_service.py`

禁止修改：

- 不删除现有 `config_path`。
- 不把完整 Profile UI 作为本任务范围。
- 不在 Web Router 里读取配置文件。
- 不输出 secret 原文。

实现要求：

1. 支持从 `config_path` 读取现有配置。
2. 生成 `config_hash`。
3. 生成 `masked_snapshot`。
4. 记录 `config_source`。
5. 与 `job_id` 关联。
6. 配置缺失返回结构化用户错误。

验收标准：

- 创建 Job 后可以查询到配置快照摘要。
- 敏感字段不出现在 API、日志、Artifact。
- 现有 job 仍可通过 `config_path` 运行。

UI 关联任务：

- `UI-V1-009 Config Snapshot Readonly Panel`
- `UI-V1-005 Job Detail 页面`

---

### [ ] NW-V1-S1-003 P0 实现 Artifact Contract 与 ArtifactService MVP

任务目标：建立统一产物元数据，支撑 Web 解释和下载产物。

允许修改：

- `src/services/artifact_contracts.py`
- `src/services/artifact_service.py`
- `src/services/job_service.py`
- `tests/services/test_artifact_service.py`

禁止修改：

- 不暴露服务器绝对路径。
- 不让前端直接读取文件系统路径。
- 不只保存 path，必须包含可解释元数据。

Artifact Metadata 必须包含：

- artifact_id
- job_id
- workflow_id
- step_id
- kind
- title
- summary
- safe_download_url 或 download_token
- size
- created_at
- visibility
- metadata

验收标准：

- Job Detail 可以按 Step 展示产物。
- 缺失产物返回结构化错误。
- 产物下载不暴露服务器路径。

UI 关联任务：

- `UI-V1-008 Artifact Panel`
- `UI-V1-005 Job Detail 页面`
- `UI-V2-007 Artifact Center`

---

### [ ] NW-V1-S1-004 P0 建立 Job/Workflow Runtime Bridge

任务目标：把现有 `JobDefinition` / `WorkflowDefinition` 桥接到 Runtime Contract，避免重复事实源。

允许修改：

- `src/services/runtime_registry_bridge.py`
- `tests/services/test_runtime_registry_bridge.py`

禁止修改：

- 不新增第二套 JobDefinition。
- 不新增 WebJobDefinition。
- 不长期复制 WorkflowDefinition。
- 不删除现有 Registry。

实现要求：

1. 将 JobDefinition 映射为 Job Contract。
2. 将 WorkflowDefinition 映射为 Workflow Contract。
3. 保留 permission、risk、param_schema、runnable、requires_confirmation。
4. 明确不可映射字段并写入审计文档。
5. 新增 Job / Workflow 仍只有一个登记入口。

验收标准：

- 所有现有 Job 类型可通过 bridge 读取。
- 所有现有 Workflow 可通过 bridge 读取。
- 测试覆盖字段映射。

UI 关联任务：

- `UI-V1-007 Schema-driven Workflow Run Form`
- `UI-V1-006 Step Timeline Component`

---

## Stage V1-S2：Job/Workflow/Step 执行底座

### [ ] NW-V1-S2-001 P0 实现 Step Registry

任务目标：建立统一 Step 登记入口，让业务动作可独立运行、可被 Workflow 编排、可测试。

允许修改：

- `src/services/step_registry.py`
- `tests/services/test_step_registry.py`

禁止修改：

- 不把 Step 注册写在 Web Router。
- 不把 Step 注册写成临时 dict 散落在业务代码里。
- 不强制一次性拆完所有旧 pipeline 内部步骤。

Step 必须包含：

- name
- version
- title
- input_schema
- output_schema
- risk
- permission
- execute function
- artifact definitions

验收标准：

- 重复注册失败。
- 未注册 Step 查询返回结构化错误。
- Step 输入校验可测试。

UI 关联任务：

- `UI-V1-006 Step Timeline Component`
- `UI-V1-007 Schema-driven Workflow Run Form`

---

### [ ] NW-V1-S2-002 P0 实现 Step Timeline

任务目标：让用户能看到 Workflow/Job 的执行过程，而不只是 pending/running/success/failed。

允许修改：

- `src/models/step_timeline.py`
- `src/services/step_timeline_service.py`
- `src/services/job_service.py`
- `api/routers/ui/jobs.py`
- `tests/services/test_step_timeline_service.py`

禁止修改：

- 不直接在 UI 中伪造 Step 状态。
- 不把 timeline 只写入日志文本。
- 不要求所有内部 pipeline step 一次性完全迁移。

Timeline 字段：

- step_id
- step_name
- title
- status
- started_at
- finished_at
- duration_ms
- error
- artifact_refs
- order

验收标准：

- Job Detail API 可返回 Step Timeline。
- 成功、失败、取消场景都有 timeline。
- 运行中任务可刷新 timeline。

UI 关联任务：

- `UI-V1-006 Step Timeline Component`
- `UI-V1-005 Job Detail 页面`

---

### [ ] NW-V1-S2-003 P0 实现 Workflow Runner MVP

任务目标：让 Workflow 从 UI 展示定义升级为可执行编排，但 V1 只要求支持 article_pipeline 需要的最小能力。

允许修改：

- `src/services/workflow_runner.py`
- `src/services/workflow_service.py`
- `tests/services/test_workflow_runner.py`

禁止修改：

- 不一次性替换所有旧 Workflow。
- 不强制拆掉现有 pipeline-run 内部逻辑。
- 不让 Workflow Runner 调用 Web Router。

实现要求：

1. 支持创建 Workflow Run。
2. 支持按 Step 顺序执行。
3. 支持失败停止。
4. 支持记录 Step Timeline。
5. 支持绑定 Artifact。
6. 支持把旧 Job 映射为一个可见 Step。

验收标准：

- article_pipeline 可以通过 Workflow Runner 创建 Job 并记录 timeline。
- 失败 Step 能写入 StepError。
- Workflow Runner 单元测试通过。

UI 关联任务：

- `UI-V1-007 Schema-driven Workflow Run Form`
- `UI-V1-010 Article Pipeline Page`
- `UI-V1-005 Job Detail 页面`

---

## Stage V1-S3：article_pipeline 纵向切片

### [ ] NW-V1-S3-001 P0 定义 article_pipeline PipelineSpec

任务目标：把文章处理链路定义为第一条可交付业务切片。

输出：

- `src/pipelines/article_pipeline_spec.py`
- `tests/pipelines/test_article_pipeline_spec.py`

PipelineSpec 必须包含：

- pipeline_id
- title
- description
- required_profile_sections
- input_schema
- output_artifacts
- workflow_id
- job_types
- steps
- user_visible_success_criteria

验收标准：

- article_pipeline 可被 Workflow Catalog 读取。
- 输入 schema 可用于 Web 表单。
- 输出 artifact 定义可用于 Job Detail。
- PipelineSpec 中明确对应 UI 页面和 UI Task ID。

UI 关联任务：

- `UI-V1-010 Article Pipeline Page`
- `UI-V1-007 Schema-driven Workflow Run Form`

---

### [ ] NW-V1-S3-002 P0 接入现有 crawl / pipeline-run / pipeline-step

任务目标：复用现有文章处理能力，不重写业务逻辑。

允许修改：

- `src/services/pipeline_application_service.py`
- `src/services/workflow_runner.py`
- 必要的 pipeline adapter 文件
- tests

禁止修改：

- 不把现有 pipeline 全量重写。
- 不在 API Router 中调用 pipeline 内部函数。
- 不破坏现有 CLI dev 调试入口。

实现要求：

1. Application Service 接收 article_pipeline 运行请求。
2. 加载 config snapshot。
3. 创建 Job。
4. 触发 Workflow Runner。
5. 调用现有 pipeline 能力。
6. 写入 Step Timeline。
7. 绑定 Artifact。

验收标准：

- Web/API 可以触发 article_pipeline。
- Job Detail 能看到步骤、日志、产物、配置快照。
- 失败时有结构化错误。
- 现有 CLI 调试入口仍可运行。

UI 关联任务：

- `UI-V1-010 Article Pipeline Page`
- `UI-V1-005 Job Detail 页面`
- `UI-V1-008 Artifact Panel`
- `UI-V1-009 Config Snapshot Readonly Panel`

---

### [ ] NW-V1-S3-003 P0 article_pipeline API

任务目标：提供稳定 API 给 Web UI 触发和查询 article_pipeline。

允许修改：

- `api/routers/ui/workflows.py`
- `api/routers/ui/pipelines.py`
- API schema 文件
- tests

禁止修改：

- 不让 API 直接执行 pipeline。
- 不绕过 Application Service。
- 不返回服务器绝对路径。

API 至少包括：

- `GET /api/ui/v1/pipelines`
- `GET /api/ui/v1/pipelines/article_pipeline`
- `POST /api/ui/v1/pipelines/article_pipeline/run`
- `GET /api/ui/v1/jobs/{job_id}`
- `GET /api/ui/v1/jobs/{job_id}/timeline`
- `GET /api/ui/v1/jobs/{job_id}/artifacts`

验收标准：

- Web 可以通过 API 完成完整运行。
- API 错误结构统一。
- API 文档更新。
- API response 支撑 UI-V1 需要的 loading/error/empty/permission denied 状态。

UI 关联任务：

- `UI-V1-002 建立统一 API Client`
- `UI-V1-010 Article Pipeline Page`
- `UI-V1-007 Schema-driven Workflow Run Form`

---

## Stage V1-S4：V1 产品化收口

### [ ] NW-V1-S4-001 P0 V1 E2E 回归

任务目标：提供可重复的 V1 回归验证。

输出：

- `tests/e2e/test_article_pipeline_v1.py`
- `docs/New-Web-V1-E2E.md`

验收标准：

- 本地可执行 E2E。
- 覆盖成功、失败、空数据、权限不足至少一种。
- E2E 能验证 Job、Timeline、Artifact、Config Snapshot。
- E2E 覆盖 Web UI 关键路径或提供人工 UI 验收替代方案。

UI 关联任务：

- `UI-V1-011 Web UI 基础测试和验收`

---

### [ ] NW-V1-S4-002 P0 V1 用户文档与验收说明

任务目标：让真实用户知道如何通过 Web 完成 article_pipeline。

输出：

- `docs/New-Web-V1-UserManual.md`
- `docs/New-Web-V1-Release-Checklist.md`

验收标准：

- 文档中的操作路径与 Web UI 一致。
- 页面名称与实际 UI 一致。
- 失败后用户知道如何查看错误、日志、配置快照和产物。
- 文档明确哪些能力进入 V2/V3。

UI 关联任务：

- `UI-V1-001` ～ `UI-V1-011`

---

# V2：正式 Profile + 正式 Web 工作台 + Market/Strategy

## V2 交付目标

V2 从“可验收 UI”升级为“正式用户工作台”，并完成 `config_path` → Profile 的主路径迁移。

V2 必须交付：

1. Profile 正式模型。
2. config_path 到 Profile 的迁移工具。
3. Profile List / Detail / Import / Validate / Snapshot。
4. 正式 Web 信息架构和 Dashboard。
5. Market Data 纵向切片。
6. Strategy Run 纵向切片。
7. Artifact Center。
8. CLI 正式入口继续降级。
9. 用户可理解的错误恢复体验。

---

## Stage V2-S1：Profile 正式迁移

### [ ] NW-V2-S1-001 P0 定义 Profile 最终模型

任务目标：确定 Profile 是长期配置事实源，`config_path` 降级为导入/导出/dev 兼容入口。

允许修改：

- `src/models/config_profile.py`
- `src/services/config_profile_service.py`
- migration
- tests

禁止修改：

- 不立即删除 `config_path`。
- 不在 Profile 中保存 secret 明文。
- 不让 Job 直接引用可变 Profile 而不保存 Snapshot。

Profile 模型必须支持：

- profile_id
- name
- environment
- version
- sections
- secret_refs 或 masked fields
- validation_status
- created_by
- updated_at
- archived_at

验收标准：

- 可创建默认 Profile。
- 可从现有 config_path 导入 Profile。
- Job 运行保存 ProfileSnapshot。
- Profile 修改不影响历史 Job Snapshot。

UI 关联任务：

- `UI-V2-002 Profile List / Detail / Import`
- `UI-V2-003 Profile Editor MVP`

---

### [ ] NW-V2-S1-002 P0 实现 config_path 到 Profile 的迁移工具

任务目标：让现有配置可迁移到正式 Profile，而不是长期依赖 config_path。

输出：

- `src/services/config_migration_service.py`
- dev CLI 子命令或脚本
- tests
- `docs/New-Web-Config-Migration.md`

验收标准：

- 能读取现有 config_path。
- 能生成 masked preview。
- 能校验缺失项。
- 能保存 Profile。
- 能保留 config_path 兼容入口。
- 文档明确什么时候可以停用 config_path 正式入口。

UI 关联任务：

- `UI-V2-002 Profile List / Detail / Import`

---

## Stage V2-S2：Market Data 纵向切片

### [ ] NW-V2-S2-001 P0 定义 market_data PipelineSpec

覆盖能力：

- kaipan-fetch
- kaipan-normalize
- kaipan-run
- ohlcv-crawl
- market-state-build
- snapshot-build

验收标准：

- 每个能力有 Step、Workflow、Job、Artifact、权限、错误定义。
- 支持 Web 触发、状态查看、产物查看。
- 支持 Profile 配置依赖。
- PipelineSpec 明确 UI 页面和 UI Task ID。

UI 关联任务：

- `UI-V2-005 Market Data Workspace`
- `UI-V2-007 Artifact Center`

---

### [ ] NW-V2-S2-002 P0 实现 Market Data Workflow

任务目标：将市场数据能力接入 Workflow Runner 和 Job Center。

验收标准：

- 能运行 Kaipan 抓取/归一化。
- 能运行 OHLCV 抓取。
- 能构建 market state / snapshot。
- Job Detail 展示对应 artifacts。
- 失败时用户能看到 provider/config/data 错误分类。

UI 关联任务：

- `UI-V2-005 Market Data Workspace`
- `UI-V1-005 Job Detail 页面`
- `UI-V2-008 Web UI 错误恢复体验`

---

## Stage V2-S3：Strategy Run 纵向切片

### [ ] NW-V2-S3-001 P0 定义 strategy PipelineSpec

覆盖能力：

- strategy-build
- run-pre-market
- run-after-close
- evidence package
- ranking
- memory update，如果现有项目支持

验收标准：

- 策略运行有明确输入、输出、产物、权限。
- 策略版本可追溯。
- 盘前/盘后结果可通过 Web 查看。
- PipelineSpec 明确 UI 页面和 UI Task ID。

UI 关联任务：

- `UI-V2-006 Strategy Workspace`
- `UI-V2-007 Artifact Center`

---

### [ ] NW-V2-S3-002 P0 实现 Strategy Workflow

验收标准：

- Web/API 可触发策略版本构建。
- Web/API 可触发盘前/盘后。
- Job Detail 可展示报告和证据包。
- Artifact Center 可检索策略产物。

UI 关联任务：

- `UI-V2-006 Strategy Workspace`
- `UI-V2-007 Artifact Center`
- `UI-V2-008 Web UI 错误恢复体验`

---

## Stage V2-S4：正式 UI 与 CLI 降级

### [ ] NW-V2-S4-001 P0 正式 Web 工作台收口

任务目标：确保 V2 的 Profile、Market、Strategy 有正式 Web 工作台，而不是临时页面堆叠。

验收标准：

- Dashboard 可进入 Profile / Market / Strategy / Jobs / Artifacts。
- 页面状态一致。
- 错误恢复体验一致。
- 用户不需要 CLI 完成 V2 正式功能。

UI 关联任务：

- `UI-V2-001 正式 Web 信息架构`
- `UI-V2-004 Dashboard 首页`
- `UI-V2-008 Web UI 错误恢复体验`
- `UI-V2-009 UI Component Kit`

---

### [ ] NW-V2-S4-002 P0 CLI 正式入口降级

任务目标：CLI 不再作为正式用户入口，只保留 dev 调试能力。

保留：

- `dev run-step`
- `dev run-workflow`
- `dev list-workflows`
- `dev config-migrate`

禁止：

- 不新增复杂正式 CLI 命令。
- 不让 CLI 持有独立业务逻辑。
- 不让 CLI 与 Web 参数 schema 分叉。

验收标准：

- CLI 调用 Application Service。
- 用户文档不再把 CLI 作为正式路径。
- 旧 CLI 命令标记 deprecated 或移入 dev namespace。
- Web 已覆盖对应正式入口。

UI 关联任务：

- V2 所有正式工作台任务。

---

# V3：完整交付版本

## V3 交付目标

V3 完成完整项目交付：

1. Backtest Center。
2. Optimization Candidate Review。
3. Rule Pool Review。
4. Admin Ops Console。
5. Health Check Dashboard。
6. Backup / Restore UI。
7. Permission / Audit。
8. 最终 Web UI 收口。
9. 部署、运维、发布验收。
10. 用户手册、API 文档、管理员手册完整一致。

---

## Stage V3-S1：Backtest / Optimize / Rule Pool

### [ ] NW-V3-S1-001 P0 定义并实现 backtest PipelineSpec / Workflow

覆盖能力：

- backtest-run
- backtest-validate-rules
- backtest-reproducibility-check

验收标准：

- 回测输入清晰。
- 输出指标可解释。
- fingerprint 可复现。
- Artifact 包含报告、JSON、CSV。
- Web 可运行、查看、下载结果。

UI 关联任务：

- `UI-V3-001 Backtest Center`

---

### [ ] NW-V3-S1-002 P0 定义并实现 optimize / rule_pool PipelineSpec / Workflow

覆盖能力：

- optimize-create-candidate
- rule-pool-backtest
- candidate review
- rule approval / reject

验收标准：

- 候选版本可追溯。
- 规则审核有权限和审计。
- 高风险操作需要确认。
- 结果可以回写并审计。
- Web 可完成审核流程。

UI 关联任务：

- `UI-V3-002 Rule Pool Review UI`
- `UI-V3-003 Optimize Candidate UI`

---

## Stage V3-S2：Admin Ops / 权限 / 审计

### [ ] NW-V3-S2-001 P0 权限与审计闭环

任务目标：让管理员能查看谁在什么时候执行了什么任务，使用了什么配置，产生了什么结果。

验收标准：

- Job audit 可查询。
- 高风险操作有 actor/source/confirmation。
- UI 不展示敏感信息。
- 权限不足返回用户可理解错误。
- Admin UI 可查看审计。

UI 关联任务：

- `UI-V3-007 Permission / Audit UI`

---

### [ ] NW-V3-S2-002 P0 运维与恢复闭环

覆盖能力：

- health check
- backup-data
- restore-data
- stale job recovery
- provider connectivity check
- storage check

验收标准：

- 管理员能判断系统是否可用。
- 备份/恢复高风险操作需要确认。
- 恢复操作有审计和失败处理。
- Web Admin Console 可完成运维主流程。

UI 关联任务：

- `UI-V3-004 Admin Ops Console`
- `UI-V3-005 Health Check Dashboard`
- `UI-V3-006 Backup / Restore UI`

---

## Stage V3-S3：最终发布验收

### [ ] NW-V3-S3-001 P0 全量 E2E 与发布检查

任务目标：确保项目达到完整交付状态。

输出：

- `docs/New-Web-Final-Acceptance.md`
- `docs/New-Web-Deployment-Guide.md`
- `docs/New-Web-Admin-Manual.md`
- `docs/New-Web-UserManual.md`
- `tests/e2e/`

验收标准：

- V1/V2/V3 所有 P0 完成。
- UI-V1/UI-V2/UI-V3 所有 P0 完成。
- 用户手册与 UI 一致。
- API 文档与实现一致。
- 部署文档可重复执行。
- 失败、空数据、权限不足、外部依赖失败场景均有处理。
- 无正式业务能力只能通过 CLI 使用。
- 无长期双 Job/Workflow/Profile/Artifact 事实源。

UI 关联任务：

- `UI-V3-008 Final UX Review`
- `UI-V3-009 User Manual Coverage Verification`

---

## 5. 主任务与 UI 任务映射表

| 主任务 | 必须同步检查的 UI 任务 |
| --- | --- |
| NW-V1-S0-001 | UI-V1-001, UI-V1-003 |
| NW-V1-S0-002 | UI-V1-001, UI-V1-004, UI-V1-005 |
| NW-V1-S0-003 | UI-V1-011 |
| NW-V1-S1-001 | UI-V1-005, UI-V1-006, UI-V1-008, UI-V1-009 |
| NW-V1-S1-002 | UI-V1-009, UI-V1-005 |
| NW-V1-S1-003 | UI-V1-008, UI-V1-005, UI-V2-007 |
| NW-V1-S1-004 | UI-V1-007, UI-V1-006 |
| NW-V1-S2-001 | UI-V1-006, UI-V1-007 |
| NW-V1-S2-002 | UI-V1-006, UI-V1-005 |
| NW-V1-S2-003 | UI-V1-007, UI-V1-010, UI-V1-005 |
| NW-V1-S3-001 | UI-V1-010, UI-V1-007 |
| NW-V1-S3-002 | UI-V1-010, UI-V1-005, UI-V1-008, UI-V1-009 |
| NW-V1-S3-003 | UI-V1-002, UI-V1-010, UI-V1-007 |
| NW-V1-S4-001 | UI-V1-011 |
| NW-V1-S4-002 | UI-V1-001 ~ UI-V1-011 |
| NW-V2-S1-001 | UI-V2-002, UI-V2-003 |
| NW-V2-S1-002 | UI-V2-002 |
| NW-V2-S2-001 | UI-V2-005, UI-V2-007 |
| NW-V2-S2-002 | UI-V2-005, UI-V1-005, UI-V2-008 |
| NW-V2-S3-001 | UI-V2-006, UI-V2-007 |
| NW-V2-S3-002 | UI-V2-006, UI-V2-007, UI-V2-008 |
| NW-V2-S4-001 | UI-V2-001, UI-V2-004, UI-V2-008, UI-V2-009 |
| NW-V2-S4-002 | UI-V2 全部正式工作台 |
| NW-V3-S1-001 | UI-V3-001 |
| NW-V3-S1-002 | UI-V3-002, UI-V3-003 |
| NW-V3-S2-001 | UI-V3-007 |
| NW-V3-S2-002 | UI-V3-004, UI-V3-005, UI-V3-006 |
| NW-V3-S3-001 | UI-V3-008, UI-V3-009 |

---

## 6. Review Checklist

每个 PR 或 AI Agent 任务完成后必须检查：

```text
[ ] 是否只完成指定 Task ID？
[ ] 是否检查了对应 UI Task ID？
[ ] 是否新增重复事实源？
[ ] 是否绕过 JobService / WorkflowService / Runtime Contract？
[ ] 是否在 Router 或 UI 中写了业务逻辑？
[ ] 是否泄露 secret 或服务器路径？
[ ] 是否有测试或人工验收？
[ ] 是否更新相关文档？
[ ] 是否影响旧兼容入口？
[ ] 是否明确兼容层退出条件？
[ ] 用户可见能力是否有 Web 页面、状态和错误处理？
```

---

## 7. 兼容层退出规则

1. `config_path` 在 V1/V2 可保留，但所有正式运行必须生成 ConfigSnapshot。
2. Profile UI 和迁移工具完成后，`config_path` 降级为 dev/import/export 入口。
3. 旧 CLI 在 V1/V2 可保留，但 V3 前必须从用户正式文档移除。
4. 旧 Workflow UI Definition 可通过 bridge 使用，但新增 workflow 必须有 Runtime Contract。
5. 临时 Web UI 可在 V2/V3 重做，但不能破坏 API / Runtime Contract。
6. 兼容层删除前必须有迁移矩阵、UI 页面映射和 E2E 覆盖。
