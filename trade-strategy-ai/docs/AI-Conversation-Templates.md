# Trade Strategy AI 重构对话模板

## 1. 使用说明

本文件用于指导你与 Codex、Claude Code、Cursor Agent 或其他代码 Agent 配合完成 `trade-strategy-ai` 重构。

使用原则：

1. 一次只执行一个明确 Task，或一个 Stage 中紧密关联的少量 Task。
2. 每次开始前要求 AI 读取 `AGENTS.md`、主 TaskList 和当前任务相关文档。
3. 每个任务完成后先 Review，再进入下一任务。
4. 未满足验收、未运行测试或存在阻塞时，禁止 AI 声称完成。
5. 所有重构文档只能在 `trade-strategy-ai/docs` 中生成和更新。
6. 不要一次要求 AI 连续完成多个 Stage。

---

# 2. 第一次开始重构

第一次只执行 Stage 0：现状审计和迁移矩阵。

```text
请开始执行 trade-strategy-ai 的重构任务。

在执行前，请严格按顺序读取：

1. AGENTS.md
2. trade-strategy-ai/docs/Trade-Refactor-TaskList.md
3. trade-strategy-ai/docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md
4. trade-strategy-ai/docs/PROMPT_REVIEW_AND_MIGRATION.md
5. trade-strategy-ai/docs/AUTHOR_PROFILE_PROMPT_FLOW.md

本次只执行：

RT-S0-001 现状审计
RT-S0-002 迁移矩阵

要求：

1. 这一轮只分析，不修改核心业务代码。
2. 全面检查当前前端路由、Sidebar、页面、API、Service、Job、Workflow、Pipeline、数据库模型、Prompt、OHLCV、Kaipan、市场状态、规则、回测、作者画像、策略、盘前和盘后实现。
3. 找出现有重复入口、重复 Schema、重复事实源和 legacy 实现。
4. 对每项现有能力标记：
   - 保留
   - 改造
   - 合并
   - 迁移
   - 兼容
   - 退役
5. 明确每个旧入口迁移后的新入口和退役条件。
6. 不要因为已有 TaskList 就假设代码已经符合文档，必须以实际代码为准。
7. 所有新生成和更新的文档只能放在 trade-strategy-ai/docs。
8. 更新 trade-strategy-ai/docs/Refactor-Implementation-Log.md。
9. 未完成审计和迁移矩阵前，不要开始 Stage 1。
10. 不要在未满足验收标准时标记完成。

输出文档：

- trade-strategy-ai/docs/Refactor-Current-State-Audit.md
- trade-strategy-ai/docs/Refactor-Migration-Matrix.md

完成后请按 AGENTS.md 的固定格式汇报：

任务：
状态：
已完成：
未完成：
修改文件：
数据库迁移：
已运行测试：
测试结果：
已知风险：
验收结论：
```

---

# 3. 第一次结果返回后的 Review

```text
请先不要开始下一阶段。

请对刚才完成的 RT-S0-001 和 RT-S0-002 做一次严格 Review：

1. 检查是否遗漏任何前端页面、API、数据库表、Prompt、Job、Workflow、调度和历史兼容入口。
2. 检查迁移矩阵是否为每个旧入口明确了目标入口和退役条件。
3. 检查是否发现第二套规则、策略、画像或数据事实源。
4. 检查是否有仅根据文档推断、但没有通过代码确认的结论。
5. 检查 Refactor-Implementation-Log.md 是否完整更新。
6. 对照 Stage 0 的出口条件，明确是否可以进入 Stage 1。

如果存在遗漏，请直接修正文档。
只有全部满足后，才把 Stage 0 标记为完成。
不要开始 Stage 1。
```

---

# 4. 后续继续任务的通用模板

```text
请继续执行 trade-strategy-ai 重构任务。

本次只执行：

[填写 Task ID 和任务名称]

执行前请读取：

- AGENTS.md
- trade-strategy-ai/docs/Trade-Refactor-TaskList.md
- trade-strategy-ai/docs/Refactor-Implementation-Log.md
- 当前任务依赖的设计、迁移和验收文档
- 当前任务涉及的实际代码和测试

要求：

1. 先确认前置任务和依赖是否已完成。
2. 先检查现有实现，不要重复建设。
3. 只执行本次指定任务，不要自行跨 Stage。
4. 可以修改 UI、前端、后端、数据库和 Prompt，只要有利于正式重构目标。
5. 不允许形成第二套正式入口、Schema 或事实源。
6. 不允许使用 Mock、硬编码、空接口或占位页冒充完成。
7. 必须处理数据迁移、兼容、错误状态和用户说明。
8. 必须运行所有受影响测试。
9. 无法运行的测试必须明确记录，不能声称通过。
10. 所有文档只能在 trade-strategy-ai/docs 中生成和更新。
11. 更新 Refactor-Implementation-Log.md。
12. 完成后对照任务验收标准和阶段出口条件做自查。
13. 不要自动开始下一个任务。

完成后按以下格式回复：

任务：
状态：
已完成：
未完成：
修改文件：
数据库迁移：
已运行测试：
测试结果：
已知风险：
验收结论：
```

---

# 5. 每个 Stage 完成后的 Review 模板

```text
请不要开始下一 Stage。

请对刚完成的 Stage [编号] 做一次严格 Review。

Review 内容：

1. 逐条检查该 Stage 中所有 Task 的验收标准。
2. 使用真实数据走通本 Stage 定义的用户演示路径。
3. 检查前端、后端、数据库、Prompt 和运行契约是否一致。
4. 检查是否仍有 Mock、占位、硬编码或未接通功能。
5. 检查是否新增了重复入口、重复 Schema 或第二套事实源。
6. 检查旧入口是否有兼容和退役计划。
7. 检查测试是否真实运行并通过。
8. 检查数据迁移是否可重跑、可恢复。
9. 检查用户界面是否仍出现不必要的开发术语。
10. 检查 Refactor-Implementation-Log.md 是否完整。

请输出：

- 已满足项
- 未满足项
- 阻塞项
- 需要修复的问题
- 是否满足 Stage 出口条件
- 是否允许进入下一 Stage

如果有问题，请直接修复并重新 Review。
在出口条件全部满足前，不要进入下一 Stage。
```

---

# 6. 新 Session 或中断后继续

```text
请继续 trade-strategy-ai 重构。

不要根据聊天记忆推断当前进度，请先读取：

1. AGENTS.md
2. trade-strategy-ai/docs/Trade-Refactor-TaskList.md
3. trade-strategy-ai/docs/Refactor-Implementation-Log.md
4. trade-strategy-ai/docs/Refactor-Current-State-Audit.md
5. trade-strategy-ai/docs/Refactor-Migration-Matrix.md
6. 当前已完成 Stage 的相关 Review 和验收文档
7. Git 当前分支、最近提交和未提交改动

然后输出：

- 当前正在执行的 Task ID
- 已完成的 Stage
- 当前任务已经完成的内容
- 尚未完成的内容
- 当前阻塞
- 下一步应执行的最小任务

确认实际状态后，只继续当前未完成任务。
不要重复已完成工作，也不要跳到后续 Stage。
```

---

# 7. AI 声称完成但需要核验

```text
你刚才声称任务已经完成。请重新按 AGENTS.md 的完成判定严格核验。

重点检查：

1. 是否使用真实数据而不是 Mock。
2. 前端页面是否实际调用正式 API。
3. 数据库迁移是否已经执行和测试。
4. 受影响测试是否真实运行。
5. 是否存在失败或未运行测试。
6. 页面是否覆盖 loading、empty、error、partial 和权限状态。
7. 用户是否能从正式主入口访问该功能。
8. 是否更新了实施记录和用户文档。
9. 是否存在已知未完成项。
10. 是否逐条满足任务验收标准。

请提供具体证据，包括：

- 修改文件
- API 路径
- 数据库迁移
- 测试命令和结果
- 实际用户操作路径
- 尚存风险

如果任何一项未满足，请把状态改为“进行中”或“阻塞”，不要继续声称完成。
```

---

# 8. AI 跑偏时的纠偏模板

```text
停止当前扩展工作，不要继续新增功能。

你当前实现可能偏离正式重构目标。请重新读取：

- AGENTS.md
- trade-strategy-ai/docs/Trade-Refactor-TaskList.md
- 最新重构方案
- 当前 Task 的验收标准

然后检查：

1. 是否新增了 TaskList 未定义的业务方向。
2. 是否创建了第二套入口、Schema、Service 或事实源。
3. 是否为了保留旧代码牺牲了用户流程。
4. 是否把开发工具页面换皮后当成用户产品。
5. 是否越过了当前 Stage。
6. 是否省略了迁移、测试或真实数据接入。

请撤销或修正偏离部分，只保留符合当前 Task 的实现。
修正后重新汇报当前真实状态。
```

---

# 9. 特殊任务 Prompt 模板

以下任务不建议只使用通用模板，应增加专用约束。

## 9.1 Stage 1：信息架构和首页

适用于：

- RT-S1-001
- RT-S1-002
- RT-S1-003

```text
请执行 Stage 1 的产品信息架构任务。

本次只执行：

[填写 RT-S1 Task]

要求：

1. 最终页面必须面向普通中国用户。
2. 普通用户主导航不得出现 Job、Workflow、Pipeline、Artifact、Provider 等开发术语。
3. 不得只更换 Sidebar 名称，必须重构用户操作路径。
4. 每个主要页面必须明确：
   - 页面用途
   - 输入
   - 处理状态
   - 输出
   - 下一步
5. 首页必须是“下一步操作中心”，不能是工具入口集合。
6. 未迁移完成的旧页面只能作为兼容入口，不能形成两个正式入口。
7. 所有页面必须覆盖 loading、empty、error、partial、permission denied 和 unavailable 状态。
8. 不使用 Mock 数据冒充正式完成。
9. 完成后使用真实数据演示用户从首页进入下一步操作。
10. 不要开始 Stage 2。
```

## 9.2 Stage 2：数据库和领域模型

适用于：

- RT-S2-001
- RT-S2-002
- RT-S2-003

```text
请执行 Stage 2 的领域模型和数据库重构任务。

本次只执行：

[填写 RT-S2 Task]

要求：

1. 先检查现有模型和表，不要直接新建第二套结构。
2. 明确每个旧模型迁移到哪个新模型。
3. 核心对象必须有稳定 ID、状态、版本和来源引用。
4. Prompt、规则、画像、策略、数据集和市场状态模型必须版本化。
5. 不得使用文件路径作为正式业务引用。
6. 数据库迁移必须：
   - 可安全重跑
   - 可恢复或回滚
   - 不静默丢失旧数据
   - 对无法迁移数据记录质量状态
7. 同步更新 Repository、Service、API、前端类型和测试。
8. 不得只创建表而不接入业务。
9. 提供迁移前后数据核对结果。
10. 不要开始 Stage 3。
```

## 9.3 Stage 3：Prompt 与文章处理

适用于：

- RT-S3-001
- RT-S3-002
- RT-S3-003

```text
请执行 Stage 3 的 Prompt 与文章处理任务。

本次只执行：

[填写 RT-S3 Task]

要求：

1. 接入 docs 和 prompts 中定义的新版本 Prompt。
2. Prompt、Pydantic Schema 和测试必须使用同一契约。
3. 保存 prompt_version、schema_version、输入引用和原始输出。
4. 文章未声明市场状态时必须输出 not_declared。
5. LLM 推断不能进入正式前置条件。
6. 不允许 LLM 编造止损、持有周期和参数。
7. 实现自动审核和人工审核 UI。
8. 自动审核通过只允许进入待回测。
9. 正式策略入选前仍需人工确认。
10. 黄金样本不要求用户提前提供：
    - 从现有文章中自动筛选 10～15 篇候选样本
    - 固定 article_id、内容版本、Prompt 版本和审核结果
11. 固定回归样本通过前，不得批量重跑全部 100+ 篇文章。
12. 批处理必须支持断点续跑、失败重试和增量更新。
13. 更新 Prompt 回归测试和实施记录。
14. 不要开始 Stage 4。

完成后请提供：

- Prompt 接入位置
- Schema 定义
- 固定样本列表
- 自动审核结果
- 人工审核操作路径
- 测试结果
- 未解决问题
```

## 9.4 Stage 4：规则审核、去重和规则族

适用于：

- RT-S4-001
- RT-S4-002
- RT-S4-003

```text
请执行 Stage 4 的规则管理任务。

本次只执行：

[填写 RT-S4 Task]

要求：

1. 自动审核必须以确定性规则为主，不得用另一个自由 LLM 做最终裁决。
2. 自动审核状态统一为：
   - 自动通过
   - 建议通过
   - 需要人工确认
   - 不可回测
   - 建议拒绝
3. 自动通过只表示可进入待回测，不表示正式可用。
4. 高风险、歧义、冲突、参数补充和策略入选规则必须人工审核。
5. 人工审核 UI 必须展示：
   - 原文证据
   - 自动审核原因
   - 风险等级
   - 模糊词和缺失字段
   - 数据依赖
   - 重复和冲突
6. 支持批量处理低风险规则。
7. 所有审核操作必须记录审核人、时间、原因和修改前后内容。
8. 建立规则指纹、规则族和参数变体，避免重复回测。
9. 不得误合并语义不同但表面相似的规则。
10. 不要开始 Stage 5。
```

## 9.5 Stage 5：OHLCV、Kaipan 和调度

适用于：

- RT-S5-001
- RT-S5-002
- RT-S5-003

```text
请执行 Stage 5 的基础数据和调度任务。

本次只执行：

[填写 RT-S5 Task]

要求：

1. OHLCV 是基础回测数据，支持首次历史回灌和每日盘后增量。
2. Kaipan 分盘前和盘后数据，不得混成一个无时间语义的数据集。
3. 核心数据记录：
   - trade_date
   - available_at
   - captured_at
   - effective_at
   - source
   - slot
4. 数据不足不得默认为 false、0 或条件已满足。
5. 回测前可以一键补齐数据，但回测过程中不得调用实时 Provider。
6. 普通用户只看到数据是否就绪、影响和修复操作。
7. 抓取、调度和技术日志放入系统管理。
8. 数据任务必须支持断点、重试、幂等和覆盖率检查。
9. 更新数据完整性和调度测试。
10. 不要开始 Stage 6。
```

## 9.6 Stage 6：回测和规则适用性

适用于：

- RT-S6-001
- RT-S6-002
- RT-S6-003
- RT-S6-004

```text
请执行 Stage 6 的回测和规则适用性任务。

本次只执行：

[填写 RT-S6 Task]

要求：

1. 每次回测固定 DatasetSnapshot。
2. 禁止回测过程中调用实时 Provider。
3. 严格防止未来数据泄漏。
4. 每个交易日使用当时已可获得的数据和市场状态。
5. 输出全周期和分市场状态结果。
6. 样本不足必须标记 insufficient_sample。
7. 区分：
   - OHLCV
   - OHLCV + 市场状态
   - OHLCV + 市场状态 + Kaipan
8. 缺失 Kaipan 时必须显示覆盖率和影响，不能当作规则失败。
9. RuleApplicabilityProfile 必须关联规则版本、数据版本和市场状态模型版本。
10. 回测结果必须可复现。
11. 不要开始 Stage 7。
```

## 9.7 Stage 7：作者画像

适用于：

- RT-S7-001
- RT-S7-002
- RT-S7-003
- RT-S7-004

```text
请执行 Stage 7 的作者画像任务。

本次只执行：

[填写 RT-S7 Task]

要求：

1. 作者画像不是用户画像，也不是作者真实实盘画像。
2. 必须拆分：
   - AuthorMethodProfile
   - AuthorRuleProfile
   - AuthorValidatedProfile
3. LLM 负责文章方法理解和解释。
4. 程序统计负责规则结构、数量、重复和冲突。
5. 回测负责优势和弱势市场状态验证。
6. 不得声称作者真实胜率、收益率、仓位、回撤或执行纪律。
7. 文章表达、规则结构和回测验证必须分区展示。
8. 支持时间分段画像，不能把方法变化强行平均。
9. 新文章、新规则和单日结果只生成画像草稿或累计证据。
10. 正式画像必须人工审核后发布。
11. 不要开始 Stage 8。
```

## 9.8 Stage 8：策略中心

适用于：

- RT-S8-001
- RT-S8-002
- RT-S8-003

```text
请执行 Stage 8 的策略中心任务。

本次只执行：

[填写 RT-S8 Task]

要求：

1. 正式 StrategyVersion 不得每天生成。
2. 策略必须包含规则池、基础权重、作者画像版本、风险、仓位、标的范围和市场状态政策。
3. 支持草稿、验证、审核、发布、当前使用和归档。
4. 支持样本外验证、版本比较和回滚。
5. 策略优化只能生成 StrategyRevisionProposal，不能直接覆盖正式策略。
6. 用户必须能理解策略由哪些规则和画像组成。
7. 正式策略入选规则必须人工确认。
8. 不要开始 Stage 9。
```

## 9.9 Stage 9：每日盘前

适用于：

- RT-S9-001
- RT-S9-002
- RT-S9-003

```text
请执行 Stage 9 的每日盘前任务。

本次只执行：

[填写 RT-S9 Task]

要求：

1. 自动检查 Kaipan、OHLCV、市场状态、正式策略和规则适用性。
2. 每天生成：
   - DailyRuleSelection
   - DailyStrategyInstance
   - TradingDayPlan
3. 不得每天生成新的正式 StrategyVersion。
4. 规则选择优先级：
   规则正式适用性
   > 当前市场状态
   > 正式策略
   > 数据质量
   > 作者验证画像
   > 作者方法画像
5. 页面必须展示启用、降权和暂停规则的原因。
6. 数据缺失时提供一键修复或明确降级。
7. 盘前计划必须可追溯到所有输入版本。
8. 用户日常操作应尽量只剩查看、调整和批准。
9. 不要开始 Stage 10。
```

## 9.10 Stage 10：每日盘后

适用于：

- RT-S10-001
- RT-S10-002
- RT-S10-003
- RT-S10-004

```text
请执行 Stage 10 的每日盘后任务。

本次只执行：

[填写 RT-S10 Task]

要求：

1. 对每个信号记录触发、执行、结果、MFE、MAE、收益、规则和市场状态。
2. 归因必须区分：
   - 数据问题
   - 市场状态问题
   - 规则问题
   - 策略组合问题
   - 执行问题
3. LLM 只负责校验和解释，不得重新计算程序指标。
4. 分别生成：
   - RuleOptimizationProposal
   - AuthorProfileRevisionProposal
   - StrategyRevisionProposal
5. 单日结果不得直接修改正式对象。
6. 页面固定展示：
   - 盘前预测
   - 实际结果
   - 差异
   - 成功原因
   - 失败原因
   - 建议操作
7. 用户可以接受、拒绝或继续观察建议。
8. 不要开始 Stage 11。
```

## 9.11 Stage 11：系统管理、可观测性和成本

适用于：

- RT-S11-001 至 RT-S11-006

```text
请执行 Stage 11 的系统管理和运行保障任务。

本次只执行：

[填写 RT-S11 Task]

要求：

1. 普通用户日常不依赖系统管理。
2. 所有业务运行有统一 run_id。
3. 记录步骤状态、时间、错误和重试。
4. Prompt 调用记录模型、版本、Token 和成本。
5. 数据抓取记录日期范围、覆盖率和时间语义。
6. 实现文章哈希、Prompt 缓存、并发限制和重试上限。
7. 实现灰度迁移、对照验证和回滚。
8. 错误信息必须告诉用户发生了什么、影响什么、如何处理。
9. 不得把技术日志直接暴露给普通用户。
10. 不要开始 Stage 12。
```

## 9.12 Stage 12：旧入口退役和最终交付

适用于：

- RT-S12-001
- RT-S12-002
- RT-S12-003

```text
请执行 Stage 12 的最终交付任务。

本次只执行：

[填写 RT-S12 Task]

要求：

1. 删除或隐藏已经迁移完成的旧入口。
2. 不允许新旧正式入口长期并存。
3. 使用真实数据完整走通：
   文章
   → 规则
   → 回测
   → 规则适用性
   → 作者画像
   → 策略
   → 盘前
   → 盘后
   → 优化建议
4. 完成 E2E、后端、前端、迁移和 Prompt 回归测试。
5. 完成面向用户的快速开始和完整使用手册。
6. 用户文档不得要求理解内部开发术语。
7. 任何最终验收项未满足，都不得宣布重构完成。
```

---

# 10. 推荐执行节奏

每次对话只做一种工作：

```text
实现一个 Task
或
Review 一个 Task
或
Review 一个 Stage
```

推荐节奏：

```text
实现
→ AI 自查
→ 严格 Review
→ 修复
→ Stage 验收
→ 进入下一任务
```

不要一次要求：

```text
完成 Stage 0 到 Stage 5
```

最常用的开场约束：

```text
先严格读取 AGENTS.md 和正式 TaskList。本次只执行指定 Task，不要跨 Stage；未满足验收、未完成测试或仍有阻塞时，禁止声称完成。
```


# 11. Prompt 调用编排核验模板

```text
请核验当前 Prompt 实现是否符合 trade-strategy-ai/docs/LLM-Prompt-Orchestration.md：

1. 单篇普通文章是否只调用一次 article_analysis_v1。
2. 是否只在 Schema 或局部字段失败时调用一次 article_analysis_repair_v1。
3. 是否避免逐篇调用作者画像 Prompt。
4. 是否只在低置信度、证据冲突或重要信号时调用 llm_attribution_v1。
5. 是否记录 Prompt、Schema、模型、Token、成本和 input_hash。
6. 是否对相同输入启用缓存和幂等。
7. 旧 Prompt 是否已停止产生正式数据。
8. 删除旧 Prompt 前是否满足全部退役验收。

如果任一项不满足，请修正后再标记 Prompt 任务完成。
```
