# New-Web-Execution-Guide

## 文件说明

本 文件夹 包包含 3 个文件：

1. `New-Web-TaskList.md`
   - 最终版主 TaskList。
   - 覆盖 V1/V2/V3 的后端、运行时、业务切片、配置迁移、CLI 降级、部署与最终交付。
   - 每个主任务都包含 `UI 关联任务`。
   - 文末包含 `主任务与 UI 任务映射表`。

2. `New-Web-UI-TaskList.md`
   - Web UI 专项 TaskList。
   - 覆盖 V1/V2/V3 的页面、组件、API Client、状态、交互和前端验收。
   - 每个 UI 任务都包含 `主任务关联`。

3. `New-Web-Execution-Guide.md`
   - 当前文件。
   - 说明如何一起执行主 TaskList 和 UI TaskList。

## 是否单独执行 UI TaskList？

不建议单独执行。

UI TaskList 应该作为 V1/V2/V3 的前端子任务，和主 TaskList 并行执行。

## 推荐执行节奏

### V1

目标：

```text
产品化运行底座 + article_pipeline 完整闭环
```

执行：

```text
主任务：NW-V1-*
UI 任务：UI-V1-*
```

必须同步完成：

- Runtime Contract
- Config Snapshot
- Artifact Contract
- Step Timeline
- Workflow Runner MVP
- article_pipeline API
- Job Detail UI
- Artifact Panel
- Config Snapshot Panel
- Article Pipeline Page
- V1 UI 验收

### V2

目标：

```text
正式 Profile + 正式 Web 工作台 + Market/Strategy
```

执行：

```text
主任务：NW-V2-*
UI 任务：UI-V2-*
```

必须同步完成：

- Profile 正式模型
- config_path → Profile 迁移
- Profile UI
- Dashboard
- Market Data Workspace
- Strategy Workspace
- Artifact Center

### V3

目标：

```text
完整交付项目
```

执行：

```text
主任务：NW-V3-*
UI 任务：UI-V3-*
```

必须同步完成：

- Backtest Center
- Rule Pool Review
- Optimize Candidate UI
- Admin Ops Console
- Health Check Dashboard
- Backup / Restore UI
- Permission / Audit UI
- Final UX Review
- User Manual Coverage Verification

## AI Agent 使用方式

建议给 AI 的任务格式：

```text
请执行 Task ID: <ID>

必须先阅读：
- New-Web-TaskList.md 中对应主任务
- New-Web-UI-TaskList.md 中对应 UI 任务
- 两个文档中的映射表

只实现该 Task ID 的范围。

完成后说明：
1. 修改了哪些文件
2. 是否触碰了禁止修改项
3. 如何测试
4. 是否存在 Blocking
5. 是否同步检查了关联 UI/主任务
```

## 验证重点

检查 `New-Web-TaskList.md` 是否包含：

- “UI TaskList 不是独立执行文档”的说明。
- 每个 Stage 的 UI 关联任务。
- 每个关键 Task 的 UI 关联任务。
- 主任务与 UI 任务映射表。

检查 `New-Web-UI-TaskList.md` 是否包含：

- 每个 UI Task 的主任务关联。
- loading / empty / error / permission denied 状态要求。
- API Client、页面、组件、测试和验收要求。
