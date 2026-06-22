# Stage 11 系统管理、自动化与告警实施日志

## Current Snapshot

- Stage：`Stage 11 系统管理、自动化与告警`
- 当前活动：`RT-S11-003 可观测性和运行追踪`
- 当前状态：`RT-S11-001`、`RT-S11-003`、`RT-S11-007` 已接受；Stage 11 仍在进行中
- 当前 Task：`RT-S11-003 可观测性和运行追踪` 已接受
- 下一可执行项：等待用户明确授权后续 Stage 11 task
- 不得自动开始：不得自动启动 `RT-S11-002` 及后续 Stage 11 task、scheduler、automation、alerting、recovery runtime、cost-control runtime、route retirement 或 Stage 12

## 2026-06-22 RT-S11-003 可观测性和运行追踪

### Status

`ACCEPTED`

### Scope

在不引入新 canonical run source-of-truth、数据库迁移、authorization policy 变化或 legacy route retirement 的前提下，为 Stage 11 落地有界的运行追踪聚合层：

- 为正式业务运行聚合稳定 `run_id` / step / prompt / data-fetch / backtest 视图；
- 把 `/system/runs` 从占位页替换为正式运行追踪页；
- 普通用户看到业务状态、影响和下一步；
- operator/admin 可查看步骤、关联记录、指纹和诊断细节；
- 对既有历史对象中无法证明稳定 runtime chain 的场景，明确返回 derived / partial / unavailable，而不是伪造 success。

本次未实现 `RT-S11-002`、`RT-S11-004`、`RT-S11-005`、`RT-S11-006`，未新增 scheduler / automation / alerting / recovery runtime / cost-control runtime，未改 formal strategy/rule/profile/current pointers，未退役 legacy routes，未把 Job / Workflow / Pipeline / Artifact 变成普通用户 formal input。

### Entry Verification

- Stage 10 Gate：`ACCEPTED`
- Stage 11 Bootstrap：`READY`
- `RT-S11-001`：`ACCEPTED`
- `RT-S11-007`：`ACCEPTED`
- `RT-S11-003`：按冻结顺序为下一允许 Task
- working tree before edits：clean
- 未触发 `ESCALATION_REQUIRED`：未新增 migration、未改 auth policy、未重写 cross-stage contract、未建立第二 formal source-of-truth

### Implementation Notes

- backend
  - 新增 `src/services/system_run_trace_service.py`
    - 聚合 `PromptRun`、`BacktestRun/BacktestResult`、`DailyRuleSelection`、`TradingDayPlan`、`PostMarketReview` 以及关联 `DatasetSnapshot`、`MarketSnapshot`
    - 优先复用已持久化 `run_id/source_run_id`
    - 对历史 daily/post-close 对象无法证明 runtime chain 时，只暴露 derived `run_id` 并把 attempt 标记为 `unavailable`
    - 统一输出步骤、Prompt 调用、数据抓取、回测证据和 admin diagnostics
  - `api/routers/ui/system.py`
    - 新增 `/api/ui/v1/system/runs`
    - 依据 `principal.role` 分层返回普通业务信息与 admin/operator 诊断字段
  - `src/services/daily_rule_selection_service.py`
    - 新建正式每日规则选择时写入稳定 `source_run_id`
  - `src/services/daily_trading_plan_service.py`
    - 新建正式每日交易计划时写入稳定 `source_run_id`
- frontend
  - `web/src/types/system.ts`、`web/src/lib/api/system.ts`
    - 新增 system run trace response / item / step / prompt / data fetch / backtest types 与 client
  - `web/src/pages/system/index.tsx`
    - `/system/runs` 从占位页改为正式运行追踪页
    - 普通用户仅看到业务状态、真实影响、处理方式和下一步
    - operator/admin 额外看到“查看运维诊断详情”和关联记录

### Contract Checklist

- every formal business run has or exposes stable `run_id`: pass
  - `PromptRun` / `BacktestRun` 直接复用 persisted `run_id`
  - `DailyRuleSelection` / `TradingDayPlan` 新对象写入 `source_run_id`
  - 历史无 persisted source 的 formal object 通过 API 暴露稳定 derived `run_id`，并把 attempt state truthfully 标为 `unavailable`
- legacy job/workflow/prompt/backtest IDs stay out of ordinary business inputs: pass
- retry/attempt information is separated from stable `run_id`: pass
- steps expose step_id / label / status / time / duration / error / retry_count / refs / repair_guidance: pass
- prompt calls expose model/provider/version/schema/hash/validation/retry/tokens/cost/time/linked object: pass
- data fetches expose source/provider/date range/trade date/slot/coverage/timestamps/quality/missing ranges/repair guidance: pass
- backtests expose dataset snapshot / fingerprints / rule fingerprint / market-state model / engine / decision-time policy / reproducibility / coverage / limitations: pass
- normal users see business status and next action: pass
- admin/operator can see diagnostics, linked IDs and raw metadata: pass
- missing / partial / unavailable / degraded / invalid / conflict states remain truthful: pass
- preserved RT-S11-007 happened / affected / repair_guidance contract: pass

### Verification

- backend/API
  - `python -m pytest tests/api/routers/ui/test_ui_system_runs.py tests/unit/services/test_system_run_trace_service.py -q`
  - `python -m pytest tests/api/routers/ui/test_ui_system_dashboard.py tests/api/routers/ui/test_ui_system_runs.py -q`
  - `python -m pytest tests/unit/services/test_daily_trading_plan_service.py tests/unit/services/test_backtest_application_service.py -q`
- frontend
  - `pnpm vitest run src/lib/api/system.test.ts src/pages/system/index.test.tsx`
  - `pnpm typecheck`
- safety / terminology
  - `git diff --check`
  - `rg -n '"run_id"|"job_id"|"workflow_run_id"|"prompt_run_id"|"config_path"|"Job"|"Workflow"|"Pipeline"|"Artifact"' web/src/pages/system/index.tsx web/src/pages/system/SystemHubPage.tsx`

### Result

- `tests/api/routers/ui/test_ui_system_runs.py` + `tests/unit/services/test_system_run_trace_service.py`: passed (`4` tests)
- `tests/api/routers/ui/test_ui_system_dashboard.py` + `tests/api/routers/ui/test_ui_system_runs.py`: passed (`3` tests)
- `tests/unit/services/test_daily_trading_plan_service.py` + `tests/unit/services/test_backtest_application_service.py`: passed (`44` tests)
- `pnpm vitest run src/lib/api/system.test.ts src/pages/system/index.test.tsx`: passed (`13` tests)
- `pnpm typecheck`: passed
- `git diff --check`: passed
- grep:
  - no quoted internal runtime terms leaked into `/system/runs` or `SystemHubPage` ordinary-user copy
  - remaining `run_id` code reference in `index.tsx` is implementation identifier, not rendered business input

未运行：

- browser E2E：本次为 focused system-management UI/API task，未运行
- 全仓 pytest / 全量 vitest：本次未修改无关模块，不做全量回归

### Residual Risks

- 历史 `DailyRuleSelection` / `TradingDayPlan` / `PostMarketReview` 记录中，部分运行链路缺少 persisted runtime attempt evidence；当前页面会 truthfully 以 derived `run_id` + unavailable attempt state 呈现，但无法回填真实历史 retry chain
- `PostMarketReview` 仍无独立 `source_run_id` 字段；本次仅通过 formal object identity 暴露稳定 run_id，并把缺失 runtime chain 明确标记为 partial
- `/system/runs` 当前聚合的是 bounded formal run-trace view，不是全量 scheduler / automation / alert runtime；这些仍属于后续 Stage 11 task

### Acceptance Conclusion

`RT-S11-003` is `ACCEPTED` under the frozen Stage 11 contract.

Current conclusion：

- `/system/runs` 现已提供正式运行追踪页，而不是占位说明；
- 普通用户只需理解业务状态、影响和下一步，不需要理解 `job_id` / `workflow_run_id` / `prompt_run_id`；
- operator/admin 现在可在系统管理中查看步骤、Prompt 调用、数据抓取、回测证据和关联诊断元数据；
- 对无法证明稳定历史 runtime chain 的旧记录，页面会明确呈现 partial / unavailable，而不是伪造完整成功链路；
- Stage 11 仍为 `[-] 进行中`，不得自动开始 `RT-S11-002`、`RT-S11-004`、`RT-S11-005`、`RT-S11-006` 或 Stage 12。

### 2026-06-22 Review Repair

针对 original Task Card 的复核发现一处 bounded gap：

- backend/API 已经返回 `prompt_calls`、`data_fetches`、`backtests`，但 `/system/runs` admin 视图最初没有把这些 technical details 渲染出来，导致“管理员查看技术详情”的页面证据不完整；
- backtest trace 只有 `rule_version_fingerprint` / `engine_version`，缺少 Task Card 明确要求的“规则版本”和“代码版本”字段表达。

本次 repair 保持 `RT-S11-003` 范围不变，只补齐缺失项：

- `src/services/system_run_trace_service.py`
  - backtest trace 改为显式输出 `rule_version`（id / version_no / fingerprint）和 `code_version`
- `web/src/types/system.ts`
  - 同步更新 backtest trace 类型
- `web/src/pages/system/index.tsx`
  - admin/operator 诊断详情中新增 Prompt 调用、数据抓取、正式回测证据三个技术细节区块
- `tests/unit/services/test_system_run_trace_service.py`
  - 新增 backtest rule/code version 暴露断言
- `tests/api/routers/ui/test_ui_system_runs.py`
  - 补齐 run trace fixture 中的 data fetch / backtest payload
- `web/src/pages/system/index.test.tsx`
  - 补齐 admin 技术详情渲染断言，并修正文案匹配为 `代码版本：engine-v5`

Review repair focused verification：

- `python -m pytest tests/api/routers/ui/test_ui_system_runs.py tests/unit/services/test_system_run_trace_service.py -q` → passed (`5 passed`)
- `pnpm vitest run src/lib/api/system.test.ts src/pages/system/index.test.tsx` → passed (`13 passed`)
- `pnpm typecheck` → passed
- `git diff --check` → passed

## 2026-06-22 RT-S11-007 用户友好错误

### Status

`ACCEPTED`

### Scope

在不重做全局 API error envelope、authorization policy 或 canonical run source-of-truth 的前提下，为 Stage 11 相关共享错误组件和系统管理页面补齐统一的用户友好错误契约：

- 每个用户可见错误状态明确展示：
  - `发生了什么`
  - `影响什么`
  - `应该怎么处理`
- 普通用户仅看到业务化说明与下一步动作；
- operator/admin 才能展开运维诊断详情；
- `invalid` / `conflict` / `degraded` 状态不再被统一压成 generic unavailable；
- `Job failed` 不再作为普通用户唯一可见错误文案。

本次未修改 backend/API response shape，未新增 scheduler、automation、alerting、recovery runtime、cost-control runtime，未修改 Stage 11 route grouping，未启动 Stage 12。

### Delegation

使用 `refactor-orchestrator`。Parent 明确派发了 1 个 bounded `refactor_executor_mini` 作为辅助实现通道，但该子代理只完成 scoped read-through 与 surface mapping，未交付最终 patch 或验证结果。

Parent 收回关键路径，直接完成实现、verification、diff review、文档更新与最终 acceptance decision。

### Entry Verification

- Stage 10 Gate：`ACCEPTED`
- Stage 11 Bootstrap：`READY`
- `RT-S11-001`：`ACCEPTED`
- Stage 12：未开始
- 本次实现前 working tree：仅包含 RT-S11-007 当前改动
- 未触发需要 `ESCALATION_REQUIRED` 的全局 envelope / auth / run_id redesign 条件

### Implementation Notes

- `web/src/components/layout/business-page-shell.tsx`
  - 扩展共享页面状态为 `degraded` / `invalid` / `conflict`
  - 在错误/受限状态卡片中显式展示“发生了什么 / 影响什么 / 应该怎么处理”
  - `degraded` 状态允许继续显示下一步业务动作
- `web/src/components/layout/product-page-adapter.tsx`
  - 运维诊断详情从 admin-only 放宽到 operator/admin，与 Stage 11 frozen visibility contract 对齐
- `web/src/components/state/ErrorState.tsx`
  - 新增 happened / affected / repairGuidance 共享契约字段
  - 普通用户隐藏 raw diagnostic detail；operator/admin 才能展开“查看运维诊断详情”
  - category badge 改为业务中文标签
- `web/src/lib/error-recovery.ts`
  - shared recovery builder 统一返回 happened / affected / repairGuidance
- `web/src/pages/system/index.tsx`
  - `invalid` / `conflict` / `insufficient_coverage` 分别映射到 `invalid` / `conflict` / `degraded`
- `web/src/features/system-status/system-status-panel.tsx`
  - product-mode 错误改为共享业务错误组件，raw payload 仅进入 operator/admin 诊断详情
- `web/src/features/market-datasets/market-dataset-viewer-state.ts`
  - 补齐新 `ErrorRecoveryState` 契约字段，保证 shared typecheck 通过

### Contract Checklist

- errors include `happened` / `affected` / `repair_guidance`: pass
- normal UI has no raw stack-only error: pass
- normal UI has no `Job failed`-only message: pass
- permission denied / unavailable / partial / degraded / invalid / conflict / failed operation states have focused frontend tests: pass
- admin diagnostic detail separated from normal business copy: pass
- `config_path` not exposed as ordinary Web input: pass
- Job / Workflow / Pipeline / Artifact not exposed as ordinary business inputs by this task: pass
- System Management grouping from `RT-S11-001` remains intact: pass
- backend/API error envelope unchanged: pass

### Verification

- `pnpm vitest run src/components/state/ErrorState.test.tsx src/components/layout/business-page-shell.test.tsx src/components/layout/product-page-adapter.test.tsx src/pages/system/index.test.tsx src/pages/system/system-pages.test.tsx src/features/system-status/system-status-panel.test.tsx src/lib/error-recovery.test.ts`
- `pnpm typecheck`
- `rg -n "Job failed|Job|Workflow|Pipeline|Artifact|config_path|run_id|prompt_run_id" web/src/components/state web/src/components/layout web/src/pages/system web/src/features/system-status web/src/features/system-management web/src/features/market-datasets`
- `git diff --check`

### Result

- Targeted Vitest: passed (`7` files, `46` tests)
- Typecheck: passed
- `git diff --check`: passed
- grep:
  - no new ordinary-user copy exposure in changed shared components/system pages
  - remaining matches are limited to compatibility dataset deep-links, internal imports, and tests; no new Stage 11 formal user input was introduced

未运行：

- backend/API tests：未修改 backend/API contract
- browser E2E：本次为 focused shared frontend error contract task，未运行

### Residual Risks

- compatibility dataset viewer 仍保留 `/jobs` / `/artifacts` deep-link，属于 legacy compatibility surface；本次仅补齐共享 error contract，不改变其 route policy
- 其他非 Stage 11 shared pages 继续通过同一个 `ErrorState` 受益于新契约，但未逐页做人工 copy 审核；Stage 12 最终交付前仍需统一做全站用户术语复核
- operator 现可查看运维诊断详情，符合 frozen contract；如果后续要细分 operator/admin 诊断粒度，应在单独 Task 中冻结更细权限语义

### Acceptance Conclusion

`RT-S11-007` is `ACCEPTED` under the frozen Stage 11 contract.

Current conclusion:

- 普通用户现在能看到业务化错误解释、影响范围和明确修复动作；
- operator/admin 才能进入诊断详情，技术细节与普通错误说明已分层；
- `invalid` / `conflict` / `insufficient_coverage` / failed operation 状态在系统管理正式页中被真实表达，而不是 generic success/unavailable；
- Stage 11 仍为 `[-] 进行中`，不得自动开始 `RT-S11-002` / `RT-S11-003` / `RT-S11-004` / `RT-S11-005` / `RT-S11-006` 或 Stage 12。

## 2026-06-22 RT-S11-001 系统管理入口

### Status

`ACCEPTED`

### Continuation (final repair / acceptance verification)

- continuation inspected latest committed RT-S11-001 at `1ad91688ce1932368a055543c0bcbe54e4f055ef`.
- verified committed code already mapped `/market/datasets` to `/system/data` in `web/src/app/route-config.tsx` legacy metadata.
- verification also found the committed `/system` UX only implied this mapping through generic “回测数据集” copy inside the `数据源` group; `/system/data` itself did not yet expose a visible compatibility link for `/market/datasets`.
- bounded repair added a visible `数据源兼容入口` section to `/system/data`, including `回测数据版本详情 -> /market/datasets`, while keeping `/market/datasets` as a compatibility route and without introducing any new business input.
- no other Stage 11 task, authorization policy, scheduler, automation, alerting, recovery runtime, cost-control runtime, legacy route retirement, or Stage 12 behavior was added.

### Scope

将 `/system` 从跳转页调整为系统管理分组落地页，并保持普通业务页面留在系统管理之外。新的落地页按角色展示常用状态/修复入口与完整系统管理分类，覆盖：

- `Profile 配置`
- `数据源`
- `数据与调度`
- `任务运行`
- `失败与告警`
- `数据库与备份`
- `权限与审计`

同时更新相关页面文案与测试，确保普通用户只看到状态和修复入口，管理员/操作员可看到更完整的管理分类说明。

本次未实现 `RT-S11-002`、`RT-S11-003`、`RT-S11-004`、`RT-S11-005`、`RT-S11-006`、`RT-S11-007`，未新增 scheduler、automation、alerting、recovery runtime、cost-control runtime，未退役 legacy routes，未修改 formal strategy/rule/profile/current pointers，未引入新的 canonical run source-of-truth。

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定委派 1 个 bounded frontend `refactor_executor_mini`：

- `Executor Gamma`：限定在 `route-config`、`/system` hub、`system-management workspace` 和 focused frontend tests 范围内完成实现草稿。

Parent 保留 contract review、compatibility mapping 判断、focused verification、bounded repair、文档更新和最终 acceptance decision。

### Entry Verification

- Stage 10 Gate：`ACCEPTED`。
- Stage 11 Bootstrap：`READY`。
- `RT-S11-001`：是下一个允许执行的 Task。
- Stage 12：未开始。
- 本次实现前 working tree：clean。
- 本次实现前完整 diff：empty。
- 未发现需要新的 authorization policy、legacy route retirement、formal data input 变更、canonical run source-of-truth 变更或 Stage 12 work。

### Implementation Notes

- `web/src/app/route-config.tsx`：`/system` 改为渲染 `SystemPage`，不再立即跳转到 `/system/status`。
- `web/src/pages/system/SystemHubPage.tsx`：重建系统管理落地页，加入常用入口、使用说明和按角色分层的分类卡片。
- `web/src/pages/system/DatabaseMigrationPage.tsx`：移除面向普通用户的 `Job` 文案。
- `web/src/features/system-management/system-management-workspace.tsx`：系统管理页面文案改为业务化表达，保持后台任务与运行审计的分区说明。
- `web/src/pages/system/index.test.tsx`：新增管理员、操作员和普通用户可见性断言。
- `web/src/app/route-config.test.tsx`：更新 `/system` 与 `/market/datasets` 的 legacy 元数据期望。
- `web/src/app/router-auth.test.tsx`：验证 viewer/operator 可直接访问正式 `/system` 入口。
- continuation bounded repair：
  - `web/src/pages/system/index.tsx`：在 `/system/data` 正式页增加“数据源兼容入口”，显式展示市场数据、市场快照、回测数据版本详情、盘前盘后数据和历史行情等 legacy deep-link。
  - `web/src/pages/system/index.test.tsx`：新增 focused assertion，验证 `/system/data` 内可见 `回测数据版本详情` 且链接到 `/market/datasets`。

### Contract Checklist

- System Management 七类分组：pass。
- profile / market / jobs / workflows / artifacts / alerts / existing system pages 均有明确系统管理 placement 或 compatibility mapping：pass。
- business pages 仍保持在 System Management 之外：pass。
- primary navigation 仍为 business-first 七项：pass。
- ordinary-user / operator / admin visibility 有 focused tests：pass。
- 未把 `config_path` 作为 Web formal input 暴露：pass。
- 未把 Job / Workflow / Pipeline / Artifact 记录变成 formal business input：pass。
- 未新增 scheduler / automation / alert runtime：pass。
- 未退役 legacy routes：pass。
- 未变更既有 role policy，仅在现有 `viewer/operator/admin` 权限上做入口可见性分层：pass。

### Verification

- `pnpm vitest run src/app/route-config.test.tsx src/app/router-auth.test.tsx src/components/layout/sidebar.test.tsx src/pages/system/index.test.tsx src/pages/system/system-pages.test.tsx src/features/system-management/system-management-workspace.test.tsx`
- `pnpm typecheck`
- `rg -n "Job|Workflow|Pipeline|Artifact|Provider|config_path|prompt_run_id|run_id" web/src/pages/system web/src/features/system-management web/src/app/route-config.tsx`
- `git diff --check`

### Result

- Targeted Vitest: passed (`6` files, `49` tests).
- Typecheck: passed.
- diff --check: passed.
- grep: still reports internal import symbols in `route-config.tsx` and `system-management` test/helper imports, but no new user-facing `/system` hub copy or button labels expose those terms.
- continuation re-verification:
  - Targeted Vitest: passed (`6` files, `50` tests).
  - Typecheck: passed.
  - focused mapping result: `/market/datasets` is now evidenced in two places:
    - route compatibility metadata maps it to `/system/data`;
    - `/system/data` visibly exposes `回测数据版本详情` linking to `/market/datasets`.

未运行：

- backend/API tests：本次未修改 backend 或 API contract
- browser E2E：本次未运行；当前为 focused frontend regrouping task

### Residual Risks

- 兼容页面如 `/jobs`、`/workflows`、`/artifacts`、`/market/*` 仍保留 legacy implementation 和部分技术标识；本次仅要求它们具备系统管理归属，不在 `RT-S11-001` 内退役。
- `Profile 配置` 作为冻结分组标题保留中英混合写法；当前符合 bootstrap contract，但后续若要统一为纯中文，应在不改 contract 语义前提下单独评估。
- `/system/runs` 目前仍承载运行、告警和附件兼容入口；更细粒度 observability/run-trace separation 仍属于 `RT-S11-003`。

### Acceptance Conclusion

`RT-S11-001` is `ACCEPTED` under the frozen Stage 11 contract.

Current conclusion：

- 低频管理能力现已通过正式 `/system` 入口聚合；
- daily business pages 仍保持业务优先，不要求普通用户依赖系统管理完成日常工作；
- 管理分组、兼容映射和可见性边界满足当前 Stage 11 frozen acceptance criteria；
- `/market/datasets` 已明确映射在 `/system/data` 下，且该映射现在对系统管理页面读者可见；
- Stage 11 仍为 `[-] 进行中`；仅 `RT-S11-001` 已接受。

Next allowed action：wait for explicit user authorization for `RT-S11-007 用户友好错误`，或按冻结顺序执行 `RT-S11-003 可观测性和运行追踪`。Do not start `RT-S11-002`、`RT-S11-003`、`RT-S11-004`、`RT-S11-005`、`RT-S11-006`、`RT-S11-007` automatically, and do not start Stage 12.

## 2026-06-22 Stage 11 Bootstrap / Planning

### Status

`READY`

### Scope

本次只执行 Stage 11 bootstrap / contract freezing：

- verify Stage 10 entry state;
- map existing Stage 11-relevant code and tests;
- freeze Stage 11 source-of-truth contracts;
- split `RT-S11-001` through `RT-S11-007` into safe implementation order;
- define per-task acceptance criteria;
- classify Stage 10 residual risks;
- create Stage 11 implementation plan and log;
- update the main implementation log.

本次未实现生产代码、未新增 scheduler、未新增 automation runtime、未新增 alerting runtime、未新增 recovery runtime、未新增 cost-control runtime、未修改 UI 代码、未变更业务数据、未退役 legacy routes、未启动 Stage 12。

### Delegation

使用 `refactor-orchestrator`。Parent 明确决定委派 2 个 read-only `refactor_explorer_mini`，因为 Stage 11 bootstrap 是跨后端和前端的 read-heavy mapping：

- Backend Explorer：system/config/ops、scheduler/recovery、job/workflow/prompt run、cost、data time semantics、backup/restore、audit、tests。
- Frontend Explorer：route/navigation/visibility、system pages、API clients/types、error components、business pages、legacy terms、tests。

未委派 Executor。Bootstrap 禁止生产代码实现。Parent 保留契约冻结、Task order、risk classification、acceptance criteria 和 bootstrap decision。

### Entry Verification

- Stage 10 Gate：`ACCEPTED`。
- `RT-S10-001`：accepted。
- `RT-S10-002`：accepted。
- `RT-S10-003`：accepted。
- `RT-S10-004`：accepted。
- Stage 11：本次 bootstrap 前未开始。
- Stage 12：未开始。
- Bootstrap 前 working tree：clean。
- Bootstrap 前完整 diff：empty。
- Baseline commit：`351e58581d62850d4155800ad38935fad05cb3a2`。

### Existing Code Map

#### System Management / Profile / Config

- `web/src/app/route-config.tsx` already defines canonical `/system` routes and hidden compatibility routes.
- `web/src/pages/system/*` and `web/src/features/system-management/*` are existing system/admin UI surfaces.
- `api/routers/ui/system.py`, `api/routers/ui/settings.py`, `api/routers/ui/profiles.py`, `api/routers/ui/ops.py`, `api/routers/ui/system_data.py`, `api/routers/ui/security_audit.py`, `api/routers/ui/job_audits.py`, and `api/routers/ui/data_audits.py` expose system-facing APIs.
- `src/services/system_service.py`, `src/services/config_profile_service.py`, `src/services/runtime_config.py`, and `src/services/config_migration_service.py` are current profile/config/service entry points.

#### Automation / Recovery / Scheduling

- `src/services/data_scheduling_service.py` defines the formal `system-data-operation` lane.
- `src/services/job_service.py` persists job state, retry fields, stale-job recovery, heartbeat, progress, runtime state, and audit events.
- `src/services/ops_service.py` exposes backup/restore/stale-job recovery wrappers.
- `src/services/article_pipeline_schedule_service.py` remains an in-memory scheduler compatibility path and is not frozen as the Stage 11 durable scheduler contract.

#### Observability / Run Tracking

- `jobs` / `job_audit_events`, `workflow_runs` / `workflow_run_steps`, `prompt_runs`, `backtest_runs`, `backtest_results`, and daily business objects already contain partial run/provenance fields.
- No unified Stage 11 run-trace query contract is currently implemented.

#### Cost / Incremental Control

- `ArticleRevision.content_hash`, prompt runtime cache lookup, `PromptRun.token_usage`, `PromptRun.cost_amount`, backtest request/result fingerprints, and snapshot fingerprints are existing primitives.
- No dedicated Stage 11 LLM cost/budget summary or cache-state UI contract is currently implemented.

#### Data Time Semantics

- `MarketSnapshot` has the strongest current time contract: `trade_date`, `slot`, `captured_at`, `available_at`, `effective_at`, source/provider-like fields, and quality status.
- `DatasetSnapshot` has immutable fingerprints and `available_at` / `frozen_at`, but does not uniformly carry all Stage 11 required time fields.
- Backtest service already enforces point-in-time snapshot binding in Stage 6 paths.

#### Error Handling

- Backend `ServiceResult` and frontend `BusinessPageShell` / `ProductPageAdapter` / `ErrorState` provide a base for user-friendly errors.
- Compatibility pages can still expose technical terms and internal categories.

### Frozen Contracts

Stage 11 global contracts are frozen in:

- [Stage 11 implementation plan](../refactor-implementation-plans/stage-11-implementation-plan.md)

Key frozen points:

- Low-frequency management belongs under System Management; daily business pages remain simple.
- Ordinary users do not need System Management for normal daily work.
- Admins can locate and repair data, scheduling, runtime, backup/restore, permission, audit, and failure issues.
- Legacy `Job` / `Workflow` / `Pipeline` / `Artifact` records do not become formal business inputs.
- `config_path` must not return as a Web formal input.
- Missing data remains unavailable/partial/conflict/invalid/degraded.
- Automation cannot silently publish, overwrite, approve, or execute user-impacting decisions.
- Stage 11 does not retire legacy routes unless explicitly scoped later.
- Stage 12 does not start from this bootstrap.

### Task Order

1. `RT-S11-001 系统管理入口`
2. `RT-S11-007 用户友好错误`
3. `RT-S11-003 可观测性和运行追踪`
4. `RT-S11-002 自动化和恢复`
5. `RT-S11-005 数据时间语义`
6. `RT-S11-004 成本与增量控制`
7. `RT-S11-006 灰度迁移和回滚`

### Task Combination Rules

- `RT-S11-001 + RT-S11-007`：可以，同 Session，前提是只涉及入口、文案、错误展示和 focused tests。
- `RT-S11-002 + RT-S11-003`：有条件，同 Session 串行，必须先实现 observability。
- `RT-S11-004 + RT-S11-005`：有条件，同 Parent Session 多批次，必须先完成 time semantics。
- `RT-S11-006`：单独且最后。
- 不得组合 Stage 11 与 Stage 12。

### Per-Task Acceptance Criteria

#### RT-S11-001

- System Management groups Profile 配置、数据源、数据与调度、任务运行、失败与告警、数据库与备份、权限与审计.
- Existing profile/data/runtime/failure/backup/audit pages have clear System Management placement or compatibility mapping.
- Business pages remain outside System Management.
- Ordinary-user and admin-user visibility is tested.
- `config_path` and internal Job/Workflow/Pipeline/Artifact concepts are not formal Web inputs for ordinary business flows.

#### RT-S11-002

- Scheduled tasks, retry, resume, backfill, LLM batch recovery, night jobs, and health checks have bounded behavior.
- Retry/resume/backfill is idempotent and bounded.
- Notify-only / automatic retry / admin approval boundaries are explicit.
- Automation cannot publish, overwrite, approve, or execute user-impacting decisions.

#### RT-S11-003

- Every formal business run exposes stable `run_id`.
- Steps record status, start/end time, error, retry count, and repair guidance.
- Prompt/data/backtest provenance is visible with user/admin separation.
- Normal users see business status; admins see technical details.

#### RT-S11-004

- Article hash/dedupe, prompt cache, concurrency, retry caps, incremental profile updates, backtest reuse, metric cache, and LLM cost stats have explicit contracts.
- Cache invalidation includes required fingerprints/versions.
- Stale/unavailable cache states are not hidden as success.

#### RT-S11-005

- Required time fields are present or explicitly mapped for relevant objects.
- Pre-market, post-market, and backtest enforce point-in-time availability.
- Later-filled data does not become earlier-available data.
- Missing/late data shows impact and repair guidance.

#### RT-S11-006

- Rollout path follows 新旧链路对照 → 新链路只读展示 → 小范围启用 → 新链路成为默认 → 旧入口只读 → 最终退役.
- Database, Prompt, and batch article processing have rollback or recovery evidence.
- Legacy routes are not retired unless separately authorized.

#### RT-S11-007

- Errors include happened, affected, and repair_guidance.
- Normal users receive business explanations; admins may see trace IDs and technical detail.
- No raw exception-only UI and no `Job failed`-only message.

### Residual Risks And Classification

- execution supplement missing：future execution supplement task; Stage 11 automation/recovery may observe/repair evidence but must keep execution-specific fields unavailable rather than false/success.
- caller-supplied `post_close_market_state_id`：Stage 11 observability/time-semantics hardening should validate/resolve canonical identity and preserve unavailable/invalid states.
- OpenAPI response-schema assertions partial：Stage 11 hardening for system/observability APIs; final Stage 12 Gate still requires full contract review.
- `/strategies/after-close` compatibility route remains：Stage 12 retirement follow-up; Stage 11 may surface compatibility visibility but must not retire it.
- browser E2E not run：final Stage 12 E2E unless a focused Stage 11 UI task changes relevant UI and requires targeted browser verification.

### Recommended Model / Session For RT-S11-001

- Recommended: `gpt-5.4` Task Implementation session.
- Use 0-1 mini Executor only for bounded frontend route/page grouping and focused tests.
- Escalate to `gpt-5.5` if implementation needs authorization-policy changes, route retirement, canonical run source-of-truth changes, or formal data input changes.

### Verification

Read-only / documentation verification completed:

- `AGENTS.md`
- `trade-strategy-ai/AGENTS.md`
- `docs/AI-Conversation-Templates.md`
- Stage 11-relevant sections of `docs/AI-Conversation-Project-Constraints-1.md`
- Stage 11-relevant sections of `docs/AI-Conversation-Project-Constraints-2.md`
- Stage 11 row/constraints from `docs/AI-Conversation-Task-Matrix.md`
- `docs/Trade-Refactor-TaskList.md`
- `docs/refactor-implementation-logs/stage-10.md`
- `docs/Refactor-Implementation-Log.md`
- current git status and full diff
- existing Stage 11-relevant code/tests listed above

No production tests were run because this bootstrap only updates planning/log documentation and does not change production code.

### Bootstrap Decision

`Stage 11 Bootstrap READY`

Next allowed action：wait for explicit user authorization for `RT-S11-001 系统管理入口`, or a permitted combined `RT-S11-001 + RT-S11-007` Task Session. Do not start implementation, scheduler, automation, alerting, recovery runtime, cost-control runtime, route retirement, or Stage 12 automatically.
