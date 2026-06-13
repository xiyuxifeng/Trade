# trade-strategy-ai 项目级 Agent 约束

本文件补充仓库根目录 `AGENTS.md`，适用于 `trade-strategy-ai` 下的重构任务。

## 实施日志结构

```text
docs/Refactor-Implementation-Log.md
= 当前状态摘要、Task 索引、阻塞项、下一步和 Stage 日志链接

docs/refactor-implementation-logs/stage-<n>.md
= 当前 Stage 的详细实施、Review、修复、验证和 Stage Gate 历史

docs/refactor-implementation-logs/README.md
= 日志创建、读取和更新规则

../.codex/refactor-state/<stage-id>/
= 临时 Task Card、完整 diff、长测试日志和 subagent handoff
```

## 必读规则

开始或恢复任务时：

1. 先读取 `docs/Refactor-Implementation-Log.md`。
2. 只读取当前 Stage 对应的 `docs/refactor-implementation-logs/stage-<n>.md`。
3. 读取当前 Task 的直接设计、实施、迁移和验收文档。
4. 检查 TaskList、当前分支、基线、`git status` 和完整 diff。
5. 不默认读取已完成 Stage 的详细日志；只有当前 Task 明确依赖历史决定时才读取。

同一个 Parent Session 内继续同一 Stage 时，只读取：

- 主实施日志的新变化；
- 当前 Stage 日志新增条目；
- 上游 handoff；
- 当前 Task 相关代码、测试和 diff。

## 更新规则

每个 Task、修复批次或 Review 后：

1. 详细记录追加到当前 `stage-<n>.md`。
2. 主实施日志只更新：
   - 当前 Stage/Task；
   - Task 状态；
   - 阻塞项；
   - 未完成 Stage Gate；
   - 下一步；
   - 最近接受结论和 Stage 日志链接。
3. 不将长测试输出、完整堆栈、完整 Task Card、subagent 对话或完整 diff 写入正式文档。
4. 测试只记录命令、数量、结果、关键错误和证据路径。
5. 新 Stage 开始时创建 `docs/refactor-implementation-logs/stage-<n>.md`。
6. Stage Gate 完成后，在 Stage 日志追加最终验收，并同步主实施日志。

如果旧 Prompt 或历史文档只写了：

```text
Update Refactor-Implementation-Log.md
```

必须按本文件解释为：

```text
详细实施、Review 和验证记录 → 当前 stage-<n>.md
当前状态、阻塞项、下一步和索引 → Refactor-Implementation-Log.md
```

不得继续把全部详细历史追加到主实施日志。

## 状态权威性

- `docs/Trade-Refactor-TaskList.md`：Task 定义、顺序和正式验收条件的权威来源。
- `docs/Refactor-Implementation-Log.md`：当前状态镜像和恢复入口。
- Stage 日志：详细历史。
- `.codex/refactor-state`：临时证据，不是正式状态源。

状态不一致时，以 TaskList 为准，并修正主实施日志和当前 Stage 日志。

## 文档范围

所有正式重构文档继续只放在 `trade-strategy-ai/docs`。不得在源码目录、仓库根目录或 `.codex/refactor-state` 中建立第二套正式实施记录。