# New-Web-UI-TaskList

> `trade-strategy-ai` Web UI 专项任务清单。
>
> 本文档是 `New-Web-TaskList.md`、`New-Web-V2-TaskList.md`、`New-Web-V3-TaskList.md` 的前端配套执行规格。它不是独立孤立执行的计划，而是嵌入 V1/V2/V3 各阶段：每当主 TaskList 交付一个后端/API/Workflow/Artifact 能力时，必须同步完成本文件中对应的 UI 任务，确保最终项目不是“只有 API 能用”，而是用户可以通过 Web 完成真实操作。
>
> 当前 Web UI 可作为 V1 临时验收入口，但 V2/V3 必须逐步收敛为正式用户工作台。长期稳定边界是 API、Service、Runtime Contract、Job/Workflow/Step、Config/Profile、Artifact 模型；UI 可以重构，但不允许绕过这些边界。

---

## 0. 执行关系

### 0.1 与 V1/V2/V3 TaskList 的关系

本文件应与主 TaskList 一起执行：

| 主版本 | 主 TaskList 目标 | 本 UI TaskList 对应范围 |
| --- | --- | --- |
| V1 | 产品化运行底座 + article_pipeline 完整切片 | `UI-V1-*`：临时但规范化的验收 UI |
| V2 | Profile 正式迁移 + Market/Strategy 工作台 | `UI-V2-*`：正式信息架构、Profile、市场数据、策略工作台 |
| V3 | Backtest/Rule/Ops/权限/最终交付 | `UI-V3-*`：完整交付 UI、运维、审计、发布级体验 |

执行原则：

```text
主 TaskList 定义产品能力和后端交付边界。
本 UI TaskList 定义用户如何在 Web 中操作、理解和验收这些能力。
任何用户可见能力，如果没有对应 UI 或明确标记为 API-only，则不得视为完整交付。
```

### 0.2 是否可以单独执行

不建议单独执行。UI 任务必须依赖后端 API、Job/Workflow/Artifact/Profile 契约。只有以下任务可以提前独立做：

- UI Foundation
- Layout / Routing
- API Client
- 通用状态组件
- Job List / Job Detail 的 mock 或现有 API 接入

业务工作台类任务必须等对应 API 和运行契约完成后执行。

---

## 1. AI Implementation Rules for Web UI

后续 Web UI 任务可能由 AI Agent 执行。每个 AI 任务必须遵守：

1. 每次只处理一个 Task ID。
2. 修改前先阅读本任务的“允许修改 / 禁止修改 / API 依赖 / 验收标准”。
3. 页面组件不得直接调用裸 `fetch`，必须通过统一 API Client。
4. 不允许在前端复制后端业务规则、参数 schema、权限规则或风险判断。
5. 不允许在前端展示服务器绝对路径。
6. 不允许展示 token、cookie、secret、password、api_key 等敏感字段原文。
7. 不允许把临时 mock 数据作为正式实现提交，除非任务明确允许。
8. 不允许为单个页面重复实现通用表格、Badge、Error、Loading、JsonViewer、ArtifactList。
9. 每个页面必须覆盖 loading、empty、error、permission denied、not found 中适用的状态。
10. 每个用户操作必须有成功、失败、确认、不可执行状态的处理。
11. 如果后端 API 缺失，必须在任务结果中标记 Blocking，不允许前端硬编码绕过。
12. 如果需要新增组件，必须放入清晰目录，并说明是否为通用组件。
13. 如果任务会影响路由、导航、权限、API Client，必须同步更新 UI Review Checklist。

---

## 2. Web UI 总体目标

最终交付版本的 Web UI 必须支持：

1. 普通用户完成文章处理、市场数据、策略运行、回测优化、规则池审核、任务查看、产物查看。
2. 管理员完成 Profile/配置管理、数据健康检查、备份恢复、权限管理、运行日志查看、基础告警查看。
3. 用户能理解每个 Job 的输入、配置快照、执行步骤、日志、错误、产物和恢复建议。
4. 用户能通过 Workflow Catalog 或业务工作台触发任务，而不是记住 CLI 命令。
5. 表单参数来自后端 schema 或稳定 API，不与后端分叉。
6. Artifact 能预览、下载、解释，不只显示文件路径。
7. Profile 取代 config_path 成为正式用户配置入口；config_path 仅保留为开发/导入/兼容方式。
8. Web UI 允许在 V1 临时，但 V2/V3 必须形成正式信息架构。

---

## 3. 目标信息架构

最终路由建议：

```text
/dashboard
/jobs
/jobs/:jobId
/workflows
/workflows/:workflowId
/articles
/market
/strategy
/backtest
/rules
/artifacts
/profiles
/profiles/:profileId
/settings
/admin
/admin/health
/admin/backup
/admin/audit
/admin/users
```

V1 只要求实现必要路由：

```text
/dashboard
/jobs
/jobs/:jobId
/workflows
/articles
/artifacts
/settings
```

V2 增加：

```text
/profiles
/profiles/:profileId
/market
/strategy
```

V3 增加：

```text
/backtest
/rules
/admin/*
```

---

## 4. 通用页面状态规范

所有页面都必须考虑：

```text
loading：数据加载中
empty：无数据，但不是错误
error：API 或运行错误
permission denied：权限不足
not found：资源不存在
partial：部分数据缺失，例如 artifact 文件缺失
stale：数据过旧或状态未刷新
```

通用操作反馈：

```text
成功：Toast 或页面内状态更新
失败：显示用户可理解错误，不只显示 stacktrace
高风险操作：确认弹窗
不可执行操作：按钮 disabled + 原因说明
后台任务：创建成功后跳转 Job Detail
```

---

# V1 UI：临时但规范化的验收 UI

V1 UI 目标：不追求最终视觉效果，但必须能完整验收 article_pipeline 和产品化运行底座。

## UI-V1-001 P0 建立 Web UI 临时策略与路由规划

任务目标：

明确当前 Web UI 是 V1 验收入口，不是最终视觉形态；建立基础路由和导航，避免后续页面继续随意堆叠。

允许修改：

- `web/src/App.*`
- `web/src/routes/*`
- `web/src/layouts/*`
- `web/src/components/navigation/*`
- `docs/New-Web-UI-TaskList.md`

禁止修改：

- 不允许删除已有可用页面，除非提供兼容路由。
- 不允许在路由层执行业务逻辑。
- 不允许把后端 API 地址硬编码到页面组件。

实现要求：

1. 建立主 Layout：Sidebar + Header + Content。
2. 建立 V1 必要路由：`/dashboard`、`/jobs`、`/jobs/:jobId`、`/workflows`、`/articles`、`/artifacts`、`/settings`。
3. 未实现页面必须显示明确 Placeholder，说明所属版本和依赖任务。
4. 导航项预留权限字段，例如 `viewer`、`operator`、`admin`。
5. 旧临时页面可以保留在 legacy 分组或兼容入口。

测试要求：

- 前端构建通过。
- 每个 V1 路由可访问。
- 未实现页面不应空白或崩溃。

验收标准：

- 用户能从导航进入 Job、Workflow、Article、Artifact、Settings 页面。
- Placeholder 清楚说明功能状态。
- 后续业务页面有统一挂载位置。

---

## UI-V1-002 P0 建立统一 API Client

任务目标：

统一 Web API 调用方式，避免页面组件直接调用裸 `fetch`，为后续 AI 实现提供稳定入口。

允许修改：

- `web/src/api/*`
- `web/src/hooks/*`
- `web/src/types/*`
- `web/src/config/*`

禁止修改：

- 不允许在页面组件中新增裸 `fetch`。
- 不允许在组件中硬编码 API base URL。
- 不允许吞掉 API error。
- 不允许全部使用 `any` 绕过类型约束。

实现要求：

1. 建立统一 request 方法。
2. 支持 API base URL 配置。
3. 支持 API key / auth header 注入。
4. 统一处理 HTTP status、error body、network error。
5. 建立以下 API client：
   - `jobsApi`
   - `workflowsApi`
   - `artifactsApi`
   - `settingsApi`
6. 建立基础类型：`Job`、`JobStatus`、`JobDefinition`、`WorkflowDefinition`、`ArtifactRef`、`ApiError`。

测试要求：

- API client 至少有基础单元测试或 mock 测试。
- Job List / Job Detail 必须使用 API client。

验收标准：

- 页面中不再新增裸 `fetch`。
- API 失败能显示统一错误消息。
- 切换 API base URL 不需要改业务组件。

---

## UI-V1-003 P0 建立基础 UI Component Kit

任务目标：

建立最小通用组件，避免 AI 后续在每个页面重复实现状态、表格、Badge、错误展示。

允许修改：

- `web/src/components/ui/*`
- `web/src/components/common/*`

禁止修改：

- 不引入大型 UI 框架，除非仓库已有依赖或任务明确允许。
- 不在业务页面重复实现通用 Loading / Error / Empty。

组件清单：

- `PageHeader`
- `SectionCard`
- `StatusBadge`
- `RiskBadge`
- `DataTable`
- `LoadingState`
- `EmptyState`
- `ErrorState`
- `ConfirmDialog`
- `JsonViewer`
- `LogViewer`
- `ArtifactList`

实现要求：

1. 组件保持简单、可复用。
2. 状态组件支持标题、描述、操作按钮。
3. StatusBadge 支持 Job 状态。
4. RiskBadge 支持 low / medium / high / critical。
5. JsonViewer 默认折叠长对象。

验收标准：

- Job List / Job Detail 至少使用 `PageHeader`、`SectionCard`、`StatusBadge`、`ErrorState`。
- 新增业务页面不得重复造基础状态组件。

---

## UI-V1-004 P0 实现 Job List 页面

任务目标：

让用户查看 Job Center 中所有任务，支持基本过滤和跳转详情。

允许修改：

- `web/src/pages/jobs/JobListPage.*`
- `web/src/components/jobs/*`
- `web/src/api/jobs.*`
- `web/src/types/job.*`

禁止修改：

- 不允许前端直接推断 Job 数据结构，必须以 API 类型为准。
- 不允许显示服务器绝对路径。
- 不允许在列表页执行任务业务逻辑。

页面必须展示：

- Job ID 短显示 + 可复制完整 ID
- job_type
- status
- created_by
- created_at
- started_at
- finished_at
- retry_count
- 操作：查看详情

过滤要求：

- status
- job_type
- created_by

状态要求：

- loading
- empty
- error
- permission denied

验收标准：

- 能列出 Job。
- 能按状态和类型过滤。
- 点击进入 Job Detail。
- API 失败时显示错误，不是空白页。

---

## UI-V1-005 P0 实现 Job Detail 页面

任务目标：

让用户可以理解一个 Job 的输入、配置、执行过程、日志、失败原因和产物。

允许修改：

- `web/src/pages/jobs/JobDetailPage.*`
- `web/src/components/jobs/*`
- `web/src/components/artifacts/*`
- `web/src/api/jobs.*`
- `web/src/types/job.*`

禁止修改：

- 不允许前端自行判断 Job 是否成功，必须以后端 status 为准。
- 不允许展示 secret 原文。
- 不允许展示服务器绝对路径。
- 不允许把 artifact 下载 URL 写死。

页面必须展示：

1. 基本信息：job_id、job_type、status、created_by、created_at、started_at、finished_at、retry_count、cancel_requested。
2. 参数快照：params、config_snapshot、masked sensitive fields。
3. Step Timeline：step name、status、started_at、finished_at、duration、error summary。
4. 日志：最近日志、刷新按钮、下载入口。
5. 错误：error type、user message、technical message、retry suggestion。
6. 产物：artifact type、title、summary、created_at、preview/download action。
7. 操作：cancel、retry，若后端未支持则显示 disabled + 原因。

状态要求：

- loading
- not found
- running
- success
- failed
- cancelled
- permission denied
- artifact missing

测试要求：

- 至少 mock success / failed / running / not found 四种状态。

验收标准：

- 成功 Job 可以看到结果和产物。
- 失败 Job 可以看到失败原因。
- 运行中 Job 可以刷新状态。
- Secret 和服务器绝对路径不会显示。

---

## UI-V1-006 P0 实现 Workflow Catalog 页面

任务目标：

让用户查看可运行 Workflow，并从 Workflow 进入运行表单。

允许修改：

- `web/src/pages/workflows/WorkflowCatalogPage.*`
- `web/src/components/workflows/*`
- `web/src/api/workflows.*`
- `web/src/types/workflow.*`

禁止修改：

- 不允许前端硬编码 Workflow 列表。
- 不允许绕过后端 WorkflowDefinition。

页面展示：

- workflow_id
- title
- description
- permissions
- risk / requires_confirmation
- steps summary
- action：run / view detail

验收标准：

- Workflow 列表来自 API。
- 每个 Workflow 显示步骤摘要。
- 可以进入运行表单。

---

## UI-V1-007 P0 实现 Schema-driven Workflow Run Form

任务目标：

根据后端 JobDefinition / WorkflowDefinition 动态渲染运行表单，避免前后端参数 schema 分叉。

允许修改：

- `web/src/pages/workflows/WorkflowRunPage.*`
- `web/src/components/forms/*`
- `web/src/api/workflows.*`
- `web/src/api/jobs.*`
- `web/src/types/workflow.*`

禁止修改：

- 不允许在前端手写每个 job_type 的完整参数 schema。
- 不允许绕过后端 validate API。
- 不允许把 required/default/risk 写死在页面中。

实现要求：

1. 从 API 获取 workflow definition 和 job param_schema。
2. 支持字段类型：string、integer、number、boolean、date、path、object、array。
3. 展示字段 description、default、required。
4. 提交前调用 validate API。
5. 高风险任务显示确认弹窗。
6. 创建 Job 成功后跳转 Job Detail。
7. 表单错误显示在字段附近和页面顶部。

验收标准：

- `pipeline-run` 可以通过表单创建。
- required 缺失有明确提示。
- 高风险任务需要确认。
- 表单字段来自后端 schema。

---

## UI-V1-008 P0 实现 Artifact Panel

任务目标：

统一展示 Job 产物，支持预览、下载、缺失处理和解释说明。

允许修改：

- `web/src/components/artifacts/*`
- `web/src/pages/artifacts/*`
- `web/src/api/artifacts.*`
- `web/src/types/artifact.*`

禁止修改：

- 不允许显示服务器绝对路径。
- 不允许直接拼接本地文件路径。
- 不允许假设 artifact 一定存在。

实现要求：

1. 支持 artifact list。
2. 支持按类型显示图标或标签：report、csv、json、log、chart、snapshot、file。
3. 支持 summary / description。
4. 支持 download action。
5. JSON artifact 支持预览。
6. 缺失 artifact 显示 partial 状态。

验收标准：

- Job Detail 能展示 artifact。
- artifact 缺失不会导致页面崩溃。
- 用户能理解 artifact 是什么。

---

## UI-V1-009 P0 实现 Config Snapshot Readonly Panel

任务目标：

让用户查看本次 Job 使用的配置来源、hash、脱敏快照和校验结果。

允许修改：

- `web/src/components/config/*`
- `web/src/components/jobs/*`
- `web/src/api/settings.*`
- `web/src/types/config.*`

禁止修改：

- 不允许展示 secret 原文。
- 不允许让用户编辑 Job 的运行快照。
- 不允许把 config_path 作为唯一正式配置入口展示给普通用户。

展示内容：

- config_source
- config_hash
- profile_id / profile_name（如有）
- snapshot_created_at
- validation_status
- masked values
- warnings / errors

验收标准：

- Job Detail 能看到配置快照。
- 敏感字段脱敏。
- 用户能看到配置来源。

---

## UI-V1-010 P0 实现 article_pipeline 操作页面

任务目标：

为 V1 核心业务切片提供可验收的文章处理入口。

允许修改：

- `web/src/pages/articles/*`
- `web/src/components/articles/*`
- `web/src/api/workflows.*`
- `web/src/api/jobs.*`

禁止修改：

- 不允许在页面中执行抓取、清洗、入库、抽取逻辑。
- 不允许绕过 Workflow / Job API。
- 不允许写死 article_pipeline 的完整后端逻辑。

页面能力：

1. 显示 article_pipeline 简介。
2. 显示输入参数表单，来源于 workflow/job schema。
3. 支持选择或输入 config 兼容参数。
4. 支持 dry run / force / max_articles 等已有参数。
5. 创建 Job 后跳转 Job Detail。
6. 显示最近 article pipeline Job。
7. 显示常见失败原因和恢复提示。

验收标准：

- 用户可以从文章页面触发 article_pipeline。
- 成功后能进入 Job Detail 查看执行过程和产物。
- 参数错误能在提交前或提交后明确显示。

---

## UI-V1-011 P0 Web UI 基础测试与验收

任务目标：

保证 V1 UI 不只是能打开页面，而是能支撑 article_pipeline 人工验收。

允许修改：

- `web/src/**/*.test.*`
- `web/tests/*`
- `docs/WebOnly-V1-Acceptance.md`
- `docs/New-Web-UI-TaskList.md`

禁止修改：

- 不允许删除已有测试来通过构建。
- 不允许只测试组件渲染，不测试核心用户路径。

测试路径：

1. 打开 Dashboard。
2. 进入 Workflows。
3. 选择 article_pipeline / pipeline-run。
4. 填写参数并提交。
5. 跳转 Job Detail。
6. 查看状态、日志、Config Snapshot、Artifact。
7. 处理失败状态。

验收标准：

- V1 人工验收路径可重复执行。
- UI smoke test 通过。
- 所有 P0 页面有 loading / error / empty 处理。

---

# V2 UI：正式用户工作台与 Profile UI

V2 UI 目标：从临时验收 UI 过渡为正式用户工作台，重点完成 Profile、市场数据、策略运行和正式信息架构。

## UI-V2-001 P0 正式 Web 信息架构重整

任务目标：

在保留 V1 可用性的基础上，建立面向真实用户的正式导航和页面组织。

允许修改：

- `web/src/routes/*`
- `web/src/layouts/*`
- `web/src/components/navigation/*`
- `web/src/pages/dashboard/*`

禁止修改：

- 不允许破坏 V1 核心路径。
- 不允许隐藏 Job Center。
- 不允许把未完成业务伪装成已完成。

实现要求：

1. Dashboard 展示系统状态、最近 Job、失败 Job、常用 Workflow。
2. 导航按业务分组：工作台、任务、产物、配置、管理。
3. 页面 Placeholder 显示版本和依赖任务。
4. 权限不足时显示解释。

验收标准：

- 用户可以从 Dashboard 进入主要业务入口。
- V1 article pipeline 路径仍可用。

---

## UI-V2-002 P0 Profile List / Detail / Import 页面

任务目标：

建立正式 Profile 管理入口，为 `config_path` 向 Profile 迁移提供用户界面。

允许修改：

- `web/src/pages/profiles/*`
- `web/src/components/profiles/*`
- `web/src/api/profiles.*`
- `web/src/types/profile.*`

禁止修改：

- 不允许在前端保存 secret 原文到 localStorage。
- 不允许让用户编辑运行中的 Job Snapshot。
- 不允许删除 config_path 兼容入口。
- 不允许把 Profile schema 写死在页面中。

页面范围：

1. Profile List：name、environment、status、updated_at、validation_status。
2. Profile Detail：basic info、config sections、masked secret fields、validation result、linked jobs。
3. Profile Import：from config_path、preview masked values、validate before save。
4. Snapshot Viewer：read-only、linked job、config_hash、source。

验收标准：

- 用户能从 Web 查看默认 Profile。
- 用户能导入现有 config_path 生成 Profile。
- Secret 字段脱敏。
- Job Detail 能跳转到对应 Snapshot。
- config_path 仍可作为兼容方式运行。

---

## UI-V2-003 P1 Profile Editor MVP

任务目标：

提供可控的 Profile 编辑能力，支持非敏感字段编辑和敏感字段安全更新。

允许修改：

- `web/src/pages/profiles/*`
- `web/src/components/profiles/ProfileEditor.*`
- `web/src/api/profiles.*`

禁止修改：

- 不允许回显 secret 原文。
- 不允许未校验直接保存。
- 不允许编辑已绑定历史 Job Snapshot。

实现要求：

1. 基于后端 Profile schema 渲染字段。
2. 非敏感字段可编辑。
3. 敏感字段只允许替换，不回显。
4. 保存前调用 validate。
5. 保存后生成新版本或 updated_at。
6. 显示 diff summary。

验收标准：

- 用户能安全更新 Profile。
- 配置非法时无法保存。
- Secret 不泄露。

---

## UI-V2-004 P0 Market Data Workspace

任务目标：

为市场数据链路提供正式 Web 工作台。

允许修改：

- `web/src/pages/market/*`
- `web/src/components/market/*`
- `web/src/api/workflows.*`
- `web/src/api/jobs.*`

禁止修改：

- 不允许页面直接调用 Provider。
- 不允许绕过 Job Center。
- 不允许把市场数据状态写死。

页面能力：

1. 展示市场数据 Workflow：kaipan-fetch、kaipan-normalize、kaipan-run、ohlcv-crawl、market-state-build、snapshot-build。
2. 根据 schema 渲染运行表单。
3. 显示最近市场数据 Job。
4. 显示数据新鲜度、最后成功时间、失败原因。
5. 产物跳转 Artifact / Job Detail。

验收标准：

- 用户能通过 Web 触发市场数据相关 Job。
- 用户能查看最近执行结果和失败原因。
- 所有长任务走 Job Center。

---

## UI-V2-005 P0 Strategy Workspace

任务目标：

为策略构建、盘前、盘后链路提供正式 Web 工作台。

允许修改：

- `web/src/pages/strategy/*`
- `web/src/components/strategy/*`
- `web/src/api/workflows.*`
- `web/src/api/jobs.*`

禁止修改：

- 不允许前端计算策略结果。
- 不允许绕过 Job/Workflow API。
- 不允许把交易员、日期、版本逻辑硬编码。

页面能力：

1. 触发 strategy-build。
2. 触发 run-pre-market。
3. 触发 run-after-close。
4. 查看最近策略版本 Job。
5. 查看证据包、报告、排名类 Artifact。
6. 显示常见失败原因和依赖数据缺失提示。

验收标准：

- 用户能完成策略相关 Job 创建。
- 策略结果产物可从 Job Detail 或 Artifact Center 打开。

---

## UI-V2-006 P1 Artifact Center

任务目标：

建立跨 Job 的产物中心，用户可以按类型、Job、业务域查找历史产物。

允许修改：

- `web/src/pages/artifacts/*`
- `web/src/components/artifacts/*`
- `web/src/api/artifacts.*`

禁止修改：

- 不允许直接遍历服务器目录。
- 不允许显示绝对路径。

页面能力：

- Artifact 列表
- 按 kind / job_type / date 过滤
- 预览 JSON / report metadata
- 下载
- 跳转 Job Detail

验收标准：

- 用户能找到最近产物。
- 缺失产物显示 partial 状态。

---

## UI-V2-007 P1 Web UI 错误恢复体验

任务目标：

让用户遇到任务失败、配置错误、数据缺失时知道如何恢复。

允许修改：

- `web/src/components/errors/*`
- `web/src/components/jobs/*`
- `web/src/pages/*`

禁止修改：

- 不允许只显示原始 stacktrace。
- 不允许隐藏技术详情，管理员应可展开查看。

实现要求：

1. ErrorExplanation 组件。
2. RetrySuggestion 组件。
3. MissingDependency 组件。
4. 技术详情折叠展示。
5. 根据 error.type 显示用户建议。

验收标准：

- 配置缺失、权限不足、Provider 失败、Artifact 缺失都有明确 UI。

---

# V3 UI：完整交付 UI、运维、权限、发布级体验

V3 UI 目标：覆盖回测、规则池、优化、管理员运维、权限审计和最终发布验收。

## UI-V3-001 P0 Backtest Center

任务目标：

为回测、规则验真、可复现性检查提供正式 Web 入口。

允许修改：

- `web/src/pages/backtest/*`
- `web/src/components/backtest/*`
- `web/src/api/workflows.*`
- `web/src/api/jobs.*`

禁止修改：

- 不允许前端计算回测指标。
- 不允许直接读取本地回测文件。
- 不允许绕过 Job Center。

页面能力：

1. 触发 backtest-run。
2. 触发 backtest-validate-rules。
3. 触发 backtest-reproducibility-check。
4. 展示回测 Job 历史。
5. 展示报告 Artifact、指标摘要、fingerprint。
6. 失败时显示数据缺失或配置错误提示。

验收标准：

- 用户能通过 Web 完成回测任务创建与结果查看。

---

## UI-V3-002 P0 Rule Pool Review UI

任务目标：

提供规则池审核、回测结果查看和审核决策入口。

允许修改：

- `web/src/pages/rules/*`
- `web/src/components/rules/*`
- `web/src/api/rules.*`
- `web/src/api/jobs.*`

禁止修改：

- 不允许前端直接修改规则状态，必须走 API。
- 不允许隐藏风险提示。

页面能力：

- 规则列表
- 规则详情
- 回测结果摘要
- 审核操作：approve / reject / needs_changes
- 审计记录
- 触发 rule-pool-backtest

验收标准：

- 管理员能完成规则审核闭环。
- 审核操作有确认和审计。

---

## UI-V3-003 P0 Optimize Candidate UI

任务目标：

支持候选策略版本生成、比较、确认和产物查看。

允许修改：

- `web/src/pages/optimize/*`
- `web/src/components/optimize/*`
- `web/src/api/workflows.*`
- `web/src/api/jobs.*`

禁止修改：

- 不允许前端生成候选策略文件。
- 不允许绕过 optimize-create-candidate Job。

页面能力：

- 触发 optimize-create-candidate
- 查看候选版本列表
- 查看调整摘要
- 对比父版本与候选版本
- 查看 Artifact

验收标准：

- 用户能通过 Web 生成候选版本并查看结果。

---

## UI-V3-004 P0 Admin Ops Console

任务目标：

提供管理员运维入口，包括健康检查、备份恢复、日志和告警。

允许修改：

- `web/src/pages/admin/*`
- `web/src/components/admin/*`
- `web/src/api/admin.*`
- `web/src/api/jobs.*`

禁止修改：

- 不允许普通用户看到高风险运维操作。
- 不允许高风险操作没有确认。
- 不允许 Web 任意执行 shell 命令。

页面能力：

- Health Check Dashboard
- Backup / Restore
- Failed Jobs
- Stale Jobs
- Basic Alerts
- System Info

验收标准：

- 管理员能判断系统是否健康。
- 高风险操作有确认、权限和审计。

---

## UI-V3-005 P0 Permission / Audit UI

任务目标：

提供用户权限、操作审计和 Job 审计查看能力。

允许修改：

- `web/src/pages/admin/audit/*`
- `web/src/pages/admin/users/*`
- `web/src/components/audit/*`
- `web/src/api/audit.*`

禁止修改：

- 不允许前端伪造权限。
- 不允许隐藏审计事件。

页面能力：

- 当前用户信息
- 用户/角色列表
- Job audit events
- 高风险操作审计
- 过滤和导出

验收标准：

- 管理员能追踪谁在什么时候做了什么操作。

---

## UI-V3-006 P1 Final UX Review 与发布级体验

任务目标：

完成最终交付前的 UI 一致性、可理解性和文档覆盖检查。

允许修改：

- `web/src/pages/*`
- `web/src/components/*`
- `docs/WebUserManual.md`
- `docs/Web-UserManual-Coverage.md`
- `docs/New-Web-UI-TaskList.md`

禁止修改：

- 不允许只做视觉润色而不修复阻断体验。
- 不允许文档描述和实际页面不一致。

检查内容：

1. 所有主要页面有标题、说明、状态和操作入口。
2. 所有高风险操作有确认。
3. 所有 Job 创建后能跳转 Job Detail。
4. 所有 Artifact 不暴露绝对路径。
5. 所有 secret 脱敏。
6. 用户手册流程与页面一致。
7. 错误状态用户可理解。

验收标准：

- V3 Release Checklist 通过。
- 用户手册可以指导真实用户完成核心操作。

---

## 5. UI Review Checklist

每个 Web UI PR 必须检查：

```text
[ ] 是否通过统一 API Client 调用后端？
[ ] 是否避免裸 fetch？
[ ] 是否没有复制后端业务规则？
[ ] 是否没有展示 secret 原文？
[ ] 是否没有展示服务器绝对路径？
[ ] 是否覆盖 loading / empty / error / permission denied？
[ ] 是否高风险操作有确认？
[ ] 是否失败时显示用户可理解原因？
[ ] 是否 Job 创建后跳转 Job Detail？
[ ] 是否 Artifact 展示有摘要和缺失处理？
[ ] 是否表单字段来自后端 schema 或稳定 API？
[ ] 是否更新用户文档或验收说明？
```

---

## 6. 主 TaskList 链接指引

主 TaskList 应在对应阶段添加引用：

```markdown
### UI 任务引用

本阶段涉及用户可见 Web 操作，必须同步执行 `docs/New-Web-UI-TaskList.md` 中对应任务：

- V1 阶段：`UI-V1-*`
- V2 阶段：`UI-V2-*`
- V3 阶段：`UI-V3-*`

没有完成对应 UI 任务的用户可见能力，不得标记为完整交付。
```

建议映射：

| 主任务阶段 | UI 引用 |
| --- | --- |
| V1 Runtime / Job / Workflow | UI-V1-001 ~ UI-V1-009 |
| V1 article_pipeline | UI-V1-010 ~ UI-V1-011 |
| V2 Profile | UI-V2-002 ~ UI-V2-003 |
| V2 Market | UI-V2-004 |
| V2 Strategy | UI-V2-005 |
| V2 Artifact Center | UI-V2-006 |
| V3 Backtest | UI-V3-001 |
| V3 Rule Pool | UI-V3-002 |
| V3 Optimize | UI-V3-003 |
| V3 Admin/Ops | UI-V3-004 ~ UI-V3-005 |
| V3 Release | UI-V3-006 |
