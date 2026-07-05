# Trade Strategy AI 重构执行包

包含：

- `docs/stage-12-user-docs/README.md`：Stage 12 正式用户、管理员和部署文档入口。
- `docs/stage-12-user-docs/Quick-Start.md`：普通用户快速开始。
- `docs/stage-12-user-docs/User-Manual.md`：普通用户完整使用手册。
- `docs/stage-12-user-docs/First-Time-Initialization.md`：管理员首次初始化指南。
- `docs/stage-12-user-docs/Daily-Pre-Market-Guide.md`：每日盘前说明。
- `docs/stage-12-user-docs/Daily-After-Close-Guide.md`：每日盘后说明。
- `docs/stage-12-user-docs/Data-Failure-Handling.md`：数据不足和失败处理说明。
- `docs/stage-12-user-docs/Admin-Operations-Guide.md`：管理员运维指南。
- `docs/stage-12-user-docs/Deployment-Runbook.md`：部署与运行手册。
- `docs/Trade-Refactor-TaskList.md`：AI 可执行主 TaskList。
- `docs/TaskList-Review.md`：基于前期讨论的 Review 结论。
- `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`：完整重构方案。
- `docs/PROMPT_REVIEW_AND_MIGRATION.md`：现有 Prompt 检查和迁移说明。
- `docs/AUTHOR_PROFILE_PROMPT_FLOW.md`：作者画像 Prompt 使用流程。
- `prompts/`：版本化 Prompt 套件。

建议 AI 开始前先阅读：

1. `docs/Trade-Refactor-TaskList.md`
2. `docs/trade-strategy-ai-web-refactor-plan-market-state-v2.md`
3. `docs/PROMPT_REVIEW_AND_MIGRATION.md`
4. `docs/AUTHOR_PROFILE_PROMPT_FLOW.md`

本版本新增：候选规则自动审核、人工审核工作台、批量审核、审核审计和正式策略入选前二次确认。

本版本新增：自动建立回归样本、阶段出口条件、可观测性、成本控制、数据时间语义和灰度迁移要求。


最终版新增：

- `prompts/concept_extraction_v1.md`
- `prompts/llm_attribution_v1.md`
- `prompts/article_analysis_v1.md`
- `prompts/article_analysis_repair_v1.md`
- `docs/LLM-Prompt-Orchestration.md`
- 旧 Prompt 完整退役和删除验收
