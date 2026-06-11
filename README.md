# Codex Refactor Orchestrator

通用的仓库级 Codex 重构编排 Skill。

A repository-scoped Codex Skill for staged software refactors.

```text
GPT-5.5 parent
├── optional GPT-5.4 mini Explorer agents
├── bounded GPT-5.4 mini Executor agents
└── GPT-5.5 review and stage acceptance
```

## 特性 / Features

- 最小 Agent lane 策略 / minimum viable lanes
- 最多三轮修复 / bounded three-round fix loop
- 运行时探测 / runtime probe
- 每轮 diff 与测试证据 / per-round artifacts
- native subagent 不可用时安全回退 / single-controller fallback
- Stage Plan、Task Card、Handoff、Review 模板
- 中文和英文通用使用说明

## 安装 / Installation

```bash
./install.sh /path/to/repository
```

验证 / Validate:

```bash
bash .agents/skills/refactor-orchestrator/scripts/validate-install.sh
bash .agents/skills/refactor-orchestrator/scripts/runtime-probe.sh
```

启动 / Start:

```bash
codex -m gpt-5.5
```

文档 / Documentation:

- [中文通用使用说明](docs/01-通用项目使用说明.md)
- [English guide](docs/README_EN.md)

## License

MIT
