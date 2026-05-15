# AGENTS.md

**Agent 必读入口文件。**

本文件面向AI Agent，目标是让 Agent 在 `trade-strategy-ai` 项目中以一致、可追踪、可恢复、可验收的方式工作。

本文件只保留高频强约束和路由规则。详细规则见：

```text
trade-strategy-ai/docs/agent-rules/
```

---

## 0. Rule Priority（规则优先级）

当规则冲突时，按以下优先级执行：

| 优先级 | 规则来源 |
|---|---|
| P0 | 用户当前明确指令 |
| P1 | 安全 / 数据保护 / 禁止破坏性操作 |
| P2 | 本 `AGENTS.md` |
| P3 | `docs/agent-rules/*` |
| P4 | `ACTIVE_TASK_LIST` / docs / specs / plans / guides |
| P5 | Agent 自主建议 |

要求：

- 不允许以“优化”为理由绕过用户要求
- 不允许以“自动执行”为理由绕过确认机制
- 不确定时必须说明不确定点并向用户确认

---

## 1. Required Rule Loading Matrix（规则加载矩阵）

| 场景 | 必须读取 |
|---|---|
| 普通代码修改 | `docs/agent-rules/task-workflow.md`, `docs/agent-rules/testing-and-quality.md` |
| UI 修改 | `docs/agent-rules/task-workflow.md`, `docs/agent-rules/ui-rules.md` |
| API / schema / workflow 修改 | `docs/agent-rules/architecture-boundary.md`, `docs/agent-rules/testing-and-quality.md` |
| start / end | `docs/agent-rules/session-report.md`, `docs/agent-rules/task-workflow.md` |
| TaskList 更新 | `docs/agent-rules/task-workflow.md` |
| 敏感信息 / 数据库 / 删除文件 | `docs/agent-rules/safety-rules.md` |
| 多 Agent 接手 | `docs/agent-rules/multi-agent-rules.md`, `docs/agent-rules/session-report.md` |
| 完成任务输出 | `docs/agent-rules/delivery-output.md` |

---
docs/agent-rules/task-workflow.md## 8. 任务执行规则与约束

 1. UI-V1-002
  2. UI-V1-004
  3. UI-V1-008
  4. UI-V1-009
  5. UI-V1-011
  6. NW-V1-S4-001
  7. NW-V1-S4-002

## 2. 默认语言

- 默认使用中文回答
- 默认使用中文更新：
  - `daily-sessions`
  - `daily-report`
  - TaskList
- 技术术语可以保留英文原词
- 用户明确要求其他语言时，优先遵循用户要求

详细见：

```text
docs/agent-rules/language-and-paths.md
```

---

## 3. 项目路径

项目根目录：

```text
trade-strategy-ai
```

推荐使用相对 workspace 根目录路径：

```text
trade-strategy-ai/daily-sessions
trade-strategy-ai/daily-report
trade-strategy-ai/docs/New-Web-Linked-TaskLists
trade-strategy-ai/docs/superpowers
```

尽量不要在对话中依赖 `cd`。

详细见：

```text
docs/agent-rules/language-and-paths.md
```

---

## 4. ACTIVE_TASK_LIST

当前任务必须基于：

```text
docs/New-Web-Linked-TaskLists/*
```

要求：

- 会话开始时确认 `ACTIVE_TASK_LIST`
- 切换任务时确认是否切换 `ACTIVE_TASK_LIST`
- 更新任务状态前确认目标文件
- 不允许创建重复 Task 编号

详细见：

```text
docs/agent-rules/task-workflow.md
```

---

## 5. 每次 Coding 前必须做

在修改代码或文档前：

1. 确认用户目标
2. 读取相关 TaskList / docs
3. 如任务复杂，先输出 Plan 并等待确认
4. 涉及架构冻结层时，必须先说明影响范围并获得确认
5. 涉及破坏性操作时，必须先获得确认

复杂任务和架构冻结层规则见：

```text
docs/agent-rules/task-workflow.md
docs/agent-rules/architecture-boundary.md
```

---

## 6. 每次 Coding 后必须做

完成修改后：

1. 运行相关测试或说明无法运行的原因
2. Review 是否满足验收标准
3. 根据实际完成度更新 Task 状态
4. 必要时更新 `daily-sessions` / `daily-report`
5. 输出完成内容、修改文件、验证结果、风险和下一步建议

详细见：

```text
docs/agent-rules/testing-and-quality.md
docs/agent-rules/session-report.md
```

---

## 7. Task 状态机

所有 Task 只能使用以下状态：

| 状态 | 含义 |
|---|---|
| `[ ]` | 未开始 |
| `[-]` | 正在进行 |
| `[!]` | 被阻塞 |
| `[~]` | 已拆出到未来优化，不阻塞第一版交付 |
| `[x]` | 已验收完成 |

**未满足 Definition of Done 时，禁止标记 `[x]`。**

详细见：

```text
docs/agent-rules/task-workflow.md
```

---

## 8. Definition of Done 摘要

任务标记 `[x]` 前必须至少满足：

- 功能实现完成
- 编译 / 相关测试通过，或明确说明无法验证原因
- 满足 TaskList 验收标准
- UI 与 API contract 对齐
- TaskList / 文档已同步
- 无未追踪临时方案、mock、TODO

详细见：

```text
docs/agent-rules/task-workflow.md
```

---

## 9. 禁止行为摘要

未经用户明确确认，禁止：

- 删除文件、清空目录、覆盖重要文档
- 清理 cookie / key / token / secret
- 修改数据库 schema 或执行不可逆 migration
- 修改 provider interface / workflow DAG / API contract
- 大规模重构、升级依赖、修改 CI/CD、deployment
- 将未验收任务标记为 `[x]`
- 引入 mock 或临时方案但不标记、不创建收口任务

详细见：

```text
docs/agent-rules/safety-rules.md
docs/agent-rules/architecture-boundary.md
```

---

## 10. start / end / test / update task list

触发词：

| 指令 | 动作 |
|---|---|
| `start` | 会话初始化 |
| `end` | 会话收尾 |
| `test` | 测试流程 |
| `update task list` | 同步 Task 状态 |
| `reset` / `review rules` | 重新阅读核心规则 |

详细见：

```text
docs/agent-rules/task-workflow.md
docs/agent-rules/session-report.md
```

---

## 11. daily-session 是唯一上下文恢复入口

不维护独立：

```text
daily-sessions/index.md
```

最新 `daily-session` 必须包含：

```md
## Current Context
## Resume Point
```

Agent 切换或恢复上下文时，优先读取最新 `daily-session` 的 `Resume Point`。

详细见：

```text
docs/agent-rules/session-report.md
```

---

## 12. UI 开发

涉及 UI 创建或修改时：

- 优先使用 `skill:ui-ux-pro-max`
- 必须遵循 UI TaskList
- 必须覆盖 Loading / Error / Empty / Retry / Success 状态
- 必须确认 UI 与 API contract 对齐

详细见：

```text
docs/agent-rules/ui-rules.md
```

---

## 13. Multi-Agent 协作

多个 Agent 协作时必须保持一致：

- `ACTIVE_TASK_LIST`
- Task 编号
- Task 状态
- API contract
- schema
- workflow
- UI 绑定关系
- latest daily-session Resume Point

详细见：

```text
docs/agent-rules/multi-agent-rules.md
```

---

## 14. 最终原则

Agent 必须始终遵循：

- 先理解，再执行
- 先确认，再做破坏性操作
- 先小范围验证，再扩大范围
- 先记录恢复点，再结束会话
- 必须满足交付目标，必要时可修改现有架构
