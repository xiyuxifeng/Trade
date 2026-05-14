# New-Web-UI-Routing

> **重点：Web UI 只能有一套 canonical 路由。**
> 所有旧入口都只能作为显式兼容层存在，不能与 canonical 路由并行演进，更不能继续新增功能。

## 1. 路由原则

1. **Canonical 路由唯一。**
   - 新页面、新导航、新文档、新验收只引用 canonical 路由。
2. **Legacy 入口显式存在。**
   - legacy 入口只用于历史书签、旧文档、过渡链接。
   - legacy 入口必须单独列出，不能散落在页面代码里。
3. **兼容层必须可退役。**
   - 每个 legacy 入口都必须标记所属退役阶段。
   - 到达退役阶段后，legacy 入口必须从导航和正式文档中移除。
4. **不允许多入口并行扩张。**
   - 不能把新功能同时挂到 canonical 和 legacy 两条路径。
   - 不能把 legacy 入口当成“另一个正式入口”。

## 2. Canonical 路由

| Canonical 路由 | 说明 |
| --- | --- |
| `/dashboard` | V1/V2/V3 统一的工作台入口。 |
| `/jobs` | Job Center 列表入口。 |
| `/jobs/:jobId` | Job Detail canonical 入口。 |
| `/workflows` | Workflow 目录入口。 |
| `/workflows/:workflowId/run` | Workflow 运行入口。 |
| `/articles` | article_pipeline 验收入口。 |
| `/artifacts` | Artifact Center 入口。 |
| `/settings` | 设置入口。 |

## 3. Legacy 兼容层

| Legacy 入口 | Canonical 映射 | 允许存在阶段 | 退役阶段 | 说明 |
| --- | --- | --- | --- | --- |
| `/` | `/dashboard` | V1, V2 | V3 | 旧首页入口，仅保留过渡跳转。 |
| `/overview` | `/dashboard` | V1, V2 | V3 | 旧概览入口，仅作兼容。 |
| `/jobs?jobId=...` | `/jobs/:jobId` | V1, V2 | V3 | 兼容旧查询参数选中任务。 |
| `/workflows/:workflowId` | `/workflows/:workflowId/run` | V1, V2 | V3 | 兼容旧工作流详情入口。 |
| `/legacy/*` | 具体 legacy 页面 | V1, V2 | V3 | 过渡壳，用于临时页面收口。 |

## 4. 阶段化收口计划

### V1

- 定义 canonical 路由。
- 明确 legacy 兼容映射。
- 所有未实现页面使用明确 placeholder。
- 不在 legacy 入口中新增业务逻辑。

### V2

- 所有正式导航只展示 canonical 路由。
- legacy 入口只能用于历史链接和临时过渡。
- 路由文档、导航文档、验收文档只写 canonical 路由。
- 开始减少对 `/legacy/*` 的依赖。

### V3

- 删除 legacy 路由别名。
- 删除 `/legacy/*` 临时壳。
- 只保留 canonical 路由。
- 通过最终 E2E 和发布验收确认路由已收口。

## 5. 维护规则

- 页面组件不得自己决定是否“顺手”保留旧入口。
- 新增路由前必须先判断是否属于 canonical。
- 任何 legacy 入口若无明确退役阶段，视为设计缺陷。
- 兼容层如果超过 V3 仍未退役，必须升级为阻塞问题处理。

## 6. 关联任务

- `UI-V1-001` 定义 canonical 路由和 legacy 兼容策略。
- `NW-V2-S4-003` 收口 legacy 入口并冻结兼容层。
- `NW-V3-S3-002` 删除 legacy 路由并完成最终退役。
