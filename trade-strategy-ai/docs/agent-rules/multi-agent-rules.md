# Multi-Agent Rules

## 1. Multi-Agent 协作规范

多个 Agent（Claude Code / Codex / ChatGPT / Cursor Agent）协作时，必须保持以下内容一致：

- `ACTIVE_TASK_LIST`
- Task 编号
- Task 状态
- API contract
- schema
- workflow
- UI 绑定关系
- daily-session 恢复点

---

## 2. 禁止并行冲突

禁止：

- 多个 Agent 并行修改同一 schema
- 多个 Agent 并行修改同一 workflow
- 多个 Agent 并行修改同一 API contract
- 一个 Agent 更新 TaskList，另一个 Agent 不读取最新状态继续执行
- 多个 Agent 维护不同版本的任务状态

---

## 3. Agent 切换流程

切换 Agent 时，新的 Agent 必须优先读取：

1. 根目录 `AGENTS.md`
2. 最新 daily-session 的 `Resume Point`
3. 当前 `ACTIVE_TASK_LIST`
4. 必要的 docs / specs / plans

然后输出：

```md
## 我读取到的当前状态

## 当前任务

## 阻塞点

## 下一步建议

## 需要确认的事项
```

---

## 4. Agent Boundary

Agent 不应主动执行以下行为，除非用户明确要求或 TaskList 明确要求：

- 升级依赖
- 替换框架
- 重构整个系统
- 修改 infra
- 修改 deployment
- 修改 CI/CD
- 修改数据库结构
- 修改 provider 协议
- 修改 workflow 架构
- 大规模重命名
- 批量格式化无关文件
- 引入新工具链

允许主动执行：

- 阅读相关文档
- 分析问题
- 给出建议
- 小范围修复
- 补充测试
- 更新与当前任务直接相关的文档
- 标注风险和 TODO
