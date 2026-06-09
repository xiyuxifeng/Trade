# Language and Paths

## 1. 语言输出规范

- 默认使用中文回答
- 默认使用中文更新：
  - `daily-sessions`
  - `daily-report`
  - TaskList
- 用户使用英文提问时，仍默认中文回答，除非用户明确要求英文
- 技术术语可以保留英文原词，并在必要时补充中文解释
- 用户明确要求其他语言时，优先遵循用户要求

---

## 2. 目录结构与路径约定

项目根目录：

```text
trade-strategy-ai
```

VS Code workspace 根目录：

```text
trade-strategy-ai 的上一层
```

推荐做法：

- 尽量不要在对话中执行 `cd`
- 直接使用相对 workspace 根目录的路径

常用路径：

```text
trade-strategy-ai/daily-sessions
trade-strategy-ai/daily-report
trade-strategy-ai/docs/superpowers/plans
trade-strategy-ai/docs/superpowers/specs
trade-strategy-ai/docs/superpowers/guides
trade-strategy-ai/docs/New-Web-Linked-TaskLists
```

如果用户已经明确执行：

```bash
cd trade-strategy-ai
```

则以下路径等价：

```text
trade-strategy-ai/daily-sessions ≈ daily-sessions
trade-strategy-ai/daily-report   ≈ daily-report
trade-strategy-ai/docs/...       ≈ docs/...
```

文档中的路径解释：

- `trade-strategy-ai/...` 表示相对于 workspace 根目录
- `docs/...` 表示相对于 `trade-strategy-ai` 项目根目录

---

## 3. superpowers 存储约定

以下文件夹已经存在，不要重新创建。

### plans

```text
trade-strategy-ai/docs/superpowers/plans
```

如果当前在 `trade-strategy-ai` 目录中：

```text
docs/superpowers/plans
```

用途：

- 记录 `skill:superpowers` 生成的执行计划

### specs

```text
trade-strategy-ai/docs/superpowers/specs
```

如果当前在 `trade-strategy-ai` 目录中：

```text
docs/superpowers/specs
```

用途：

- 记录 `skill:superpowers` 生成的设计文档

### guides

```text
trade-strategy-ai/docs/superpowers/guides
```

如果当前在 `trade-strategy-ai` 目录中：

```text
docs/superpowers/guides
```

用途：

- 记录 `skill:superpowers` 生成的操作指南
