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

## ⭐️ 全局变量约定

- `ACTIVE_TASK_LIST`: `docs/New-Web-Linked-TaskLists/*`。这个变量应该在会话开始时或切换任务时设置，以确保所有对 `TaskList` 的更新都指向正确的文件。

---

## ⚡ 自动执行约定

当用户输入以下任一指令时，必须触发对应流程：

| 指令 | 触发动作 | 说明 |
| --- | --- | --- |
| `start` | 执行“开始（会话初始化）”流程 | 读取最新 `daily-sessions` 与 `daily-report`，并输出当前状态摘要 |
| `end` | 执行“结束（会话收尾）”流程 | 在会话结束前询问是否执行保存、清理与同步操作 |
| `update task list` | 更新 `ACTIVE_TASK_LIST` 完成进度 | 根据当前代码完成情况同步任务状态 |
| `test` | 执行测试流程 | 验证项目编译、核心逻辑和关键功能是否正常 |
| `reset` / `review rules` | 执行“规则重载”流程 | 强制Agent重新阅读 `AGENTS.md` 和 `CLAUDE.md` 的全部内容，并确认核心约定。|

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
  - 是否更新`ACTIVE_TASK_LIST`中完成进度

2. 根据用户的选择：
  - 选择“是”时：执行对应保存或清理操作
  - 选择“否”时：跳过对应操作
  - 数据库停止命令为：`brew services stop postgresql@15`

---

## 💻 代码规范
- 类和方法以及配置项等需要有注释解释其作用，注释用中文写

---

## ✅ 代码质量与测试约定

- **编写即测试**：在完成一个独立的函数或模块后，应主动为其编写单元测试，或在现有测试文件中补充测试用例。测试文件通常位于 `tests/` 目录下，并与源文件结构保持对应。
- **修改即验证**：在修改任何现有代码后，必须重新运行相关的单元测试或集成测试，以确保变更没有引入新的问题（回归错误）。
- **提交即整洁**：在完成一系列开发任务后，应确保代码符合项目规范（如 linting），移除不必要的调试代码（如 `print` 语句），并保证所有测试都能通过。

---

## 📝 任务执行规则与约束

1. 开始`ACTIVE_TASK_LIST`中的任务之前，需要先理解以下约定和准则：
   - `New-Web-UI-TaskList.md`中的 `## 0. 执行关系`、`## 1. AI UI Implementation Rules`, `## 2. UI 架构目标`
   - `New-Web-Linked-TaskLists`中的 `## 0. 执行方式总则`、`## 1. 项目阶段定位`, `## 2. AI Implementation Rules`, `## 3. 目标架构`, `## 4. 版本路线与 UI 绑定`
2. 任务完成后需要Review一遍，确保实现符合需求和验收标准，当任务有Task文档追踪的时候需要更新任务的完成情况。

---

## 🧠 行为规范

- 始终优先基于已有上下文和文档进行推理，避免重复工作，重点关注`docs`目录下的文档
- 在执行任务时，需要遵循 `任务执行规则与约束` 中的要求
- **任务分解与规划**: 优先使用**skill:`superpowers`**, 否则使用以下步骤：
    1.  在接收到复杂任务时（例如“实现一个新功能”或“重构某个模块”，首先要向用户确认已经理解了核心目标。
    2.  然后，查阅 `docs` 目录下的相关文档（如需求、设计文档）以获取上下文。
    3.  基于目标和上下文，生成一个分步骤的执行计划，并以 `ACTIVE_TASK_LIST`中的格式呈现。
    4.  将计划呈现给用户，并询问“我准备按此计划执行，是否需要调整？”。待用户确认后，再开始执行。
- **错误处理与恢复**:
    1.  当操作（如执行命令、修改文件）失败时，必须首先分析错误日志和返回信息，定位问题原因。
    2.  尝试根据错误原因进行修复（例如，如果是依赖缺失，则尝试安装依赖）。
    3.  如果初次修复后依然失败，应尝试更换策略或思路。
    4.  如果多次尝试（建议不超过3次）后仍无法解决，必须停止操作，将问题、已尝试的解决方案和相关日志汇总，并向用户请求指导。
- 对关键状态、进展和决策进行结构化总结
- 不擅自修改 `daily-sessions`、`daily-report` 和 `ACTIVE_TASK_LIST`，除非用户确认或当前流程明确要求
- 保持输出简洁、清晰、可追踪
- 对不确定的信息进行标注说明
- 设计方案时，在给出选项的同时必须给出选项的优缺点，并给出建议和原因
- 当前任务完成后，如有明确进度变化，需要同步 `ACTIVE_TASK_LIST`，并给出下一步建议
- **优先使用skill进行处理，skill和本文档冲突的时候，以本文内容为准**
- **定期校准与主动回溯**：在执行 `start`、`end` 或进行复杂的**任务分解与规划**前，必须重新阅读本文档的核心规范。当对用户意图或执行标准感到不确定时，也应主动回溯本文档寻求澄清，若仍不确定则向用户提问。
- **UI 设计实现**：若需要创建或修改用户界面，应首先使用**skill:`ui-ux-pro-max`** 进行设计和实现。
- **资源与成本意识**：
    - 在执行可能消耗大量时间或计算资源的操作（如全量数据回测、大规模数据爬取）前，应首先向用户确认执行范围，并估算可能的影响。
    - 优先使用缓存或快照数据，避免重复执行相同的数据处理任务。
    - 在进行搜索或查询时，尽量使用精确的关键词以缩小范围，提高效率。

---

## 📂 存储约定

- `daily-sessions`（短期记忆）：
  - **这个文件夹已经存在，不要重新创建**
  - 从 workspace 根目录访问路径：`trade-strategy-ai/daily-sessions`
  - 如果当前在 `trade-strategy-ai` 目录中，路径：`daily-sessions`
  - 记录“怎么推进到当前状态”的过程信息，重点保留上下文、关键决策、验证过程和临时风险
  - 不写重复的成果总结，不把 `daily-report` 的正式结论再写一遍
  - 每次任务结束后更新时，必须写清楚“当前停在什么位置、为什么停在这里、下一次应该从哪个 Task 任务继续”
  - `下一步` 必须优先引用 `ACTIVE_TASK_LIST` 中的任务编号，例如 `NTL-S0-007`
  - 如果任务未完成，必须写明：已完成部分、未完成部分、阻塞点、继续执行前需要确认的事项
  - 只记录已经验证过的事实、结论和风险；未经验证的猜测要明确标注为“待确认”
  - 重点记录“下一次接手怎么继续做”，不要把大量结果型总结重复写入 `daily-report`
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
  - 每次任务结束后更新时，必须明确哪些Task已经完成、哪些只是推进但未完成
  - `下一步` 必须按优先级列出 3 到 6 条，并尽量引用 `ACTIVE_TASK_LIST` 中的任务编号
  - 只保留阶段性结论、交付物、验证结果和后续优先级，不重复写调试细节
  - 如果某个任务没有真正达到验收标准，不能在 `daily-report` 中写成“已完成”
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
  - `daily-sessions` 负责回答“下次从哪里继续做”
  - `daily-report` 负责回答“这次最终交付了什么”


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

- 所有关键操作需在用户确认后执行
- 避免丢失上下文信息
- 保持上下文的连续性和一致性
- 在不明确任务时，优先向用户确认

---
