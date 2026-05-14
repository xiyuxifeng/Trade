# New-Web-UI-TaskList

> `trade-strategy-ai` Web UI 专项 AI 可执行任务清单。  
> 本文档不是独立项目，而是 `New-Web-TaskList.md` 的 UI 子计划。  
> **UI 任务必须随着 V1/V2/V3 主任务一起执行，不能等后端全部完成后再补。**

---

## 0. 执行关系

### 0.1 与主 TaskList 的关系

- 主文档：`New-Web-TaskList.md`
- UI 专项文档：`New-Web-UI-TaskList.md`

执行规则：

```text
每个 V1/V2/V3 Stage 开始前：
先阅读主 TaskList 的 Stage 目标
再阅读本 UI TaskList 对应版本的 UI 任务
最后按 Task ID 分批实现
```

### 0.2 UI 版本定位

| 版本 | UI 定位 | 目标 |
| --- | --- | --- |
| UI-V1 | 临时但规范化的验收 UI | 支撑 article_pipeline 和运行底座验收 |
| UI-V2 | 正式用户工作台 | 建立正式信息架构、Profile UI、Market/Strategy 工作台 |
| UI-V3 | 完整交付 UI | 补齐 Backtest、Rule Pool、Admin Ops、权限审计、最终体验 |

### 0.3 重要原则

当前 Web UI 是临时解决方案，但 Web UI 任务不能随意堆功能。  
长期稳定资产是：

```text
API Client
页面路由
业务工作台信息架构
Job Detail 展示口径
Workflow Form 生成规则
Artifact 展示规则
Config/Profile 展示规则
错误和权限状态
测试与验收流程
```

---

## 1. AI UI Implementation Rules

1. 每次只实现一个 UI Task ID。
2. 页面组件不得直接调用裸 `fetch`，必须通过统一 API Client。
3. 页面不得直接拼接服务器绝对路径。
4. 页面不得展示 token、cookie、secret、password 原文。
5. 页面不得写业务执行逻辑。
6. 表单 schema 优先来自后端 JobDefinition / WorkflowDefinition / PipelineSpec。
7. 不得在前端硬编码 risk、permission、required、default，除非任务明确要求。
8. 所有页面必须处理 loading、empty、error、permission denied。
9. Job 状态以后端 status 为准，前端不得自行推断。
10. 高风险操作必须显示确认。
11. 新增用户可见页面必须有验收说明。
12. UI 任务完成后必须检查主 TaskList 的对应业务任务是否已提供 API。
13. 如果后端 API 缺失，不要伪造数据完成页面，应标记 Blocking 或使用明确 mock boundary。
14. 不引入大型 UI 框架，除非项目已有依赖或任务明确批准。
15. V1 UI 可以朴素，但不能破坏后续 V2/V3 正式 UI 的路径。

---

## 2. UI 架构目标

```text
web/src/
  api/
    client.ts
    jobs.ts
    workflows.ts
    pipelines.ts
    artifacts.ts
    profiles.ts
    market.ts
    backtest.ts
    rules.ts
    admin.ts
  types/
    job.ts
    workflow.ts
    pipeline.ts
    artifact.ts
    profile.ts
    market.ts
    backtest.ts
    rule.ts
    api.ts
  layouts/
    AppLayout.tsx
  routes/
    index.tsx
  pages/
    dashboard/
    jobs/
    workflows/
    articles/
    profiles/
    market/
    strategy/
    backtest/
    rule-pool/
    admin/
    settings/
  components/
    ui/
    jobs/
    workflows/
    artifacts/
    profiles/
    forms/
    layout/
  hooks/
```

---

# UI-V1：临时但规范化的验收 UI

## UI-V1 目标

UI-V1 只要求支撑 V1 验收，不追求最终视觉设计。  
但它必须为后续正式 UI 打好边界：

- 统一 API Client。
- 基础 Layout 和路由。
- Job List / Job Detail。
- Workflow Catalog。
- Schema-driven Run Form。
- Artifact Panel。
- Config Snapshot Readonly Panel。
- article_pipeline 页面。
- 基础测试和人工验收。

---

### [x] UI-V1-001 P0 Web UI 临时策略与路由规划

任务目标：明确 V1 UI 是临时验收入口，同时建立单一 canonical 路由、显式 legacy 兼容层和明确退役计划，不阻碍 V2/V3 的正式路由。

当前相关文件：

- `web/src/`
- `api/routers/ui/jobs.py`
- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `docs/New-Web-UI-Routing.md`

允许修改：

- `docs/New-Web-UI-Routing.md`
- `web/src/routes/*`
- `web/src/App.*`

禁止修改：

- 不做最终视觉设计。
- 不删除现有可用页面，除非提供兼容路由。
- 不在路由里写业务执行逻辑。

实现要求：

1. 定义 V1 路由：
   - `/dashboard`
   - `/jobs`
   - `/jobs/:jobId`
   - `/workflows`
   - `/workflows/:workflowId/run`
   - `/articles`
   - `/artifacts`
   - `/settings`
2. 未实现页面必须显示明确 placeholder。
3. `legacy` 入口只允许作为兼容层存在，不得与 canonical 路由并行扩张。
4. 路由文档必须说明每个 legacy 入口的 canonical 映射和退役阶段。
5. 现有临时页面可以挂到 `/legacy/*`，但必须在文档里标记退出条件。

状态要求：

- loading
- route not found
- page not implemented

验收标准：

- 所有 V1 路由可访问。
- 未实现页面不是空白页。
- 现有可用页面未被破坏。

主任务关联：

- `NW-V1-S0-001`
- `NW-V1-S0-003`

完成情况：

- 已建立单一 canonical 路由和显式 legacy 兼容层。
- 已输出路由文档：[docs/New-Web-UI-Routing.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/New-Web-UI-Routing.md)
- 已补齐 `/dashboard`、`/jobs/:jobId`、`/workflows/:workflowId/run`、`/articles`、`/legacy/*` 的路由与占位页。
- 已把 `/`、`/overview`、`/workflows/:workflowId` 作为 legacy 入口收口到 canonical 路由。
- 已补充路由解析测试：[web/src/app/route-registry.test.ts](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/app/route-registry.test.ts)
- 兼容层退役计划已同步写入 V2/V3 任务阶段。

---

### [ ] UI-V1-002 P0 建立统一 API Client

任务目标：所有 Web 页面通过统一 API Client 调用后端，避免请求逻辑散落。

允许修改：

- `web/src/api/client.ts`
- `web/src/api/jobs.ts`
- `web/src/api/workflows.ts`
- `web/src/api/pipelines.ts`
- `web/src/api/artifacts.ts`
- `web/src/types/api.ts`
- `web/src/hooks/*`

禁止修改：

- 不允许页面组件直接调用裸 `fetch`。
- 不允许在组件中硬编码 API base URL。
- 不允许吞掉 API error。
- 不允许所有 response 都长期使用 `any`。

实现要求：

1. 封装基础 request 方法。
2. 支持 base URL 配置。
3. 支持 API key / auth header 注入。
4. 统一 HTTP error 结构。
5. 提供 jobs/workflows/pipelines/artifacts client。
6. API error 至少包含 status、message、detail、requestId，如果后端提供。

状态要求：

- network error
- unauthorized
- forbidden
- not found
- validation error
- server error

测试要求：

- 至少测试 API Client error mapping。
- Job List 或 Job Detail 使用 API Client。

验收标准：

- 页面中不新增裸 fetch。
- Job API 调用经统一 client。
- 错误能统一展示。

主任务关联：

- `NW-V1-S3-003`

---

### [x] UI-V1-003 P0 基础 Layout 与导航

任务目标：建立统一页面框架，为后续业务工作台提供稳定入口。

允许修改：

- `web/src/layouts/AppLayout.*`
- `web/src/components/layout/*`
- `web/src/components/navigation/*`
- `web/src/routes/*`

禁止修改：

- 不做复杂主题系统。
- 不把权限逻辑写死到页面内部。
- 不把业务 API 调用放到 Layout。

实现要求：

1. 提供 Sidebar + Header + Content。
2. 导航项包含：
   - Dashboard
   - Jobs
   - Workflows
   - Articles
   - Artifacts
   - Settings
3. 导航项预留 permission 字段。
4. 当前页面高亮。
5. Header 展示环境/用户/连接状态占位。

状态要求：

- collapsed sidebar 可选。
- unknown permission 时默认隐藏高风险入口或显示 disabled。

验收标准：

- 所有 V1 页面使用统一 Layout。
- 导航跳转正常。
- 未实现入口有 placeholder。

主任务关联：

- `NW-V1-S0-003`

完成情况：

- 已完成统一页面框架与基础导航。
- 当前实现已包含 Sidebar、Header、Content、当前页面高亮和权限入口控制。
- 未生成单独文档，当前以代码实现为准。

---

### [ ] UI-V1-004 P0 Job List 页面

任务目标：让用户查看任务列表、状态和基本筛选。

允许修改：

- `web/src/pages/jobs/JobListPage.*`
- `web/src/components/jobs/JobTable.*`
- `web/src/api/jobs.ts`
- `web/src/types/job.ts`

禁止修改：

- 不在前端伪造 Job 状态。
- 不直接读取文件路径。
- 不把后端状态转换成不一致的前端状态。

页面必须展示：

- job_id
- job_type
- status
- created_by
- created_at
- started_at
- finished_at
- retry_count
- actions：查看详情

筛选：

- status
- job_type
- created_by，可选
- pagination

状态要求：

- loading
- empty
- error
- permission denied

验收标准：

- 能展示 Job 列表。
- 点击进入 Job Detail。
- API 错误可见。
- 空列表有友好提示。

主任务关联：

- `NW-V1-S2-002`
- `NW-V1-S4-001`

---

### [ ] UI-V1-005 P0 Job Detail 页面

任务目标：让用户理解一个 Job 的输入、执行过程、结果、失败原因和产物。

允许修改：

- `web/src/pages/jobs/JobDetailPage.*`
- `web/src/components/jobs/*`
- `web/src/api/jobs.ts`
- `web/src/types/job.ts`

边界说明：

- 只消费后端返回的 Job / Step / Artifact / Config Snapshot 结果，不在页面内补业务判断。
- 不自己解析文件系统路径，不从 `params` 或 `result` 里推断后端未暴露的事实。
- 产物、日志、快照都必须来自 API contract，页面只负责展示与轻量交互。

禁止修改：

- 不在前端推断 Job 成败。
- 不展示服务器绝对路径。
- 不展示 secret 原文。
- 不写死 Artifact 下载 URL。
- 不把日志、产物、配置解析逻辑散落到页面。

页面必须展示：

1. Job 基本信息：
   - job_id
   - job_type
   - status
   - created_by
   - idempotency_key
   - retry_count
   - created_at
   - started_at
   - finished_at
2. 参数快照：
   - params
   - config snapshot ref
   - masked sensitive fields
3. Step Timeline：
   - step name
   - status
   - started_at
   - finished_at
   - duration
   - error summary
4. 日志：
   - 最近日志
   - 刷新按钮
   - 下载日志，如果 API 支持
5. 错误：
   - error type
   - user message
   - technical detail，可折叠
   - retry suggestion
6. 产物：
   - artifact type
   - title
   - summary
   - created_at
   - preview/download action

状态要求：

- loading
- not found
- running refresh
- failed
- cancelled
- permission denied
- artifact missing

验收标准：

- 成功 Job 可看到结果和产物。
- 失败 Job 可看到失败原因。
- 运行中 Job 可刷新状态。
- Secret 不显示。
- 服务器路径不显示。

主任务关联：

- `NW-V1-S1-002`
- `NW-V1-S1-003`
- `NW-V1-S2-002`
- `NW-V1-S3-002`

---

### [ ] UI-V1-006 P0 Step Timeline Component

任务目标：提供通用 Step Timeline 组件供 Job Detail 和业务页面复用。

允许修改：

- `web/src/components/jobs/StepTimeline.*`
- `web/src/types/job.ts`

禁止修改：

- 不在组件内部调用 API。
- 不自行推断不存在的 step。
- 不把 timeline 当日志文本解析。

实现要求：

1. 接收 timeline items props。
2. 支持 pending/running/success/failed/cancelled/skipped。
3. 展示时间、耗时、错误摘要。
4. 支持点击 Step 展开详情。
5. 支持空 timeline fallback。

验收标准：

- Job Detail 使用该组件。
- 空 timeline 有 fallback。
- failed step 显示错误摘要。

主任务关联：

- `NW-V1-S2-002`

---

### [ ] UI-V1-007 P0 Schema-driven Workflow Run Form

任务目标：根据后端 JobDefinition / WorkflowDefinition / PipelineSpec 动态渲染运行表单，避免前后端 schema 分叉。

允许修改：

- `web/src/pages/workflows/*`
- `web/src/components/forms/*`
- `web/src/components/workflows/*`
- `web/src/api/workflows.ts`
- `web/src/types/workflow.ts`

禁止修改：

- 不在前端手写每个 job_type 的完整参数 schema。
- 不绕过后端 validate API。
- 不硬编码 required/default/risk。
- 不直接创建 Job 绕过 workflow/pipeline API，除非后端只提供 Job API 且任务明确允许。

字段类型：

- string
- integer
- number
- boolean
- date
- path
- object
- array

实现要求：

1. 从 API 获取 definition。
2. 根据 param_schema 渲染字段。
3. 显示 description、required、default。
4. 提交前调用 validate API，如果存在。
5. 高风险任务显示确认弹窗。
6. 创建成功后跳转 Job Detail。
7. validation error 显示到对应字段。

状态要求：

- loading definition
- validation failed
- submit failed
- confirmation required
- success redirect

验收标准：

- pipeline-run 可以通过表单创建。
- 缺少 required 字段有明确提示。
- 高风险任务需要确认。
- 字段来自后端 schema。

主任务关联：

- `NW-V1-S1-004`
- `NW-V1-S3-003`

---

### [ ] UI-V1-008 P0 Artifact Panel

任务目标：统一展示 Job / Step 产物，让用户知道结果是什么、怎么下载、如何解释。

允许修改：

- `web/src/components/artifacts/ArtifactPanel.*`
- `web/src/api/artifacts.ts`
- `web/src/types/artifact.ts`

边界说明：

- 只渲染后端给出的 artifact 元数据，不在组件内发现、拼接或推断 artifact。
- 不直接读取文件系统，不拼服务器绝对路径，不自己生成下载地址。
- 预览与下载都必须走 API 返回的安全入口，不扩展成跨 Job 搜索或资源管理中心。

禁止修改：

- 不展示服务器绝对路径。
- 不直接使用 path 作为下载链接。
- 不假设所有 artifact 都是文件。
- 不把 preview 逻辑写死到 Job Detail。

Artifact 类型至少支持：

- report
- csv
- json
- log
- chart-data
- snapshot
- external-link

实现要求：

1. 展示 title、kind、summary、created_at、size。
2. 支持 download action。
3. 支持 JSON preview。
4. 支持 missing artifact error。
5. 支持 permission denied。
6. 支持按 Step 分组。

验收标准：

- Job Detail 使用 Artifact Panel。
- 缺失产物不导致页面崩溃。
- 下载不暴露服务器路径。
- 用户能理解 artifact 含义。

主任务关联：

- `NW-V1-S1-003`

---

### [ ] UI-V1-009 P0 Config Snapshot Readonly Panel

任务目标：展示 Job 使用的脱敏配置快照，支撑复盘和问题定位。

允许修改：

- `web/src/components/profiles/ConfigSnapshotPanel.*`
- `web/src/api/profiles.ts`
- `web/src/types/profile.ts`

边界说明：

- 只展示 Job 关联的脱敏配置快照，不把快照当成可编辑 Profile。
- 不从 localStorage 或前端缓存还原配置原文，不反向推断未暴露字段。
- 页面只负责“看快照”和“定位问题”，不负责快照生成或配置修复。

禁止修改：

- 不展示 secret 原文。
- 不允许编辑 Job Snapshot。
- 不把 snapshot 当 Profile 编辑。
- 不使用 localStorage 保存配置。

页面展示：

- config_source
- config_hash
- profile_id，如果有
- snapshot_created_at
- validation_status
- masked sections
- missing/invalid fields

状态要求：

- no snapshot
- loading
- invalid config
- permission denied

验收标准：

- Job Detail 能展示脱敏配置。
- Secret 字段显示为 masked。
- 无 snapshot 时有明确提示。

主任务关联：

- `NW-V1-S1-002`

---

### [ ] UI-V1-010 P0 Article Pipeline Page

任务目标：提供 V1 核心业务入口，让用户通过 Web 完成 article_pipeline 验收。

允许修改：

- `web/src/pages/articles/ArticlePipelinePage.*`
- `web/src/components/articles/*`
- `web/src/api/pipelines.ts`
- `web/src/types/pipeline.ts`

禁止修改：

- 不在页面中执行 pipeline 逻辑。
- 不直接调用 crawl/pipeline 内部 API。
- 不硬编码所有参数 schema。
- 不绕过 Job Center。

页面能力：

1. 查看 article_pipeline 说明。
2. 查看输入参数。
3. 选择/输入 config_path 或 Profile，占位兼容。
4. 提交运行。
5. 创建成功跳转 Job Detail。
6. 显示最近 article_pipeline jobs。
7. 显示常见失败原因说明。

状态要求：

- API unavailable
- validation error
- running
- success
- failed
- empty history

验收标准：

- 用户可以从该页面触发 article_pipeline。
- 创建 Job 后能跳转详情。
- 最近任务可查看。
- 失败原因能回到 Job Detail 定位。

主任务关联：

- `NW-V1-S3-001`
- `NW-V1-S3-002`
- `NW-V1-S3-003`

---

### [ ] UI-V1-011 P0 Web UI 基础测试和验收

任务目标：为 V1 UI 提供基础回归和人工验收路径。

允许修改：

- `web/src/**/*.test.*`
- `web/tests/*`
- `docs/New-Web-UI-V1-Acceptance.md`

禁止修改：

- 不为了通过测试删除状态处理。
- 不只测试 happy path。

测试/验收覆盖：

1. 路由可访问。
2. Job List loading/empty/error。
3. Job Detail success/failed/no artifact。
4. Workflow Form required validation。
5. Article Pipeline submit success。
6. Config Snapshot masked。
7. Artifact missing fallback。

验收标准：

- 有自动化测试或明确人工验收步骤。
- 文档能指导用户完整跑通 V1 UI。

主任务关联：

- `NW-V1-S4-001`
- `NW-V1-S4-002`

---

# UI-V2：正式用户工作台

## UI-V2 目标

UI-V2 从临时验收 UI 升级为正式用户工作台。  
重点是 Profile 迁移、正式信息架构、Dashboard、Market Data、Strategy、Artifact Center。

---

### [ ] UI-V2-001 P0 正式 Web 信息架构

任务目标：建立正式产品级导航与页面分组，替代 V1 临时页面结构。

允许修改：

- `web/src/routes/*`
- `web/src/layouts/*`
- `web/src/components/navigation/*`
- `docs/New-Web-UI-Information-Architecture.md`

禁止修改：

- 不删除 V1 页面入口，除非提供 redirect。
- 不把业务权限写死在组件里。
- 不做过度视觉重构。

正式导航：

- Dashboard
- Workflows
- Jobs
- Articles
- Market Data
- Strategy
- Backtest，占位
- Rule Pool，占位
- Artifacts
- Profiles
- Admin
- Settings

验收标准：

- V1 页面仍可访问。
- 新导航结构清晰。
- 未完成模块显示 V2/V3 placeholder。

主任务关联：

- `NW-V2-S1-001`
- `NW-V2-S2-001`
- `NW-V2-S3-001`

---

### [ ] UI-V2-002 P0 Profile List / Detail / Import

任务目标：建立正式 Profile 管理入口，为 config_path 迁移提供用户路径。

允许修改：

- `web/src/pages/profiles/*`
- `web/src/components/profiles/*`
- `web/src/api/profiles.ts`
- `web/src/types/profile.ts`

禁止修改：

- 不在前端保存 secret 原文。
- 不允许编辑运行中的 Job snapshot。
- 不把 Profile schema 写死在页面。
- 不删除 config_path 兼容入口。

页面范围：

1. Profile List：
   - name
   - environment
   - status
   - updated_at
   - validation_status
2. Profile Detail：
   - basic info
   - config sections
   - masked secret fields
   - validation result
   - linked jobs
3. Profile Import：
   - from config_path
   - masked preview
   - validate before save
4. Snapshot Viewer：
   - read-only
   - linked job
   - config_hash
   - source

状态要求：

- no profile
- import failed
- validation failed
- permission denied

验收标准：

- 用户能查看默认 Profile。
- 用户能导入 config_path 生成 Profile。
- Secret 脱敏。
- Job Detail 能跳转 snapshot。
- config_path 仍可兼容运行。

主任务关联：

- `NW-V2-S1-001`
- `NW-V2-S1-002`

---

### [ ] UI-V2-003 P1 Profile Editor MVP

任务目标：提供最小可用 Profile 编辑能力。

禁止修改：

- 不编辑 secret 原文。
- 不允许保存未通过基本校验的 Profile。
- 不影响历史 Job Snapshot。

实现要求：

1. 分 section 编辑。
2. 字段说明、默认值、来源提示。
3. 保存前 validate。
4. 保存后生成新 version。
5. 支持 archive 而不是硬删除。

验收标准：

- 可编辑非敏感字段。
- 保存产生新版本。
- 历史 Job Snapshot 不变化。

主任务关联：

- `NW-V2-S1-001`

---

### [ ] UI-V2-004 P0 Dashboard 首页

任务目标：提供用户进入系统后的总览页面。

页面内容：

- 今日/最近 Job 状态统计。
- 最近失败任务。
- 最近 artifacts。
- Profile 状态。
- Market/Strategy 快捷入口。
- 系统健康状态简要，占位可用。

禁止修改：

- 不在 Dashboard 执行业务动作。
- 不重复实现 Job 查询逻辑，必须使用 API Client。

验收标准：

- 用户可以从 Dashboard 进入主要工作台。
- 失败任务可跳转 Job Detail。
- 空数据状态友好。

主任务关联：

- `NW-V2-S2-001`
- `NW-V2-S3-001`

---

### [ ] UI-V2-005 P0 Market Data Workspace

任务目标：提供市场数据链路的正式 Web 工作台。

覆盖能力：

- Kaipan fetch
- Kaipan normalize
- Kaipan run
- OHLCV crawl
- Market State build
- Snapshot build

页面能力：

1. 查看 Market Data workflows。
2. 运行指定任务。
3. 查看最近任务。
4. 查看 provider/config 错误。
5. 查看 market data artifacts。
6. 跳转 Job Detail。

禁止修改：

- 不直接调用 provider。
- 不在前端拼接 market data 文件路径。
- 不绕过 Job Center。

验收标准：

- 能触发至少一个 market workflow。
- 失败时用户能理解是配置、provider、数据还是系统错误。
- 产物可查看。

主任务关联：

- `NW-V2-S2-001`
- `NW-V2-S2-002`

---

### [ ] UI-V2-006 P0 Strategy Workspace

任务目标：提供策略版本、盘前、盘后相关操作入口。

覆盖能力：

- strategy-build
- run-pre-market
- run-after-close
- evidence package
- ranking/report artifacts

页面能力：

1. 选择 trader/date/profile。
2. 触发策略构建。
3. 触发盘前/盘后。
4. 查看最近策略任务。
5. 查看报告和证据包。
6. 跳转 Artifact Center。

禁止修改：

- 不在前端计算策略结果。
- 不在前端推断排名。
- 不绕过 Workflow/Job。

验收标准：

- 用户能通过 Web 运行策略相关任务。
- 结果能通过 artifact 解释。
- 高风险/覆盖操作需要确认。

主任务关联：

- `NW-V2-S3-001`
- `NW-V2-S3-002`

---

### [ ] UI-V2-007 P0 Artifact Center

任务目标：提供跨 Job 的产物检索和查看入口。

页面能力：

- 按 artifact kind 筛选。
- 按 job_type 筛选。
- 按 date 筛选。
- 查看 artifact summary。
- 下载/预览。
- 跳转来源 Job。

禁止修改：

- 不直接使用文件系统路径。
- 不把 artifact 当成只有文件下载。
- 不显示无权限 artifact 内容。

验收标准：

- 用户能找到最近产物。
- artifact 能回溯到 Job。
- 缺失/过期/无权限有明确状态。

主任务关联：

- `NW-V1-S1-003`
- `NW-V2-S2-002`
- `NW-V2-S3-002`

---

### [ ] UI-V2-008 P1 Web UI 错误恢复体验

任务目标：统一错误展示，让用户知道下一步怎么处理。

错误类型：

- validation error
- permission denied
- config missing
- provider unavailable
- data empty
- artifact missing
- job failed
- network error

实现要求：

1. 通用 ErrorState。
2. 错误详情可折叠。
3. 用户建议单独展示。
4. 可跳转 Job Detail / Settings / Profile。

验收标准：

- Market/Strategy/Profile/Job 页面使用统一错误组件。
- 用户可以理解下一步操作。

主任务关联：

- 所有 V2 P0。

---

### [ ] UI-V2-009 P1 UI Component Kit

任务目标：提供统一组件，避免业务页面重复实现。

组件清单：

- PageHeader
- SectionCard
- StatusBadge
- RiskBadge
- DataTable
- EmptyState
- ErrorState
- LoadingState
- ConfirmDialog
- JsonViewer
- ArtifactList
- LogViewer
- SchemaForm

验收标准：

- Job、Profile、Market、Strategy 页面至少复用核心组件。
- 新页面不再复制基础状态组件。

主任务关联：

- 所有 UI-V2 页面。

---

### [ ] UI-V2-010 P0 Market Snapshot Browser

任务目标：让用户在 Web 中查询、查看和理解 Market Snapshot，而不是依赖本地文件。

主任务关联：

- `NW-V2-S2-003 扩展 Market Snapshot 数据覆盖`
- `NW-V2-S2-004 Market Data DB Storage`
- `NW-V2-S2-005 Market Snapshot Query API`
- `NW-V2-S2-006 Market Regime Feature Build`

允许修改：

- `web/src/pages/market/MarketSnapshotBrowserPage.*`
- `web/src/components/market/*`
- `web/src/api/market.ts`
- `web/src/types/market.ts`
- `web/src/routes/*`

禁止修改：

- 不直接读取文件路径。
- 不直接调用 provider。
- 不在前端计算 Market Snapshot。
- 不展示 provider secret 或私有凭据。
- 不伪造 snapshot 数据完成页面。

页面能力：

1. 按 `trade_date` / `market` / `quality_status` 查询 snapshot。
2. 展示 snapshot list：
   - snapshot_id
   - trade_date
   - market
   - data_version
   - quality_status
   - created_at
3. 展示 snapshot detail：
   - sections
   - record_count
   - provider
   - missing_reason
   - quality_status
4. 支持查看 data quality report。
5. 支持跳转来源 Job Detail。
6. 支持跳转 Artifact Center。
7. 支持查看 regime features，如果 API 已提供。

状态要求：

- loading
- empty
- partial snapshot
- data missing
- permission denied
- API unavailable
- invalid query

验收标准：

- 用户可以通过 Web 查询指定日期的 Market Snapshot。
- 用户可以看到每个 section 的数据质量和缺失原因。
- 页面不暴露服务器绝对路径。
- Snapshot 缺失时有明确错误说明。
- 可以从 Snapshot 跳转到来源 Job / Artifact。

---

### [ ] UI-V2-011 P0 Market Dataset Viewer

任务目标：让用户查看 DB 中的市场数据集摘要和样本，支撑外部系统接入前的人工验证。

主任务关联：

- `NW-V2-S2-004 Market Data DB Storage`
- `NW-V2-S2-005 Market Snapshot Query API`

允许修改：

- `web/src/pages/market/MarketDatasetViewerPage.*`
- `web/src/components/market/*`
- `web/src/api/market.ts`
- `web/src/types/market.ts`

禁止修改：

- 不直接读取本地文件。
- 不在前端拼接 SQL。
- 不一次性加载超大数据集。
- 不绕过 API pagination。

页面能力：

1. 按 dataset_id / trade_date / symbol / section 查询。
2. 展示 dataset metadata。
3. 展示分页 sample rows。
4. 展示 data quality summary。
5. 支持跳转 snapshot detail。
6. 支持下载导出 artifact，如果后端支持。

状态要求：

- loading
- empty
- pagination loading
- permission denied
- dataset missing
- API unavailable

验收标准：

- 用户可以通过 Web 查看 DB 中的市场数据摘要。
- 大数据集不会一次性全量加载。
- 数据集能回溯到 snapshot_id。
- 页面不暴露服务器绝对路径。

---

# UI-V3：完整交付 UI

## UI-V3 目标

UI-V3 补齐完整交付版本需要的高级业务页面、运维页面、权限审计和最终体验。

---

### [ ] UI-V3-001 P0 Backtest Center

任务目标：提供回测运行、结果查看、可复现性检查入口。

覆盖能力：

- backtest-run
- backtest-validate-rules
- backtest-reproducibility-check

页面能力：

1. 选择 trader/date range/strategy version/profile。
2. 触发回测。
3. 查看指标摘要。
4. 查看报告 artifact。
5. 查看 reproducibility fingerprint。
6. 跳转 Job Detail。

禁止修改：

- 不在前端计算回测指标。
- 不伪造 fingerprint。
- 不绕过 Job Center。

验收标准：

- 用户能运行回测。
- 用户能理解结果。
- 失败/无数据有清晰提示。

主任务关联：

- `NW-V3-S1-001`

---

### [ ] UI-V3-002 P0 Rule Pool Review UI

任务目标：提供规则池审核、回测、批准/拒绝入口。

页面能力：

- rule list
- rule detail
- backtest result
- approve/reject action
- audit history
- high-risk confirmation

禁止修改：

- 不让无权限用户审核。
- 不跳过高风险确认。
- 不在前端直接写库。

验收标准：

- 审核动作有审计。
- 高风险操作有确认。
- 结果可追踪到 Job。

主任务关联：

- `NW-V3-S1-002`

---

### [ ] UI-V3-003 P0 Optimize Candidate UI

任务目标：提供优化候选版本查看、比较和提交审核入口。

页面能力：

- candidate list
- candidate detail
- parent version
- adjustments
- backtest evidence
- artifact links
- submit/approve/reject

验收标准：

- 候选版本来源可追溯。
- 调整内容可解释。
- 操作有权限和审计。

主任务关联：

- `NW-V3-S1-002`

---

### [ ] UI-V3-004 P0 Admin Ops Console

任务目标：提供管理员运维入口。

页面能力：

- system overview
- job recovery
- stale jobs
- provider checks
- storage checks
- recent critical failures

禁止修改：

- 不让普通用户访问。
- 不在前端执行 shell。
- 高风险操作必须确认。

验收标准：

- 管理员能判断系统运行状态。
- 失败任务可恢复或定位。
- 操作有审计。

主任务关联：

- `NW-V3-S2-002`

---

### [ ] UI-V3-005 P0 Health Check Dashboard

任务目标：展示系统健康状态。

展示项：

- API status
- DB status
- worker status
- job queue status
- provider connectivity
- storage/artifact status
- config/profile validation status

验收标准：

- 健康异常有明确提示。
- 能跳转到相关设置或 Job。
- 不泄露敏感配置。

主任务关联：

- `NW-V3-S2-002`

---

### [ ] UI-V3-006 P0 Backup / Restore UI

任务目标：提供备份和恢复操作入口。

页面能力：

- backup list
- create backup
- restore preview
- restore confirmation
- restore job status
- audit history

禁止修改：

- 不允许无确认恢复。
- 不允许普通用户恢复。
- 不直接拼接备份路径。
- 不绕过 Job Center。

验收标准：

- 备份/恢复通过 Job 执行。
- 恢复前有风险提示。
- 结果可审计。

主任务关联：

- `NW-V3-S2-002`

---

### [ ] UI-V3-007 P0 Permission / Audit UI

任务目标：让管理员查看权限、审计和高风险操作历史。

页面能力：

- audit event list
- filter by actor/job_type/operation/date
- high-risk actions
- permission denied logs
- job audit detail

禁止修改：

- 不展示 secret。
- 不允许前端绕过权限。
- 不伪造 audit 数据。

验收标准：

- 管理员能追踪关键操作。
- 高风险操作可审计。
- 无权限用户无法访问。

主任务关联：

- `NW-V3-S2-001`

---

### [ ] UI-V3-008 P0 Final UX Review

任务目标：对所有正式 UI 做发布前体验收口。

检查范围：

- navigation consistency
- status consistency
- error consistency
- artifact consistency
- form validation
- permission states
- mobile/responsive basic behavior
- empty states
- loading states

验收标准：

- 所有 V1/V2/V3 P0 页面通过人工验收。
- 用户能完成主流程。
- 页面不出现空白、未处理异常、明显错位。
- 文案与用户手册一致。

主任务关联：

- `NW-V3-S3-001`

---

### [ ] UI-V3-009 P0 User Manual Coverage Verification

任务目标：确保用户手册、管理员手册和实际 UI 一致。

允许修改：

- `docs/New-Web-UserManual.md`
- `docs/New-Web-Admin-Manual.md`
- `docs/New-Web-Final-Acceptance.md`

验收标准：

- 每个手册步骤在 UI 中存在对应入口。
- 页面名称一致。
- 操作结果一致。
- 错误处理说明一致。
- 不再出现“只能通过 CLI 完成”的正式用户流程。

主任务关联：

- `NW-V3-S3-001`

---

### [ ] UI-V3-010 P0 Market Regime Viewer

任务目标：展示指定交易日或 snapshot 的 Market Regime，让用户理解系统如何判断当前市场状态。

主任务关联：

- `NW-V3-SX-001 Market Regime Definition`

允许修改：

- `web/src/pages/market/MarketRegimeViewerPage.*`
- `web/src/components/market/*`
- `web/src/api/market.ts`
- `web/src/types/market.ts`

禁止修改：

- 不在前端计算 regime。
- 不隐藏 low confidence / missing features。
- 不把 regime 展示成不可解释的单一标签。

验收标准：

- 用户可以看到 regime labels、features、confidence。
- 用户可以看到每个 label 的证据来源。
- 数据不足时显示 missing_reason。

---

### [ ] UI-V3-011 P0 Regime Backtest Report

任务目标：展示 rule / strategy 在不同 market regime 下的回测表现，避免只看整体指标。

主任务关联：

- `NW-V3-SX-002 Regime-aware Backtest`

允许修改：

- `web/src/pages/backtest/RegimeBacktestReportPage.*`
- `web/src/components/backtest/*`
- `web/src/api/backtest.ts`
- `web/src/types/backtest.ts`

禁止修改：

- 不在前端计算回测指标。
- 不隐藏 sample_count / confidence。
- 不把低样本结论展示为强结论。

验收标准：

- 用户可以同时看到 overall metrics 和 per-regime metrics。
- 用户可以看到某 rule 在不同 regime 下的表现差异。
- 低样本 regime 有明确标记。
- 可以跳转来源 Backtest Job / Artifact。

---

### [ ] UI-V3-012 P0 Rule Applicability Viewer

任务目标：展示每条 rule 的适用市场环境、禁用市场环境和证据来源。

主任务关联：

- `NW-V3-SX-003 Rule Applicability Profile`

允许修改：

- `web/src/pages/rule-pool/RuleApplicabilityPage.*`
- `web/src/components/rules/*`
- `web/src/api/rules.ts`
- `web/src/types/rule.ts`

禁止修改：

- 不在前端修改 rule 原始定义。
- 不隐藏 blocked_regimes。
- 不允许无审计地激活低置信度 profile。

验收标准：

- 用户可以看到 applicable_regimes / blocked_regimes / neutral_regimes。
- 用户可以看到 source_backtest_id。
- 用户可以看到 profile version 和 review status。
- 低置信度或样本不足有明确提示。

---

### [ ] UI-V3-013 P0 Regime-aware Rule Selection View

任务目标：展示盘前策略运行时为什么选择或跳过某些 rule。

主任务关联：

- `NW-V3-SX-004 Regime-aware Rule Selection`
- `UI-V2-006 Strategy Workspace`

允许修改：

- `web/src/pages/strategy/RegimeRuleSelectionPage.*`
- `web/src/components/strategy/*`
- `web/src/api/rules.ts`
- `web/src/api/market.ts`

禁止修改：

- 不在前端选择 rule。
- 不隐藏 blocked rule。
- 不允许无审计 override。

验收标准：

- 用户可以看到 selected_rules / skipped_rules / blocked_rules。
- 每条 rule 都有 selection_reason。
- override 有 operator / reason / timestamp / risk level。
- 可以回溯到 market_regime 和 applicability profile version。

---

## 4. UI Review Checklist

每个 UI PR 或 AI 任务完成后必须检查：

```text
[ ] 是否只实现指定 UI Task ID？
[ ] 是否检查了主 TaskList 对应任务？
[ ] 是否使用统一 API Client？
[ ] 是否处理 loading / empty / error / permission denied？
[ ] 是否避免展示 secret？
[ ] 是否避免展示服务器绝对路径？
[ ] 是否没有在页面写业务逻辑？
[ ] 表单 schema 是否来自后端或明确的 PipelineSpec？
[ ] 高风险操作是否有确认？
[ ] Job 状态是否以后端为准？
[ ] 是否有测试或人工验收说明？
```
