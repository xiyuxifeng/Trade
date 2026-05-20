# New-Web-UI-Routing

> **重点：Web UI 只能有一套 canonical 路由。**
> 旧入口与临时壳已经在 V3 收口阶段完成退役，文档只保留正式路由事实源。

## 1. 路由原则

1. **Canonical 路由唯一。**
   - 新页面、新导航、新文档、新验收只引用 canonical 路由。
2. **不再保留旧入口。**
   - 已退役的旧入口不再写入正式导航、正式文档和正式验收。
   - 新功能不得再挂到旧入口名下。
3. **单一事实源。**
   - 路由文档、导航配置和验收用例必须保持一致。
   - 维护者只需要理解一套 canonical 路由。

## 2. Canonical 路由

| Canonical 路由 | 说明 |
| --- | --- |
| `/dashboard` | V1/V2/V3 统一的工作台入口。 |
| `/jobs` | Job Center 列表入口。 |
| `/jobs/:jobId` | Job Detail canonical 入口。 |
| `/workflows` | Workflow 目录入口。 |
| `/workflows/:workflowId/run` | Workflow 运行入口。 |
| `/articles` | article_pipeline 验收入口。 |
| `/market` | 市场快照浏览器。 |
| `/market/datasets` | 市场数据集浏览器。 |
| `/strategies` | 策略工作台。 |
| `/backtest` | 回测占位入口。 |
| `/rule-pool` | 规则池占位入口。 |
| `/artifacts` | Artifact Center 入口。 |
| `/profiles` | Profile 管理入口。 |
| `/system` | 系统管理入口。 |
| `/system/audit` | 权限与审计详情页。 |
| `/system/users` | 用户管理详情页。 |
| `/system/health` | 系统健康检查详情页。 |
| `/system/db-migrate` | 数据库迁移详情页。 |
| `/system/backup` | 数据备份详情页。 |
| `/system/restore` | 数据恢复详情页。 |
| `/settings` | 旧设置入口，兼容跳转到 `/profiles`。 |

## 3. 维护规则

- 页面组件不得自己决定是否“顺手”保留旧入口。
- 新增路由前必须先判断是否属于 canonical。
- 任何尝试重新引入旧入口，都必须先补充到 TaskList 和验收文档。
- sidebar / 顶层导航不得展示旧入口或兼容入口分组。

## 4. Compatibility 路由

| 兼容路由 | 说明 |
| --- | --- |
| `/admin` | 旧管理中心，跳转到 `/system`。 |
| `/admin/audit` | 旧审计入口，跳转到 `/system/audit`。 |

## 5. 关联任务

- `UI-V1-001` 定义 canonical 路由。
- `NW-V2-S4-003` 完成路由收口与导航冻结。
- `NW-V3-S3-002` 完成最终退役。
