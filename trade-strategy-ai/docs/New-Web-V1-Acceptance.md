# New-Web-V1-Acceptance

> `trade-strategy-ai` 的 V1 可交付版本验收清单。
> 本文档只定义 V1 的验收口径，不把 V2/V3 能力列为 V1 阻断项。

## 0. 约定

- 状态符号遵循 [New-Web-TaskList.md](/Users/wanghui/Documents/Vibe/Trade/trade-strategy-ai/docs/New-Web-Linked-TaskLists/New-Web-TaskList.md) 的 0.4 约定。
- 优先级遵循 0.5 约定，`P0` 高于 `P1`、`P2`。
- 任务只有同时满足 0.6 的完成条件后，才可以标记为 `[x]`。
- 每个验收项都必须能回溯到主 Task ID 和 UI Task ID。

## 1. V1 验收范围

V1 只验收以下能力：

- `article_pipeline` 用户主流程。
- Job Center 可追踪性。
- Step Timeline。
- Artifact 可下载和可解释。
- Config Snapshot 脱敏展示。
- 权限不足场景。
- 失败、重试、取消、空数据场景。
- Web UI 人工验收路径。
- E2E 命令。

V1 不作为阻断项的能力：

- V2/V3 的正式工作台视觉设计。
- Profile/Market/Backtest/Rule Pool/Admin 的完整工作台。
- 仅面向后续阶段的正式信息架构重做。

## 2. 验收映射表

| 验收项 | 主 Task ID | UI Task ID | 验收要点 |
| --- | --- | --- | --- |
| `article_pipeline` 用户主流程 | `NW-V1-S3-001`, `NW-V1-S3-002`, `NW-V1-S3-003` | `UI-V1-007`, `UI-V1-010`, `UI-V1-005`, `UI-V1-008`, `UI-V1-009` | 能从 Web 发起流程，看到执行过程、结果产物、配置快照和 Job 详情。 |
| Job Center 可追踪性 | `NW-V1-S1-002`, `NW-V1-S1-003`, `NW-V1-S2-002`, `NW-V1-S4-001` | `UI-V1-005`, `UI-V1-006`, `UI-V1-008`, `UI-V1-009`, `UI-V1-011` | 能看到状态、日志、错误、产物、取消、重试入口，且不同状态有可解释展示。 |
| Step Timeline | `NW-V1-S2-002`, `NW-V1-S2-003` | `UI-V1-005`, `UI-V1-006`, `UI-V1-011` | Job/Workflow Detail 可展示按步骤展开的时间线，成功、失败、取消都能体现。 |
| Artifact 可下载和可解释 | `NW-V1-S1-003`, `NW-V1-S2-003`, `NW-V1-S3-002`, `NW-V1-S3-003` | `UI-V1-005`, `UI-V1-008`, `UI-V1-011` | 产物能按步骤查看、下载，且不暴露服务器绝对路径。 |
| Config Snapshot 脱敏展示 | `NW-V1-S1-002` | `UI-V1-005`, `UI-V1-009`, `UI-V1-011` | 能看到本次运行实际使用的配置摘要，敏感字段已脱敏。 |
| 权限不足场景 | `NW-V1-S0-001`, `NW-V1-S1-002`, `NW-V1-S1-003`, `NW-V1-S4-001` | `UI-V1-001`, `UI-V1-005`, `UI-V1-007`, `UI-V1-009`, `UI-V1-011` | 无权限时返回结构化错误，UI 不能空白或伪装成功。 |
| 失败、重试、取消、空数据场景 | `NW-V1-S2-002`, `NW-V1-S2-003`, `NW-V1-S4-001` | `UI-V1-005`, `UI-V1-006`, `UI-V1-008`, `UI-V1-011` | 失败、取消、重试和空数据都要有明确提示，不只覆盖成功态。 |
| Web UI 人工验收路径 | `NW-V1-S4-001`, `NW-V1-S4-002` | `UI-V1-011` | 有可执行的人工验收步骤，能完整走通 V1 主链路。 |
| E2E 命令 | `NW-V1-S4-001`, `NW-V1-S4-002` | `UI-V1-011` | 保留统一回归命令，例如 `python -m cli.main e2e-regression --config config/app.yaml`。 |

## 3. 验收判定规则

- 每个验收项必须写明主任务和 UI 任务，不允许只写“页面可用”。
- UI 验收必须覆盖 `loading`、`empty`、`error`、`permission denied`。
- 不允许把 V2/V3 能力当作 V1 阻断项。
- 如果某个能力只有后端而没有对应 UI，必须明确写出当前缺口和后续任务。
- 只有当验收项、文档、任务状态三者一致时，才算可交付。

## 4. 当前结论

- V1 的验收边界已经可以被 `NW-V1-S0-003` 直接引用。
- `UI-V1-011` 是 V1 验收的最终测试与人工验收入口，但不作为本任务的完成前提。
- 后续如果主任务再补齐新的 V1 能力，只需要补充本清单的映射表，不需要重写 V1 验收定义。
