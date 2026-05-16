# UI-V2-004 Dashboard 首页与告警详情页设计

## 背景

`UI-V2-004` 的目标是把 V2 工作台的首屏做成正式交付版入口，而不是继续堆 Demo 式信息海报或技术入口集合。

当前仓库里已经有可复用的基础能力：

- [`web/src/routes/overview.tsx`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/routes/overview.tsx) 作为 Dashboard/Overview 的承载页
- [`web/src/features/system-status/system-status-panel.tsx`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/features/system-status/system-status-panel.tsx) 提供系统状态摘要
- [`web/src/components/status/recent-jobs-panel.tsx`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/components/status/recent-jobs-panel.tsx) 提供最近任务
- [`web/src/components/status/recent-artifacts-panel.tsx`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/components/status/recent-artifacts-panel.tsx) 提供最近产物
- [`web/src/features/alerts/alerts-center.tsx`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/features/alerts/alerts-center.tsx) 提供告警历史、acknowledge、resolve 等能力
- [`web/src/lib/api/alerts.ts`](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/web/src/lib/api/alerts.ts) 提供告警历史和动作 API

本任务不是重写这些能力，而是把它们组织成更适合最终用户的正式工作台结构。

## 目标

1. Dashboard 首屏优先回答“系统现在是否正常”。
2. 首屏其次回答“最近发生了什么”。
3. 首屏最后才给轻量快捷入口，不让入口压过状态信息。
4. 重点告警只展示摘要，点击后进入新的告警详情页。
5. 告警详情页提供完整上下文，不污染 Dashboard 首屏。
6. 全部文案保持浅色中文工作台风格，和 `UI-V2-002` 一致。

## 非目标

- 不做复杂主题系统。
- 不把业务 API 调用放进 Layout。
- 不新增 CLI 命令。
- 不把告警规则编辑做进本任务。
- 不改现有告警数据模型和后端规则逻辑。
- 不把 Dashboard 做成“功能海报”或“导航页”。

## 设计原则

### 1. 系统状态优先

Dashboard 首屏必须先展示系统整体健康状态，再展示任务和产物。

### 2. 告警摘要与详情分离

首页只展示重点告警摘要，点击后进入独立详情页查看上下文和处理记录。

### 3. 中文优先

用户可见文案尽量使用中文，保留必要技术名词：

- Job
- Workflow
- Artifact
- Profile

### 4. 浅色正式工作台

延续 `UI-V2-002` 的浅色中文工作台风格：

- 低饱和蓝灰主色
- 轻边框
- 弱阴影
- 克制的状态色
- 数据卡片密度高但不压迫

## 页面结构

## 1. Dashboard 首页

### 1.1 顶部大总览

首屏顶部展示一排总览卡，回答系统当前状态：

- 系统健康
- 今日运行
- 失败任务数
- 最近产物数
- Profile 状态摘要
- Market 状态摘要

这些卡片的职责是“先让用户知道系统是否正常”，不承载深操作。

### 1.2 重点告警状态栏

在总览卡下方或右上角放一条重点告警状态栏，展示 3 到 5 条最重要的告警摘要。

每条摘要至少包含：

- 告警标题
- 严重级别
- 发生时间
- 关联对象简写

交互：

- 点击摘要跳转到新的告警详情页
- 若无告警，显示友好的空态说明

### 1.3 双栏详情

首屏主内容采用双栏布局：

- 左栏：最近失败任务
- 右栏：最近产物或最近完成任务

左栏优先帮助用户发现失败和异常。
右栏优先帮助用户快速确认系统最近输出了什么。

### 1.4 底部轻量辅助区

底部可放少量快捷入口，但不得抢占首屏注意力。

可保留的入口包括：

- Jobs
- Market Data Workspace
- Profiles
- Artifact Center

这些入口只能作为辅助，不作为首屏主视觉。

## 2. 告警详情页

### 2.1 页面目标

告警详情页用于承接 Dashboard 的重点告警点击，提供完整上下文与处理动作。

### 2.2 页面结构

顶部：

- 告警标题
- 严重级别
- 当前状态
- 发生时间

主内容区：

- 告警消息
- 原始上下文摘要
- 变化时间线
- 处理记录

右侧信息栏：

- 关联 Job
- 关联 Workflow
- 关联 Artifact
- 标签
- 来源

底部操作区：

- acknowledge
- resolve
- 返回 Dashboard

### 2.3 交互规则

- 告警详情页默认展示最近相关上下文。
- 若告警已确认或已解决，状态要明确显示。
- acknowledge / resolve 成功后应刷新本页和相关摘要区域。
- 若告警不存在，显示结构化错误页或空态页，不跳回首页。

## 数据流

### Dashboard 首页

Dashboard 首页只消费已有的查询型 API：

- 系统状态 API
- 最近 Job 列表 API
- 最近 Artifact 列表 API
- 告警历史 API 的摘要查询

首页不直接做业务动作。

### 告警详情页

告警详情页复用现有告警历史 API 和动作 API：

- `GET /alerts/history`
- `GET /alerts/history/{recordId}`
- `POST /alerts/{recordId}/acknowledge`
- `POST /alerts/{recordId}/resolve`

页面只负责展示和触发动作，不引入新的告警规则编辑流程。

## 状态处理

每个数据块都必须支持：

- Loading
- Empty
- Error
- Retry
- Success

告警详情页还必须支持：

- Not found
- Permission denied
- Acknowledge failed
- Resolve failed

## 视觉要求

沿用 `UI-V2-002` 风格：

- 浅色背景
- 蓝灰主视觉
- 低饱和告警色
- 轻边框与弱阴影
- 中文优先
- 数据密度高但不拥挤

告警的视觉优先级应当明确：

- 严重告警：红
- 警告告警：橙黄
- 信息告警：蓝灰
- 正常状态：绿

## 实现边界

- Dashboard 页面可继续承载在 `overview` 路由或其 canonical 页面上。
- 告警详情页应作为独立新页面接入，不使用抽屉替代。
- 现有 `AlertsCenter` 可以保留为告警历史主页面，Dashboard 仅展示摘要和跳转。
- 不新增 CLI 命令。
- 不把权限逻辑硬写进页面内部。
- 不把业务 API 调用塞进 Layout。

## 验收标准

1. Dashboard 首屏能清楚展示系统总览。
2. Dashboard 能清楚展示重点告警摘要。
3. 点击重点告警能进入新的告警详情页。
4. 告警详情页能展示完整上下文和处理动作。
5. 首屏的失败任务和最近产物都可正常查看。
6. 空数据、错误数据、权限不足时都有友好状态。
7. 页面语言以中文为主，风格与 `UI-V2-002` 一致。
8. 不新增 CLI 产品入口。
9. 不引入新的告警规则编辑能力。

## 任务拆分建议

如果后续进入实现，建议拆成两个阶段：

1. Dashboard 首页重排与重点告警摘要接入。
2. 告警详情页新路由、新页面与动作回流。

这样可以先把首屏收口，再补详情页，不会一次性扩散到整套告警系统。
