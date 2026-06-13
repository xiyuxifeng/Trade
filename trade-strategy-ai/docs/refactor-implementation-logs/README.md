# 重构实施日志管理规则

本目录保存按 Stage 拆分的详细实施历史。

## 文件职责

```text
trade-strategy-ai/docs/Refactor-Implementation-Log.md
= 当前状态摘要、Task 状态索引、阻塞项、下一步和 Stage 日志链接

trade-strategy-ai/docs/refactor-implementation-logs/stage-<n>.md
= 当前 Stage 的详细实施、Review、修复、验证和 Stage Gate 历史

.codex/refactor-state/<stage-id>/
= 临时 Task Card、完整 diff、长测试日志、subagent handoff 和运行证据
```

`Trade-Refactor-TaskList.md` 仍是 Task 定义、依赖、顺序和正式验收标准的权威来源。

## 状态事实源

- TaskList：权威 Task 状态和验收条件。
- 主实施日志：当前状态镜像和恢复入口。
- Stage 日志：详细历史和证据摘要。
- `.codex/refactor-state`：临时执行证据，不是正式状态源。

状态不一致时，以 TaskList 为准，并同步修正主实施日志和当前 Stage 日志。

## 新 Task 开始前

1. 读取 `Refactor-Implementation-Log.md`。
2. 只读取当前 Stage 对应的 `stage-<n>.md`。
3. 不读取已完成 Stage 的详细日志，除非当前 Task 明确依赖其中的历史决定。
4. 检查 TaskList、当前分支、基线、`git status` 和完整 diff。

## Task 更新规则

每个 Task 或修复批次完成后：

1. 在当前 `stage-<n>.md` 追加详细记录。
2. 在主实施日志中只更新：
   - 当前 Stage/Task；
   - Task 状态；
   - 当前阻塞和未完成 Stage Gate；
   - 下一步；
   - 最近接受的关键结论。
3. 不把长测试输出、完整堆栈、完整 Task Card、subagent 对话或完整 diff 写入正式日志。
4. 测试记录只保留命令、通过/失败数量、关键错误和证据路径。
5. 历史条目不回写成当前状态；当前状态只在主实施日志维护。

## Stage 结束规则

Stage Gate 完成后：

1. 在对应 Stage 日志追加最终验收记录。
2. 更新主实施日志中的 Stage 状态和下一 Stage 入口。
3. 新建下一 Stage 的日志文件，使用以下结构：

```markdown
# Stage N 实施记录

## Stage 摘要

- Stage：
- 当前状态：
- 入口条件：
- 出口条件：

## Task 记录

## Stage Gate

## 残余风险与后续依赖
```

## 读取预算

- 新 Session：主实施日志 + 当前 Stage 日志 + 当前 Task 文档。
- 同一 Stage 延续：只读主实施日志变化、当前 Stage 新增条目、上游 handoff 和当前 diff。
- 新 Stage：不默认重读旧 Stage 详细日志。

这样可以保留审计历史，同时避免实施日志无限增长并反复占用 Agent 上下文。