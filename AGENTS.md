# AGENTS.md

**如果你是一个AI Agent，请认真阅读下面的内容，必须严格遵循以下约定、行为规范、注意事项等内容，以便与我们进行更高效的协作。**

---

## 🌐 语言输出规范

- **优先使用中文进行回答和更新`daily-sessions`, `daily-report`**
- 当用户使用英文提问时，仍优先用中文回答，除非用户明确要求使用英文
- 如涉及技术术语，可保留英文原词并在中文中解释
- 当用户明确要求使用其他语言时，优先遵循用户指令

---

## 📁 目录结构与路径约定

- 项目根目录：`trade-strategy-ai`（绝大部分代码和文档都在这里）
- VS Code workspace 根目录：`trade-strategy-ai`的上一层
- **推荐做法：尽量不要在对话中执行 `cd` 命令，直接使用相对 workspace 根目录的路径**，例如：
  - `trade-strategy-ai/daily-sessions`
  - `trade-strategy-ai/daily-report`
  - `trade-strategy-ai/docs/superpowers/plans`
  - `trade-strategy-ai/docs/superpowers/specs`
  - `trade-strategy-ai/docs/superpowers/guides`
- 如果用户已经明确执行了 `cd trade-strategy-ai`，则以下路径等价：
  - `trade-strategy-ai/daily-sessions` ≈ `daily-sessions`
  - `trade-strategy-ai/daily-report` ≈ `daily-report`
  - `trade-strategy-ai/docs/superpowers/...` ≈ `docs/superpowers/...`
- 文档中的路径约定：
  - 看到 `trade-strategy-ai/...` 时，理解为「相对于 workspace 根目录」的路径
  - 看到 `docs/superpowers/...` 时，理解为「相对于 trade-strategy-ai 目录」的路径

---

## ⚡ 自动执行约定

当用户输入以下任一指令时，必须触发对应流程：

| 指令 | 触发动作 | 说明 |
| --- | --- | --- |
| `start` | 执行“开始（会话初始化）”流程 | 读取最新 `daily-sessions` 与 `daily-report`，并输出当前状态摘要 |
| `end` | 执行“结束（会话收尾）”流程 | 在会话结束前询问是否执行保存、清理与同步操作 |
| `update task list` | 更新 `TaskList` 完成进度 | 根据当前代码完成情况同步任务状态 |
| `test` | 执行测试流程 | 验证项目编译、核心逻辑和关键功能是否正常 |

---

## 🚀 开始（会话初始化）

在每次开始会话前，代理必须：

1. 从 `daily-sessions` 中获取最新的会话上下文
2. 从 `daily-report` 中获取最新的工作内容
3. 对上述内容进行汇总分析，并输出：

  - 上一次做了什么
  - 当前项目状态
  - 下一步需要做什么
  - 需要注意的事项 / 风险点

---

## 🧾 结束（会话收尾）

在每次会话结束前，代理必须：

1. 主动询问用户是否需要进行如下保存操作：
  - 是否更新停止数据库连接
  - 是否清理 `config` 中配置的 `cookie` 和密钥信息
  - 是否将当前上下文更新到 `daily-sessions`
  - 是否将本次结果更新到 `daily-report`
  - 是否更新TaskList中完成进度

2. 根据用户的选择：
  - 选择“是”时：执行对应保存或清理操作
  - 选择“否”时：跳过对应操作
  - 数据库停止命令为：`brew services stop postgresql@15`

---

## 代码规范
- 类和方法以及配置项等需要有注释解释其作用，注释用中文写

---

## Git规范
- **不要自动进行任何`git`操作和命令，除非用户明确指示**

---

## 🧠 行为规范

- 始终优先基于已有上下文和文档进行推理，避免重复工作，重点关注`docs`目录下的文档
- 对关键状态、进展和决策进行结构化总结
- 不擅自修改 `daily-sessions`、`daily-report` 和 `TaskList`，除非用户确认或当前流程明确要求
- 保持输出简洁、清晰、可追踪
- 对不确定的信息进行标注说明
- 当前任务完成后，如有明确进度变化，需要同步 `TaskList` 和待办列表，并给出下一步建议
- **优先使用Skills进行处理，Skill和本文档冲突的时候，以本文内容为准**
- 每次完成TaskList中的3个任务后，自动读取一下此文件中的内容，并输出"刷新Mermory"，以便与我进行更高效的协作

---

## 📂 存储约定

- `daily-sessions`（短期记忆）：
  - **这个文件夹已经存在，不要重新创建**
  - 从 workspace 根目录访问路径：`trade-strategy-ai/daily-sessions`
  - 如果当前在 `trade-strategy-ai` 目录中，路径：`daily-sessions`
  - 记录“怎么推进到当前状态”的过程信息，重点保留上下文、关键决策、验证过程和临时风险
  - 不写重复的成果总结，不把 `daily-report` 的正式结论再写一遍
  - 建议结构模板：
    ```md
    # YYYY-MM-DD daily session

    ## 一句话目标
    ## 关键决策
    ## 今日完成
    ## 验证结果
    ## 发现的问题 / 风险
    ## 下一步（3-5 条，只保留当前会话要继续做的事情）
    ## 产物
    ## 风险与注意事项
    ```

- `daily-report`（长期记录）：
  - **这个文件夹已经存在，不要重新创建**
  - 从 workspace 根目录访问路径：`trade-strategy-ai/daily-report`
  - 如果当前在 `trade-strategy-ai` 目录中，路径：`daily-report`
  - 记录“最终交付了什么”，重点保留成果、最终验证结论、已修复风险和阶段性下一步
  - 不写详细调试过程、临时样本、命令执行噪音或中间失败路径
  - 建议结构模板：
    ```md
    # YYYY-MM-DD 日报

    ## 今日成果
    ## 实现内容
    ## 验证
    ## 发现的问题 / 风险
    ## 下一步（按优先级，保留 3-6 条）
    ## 产物
    ```

- session和report的去重原则：
  - 如果一条信息会影响“下一次接手怎么继续做”，放 `daily-sessions`
  - 如果一条信息会影响“项目阶段总结、长期留档、对外汇报”，放 `daily-report`
  - 同一事实只保留一份主记录，另一份只保留摘要引用或结论，不要全文重复
  - 如果不确定归属，优先放到 `daily-sessions`，再在 `daily-report` 中写结论摘要


- `docs/superpowers/plans`:
  - 记录superpowers的plan
  - **这个文件夹已经存在，不要重新创建**
  - 从 workspace 根目录访问路径：`trade-strategy-ai/docs/superpowers/plans`
  - 如果当前在 `trade-strategy-ai` 目录中，路径：`docs/superpowers/plans`

- `docs/superpowers/specs`:
  - 记录superpowers的design
  - **这个文件夹已经存在，不要重新创建**
  - 从 workspace 根目录访问路径：`trade-strategy-ai/docs/superpowers/specs`
  - 如果当前在 `trade-strategy-ai` 目录中，路径：`docs/superpowers/specs`

- `docs/superpowers/guides`:
  - 记录superpowers的guides
  - **这个文件夹已经存在，不要重新创建**
  - 从 workspace 根目录访问路径：`trade-strategy-ai/docs/superpowers/guides`
  - 如果当前在 `trade-strategy-ai` 目录中，路径：`docs/superpowers/guides`

---

## ⚠️ 注意事项

- **不要自动进行任何`git`操作和shell命令，除非用户明确指示**
- 所有关键操作需在用户确认后执行
- 避免丢失上下文信息
- 保持上下文的连续性和一致性
- 在不明确任务时，优先向用户确认

---