# Session and Report Rules

## 1. daily-sessions（短期记忆）

路径：

```text
trade-strategy-ai/daily-sessions
```

如果当前在 `trade-strategy-ai` 目录中：

```text
daily-sessions
```

用途：

- 记录“怎么推进到当前状态”
- 记录上下文
- 记录关键决策
- 记录验证过程
- 记录临时风险
- 记录下一次如何继续

禁止：

- 重复 `daily-report` 的正式成果总结
- 写大量无价值命令日志
- 写未验证猜测但不标注
- 重新创建已存在的文件夹

最新 daily-session 必须承担上下文恢复入口职责，不再单独维护：

```text
daily-sessions/index.md
```

推荐模板：

```md
# YYYY-MM-DD daily session

## 一句话目标

## Current Context
ACTIVE_TASK_LIST:
Current Stage:
Current Focus:
Current Status:

## 关键决策

## 今日完成

## 验证结果

## 发现的问题 / 风险

## Resume Point
Current Task:
Blocked By:
Files:
Commands:
Pending Validation:
Next Action:

## 下一步（3-5 条，优先引用 ACTIVE_TASK_LIST 中的任务编号）

## 产物

## 风险与注意事项
```

---

## 2. daily-report（长期记录）

路径：

```text
trade-strategy-ai/daily-report
```

如果当前在 `trade-strategy-ai` 目录中：

```text
daily-report
```

用途：

- 记录最终交付了什么
- 记录阶段成果
- 记录最终验证结论
- 记录已修复风险
- 记录阶段性下一步

禁止：

- 写详细调试过程
- 写临时样本
- 写命令执行噪音
- 写中间失败路径
- 把未完成任务写成已完成
- 重新创建已存在的文件夹

推荐模板：

```md
# YYYY-MM-DD 日报

## 今日成果

## 实现内容

## 验证

## 完成的 Task

## 推进但未完成的 Task

## 发现的问题 / 风险

## 下一步（按优先级，3-6 条，尽量引用 ACTIVE_TASK_LIST 编号）

## 产物
```

---

## 3. session 与 report 去重原则

- 影响“下一次接手怎么继续做”的信息，放 `daily-sessions`
- 影响“项目阶段总结、长期留档、对外汇报”的信息，放 `daily-report`
- 同一事实只保留一份主记录
- 另一份只保留摘要引用或结论
- 不确定归属时，优先放 `daily-sessions`
- `daily-sessions` 回答：“下次从哪里继续做？”
- `daily-report` 回答：“这次最终交付了什么？”

---

## 4. 上下文恢复规则

Agent 恢复上下文时：

1. 读取根目录 `AGENTS.md`
2. 读取最新 daily-session
3. 重点读取 `Resume Point`
4. 如信息不足，再读取最近 daily-report
5. 仍不足时，再追溯更早 session 或 docs

恢复后必须确认：

```md
## 当前任务

## 当前状态

## 阻塞点

## 下一步

## 需要用户确认的事项
```

---

## 5. end 时记录规则

执行 `end` 时，必须询问用户是否更新：

- `daily-sessions`
- `daily-report`
- `ACTIVE_TASK_LIST`

不得未经确认直接写入长期记录。

如果用户确认写入：

- `daily-sessions` 记录恢复上下文
- `daily-report` 记录最终交付结论
- `ACTIVE_TASK_LIST` 只记录真实状态变化
