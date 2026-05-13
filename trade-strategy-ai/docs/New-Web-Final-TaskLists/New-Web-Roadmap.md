# New-Web-Roadmap

## 文档组成

- `New-Web-TaskList.md`：主 TaskList，覆盖 V1/V2/V3 的架构、后端、运行时、业务切片、配置迁移、CLI 降级、部署和最终交付。
- `New-Web-UI-TaskList.md`：UI 专项 TaskList，覆盖 V1/V2/V3 的页面、组件、API Client、状态、交互和验收。

## 是否单独执行 UI TaskList？

不建议单独执行。UI TaskList 是主 TaskList 的前端子计划，必须和 V1/V2/V3 一起执行。

```text
主任务提供 API / Contract / Workflow / Artifact。
UI 任务提供页面 / 表单 / 状态 / 用户验收。
两者缺一不可。
```

## 推荐执行顺序

### V1

完成产品化运行底座和 article_pipeline：

- 主任务：`NW-V1-*`
- UI 任务：`UI-V1-*`

### V2

完成正式 Profile、正式工作台、Market Data 和 Strategy：

- 主任务：`NW-V2-*`
- UI 任务：`UI-V2-*`

### V3

完成 Backtest、Rule Pool、Admin Ops、权限审计和最终发布验收：

- 主任务：`NW-V3-*`
- UI 任务：`UI-V3-*`

## AI Agent 使用提示

给 AI 的任务建议这样写：

```text
请执行 Task ID: <ID>。
先阅读 New-Web-TaskList.md 的对应阶段，以及 New-Web-UI-TaskList.md 中相关 UI 任务。
只实现该 Task ID 的范围。
完成后说明修改文件、测试方式、是否存在 Blocking，以及对应 UI/主任务是否已同步。
```
