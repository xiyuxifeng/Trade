# Web S9-003 Operational Dashboard Design

> **For agentic workers:** this design defines the Stage 9 operational dashboard work. Keep `Overview` as a light entry page and extend the existing `Data Health` route into a dedicated operational dashboard surface. Do not fold these metrics back into the homepage.

**Goal:** 为 `trade-strategy-ai` 增加一个独立的运维 Dashboard 页面，用来展示最近失败任务、任务耗时、数据新鲜度、告警摘要，以及可追踪到 `request/job` 的日志线索；同时保持 `Overview` 只承担轻量总览和快速跳转职责。

**Architecture:** 复用现有 `Data Health` 路由作为独立 Dashboard 承载页，保留 `Overview` 首页的轻量化布局。后端新增一个面向 Dashboard 的系统汇总接口，与基础健康检查接口分离：`/api/ui/v1/system/status` 继续负责 API、数据库、目录与配置加载检查；新增 `/api/ui/v1/system/dashboard` 提供失败任务、耗时统计、数据新鲜度、告警摘要和日志追踪入口。前端 Dashboard 页面同时消费这两类数据，但展示层级更偏向运维分析，而不是入口摘要。

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, React, TanStack Query, TypeScript, Vite, shadcn/ui.

## 1. 设计边界

- 不把 Dashboard 指标塞回 `Overview`，避免首页过重。
- 不新建第二个“监控中心”入口，复用现有 `Data Health` 页面和路由。
- 不引入新的消息队列或可观测性基础设施。
- 不做实时流式日志平台，只提供可追踪的关联线索和摘要。
- 不在本任务内改造整套日志系统，只补能支持 Dashboard 验收的最小数据链路。

## 2. 页面分工

### 2.1 `Overview`

保留为轻量入口页，继续展示：

- 系统状态
- 最近任务
- 最近产物
- 跳转提示

`Overview` 的职责是“看一眼系统是否正常”，不是“深入诊断系统问题”。

### 2.2 `Data Health` / Operational Dashboard

沿用现有 `/data-health` 路由作为独立 Dashboard 页面，页面内容升级为：

- 最近失败任务
- 最近完成任务耗时
- 数据新鲜度
- 告警摘要
- 日志追踪线索

页面目标是“定位问题与追踪异常”，不是单纯展示一个报告文件。

## 3. 推荐方案

### 3.1 推荐方案：双接口 + 单 Dashboard 页

后端保留 `/status`，新增 `/dashboard`；前端 `DataHealthPage` 改造成运维 Dashboard，顶部保留简短健康提示，主体展示运维指标卡、失败任务表、耗时摘要和告警区块。

优点：

- 接口职责清晰，基础健康与运维分析分开。
- 页面层级明确，首页不会被监控指标挤爆。
- 后续加更多分析块时，不会破坏 `Overview`。

缺点：

- 需要新增一个后端汇总接口。
- 需要更新现有 `Data Health` 页面文案和测试。

### 3.2 备选方案：把所有指标塞进 `/status`

优点：

- 接口更少。
- 实现最快。

缺点：

- `status` 会变成大而杂的混合接口。
- 基础健康检查和分析数据耦合，后续很难维护。

### 3.3 不推荐方案：新建一个完全独立的 `/dashboard` 路由

优点：

- 路由命名最直观。

缺点：

- 需要同时维护 `Data Health` 与 `Dashboard` 两个入口的迁移和导航关系。
- 现有信息架构里已经有一个合适的承载页，重复造路由成本高。

## 4. 后端设计

### 4.1 系统服务扩展

在 `src/services/system_service.py` 中增加一个面向 Dashboard 的聚合方法，建议命名为 `build_dashboard_summary()` 或等价方法。该方法负责读取以下信息：

- API / 数据库健康状态
- Job Worker 最近心跳时间
- 最近失败任务列表
- 最近完成任务耗时统计
- 数据新鲜度概览
- 告警摘要
- 日志关联线索

其中：

- 失败任务至少返回任务标识、任务类型、状态、失败时间、错误摘要、关联 `request_id` 或 `job_id`
- 耗时统计至少返回最近完成任务列表和基础统计值
- 数据新鲜度至少返回每个关键数据源的最新更新时间、年龄和状态
- 告警摘要至少返回严重级别计数和最新告警文本

### 4.2 API 路由

在 `api/routers/ui/system.py` 中保留：

- `GET /api/ui/v1/system/status`

新增：

- `GET /api/ui/v1/system/dashboard`

`status` 继续作为机器可读健康检查，`dashboard` 提供面向人类运维的汇总视图。两者都保留 `X-API-Key` 鉴权。

### 4.3 数据来源原则

- 不新增数据库表。
- 优先复用现有 Job、Audit Event、Alert、Freshness 相关查询。
- 如现有服务缺少聚合方法，只补最小查询方法，不重构底层模型。
- 对日志追踪，只暴露能串联 `request_id` / `job_id` 的字段，不把完整日志内容塞进 API。

## 5. 前端设计

### 5.1 页面结构

`web/src/pages/data-health/index.tsx` 继续作为独立页面入口，但页面文案和内容升级为 Operational Dashboard。

建议布局：

1. 顶部状态条
   - 显示 API、数据库、Worker 心跳的简短摘要
2. KPI 卡片区
   - 最近失败任务数
   - 平均耗时 / P95 耗时
   - 最近数据新鲜度等级
   - 当前告警数
3. 失败任务表
   - 任务名、状态、失败时间、错误摘要、追踪入口
4. 耗时区块
   - 最近任务列表或简短统计条
5. 数据新鲜度区块
   - 按数据源列出更新时间和过期程度
6. 告警摘要区块
   - 严重级别、最新告警、确认状态

### 5.2 视觉约束

- 保持现有深色数据密集风格，不切换到完全不同的视觉语言。
- 使用清晰的 KPI 卡、表格和摘要区块，不做花哨装饰。
- 失败态、空态、加载态都要局部处理，不让整个页面被单点失败打断。
- 维持与 `Overview` 相同的字体与基础组件体系，避免风格分裂。

### 5.3 导航约束

- `Overview` 继续作为首页。
- `Data Health` 继续保留在导航中，作为独立 Dashboard 入口。
- 如后续决定将导航标签改为 `Dashboard`，应作为单独任务处理，不在本任务内同时改路由和语义。

## 6. 错误处理

- `/dashboard` 接口失败时，页面仍应展示基础健康块或明确错误提示。
- 失败任务、耗时统计、新鲜度、告警区块应支持局部空态。
- 如果某类指标暂时没有数据，页面应显示“暂无数据”而不是空白。
- 任何聚合失败都不能影响 `Overview` 和 `/status` 的可用性。

## 7. 测试策略

### 7.1 后端测试

- 系统 Dashboard API 的响应结构测试。
- Dashboard 聚合服务的单测，覆盖失败任务、耗时统计、新鲜度和告警摘要的返回。
- 现有 `status` 接口回归测试，确保基础健康检查未被破坏。

### 7.2 前端测试

- `DataHealthPage` 路由可达测试。
- Dashboard 内容展示测试，覆盖：
  - 有数据时渲染 KPI、失败任务和告警摘要
  - 空状态
  - API 失败状态
- `Overview` 回归测试，确保页面仍保持轻量。

### 7.3 回归验证

- `pytest` 通过后端相关测试。
- `vitest` 通过前端页面和 API client 测试。
- `build`、`typecheck`、`lint` 保持全绿。

## 8. 验收标准

- `Overview` 保持轻量，不新增运维分析块。
- 独立 Dashboard 页面可展示最近失败任务、任务耗时、数据新鲜度、告警摘要和日志追踪线索。
- 基础健康检查仍可通过 `status` 接口获取。
- Dashboard 页面在加载、空态和错误态下都有明确反馈。
- 文档、任务列表和实现代码保持一致。

## 9. 非目标

- 不做实时日志检索引擎。
- 不做告警订阅、通知推送或 WebSocket 实时刷新。
- 不做新的权限模型。
- 不把所有监控数据迁移到单一超级接口。

