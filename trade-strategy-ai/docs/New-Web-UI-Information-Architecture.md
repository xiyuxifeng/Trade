# New-Web-UI-Information-Architecture

> 本文档定义 `trade-strategy-ai` 的正式 Web 信息架构。
> V2 的目标是面向最终交付的 Web 项目，不是继续把 Demo 功能堆在 CLI 上。

## 1. 设计原则

1. **正式入口优先。**
   - 顶层导航只展示正式工作台入口。
   - 新任务、新文档、新验收优先引用正式入口。
2. **兼容入口显式收口。**
   - 旧页面和临时页面保留为兼容层，但必须从正式 sidebar 中移除，不能继续作为主导航分组展示。
   - 兼容入口不得继续演进成第二套正式产品入口。
3. **占位必须明确。**
   - V2 / V3 预留模块必须展示清晰的 placeholder。
   - 不允许空白页，也不允许用旧 Demo 页面假装正式完成。
4. **UI 风格保持一致。**
   - 继续沿用 `UI-V2-002` 的浅色、白底、细边框、圆角卡片、低饱和蓝色强调风格。
   - 不在 IA 阶段引入新的视觉体系。

## 2. 顶层导航

### 2.1 正式入口

- 仪表盘
- 任务
- 工作流
- 文章
- 市场数据
- 数据集
- 策略
- 回测
- 规则池
- 产物
- 配置管理
- 管理中心
- 设置

### 2.2 兼容入口

- 快照
- 告警
- 报告
- 信号
- 画像
- 市场状态
- 导入
- 开盘
- 数据健康
- 策略实验室
- 回测中心
- 用户管理
- 运维

## 3. Canonical 路由

| 路由 | 说明 | 状态 |
| --- | --- | --- |
| `/dashboard` | 系统运行状态与入口摘要 | 正式 |
| `/jobs` | 长时间运行的任务中心 | 正式 |
| `/jobs/:jobId` | Job Detail 入口 | 正式 |
| `/workflows` | Workflow 目录入口 | 正式 |
| `/workflows/:workflowId/run` | Workflow 运行入口 | 正式 |
| `/articles` | article_pipeline 验收入口 | 正式 |
| `/market` | 市场快照浏览器 | 正式 |
| `/market/datasets` | 市场数据集浏览器 | 正式 |
| `/strategies` | 策略工作台 | 正式 |
| `/backtest` | 回测占位入口 | 预留 |
| `/rule-pool` | 规则池占位入口 | 预留 |
| `/artifacts` | Artifact Center | 正式 |
| `/profiles` | Profile 管理入口 | 正式 |
| `/admin` | 管理中心 | 正式 |
| `/settings` | 应用配置入口 | 正式 |

## 4. Legacy / Compatibility 路由

| 路由 | 说明 | 退役阶段 |
| --- | --- | --- |
| `/` | 旧首页跳转入口 | V3 |
| `/overview` | 旧概览跳转入口 | V3 |
| `/workflows/:workflowId` | 旧工作流详情入口 | V3 |
| `/legacy/*` | 兼容壳 | V3 |
| `/alerts` | 旧告警页 | V3 |
| `/alerts/:recordId` | 旧告警详情页 | V3 |
| `/reports` | 旧报告页 | V3 |
| `/snapshots` | 旧快照页 | V3 |
| `/signals` | 旧信号页 | V3 |
| `/persona` | 旧画像页 | V3 |
| `/market-state` | 旧市场状态页 | V3 |
| `/imports` | 旧导入页 | V3 |
| `/kaipan` | 旧 Kaipan 页 | V3 |
| `/data-health` | 旧数据健康页 | V3 |
| `/strategy-studio` | 旧策略实验页 | V3 |
| `/backtests` | 旧回测中心 | V3 |
| `/users` | 旧用户管理页 | V3 |
| `/ops` | 旧运维页 | V3 |

## 5. 信息分组规则

1. 正式入口优先显示在 sidebar 上半部分。
2. 占位模块必须与正式入口并列展示，但要清楚标记为预留。
3. 兼容入口不应继续出现在正式 sidebar，若必须保留直达，只能通过显式兼容壳或历史链接进入。
4. 旧页面可以继续访问，但不应再作为默认导航和文档入口。
5. `UI-V2-001` 以后新增的正式 UI 页面，必须先判断是否属于正式入口或兼容入口。

## 6. 与 TaskList 的关系

- `UI-V2-001` 负责落地这份 IA。
- `UI-V2-006`、`UI-V2-007`、`UI-V2-010`、`UI-V2-011` 在这份 IA 下继续补正式页面。
- `NW-V2-S4-001` 依赖这份 IA 完成 V2 正式工作台收口。
