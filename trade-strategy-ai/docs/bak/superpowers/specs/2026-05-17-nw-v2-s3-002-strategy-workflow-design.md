# NW-V2-S3-002 Strategy Workflow Design

## 1. 背景

`NW-V2-S3-002` 的目标不是继续堆 Demo，也不是强化 CLI，而是把 V2 的策略工作流做成面向最终交付的 Web 能力闭环。

当前已完成：

- `UI-V2-006 Strategy Workspace`
- `UI-V2-007 Artifact Center`
- `UI-V2-008 Web UI 错误恢复体验`
- `NW-V2-S3-001 strategy PipelineSpec`

这意味着 Web 侧的正式入口、统一错误组件、策略规范契约已经到位。当前任务需要补的是“真的能跑起来，并且结果能看懂”的主链路闭环。

## 2. 目标

本任务只覆盖 strategy 主链路的可交付闭环：

- Web/API 可以触发 `strategy-build`
- Web/API 可以触发 `run-pre-market`
- Web/API 可以触发 `run-after-close`
- Job Detail 可以解释策略任务结果
- Artifact Center 可以检索策略产物

## 3. 非目标

本任务不做以下内容：

- 不做 `UI-V2-009 UI Component Kit`
- 不把策略工作流扩展成新的 CLI 产品面
- 不在前端计算策略结果
- 不在前端推断排名、规则优先级或收益
- 不新增独立的策略文件浏览器
- 不把 Job Detail 再拆成新页面

## 4. 当前基线

### 4.1 已有策略入口

`/strategies` 已经是正式策略工作台，支持：

- trader/date/profile 选择
- `strategy-build`
- `run-pre-market`
- `run-after-close`
- 最近策略任务
- 版本列表
- 产物解释入口

### 4.2 已有策略规范

`NW-V2-S3-001` 已定义 canonical `PipelineSpec`，并明确：

- `strategy-build`
- `run-pre-market`
- `run-after-close`
- UI 绑定关系

### 4.3 已有产物中心

`/artifacts` 已是正式 Artifact Center，支持：

- `artifact kind`
- `job_type`
- `date`
- `job_id`
- 预览 / 下载
- 来源 Job 跳转

### 4.4 已有统一错误恢复

`UI-V2-008` 已提供共享 `ErrorState`，可用于：

- validation error
- permission denied
- config missing
- provider unavailable
- data empty
- artifact missing
- job failed
- network error

## 5. 推荐方案

推荐按“先执行闭环，再解释结果，再补检索”的顺序实现。

### 5.1 子块 A: Strategy Workflow 执行闭环

让三种策略动作都走同一套 Web/API -> Job -> Runner -> Service 的正式链路。

### 5.2 子块 B: Job Detail 结果解释闭环

让 Job Detail 能清楚展示策略任务的报告、证据包、失败原因和产物跳转。

### 5.3 子块 C: Artifact Center 策略产物检索

让策略产物能按 job type / date / kind 被检索，并能回到来源 Job。

### 5.4 子块 D: 验收收口

把 API contract、UI 回归、TaskList、daily-session、daily-report 一起收口。

## 6. 具体设计

### 6.1 Strategy Workflow 执行闭环

#### 设计原则

- Web 提交仍然是正式入口
- 运行结果由 Job 体系承接
- `strategy-build` 不再是前端按钮幻觉，而是后端可执行任务
- `run-pre-market` / `run-after-close` 复用现有 workflow / runner 体系

#### 处理方式

- `strategy-build`
  - 保持在 Job 体系内执行
  - 通过 `StrategyService.build_strategy_version()` 生成正式策略版本
  - 结果写入 Job / Strategy Version 的正式数据结构

- `run-pre-market`
  - 继续走已存在的盘前工作流映射
  - 由 JobRunner / WorkflowService 负责执行

- `run-after-close`
  - 继续走已存在的盘后工作流映射
  - 由 JobRunner / WorkflowService 负责执行

#### 结果约束

- 前端不直接调度后端内部函数
- 不新增 CLI 旁路
- 不引入新的策略执行存储事实源

### 6.2 Job Detail 结果解释闭环

#### 设计原则

- Job Detail 负责解释，不负责执行
- 策略任务的结果和失败原因必须可读
- 报告和证据包必须从后端真实数据中来

#### 页面行为

- 成功任务：
  - 显示执行参数
  - 显示策略版本摘要
  - 显示报告 / 证据包 / 相关产物
  - 显示来源 Config Snapshot

- 失败任务：
  - 显示共享 `ErrorState`
  - 显示技术详情折叠
  - 显示重试建议
  - 显示返回任务列表 / 前往设置 / 前往配置管理等动作

#### 数据来源

- Job 结果来自 Job API
- 策略版本来自 StrategyService
- 报告 / 证据包来自 Artifact API
- 失败状态通过统一错误恢复层解释

### 6.3 Artifact Center 策略产物检索

#### 设计原则

- 产物中心继续是正式 Web 检索入口
- 只使用后端返回的 artifact 元数据
- 不暴露服务器绝对路径
- 不把 artifact 简化成单纯文件下载

#### 检索策略

- 按 `job_type` 过滤
- 按 `date` 过滤
- 按 `kind` 过滤
- 按 `job_id` 过滤

#### 策略相关产物

重点检索以下来源：

- `strategy-build`
- `run-pre-market`
- `run-after-close`

### 6.4 错误处理

#### 统一原则

- 页面级错误使用共享 `ErrorState`
- 技术详情默认折叠
- 用户建议单独展示
- 可恢复错误必须提供明确动作

#### 策略相关错误

- `strategy-build` 提交失败
- `run-pre-market` 提交失败
- `run-after-close` 提交失败
- Job 详情找不到
- Job 失败但产物缺失
- Artifact 缺失或过期

#### 期望动作

- 返回当前页面
- 返回任务列表
- 前往设置
- 前往配置管理
- 打开产物中心

## 7. 实施边界

本任务只改与 strategy workflow 闭环直接相关的部分：

- `src/services/strategy_service.py`
- `src/services/job_runner.py`
- `src/services/workflow_service.py`
- `src/services/job_registry.py`
- `src/services/artifact_service.py`
- `api/routers/ui/jobs.py`
- `api/routers/ui/artifacts.py`
- `web/src/pages/jobs/JobDetailPage.tsx`
- `web/src/features/strategy-workspace/*`
- `web/src/features/market-workspace/*` 仅在必须时微调策略相关产物展示

不把 `UI-V2-009` 的组件平台化工作混进来。

## 8. 测试策略

### 8.1 后端测试

覆盖：

- `strategy-build` 可以通过 Job 提交
- `run-pre-market` 可以通过 workflow 执行
- `run-after-close` 可以通过 workflow 执行
- Job Detail 产物和报告可读
- Artifact 查询可以按 `job_type` / `date` 找到策略产物

### 8.2 前端测试

覆盖：

- 策略工作台三种动作的确认弹窗与提交
- Job Detail 的结果和错误态
- Artifact Center 的策略产物筛选和来源跳转
- 错误状态使用共享 `ErrorState`

### 8.3 验收测试

至少覆盖：

- 成功提交策略版本
- 成功提交盘前/盘后
- 失败时可解释
- 产物可回溯来源 Job

## 9. 验收标准映射

### 9.1 Web/API 可触发策略版本构建

由 `strategy-build` 的提交与执行测试保证。

### 9.2 Web/API 可触发盘前/盘后

由 `run-pre-market` / `run-after-close` 的 workflow 映射与测试保证。

### 9.3 Job Detail 可展示报告和证据包

由 Job Detail 页面与相关 API / artifact 取数测试保证。

### 9.4 Artifact Center 可检索策略产物

由 ArtifactService 过滤与 `/artifacts` 页面测试保证。

## 10. 风险与约束

- 现有仓库里还有历史类型错误，全量 typecheck 不能作为本任务唯一验收凭据。
- 本机浏览器实机验收可能受 Node 版本影响，需要以 Vitest / API contract 为主。
- 如果 `strategy-build` 的 runtime 结果结构再扩展，需要同步更新 Job Detail 与 Artifact 解释层，但不应回退到 CLI 旁路。

## 11. 结论

`NW-V2-S3-002` 应当先做执行闭环，再补 Job Detail 和 Artifact Center 的结果解释与检索，最后做验收收口。这样能够保持 V2 的正式 Web 交付定位，并避免把 `UI-V2-009` 过早混入主链路。
