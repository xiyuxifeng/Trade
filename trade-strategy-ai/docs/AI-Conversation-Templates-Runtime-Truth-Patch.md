# AI-Conversation-Templates Runtime Truth Patch

本文件记录应合并到 `AI-Conversation-Templates.md` 的修改。完成合并后可删除本文件。

## 1. 将 3.3 替换为

```markdown
## 3.3 运行证据说明

完整的 runtime truth 规则以 `.agents/skills/refactor-orchestrator/SKILL.md` 为准。

配置文件和 `runtime-probe.sh` 只能表示预期配置，不能单独证明实际模型、权限或 subagent 已生效。执行任务时所需的最小完整规则必须直接写入可复制 Prompt，不能依赖 Agent 额外读取本节。
```

## 2. 在通用 Task Prompt 固定开场之后加入

```text
Runtime truth requirements:
- Verify actual native subagent spawning before reporting that subagents were used.
- TOML configuration and runtime-probe.sh show expected configuration only; they do not prove the actual runtime model or effective permissions.
- Report a model or permission only when runtime evidence supports it.
- When native spawning, runtime identity, or effective permissions cannot be verified, use single-controller fallback and state that explicitly.
- Do not report a subagent, model, permission, test result, or Task completion as verified without runtime, command, or workspace evidence.
```

并将 `Before delegation` 中的：

```text
- verify Orchestrator runtime evidence when delegation is used
```

替换为：

```text
- apply the Runtime truth requirements above before delegation
```

## 3. 在 RT-S1-002 Session A Prompt 固定开场之后加入

```text
Runtime truth requirements:
- Verify actual native subagent spawning before reporting that subagents were used.
- TOML configuration and runtime-probe.sh show expected configuration only; they do not prove the actual runtime model or effective permissions.
- Report a model or permission only when runtime evidence supports it.
- When native spawning, runtime identity, or effective permissions cannot be verified, use single-controller fallback and state that explicitly.
- Do not report a subagent, model, permission, test result, or Task completion as verified without runtime, command, or workspace evidence.
```

将最终报告要求调整为：

```text
Report verified runtime mode, actual agents, models/permissions only when verified, fallback mode when applicable, risks, Task Cards, contracts, files, tests, visual status, remaining Session B work and scope confirmation.
```

## 4. 在 RT-S1-002 Session B Prompt 固定开场之后加入相同 Runtime truth requirements

最终报告要求调整为：

```text
Report verified runtime mode, actual agents, models/permissions only when verified, fallback mode when applicable, Task Cards, formal routes, compatibility, tests, visual verification, risks and scope confirmation.
```

## 5. 在 Review Prompt 中加入

```text
Runtime truth requirements:
- Do not accept claimed subagent spawning, model identity, effective permissions, test results, or Task completion without runtime, command, or workspace evidence.
- TOML configuration and runtime-probe.sh prove expected configuration only.
- When runtime identity or permissions cannot be verified, record the uncertainty and evaluate the work as single-controller fallback.
```

并要求 Review 输出：

```text
verified runtime facts, findings, repairs, evidence, residual risk, acceptance conclusion and whether the next Task/Stage is allowed
```

## 6. 恢复与完成核验 Prompt

新 Session 恢复模板加入：

```text
Treat prior model, permission, subagent and test claims as unverified unless supporting evidence is present.
```

完成核验模板加入：

```text
Do not accept subagent, model, permission, test or completion claims without runtime or workspace evidence.
```
