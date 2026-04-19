# 当前项目 Code Review

> 审查时间：2026-04-09
>
> 审查方式：静态代码审查 + `TaskList` 对齐检查。
>
> 说明：本次未执行全量测试，以下结论以当前仓库代码和文档状态为准。

## 1. 发现的问题

### 高优先级

1. `FastAPI` 手动触发接口在异步上下文中调用 `asyncio.run()`，运行时会失效
   - 证据：
     - `src/api/main.py:62-97` 的 `/run/pre_market`、`/run/after_close`
     - `src/api/main.py:109-120` 的 `/host/command`
     - `src/host/handler.py:21-45` 的 `handle_command()` 内部调用 `asyncio.run(...)`
   - 问题说明：
     - 这些接口本身是 `async def`，在 FastAPI 事件循环内再调用 `asyncio.run()`，实际服务运行时会触发事件循环嵌套问题。
     - 这不是边缘问题，而是接口主路径不可用。
   - 影响：
     - `P1-032`、`P1-035` 虽然有路由和 handler，但线上/本地服务形态下不可正常工作。

2. 复盘任务先落盘、后补字段，导致持久化任务与真实写回状态不一致
   - 证据：
     - `src/agents/manager_agent/agent.py:493-516`
   - 问题说明：
     - `review_task` 在 `502` 行先执行 `_append_task(review_task)` 写入 `agent_tasks.jsonl`。
     - 随后才在 `515-516` 行补写 `writeback_status=written` 和 `memory_id`。
     - 因为补写发生在落盘之后，磁盘中的任务记录缺少闭环追踪所需字段。
   - 影响：
     - `P2-109A` 标注的“评估结果 → 复盘任务 → TraderMemory 写回”只完成了内存对象更新，没有完成任务记录层面的闭环追踪。

### 中优先级

3. 文章查询接口声明支持 `trader_id` 过滤，但实现中完全未生效
   - 证据：
     - `src/api/routes/articles.py:21-30` 定义了 `trader_id`
     - `src/api/routes/articles.py:35-52` 查询条件未使用 `trader_id`
     - `src/api/routes/articles.py:75-80` 抽取出的过滤函数同样未处理 `trader_id`
   - 问题说明：
     - API 契约与实际行为不一致，会误导调用方。
   - 影响：
     - 查询结果可能包含错误交易员的数据，影响后续画像、回放和接口接入。

4. `TraderAgent` 的建议生成仍然是 Phase 0 模板化逻辑，画像/记忆只做轻量拼接
   - 证据：
     - `src/agents/trader_agent/agent.py:124-161`
   - 问题说明：
     - 核心建议仍基于 `last_price + default_target_pct/default_stop_pct`。
     - `rationale` 仍然保留 `"Phase0: rule-based idea from watchlist + mock price"`。
     - 画像与记忆仅影响文案拼接和固定加分，不构成真实的策略生成或校验闭环。
   - 影响：
     - 虽然这部分在 `TaskList` 中没有被错误标为完成，但它是当前主链路能力上限，直接限制 Phase 2 的推进。

### 低优先级

5. `build_trader_profiles()` 仍只基于文章元数据与 cluster 聚合，没有接入交易记录
   - 证据：
     - `src/trader_profile/service.py:144-175`
   - 问题说明：
     - 当前只读取 `BlogArticle` 与 `ArticleMetadata`，没有读取 `TradeLog`。
   - 影响：
     - 这进一步说明 `P2-102` 尚未完成，当前画像更接近“文章摘要画像”，而不是“文章 + 交易记录”的完整画像。

## 2. 未完成但被标记为完成的任务

### 明确错标

1. `P1-026J dedup_task 重构/扩展`
   - `TaskList` 位置：`docs/TaskList.md:140-142`
   - 代码证据：
     - `src/pipeline/tasks/dedup_task.py:19-64` 仅保留一个独立文件去重任务
     - 全仓搜索显示该任务没有接入当前 pipeline 主链路，只有测试引用
   - 结论：
     - 该任务当前不是“完成”，而是“保留了一个孤立实现，尚未接入或清理”。

2. `P1-032 实现手动触发接口`
   - `TaskList` 位置：`docs/TaskList.md:151-153`
   - 代码证据：
     - `src/api/main.py:62-97`
     - `src/host/handler.py:21-45`
   - 结论：
     - 接口路径存在，但在 FastAPI 异步运行模型下不可正常使用，不能算完成。

3. `P1-033 实现报告查询接口（日报/考核报告/复盘报告）`
   - `TaskList` 位置：`docs/TaskList.md:151-153`
   - 代码证据：
     - `src/api/routes/reports.py:60-247` 仅实现了 `daily` 和 `evaluation`
     - `src/api/routes/reports.py:254-320` 实现的是 `persona-route`
     - 仓库中未发现复盘报告查询/导出接口
   - 结论：
     - “日报/考核报告”已实现，但“复盘报告”没有对应接口，任务描述与实现不一致。

4. `P1-035 提供薄壳入口（FastAPI /host/command）`
   - `TaskList` 位置：`docs/TaskList.md:155-158`
   - 代码证据：
     - `src/api/main.py:109-120`
     - `src/host/handler.py:21-45`
   - 结论：
     - 路径存在，但同样受 `asyncio.run()` 问题影响，当前不能算真正完成。

5. `P2-109A 明确盘后复盘写回的最小闭环`
   - `TaskList` 位置：`docs/TaskList.md:195-199`
   - 代码证据：
     - `src/agents/manager_agent/agent.py:493-516`
   - 结论：
     - 内存写回做了，但“任务记录包含写回结果并可追踪”这一点没有真正完成，当前更适合标记为“部分完成”。

### 实现存在，但验收未完成，不应视为完全关闭

1. `P2-002`
   - `docs/TaskList.md:203`
   - 任务自身备注已写明：`待用真实LLM抽取结果验证概念标签覆盖度`

2. `P2-006`
   - `docs/TaskList.md:207`
   - 任务自身备注已写明：`待用真实抽取规则验证生成效果`

3. `P2-007`
   - `docs/TaskList.md:208`
   - 任务自身备注已写明：`待用真实抽取数据验证流程`

4. `P2-LLM-v1-001` ~ `P2-LLM-v1-004`
   - `docs/TaskList.md:239-243`
   - 这些项都写着待真实 API / 真实场景验证，当前只能算“代码实现完成，验收未完成”。

5. `P2-LLM-001` ~ `P2-LLM-003`
   - `docs/TaskList.md:245-248`
   - 同样仍处于“待真实抽取数据/错误场景/日志记录验证”状态，不适合完全关闭。

## 3. 下一步开发计划

1. 先修复运行闭环入口
   - 将 `src/host/handler.py` 改为异步接口，FastAPI 路由直接 `await`。
   - 为 `/run/pre_market`、`/run/after_close`、`/host/command` 增加集成测试。
   - 修复错误返回语义，避免业务失败仍返回普通成功响应。

2. 修复复盘闭环一致性
   - 在 `ManagerAgent.run_after_close()` 中先完成 `memory` 写回，再统一构造并落盘完整的 `review_task`。
   - 为 `writeback_status`、`memory_id` 增加回归测试，补足 `P2-109D`。

3. 清理 API 契约与 TaskList 偏差
   - 修复 `/articles` 的 `trader_id` 过滤。
   - 明确 `P1-033` 是补齐“复盘报告接口”，还是把任务描述改成“日报/考核报告接口”。
   - 明确 `P1-026J` 是接入 pipeline 还是删除无主实现。

4. 推进 Phase 2 主链路而不是继续扩散外围功能
   - 优先完成 `P2-102`、`P2-104`、`P2-105`、`P2-109B`、`P2-109D`。
   - Trader 画像应接入交易记录，而不仅是文章 metadata。
   - TradeIdea 生成要从“模板 + 固定权重”升级为“画像/记忆/市场数据驱动”的可解释生成。

5. 重新定义“完成”标准
   - 把“代码已写”与“真实数据验收通过”拆成两个状态。
   - 对带有“待真实验证”备注的任务，统一回退为“进行中”或新增单独验收子任务，避免 `TaskList` 继续失真。
