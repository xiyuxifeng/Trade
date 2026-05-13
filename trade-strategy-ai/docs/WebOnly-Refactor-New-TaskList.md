# WebOnly-Refactor-New-TaskList

> 本文件是 `trade-strategy-ai` Web-only 终态重构的一步到位执行清单。  
>  
> 目标不是做一个演示版本，而是把当前系统重构成可交付真实用户使用的 Web/API/Worker 产品形态：普通用户通过 Web 完成主要操作，管理员通过 Web 完成设置、任务追踪、产物查看、运维检查和恢复操作，CLI 只保留开发调试薄入口。  
>  
> 拆分方式采用“方案 A：终态一步到位、交付分切片”。每个 Stage 都必须产出可验证的系统能力，避免只完成底层框架但业务不可用。

---

2. 盘后自动补足增量数据，否则无法进行盘后优化
建议：必须实现自动补全。

盘后优化（如 ranking、归因、策略建议等）依赖于当天的完整数据（如行情、信号、评估结果等）。
如果盘后流程未自动补全缺失的增量数据（如行情、快照、信号等），会导致优化、归因、评估等步骤无法正常进行，甚至产物缺失。
建议在盘后流程（如 run-after-close、优化调度器）中自动检测并补全所有依赖的增量数据，确保数据链路闭环。
总结与建议
盘后自动补全增量数据，是保证盘后优化和评估链路可靠的基础。



## 1. 文档用途

本清单承担 5 个作用：

1. 把 Web-only 终态重构拆成可执行、可追踪、可验收的 Stage。
2. 避免 CLI、Web、Job、Workflow、Service 各自复制业务逻辑。
3. 确保每个业务能力都按“后端服务、Workflow/Step、Job Center、Web 页面、产物、权限、测试、用户文档”完整交付。
4. 作为后续开发、Review、测试、验收和发布的唯一执行清单。
5. 确保所有 Stage 完成后，第一版就是可交付版本，而不是临时样板。

---

## 2. 使用说明

### 2.1 接手前必须阅读

执行本清单前，必须先阅读：

- `docs/WebOnly-Refactor.md`
- `docs/WebOnly-Refactor-Execution-TaskList.md`
- `docs/WebUserManual.md`
- `docs/Web-UserManual-Coverage.md`
- `docs/APIReference.md`
- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/job_service.py`
- `api/routers/ui/jobs.py`

阅读目的：

- 确认现有 `JobDefinition`、`WorkflowDefinition`、`JobService` 和 UI Job API 已经存在，不要重复建设第二套事实源。
- 确认旧 TaskList 中已有的阶段拆分和风险，但执行时以本文件为准。
- 确认 Web 用户手册已经定义了面向普通用户的功能口径，后续实现必须能支撑手册描述。

### 2.2 任务状态规则

- `[ ]` 未开始
- `[-]` 进行中
- `[x]` 已完成
- `[!]` 阻塞
- `[~]` 已拆出到未来优化，不阻塞第一版交付

### 2.3 优先级规则

- `P0`：第一版交付必需能力，不完成不能对真实用户交付。
- `P1`：第一版建议完成的可靠性、体验或运维增强；如缺失会增加使用成本，但不应破坏主链路。
- `P2`：第一版之后的优化方向，不阻塞第一版上线。

### 2.4 完成规则

任务只能在同时满足以下条件后标记为 `[x]`：

1. 代码或文档已经落地到指定范围。
2. 相关单元测试、集成测试、端到端测试或人工验收已经完成。
3. Web UI、API、Job Center、Artifact、权限、审计、用户文档之间没有明显口径不一致。
4. 对旧 CLI 或旧 API 的影响已经在迁移矩阵中记录。
5. 失败场景、重试场景、无数据场景和权限不足场景至少完成一种可验证处理。

### 2.5 执行原则

```text
Web/API/Worker 是正式产品入口。
CLI 只作为开发调试入口。
Workflow 只负责编排。
Step 执行业务动作。
Job Center 负责异步任务生命周期、日志、产物和状态。
Service / Domain Module 承载业务能力。
DB / Artifact / Snapshot 保存结果。
Web UI 不直接拼业务逻辑。
API 不直接复制 CLI 逻辑。
```

必须遵守：

- 新增长任务必须进入 Job Center。
- 新增用户可见能力必须有 Web 页面或 Web 操作入口。
- 新增任务必须能查看执行状态、日志、产物和失败原因。
- 新增设置项必须有作用说明、默认值、校验规则和敏感信息脱敏。
- 新增业务能力必须补充用户文档和覆盖矩阵。
- 不允许把任意 shell 命令包装成 Web 功能。
- 不允许把 `subprocess`、本地文件路径拼接、Provider 调用细节散落到 Web Router。
- 不允许绕过现有 `JobDefinition`、`WorkflowDefinition`、`JobService` 另起一套任务事实源。

---

## 3. 第一版最终交付目标

所有 P0 Stage 完成后，系统必须达到以下状态：

1. 普通用户可以通过 Web 完成文章处理、市场数据、策略运行、回测优化、规则池审核、任务查看和产物查看。
2. 管理员可以通过 Web 完成配置管理、数据健康检查、备份恢复、用户与权限管理、运行日志查看和告警查看。
3. 所有超过 3 秒、会写库、会写文件、会调用外部服务、需要追踪进度的操作都通过 Job Center 执行。
4. 每个 Job 都记录输入快照、执行上下文、步骤时间线、日志、错误、产物、创建人、重试次数和取消状态。
5. 所有核心 Workflow 都能在 Web 中触发、停止、重试、查看历史和下载产物。
6. CLI 不再是正式产品入口，只保留 `dev run-step`、`dev run-workflow`、`dev list-workflows` 等薄调试能力。
7. 用户文档、API 文档、部署文档、运维文档和验收清单与实际功能一致。
8. 具备可重复的本地验收、回归测试和发布前检查流程。

第一版不允许以下交付状态：

- 只有底层框架，没有业务 Workflow 可用。
- Web 只能触发任务，不能解释执行结果。
- 任务成功但产物不可追溯。
- 设置项存在但用户不知道用途、默认值或影响范围。
- 回测、策略、文章、市场数据任一主链路只能通过 CLI 使用。
- 管理员无法判断任务失败原因或恢复系统。

---

## 4. 当前基础与主要差距

### 4.1 已有基础

当前项目已经具备以下基础，后续重构应复用和收敛：

- `src/services/job_registry.py` 已提供 Job 类型白名单、风险等级、参数 Schema、产物定义和 UI 动作定义。
- `src/services/workflow_service.py` 已提供 UI Workflow 定义和 Workflow Step 展示结构。
- `src/services/job_service.py` 已提供 Job 数据访问、状态更新和产物目录能力。
- `api/routers/ui/jobs.py` 已提供 UI Job 相关 API。
- Web 已经具备部分页面、导航、API Client 和 Job/Artifact 展示基础。
- `docs/WebUserManual.md` 已经具备面向普通用户的操作说明口径。

### 4.2 主要差距

当前要解决的核心问题：

- CLI 仍然承载部分正式使用路径，Web-only 交付边界不清晰。
- Workflow 目前更偏 UI 定义，缺少统一可执行 Step Contract 和 Step Timeline。
- Job、Workflow、Step、Artifact、Config Profile 之间缺少统一运行上下文。
- 配置快照、输入参数、执行产物和结果解释不够完整，难以复盘。
- 不同业务链路的 Web 操作、任务执行、结果展示和文档覆盖不均衡。
- 旧 TaskList 偏“先做底层、再迁移业务”，容易出现长期不可交付的中间态。

### 4.3 一步到位重构策略

本清单采用以下策略：

1. 先冻结现状和迁移矩阵，避免遗漏功能。
2. 建立统一运行契约，但必须桥接现有 `JobDefinition`、`WorkflowDefinition` 和 `JobService`。
3. 按业务纵向切片交付，每个切片都包含后端、Workflow、Job、Web、产物、权限、测试和文档。
4. 每个 Stage 完成后都应形成可运行能力，而不是只交付抽象框架。
5. 最后统一降级 CLI、收敛文档、完成 E2E 和发布验收。

---

## 5. Stage 总览

| Stage | 名称 | 优先级 | 交付目标 |
| --- | --- | --- | --- |
| Stage 0 | 现状冻结、迁移矩阵与交付边界 | P0 | 明确所有旧功能去向和第一版交付口径 |
| Stage 1 | 统一运行契约与兼容桥 | P0 | 建立 Config Profile、RunContext、StepResult、ArtifactRef，并桥接现有 Job/Workflow |
| Stage 2 | Job/Workflow/Step 执行底座 | P0 | 让 Workflow 真正可执行、可追踪、可恢复 |
| Stage 3 | 文章处理纵向切片 | P0 | Web 可完成文章抓取、清洗、入库、抽取、结果查看 |
| Stage 4 | 市场数据纵向切片 | P0 | Web 可完成开盘啦、快照、OHLCV、市场状态链路 |
| Stage 5 | 策略运行纵向切片 | P0 | Web 可完成策略版本、盘前、盘后、证据包、排名和记忆更新 |
| Stage 6 | 回测优化与规则池纵向切片 | P0 | Web 可完成回测、优化建议、候选策略、规则审核 |
| Stage 7 | 设置、权限、运维与恢复闭环 | P0 | 管理员可管理配置、权限、备份恢复、健康检查和告警 |
| Stage 8 | CLI 降级与兼容清理 | P0 | CLI 退为开发薄入口，正式业务入口收敛到 Web/API/Worker |
| Stage 9 | Web 收敛、文档、E2E 与发布验收 | P0 | 完成真实用户可交付验收 |
| Future | 第一版之后优化方向 | P2 | 增强可观测性、调度、分布式执行和高级体验 |

---

## 6. Stage 0：现状冻结、迁移矩阵与交付边界（P0）

### Stage 目标

- 冻结当前 CLI、Web、API、Service、Job、Artifact 能力现状。
- 建立完整“旧功能 -> 新 Web/API/Workflow/Step/Job”的迁移矩阵。
- 明确第一版交付边界，避免执行中变成框架重写或范围漂移。

### 阶段交付物

- `docs/WebOnly-Migration-Matrix.md`
- `docs/WebOnly-Current-State-Audit.md`
- `docs/WebOnly-V1-Acceptance.md`
- `docs/WebOnly-Development-Constraints.md`

### 任务清单

#### [ ] WON-S0-001 P0 建立 Web-only 迁移矩阵

目标：

建立旧 CLI、旧脚本、现有 Web/API/Job 到新 Web-only 架构的完整映射，避免功能遗漏。

输入：

- `docs/UserManual.md`
- `docs/WebUserManual.md`
- `docs/Web-UserManual-Coverage.md`
- `docs/WebOnly-Refactor.md`
- `docs/WebOnly-Refactor-Execution-TaskList.md`
- `cli/`
- `api/routers/ui/`
- `src/services/`

输出：

- `docs/WebOnly-Migration-Matrix.md`

矩阵字段：

```text
旧入口
当前 Service
当前 API
新 Step
新 Workflow
新 Job Type
Web 页面
配置依赖
产物类型
权限
风险等级
迁移策略
迁移状态
验收方式
备注
```

前置依赖：无。

可并行：`WON-S0-002`、`WON-S0-003`。

验收标准：

- 所有旧 CLI 命令、现有 UI Job、现有 Workflow 定义都有迁移策略。
- 每个保留能力至少映射到 Service、Step、Workflow、Job、Web 页面中的一项。
- 不迁移能力必须明确标记为 `deprecated` 或 `remove-later`，并说明原因。
- 没有未解释的“未知功能”。

注意事项：

- 迁移矩阵是后续 Stage 的验收入口。未进入矩阵的能力，不允许直接进入实现。
- `docs/bak/crawl.md` 可以作为历史参考，但不能当作当前正式文档。

完成情况：未开始。

#### [ ] WON-S0-002 P0 完成当前实现审计

目标：

记录当前项目真实实现状态，明确哪些能力已经可复用，哪些能力需要重构，哪些能力存在重复事实源。

输入：

- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/job_service.py`
- `api/routers/ui/jobs.py`
- `web/src/`
- `tests/`

输出：

- `docs/WebOnly-Current-State-Audit.md`

审计内容：

- Job 类型、风险等级、参数 Schema 和产物定义现状。
- Workflow 定义和 UI 展示现状。
- Job 状态、日志、错误、产物和取消能力现状。
- Web 页面覆盖现状。
- 测试覆盖现状。
- 明确重复逻辑、缺失能力和高风险路径。

前置依赖：无。

可并行：`WON-S0-001`、`WON-S0-003`。

验收标准：

- 已列出现有可复用模块和不可复用模块。
- 已标记所有可能与新运行契约冲突的现有实现。
- 已明确后续 Stage 需要桥接而不是重写的模块。

注意事项：

- 审计结论必须基于代码和已有文档，不写未经验证的判断。
- 不得为了新架构直接否定已有 Job Registry 和 Workflow Service。

完成情况：未开始。

#### [ ] WON-S0-003 P0 明确第一版交付验收清单

目标：

定义第一版可交付真实用户使用的最低验收口径。

输入：

- `docs/WebUserManual.md`
- `docs/Web-UserManual-Coverage.md`
- `docs/APIReference.md`
- `docs/WebOnly-Migration-Matrix.md`

输出：

- `docs/WebOnly-V1-Acceptance.md`

验收清单必须包含：

- 普通用户主流程验收。
- 管理员配置和运维验收。
- Job Center 可追踪性验收。
- Artifact 可下载和可解释验收。
- 权限、审计、敏感配置脱敏验收。
- E2E 回归验收命令和人工验收路径。
- 发布前阻断项。

前置依赖：`WON-S0-001` 可先并行草拟，最终需回填矩阵结论。

可并行：`WON-S0-002`、`WON-S0-004`。

验收标准：

- 每个第一版核心功能都有明确“用户能做什么、在哪里做、怎么看结果、失败后怎么办”。
- 所有验收项都能映射到后续 Stage 或 Future 优化。
- 不把 Future 优化列为第一版阻断项。

注意事项：

- 第一版验收必须以真实用户可操作为标准，不以代码结构完成为标准。

完成情况：未开始。

#### [ ] WON-S0-004 P0 建立 Web-only 开发约束

目标：

防止重构过程中继续向 CLI、Web Router、Job Runner 堆业务逻辑。

输入：

- `docs/WebOnly-Refactor.md`
- `docs/WebOnly-Current-State-Audit.md`

输出：

- `docs/WebOnly-Development-Constraints.md`

约束内容：

- CLI 允许和禁止的能力。
- Web Router 允许和禁止的能力。
- Job Runner 允许和禁止的能力。
- Workflow 和 Step 的责任边界。
- Artifact 写入和命名规范。
- 配置读取、快照、脱敏和审计规范。
- Review Checklist。

前置依赖：`WON-S0-002`。

可并行：无。

验收标准：

- 后续 PR 可直接按该文档判断是否违反 Web-only 约束。
- 明确禁止 Web 任意执行 shell。
- 明确禁止新增复杂正式 CLI 命令。
- 明确新增业务能力必须补 Web、Job、Artifact、测试和用户文档。

注意事项：

- 约束必须可执行，避免只写原则。

完成情况：未开始。

### 阶段注意事项

- Stage 0 不实现新业务功能，只建立边界和可追踪依据。
- 不得修改 `Web-TaskList.md` 作为本阶段目标。
- 如果审计发现文档与实现不一致，以当前实现为事实来源，并在审计文档中标记文档差异。

### 阶段验收标准

- 4 个阶段交付物均存在且内容互相一致。
- 迁移矩阵覆盖全部旧入口和现有 Web Job/Workflow。
- 第一版验收清单可以作为 Stage 9 发布检查依据。
- 后续 Stage 的任务都能追溯到迁移矩阵或第一版验收清单。

---

## 7. Stage 1：统一运行契约与兼容桥（P0）

### Stage 目标

- 建立 Config Profile、RunContext、StepResult、ArtifactRef、StepError 的统一契约。
- 不替换现有 `JobDefinition`、`WorkflowDefinition`、`JobService`，而是建立兼容桥。
- 让后续业务切片都能复用统一输入快照、执行上下文、产物引用和错误结构。

### 阶段交付物

- 统一运行契约代码。
- Config Profile 和 Config Snapshot 服务。
- Job/Workflow 兼容桥。
- 契约测试和迁移说明。

### 任务清单

#### [ ] WON-S1-001 P0 设计并落地运行契约

目标：

定义所有 Step 和 Workflow 共用的运行数据结构。

输入：

- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/job_service.py`
- `docs/WebOnly-Development-Constraints.md`

输出：

- `src/services/runtime_contracts.py`
- `tests/services/test_runtime_contracts.py`

契约必须包含：

- `RunContext`
- `StepInput`
- `StepResult`
- `StepError`
- `ArtifactRef`
- `ConfigSnapshot`
- `UserContext`

前置依赖：Stage 0 完成。

可并行：`WON-S1-002`。

验收标准：

- Contract 类型具备序列化和反序列化测试。
- 错误结构能表达用户错误、系统错误、外部依赖错误和权限错误。
- ArtifactRef 能表达文件、表格、报告、JSON、图表和外部链接。
- Contract 不依赖 CLI 或 Web 框架。

注意事项：

- Contract 不能直接读取配置文件、数据库或环境变量。
- Contract 字段命名必须稳定，后续会写入 Job 历史和 Artifact 元数据。

完成情况：未开始。

#### [ ] WON-S1-002 P0 实现 Config Profile 与配置快照

目标：

让每次任务执行都能追踪使用了什么配置，同时保护敏感信息。

输入：

- 现有配置读取逻辑。
- `docs/WebUserManual.md` 中的设置说明。

输出：

- `src/services/config_profile_service.py`
- `src/services/config_snapshot_service.py`
- `api/routers/ui/settings.py` 配置快照相关接口
- `tests/services/test_config_profile_service.py`
- `tests/services/test_config_snapshot_service.py`

能力要求：

- 读取默认配置档。
- 生成任务运行配置快照。
- 记录配置版本、来源、哈希、脱敏字段和校验结果。
- 支持 Web 查询配置项说明、默认值、当前值来源和风险提示。

前置依赖：Stage 0 完成。

可并行：`WON-S1-001`。

验收标准：

- 敏感字段不会出现在 API 响应、Job 日志或 Artifact 元数据中。
- 配置快照能与 Job 关联。
- 配置缺失或非法时返回用户可理解的错误。
- Web 设置页能解释配置项用途和影响范围。

注意事项：

- 第一版可以只有默认配置档，但数据结构必须允许后续扩展多配置档。
- 不允许在 Web 中展示 cookie、token、secret 原文。

完成情况：未开始。

#### [ ] WON-S1-003 P0 建立 Job/Workflow 兼容桥

目标：

把现有 Job Registry 和 Workflow Definition 桥接到新运行契约，避免重复定义任务和工作流。

输入：

- `src/services/job_registry.py`
- `src/services/workflow_service.py`
- `src/services/runtime_contracts.py`

输出：

- `src/services/runtime_registry_bridge.py`
- `tests/services/test_runtime_registry_bridge.py`

能力要求：

- 将现有 `JobDefinition` 转换为可执行 Job Contract。
- 将现有 `WorkflowDefinition` 转换为 Workflow Contract。
- 保留现有风险等级、参数 Schema、产物定义和 UI Action。
- 明确新旧字段映射关系。

前置依赖：`WON-S1-001`。

可并行：`WON-S1-004`。

验收标准：

- 现有 Job 类型全部可通过桥接层读取。
- 现有 Workflow 定义全部可通过桥接层读取。
- 无重复 Job Type 事实源。
- 新增 Job 或 Workflow 的流程只有一个登记入口。

注意事项：

- 兼容桥是过渡期关键模块，不允许一边保留旧 Registry，一边新增另一套长期 Registry。
- 如果发现字段无法映射，必须回到 Stage 0 审计文档记录差异。

完成情况：未开始。

#### [ ] WON-S1-004 P0 建立统一 Artifact 元数据规范

目标：

让所有任务产物具备统一命名、类型、来源、权限、下载和解释方式。

输入：

- `src/services/job_service.py`
- 现有 Artifact 相关 API 和 Web 页面。

输出：

- `src/services/artifact_contracts.py`
- `src/services/artifact_service.py` 增强
- `tests/services/test_artifact_contracts.py`

能力要求：

- Artifact 元数据包含 Job、Workflow、Step、创建时间、类型、路径、大小、摘要、可见权限和解释说明。
- 支持报告、CSV、JSON、日志、图表数据、数据快照。
- 支持产物过期、缺失、权限不足的结构化错误。

前置依赖：`WON-S1-001`。

可并行：`WON-S1-003`。

验收标准：

- Job 详情页可以按 Step 分组展示产物。
- Artifact API 不暴露服务器绝对路径。
- 缺失文件不会导致 Job 详情页崩溃。
- 产物说明能支撑普通用户理解“结果是什么”。

注意事项：

- Artifact 元数据是用户理解执行结果的关键，不只用于下载文件。

完成情况：未开始。

### 阶段注意事项

- Stage 1 只建立契约和桥接，不大规模迁移业务逻辑。
- 所有新契约必须有测试，避免后续 Stage 在不稳定结构上开发。
- 不要破坏现有 UI Job 列表和已有 API 响应，必要时做兼容字段。

### 阶段验收标准

- 新 Contract、Config Snapshot、Artifact Metadata、Registry Bridge 均有自动化测试。
- 现有 Job 和 Workflow 能通过兼容桥读取。
- Web 设置页和 Job 详情页具备配置快照、产物元数据的基础展示能力。
- 后续业务切片不需要再各自定义运行上下文。

---

## 8. Stage 2：Job/Workflow/Step 执行底座（P0）

### Stage 目标

- 把 Workflow 从 UI 展示定义升级为可执行编排。
- 建立 Step Registry、Workflow Runner、Step Timeline、取消、重试和失败恢复能力。
- 让 Job Center 成为所有长任务的统一执行入口。

### 阶段交付物

- Step Registry。
- Workflow Runner。
- Job Runner 集成。
- Step Timeline API 和 Web 展示。
- 执行底座测试。

### 任务清单

#### [ ] WON-S2-001 P0 实现 Step Registry

目标：

建立统一 Step 登记入口，让业务动作可独立运行、可被 Workflow 编排、可被测试。

输入：

- `src/services/runtime_contracts.py`
- `src/services/runtime_registry_bridge.py`

输出：

- `src/services/step_registry.py`
- `tests/services/test_step_registry.py`

能力要求：

- Step 具备名称、版本、输入 Schema、输出 Schema、风险等级、权限要求和执行函数。
- 支持按名称获取 Step。
- 支持列出可用 Step。
- 支持校验 Step 输入。

前置依赖：Stage 1 完成。

可并行：无。

验收标准：

- 注册重复 Step 会失败并返回明确错误。
- 输入非法时不会进入业务执行函数。
- Step Registry 不依赖 Web Router 或 CLI。

注意事项：

- Step 名称一旦写入 Job 历史，不应随意修改；需要改名时必须保留别名或迁移方案。

完成情况：未开始。

#### [ ] WON-S2-002 P0 实现 Workflow Runner

目标：

让 Workflow 能按 Step 顺序执行，并记录每个 Step 的输入、输出、耗时、状态、错误和产物。

输入：

- `src/services/step_registry.py`
- `src/services/runtime_contracts.py`
- `src/services/job_service.py`

输出：

- `src/services/workflow_runner.py`
- `tests/services/test_workflow_runner.py`

能力要求：

- 顺序执行 Step。
- Step 失败时停止或按 Workflow 策略跳过。
- 记录 Step Timeline。
- 支持运行上下文透传。
- 支持 Workflow 级别产物汇总。

前置依赖：`WON-S2-001`。

可并行：`WON-S2-003` 可在接口稳定后并行。

验收标准：

- Workflow 成功时每个 Step 都有完成记录。
- Workflow 失败时能定位失败 Step 和失败原因。
- Step 产物能回写到 Job Artifact。
- Workflow Runner 有成功、失败、跳过、无产物四类测试。

注意事项：

- Workflow Runner 不写具体业务逻辑。
- 不能把某个业务链路硬编码到 Runner。

完成情况：未开始。

#### [ ] WON-S2-003 P0 集成 Job Runner 与异步执行生命周期

目标：

让 Job Center 能执行 Step 或 Workflow，并完整记录生命周期。

输入：

- `src/services/job_service.py`
- `src/services/workflow_runner.py`
- `api/routers/ui/jobs.py`

输出：

- `src/services/job_runner.py` 增强或重构
- `api/routers/ui/jobs.py` 增强
- `tests/services/test_job_runner.py`
- `tests/api/test_ui_jobs.py`

能力要求：

- 创建 Job 时保存输入参数和配置快照。
- 执行中更新状态、进度、日志和 Step Timeline。
- 支持取消请求。
- 支持失败后重试。
- 支持 Job 详情按 Workflow/Step/Artifact 展示。

前置依赖：`WON-S2-002`。

可并行：`WON-S2-004`。

验收标准：

- Web 发起的长任务都能在 Job Center 查询状态。
- 取消任务后状态一致，不出现任务实际继续写库但 UI 显示取消成功的情况。
- 重试任务保留原 Job 关联信息或明确生成新 Job，并可追溯来源。
- API 对普通用户和管理员返回的字段符合权限要求。

注意事项：

- Job Runner 只负责生命周期，不负责业务算法。
- 如果底层业务无法安全取消，UI 必须说明“取消请求已提交，等待当前步骤结束”。

完成情况：未开始。

#### [ ] WON-S2-004 P0 完成 Job 详情 Web 追踪视图

目标：

让普通用户和管理员能理解任务执行到了哪里、产出了什么、失败原因是什么。

输入：

- Job API。
- Artifact API。
- Step Timeline 数据结构。

输出：

- `web/src/pages/jobs/` 增强
- `web/src/lib/api/jobs.ts` 增强
- `web/src/types/jobs.ts` 增强
- Web 组件测试或端到端测试

能力要求：

- 展示 Job 状态、创建人、开始时间、结束时间、耗时、风险等级。
- 展示 Step Timeline。
- 展示每个 Step 的日志摘要、错误摘要和产物。
- 支持取消、重试、下载产物。
- 对失败结果给出用户可理解的解释。

前置依赖：`WON-S2-003`。

可并行：无。

验收标准：

- 用户不看后台日志也能判断任务成功、失败或等待的原因。
- 产物缺失、权限不足、任务取消都有清晰提示。
- 移动端和桌面端都可正常查看核心信息。

注意事项：

- 不在前端推断业务结果含义；结果含义应由 API 或 Artifact 元数据提供。

完成情况：未开始。

### 阶段注意事项

- Stage 2 是后续所有业务切片的基础，不应夹带具体业务重写。
- 可以用最小样例 Step 做底座测试，但不能把样例当第一版交付功能。
- 需要保持现有 Job API 基本兼容，避免 Web 已有页面断裂。

### 阶段验收标准

- Web 可以发起、查看、取消、重试一个真实 Workflow Job。
- Job 详情中能看到 Step Timeline、日志、错误和 Artifact。
- 执行底座自动化测试覆盖成功、失败、取消、重试、无权限、产物缺失。
- 后续 Stage 可以只注册业务 Step 和 Workflow，不再重写执行底座。

---

## 9. Stage 3：文章处理纵向切片（P0）

### Stage 目标

- 将文章抓取、清洗、校验、入库、元数据抽取作为第一个完整业务切片交付。
- 验证 Web-only 架构对真实业务链路可用。
- 形成后续市场、策略、回测切片的实现模板。

### 阶段交付物

- Article Pipeline Step 和 Workflow。
- Article Job Type。
- Web 文章处理页面。
- 文章处理产物和结果解释。
- 文章处理测试和用户文档更新。

### 任务清单

#### [ ] WON-S3-001 P0 定义 article_pipeline 业务契约

目标：

明确文章处理链路的输入、输出、步骤、产物和失败语义。

输入：

- 现有文章抓取、Pipeline、抽取相关 Service。
- `docs/WebUserManual.md`
- `docs/WebOnly-Migration-Matrix.md`

输出：

- `docs/WebOnly-Article-Pipeline-Contract.md`
- Article Workflow Definition 更新
- Article Job Definition 更新

契约步骤：

```text
crawl_articles
clean_articles
validate_articles
store_articles
extract_article_metadata
```

前置依赖：Stage 2 完成。

可并行：无。

验收标准：

- 每个 Step 的输入、输出、错误、产物都定义清楚。
- Web 页面需要展示的结果字段已经明确。
- 与迁移矩阵中的文章相关旧入口完成映射。

注意事项：

- 不使用 `docs/bak/crawl.md` 作为正式行为来源，只可参考历史设计。

完成情况：未开始。

#### [ ] WON-S3-002 P0 实现文章抓取 Step

目标：

将文章抓取能力封装为可被 Workflow 调用的 Step。

输入：

- 现有抓取 Service。
- Config Snapshot。

输出：

- Article Step 代码。
- Article Step 测试。

能力要求：

- 支持来源、时间范围、数量限制、去重策略。
- 记录抓取数量、成功数量、失败数量、跳过数量。
- 生成抓取原始结果 Artifact。
- 外部依赖失败时返回结构化错误。

前置依赖：`WON-S3-001`。

可并行：`WON-S3-003` 在契约稳定后可并行。

验收标准：

- 无网络或来源不可用时任务失败原因清晰。
- 重复文章不会重复入库或重复计数。
- Step 输出可在 Job 详情中解释。

注意事项：

- 大规模抓取必须支持数量限制，避免误触发大量请求。

完成情况：未开始。

#### [ ] WON-S3-003 P0 实现文章清洗、校验和入库 Step

目标：

将抓取结果处理成可用于后续分析的数据。

输入：

- 抓取 Step 输出。
- 现有文章处理 Service。

输出：

- 清洗 Step。
- 校验 Step。
- 入库 Step。
- 对应测试。

能力要求：

- 清洗标题、正文、来源、时间、标签。
- 校验必填字段和重复数据。
- 入库时记录新增、更新、跳过、失败数量。
- 生成清洗摘要和校验错误 Artifact。

前置依赖：`WON-S3-001`。

可并行：`WON-S3-002`。

验收标准：

- 脏数据不会导致整个 Job 无解释崩溃。
- 入库结果可以在 Web 上解释。
- 校验失败样本可下载。

注意事项：

- 入库 Step 必须幂等，同一输入重复执行不应造成重复数据。

完成情况：未开始。

#### [ ] WON-S3-004 P0 实现文章元数据抽取 Step

目标：

从文章中抽取后续策略和市场分析需要的结构化信息。

输入：

- 已入库文章。
- 现有抽取 Service 或 Provider。

输出：

- 元数据抽取 Step。
- 抽取结果 Artifact。
- 对应测试。

能力要求：

- 抽取标的、主题、事件、情绪、置信度、引用来源。
- 记录抽取成功、失败、跳过数量。
- Provider 错误结构化记录。

前置依赖：`WON-S3-003`。

可并行：无。

验收标准：

- 抽取结果可回溯到原文章。
- Provider 失败不会污染已成功结果。
- Web 能解释置信度和失败样本含义。

注意事项：

- 如果涉及外部模型或 Provider，必须受配置档和权限控制。

完成情况：未开始。

#### [ ] WON-S3-005 P0 完成文章处理 Web 页面与结果解释

目标：

让普通用户可通过 Web 发起文章处理、查看状态、查看结果和下载产物。

输入：

- Article Workflow。
- Article Job Type。
- Artifact 元数据。

输出：

- Web 文章处理页面。
- API Client 和类型定义。
- 用户文档更新。
- Web 测试或端到端测试。

能力要求：

- 支持选择来源、时间范围、数量限制和抽取选项。
- 显示执行状态、Step Timeline、统计结果、失败样本和产物。
- 解释抓取数量、清洗数量、入库数量、抽取数量的含义。

前置依赖：`WON-S3-002`、`WON-S3-003`、`WON-S3-004`。

可并行：无。

验收标准：

- 用户只看 WebUserManual 和 Web 页面即可完成文章处理。
- 执行结果和 Job 详情一致。
- 失败时能知道是配置问题、来源问题、数据问题还是系统问题。

注意事项：

- 文章页面不要暴露底层 Step 名称作为唯一解释，需提供用户可理解的文案。

完成情况：未开始。

### 阶段注意事项

- Stage 3 是第一条业务样板，但验收标准必须按真实业务交付，不按样板降低要求。
- 文章切片完成后，必须回顾 Stage 1 和 Stage 2 契约是否足够支撑后续业务。

### 阶段验收标准

- Web 能完成完整 article_pipeline。
- Job Center 能追踪每个文章 Step。
- 文章处理产物可下载、可解释、可追溯。
- 用户文档和覆盖矩阵已更新。
- 自动化测试覆盖文章链路的成功、无数据、外部依赖失败和脏数据场景。

---

## 10. Stage 4：市场数据纵向切片（P0）

### Stage 目标

- 将开盘啦数据、市场快照、OHLCV、市场状态构建收敛到 Web-only 业务链路。
- 让用户能通过 Web 准备策略运行所需的市场数据，并理解数据质量。

### 阶段交付物

- Market Data Workflow。
- Kaipan、Snapshot、OHLCV、Market State Step。
- 市场数据 Web 页面。
- 数据质量报告和 Artifact。
- 测试和文档更新。

### 任务清单

#### [ ] WON-S4-001 P0 定义 market_data_pipeline 业务契约

目标：

明确市场数据链路的输入、输出、数据源、缓存、快照和质量指标。

输入：

- 现有市场数据 Service。
- 迁移矩阵中 market、kaipan、snapshot、ohlcv 相关项。

输出：

- `docs/WebOnly-Market-Data-Contract.md`
- Market Workflow Definition。
- Market Job Definition。

建议步骤：

```text
fetch_kaipan_data
normalize_kaipan_data
crawl_ohlcv_data
build_market_snapshot
build_market_state
validate_market_data_quality
```

前置依赖：Stage 2 完成。

可并行：无。

验收标准：

- 每种数据源的配置依赖、失败语义、缓存策略和产物都明确。
- 市场数据质量指标可用于 Web 展示。
- 与策略运行所需输入完成对齐。

注意事项：

- 不能只做数据抓取，必须交付可解释的数据质量结果。

完成情况：未开始。

#### [ ] WON-S4-002 P0 实现开盘啦抓取与标准化 Step

目标：

将开盘啦相关 CLI 能力迁移为 Web 可执行 Step。

输入：

- 现有 kaipan fetch / normalize / status / run 能力。

输出：

- `fetch_kaipan_data` Step。
- `normalize_kaipan_data` Step。
- 对应测试。

能力要求：

- 支持按日期或交易日范围执行。
- 输出抓取摘要、标准化摘要和异常数据。
- 支持配置缺失、认证失败、限流、无数据的结构化错误。

前置依赖：`WON-S4-001`。

可并行：`WON-S4-003`。

验收标准：

- Web 上能看到开盘啦数据最新状态。
- 标准化失败样本可下载。
- 不暴露 cookie 或 token。

注意事项：

- 如果数据源需要敏感配置，只能从 Config Profile 读取并脱敏展示。

完成情况：未开始。

#### [ ] WON-S4-003 P0 实现 OHLCV 与市场快照 Step

目标：

让 Web 能准备策略运行所需的行情和市场快照。

输入：

- 现有 snapshot build、ohlcv crawl、market-state build 能力。

输出：

- `crawl_ohlcv_data` Step。
- `build_market_snapshot` Step。
- `build_market_state` Step。
- 对应测试。

能力要求：

- 支持交易日、股票池、回溯窗口配置。
- 输出行情覆盖率、缺失标的、异常标的、快照版本。
- 生成市场快照 Artifact。

前置依赖：`WON-S4-001`。

可并行：`WON-S4-002`。

验收标准：

- 缺失行情不会静默成功。
- 快照版本能被策略运行引用。
- Web 能解释覆盖率、缺失数、异常数。

注意事项：

- 快照必须可追溯，不允许策略运行读取一个无法定位来源的临时状态。

完成情况：未开始。

#### [ ] WON-S4-004 P0 完成市场数据 Web 页面与质量报告

目标：

让用户可通过 Web 执行市场数据准备，并判断数据是否可用于策略运行。

输入：

- Market Workflow。
- Market Artifact。
- Data Quality 输出。

输出：

- Web 市场数据页面增强。
- 数据质量报告组件。
- 用户文档更新。
- Web 测试或端到端测试。

能力要求：

- 展示数据源状态、最近更新时间、覆盖率、缺失项、异常项。
- 支持发起数据更新任务。
- 支持查看和下载市场快照。
- 提供“是否可以进入策略运行”的明确提示。

前置依赖：`WON-S4-002`、`WON-S4-003`。

可并行：无。

验收标准：

- 用户能判断市场数据是否可用。
- 市场数据 Job 失败时能定位失败来源。
- 市场快照能被后续 Stage 5 策略运行选择或引用。

注意事项：

- Web 页面不能把数据质量问题隐藏在日志里，必须正面展示。

完成情况：未开始。

### 阶段注意事项

- 市场数据是策略运行前置条件，验收不能只看任务成功状态。
- 所有数据快照必须有版本和生成来源。

### 阶段验收标准

- Web 可以完成市场数据准备链路。
- 市场数据结果有质量报告和可下载产物。
- 策略运行可以引用明确版本的市场快照。
- 文档说明了每个数据指标的含义和异常处理方式。

---

## 11. Stage 5：策略运行纵向切片（P0）

### Stage 目标

- 将策略版本构建、盘前运行、盘后复盘、证据包、排名更新、交易记忆更新收敛到 Web-only 链路。
- 让普通用户可以通过 Web 完成每日策略运行，并理解信号结果。

### 阶段交付物

- Strategy Workflow。
- Pre-market 和 After-close Workflow。
- 策略运行 Web 页面。
- 信号、证据包、排名、交易记忆产物。
- 测试和文档更新。

### 任务清单

#### [ ] WON-S5-001 P0 定义 strategy_run_pipeline 业务契约

目标：

明确策略运行所需输入、输出、版本、快照依赖和结果解释。

输入：

- 现有 strategy build/list。
- 现有 run-pre-market、run-after-close、list-signals。
- Stage 4 市场快照。

输出：

- `docs/WebOnly-Strategy-Run-Contract.md`
- Strategy Workflow Definition。
- Strategy Job Definition。

建议 Workflow：

```text
build_strategy_version
run_pre_market
run_after_close
build_evidence_pack
update_ranking
write_trader_memory
```

前置依赖：Stage 4 完成。

可并行：无。

验收标准：

- 策略版本、市场快照、配置快照之间关系明确。
- 每类信号结果有解释字段。
- 盘前和盘后的成功、失败、无信号场景定义清楚。

注意事项：

- 策略结果必须可复盘，不能只保存最终推荐列表。

完成情况：未开始。

#### [ ] WON-S5-002 P0 实现策略版本构建 Step

目标：

将策略配置、规则、市场依赖打包成可追溯策略版本。

输入：

- 策略配置。
- 市场快照。
- 规则池状态。

输出：

- `build_strategy_version` Step。
- 策略版本 Artifact。
- 对应测试。

能力要求：

- 记录策略版本号、规则版本、配置快照、市场快照。
- 校验策略依赖是否满足。
- 输出策略版本摘要。

前置依赖：`WON-S5-001`。

可并行：`WON-S5-003` 可在契约稳定后并行。

验收标准：

- 同一次策略运行可以追溯到明确策略版本。
- 缺少市场快照或规则池异常时不能静默运行。
- Web 能解释策略版本包含什么。

注意事项：

- 策略版本是盘前、盘后、回测的共同基础，字段必须稳定。

完成情况：未开始。

#### [ ] WON-S5-003 P0 实现盘前运行 Step 与信号结果

目标：

让用户通过 Web 执行盘前策略运行，并获得可解释信号。

输入：

- 策略版本。
- 市场快照。

输出：

- `run_pre_market` Step。
- 信号结果 Artifact。
- 对应测试。

能力要求：

- 输出候选标的、信号类型、理由、风险、置信度、数据来源。
- 支持无信号结果。
- 支持运行参数快照。

前置依赖：`WON-S5-002`。

可并行：无。

验收标准：

- 无信号也是成功结果，并在 Web 中解释原因。
- 每条信号可追溯到策略版本和输入数据。
- 失败时可判断是数据问题、策略配置问题还是系统问题。

注意事项：

- 信号结果不是交易建议文案，Web 必须展示风险和来源。

完成情况：未开始。

#### [ ] WON-S5-004 P0 实现盘后复盘、证据包、排名和记忆更新

目标：

完成策略运行闭环，让盘后结果能沉淀到后续策略评估。

输入：

- 当日盘前信号。
- 市场收盘数据。
- 策略版本。

输出：

- `run_after_close` Step。
- `build_evidence_pack` Step。
- `update_ranking` Step。
- `write_trader_memory` Step。
- 对应测试。

能力要求：

- 输出盘后表现、命中情况、失败样本、证据包、排名变化、交易记忆更新摘要。
- 产物可下载并能在 Web 中解释。

前置依赖：`WON-S5-003`。

可并行：无。

验收标准：

- 盘前信号和盘后表现可以关联。
- 证据包包含可复盘的数据来源。
- 排名和记忆更新失败不会覆盖原有有效数据。

注意事项：

- 盘后链路会写入长期状态，必须具备备份和回滚说明。

完成情况：未开始。

#### [ ] WON-S5-005 P0 完成策略运行 Web 页面

目标：

让用户可以通过 Web 完成策略版本构建、盘前运行、盘后复盘和结果查看。

输入：

- Strategy Workflow。
- Strategy Artifact。
- Signal Result API。

输出：

- Web 策略页面增强。
- 策略结果解释组件。
- 用户文档更新。
- Web 测试或端到端测试。

能力要求：

- 展示策略版本、市场快照、运行状态、信号列表、证据包、排名变化和记忆摘要。
- 支持查看历史运行。
- 支持下载结果和证据包。

前置依赖：`WON-S5-002`、`WON-S5-003`、`WON-S5-004`。

可并行：无。

验收标准：

- 用户能完成每日盘前和盘后操作。
- 结果解释不依赖后台日志。
- 历史运行可比较、可追溯。

注意事项：

- UI 必须明确结果含义和风险，不应把分数或排名直接当结论。

完成情况：未开始。

### 阶段注意事项

- 策略链路必须依赖 Stage 4 的市场快照，不允许读取无法追溯的临时数据。
- 所有策略输出都必须有版本和来源。

### 阶段验收标准

- Web 可以完成策略版本构建、盘前运行、盘后复盘。
- 用户可以查看信号、证据包、排名和记忆更新结果。
- 结果具备可追溯版本和 Artifact。
- 自动化测试覆盖成功、无信号、数据缺失、配置错误和写入失败场景。

---

## 12. Stage 6：回测优化与规则池纵向切片（P0）

### Stage 目标

- 将回测、报告、规则校验、优化建议、候选策略、规则池审核迁移到 Web-only。
- 让用户能通过 Web 验证策略质量，并管理规则进入或退出。

### 阶段交付物

- Backtest Workflow。
- Optimize Workflow。
- Rule Pool Workflow。
- 回测和规则池 Web 页面。
- 回测报告、优化建议、规则审核产物。
- 测试和文档更新。

### 任务清单

#### [ ] WON-S6-001 P0 定义 backtest_optimize_rule_pipeline 业务契约

目标：

明确回测、优化和规则池之间的数据关系和用户操作路径。

输入：

- 现有 backtest run/report/validate-rules。
- 现有 optimize filter/advise/create-candidate。
- 现有 rule-pool show/list/review/review-batch。
- 策略版本和市场快照。

输出：

- `docs/WebOnly-Backtest-Optimize-Rule-Contract.md`
- Backtest Workflow Definition。
- Optimize Workflow Definition。
- Rule Pool Workflow Definition。

前置依赖：Stage 5 完成。

可并行：无。

验收标准：

- 回测输入、数据窗口、费用模型、规则版本、策略版本定义明确。
- 优化建议如何转为候选策略定义明确。
- 规则审核状态机定义明确。

注意事项：

- 不允许把回测结果只作为文件输出，必须能在 Web 中解释关键指标。

完成情况：未开始。

#### [ ] WON-S6-002 P0 实现回测运行、报告和规则校验 Step

目标：

让用户通过 Web 执行回测并理解结果。

输入：

- 策略版本。
- 市场数据窗口。
- 费用和滑点配置。

输出：

- `run_backtest` Step。
- `build_backtest_report` Step。
- `validate_backtest_rules` Step。
- 回测报告 Artifact。
- 对应测试。

能力要求：

- 输出收益、回撤、胜率、交易次数、风险指标、异常样本。
- 生成可下载报告。
- 校验规则是否适用于指定数据窗口。

前置依赖：`WON-S6-001`。

可并行：`WON-S6-003` 在契约稳定后并行。

验收标准：

- 回测结果可复现。
- 数据不足、规则不适配、参数非法时返回结构化错误。
- Web 能解释关键指标和异常样本。

注意事项：

- 回测可能消耗较多资源，必须支持参数限制和任务取消。

完成情况：未开始。

#### [ ] WON-S6-003 P0 实现优化建议和候选策略 Step

目标：

把优化结果从离线命令迁移为 Web 可审阅的候选建议。

输入：

- 回测结果。
- 策略版本。
- 规则池状态。

输出：

- `filter_optimization_candidates` Step。
- `advise_optimization` Step。
- `create_strategy_candidate` Step。
- 优化建议 Artifact。
- 对应测试。

能力要求：

- 输出建议类型、影响范围、预期改善、风险和证据来源。
- 支持用户在 Web 上查看候选策略。
- 候选策略不自动生效，必须进入审核。

前置依赖：`WON-S6-002`。

可并行：无。

验收标准：

- 优化建议可追溯到回测结果。
- 候选策略状态明确，不会直接污染正式策略。
- Web 能解释为什么产生该建议。

注意事项：

- 优化建议属于辅助决策，必须展示风险和证据。

完成情况：未开始。

#### [ ] WON-S6-004 P0 实现规则池审核 Workflow

目标：

让管理员或有权限用户通过 Web 审核规则和候选策略。

输入：

- 候选策略。
- 规则池状态。

输出：

- `review_rule` Step。
- `review_rule_batch` Step。
- Rule Pool API 增强。
- 对应测试。

能力要求：

- 支持通过、拒绝、退回、禁用、批量审核。
- 记录审核人、审核时间、审核意见和前后状态。
- 生成审核记录 Artifact 或审计日志。

前置依赖：`WON-S6-003`。

可并行：`WON-S6-005` 可在接口稳定后并行。

验收标准：

- 未授权用户不能审核规则。
- 审核状态可追溯且不可静默覆盖。
- 批量审核失败时能说明部分成功和部分失败。

注意事项：

- 规则池变更会影响策略运行，必须有审计记录。

完成情况：未开始。

#### [ ] WON-S6-005 P0 完成回测、优化和规则池 Web 页面

目标：

让用户通过 Web 完成回测、查看报告、查看优化建议、审核规则。

输入：

- Backtest Workflow。
- Optimize Workflow。
- Rule Pool Workflow。
- Artifact 元数据。

输出：

- Web 回测页面。
- Web 优化建议页面。
- Web 规则池页面。
- 用户文档更新。
- Web 测试或端到端测试。

能力要求：

- 支持选择策略版本、市场窗口、回测参数。
- 展示关键指标、收益曲线数据、异常样本和报告下载。
- 展示优化建议和候选策略。
- 支持规则审核操作和审核历史查看。

前置依赖：`WON-S6-002`、`WON-S6-003`、`WON-S6-004`。

可并行：无。

验收标准：

- 用户不使用 CLI 也能完成回测、优化和规则审核。
- 结果解释与 Artifact 一致。
- 权限不足时操作不可见或明确提示。

注意事项：

- 高风险审核操作需要二次确认或明确风险提示。

完成情况：未开始。

### 阶段注意事项

- 回测和优化必须强调可复现和可追溯。
- 规则池变更必须具备权限控制和审计。

### 阶段验收标准

- Web 可完成回测、报告、优化建议和规则审核。
- 结果有可下载 Artifact 和 Web 解释。
- 自动化测试覆盖参数非法、数据不足、无建议、审核权限和批量失败场景。
- 用户文档说明关键指标含义和审核影响。

---

## 13. Stage 7：设置、权限、运维与恢复闭环（P0）

### Stage 目标

- 让管理员通过 Web 管理配置、权限、健康检查、备份恢复、告警和运行诊断。
- 补齐真实用户交付所需的安全和运维能力。

### 阶段交付物

- 设置中心。
- 用户和角色权限。
- 系统健康检查。
- 备份恢复。
- 告警和审计。
- 运维文档和测试。

### 任务清单

#### [ ] WON-S7-001 P0 完成设置中心

目标：

让管理员能查看和配置第一版必要设置项，并理解每个设置项影响。

输入：

- Config Profile Service。
- Config Snapshot Service。
- `docs/WebUserManual.md` 设置章节。

输出：

- Web 设置中心。
- Settings API 增强。
- 设置项说明数据。
- 测试和文档更新。

能力要求：

- 展示配置项名称、用途、默认值、当前值来源、校验状态、风险等级。
- 支持保存允许 Web 管理的非敏感设置。
- 支持敏感配置只显示是否已配置，不显示原文。
- 支持配置校验。

前置依赖：Stage 1 完成。

可并行：`WON-S7-002`。

验收标准：

- 管理员能判断当前配置是否可运行核心 Workflow。
- 敏感信息不泄露。
- 配置变更可审计。

注意事项：

- 第一版不一定支持所有配置在线编辑，但必须能解释和校验所有关键配置。

完成情况：未开始。

#### [ ] WON-S7-002 P0 完成用户、角色和权限闭环

目标：

确保普通用户、管理员、高风险操作之间有明确权限边界。

输入：

- 现有认证和用户体系。
- Job Definition 风险等级。

输出：

- 权限策略。
- Web 用户管理页面或管理员入口。
- API 权限测试。

能力要求：

- 普通用户可运行低风险业务任务和查看自己有权限的结果。
- 管理员可管理设置、用户、备份恢复和高风险任务。
- 高风险操作具备权限校验和审计记录。

前置依赖：Stage 2 完成。

可并行：`WON-S7-001`、`WON-S7-003`。

验收标准：

- 未授权用户无法调用高风险 API。
- UI 不展示用户无权执行的关键操作，或展示明确无权提示。
- 权限测试覆盖主要角色。

注意事项：

- 权限不能只依赖前端隐藏按钮，后端必须强校验。

完成情况：未开始。

#### [ ] WON-S7-003 P0 完成备份、恢复和数据健康检查

目标：

让管理员能在 Web 中判断系统数据状态，并执行受控备份恢复。

输入：

- 现有 backup-data、restore-data、db-check、db-migrate、seed-data 能力。

输出：

- Ops Workflow。
- Backup/Restore Job Type。
- 数据健康检查页面。
- 运维测试。

能力要求：

- 支持创建备份、查看备份列表、恢复前校验、恢复执行记录。
- 支持数据库连接检查、迁移状态检查、关键表数据量检查。
- 恢复操作必须有高风险确认和权限校验。

前置依赖：Stage 2 完成。

可并行：`WON-S7-002`。

验收标准：

- 管理员可以通过 Web 完成备份和恢复流程。
- 恢复失败不会让 UI 显示成功。
- 备份文件和恢复记录可追溯。

注意事项：

- 恢复是高风险操作，必须记录审计日志并提示影响范围。

完成情况：未开始。

#### [ ] WON-S7-004 P0 完成告警、审计和运行诊断

目标：

让管理员能发现失败、慢任务、配置错误、数据质量异常和权限风险。

输入：

- Job Center。
- Config Snapshot。
- Data Quality Report。
- 审计日志。

输出：

- 告警规则。
- 运维看板。
- 审计日志页面或查询入口。
- 测试和文档更新。

能力要求：

- 展示最近失败任务、慢任务、外部依赖错误、数据质量异常。
- 展示关键操作审计记录。
- 支持按时间、用户、任务类型、风险等级筛选。

前置依赖：`WON-S7-002`、`WON-S7-003`。

可并行：无。

验收标准：

- 管理员能在 Web 中定位常见故障。
- 高风险操作都有审计记录。
- 告警信息能链接到 Job 详情或相关设置项。

注意事项：

- 第一版告警可以是 Web 内部告警列表，不强制接入外部通知系统。

完成情况：未开始。

### 阶段注意事项

- Stage 7 是真实交付的关键，不是附加功能。
- 没有配置校验、权限、备份恢复和故障诊断，系统不能交付给真实用户长期使用。

### 阶段验收标准

- 管理员可以通过 Web 完成配置校验、权限管理、备份恢复和故障定位。
- 敏感信息不泄露。
- 高风险操作有权限控制、确认和审计。
- 运维文档覆盖常见故障处理路径。

---

## 14. Stage 8：CLI 降级与兼容清理（P0）

### Stage 目标

- 将 CLI 从正式产品入口降级为开发调试薄入口。
- 清理或冻结旧 CLI 业务编排，避免双入口长期分叉。
- 确保 Web/API/Worker 是唯一正式用户入口。

### 阶段交付物

- Thin Dev CLI。
- CLI 退役说明。
- 旧入口兼容策略。
- 回归测试。

### 任务清单

#### [ ] WON-S8-001 P0 实现 Thin Dev CLI

目标：

保留必要开发调试能力，但 CLI 只能调用 Step 或 Workflow。

输入：

- Step Registry。
- Workflow Runner。
- 迁移矩阵。

输出：

- `dev run-step <step_name>`
- `dev run-workflow <workflow_name>`
- `dev list-steps`
- `dev list-workflows`
- CLI 测试。

前置依赖：Stage 6 完成。

可并行：`WON-S8-002`。

验收标准：

- Thin CLI 不直接调用业务内部实现。
- Thin CLI 输出 Job ID、状态和 Artifact 路径或链接。
- CLI 参数校验复用 Step/Workflow Schema。

注意事项：

- CLI 是开发工具，不写入普通用户文档作为正式使用路径。

完成情况：未开始。

#### [ ] WON-S8-002 P0 标记并限制旧 CLI 命令

目标：

避免用户继续依赖旧 CLI 正式能力。

输入：

- 迁移矩阵。
- 现有 CLI 命令。

输出：

- 旧 CLI 命令退役提示。
- 兼容命令映射。
- CLI 文档更新。

能力要求：

- 对已迁移命令显示 Web/API/Workflow 替代路径。
- 对短期保留命令标记原因和移除阶段。
- 对高风险旧命令限制执行或要求明确开发模式。

前置依赖：Stage 6 完成。

可并行：`WON-S8-001`。

验收标准：

- 迁移矩阵中所有旧 CLI 命令都有处理状态。
- 旧 CLI 不再作为正式验收路径。
- 用户文档不再引导普通用户使用旧 CLI。

注意事项：

- 不要一次性删除仍被测试或部署脚本依赖的 CLI；先兼容、警告、迁移，再移除。

完成情况：未开始。

#### [ ] WON-S8-003 P0 清理重复业务逻辑

目标：

收敛 CLI、API、Web、Job 中重复的业务编排。

输入：

- 现状审计。
- 迁移矩阵。
- 已完成业务切片。

输出：

- 重复逻辑清理 PR。
- 回归测试。
- 兼容说明。

前置依赖：`WON-S8-001`、`WON-S8-002`。

可并行：无。

验收标准：

- 同一个业务能力只有一个 Service/Step 实现。
- Web、API、CLI 都通过统一 Workflow/Step 调用。
- 删除或废弃的路径在迁移矩阵中标记完成。

注意事项：

- 清理重复逻辑时必须先有测试保护，避免破坏已交付业务切片。

完成情况：未开始。

### 阶段注意事项

- CLI 降级应在主要业务切片完成后执行，避免提前切断尚未迁移的能力。
- 所有兼容行为都必须有结束条件，避免永久双入口。

### 阶段验收标准

- 普通用户不需要 CLI 即可完成第一版核心功能。
- CLI 只调用 Step 或 Workflow。
- 旧 CLI 命令都有迁移、废弃或保留理由。
- 回归测试证明 Web/API/Worker 主入口可用。

---

## 15. Stage 9：Web 收敛、文档、E2E 与发布验收（P0）

### Stage 目标

- 完成第一版真实交付前的产品收敛。
- 确保 Web 页面、用户文档、API 文档、部署文档、测试结果和验收清单一致。
- 输出可交付版本。

### 阶段交付物

- 完整 Web 导航和页面收敛。
- 用户手册和管理员手册更新。
- API 文档更新。
- E2E 回归测试。
- 发布检查报告。

### 任务清单

#### [ ] WON-S9-001 P0 收敛 Web 信息架构和入口

目标：

让普通用户和管理员能从 Web 导航找到所有第一版核心功能。

输入：

- 已完成业务页面。
- `docs/WebUserManual.md`。

输出：

- Web 导航和页面收敛。
- 空状态、加载态、错误态、权限态统一。
- Web 可用性检查。

前置依赖：Stage 8 完成。

可并行：`WON-S9-002`。

验收标准：

- 所有第一版功能都有明确 Web 入口。
- 用户不需要知道内部 Step 或 CLI 名称即可操作。
- 关键页面在桌面端和移动端可用。

注意事项：

- 不为了追求页面数量拆散主流程；应按用户任务组织入口。

完成情况：未开始。

#### [ ] WON-S9-002 P0 更新用户文档、API 文档和覆盖矩阵

目标：

确保文档与最终实现一致，用户看文档即可正常使用系统。

输入：

- `docs/WebUserManual.md`
- `docs/APIReference.md`
- `docs/Web-UserManual-Coverage.md`
- 已完成 Web/API/Workflow。

输出：

- 更新后的用户手册。
- 更新后的 API 文档。
- 更新后的覆盖矩阵。
- 发布说明。

前置依赖：Stage 8 完成。

可并行：`WON-S9-001`、`WON-S9-003`。

验收标准：

- 每个主要功能都说明用途、操作方法、设置项、结果查看和结果含义。
- API 文档覆盖 Web 依赖的主要接口。
- 覆盖矩阵中不存在第一版功能缺文档的问题。

注意事项：

- 文档必须面向普通用户和管理员，不写成开发者内部说明。

完成情况：未开始。

#### [ ] WON-S9-003 P0 完成端到端回归测试

目标：

验证第一版核心功能从 Web 到 Job 到 Artifact 到文档说明全部可用。

输入：

- 所有 P0 Stage 产物。
- `docs/WebOnly-V1-Acceptance.md`

输出：

- E2E 测试用例。
- 回归测试报告。
- 失败项修复记录。

E2E 覆盖：

- 登录和权限。
- 设置校验。
- 文章处理。
- 市场数据准备。
- 策略盘前运行。
- 策略盘后复盘。
- 回测和报告。
- 优化建议和规则审核。
- Job 取消、重试、失败查看。
- Artifact 下载。
- 备份恢复。

前置依赖：Stage 8 完成。

可并行：`WON-S9-002`。

验收标准：

- 所有第一版 P0 用户流程通过。
- 失败用例均有修复或明确阻断记录。
- 回归命令和人工验收步骤记录在发布检查报告中。

注意事项：

- 不能只跑单元测试代替 E2E。
- 如果 E2E 依赖外部数据源，必须提供可控测试数据或 mock 策略。

完成情况：未开始。

#### [ ] WON-S9-004 P0 完成发布前检查和交付包

目标：

形成可以交付真实用户部署和使用的版本。

输入：

- E2E 回归报告。
- 用户文档。
- 运维文档。
- 发布配置。

输出：

- `docs/WebOnly-V1-Release-Checklist.md`
- 部署和回滚说明。
- 已知问题清单。
- 第一版发布说明。

发布检查必须覆盖：

- 数据库迁移。
- 配置项校验。
- 敏感信息清理。
- 权限和默认管理员。
- 备份恢复验证。
- 核心 Workflow 验证。
- 日志和 Artifact 目录权限。
- 回滚方案。

前置依赖：`WON-S9-001`、`WON-S9-002`、`WON-S9-003`。

可并行：无。

验收标准：

- 发布检查清单全部通过或有明确风险接受记录。
- 管理员可以按文档完成部署、验证、恢复和日常使用。
- 第一版不依赖未完成的 Future 项。

注意事项：

- 发布前必须清理示例密钥、cookie、临时数据和调试输出。

完成情况：未开始。

### 阶段注意事项

- Stage 9 是交付阶段，不允许再引入大规模架构变化。
- 所有验收以用户实际可操作为准，不以代码完成为准。

### 阶段验收标准

- `docs/WebOnly-V1-Acceptance.md` 中的 P0 验收项全部通过。
- 用户文档、API 文档、运维文档与系统一致。
- E2E 回归通过。
- 发布检查报告确认系统可交付真实用户使用。

---

## 16. Future：第一版之后优化方向（P2）

以下方向不阻塞第一版交付，只在 Stage 0 到 Stage 9 全部完成并稳定运行后推进。

### [~] WON-F-001 P2 多 Config Profile 和环境切换

目标：

支持开发、测试、生产、不同账户或不同数据源的多配置档管理。

价值：

- 降低多环境切换成本。
- 支持不同用户或团队使用不同配置。
- 提升配置审计和回滚能力。

前置条件：

- 第一版 Config Snapshot 已稳定运行。

完成情况：未来优化。

### [~] WON-F-002 P2 分布式 Worker 和队列调度

目标：

将 Job 执行从单进程或本地 Worker 扩展到可水平扩展的队列执行模式。

价值：

- 支持更大规模抓取、回测和优化任务。
- 降低长任务对 Web 服务的影响。
- 支持任务优先级和资源隔离。

前置条件：

- 第一版 Job/Workflow/Step 契约稳定。

完成情况：未来优化。

### [~] WON-F-003 P2 高级可观测性和外部告警

目标：

接入指标、追踪、日志聚合和外部通知渠道。

价值：

- 更快定位生产问题。
- 支持任务失败、数据异常、外部依赖异常主动通知。

前置条件：

- 第一版内部告警和审计已稳定。

完成情况：未来优化。

### [~] WON-F-004 P2 Step Replay 和数据血缘图

目标：

支持在 Web 中重放单个 Step，并展示数据从输入到产物的血缘关系。

价值：

- 提升调试效率。
- 方便解释策略结果和回测结果来源。

前置条件：

- 第一版 Artifact Metadata 和 Step Timeline 完整可靠。

完成情况：未来优化。

### [~] WON-F-005 P2 更细粒度 RBAC 和审批流

目标：

支持按功能、数据范围、任务风险、规则池变更类型配置更细权限和审批流程。

价值：

- 适配多人协作和更严格治理场景。
- 降低高风险操作误用概率。

前置条件：

- 第一版角色权限和审计记录稳定。

完成情况：未来优化。

---

## 17. 总体验收口径

当 Stage 0 到 Stage 9 全部完成后，必须满足：

1. Web/API/Worker 是正式入口，CLI 是开发调试薄入口。
2. 普通用户可以通过 Web 完成文章、市场、策略、回测、优化、规则审核和结果查看。
3. 管理员可以通过 Web 完成设置、权限、备份恢复、健康检查、告警和审计。
4. 每个核心 Workflow 都能通过 Job Center 追踪状态、Step Timeline、日志、错误和产物。
5. 每个产物都有来源、解释、权限和下载路径。
6. 每个设置项都有用途、默认值、校验和敏感信息保护。
7. 第一版用户文档与最终实现一致。
8. 端到端回归和发布检查通过。
9. Future 项全部不影响第一版可交付性。

