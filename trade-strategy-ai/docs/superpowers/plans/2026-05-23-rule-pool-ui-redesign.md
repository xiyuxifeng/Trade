# Rule Pool UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把规则池从单页审核工作台重构为「筛选列表页 + 规则详情页」两层结构，并补齐全量筛选选项、规则回测入口和 Job 跳转。

**Architecture:** 列表页只负责全量筛选、概览统计和规则浏览，详情页承接规则证据、适用性画像、审核动作、审计历史和回测提交。后端提供稳定的 `filter-options` 接口供前端下拉使用，列表点击行进入详情页，回测结果通过 `rule-pool-backtest` Job 和 `/jobs/:jobId` 统一追踪。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, React Router, TanStack Query, Vitest, Pytest

---

### Task 1: Stabilize rule-pool filter option contract

**Files:**
- Modify: `src/services/rule_pool_service.py`
- Modify: `api/routers/ui/rule_pool.py`
- Modify: `tests/unit/services/test_rule_pool_service.py`
- Modify: `tests/api/routers/test_rule_pool.py`
- Modify: `tests/api/test_ui_openapi_contract.py`

- [ ] **Step 1: Write the failing test**

新增测试，覆盖 `/api/ui/v1/rule-pool/filter-options` 返回完整下拉数据，并确认 OpenAPI 暴露该 GET 路由与响应 schema。

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/services/test_rule_pool_service.py tests/api/routers/test_rule_pool.py tests/api/test_ui_openapi_contract.py -q`

Expected: FAIL because `list_filter_options` 或路由/schema 还未完全对齐。

- [ ] **Step 3: Write minimal implementation**

让 `RulePoolService.list_filter_options()` 从全量规则池表读取 distinct 值，合并默认枚举后返回：

```python
payload = {
    "review_statuses": [...],
    "mapping_statuses": [...],
    "source_types": [...],
    "rule_types": [...],
    "instrument_focuses": [...],
}
```

在 `api/routers/ui/rule_pool.py` 中暴露 `GET /api/ui/v1/rule-pool/filter-options`，并返回稳定的 `RulePoolFilterOptionsResponse`。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/services/test_rule_pool_service.py tests/api/routers/test_rule_pool.py tests/api/test_ui_openapi_contract.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/rule_pool_service.py api/routers/ui/rule_pool.py tests/unit/services/test_rule_pool_service.py tests/api/routers/test_rule_pool.py tests/api/test_ui_openapi_contract.py
git commit -m "feat(rule-pool): add canonical filter options contract"
```

### Task 2: Rebuild the rule pool list page as a full-width filter-and-list workspace

**Files:**
- Modify: `web/src/features/rule-pool/rule-pool-list.tsx`
- Modify: `web/src/lib/api/rule-pool.ts`
- Modify: `web/src/types/rule-pool.ts`
- Modify: `web/src/pages/rule-pool/index.tsx`
- Modify: `web/src/pages/rule-pool/index.test.tsx`

- [ ] **Step 1: Write the failing test**

新增列表页测试，覆盖以下行为：
- 规则筛选卡独立整行展示
- 所有可枚举筛选项来自 `filter-options`
- `仅显示已映射规则` checkbox 不再存在
- `刷新` 按钮不再存在，取而代之的是 `搜索`
- `规则概览与列表` 合并到同一个 card
- 列表区域可独立滚动
- 点击某条规则行会跳转到 `/rule-pool/:ruleId`

- [ ] **Step 2: Run test to verify it fails**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm test -- src/pages/rule-pool/index.test.tsx`

Expected: FAIL because the current page structure and labels do not fully match the new design.

- [ ] **Step 3: Write minimal implementation**

在 `web/src/lib/api/rule-pool.ts` 增加 `listRulePoolFilterOptions()`。

在 `web/src/types/rule-pool.ts` 增加筛选选项响应类型。

在 `web/src/features/rule-pool/rule-pool-list.tsx`：
- 使用 `useQuery` 拉取筛选选项与规则列表
- 用下拉框替换所有可枚举输入
- 保留草稿态与已应用态，搜索时才发起列表查询
- 把 overview 和 list 合并在同一个 `SectionCard`
- 列表区域加 `max-h` + `overflow-auto`
- 点击行直接 `navigate('/rule-pool/:ruleId')`

在 `web/src/pages/rule-pool/index.tsx` 继续作为正式入口导出列表页。

- [ ] **Step 4: Run test to verify it passes**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm test -- src/pages/rule-pool/index.test.tsx`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/rule-pool/rule-pool-list.tsx web/src/lib/api/rule-pool.ts web/src/types/rule-pool.ts web/src/pages/rule-pool/index.tsx web/src/pages/rule-pool/index.test.tsx
git commit -m "feat(rule-pool-ui): rebuild rule pool list workspace"
```

### Task 3: Build the rule pool detail page for rule evidence, review, and backtest entry

**Files:**
- Modify: `web/src/features/rule-pool/rule-pool-detail.tsx`
- Modify: `web/src/features/rule-pool/index.ts`
- Modify: `web/src/pages/rule-pool/RulePoolDetailPage.tsx`
- Modify: `web/src/pages/rule-pool/RulePoolDetailPage.test.tsx`
- Modify: `web/src/app/router.tsx`
- Modify: `web/src/app/route-registry.ts`
- Modify: `web/src/app/route-registry.test.ts`

- [ ] **Step 1: Write the failing test**

新增详情页测试，覆盖：
- 返回按钮存在
- 规则详情、适用性画像、审核动作、审计历史、规则回测都显示
- 用户可以修改回测参数后提交 `rule-pool-backtest`
- 提交成功后显示跳转 Job 详情按钮
- 审核动作在审计历史上方
- 点击列表项后能进入详情页路由

- [ ] **Step 2: Run test to verify it fails**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm test -- src/pages/rule-pool/RulePoolDetailPage.test.tsx src/app/route-registry.test.ts`

Expected: FAIL because detail page route/export and some interaction assertions are not yet aligned.

- [ ] **Step 3: Write minimal implementation**

在 `web/src/features/rule-pool/rule-pool-detail.tsx`：
- 读取规则详情、适用性画像列表和当前画像详情
- 顶部提供返回按钮
- 详情页布局按“规则详情 -> 适用性画像 -> 规则回测 -> 审核动作 -> 审计历史”排列
- 回测入口允许用户调整日期、最小置信度和 market regime version 后提交
- 成功后保存 `job.id` 并提供“前往 Job 详情”按钮

在 `web/src/features/rule-pool/index.ts` 和 `web/src/pages/rule-pool/RulePoolDetailPage.tsx` 暴露详情页。

在 `web/src/app/router.tsx` 和 `web/src/app/route-registry.ts` 注册 `/rule-pool/:ruleId`。

- [ ] **Step 4: Run test to verify it passes**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm test -- src/pages/rule-pool/RulePoolDetailPage.test.tsx src/app/route-registry.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/features/rule-pool/rule-pool-detail.tsx web/src/features/rule-pool/index.ts web/src/pages/rule-pool/RulePoolDetailPage.tsx web/src/pages/rule-pool/RulePoolDetailPage.test.tsx web/src/app/router.tsx web/src/app/route-registry.ts web/src/app/route-registry.test.ts
git commit -m "feat(rule-pool-ui): add rule detail workspace"
```

### Task 4: Refresh API client coverage for the new rule-pool contract

**Files:**
- Modify: `web/src/lib/api/rule-pool.test.ts`
- Modify: `web/src/lib/api/rule-pool.ts`

- [ ] **Step 1: Write the failing test**

补充 API 客户端测试，覆盖 `listRulePoolFilterOptions()`、列表查询参数和详情页相关接口调用顺序。

- [ ] **Step 2: Run test to verify it fails**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm test -- src/lib/api/rule-pool.test.ts`

Expected: FAIL because新接口或调用次序尚未稳定。

- [ ] **Step 3: Write minimal implementation**

确保 `web/src/lib/api/rule-pool.ts` 中所有新接口都有对应 fetch 路径和请求体结构，且不会把空值字段错误拼进 query string。

- [ ] **Step 4: Run test to verify it passes**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm test -- src/lib/api/rule-pool.test.ts`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/lib/api/rule-pool.test.ts web/src/lib/api/rule-pool.ts
git commit -m "test(rule-pool): cover canonical api client"
```

### Task 5: Final verification sweep

**Files:**
- Review: all files touched above

- [ ] **Step 1: Run targeted backend tests**

Run: `python -m pytest tests/unit/services/test_rule_pool_service.py tests/api/routers/test_rule_pool.py tests/api/test_ui_openapi_contract.py -q`

Expected: PASS.

- [ ] **Step 2: Run targeted frontend tests**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm typecheck`

Expected: PASS.

- [ ] **Step 3: Run rule-pool UI tests**

Run: `PATH=/Users/wanghui/.nvm/versions/node/v18.20.8/bin:$PATH /Users/wanghui/.nvm/versions/node/v18.20.8/bin/pnpm test -- src/pages/rule-pool/index.test.tsx src/pages/rule-pool/RulePoolDetailPage.test.tsx src/lib/api/rule-pool.test.ts`

Expected: PASS.

- [ ] **Step 4: Review residual entry points**

确认 `/rule-pool` 是正式列表入口，`/rule-pool/:ruleId` 是正式详情入口，旧 `strategy-studio` 仅作为兼容层保留，不再承担新规则池页面职责。

