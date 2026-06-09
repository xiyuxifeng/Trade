# Agent Rules

本目录存放 `trade-strategy-ai` 项目的 Agent 详细规则。

根目录 `AGENTS.md` 是短入口，适合 Codex / Claude Code / Cursor Agent 每次优先读取。

本目录中的文件按需读取：

| 文件 | 何时读取 |
|---|---|
| `language-and-paths.md` | 路径、语言、目录约定不清楚时 |
| `task-workflow.md` | start / end / test / update task list / 任务执行 |
| `session-report.md` | 更新 daily-sessions / daily-report / 恢复上下文 |
| `architecture-boundary.md` | 涉及 schema、workflow、provider、API contract、Web/CLI 边界 |
| `testing-and-quality.md` | 修改代码、运行测试、验证质量 |
| `ui-rules.md` | 创建或修改 UI |
| `safety-rules.md` | 破坏性操作、敏感信息、数据库、密钥 |
| `multi-agent-rules.md` | 多 Agent 协作、切换 Agent |
| `delivery-output.md` | 任务完成后的输出格式 |
