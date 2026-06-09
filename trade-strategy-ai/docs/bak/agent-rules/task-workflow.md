# Task Workflow Rules

## 1. ACTIVE_TASK_LIST

当前任务必须基于：

```text
docs/New-Web-Linked-TaskLists/*
```

要求：

- 会话开始时必须确认当前 `ACTIVE_TASK_LIST`
- 切换任务时必须确认是否需要切换 `ACTIVE_TASK_LIST`
- 所有任务状态更新必须写入正确的 `ACTIVE_TASK_LIST`
- 不允许在未确认目标文件的情况下批量修改 TaskList
- 如果 TaskList 有多个版本，必须优先确认用户指定的版本

---

## 2. 自动执行约定

当用户输入以下指令时，必须触发对应流程：

| 指令 | 触发动作 | 说明 |
|---|---|---|
| `start` | 执行会话初始化流程 | 读取最新 `daily-sessions` 与 `daily-report`，输出当前状态摘要 |
| `end` | 执行会话收尾流程 | 询问是否保存、清理、同步任务进度 |
| `update task list` | 更新 `ACTIVE_TASK_LIST` 完成进度 | 根据当前代码和验收情况同步任务状态 |
| `test` | 执行测试流程 | 验证编译、核心逻辑和关键功能 |
| `reset` / `review rules` | 执行规则重载流程 | 重新阅读 `AGENTS.md` 和 `CLAUDE.md`，并确认核心约定 |

---

## 3. start：会话初始化流程

执行 `start` 时，Agent 必须：

1. 重新阅读根目录 `AGENTS.md`
2. 按需阅读 `docs/agent-rules/*`
3. 确认当前 `ACTIVE_TASK_LIST`
4. 从 `daily-sessions` 中读取最近一次会话上下文
5. 从 `daily-report` 中读取最近一次阶段性成果
6. 必要时阅读相关 `docs` / specs / plans
7. 输出当前状态摘要

输出必须包含：

```md
## 上一次做了什么

## 当前项目状态

## 当前 ACTIVE_TASK_LIST

## 当前阻塞点 / 风险

## 下一步建议

## 需要用户确认的事项
```

注意：

- 不要无条件读取所有历史 session
- 优先读取最新 session
- 只有最新 session 信息不足时，才追溯更早记录
- 不维护独立 `daily-sessions/index.md`
- 最新 daily-session 本身必须承担上下文恢复入口职责

---

## 4. end：会话收尾流程

执行 `end` 时，Agent 必须先询问用户是否需要执行以下操作：

- 是否停止数据库连接
- 是否清理 `config` 中的 cookie 和密钥信息
- 是否将当前上下文更新到 `daily-sessions`
- 是否将本次结果更新到 `daily-report`
- 是否更新 `ACTIVE_TASK_LIST` 中的任务进度

数据库停止命令：

```bash
brew services stop postgresql@15
```

要求：

- 用户选择“是”时，执行对应操作
- 用户选择“否”时，跳过对应操作
- 不允许未经确认直接清理敏感配置
- 不允许未经确认直接更新长期记录
- 如果本次任务未达到验收标准，不得在 `daily-report` 中写成“已完成”

---

## 5. Task 状态机

所有 Task 必须使用以下状态：

| 状态 | 含义 |
|---|---|
| `[ ]` | 未开始 |
| `[-]` | 正在进行 |
| `[!]` | 被阻塞 |
| `[~]` | 已拆出到未来优化，不阻塞第一版交付 |
| `[x]` | 已验收完成 |

状态更新规则：

- 未开始只能是 `[ ]`
- 开始执行后改为 `[-]`
- 遇到外部依赖或关键问题改为 `[!]`
- 代码完成但尚未完全验收时改为 `[-]`
- 只有满足 Definition of Done 才能改为 `[x]`

禁止：
    
- 未验证直接标记 `[x]`
- 只完成部分功能就标记 `[x]`
- UI 完成但 API 未完成时标记 `[x]`
- 后端完成但 UI 绑定未完成时标记 `[x]`
- 跳过测试直接标记 `[x]`

---

## 6. Definition of Done

任务只有同时满足以下条件，才能标记为 `[x]`：

- 功能实现完成
- 编译通过
- 相关测试通过
- 无明显 runtime error
- 满足 TaskList 中的验收标准
- UI 与 API contract 已对齐
- 文档已更新
- TaskList 已同步
- 无未标记 mock 数据
- 无未跟踪 TODO
- 无临时方案未收口
- 已完成 Review

如果无法满足以上条件：

- 标记为 `[-]`
- 或标记为 `[!]`

---

## 7. 复杂任务规划规则

以下情况必须先生成 Plan：

- 多模块修改
- 新功能实现
- 重构
- schema 修改
- API contract 修改
- CLI -> Web 演进
- 新增页面
- 状态管理改动
- workflow 改动
- provider 接入
- profile/config 系统改动
- 回测逻辑改动
- TaskList 大规模调整

流程：

1. 确认用户目标
2. 阅读相关 docs / TaskList / specs
3. 分析现状
4. 输出分步骤 Plan
5. 按 `ACTIVE_TASK_LIST` 格式组织任务
6. 说明风险和不确定点
7. 请求用户确认后再执行

要求：

- 优先使用 `skill:superpowers`
- 如果 skill 不可用，则按上述流程手动执行
- skill 与 AGENTS 规则冲突时，以 AGENTS 规则为准

---

## 8. 任务执行规则与约束

开始 `ACTIVE_TASK_LIST` 中的任务之前，必须先理解：

```text
docs/New-Web-Linked-TaskLists/New-Web-UI-TaskList.md
docs/New-Web-Linked-TaskLists/New-Web-Linked-TaskLists.md
```

重点阅读：

- `## 0. 执行关系`
- `## 1. AI UI Implementation Rules`
- `## 2. UI 架构目标`
- `## 0. 执行方式总则`
- `## 1. 项目阶段定位`
- `## 2. AI Implementation Rules`
- `## 3. 目标架构`
- `## 4. 版本路线与 UI 绑定`

任务执行原则：

- 以项目交付为最终目标
- 过渡方案必须有后续收口任务
- 不留下无追踪临时方案
- 当前任务完成后必须 Review
- 有明确进度变化时必须同步 TaskList
- 下一步建议必须引用 Task 编号

---

## 9. update task list

执行 `update task list` 时：

1. 先确认当前 `ACTIVE_TASK_LIST`
2. 对照代码实现、测试结果、验收标准
3. 只更新真实发生变化的 Task
4. 对无法确认的 Task 保持原状态
5. 对部分完成的 Task 使用 `[-]` 或 `[~]` 标记
6. 不允许无依据批量标记 `[x]`

更新后必须输出：

```md
## 已更新 Task

## 未更新 Task

## 原因

## 风险

## 下一步
```
