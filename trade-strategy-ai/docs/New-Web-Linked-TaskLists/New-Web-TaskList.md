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

### 0.2 单一入口与退役原则

本项目的路由、API、契约和页面入口必须遵循统一原则：

1. **单一 canonical。**
   - 对外只保留一套正式入口、一套正式契约、一套正式导航。
   - 新功能、新文档、新验收只引用 canonical，不再新增并行正式入口。
2. **显式兼容层。**
   - 旧入口只能作为兼容层、适配层或过渡壳存在。
   - 兼容层必须集中管理，不能散落到多个模块中。
3. **明确退役计划。**
   - 每个兼容入口都必须标记允许存在阶段和退役阶段。
   - 到达退役阶段后，必须从正式导航、正式文档和默认跳转中移除。
4. **禁止入口膨胀。**
   - 不允许 canonical 和 legacy 并行承载新功能。
   - 不允许把兼容层当成第二个正式入口继续演进。

### 0.3 为什么 UI 不能单独执行

UI 如果最后单独执行，会导致：

- 页面依赖的 API / Contract 不稳定。
- 前端表单 schema 和后端 JobDefinition 分叉。
- Job Detail、Artifact、Config Snapshot 展示口径不一致。
- AI 实现时容易漏掉 loading / empty / error / permission denied 状态。
- Web UI 继续变成临时堆叠，而不是可交付产品入口。

因此，UI 任务必须作为每个版本的验收条件之一。

### 0.4 执行规则

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

### 0.5 任务状态规则

- `[ ]` 未开始
- `[-]` 进行中
- `[x]` 已完成
- `[!]` 阻塞
- `[~]` 已拆出到未来优化，不阻塞第一版交付

### 0.6 优先级规则

- `P0` > `P1` > `P2`...

### 0.7 完成规则

任务只能在同时满足以下条件后标记为 `[x]`：

1. 达到验收标准。
2. UI 关联任务已经处理或标记。
3. 输出文档已经生成，相关文档已经更新。
4. 相关代码和文档已经提交，并通过代码审查。

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

## 5. 新增市场数据与 Regime-aware Rule 需求编排

本节用于承接新增用户需求，避免后续 AI 实现时把市场数据扩展、数据库化和分市场状态回测做成临时补丁。

新增需求：

1. 当前生成的 Market Snapshot 市场数据太少，需要扩展 snapshot 数据覆盖。
2. 当前市场数据主要写入文件，需要引入数据库作为主查询源，后续 Web 端可查询，也便于接入其他系统。
3. 市场状态会变化，不同时期适用的 rule 可能不同；如果只做整体回测，可能把特定时期表现优秀的 rule 错误淘汰，需要支持 Regime-aware Backtest 和 Rule Applicability Profile。

编排原则：

```text
V1：
- 不实现完整 Market Data DB。
- 不实现 Regime-aware Backtest。
- 但 Runtime Contract / Artifact Contract 必须预留 DatasetRef / SnapshotRef / StorageRef。
- 后续任何 API/UI 都不得依赖服务器绝对文件路径作为长期事实源。

V2：
- 在 Market Data 纵向切片中正式扩展 Market Snapshot 数据覆盖。
- 在 Market Data 纵向切片中引入数据库主存储。
- 提供 Market Snapshot Query API。
- 为 V3 生成 market_regime_features，但不在 V2 里完成 rule 优化闭环。

V3：
- 在 Backtest / Rule Pool / Optimization 阶段实现市场状态定义、分市场状态回测、rule 适用性画像和按当前市场状态选择 rule。
```

执行约束：

- 新增市场数据能力必须通过 Step / Workflow / PipelineSpec / Artifact / Profile / UI 统一体系进入项目。
- 文件可以保留为导出、调试、归档或备份，但不能继续作为 Web 查询和策略/回测的唯一事实源。
- Strategy / Backtest 后续必须通过 `snapshot_id` / `dataset_id` 引用市场数据。
- Regime-aware rule 相关任务不得提前塞入 V1；V2 只准备数据，V3 才做回测和 rule selection。


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

### [x] NW-V1-S0-001 P0 当前实现审计

任务目标：确认当前 Demo 中哪些能力可复用、哪些是临时实现、哪些存在重复事实源。

当前相关文件：

- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/job_service.py`
- `api/routers/ui/jobs.py`
- `web/src/`
- `docs/bak/WebUserManual.md`

输出：

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

完成情况：

- 已完成。
- 已输出审计文档：[docs/New-Web-Current-State-Audit.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/New-Web-Current-State-Audit.md)
- 审计结论已用于后续任务分解，当前不再补充业务代码。
- 关联 UI 任务中，`UI-V1-003` 已完成，`UI-V1-001` 仍待处理。

---

### [x] NW-V1-S0-002 P0 建立迁移矩阵

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

完成情况：

- 已完成迁移矩阵。
- 已输出迁移矩阵文档：[docs/New-Web-Migration-Matrix.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/New-Web-Migration-Matrix.md)
- 已覆盖现有 JobDefinition、WorkflowDefinition、CLI 入口和现有 UI Job / Workflow 事实源。
- 已补齐并复核 `cli/migrate.py` 的 `upgrade/downgrade` 映射口径。
- 关联 UI 任务中，`UI-V1-001`、`UI-V1-004`、`UI-V1-005` 现已完成，迁移矩阵的 UI 侧约束已被后续任务补齐。

---

### [x] NW-V1-S0-003 P0 定义 V1 验收清单

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

完成情况：

- 已完成 V1 验收清单定义。
- 已输出验收文档：[docs/New-Web-V1-Acceptance.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/New-Web-V1-Acceptance.md)
- 已明确 V1 仅覆盖 article_pipeline、Job Center、Step Timeline、Artifact、Config Snapshot、权限、失败/重试/取消/空数据、人工验收路径和 E2E 命令。
- 已将各验收项映射到主 Task ID 与 UI Task ID，且未把 V2/V3 能力列为 V1 阻断项。
- 关联 UI 任务 `UI-V1-011` 仍作为后续测试与人工验收任务保留，当前不强制转完成状态。

---

## Stage V1-S1：Runtime Contract 与兼容桥

### [x] NW-V1-S1-001 P0 设计并落地 Runtime Contract

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
- `DatasetRef`
- `SnapshotRef`
- `StorageRef`
- `ConfigSnapshotRef`
- `WorkflowRunContext`

验收标准：

- 支持序列化/反序列化。
- StepError 能区分用户错误、系统错误、外部依赖错误、权限错误、取消。
- ArtifactRef 不暴露服务器绝对路径。
- DatasetRef / SnapshotRef 只暴露 logical id，不暴露服务器绝对路径。
- StorageRef 能表达 file/db/external 三类来源，但业务层不得直接依赖具体存储实现。
- Runtime Contract 支持未来 market snapshot 从文件迁移到数据库时不改变 Web UI contract。
- 测试覆盖必填字段、可选字段、错误类型。

UI 关联任务：

- `UI-V1-005 Job Detail 页面`
- `UI-V1-006 Step Timeline Component`
- `UI-V1-008 Artifact Panel`
- `UI-V1-009 Config Snapshot Readonly Panel`

完成情况：

- 已新增 `src/services/runtime_contracts.py`，用统一 contract 模型定义 `RunContext`、`UserContext`、`StepInput`、`StepResult`、`StepError`、`ArtifactRef`、`DatasetRef`、`SnapshotRef`、`StorageRef`、`ConfigSnapshotRef`、`WorkflowRunContext`。
- 已实现 JSON 兼容 `to_dict` / `from_dict`，支持嵌套序列化与反序列化。
- 已补充错误分类 `StepErrorType`，覆盖用户错误、系统错误、外部依赖错误、权限错误和取消。
- 已通过单测验证 contract round-trip 和绝对路径约束，`StorageRef.relative_path` 不允许保存服务器绝对路径。

---

### [x] NW-V1-S1-002 P0 实现 Config Snapshot MVP

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

边界说明：

- 只做“运行时配置快照摘要”，不扩展成第二套 Profile/编辑系统。
- 只允许由 `JobService` 挂接和暴露摘要，不把配置解析逻辑继续散落到其他服务。
- `config_snapshot` 只用于 Job 回溯和 Web 展示，不作为业务执行的事实源。

验收标准：

- 创建 Job 后可以查询到配置快照摘要。
- 敏感字段不出现在 API、日志、Artifact。
- 现有 job 仍可通过 `config_path` 运行。

UI 关联任务：

- `UI-V1-009 Config Snapshot Readonly Panel`
- `UI-V1-005 Job Detail 页面`

完成情况：

- 已新增 `src/services/config_snapshot_service.py`，负责读取配置、生成稳定 `config_hash`、返回脱敏 `masked_snapshot`、记录 `config_source`，并把快照摘要落盘。
- 已扩展 `JobService`，在 `params.config_path` 存在时自动捕获配置快照，`create_job` / `get_job` / 列表返回都能看到 `config_snapshot` 与 `config_snapshot_path`。
- 已补充单测，覆盖快照生成、缺失配置报错、Job 创建后可查询快照摘要、以及 `config_path` 缺失时的结构化错误。
- 已验证敏感字段不会以原文进入快照摘要输出，且测试生成的快照文件已清理。

---

### [x] NW-V1-S1-003 P0 实现 Artifact Contract 与 ArtifactService MVP

任务目标：建立统一产物元数据，支撑 Web 解释和下载产物。

允许修改：

- `src/services/artifact_contracts.py`
- `src/services/artifact_service.py`
- `src/services/job_service.py`
- `tests/services/test_artifact_service.py`

边界说明：

- 只定义产物元数据、查询与下载契约，不在本任务中建设 Artifact Center 页面或跨 Job 搜索能力。
- 不把产物契约扩展成文件系统浏览器，也不让前端直接读取服务器路径。
- 只允许通过 `JobService`/`ArtifactService` 暴露可解释元数据，不新增第二套产物事实源。

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
- dataset_ref，可选
- snapshot_ref，可选
- storage_ref，可选

验收标准：

- Job Detail 可以按 Step 展示产物。
- 缺失产物返回结构化错误。
- 产物下载不暴露服务器路径。
- snapshot / dataset / market-data 类型 artifact 可以通过 snapshot_id / dataset_id 回溯到对应数据集。
- 文件导出只能作为 artifact download，不作为 Web 查询的唯一数据源。

UI 关联任务：

- `UI-V1-008 Artifact Panel`
- `UI-V1-005 Job Detail 页面`
- `UI-V2-007 Artifact Center`

完成情况：

- 已新增 `src/services/artifact_contracts.py`，把产物目录项和产物详情收敛为统一契约，包含 `artifact_id`、`title`、`safe_download_url`、`storage_ref` 等解释性元数据。
- 已收紧 `ArtifactService`，列表与详情对外不再暴露服务器绝对路径，下载入口改为通过 `artifact_id` 内部解析文件路径。
- 已将 `JobService.bind_artifact` 升级为单一契约形状，支持 `workflow_id`、`step_id`、`title`、`summary`，并避免对外输出裸路径。
- 已补充单测与路由测试，确认列表、详情、下载与 Job 绑定都通过同一契约链路运行，且 `git diff --check` / 相关 pytest 均通过。

---

### [x] NW-V1-S1-004 P0 建立 Job/Workflow Runtime Bridge

任务目标：把现有 `JobDefinition` / `WorkflowDefinition` 桥接到 Runtime Contract，避免重复事实源。

终态要求：最终只保留一套 Runtime Contract 形状作为正式对外解释层，现有 Registry 只能作为兼容读源和迁移过渡层存在，不能形成双轨实现。

允许修改：

- `src/services/runtime_registry_bridge.py`
- `tests/services/test_runtime_registry_bridge.py`

边界说明：

- 只做 `JobDefinition` / `WorkflowDefinition` 到 Runtime Contract 的映射，不新增第二套定义或注册入口。
- bridge 必须是单向读取层，只允许从现有 Registry 读取并映射到 canonical contract。
- 不在 bridge 里补业务逻辑、执行逻辑或 UI 适配逻辑。
- 不把映射结果作为新的事实源，bridge 只负责兼容和过渡。

禁止修改：

- 不新增第二套 JobDefinition。
- 不新增 WebJobDefinition。
- 不长期复制 WorkflowDefinition。
- 不删除现有 Registry。
- 不允许 bridge 和旧 Registry 长期并行演进成双轨。

必须一次到位：

1. 将 JobDefinition 映射为 Job Contract。
2. 将 WorkflowDefinition 映射为 Workflow Contract。
3. 保留 permission、risk、param_schema、runnable、requires_confirmation。
4. 明确不可映射字段并写入审计文档。
5. 新增 Job / Workflow 仍只有一个登记入口。
6. bridge 输出必须足够稳定，后续 UI / Job / Workflow 只能依赖 canonical contract，不再依赖原始 registry 结构。

允许作为过渡：

1. 保留现有 `JobDefinition` / `WorkflowDefinition` 的原始实现。
2. 保留 Registry 的读取接口，作为兼容读源。
3. 允许 bridge 暂时保留少量 legacy 字段到 `metadata`，但不得形成第二套正式字段体系。

验收标准：

- 所有现有 Job 类型可通过 bridge 读取。
- 所有现有 Workflow 可通过 bridge 读取。
- 测试覆盖字段映射。
- 验收时必须确认没有新增第二套事实源，也没有出现第二个正式注册入口。

UI 关联任务：

- `UI-V1-007 Schema-driven Workflow Run Form`
- `UI-V1-006 Step Timeline Component`

完成情况：

- 已新增 `src/services/runtime_registry_bridge.py`，把现有 `JobDefinition` / `WorkflowDefinition` 归一化为 canonical contract 输出，top-level 不再暴露 `service_name` / `handler_name` / `job_definition` 这类 registry 私有结构。
- 已明确 bridge 只做单向读取与映射，现有 Registry 仍作为兼容读源保留，不新增第二套正式入口，也不把映射结果升级为新事实源。
- 已补充 `tests/unit/services/test_runtime_registry_bridge.py`，覆盖 Job / Workflow 两条映射链路，并验证 canonical 字段与 metadata 兼容字段的边界。
- 已通过 `python -m pytest tests/unit/services/test_job_registry.py tests/unit/services/test_workflow_service.py tests/unit/services/test_runtime_registry_bridge.py -q`，`11 passed`。
- 已通过 `git diff --check`。

---

## Stage V1-S2：Job/Workflow/Step 执行底座

### [x] NW-V1-S2-001 P0 实现 Step Registry

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

完成说明：

- 新增 `src/services/step_registry.py`，以 `name + version` 作为稳定键实现显式注册表。
- 新增 `tests/services/test_step_registry.py`，覆盖注册、查询、重复注册、未注册和输入校验。
- 保持 registry 为进程内 canonical 定义入口，不引入动态插件系统或自动发现机制。

---

### [x] NW-V1-S2-002 P0 实现 Step Timeline

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

完成情况：

- 新增 `src/models/step_timeline.py`，定义 Job Timeline contract 与 step item 结构。
- 新增 `src/services/step_timeline_service.py`，把 Job audit events 归一化为结构化 Step Timeline。
- `JobService` 新增 `get_job_timeline`，`/api/ui/v1/jobs/{job_id}/timeline` 现在返回结构化 contract。
- 补齐 unit / API / models / OpenAPI 回归并通过验证，确认成功、失败、取消与运行中场景可见。

---

### [x] NW-V1-S2-003 P0 实现 Workflow Runner MVP

任务目标：让 Workflow 从 UI 展示定义升级为可执行编排，但 V1 只要求支持 article_pipeline 需要的最小能力。

允许修改：

- `src/services/workflow_runner.py`
- `src/services/workflow_service.py`
- `tests/unit/services/test_workflow_runner.py`

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

完成情况：

- 已新增 [`src/services/workflow_runner.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/services/workflow_runner.py)，以薄编排器方式顺序执行 Workflow steps，并复用 `JobRunner` 处理单个 Job。
- 已调整 [`src/services/workflow_service.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/services/workflow_service.py)，保留 Workflow 定义与参数校验，运行入口改为委托 `WorkflowRunner`。
- 已补齐 [`tests/unit/services/test_workflow_runner.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/tests/unit/services/test_workflow_runner.py) 与 [`tests/unit/services/test_workflow_service.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/tests/unit/services/test_workflow_service.py)，覆盖顺序执行、失败停止和服务层委托。
- 已通过 [`tests/api/routers/test_workflows.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/tests/api/routers/test_workflows.py)、[`tests/api/routers/test_pipelines.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/tests/api/test_ui_openapi_contract.py) 与 article pipeline spec 回归，确认 UI/API contract 未回退。

---

## Stage V1-S3：article_pipeline 纵向切片

### [x] NW-V1-S3-001 P0 定义 article_pipeline PipelineSpec

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

完成情况：

- 已新增单一 canonical 文件 [src/pipelines/article_pipeline_spec.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/pipelines/article_pipeline_spec.py)，以 frozen dataclass 定义 `article_pipeline` 的稳定核心字段与扩展位。
- 已明确 `pipeline_id`、`workflow_id`、`required_profile_sections`、`input_schema`、`output_artifacts`、`job_types`、`steps`、`user_visible_success_criteria`、`ui_page`、`ui_task_ids`，并保留 `extensions` 作为后续 `NW-V1-S3-002/003` 的显式扩展槽位。
- 已通过 [src/services/runtime_registry_bridge.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/src/services/runtime_registry_bridge.py) 暴露 `list_pipeline_contracts()` / `get_pipeline_contract()`，让 catalog 层读取同一份规范。
- 已补充 [tests/pipelines/test_article_pipeline_spec.py](/Users/wanghui/Documents/Claude/trade-strategy-ai/tests/pipelines/test_article_pipeline_spec.py) 与 bridge 单测；`pytest tests/pipelines/test_article_pipeline_spec.py tests/unit/services/test_runtime_registry_bridge.py -v` 通过。

---

### [x] NW-V1-S3-002 P0 接入现有 crawl / pipeline-run / pipeline-step

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

### [x] NW-V1-S3-003 P0 article_pipeline API

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

完成情况：

- 已新增 [`src/services/pipeline_application_service.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/services/pipeline_application_service.py)，作为 `article_pipeline` 的专用应用服务，直接消费 `article_pipeline_spec` 并把执行委托给 `WorkflowRunner`。
- `article_pipeline` 现在是 `/api/ui/v1/pipelines` 的唯一 canonical 入口，路由不再依赖 `WorkflowService` 的 legacy `pipeline` workflow。
- `JobService`、`WorkflowRunner`、`JobRunner` 继续负责 config snapshot、Job 生命周期、Step Timeline、Artifact 绑定和现有 pipeline 能力。
- 已补充 [`tests/unit/services/test_pipeline_application_service.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/tests/unit/services/test_pipeline_application_service.py) 与 [`tests/api/routers/test_pipelines.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/tests/api/routers/test_pipelines.py)，覆盖列表、详情、运行和 unknown pipeline 边界。
- 已通过 pipeline application service、pipeline router、workflow service、workflow router、OpenAPI contract 与 article pipeline spec 回归，确认 canonical 入口与兼容层边界未回退。

---

## Stage V1-S4：V1 产品化收口

### [x] NW-V1-S4-001 P0 V1 E2E 回归

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

完成情况：

- 新增 `tests/e2e/e2e_runner.py` 作为共享 E2E 编排层，统一封装 `web-acceptance` 与 `cli.main e2e-regression` 的调用。
- 新增 `tests/e2e/test_article_pipeline_v1.py`，将 V1 回归收束为“CLI smoke gate + Web acceptance”的薄编排；其中真实 CLI 回归默认需要显式启用 `RUN_V1_E2E=1`，避免把产品交付路径重新绑定到 CLI。
- `web/src/e2e/web-acceptance.test.tsx` 已对齐当前 UI 文案、Job Detail 路由、Workflow submit 后跳转、Artifact / Report / Settings 文案。
- 补齐了 `reports` 相关单测文案，使 `报告中心` 与实际页面一致。
- 运行 `pytest tests/e2e/test_e2e_runner.py tests/e2e/test_web_acceptance.py tests/e2e/test_article_pipeline_v1.py -q` 通过，`test_article_pipeline_v1` 默认以 skip 方式保留真实 CLI gate，避免在没有本地 PostgreSQL 的环境里误判失败。
- 新增 `docs/New-Web-V1-E2E.md` 记录本地验收、失败定位和 CLI smoke 的显式启用方式。

---

### [x] NW-V1-S4-002 P0 V1 用户文档与验收说明

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

完成情况：

- 新增 [docs/New-Web-V1-UserManual.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/New-Web-V1-UserManual.md)，以真实用户视角说明如何通过 Web 完成 `article_pipeline`，并明确任务详情、产物、报告和配置快照的查看路径。
- 新增 [docs/New-Web-V1-Release-Checklist.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/New-Web-V1-Release-Checklist.md)，以内部发布清单形式收口 V1 自动化检查、手工验收、页面名称一致性和发布判定。
- 文档中的页面名、按钮名和主路径已对齐当前 UI：`任务`、`任务详情`、`引导式操作`、`产物中心`、`报告中心`、`配置中心`。
- 文档明确 V1 的范围边界与 V2/V3 留白，避免把独立 Artifact Center、正式 Profile 工作台和更复杂的 workflow 管理误写成 V1 前置条件。

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

### [x] NW-V2-S1-001 P0 定义 Profile 最终模型

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

完成情况：

- 后端 Profile 模型、服务、迁移和 Job ProfileSnapshot 已实现。
- 相关单测已通过。
- UI-V2-002 与 UI-V2-003 已收口，Profile 查看、导入、编辑、校验、保存新版本和归档链路已完整打通。

---

### [x] NW-V2-S1-002 P0 实现 config_path 到 Profile 的迁移工具

任务目标：让现有配置可迁移到正式 Profile，而不是长期依赖 config_path。

输出：

- `src/services/config_migration_service.py`
- 内部迁移脚本
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

完成情况：

- 已提供 `ConfigMigrationService` 和内部迁移脚本。
- 已支持 masked preview、缺失项校验和 Profile 保存。
- 已保留 `config_path` 兼容入口，并把迁移说明收口为独立文档。

---

## Stage V2-S2：Market Data 纵向切片

### [x] NW-V2-S2-001 P0 定义 market_data PipelineSpec

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

规范说明：

- 参见 `docs/New-Web-Market-PipelineSpec.md`

完成情况：

- 已定义 market_data canonical `PipelineSpec`。
- 已补齐权限与错误分类定义，供后续 market 工作台直接消费。
- 已明确 UI 页面与 UI Task ID 绑定关系。

---

### [x] NW-V2-S2-002 P0 实现 Market Data Workflow

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

完成情况：

- 已将 market data 接入 `WorkflowRunner` 和 `Job Center`。
- 已支持 Kaipan 抓取/归一化、OHLCV 抓取、market state 与 snapshot 构建。
- 已在 Job Detail 侧可回溯 market artifacts，并回传 provider / config / data / system 错误分类。

---

### [x] NW-V2-S2-003 P0 扩展 Market Snapshot 数据覆盖

任务目标：扩展当前 `snapshot-build` 的市场数据覆盖范围，解决 Market Snapshot 数据过少的问题，并为盘前策略、盘后归因、回测和 Regime-aware Rule Selection 提供统一市场上下文。

当前相关文件：

- `src/pipelines/*market*`
- `src/services/*market*`
- `src/services/*provider*`
- `src/services/artifact_service.py`
- `src/services/job_service.py`
- `api/routers/ui/*`
- 现有 `snapshot-build` / `market-state-build` 相关实现

允许修改：

- `src/pipelines/market_data_pipeline_spec.py`
- `src/services/market_snapshot_service.py`
- `src/services/market_data_service.py`
- `src/services/provider/*`
- `tests/services/test_market_snapshot_service.py`
- `tests/pipelines/test_market_data_pipeline_spec.py`
- `docs/New-Web-Market-Snapshot-Schema.md`

禁止修改：

- 不在 Web Router 中直接调用 provider。
- 不让 Web UI 直接读取本地市场数据文件。
- 不把 provider 私有字段直接暴露给 UI。
- 不把 `snapshot-build` 写成只服务某一个策略的临时逻辑。
- 不在本任务中实现完整回测或 rule 选择逻辑。

实现要求：

1. 定义 MarketSnapshot schema，至少包含：
   - `snapshot_id`
   - `trade_date`
   - `market`
   - `data_version`
   - `provider_sources`
   - `created_at`
   - `data_quality`
   - `sections`
2. Snapshot sections 至少预留并按可用 provider 逐步实现：
   - ✅ `indices`：指数数据（由 `overview` 覆盖）
   - ✅ `sectors`：板块/行业数据（由 `sector_activity` 覆盖）
   - ✅ `ohlcv`：个股日线数据
   - ✅ `topics`：热点/题材（由 `hot_topics` 覆盖）
   - ✅ `topic_constituents`：题材成分股
   - ✅ `auction`：竞价数据
   - ✅ `limit_up_down`：涨停/跌停数据
   - `dragon_tiger`：龙虎榜
   - `liquidity`：成交额/量能
   - `breadth`：市场广度
   - ✅ `sentiment`：情绪指标（由 `overview` 覆盖）
   - ✅ `strong_symbols`：强势股候选池
   - `event_data`：盘后解释需要的事件型数据
3. 每个 section 必须记录：
   - provider
   - source_time
   - record_count
   - missing_reason
   - quality_status
4. `snapshot-build` 成功后必须输出：
   - `snapshot_id`
   - snapshot summary artifact
   - data quality report artifact
5. `market_data PipelineSpec` 必须声明 `snapshot-build` 的输入、输出 artifact 和 UI Task ID。
6. 缺少某类市场数据时，不得直接失败整个 `snapshot-build`，除非该 section 被标记为 required。
7. 失败原因必须结构化，区分：
   - provider unavailable
   - config missing
   - data empty
   - data invalid
   - partial snapshot
   - system error

验收标准：

- 可以为指定 `trade_date` 生成 Market Snapshot。
- Snapshot 至少包含 indices / ohlcv / topics，或明确标记缺失原因。
- 每个 section 有 record_count 和 quality_status。
- Job Detail 能看到 snapshot summary artifact。
- Snapshot artifact 不暴露服务器绝对路径。
- 缺失数据有结构化错误或 warning。
- 后续 Strategy Run / Backtest 可以通过 `snapshot_id` 引用该 snapshot。

UI 关联任务：

- `UI-V2-005 Market Data Workspace`
- `UI-V2-010 Market Snapshot Browser`
- `UI-V2-007 Artifact Center`

完成情况：

- 已新增结构化 `MarketSnapshot` schema、section registry 和首批 section builders。
- 已实现首批 section：`overview`、`limit_up_down`、`sector_activity`、`auction`、`ohlcv`、`hot_topics`、`topic_constituents`、`strong_symbols`、`market_state`。
- 已保留旧 `snapshot_service` 兼容层，不新增产品级 CLI 入口。
- 已输出 `snapshot.json`、`snapshot.summary.json`、`snapshot.quality.json` 三类产物，并接入 Job artifact 绑定。
- 已补齐 `market_data PipelineSpec` 的新 artifact 声明。
- 已通过定向回归测试和 legacy 兼容测试。

第一批 snapshot sections 数据源映射：

| Section | 主要来源 | 说明 |
|---|---|---|
| `overview` | `ChangeStatistics` / `MarketCapacity` / `GetZsReal`（或 `RefreshStockList`） | 覆盖情绪、容量和指数概览 |
| `limit_up_down` | `MarketStockZDNum` / `DailyLimitIndex` / `ZhangTingExpression` / `fetch_limit_up_info` / `fetch_limit_up_reason` / `DailyLimitPerformance2` / `GetPMSL_PMLD` / `fetch_lhb_list` | 覆盖涨停、跌停、破板、亮点与龙虎榜 |
| `sector_activity` | `RealRankingInfo` / `ZhiShuRanking` / `WeightPerformance` / `GetBKJJ_W36` / `GetBKJJBL` | 覆盖板块、行业、地区、权重和竞价 |
| `auction` | `MorningBidding` / `MorningBiddingNum` / `MorningBiddingList` / `GetWPQC` | 覆盖盘前竞价和尾盘竞价 |
| `ohlcv` | `MarketService.get_ohlcv` + `MarketDataCache` fallback | 覆盖个股日线行情 |
| `hot_topics` | 现有 `market_universe` 热题材链路 | 覆盖热点/题材 |
| `topic_constituents` | 现有 `market_universe` 题材成分链路 | 覆盖题材成分股 |
| `strong_symbols` | 现有 `market_universe` 强势标的筛选链路 | 覆盖强势股候选池 |
| `market_state` | `PersonaService.build_market_state` | 覆盖市场状态上下文 |

UI 操作方式：

- 当前用户在 `快照中心` 页面提交抓取任务，填写开始日期、结束日期、时间插槽、快照类型、是否强制、是否离线后，点击 `构建快照`。
- 页面不会逐个 section 勾选；`snapshot-build` 会按 registry 统一构建已注册的 sections。
- `Kaipan` 页面负责原始市场数据的 `Fetch / Normalize / Run`，可选 `trade_date` 和 `slot`，适合先抓原始数据再由 `snapshot-build` 聚合。
- 构建完成后，用户在 `快照中心` 里查看快照列表和详情，或跳转到 Job Detail / Artifact Center 查看摘要和质量报告。

---

### [x] NW-V2-S2-004 P0 Market Data DB Storage

任务目标：把市场数据从“文件为主的事实源”迁移为“数据库为主的查询源”，文件只保留为导出、调试、归档或备份产物，支撑 Web 查询和外部系统接入。

当前相关文件：

- `src/services/market_data_service.py`
- `src/services/market_snapshot_service.py`
- `src/services/artifact_service.py`
- `src/db/*`
- migration 相关目录
- 当前 market data 文件读写逻辑

允许修改：

- `src/models/market_data.py`
- `src/repositories/market_data_repository.py`
- `src/repositories/market_snapshot_repository.py`
- `src/services/market_data_storage_service.py`
- migration 文件
- tests
- `docs/New-Web-Market-Data-Storage.md`

禁止修改：

- 不一次性删除现有文件导出能力。
- 不让业务代码直接拼 SQL。
- 不让 Web UI 查询本地文件路径。
- 不把 provider 原始响应不清洗直接落为主表事实源。
- 不破坏现有 CLI dev/debug 读取旧文件的兼容入口。

实现要求：

1. 建立 Market Data DB 存储模型，至少支持：
   - `market_snapshots`
   - `market_snapshot_sections`
   - `market_snapshot_items`
   - `market_datasets`
   - `market_data_quality_reports`
2. 根据现有数据库方案选择实现方式；如果项目尚未统一 ORM，需要在本任务中先记录采用方案，不得引入第二套 DB 访问事实源。
3. 建立 Repository 层：
   - `MarketSnapshotRepository`
   - `MarketDatasetRepository`
   - `MarketDataQualityRepository`
4. 写入路径：
   - provider fetch
   - normalize
   - build snapshot
   - save DB
   - generate artifact metadata
5. 查询路径：
   - by `snapshot_id`
   - by `trade_date`
   - by `symbol`
   - by `section`
   - by `dataset_id`
6. Artifact 中只能保存 `snapshot_id` / `dataset_id` / `storage_ref`，不得保存 UI 可见的服务器绝对路径。
7. 旧文件读写能力保留为兼容层，并在文档中写清退出条件。
8. 支持最小 migration / seed / rollback 说明。

验收标准：

- `snapshot-build` 可以把 market snapshot 写入 DB。
- 可以通过 repository 按 `trade_date` 查询 snapshot。
- 可以通过 repository 按 `snapshot_id` 查询 sections 和 items。
- Artifact Center 可以通过 artifact metadata 回溯到 snapshot_id。
- 文件导出仍可作为 artifact download 使用。
- Web/API 不依赖服务器绝对路径。
- 测试覆盖 DB 写入、查询、空数据、重复写入、质量报告。

UI 关联任务：

- `UI-V2-010 Market Snapshot Browser`
- `UI-V2-011 Market Dataset Viewer`
- `UI-V2-007 Artifact Center`

完成情况：

- 已建立 `market_snapshots`、`market_snapshot_sections`、`market_snapshot_items`、`market_datasets`、`market_data_quality_reports` 五张表的 ORM 模型与 Alembic migration。
- 已实现 `MarketSnapshotRepository`、`MarketSnapshotSectionRepository`、`MarketSnapshotItemRepository`、`MarketDatasetRepository`、`MarketDataQualityRepository`。
- 已实现 `MarketDataStorageService`，并将 `snapshot-build` 的真实编排链路接入 DB 持久化。
- 已在 `SnapshotService -> MarketSnapshotService` 真实路径中默认启用 DB storage，保持文件导出兼容层不变。
- 已补齐模型、repository、storage service 与编排回归测试。
- 已补充 [New-Web-Market-Data-Storage.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/New-Web-Market-Data-Storage.md) 说明文档。

---

### [ ] NW-V2-S2-004-2 P0 Workflow Run DB Storage

任务目标：把 Workflow 的运行实例从“服务层返回结果”升级为“数据库级事实源”，支持运行追踪、恢复、审计和历史查询。该子任务只作为后续收口，不在当前 V2-S2 第一版里强制落地。

建议表结构：

- `workflow_runs`
  - `id`
  - `workflow_id`
  - `workflow_title`
  - `workflow_version`
  - `status`
  - `trigger_source`
  - `created_by`
  - `confirmed`
  - `idempotency_key`
  - `started_at`
  - `finished_at`
  - `duration_ms`
  - `input_params_json`
  - `output_summary_json`
  - `error_json`
  - `metadata_json`
  - `created_at`
  - `updated_at`
- `workflow_run_steps`
  - `id`
  - `workflow_run_id`
  - `step_id`
  - `step_name`
  - `step_order`
  - `job_id`
  - `job_type`
  - `status`
  - `started_at`
  - `finished_at`
  - `duration_ms`
  - `input_json`
  - `output_json`
  - `error_json`
  - `artifact_refs_json`
  - `metadata_json`
  - `created_at`
  - `updated_at`

字段要求：

- `workflow_runs` 作为一次 workflow 运行的主记录，必须可按 `workflow_id`、`status`、`created_by`、`created_at` 查询。
- `workflow_run_steps` 作为 step 级明细，必须保留 step 顺序、对应 Job、输入、输出、错误和产物引用。
- `input_params_json` 和 `output_summary_json` 只保存 JSON 兼容结构，不保存服务器绝对路径。
- `error_json` 必须结构化，至少保留 `type`、`message`、`detail`、`metadata`。
- `artifact_refs_json` 只能保存可回溯的逻辑引用，不暴露本地文件系统绝对路径。

验收标准：

- 可以按 `workflow_id` 和时间范围查询 workflow runs。
- 可以按 `workflow_run_id` 拉取完整 step 明细。
- workflow 中断后可以保留失败现场，便于恢复或人工审计。
- UI 不需要再依赖 job audit events 拼装 workflow 历史。
- 与现有 `Step Timeline` contract 能互相映射，但不重复造两套 UI 语义。
- 新增持久化表、Repository、Service 和测试后，不破坏现有 `WorkflowRunner` 的运行链路。

---

### [x] NW-V2-S2-005 P0 Market Snapshot Query API

任务目标：提供稳定 API 给 Web UI 和外部系统查询 Market Snapshot / Dataset，避免直接读取文件或绕过 Application Service。

当前相关文件：

- `api/routers/ui/*`
- `src/services/market_snapshot_service.py`
- `src/repositories/market_snapshot_repository.py`
- API schema 文件
- tests

允许修改：

- `api/routers/ui/market.py`
- `api/schemas/market.py`
- `src/services/market_snapshot_query_service.py`
- tests
- `docs/New-Web-Market-Snapshot-API.md`

禁止修改：

- 不让 API 直接调用 provider。
- 不让 API 返回服务器绝对路径。
- 不在 API Router 中拼接复杂业务查询。
- 不绕过权限和 Profile/Config 校验。
- 不返回 secret 或 provider 私有凭据。

API 至少包括：

```text
GET /api/ui/v1/market/snapshots
GET /api/ui/v1/market/snapshots/{snapshot_id}
GET /api/ui/v1/market/snapshots/{snapshot_id}/sections
GET /api/ui/v1/market/snapshots/{snapshot_id}/sections/{section}
GET /api/ui/v1/market/datasets
GET /api/ui/v1/market/datasets/{dataset_id}
GET /api/ui/v1/market/snapshots/{snapshot_id}/quality
```

查询能力：

- `trade_date`
- `market`
- `section`
- `symbol`
- `topic`
- `quality_status`
- pagination
- limit / offset 或 cursor

验收标准：

- Web 可以查询 snapshot 列表。
- Web 可以查看 snapshot detail。
- Web 可以查看每个 section 的 record_count / quality_status。
- 无数据、部分数据、权限不足、snapshot 不存在都有结构化错误。
- API response 不暴露服务器绝对路径。
- API 文档更新。
- 测试覆盖查询、空数据、权限不足、无效参数。

UI 关联任务：

- `UI-V2-010 Market Snapshot Browser`
- `UI-V2-011 Market Dataset Viewer`
- `UI-V2-005 Market Data Workspace`

完成情况：

- 已新增 `MarketSnapshotQueryService`，统一通过 repository 查询 DB 中的 snapshot / section / item / dataset / quality report。
- 已在 `api/routers/ui/market.py` 暴露 snapshot 列表、详情、sections、section detail、dataset 列表、dataset detail 和 quality report 端点。
- 已补齐结构化查询 schema、分页模型和错误契约，Router 不再拼复杂查询逻辑。
- 已补充 `docs/New-Web-Market-Snapshot-API.md` 说明文档与测试覆盖，且未新增 CLI surface。

---

### [ ] NW-V2-S2-006 P1 Market Regime Feature Build

任务目标：在 V2 阶段只生成市场状态特征，不做 rule 优化，为 V3 的 Regime-aware Backtest 和 Rule Applicability Profile 准备数据。

当前相关文件：

- `src/services/market_snapshot_service.py`
- `src/services/market_data_service.py`
- `src/pipelines/market_data_pipeline_spec.py`
- `src/services/artifact_service.py`
- tests

允许修改：

- `src/services/market_regime_feature_service.py`
- `src/models/market_regime.py`
- `tests/services/test_market_regime_feature_service.py`
- `docs/New-Web-Market-Regime-Features.md`

禁止修改：

- 不在本任务中决定某个 rule 是否启用。
- 不在本任务中做完整 backtest。
- 不把 regime 直接写死成不可扩展枚举。
- 不让特征计算依赖 Web UI。

实现要求：

1. 基于 Market Snapshot 生成 `market_regime_features`。
2. 特征至少预留：
   - trend
   - sentiment
   - liquidity
   - volatility
   - breadth
   - theme_strength
   - limit_up_count
   - limit_down_count
   - turnover_level
3. 每个特征记录：
   - value
   - source section
   - confidence
   - missing_reason
4. 输出 regime feature artifact。
5. 保存到 DB，后续可按 `trade_date` / `snapshot_id` 查询。

验收标准：

- 可以对指定 `snapshot_id` 生成 regime features。
- 缺失输入数据时返回 partial features 和 missing_reason。
- regime features 可被 API 或 repository 查询。
- V3 Backtest 可以通过 `snapshot_id` 读取这些 features。

UI 关联任务：

- `UI-V2-010 Market Snapshot Browser`
- `UI-V2-007 Artifact Center`

---

## Stage V2-S3：Strategy Run 纵向切片

### [x] NW-V2-S3-001 P0 定义 strategy PipelineSpec

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

完成情况：

- 已新增 [`src/pipelines/strategy_pipeline_spec.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/pipelines/strategy_pipeline_spec.py) 作为 strategy 的 canonical PipelineSpec，明确 `strategy-build`、`run-pre-market`、`run-after-close` 的输入、产物、UI 页面和 UI Task ID。
- 已将 strategy PipelineSpec 接入 [`src/pipelines/__init__.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/pipelines/__init__.py) 与 [`src/services/runtime_registry_bridge.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/src/services/runtime_registry_bridge.py)，保证 catalog / bridge 可以读取同一份规范。
- 已补充 [`docs/New-Web-Strategy-PipelineSpec.md`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/New-Web-Strategy-PipelineSpec.md) 说明文档与 [`tests/pipelines/test_strategy_pipeline_spec.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/tests/pipelines/test_strategy_pipeline_spec.py)、[`tests/unit/services/test_runtime_registry_bridge.py`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/tests/unit/services/test_runtime_registry_bridge.py) 回归测试。
- 已通过相关验证：`python -m pytest tests/pipelines/test_strategy_pipeline_spec.py tests/unit/services/test_runtime_registry_bridge.py tests/api/routers/test_pipelines.py tests/api/test_ui_openapi_contract.py -q`

---

### [x] NW-V2-S3-002 P0 实现 Strategy Workflow

验收标准：

- Web/API 可触发策略版本构建。
- Web/API 可触发盘前/盘后。
- Job Detail 可展示报告和证据包。
- Artifact Center 可检索策略产物。

UI 关联任务：

- `UI-V2-006 Strategy Workspace`
- `UI-V2-007 Artifact Center`
- `UI-V2-008 Web UI 错误恢复体验`

完成情况：

- 已打通 `strategy-build`、`run-pre-market`、`run-after-close` 的 Web/API 执行闭环。
- 已让 Job Detail 通过共享错误组件解释策略任务结果，并能展示策略相关产物。
- 已让 Artifact Center 支持策略产物检索与来源 Job 跳转。
- 已通过相关后端和前端回归测试。

---

## Stage V2-S4：正式 UI 与 CLI 降级

### [x] NW-V2-S4-001 P0 正式 Web 工作台收口

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

完成情况：

- 已将 Dashboard 快捷入口补齐为 `Profile / Market / Strategy / Jobs / Artifacts` 的正式入口集合。
- 已将 Dashboard 的总览失败态与告警失败态统一到共享 `ErrorState`，保持与其他 V2 页面一致的错误恢复语言。
- 已通过首页回归测试与 `git diff --check` 验证。

---

### [x] NW-V2-S4-002 P0 CLI 正式入口降级

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

完成情况：

- 已补齐 `dev` 调试命令组：`run-step`、`run-workflow`、`list-workflows`、`config-migrate`。
- 已将 README 的 CLI 说明收敛为 dev/debug 语义，明确正式用户路径在 Web 工作台。
- 已补充 CLI 入口测试，确认 `dev` 命令树暴露且现有 CLI 子命令未受影响。

---

### [ ] NW-V2-S4-003 P0 路由兼容层收口与旧入口退役

任务目标：在 V2 正式工作台收口阶段冻结 legacy 路由，避免旧入口继续扩张导致维护复杂度失控。

收口要求：同时检查是否在 V1/V2 期间引入了新的正式入口或新的事实源；如果发现双轨或分叉，必须先回收，不允许带病进入下一阶段。

允许修改：

- `docs/New-Web-UI-Routing.md`
- `web/src/app/router.tsx`
- `web/src/app/navigation.ts`
- `web/src/routes/*`

禁止修改：

- 不再新增 legacy 功能入口。
- 不把旧入口当作正式导航展示。
- 不允许 canonical 与 legacy 分叉演进。

实现要求：

1. 所有正式导航只指向 canonical 路由。
2. legacy 路由仅保留历史链接和过渡壳。
3. 文档明确每个 legacy 入口的退役阶段。
4. 兼容层不得再承载新业务。
5. 审计 current canonical / legacy 入口数量，确认没有新增第二套正式入口。
6. 审计 current fact source 数量，确认没有新增第二套 Job / Workflow / Artifact 事实源。

验收标准：

- V2 页面只对外展示 canonical 路由。
- legacy 入口不再出现在正式导航中。
- 路由文档、导航文档和验收文档一致。
- 兼容层退出条件清晰可查。
- 若审计发现新增正式入口或事实源，必须先补收口，不得继续扩张。

UI 关联任务：

- `UI-V2-001 正式 Web 信息架构`
- `UI-V2-004 Dashboard 首页`
- `UI-V2-008 Web UI 错误恢复体验`
- `UI-V1-001 Web UI 临时策略与路由规划`

完成情况：

- 计划项，尚未执行。
- 用于确保 V2 收口时不会继续膨胀 legacy 入口。

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

---

## Stage V3-S3A：Regime-aware Backtest 与 Rule 适用性优化

> 本 Stage 放置在 V3 的 Backtest / Rule Pool 相关任务之后、Strategy / Final Acceptance 之前。它不替代原有 V3 任务，只新增“市场状态变化导致 rule 适用性不同”的实现闭环。

### [ ] NW-V3-SX-001 P0 Market Regime Definition

任务目标：定义可解释、可版本化、可回测的 Market Regime，用于把不同市场阶段下的 rule 表现分开评估。

当前相关文件：

- `src/models/market_regime.py`
- `src/services/market_regime_feature_service.py`
- `src/services/market_snapshot_service.py`
- `src/backtest/*`
- tests

允许修改：

- `src/services/market_regime_service.py`
- `src/models/market_regime.py`
- `tests/services/test_market_regime_service.py`
- `docs/New-Web-Market-Regime-Definition.md`

禁止修改：

- 不用不可解释的黑盒标签作为唯一输出。
- 不把 regime 判断写死在 Web UI。
- 不让 Strategy 直接绕过 Market Snapshot 读取文件。
- 不在本任务中实现 rule 选择。

实现要求：

1. 定义 MarketRegime schema：
   - `regime_id`
   - `trade_date`
   - `snapshot_id`
   - `regime_version`
   - `labels`
   - `features`
   - `confidence`
   - `created_at`
2. 支持基础标签：
   - `strong_bull`
   - `weak_bull`
   - `range`
   - `weak_bear`
   - `panic`
   - `theme_hot`
   - `low_liquidity`
3. 支持多标签组合，而不是单一枚举。
4. 每个标签必须能回溯到特征来源。
5. Regime 规则需要版本化，避免历史回测不可复现。

验收标准：

- 可以基于指定 `snapshot_id` 生成 Market Regime。
- Regime 输出可解释，能看到使用了哪些 features。
- Regime definition 有版本。
- Backtest 可以读取指定版本的 regime。
- 测试覆盖强势、弱势、震荡、数据缺失场景。

UI 关联任务：

- `UI-V3-010 Market Regime Viewer`
- `UI-V3-001 Backtest Center`

---

### [ ] NW-V3-SX-002 P0 Regime-aware Backtest

任务目标：在回测中按 Market Regime 分组统计 rule 表现，避免整体回测把特定市场环境下有效的 rule 错误淘汰。

当前相关文件：

- `src/backtest/*`
- `src/services/market_regime_service.py`
- `src/services/rule_pool_service.py`
- `src/services/artifact_service.py`
- tests

允许修改：

- `src/backtest/regime_backtest.py`
- `src/services/regime_backtest_service.py`
- `src/models/backtest_result.py`
- `tests/backtest/test_regime_backtest.py`
- `docs/New-Web-Regime-Aware-Backtest.md`

禁止修改：

- 不删除原有整体回测。
- 不只输出全局 win_rate / return。
- 不用未来数据判断历史 regime。
- 不在前端计算回测指标。
- 不把样本数很少的 regime 结论当成高置信度。

实现要求：

1. 回测结果必须同时包含：
   - overall metrics
   - per-regime metrics
   - per-rule per-regime metrics
2. per-regime metrics 至少包含：
   - sample_count
   - win_rate
   - avg_return
   - max_drawdown
   - profit_factor，可选
   - confidence
3. 支持按以下维度切分：
   - regime label
   - trade_date range
   - trader_id
   - rule_id
   - strategy_version
4. 输出 Regime Backtest Report artifact。
5. 样本数不足时必须标记 low confidence。
6. Backtest 运行必须引用固定的 snapshot_id / dataset_id / regime_version，保证可复现。

验收标准：

- 同一 rule 可以看到整体表现和不同 regime 下的表现。
- 样本数不足的 regime 不参与自动淘汰。
- Report 可以解释“为什么某 rule 只适合某些市场状态”。
- Job Detail / Artifact Center 可以查看 Regime Backtest Report。
- 测试覆盖整体表现差但某 regime 表现好的 rule。

UI 关联任务：

- `UI-V3-011 Regime Backtest Report`
- `UI-V3-001 Backtest Center`
- `UI-V3-002 Rule Pool`

---

### [ ] NW-V3-SX-003 P0 Rule Applicability Profile

任务目标：为每条 rule 生成适用市场环境画像，让系统能保留“特定阶段有效”的 rule，而不是只按整体评分淘汰。

当前相关文件：

- `src/services/rule_pool_service.py`
- `src/services/regime_backtest_service.py`
- `src/models/rule.py`
- `src/models/backtest_result.py`
- tests

允许修改：

- `src/services/rule_applicability_service.py`
- `src/models/rule_applicability.py`
- `tests/services/test_rule_applicability_service.py`
- `docs/New-Web-Rule-Applicability-Profile.md`

禁止修改：

- 不覆盖原始 rule 定义。
- 不把 applicability 写死为人工标签。
- 不忽略 low confidence / low sample_count。
- 不在本任务中直接生成盘前建议。

实现要求：

1. RuleApplicabilityProfile 至少包含：
   - `rule_id`
   - `profile_version`
   - `applicable_regimes`
   - `blocked_regimes`
   - `neutral_regimes`
   - `min_sample_count`
   - `confidence`
   - `best_market_conditions`
   - `worst_market_conditions`
   - `source_backtest_id`
2. 支持从 Regime-aware Backtest 结果生成。
3. 支持人工 review 状态：
   - draft
   - reviewed
   - active
   - archived
4. 支持版本化，历史策略版本引用旧 profile 时必须可复现。
5. 输出 rule applicability artifact。

验收标准：

- 可以为指定 rule 生成 applicability profile。
- 整体表现一般但特定 regime 表现好的 rule 不会被直接淘汰。
- blocked_regimes 有明确证据来源。
- Profile 修改不影响历史 backtest result。
- Rule Pool UI 可以查看适用/禁用市场环境。

UI 关联任务：

- `UI-V3-012Rule Applicability Viewer`
- `UI-V3-002 Rule Pool`

---

### [ ] NW-V3-SX-004 P0 Regime-aware Rule Selection

任务目标：盘前策略生成时结合当前 Market Regime 选择适用 rule，避免在不合适市场环境下启用错误规则。

当前相关文件：

- `src/services/strategy_service.py`
- `src/services/rule_pool_service.py`
- `src/services/rule_applicability_service.py`
- `src/services/market_regime_service.py`
- `src/pipelines/*strategy*`
- tests

允许修改：

- `src/services/regime_rule_selection_service.py`
- `src/pipelines/strategy_pipeline_spec.py`
- `tests/services/test_regime_rule_selection_service.py`
- `docs/New-Web-Regime-Aware-Rule-Selection.md`

禁止修改：

- 不让 LLM 自行忽略 rule applicability。
- 不在前端选择 rule。
- 不把 blocked_regimes 的 rule 加入候选，除非用户显式 override 且有审计记录。
- 不删除原有策略版本机制。

实现要求：

1. 盘前 Strategy Run 读取：
   - current snapshot
   - current market regime
   - trader profile
   - strategy version
   - rule applicability profiles
2. Rule selection 输出：
   - selected_rules
   - skipped_rules
   - blocked_rules
   - selection_reason
   - evidence
3. blocked rule 必须记录原因。
4. override 必须记录：
   - operator
   - reason
   - timestamp
   - risk level
5. 输出 selection artifact，供盘前建议和盘后归因使用。

验收标准：

- 不同 market regime 下，同一 trader 可以选择不同 rule set。
- blocked regime 的 rule 默认不会进入 selected_rules。
- selection artifact 可以解释每条 rule 为什么被选择或跳过。
- 盘后归因能回溯当时使用的 regime 和 rule applicability version。
- 测试覆盖 strong_bull / weak_bear / theme_hot 至少三类场景。

UI 关联任务：

- `UI-V3-013 Regime-aware Rule Selection View`
- `UI-V2-006 Strategy Workspace`
- `UI-V3-002 Rule Pool`

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
- 发布检查必须确认没有新增第二套正式入口，也没有在 V1/V2/V3 期间出现双轨实现。

UI 关联任务：

- `UI-V3-012Final UX Review`
- `UI-V3-013 User Manual Coverage Verification`

---

### [ ] NW-V3-S3-002 P0 路由兼容层最终退役

任务目标：在最终发布验收阶段删除所有 legacy 路由别名与临时壳，只保留 canonical 路由。

允许修改：

- `docs/New-Web-UI-Routing.md`
- `docs/New-Web-Final-Acceptance.md`
- `docs/New-Web-Deployment-Guide.md`
- `docs/New-Web-UserManual.md`
- `web/src/app/router.tsx`
- `web/src/app/navigation.ts`

禁止修改：

- 不再保留 `/legacy/*` 临时壳。
- 不再保留 legacy 路由别名。
- 不允许新增任何非 canonical 入口。

实现要求：

1. 删除所有 legacy 映射。
2. 导航、文档、E2E 只使用 canonical 路由。
3. 验证旧入口不再可被正式用户路径引用。
4. 只保留最终需要的页面和路线。

验收标准：

- 旧入口已经从正式文档和导航中清除。
- 兼容层不再作为长期事实源存在。
- 最终验收文档与实际路由完全一致。
- 维护者只需要理解一套 canonical 路由。

UI 关联任务：

- `UI-V3-012Final UX Review`
- `UI-V3-013 User Manual Coverage Verification`
- `UI-V2-001 正式 Web 信息架构`

完成情况：

- 计划项，尚未执行。
- 用于 V3 发布前完成最终路由收口。

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
| NW-V2-S4-003 | UI-V2-001, UI-V2-004, UI-V2-008, UI-V1-001 |
| NW-V3-S1-001 | UI-V3-001 |
| NW-V3-S1-002 | UI-V3-002, UI-V3-003 |
| NW-V3-S2-001 | UI-V3-011 |
| NW-V3-S2-002 | UI-V3-004, UI-V3-005, UI-V3-010 |
| NW-V3-S3-001 | UI-V3-016, UI-V3-013 |
| NW-V3-S3-002 | UI-V3-012, UI-V3-013, UI-V2-001 |

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
7. 路由兼容层必须在 `docs/New-Web-UI-Routing.md` 中标明 canonical、legacy 和退役阶段，V2 收口、V3 删除。

---
