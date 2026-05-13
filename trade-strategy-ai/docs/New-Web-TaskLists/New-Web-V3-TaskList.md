# New-Web-V3-TaskList

> V3 目标：在 V2 的正式 Profile、正式 Web 工作台、市场数据与策略链路基础上，完成回测优化、规则池审核、运维恢复、权限审计和最终交付级验收，使项目达到完整用户需求闭环。

## 0. V3 范围

### V3 必须交付

- 回测中心完整纵向切片。
- 优化候选版本与规则验真闭环。
- 规则池审核与回写闭环。
- 管理员运维：健康检查、备份恢复、运行日志、基础告警。
- 权限、审计、敏感配置治理。
- 最终 Web UI 收口：用户可以完成完整主流程。
- 部署、运维、备份、恢复、发布文档齐全。

### V3 可以延后

- 多租户 SaaS 化。
- 分布式 Worker。
- 高级可观测性平台。
- 高级调度 DSL。
- 高级可视化图表。

## 1. AI Implementation Rules

- 每个业务切片必须使用 V1/V2 已建立的 Runtime Contract、ProfileResolver、JobService、WorkflowService、StepRegistry、ArtifactService。
- 不允许直接调用旧 CLI 作为正式实现。
- 不允许新增平行回测 Job 模型或规则池模型。
- 高风险操作必须有权限、确认、审计、回滚或恢复说明。

## 2. Stage V3-0：V2 验收与最终差距冻结（P0）

#### [ ] NWV3-S0-001 P0 V2 回归验收

目标：确认 article、market、strategy、profile、web IA 均稳定。

输出：
- docs/New-Web-V3-Current-State.md

#### [ ] NWV3-S0-002 P0 最终交付差距矩阵

输出：
- docs/New-Web-Final-Gap-Matrix.md

字段：
- 用户需求
- 当前状态
- 缺失能力
- 对应 Task
- 是否阻断最终交付
- 验收方式

## 3. Stage V3-1：回测中心纵向切片（P0）

#### [ ] NWV3-S1-001 P0 定义 Backtest PipelineSpec

输出：
- src/pipelines/backtest/spec.py
- tests/pipelines/test_backtest_spec.py

必须覆盖：
- backtest-run
- backtest-validate-rules
- backtest-reproducibility-check

#### [ ] NWV3-S1-002 P0 接入回测运行 Workflow

目标：Web/API 可按 trader_id、date_from、date_to、strategy_version_id、mode 执行回测。

验收标准：
- Job 记录 ProfileSnapshot。
- Artifact 包含回测结果、指标摘要、交易明细引用、错误说明。
- 支持失败重试和可复现性说明。

#### [ ] NWV3-S1-003 P0 接入规则验真 Workflow

目标：Web/API 可对规则执行验真并生成报告。

验收标准：
- 报告可在 Artifact 页面解释。
- 失败规则、无效样本、数据缺失有结构化错误。

#### [ ] NWV3-S1-004 P0 接入可复现性检查 Workflow

目标：支持重复运行回测并比对 fingerprint。

验收标准：
- 输出 fingerprint diff。
- 不一致时给出原因分类。

#### [ ] NWV3-S1-005 P0 实现 Backtest Web 页面

页面能力：
- 创建回测。
- 查看历史。
- 查看指标和报告。
- 下载 Artifact。
- 启动可复现性检查。

## 4. Stage V3-2：优化候选版本与规则池闭环（P0）

#### [ ] NWV3-S2-001 P0 定义 Optimize PipelineSpec

覆盖：
- optimize-create-candidate
- candidate version artifact
- parent strategy linkage
- adjustment input

#### [ ] NWV3-S2-002 P0 实现候选版本生成 Workflow

验收标准：
- 可从规则调整生成候选版本。
- 产物包含 diff、父版本、风险提示。

#### [ ] NWV3-S2-003 P0 定义 RulePool PipelineSpec

覆盖：
- rule-pool-backtest
- rule review
- approval / reject
- audit trail

#### [ ] NWV3-S2-004 P0 实现规则池回测与审核 Workflow

验收标准：
- 高风险操作需要 admin 权限和确认。
- 审核结果有审计记录。
- 回写失败可恢复。

#### [ ] NWV3-S2-005 P0 实现 Rule Pool Web 页面

页面能力：
- 查看候选规则。
- 运行规则池回测。
- 审核通过/拒绝。
- 查看影响范围和历史。

## 5. Stage V3-3：管理员运维与恢复闭环（P0）

#### [ ] NWV3-S3-001 P0 数据健康检查

目标：管理员可以查看数据库、Artifact、Profile、Job Queue、外部依赖健康状态。

输出：
- src/services/health_service.py
- api/routers/ui/health.py
- web Admin Health 页面

#### [ ] NWV3-S3-002 P0 备份恢复正式化

目标：备份和恢复从 Demo 能力升级为可交付管理员能力。

要求：
- backup-data / restore-data 使用 Job Center。
- 恢复操作必须 admin + confirmation。
- Artifact 记录备份包元数据。
- 恢复前生成风险摘要。

#### [ ] NWV3-S3-003 P0 运行日志与审计中心

目标：管理员能查看关键操作、Job 审计、Profile 变更、规则池审核记录。

#### [ ] NWV3-S3-004 P1 基础告警

目标：失败 Job、配置缺失、外部依赖失败、数据延迟可在 Admin 页面提示。

## 6. Stage V3-4：权限、安全与审计收口（P0）

#### [ ] NWV3-S4-001 P0 权限矩阵最终化

输出：
- docs/PermissionMatrix.md

角色：
- viewer
- operator
- admin

覆盖：
- Job 创建
- Job 取消/重试
- Profile 修改
- 备份恢复
- 规则审核
- Artifact 下载

#### [ ] NWV3-S4-002 P0 敏感信息治理

验收标准：
- API、日志、Artifact、Job params、审计记录无 secret 原文。
- 有自动化测试覆盖敏感字段脱敏。

#### [ ] NWV3-S4-003 P0 高风险操作确认机制

覆盖：
- restore-data
- db-migrate
- rule-pool-backtest
- profile activation
- destructive admin operation

## 7. Stage V3-5：最终 Web UI 收口（P0）

#### [ ] NWV3-S5-001 P0 Dashboard 最终化

展示：
- 今日任务
- 数据健康
- 最近失败
- 最近产物
- 待审核规则
- 快捷入口

#### [ ] NWV3-S5-002 P0 Workflows 页面最终化

要求：
- 所有正式 Workflow 可从 Web 触发。
- 高风险 Workflow 有确认说明。
- Workflow 表单由后端 schema 驱动或与后端 schema 一致。

#### [ ] NWV3-S5-003 P0 Artifacts 页面最终化

要求：
- 支持按 Job、Workflow、类型、日期筛选。
- 支持下载、预览、解释说明。
- 不暴露服务器绝对路径。

#### [ ] NWV3-S5-004 P1 UI 体验一致性

包括：
- loading
- empty state
- error state
- permission denied
- retry action
- form validation

## 8. Stage V3-6：最终文档、部署与发布验收（P0）

#### [ ] NWV3-S6-001 P0 用户手册最终版

输出：
- docs/WebUserManual.md

必须覆盖：
- 文章处理
- 市场数据
- 策略运行
- 回测
- 规则池
- Job Center
- Artifact
- Profile
- 管理员运维

#### [ ] NWV3-S6-002 P0 API 文档最终版

输出：
- docs/APIReference.md

#### [ ] NWV3-S6-003 P0 部署文档

输出：
- docs/DeploymentGuide.md

覆盖：
- 环境变量
- DB migration
- Worker 启动
- Web 构建
- Profile 初始化
- 备份恢复

#### [ ] NWV3-S6-004 P0 运维手册

输出：
- docs/OperationsGuide.md

覆盖：
- 常见失败
- Job 恢复
- 配置回滚
- 备份恢复
- 数据健康检查

#### [ ] NWV3-S6-005 P0 最终 E2E 验收

覆盖主流程：
- 新建/导入 Profile
- 文章处理
- 市场数据
- 策略运行
- 回测
- 规则池审核
- 备份恢复演练
- Artifact 下载
- 权限校验
- 失败恢复

#### [ ] NWV3-S6-006 P0 Final Release Checklist

发布阻断项：
- 用户主流程任一无法通过 Web 完成。
- 任一长任务绕过 Job Center。
- secret 泄露。
- Artifact 不可追踪。
- Profile 无快照或不可回滚。
- 高风险操作无确认和审计。
- 文档与实现不一致。
